from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from typing import List, Optional

from .bulkhead import AdmissionResult, Bulkhead, BulkheadFullError


@dataclass
class StepOutcome:
    step: int
    action: str
    result: str
    active: int
    queued: int
    outcome: str


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="lcrc-bulkhead", description="LCRC Fill 0004: Bulkhead & Bounded Queue")
    sub = p.add_subparsers(dest="cmd", required=True)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--max-concurrent", type=int, default=2, help="max active slots")
    common.add_argument("--max-queue", type=int, default=2, help="max waiting queue slots")
    common.add_argument("--json", action="store_true", help="output JSON")

    sub.add_parser("check", parents=[common], help="single acquisition check")

    p_sim = sub.add_parser("simulate", parents=[common], help="simulate sequence of acquisitions and releases")
    p_sim.add_argument(
        "--seq",
        type=str,
        required=True,
        help="comma-separated actions: acquire,acquire,queue,release,acquire",
    )
    return p


def cmd_check(args: argparse.Namespace) -> int:
    bh = Bulkhead(max_concurrent=args.max_concurrent, max_queue=args.max_queue)
    res = bh.try_acquire()
    snap = bh.snapshot()

    if args.json:
        print(json.dumps({"result": res.value, "snapshot": asdict(snap)}, indent=2))
    else:
        print(f"result={res.value} active={snap.active_count}/{snap.max_concurrent} queue={snap.queue_count}/{snap.max_queue}")
    return 0


def cmd_simulate(args: argparse.Namespace) -> int:
    bh = Bulkhead(max_concurrent=args.max_concurrent, max_queue=args.max_queue)
    actions = [x.strip().lower() for x in args.seq.split(",") if x.strip()]
    history: List[StepOutcome] = []

    for i, act in enumerate(actions):
        if act == "acquire":
            res = bh.try_acquire()
            if res == AdmissionResult.QUEUED:
                # In simulation, manually push a dummy task to fill the queue
                bh._queue.append(lambda: None)
            outcome = res.value
        elif act == "release":
            next_task = bh.release()
            outcome = "released_with_next" if next_task else "released_empty"
        else:
            raise SystemExit(f"error: unknown action {act!r} (use 'acquire' or 'release')")

        snap = bh.snapshot()
        history.append(
            StepOutcome(
                step=i,
                action=act,
                result=outcome,
                active=snap.active_count,
                queued=snap.queue_count,
                outcome=outcome,
            )
        )

    if args.json:
        print(json.dumps({"params": {"max_concurrent": args.max_concurrent, "max_queue": args.max_queue}, "history": [asdict(h) for h in history]}, indent=2))
    else:
        for h in history:
            print(f"step={h.step:02d} action={h.action:>7} -> {h.result:>18} | active={h.active}/{args.max_concurrent} queue={h.queued}/{args.max_queue}")
    return 0


def main() -> None:
    args = build_parser().parse_args()
    if args.cmd == "check":
        raise SystemExit(cmd_check(args))
    if args.cmd == "simulate":
        raise SystemExit(cmd_simulate(args))
    raise SystemExit(2)

if __name__ == "__main__":
    main()