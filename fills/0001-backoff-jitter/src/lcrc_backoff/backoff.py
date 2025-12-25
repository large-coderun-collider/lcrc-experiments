from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Callable, Iterator, Optional


def capped_exponential(attempt: int, base: float, factor: float, cap: float) -> float:
    if attempt < 0:
        raise ValueError("attempt must be >= 0")
    if base <= 0:
        raise ValueError("base must be > 0")
    if factor < 1:
        raise ValueError("factor must be >= 1")
    if cap <= 0:
        raise ValueError("cap must be > 0")

    raw = base * (factor ** attempt)
    return min(cap, raw)


def jitter_full(delay: float, rng: random.Random) -> float:
    # Full jitter: uniform between 0 and delay
    if delay < 0:
        raise ValueError("delay must be >= 0")    
    return rng.uniform(0.0, delay)


def jitter_equal(delay: float, rng: random.Random) -> float:
    # Equal jitter: half deterministic, half random
    if delay < 0:
        raise ValueError("delay must be >= 0")    
    return delay / 2.0 + rng.uniform(0.0, delay / 2.0)


def compute_delay(
    attempt: int,
    *,
    base: float = 0.5,
    factor: float = 2.0,
    cap: float = 30.0,
    jitter: str = "full",
    rng: Optional[random.Random] = None,
) -> float:
    """
    Compute retry delay for a given attempt (0-based).

    jitter:
      - "none": no jitter (deterministic)
      - "full": full jitter
      - "equal": equal jitter
    """
    rng = rng or random.Random()
    d = capped_exponential(attempt, base, factor, cap)

    jitter = jitter.lower().strip()
    if jitter == "none":
        return d
    if jitter == "full":
        return jitter_full(d, rng)
    if jitter == "equal":
        return jitter_equal(d, rng)

    raise ValueError(f"unknown jitter mode: {jitter!r}")


@dataclass(frozen=True)
class RetryPolicy:
    max_attempts: int = 5
    base: float = 0.5
    factor: float = 2.0
    cap: float = 30.0
    jitter: str = "full"
    seed: Optional[int] = None

    def delays(self) -> Iterator[float]:
        if self.max_attempts <= 0:
            raise ValueError("max_attempts must be > 0")
        rng = random.Random(self.seed)
        for attempt in range(self.max_attempts):
            yield compute_delay(
                attempt,
                base=self.base,
                factor=self.factor,
                cap=self.cap,
                jitter=self.jitter,
                rng=rng,
            )


def retry(
    fn: Callable[[], object],
    *,
    policy: RetryPolicy,
    should_retry: Callable[[Exception], bool] = lambda _e: True,
    sleep: Callable[[float], None],
) -> object:
    """
    Execute fn with retries. sleep injected for testability.
    """
    last_exc: Optional[Exception] = None
    for i, delay in enumerate(policy.delays()):
        try:
            return fn()
        except Exception as e:  # noqa: BLE001 (intentional: policy decides)
            last_exc = e
            if i == policy.max_attempts - 1 or not should_retry(e):
                raise
            sleep(delay)

    # defensive (should never happen)
    assert last_exc is not None
    raise last_exc

