from __future__ import annotations

import time
import uuid
from collections import deque
from datetime import datetime, timezone
from threading import Lock


class ObservabilityRecorder:
    def __init__(self, max_items: int = 500) -> None:
        self.logs = deque(maxlen=max_items)
        self.traces = deque(maxlen=max_items)
        self.request_count = 0
        self.error_count = 0
        self.total_duration_ms = 0.0
        self._lock = Lock()

    def start_trace(self) -> tuple[str, float]:
        return uuid.uuid4().hex, time.perf_counter()

    def record_request(self, trace_id: str, started_at: float, method: str, path: str, status: int, actor: str = "anonymous") -> None:
        duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
        trace = {
            "traceId": trace_id,
            "time": iso_now(),
            "method": method,
            "path": path,
            "status": status,
            "durationMs": duration_ms,
            "actor": actor,
        }
        level = "error" if status >= 500 else "warning" if status >= 400 else "info"
        self._append(trace, level)

    def _append(self, trace: dict, level: str) -> None:
        log = {
            "time": iso_now(),
            "level": level,
            "message": "http.request",
            "context": trace,
        }
        with self._lock:
            self.request_count += 1
            self.total_duration_ms += float(trace["durationMs"])
            if int(trace["status"]) >= 400:
                self.error_count += 1
            self.traces.appendleft(trace)
            self.logs.appendleft(log)

    def log(self, level: str, message: str, context: dict | None = None) -> None:
        with self._lock:
            self.logs.appendleft(
                {
                    "time": iso_now(),
                    "level": level,
                    "message": message,
                    "context": context or {},
                }
            )

    def list_logs(self, limit: int = 100) -> list[dict]:
        with self._lock:
            return list(self.logs)[:limit]

    def list_traces(self, limit: int = 100) -> list[dict]:
        with self._lock:
            return list(self.traces)[:limit]

    def metrics(self) -> dict:
        with self._lock:
            avg = self.total_duration_ms / self.request_count if self.request_count else 0
            return {
                "requestCount": self.request_count,
                "errorCount": self.error_count,
                "avgDurationMs": round(avg, 2),
            }


def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()
