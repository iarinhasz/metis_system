"""Doubles Redis pequenos para validar integração e concorrência dos clientes."""

from __future__ import annotations

import threading
import time


class MemoryRedis:
    def __init__(self) -> None:
        self.values: dict[str, bytes] = {}
        self.theoretical_arrivals: dict[str, float] = {}
        self.semaphore_slots: dict[str, str] = {}
        self.lock = threading.Lock()

    def get(self, key: str) -> bytes | None:
        with self.lock:
            return self.values.get(key)

    def set(self, name: str, value: bytes, ex: int | None = None) -> bool:
        del ex
        with self.lock:
            self.values[name] = value
        return True

    def time(self) -> tuple[int, int]:
        current = time.time()
        seconds = int(current)
        microseconds = int((current - seconds) * 1_000_000)
        return seconds, microseconds

    def eval(self, script: str, numkeys: int, *args: str | int | float) -> int:
        if "local owner" in script:
            owner = str(args[numkeys])
            with self.lock:
                for index, key in enumerate(args[:numkeys], start=1):
                    if str(key) not in self.semaphore_slots:
                        self.semaphore_slots[str(key)] = owner
                        return index
            return 0
        if "return redis.call('DEL'" in script:
            key, owner = str(args[0]), str(args[1])
            with self.lock:
                if self.semaphore_slots.get(key) == owner:
                    del self.semaphore_slots[key]
                    return 1
            return 0
        if numkeys != 1:
            raise AssertionError("O token bucket deve operar numa chave por provedor.")
        key, now_value, rate_value, capacity_value = args
        now = float(now_value)
        rate = float(rate_value)
        capacity = int(capacity_value)
        interval = 1 / rate
        tolerance = (capacity - 1) * interval
        with self.lock:
            arrival = self.theoretical_arrivals.get(str(key), now)
            wait = max(0.0, arrival - tolerance - now)
            self.theoretical_arrivals[str(key)] = max(now, arrival) + interval
        return int(wait * 1000 + 0.999)


def monotonic_seconds() -> float:
    return time.monotonic()
