import unittest
import random

from lcrc_backoff.backoff import capped_exponential, compute_delay, RetryPolicy


class TestBackoff(unittest.TestCase):
    def test_capped_exponential_grows_and_caps(self):
        self.assertEqual(capped_exponential(0, 1.0, 2.0, 10.0), 1.0)
        self.assertEqual(capped_exponential(1, 1.0, 2.0, 10.0), 2.0)
        self.assertEqual(capped_exponential(2, 1.0, 2.0, 10.0), 4.0)
        self.assertEqual(capped_exponential(10, 1.0, 2.0, 10.0), 10.0)

    def test_compute_delay_none_is_deterministic(self):
        self.assertEqual(compute_delay(3, base=1.0, factor=2.0, cap=100.0, jitter="none"), 8.0)

    def test_full_jitter_in_range(self):
        rng = random.Random(123)
        d = compute_delay(4, base=1.0, factor=2.0, cap=100.0, jitter="full", rng=rng)
        # self.assertTrue(0.0 <= d <= 16.0)
        self.assertGreaterEqual(d, 0.0)
        self.assertLessEqual(d, 16.0)

    def test_equal_jitter_in_range(self):
        rng = random.Random(123)
        d = compute_delay(4, base=1.0, factor=2.0, cap=100.0, jitter="equal", rng=rng)
        # self.assertTrue(8.0 <= d <= 16.0)
        self.assertGreaterEqual(d, 8.0)
        self.assertLessEqual(d, 16.0)

    def test_policy_reproducible_with_seed(self):
        p1 = RetryPolicy(max_attempts=5, seed=42, jitter="full")
        p2 = RetryPolicy(max_attempts=5, seed=42, jitter="full")
        self.assertEqual(list(p1.delays()), list(p2.delays()))

    def test_invalid_inputs(self):
        with self.assertRaises(ValueError):
            capped_exponential(-1, 1.0, 2.0, 10.0)
        with self.assertRaises(ValueError):
            capped_exponential(0, 0.0, 2.0, 10.0)
        with self.assertRaises(ValueError):
            capped_exponential(0, 1.0, 0.9, 10.0)
        with self.assertRaises(ValueError):
            capped_exponential(0, 1.0, 2.0, 0.0)

    def test_unknown_jitter_mode(self):
        with self.assertRaises(ValueError):
            compute_delay(0, jitter="banana")

if __name__ == "__main__":
    unittest.main()

