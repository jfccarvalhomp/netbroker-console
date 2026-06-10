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

