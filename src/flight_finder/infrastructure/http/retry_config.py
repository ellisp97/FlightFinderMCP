from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence


@dataclass(frozen=True, slots=True)
class RetryConfig:
    max_retries: int = 3
    min_wait_seconds: float = 2.0
    max_wait_seconds: float = 10.0
    multiplier: float = 1.0
    retryable_status_codes: tuple[int, ...] = (429, 500, 502, 503, 504)

    def get_wait_time(self, attempt: int) -> float:
        wait = self.min_wait_seconds * (2 ** attempt) * self.multiplier
        return min(wait, self.max_wait_seconds)

    def is_retryable_status(self, status_code: int) -> bool:
        return status_code in self.retryable_status_codes


DEFAULT_RETRY_CONFIG = RetryConfig()
