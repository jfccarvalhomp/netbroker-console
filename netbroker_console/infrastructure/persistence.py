from __future__ import annotations

import copy
import json
import threading
from pathlib import Path

from netbroker_console.domain.seed import INITIAL_STATE


class JsonStateRepository:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.lock = threading.RLock()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self._write(copy.deepcopy(INITIAL_STATE))

    def read(self) -> dict:
        with self.lock:
            try:
                return json.loads(self.path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                state = copy.deepcopy(INITIAL_STATE)
                self._write(state)
                return state

    def update(self, mutator) -> dict:
        with self.lock:
            state = self.read()
            mutator(state)
            self._write(state)
            return state

    def _write(self, state: dict) -> None:
        temp = self.path.with_suffix(".tmp")
        temp.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
        temp.replace(self.path)


class PostgresStateRepository:
    def __init__(self, dsn: str) -> None:
        if not dsn:
            raise ValueError("PostgreSQL DSN is required")
        try:
            import psycopg2
        except ImportError as exc:
            raise RuntimeError("Install python3-psycopg2 to use PostgreSQL persistence") from exc

        self.dsn = dsn
        self.psycopg2 = psycopg2
        self.lock = threading.RLock()
        self._ensure_schema()
        if not self._has_state():
            self._write(copy.deepcopy(INITIAL_STATE))

    def read(self) -> dict:
        with self.lock:
            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute("select queue_depth from platform_state where id = 1")
                    row = cur.fetchone()
                    queue_depth = row[0] if row else INITIAL_STATE["queueDepth"]

                    cur.execute("select host, ip, vendor, model, site, status, cpu, backup from devices order by host")
                    devices = [
                        {
                            "host": host,
                            "ip": ip,
                            "vendor": vendor,
                            "model": model,
                            "site": site,
                            "status": status,
                            "cpu": cpu,
                            "backup": backup,
                        }
                        for host, ip, vendor, model, site, status, cpu, backup in cur.fetchall()
                    ]

                    cur.execute("select id, severity, device, text, source from alarms order by id")
                    alarms = [
                        {"id": alarm_id, "severity": severity, "device": device, "text": text, "source": source}
                        for alarm_id, severity, device, text, source in cur.fetchall()
                    ]

                    cur.execute("select name, description, queue from jobs order by queue")
                    jobs = [
                        {"name": name, "desc": description, "queue": queue}
                        for name, description, queue in cur.fetchall()
                    ]

                    cur.execute("select event_time, message from events order by position")
                    events = [[event_time, message] for event_time, message in cur.fetchall()]

            return {
                "queueDepth": queue_depth,
                "devices": devices,
                "alarms": alarms,
                "jobs": jobs,
                "events": events,
            }

    def update(self, mutator) -> dict:
        with self.lock:
            state = self.read()
            mutator(state)
            self._write(state)
            return state

    def _connect(self):
        return self.psycopg2.connect(self.dsn)

    def _ensure_schema(self) -> None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    create table if not exists platform_state (
                      id integer primary key,
                      queue_depth integer not null
                    )
                    """
                )
                cur.execute(
                    """
                    create table if not exists devices (
                      host text primary key,
                      ip text not null,
                      vendor text not null,
                      model text not null,
                      site text not null,
                      status text not null,
                      cpu integer not null,
                      backup text not null
                    )
                    """
                )
                cur.execute(
                    """
                    create table if not exists alarms (
                      id integer primary key,
                      severity text not null,
                      device text not null,
                      text text not null,
                      source text not null
                    )
                    """
                )
                cur.execute(
                    """
                    create table if not exists jobs (
                      queue text primary key,
                      name text not null,
                      description text not null
                    )
                    """
                )
                cur.execute(
                    """
                    create table if not exists events (
                      position integer primary key,
                      event_time text not null,
                      message text not null
                    )
                    """
                )

    def _has_state(self) -> bool:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute("select exists(select 1 from platform_state where id = 1)")
                return bool(cur.fetchone()[0])

    def _write(self, state: dict) -> None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute("delete from events")
                cur.execute("delete from jobs")
                cur.execute("delete from alarms")
                cur.execute("delete from devices")
                cur.execute("delete from platform_state")

                cur.execute(
                    "insert into platform_state (id, queue_depth) values (1, %s)",
                    (int(state.get("queueDepth", 0)),),
                )

                for device in state.get("devices", []):
                    cur.execute(
                        """
                        insert into devices (host, ip, vendor, model, site, status, cpu, backup)
                        values (%s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            device["host"],
                            device["ip"],
                            device["vendor"],
                            device["model"],
                            device["site"],
                            device["status"],
                            int(device["cpu"]),
                            device["backup"],
                        ),
                    )

                for alarm in state.get("alarms", []):
                    cur.execute(
                        "insert into alarms (id, severity, device, text, source) values (%s, %s, %s, %s, %s)",
                        (int(alarm["id"]), alarm["severity"], alarm["device"], alarm["text"], alarm["source"]),
                    )

                for job in state.get("jobs", []):
                    cur.execute(
                        "insert into jobs (queue, name, description) values (%s, %s, %s)",
                        (job["queue"], job["name"], job["desc"]),
                    )

                for position, event in enumerate(state.get("events", [])):
                    cur.execute(
                        "insert into events (position, event_time, message) values (%s, %s, %s)",
                        (position, event[0], event[1]),
                    )
