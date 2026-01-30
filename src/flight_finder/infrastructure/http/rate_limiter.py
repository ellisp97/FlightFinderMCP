from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class RateLimiter:
    rate: int
    per: float = 1.0
    _allowance: float = field(init=False, repr=False)
    _last_check: datetime = field(init=False, repr=False)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock, init=False, repr=False)

    def __post_init__(self) -> None:
        self._allowance = float(self.rate)
        self._last_check = datetime.now(timezone.utc)

    async def acquire(self) -> None:
        async with self._lock:
            current = datetime.now(timezone.utc)
            time_passed = (current - self._last_check).total_seconds()
            self._last_check = current

            self._allowance += time_passed * (self.rate / self.per)
            if self._allowance > self.rate:
                self._allowance = float(self.rate)

            if self._allowance < 1.0:
                sleep_time = (1.0 - self._allowance) * (self.per / self.rate)
                await asyncio.sleep(sleep_time)
                self._allowance = 0.0
            else:
                self._allowance -= 1.0

    async def try_acquire(self) -> bool:
        async with self._lock:
            current = datetime.now(timezone.utc)
            time_passed = (current - self._last_check).total_seconds()
            self._last_check = current

            self._allowance += time_passed * (self.rate / self.per)
            if self._allowance > self.rate:
                self._allowance = float(self.rate)

            if self._allowance < 1.0:
                return False

            self._allowance -= 1.0
            return True

    def reset(self) -> None:
        self._allowance = float(self.rate)
        self._last_check = datetime.now(timezone.utc)
