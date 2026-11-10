"""Lightweight in-process metrics for observability."""
from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass, field
from threading import Lock
from typing import Any, Dict


@dataclass
class Metrics:
    _lock: Lock = field(default_factory=Lock, repr=False)
    counters: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    timings_ms: Dict[str, list] = field(default_factory=lambda: defaultdict(list))
    last_errors: list = field(default_factory=list)

    def incr(self, name: str, value: int = 1) -> None:
        with self._lock:
            self.counters[name] += value

    def timing(self, name: str, ms: float) -> None:
        with self._lock:
            bucket = self.timings_ms[name]
            bucket.append(ms)
            if len(bucket) > 200:
                del bucket[:-100]

    def error(self, where: str, message: str) -> None:
        with self._lock:
            self.incr(f"error.{where}")
            self.last_errors.append({"where": where, "message": message[:300], "ts": time.time()})
            if len(self.last_errors) > 50:
                self.last_errors = self.last_errors[-50:]

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            avg = {}
            for k, vals in self.timings_ms.items():
                avg[k] = round(sum(vals) / len(vals), 1) if vals else 0
            return {
                "counters": dict(self.counters),
                "avg_timing_ms": avg,
                "recent_errors": list(self.last_errors[-10:]),
            }


metrics = Metrics()
