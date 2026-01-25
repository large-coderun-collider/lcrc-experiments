from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from typing import List, Optional

from .breaker import CircuitBreaker, CircuitOpenError


@dataclass
class StepResult:
    i: int
    t: float
    action: str
    allowed: bool
    state: str
    failures: int
    successes: int
    open_until: float
    outcome: Optional[str] = None  # "ok" | "fail" | "open"


class ManualClock:
    def __init__(self, start: float = 0.0) -> None:
        self.t = float(start)

    def now(self) -> float:
        return self.t

    def advance(self, dt: float) -> None:
        self.t += float(dt)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="lcrc-breaker", description="Circuit breaker (LCRC Fill 0003).")
    sub = p.add_subparsers(dest="cmd", required=True)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--failure-threshold", type=int, default=5)
    common.add_argument("--success-threshold", type=int, default=2)
    common.add_argument("--cooldown", type=float, default=5.0)

    s_sim = sub.add_parser("simulate", parents=[common], help="Simulate a deterministic sequence.")
    s_sim.add_argument("--dt", type=float, default=0.1, help="Default time delta between steps.")
    s_sim.add_argument(
        "--seq",
        type=str,
        required=True,
        help="Comma-separated steps: ok,fail,call,wait:SECONDS",
    )
    s_sim.add_argument("--json", action="store_true", help="Output JSON")

    s_call = sub.add_parser("call", parents=[common], help="Single call attempt (ok/fail).")
    s_call.add_argument("--ok", action="store_true", help="Call succeeds")
    s_call.add_argument("--fail", action="store_true", help="Call raises an exception")
    s_call.add_argument("--json", action="store_true", help="Output JSON")

    return p


def _make_breaker(args, clock: ManualClock) -> CircuitBreaker:
    return CircuitBreaker(
        failure_threshold=args.failure_threshold,
        success_threshold=args.success_threshold,
        cooldown=args.cooldown,
        clock=clock.now,
    )


def _snap(b: CircuitBreaker) -> dict:
    s = b.snapshot()
    return {
        "state": s.state.value,
        "failures": s.failures,
        "successes": s.successes,
        "open_until": s.open_until,
    }


def simulate(args) -> int:
    clock = ManualClock(0.0)
    b = _make_breaker(args, clock)

    seq = [x.strip() for x in args.seq.split(",") if x.strip()]
    results: List[StepResult] = []

    def ok_fn():
        return "ok"

    def fail_fn():
        raise RuntimeError("simulated failure")

    for i, token in enumerate(seq):
        action = token
        if token.startswith("wait:"):
            seconds = float(token.split(":", 1)[1])
            clock.advance(seconds)
            b.state()  # allow time-based transition
            snap = _snap(b)
            results.append(
                StepResult(
                    i=i,
                    t=clock.now(),
                    action=action,
                    allowed=b.allow(),
                    state=snap["state"],
                    failures=snap["failures"],
                    successes=snap["successes"],
                    open_until=snap["open_until"],
                    outcome="wait",
                )
            )
            continue

        # default step spacing
        if i > 0:
            clock.advance(args.dt)

        if token == "ok":
            try:
                b.call(ok_fn)
                outcome = "ok"
            except CircuitOpenError:
                outcome = "open"
            snap = _snap(b)
        elif token == "fail":
            try:
                b.call(fail_fn)
                outcome = "fail"
            except CircuitOpenError:
                outcome = "open"
            except RuntimeError:
                outcome = "fail"
            snap = _snap(b)
        elif token == "call":
            # "call" means attempt a no-op ok call, useful to see OPEN behavior
            try:
                b.call(ok_fn)
                outcome = "ok"
            except CircuitOpenError:
                outcome = "open"
            snap = _snap(b)
        else:
            raise SystemExit(f"error: unknown step {token!r}")

        results.append(
            StepResult(
                i=i,
                t=clock.now(),
                action=action,
                allowed=(outcome != "open"),
                state=snap["state"],
                failures=snap["failures"],
                successes=snap["successes"],
                open_until=snap["open_until"],
                outcome=outcome,
            )
        )

    if args.json:
        payload = {
            "params": {
                "failure_threshold": args.failure_threshold,
                "success_threshold": args.success_threshold,
                "cooldown": args.cooldown,
                "dt": args.dt,
                "seq": args.seq,
            },
            "results": [asdict(r) for r in results],
        }
        print(json.dumps(payload, indent=2))
    else:
        for r in results:
            print(
                f"t={r.t:.3f} i={r.i:02d} action={r.action:>8} "
                f"outcome={r.outcome:>4} state={r.state:>9} "
                f"f={r.failures} s={r.successes}"
            )

    return 0


def single_call(args) -> int:
    if args.ok and args.fail:
        raise SystemExit("error: choose only one of --ok or --fail")
    if not args.ok and not args.fail:
        raise SystemExit("error: choose one of --ok or --fail")

    clock = ManualClock(0.0)
    b = _make_breaker(args, clock)

    def ok_fn():
        return "ok"

    def fail_fn():
        raise RuntimeError("simulated failure")

    try:
        if args.ok:
            b.call(ok_fn)
            outcome = "ok"
        else:
            b.call(fail_fn)
            outcome = "fail"
    except CircuitOpenError:
        outcome = "open"
    except RuntimeError:
        outcome = "fail"

    snap = _snap(b)

    if args.json:
        print(json.dumps({"outcome": outcome, "snapshot": snap}, indent=2))
    else:
        print(f"outcome={outcome} state={snap['state']} failures={snap['failures']} successes={snap['successes']}")

    return 0


def main() -> None:
    args = build_parser().parse_args()
    try:
        if args.cmd == "simulate":
            raise SystemExit(simulate(args))
        if args.cmd == "call":
            raise SystemExit(single_call(args))
        raise SystemExit(f"error: unknown command {args.cmd!r}")
    except ValueError as e:
        raise SystemExit(f"error: {e}") from e
