import unittest

from lcrc_ratelimit.limiter import TokenBucket


class FakeClock:
    def __init__(self, start: float = 0.0) -> None:
        self.t = float(start)

    def now(self) -> float:
        return self.t

    def advance(self, dt: float) -> None:
        self.t += float(dt)


class TestTokenBucket(unittest.TestCase):
    def test_starts_full_allows_burst(self):
        c = FakeClock()
        b = TokenBucket(rate=1.0, capacity=5.0, clock=c.now, start_full=True)

        for _ in range(5):
            self.assertTrue(b.allow(cost=1.0))
        self.assertFalse(b.allow(cost=1.0))

    def test_refills_over_time(self):
        c = FakeClock()
        b = TokenBucket(rate=2.0, capacity=4.0, clock=c.now, start_full=False)

        self.assertFalse(b.allow(cost=1.0))
        c.advance(0.5)  # +1 token
        self.assertTrue(b.allow(cost=1.0))
        self.assertFalse(b.allow(cost=1.0))

    def test_caps_at_capacity(self):
        c = FakeClock()
        b = TokenBucket(rate=10.0, capacity=3.0, clock=c.now, start_full=False)

        c.advance(10.0)
        # refill would be 100 tokens, but must cap at 3
        self.assertTrue(b.allow(cost=3.0))
        self.assertFalse(b.allow(cost=0.1))  # empty now

    def test_wait_time(self):
        c = FakeClock()
        b = TokenBucket(rate=2.0, capacity=10.0, clock=c.now, start_full=False)
        # need 1 token at 2 tokens/s -> 0.5s
        self.assertAlmostEqual(b.wait_time(cost=1.0), 0.5)

        c.advance(0.5)
        self.assertEqual(b.wait_time(cost=1.0), 0.0)
        self.assertTrue(b.allow(cost=1.0))

    def test_invalid_params(self):
        c = FakeClock()
        with self.assertRaises(ValueError):
            TokenBucket(rate=0.0, capacity=1.0, clock=c.now)
        with self.assertRaises(ValueError):
            TokenBucket(rate=1.0, capacity=0.0, clock=c.now)

        b = TokenBucket(rate=1.0, capacity=1.0, clock=c.now)
        with self.assertRaises(ValueError):
            b.allow(cost=0.0)
        with self.assertRaises(ValueError):
            b.allow(cost=2.0)  # cost > capacity

    def test_clock_backwards_is_clamped(self):
        # ensure no negative refill weirdness
        class WeirdClock:
            def __init__(self) -> None:
                self.t = 10.0
            def now(self) -> float:
                self.t -= 1.0
                return self.t

        wc = WeirdClock()
        b = TokenBucket(rate=1.0, capacity=1.0, clock=wc.now, start_full=False)
        # should not crash, should be stable
        self.assertFalse(b.allow(cost=1.0))
