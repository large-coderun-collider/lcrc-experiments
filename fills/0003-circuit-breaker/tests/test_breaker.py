import unittest

from lcrc_breaker.breaker import CircuitBreaker, CircuitOpenError, BreakerState


class FakeClock:
    def __init__(self, t: float = 0.0) -> None:
        self.t = float(t)

    def now(self) -> float:
        return self.t

    def advance(self, dt: float) -> None:
        self.t += float(dt)


class TestCircuitBreaker(unittest.TestCase):
    def test_invalid_params(self):
        with self.assertRaises(ValueError):
            CircuitBreaker(failure_threshold=0)
        with self.assertRaises(ValueError):
            CircuitBreaker(success_threshold=0)
        with self.assertRaises(ValueError):
            CircuitBreaker(cooldown=-1)

    def test_closed_to_open_on_failure_threshold(self):
        clock = FakeClock(0.0)
        b = CircuitBreaker(failure_threshold=3, success_threshold=2, cooldown=5.0, clock=clock.now)

        def fail():
            raise RuntimeError("x")

        self.assertEqual(b.state(), BreakerState.CLOSED)

        for _ in range(2):
            with self.assertRaises(RuntimeError):
                b.call(fail)
            self.assertEqual(b.state(), BreakerState.CLOSED)

        with self.assertRaises(RuntimeError):
            b.call(fail)
        self.assertEqual(b.state(), BreakerState.OPEN)

    def test_open_is_fail_fast_until_cooldown(self):
        clock = FakeClock(0.0)
        b = CircuitBreaker(failure_threshold=1, success_threshold=1, cooldown=2.0, clock=clock.now)

        def fail():
            raise RuntimeError("x")

        with self.assertRaises(RuntimeError):
            b.call(fail)
        self.assertEqual(b.state(), BreakerState.OPEN)

        with self.assertRaises(CircuitOpenError):
            b.call(lambda: "ok")

        clock.advance(1.9)
        with self.assertRaises(CircuitOpenError):
            b.call(lambda: "ok")

        clock.advance(0.2)
        # cooldown expired -> HALF_OPEN, call should be attempted
        self.assertEqual(b.state(), BreakerState.HALF_OPEN)

    def test_half_open_success_closes(self):
        clock = FakeClock(0.0)
        b = CircuitBreaker(failure_threshold=1, success_threshold=2, cooldown=1.0, clock=clock.now)

        def fail():
            raise RuntimeError("x")

        with self.assertRaises(RuntimeError):
            b.call(fail)
        self.assertEqual(b.state(), BreakerState.OPEN)

        clock.advance(1.0)
        self.assertEqual(b.state(), BreakerState.HALF_OPEN)

        b.call(lambda: "ok")
        self.assertEqual(b.state(), BreakerState.HALF_OPEN)

        b.call(lambda: "ok")
        self.assertEqual(b.state(), BreakerState.CLOSED)

    def test_half_open_failure_reopens(self):
        clock = FakeClock(0.0)
        b = CircuitBreaker(failure_threshold=1, success_threshold=2, cooldown=1.0, clock=clock.now)

        def fail():
            raise RuntimeError("x")

        with self.assertRaises(RuntimeError):
            b.call(fail)
        self.assertEqual(b.state(), BreakerState.OPEN)

        clock.advance(1.0)
        self.assertEqual(b.state(), BreakerState.HALF_OPEN)

        with self.assertRaises(RuntimeError):
            b.call(fail)
        self.assertEqual(b.state(), BreakerState.OPEN)

    def test_success_in_closed_resets_failures(self):
        clock = FakeClock(0.0)
        b = CircuitBreaker(failure_threshold=3, success_threshold=1, cooldown=1.0, clock=clock.now)

        def fail():
            raise RuntimeError("x")

        with self.assertRaises(RuntimeError):
            b.call(fail)
        self.assertEqual(b.snapshot().failures, 1)

        b.call(lambda: "ok")
        self.assertEqual(b.snapshot().failures, 0)

    def test_clock_backwards_is_clamped(self):
        clock = FakeClock(10.0)
        b = CircuitBreaker(failure_threshold=1, success_threshold=1, cooldown=2.0, clock=clock.now)

        def fail():
            raise RuntimeError("x")

        with self.assertRaises(RuntimeError):
            b.call(fail)
        self.assertEqual(b.state(), BreakerState.OPEN)

        # move time backwards
        clock.t = 0.0
        # should still be OPEN (clamped)
        with self.assertRaises(CircuitOpenError):
            b.call(lambda: "ok")


if __name__ == "__main__":
    unittest.main()
