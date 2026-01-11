from __future__ import annotations

import argparse
import json
from dataclasses import asdict

from .limiter import TokenBucket


class SimClock:
    def __init__(self, start: float = 0.0) -> None:
        self.t = float(start)

    def now(self) -> float:
        return self.t

    def advance(self, dt: float) -> None:
        self.t += float(dt)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="lcrc-ratelimit", description="LCRC Fill 0002: Token Bucket Rate Limiter")
    sub = p.add_subparsers(dest="cmd", required=True)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--rate", type=float, required=True, help="tokens per second")
    common.add_argument("--capacity", type=float, required=True, help="max tokens (burst)")
    common.add_argument("--cost", type=float, default=1.0, help="tokens per request")
    common.add_argument("--json", action="store_true", help="output JSON")

    p_check = sub.add_parser("check", parents=[common], help="single allow() check")
    p_check.add_argument("--start-full", action="store_true", default=True)

    p_sim = sub.add_parser("simulate", parents=[common], help="deterministic simulation (no sleeping)")
    p_sim.add_argument("--n", type=int, default=10, help="number of requests")
    p_sim.add_argument("--interval", type=float, default=0.1, help="seconds between requests (virtual time)")
    p_sim.add_argument("--start", type=float, default=0.0, help="simulation start timestamp")
    p_sim.add_argument("--start-full", action="store_true", default=True)

    return p


def cmd_check(args: argparse.Namespace) -> int:
    clock = SimClock()
    bucket = TokenBucket(rate=args.rate, capacity=args.capacity, clock=clock.now, start_full=args.start_full)
    allowed = bucket.allow(cost=args.cost)
    snap = bucket.snapshot()

    if args.json:
        print(json.dumps({"allowed": allowed, "bucket": asdict(snap)}, indent=2))
    else:
        print(f"allowed={allowed} tokens={snap.tokens:.6f}/{snap.capacity:.6f}")
    return 0


def cmd_simulate(args: argparse.Namespace) -> int:
    clock = SimClock(start=args.start)
    bucket = TokenBucket(rate=args.rate, capacity=args.capacity, clock=clock.now, start_full=args.start_full)

    results = []
    for i in range(args.n):
        t = clock.now()
        allowed = bucket.allow(cost=args.cost)
        snap = bucket.snapshot()
        item = {
            "i": i,
            "t": t,
            "allowed": allowed,
            "tokens": snap.tokens,
            "capacity": snap.capacity,
        }
        results.append(item)
        clock.advance(args.interval)

    if args.json:
        payload = {
            "params": {
                "rate": args.rate,
                "capacity": args.capacity,
                "cost": args.cost,
                "n": args.n,
                "interval": args.interval,
            },
            "results": results,
        }
        print(json.dumps(payload, indent=2))
    else:
        for r in results:
            print(f"t={r['t']:.3f} i={r['i']:02d} allowed={r['allowed']} tokens={r['tokens']:.3f}/{r['capacity']:.3f}")
    return 0


def main() -> None:
    args = build_parser().parse_args()
    if args.cmd == "check":
        raise SystemExit(cmd_check(args))
    if args.cmd == "simulate":
        raise SystemExit(cmd_simulate(args))
    raise SystemExit(2)
