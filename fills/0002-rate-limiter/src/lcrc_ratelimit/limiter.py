from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional


def _validate_positive(name: str, value: float) -> None:
    if value <= 0:
        raise ValueError(f"{name} must be > 0")


@dataclass
class TokenBucketSnapshot:
    rate: float
    capacity: float
    tokens: float
    last_ts: float


class TokenBucket:
    """
    Token Bucket rate limiter.

    - rate: tokens per second
    - capacity: max tokens (burst size)
    - starts full (tokens = capacity)

    clock: injectable for tests (default: time.monotonic)
    """

    def __init__(
        self,
        *,
        rate: float,
        capacity: float,
        clock: Callable[[], float],
        start_full: bool = True,
    ) -> None:
        _validate_positive("rate", float(rate))
        _validate_positive("capacity", float(capacity))

        self._rate = float(rate)
        self._capacity = float(capacity)
        self._clock = clock

        now = float(self._clock())
        self._last_ts = now
        self._tokens = self._capacity if start_full else 0.0

    @property
    def rate(self) -> float:
        return self._rate

    @property
    def capacity(self) -> float:
        return self._capacity

    def snapshot(self) -> TokenBucketSnapshot:
        # Do not mutate on snapshot, keep it simple/predictable.
        return TokenBucketSnapshot(
            rate=self._rate,
            capacity=self._capacity,
            tokens=self._tokens,
            last_ts=self._last_ts,
        )

    def _refill(self, now: Optional[float] = None) -> None:
        t = float(self._clock()) if now is None else float(now)
        if t < self._last_ts:
            # clock moved backwards; clamp (monotonic should not do this, but tests might)
            t = self._last_ts

        elapsed = t - self._last_ts
        if elapsed <= 0:
            return

        self._tokens = min(self._capacity, self._tokens + elapsed * self._rate)
        self._last_ts = t

    def allow(self, *, cost: float = 1.0, now: Optional[float] = None) -> bool:
        cost = float(cost)
        _validate_positive("cost", cost)
        if cost > self._capacity:
            raise ValueError("cost must be <= capacity")

        self._refill(now)
        if self._tokens >= cost:
            self._tokens -= cost
            return True
        return False

    def wait_time(self, *, cost: float = 1.0, now: Optional[float] = None) -> float:
        """
        Returns seconds until a request with given cost would be allowed.
        0.0 means allowed immediately.
        """
        cost = float(cost)
        _validate_positive("cost", cost)
        if cost > self._capacity:
            raise ValueError("cost must be <= capacity")

        self._refill(now)
        if self._tokens >= cost:
            return 0.0

        missing = cost - self._tokens
        return missing / self._rate
