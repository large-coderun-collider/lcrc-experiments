from __future__ import annotations

import argparse
import json
from dataclasses import asdict

from .backoff import RetryPolicy


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="lcrc-backoff", description="Print retry delays (LCRC Fill 0001).")
    p.add_argument("--max-attempts", type=int, default=5)
    p.add_argument("--base", type=float, default=0.5)
    p.add_argument("--factor", type=float, default=2.0)
    p.add_argument("--cap", type=float, default=30.0)
    p.add_argument("--jitter", type=str, default="full", choices=["none", "full", "equal"])
    p.add_argument("--seed", type=int, default=None)
    p.add_argument("--json", action="store_true", help="Output JSON")
    return p


def main() -> None:
    args = build_parser().parse_args()
    try:
        policy = RetryPolicy(
            max_attempts=args.max_attempts,
            base=args.base,
            factor=args.factor,
            cap=args.cap,
            jitter=args.jitter,
            seed=args.seed,
        )
        delays = list(policy.delays())
    except ValueError as e:
        raise SystemExit(f"error: {e}") from e    

    policy = RetryPolicy(
        max_attempts=args.max_attempts,
        base=args.base,
        factor=args.factor,
        cap=args.cap,
        jitter=args.jitter,
        seed=args.seed,
    )
    delays = list(policy.delays())

    if args.json:
        payload = {"policy": asdict(policy), "delays": delays}
        print(json.dumps(payload, indent=2))
    else:
        for i, d in enumerate(delays):
            print(f"attempt={i} delay={d:.3f}s")

