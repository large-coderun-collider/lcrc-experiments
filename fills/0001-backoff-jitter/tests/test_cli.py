import unittest
from lcrc_backoff.cli import build_parser
from lcrc_backoff.backoff import RetryPolicy

class TestCLI(unittest.TestCase):
    def test_cli_builds_policy(self):
        p = build_parser()
        args = p.parse_args(["--max-attempts", "6", "--base", "0.5", "--cap", "10", "--seed", "42", "--jitter", "full"])
        policy = RetryPolicy(
            max_attempts=args.max_attempts,
            base=args.base,
            factor=args.factor,
            cap=args.cap,
            jitter=args.jitter,
            seed=args.seed,
        )
        self.assertEqual(policy.max_attempts, 6)
