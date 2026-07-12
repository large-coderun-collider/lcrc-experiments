from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Callable, Generic, List, Optional, TypeVar

T = TypeVar("T")


class AdmissionResult(str, Enum):
    ACCEPTED = "accepted"
    QUEUED = "queued"
    REJECTED = "rejected"


class BulkheadFullError(RuntimeError):
    """Raised when both concurrent slots and the waiting queue are full."""


@dataclass(frozen=True)
class BulkheadSnapshot:
    max_concurrent: int
    max_queue: int
    active_count: int
    queue_count: int


class Bulkhead(Generic[T]):
    """
    Bulkhead / Bounded Queue concurrency pattern.

    Protects a system from resource exhaustion by strictly bounding:
      1. Active concurrent executions (max_concurrent).
      2. Waiting tasks in queue (max_queue).

    When both are full, incoming work is immediately rejected (Shedding).
    """

    def __init__(self, *, max_concurrent: int = 3, max_queue: int = 5) -> None:
        if max_concurrent <= 0:
            raise ValueError("max_concurrent must be > 0")
        if max_queue < 0:
            raise ValueError("max_queue must be >= 0")

        self._max_concurrent = int(max_concurrent)
        self._max_queue = int(max_queue)

        self._active: int = 0
        self._queue: List[Callable[[], T]] = []

    @property
    def max_concurrent(self) -> int:
        return self._max_concurrent

    @property
    def max_queue(self) -> int:
        return self._max_queue

    def snapshot(self) -> BulkheadSnapshot:
        return BulkheadSnapshot(
            max_concurrent=self._max_concurrent,
            max_queue=self._max_queue,
            active_count=self._active,
            queue_count=len(self._queue),
        )

    def try_acquire(self) -> AdmissionResult:
        """
        Evaluates admission without executing a task.
        """
        if self._active < self._max_concurrent:
            self._active += 1
            return AdmissionResult.ACCEPTED
        if len(self._queue) < self._max_queue:
            return AdmissionResult.QUEUED
        return AdmissionResult.REJECTED

    def release(self) -> Optional[Callable[[], T]]:
        """
        Releases an active slot. If tasks are waiting in the queue,
        pops and returns the next task to be executed.
        """
        if self._active > 0:
            self._active -= 1

        if self._queue and self._active < self._max_concurrent:
            self._active += 1
            return self._queue.pop(0)
        return None

    def submit(self, fn: Callable[[], T]) -> AdmissionResult:
        """
        Submits a task for execution or queuing.
        Raises BulkheadFullError if the bulkhead is saturated.
        """
        status = self.try_acquire()
        if status == AdmissionResult.ACCEPTED:
            try:
                fn()
            finally:
                self.release()
            return AdmissionResult.ACCEPTED
        elif status == AdmissionResult.QUEUED:
            self._queue.append(fn)
            return AdmissionResult.QUEUED
        else:
            raise BulkheadFullError("bulkhead saturation: concurrent slots and queue are full")