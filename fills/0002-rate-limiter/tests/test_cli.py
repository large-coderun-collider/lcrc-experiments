import unittest

from lcrc_ratelimit.cli import build_parser


class TestCLI(unittest.TestCase):
    def test_parser_exists(self):
        p = build_parser()
        args = p.parse_args(["simulate", "--rate", "1", "--capacity", "2"])
        self.assertEqual(args.cmd, "simulate")
