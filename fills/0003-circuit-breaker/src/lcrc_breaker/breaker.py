from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Callable, Generic, Optional, TypeVar

T = TypeVar("T")


class BreakerState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitOpenError(RuntimeError):
    """Raised when a call is rejected while the circuit is OPEN."""


@dataclass
class Snapshot:
    state: BreakerState
    failures: int
    successes: int
    open_until: float


class CircuitBreaker(Generic[T]):
    """
    Circuit breaker finite-state machine.

    States:
      - CLOSED: calls pass; failures increment. On threshold -> OPEN.
      - OPEN: calls rejected until cooldown expires. Then -> HALF_OPEN.
      - HALF_OPEN: probing. successes increment. On success_threshold -> CLOSED.
                  Any failure -> OPEN.

    clock: injected time source (float seconds).
    Backward time is clamped (treated as no time elapsed).
    """

    def __init__(
        self,
        *,
        failure_threshold: int = 5,
        success_threshold: int = 2,
        cooldown: float = 5.0,
        clock: Optional[Callable[[], float]] = None,
    ) -> None:
        if failure_threshold <= 0:
            raise ValueError("failure_threshold must be > 0")
        if success_threshold <= 0:
            raise ValueError("success_threshold must be > 0")
        if cooldown < 0:
            raise ValueError("cooldown must be >= 0")

        self._failure_threshold = int(failure_threshold)
        self._success_threshold = int(success_threshold)
        self._cooldown = float(cooldown)
        self._clock = clock or (lambda: 0.0)

        self._state: BreakerState = BreakerState.CLOSED
        self._failures: int = 0
        self._successes: int = 0
        self._open_until: float = 0.0
        self._last_t: float = self._clock()

    def _now(self) -> float:
        t = float(self._clock())
        # Clamp backward time
        if t < self._last_t:
            t = self._last_t
        self._last_t = t
        return t

    def state(self) -> BreakerState:
        # Lazily advance OPEN -> HALF_OPEN if cooldown expired
        self._maybe_transition_on_time()
        return self._state

    def snapshot(self) -> Snapshot:
        self._maybe_transition_on_time()
        return Snapshot(
            state=self._state,
            failures=self._failures,
            successes=self._successes,
            open_until=self._open_until,
        )

    def _maybe_transition_on_time(self) -> None:
        if self._state != BreakerState.OPEN:
            return
        now = self._now()
        if now >= self._open_until:
            # start probing
            self._state = BreakerState.HALF_OPEN
            self._successes = 0
            # failures in HALF_OPEN are not "counted", they just reopen
            self._failures = 0

    def allow(self) -> bool:
        """
        Admission check without executing any function.
        Returns True if a call would be attempted right now.
        """
        self._maybe_transition_on_time()
        return self._state != BreakerState.OPEN

    def _trip_open(self) -> None:
        now = self._now()
        self._state = BreakerState.OPEN
        self._open_until = now + self._cooldown
        self._failures = 0
        self._successes = 0

    def _close(self) -> None:
        self._state = BreakerState.CLOSED
        self._failures = 0
        self._successes = 0
        self._open_until = 0.0

    def call(self, fn: Callable[[], T]) -> T:
        """
        Execute fn if allowed by breaker state, updating transitions.

        Raises CircuitOpenError if OPEN and cooldown not expired.
        """
        self._maybe_transition_on_time()

        if self._state == BreakerState.OPEN:
            raise CircuitOpenError("circuit is open")

        try:
            result = fn()
        except Exception:
            self._on_failure()
            raise
        else:
            self._on_success()
            return result

    def _on_failure(self) -> None:
        if self._state == BreakerState.CLOSED:
            self._failures += 1
            if self._failures >= self._failure_threshold:
                self._trip_open()
            return

        # HALF_OPEN: any failure reopens immediately
        if self._state == BreakerState.HALF_OPEN:
            self._trip_open()
            return

        # OPEN failures do not occur (calls are blocked), defensive:
        self._trip_open()

    def _on_success(self) -> None:
        if self._state == BreakerState.CLOSED:
            # On success in CLOSED, reset consecutive failures
            self._failures = 0
            return

        if self._state == BreakerState.HALF_OPEN:
            self._successes += 1
            if self._successes >= self._success_threshold:
                self._close()
            return

        # OPEN success does not occur, defensive:
        self._close()
