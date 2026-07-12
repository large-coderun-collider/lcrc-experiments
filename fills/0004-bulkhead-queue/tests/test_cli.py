import subprocess
import sys
import unittest


class TestCLI(unittest.TestCase):
    def test_check_cmd(self):
        res = subprocess.run(
            [sys.executable, "-m", "lcrc_bulkhead.cli", "check", "--max-concurrent", "2"],
            capture_output=True,
            text=True,
            check=True,
        )
        self.assertIn("result=accepted", res.stdout)

    def test_simulate_cmd_json(self):
        res = subprocess.run(
            [
                sys.executable,
                "-m",
                "lcrc_bulkhead.cli",
                "simulate",
                "--max-concurrent",
                "1",
                "--max-queue",
                "1",
                "--seq",
                "acquire,acquire,acquire,release",
                "--json",
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        self.assertIn('"result": "accepted"', res.stdout)
        self.assertIn('"result": "queued"', res.stdout)
        self.assertIn('"result": "rejected"', res.stdout)
        self.assertIn('"result": "released_with_next"', res.stdout)


if __name__ == "__main__":
    unittest.main()