import unittest

from lcrc_breaker.cli import build_parser


class TestCLI(unittest.TestCase):
    def test_parser_exists(self):
        p = build_parser()
        args = p.parse_args(["simulate", "--seq", "ok,fail,call"])
        self.assertEqual(args.cmd, "simulate")


if __name__ == "__main__":
    unittest.main()
