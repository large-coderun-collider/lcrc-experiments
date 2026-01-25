# Fill 0003 — Circuit Breaker

A compact, testable implementation of a circuit breaker (finite-state machine) with a small CLI for inspection and simulation.

## Accelerator
A circuit breaker is a control mechanism that prevents repeated calls to a failing dependency from amplifying incidents.
It provides fail-fast behavior during outages and controlled probing during recovery, reducing resource waste and stabilizing latency.

This Fill models a three-state breaker (CLOSED / OPEN / HALF_OPEN) with deterministic, test-friendly time control and a CLI that exposes behavior in both human-readable and JSON formats.

## MAPS (Model / Architecture / Patterns / Structure)
- Model: **Circuit Breaker (FSM)**
  - States:
    - `CLOSED`: calls pass; failures are counted
    - `OPEN`: calls are rejected until a cooldown expires
    - `HALF_OPEN`: limited probing; successes close the circuit, failures reopen it
  - State variables:
    - consecutive failure counter (CLOSED)
    - consecutive success counter (HALF_OPEN)
    - open-until timestamp (OPEN)
- Parameters:
  - `failure_threshold`: failures to transition `CLOSED -> OPEN`
  - `success_threshold`: successes to transition `HALF_OPEN -> CLOSED`
  - `cooldown`: seconds to keep `OPEN` before probing
  - `clock`: injected time source for deterministic tests
- Operations:
  - `call(fn) -> result`: execute a protected call, applying state transitions
  - `allow() -> bool`: admission decision without calling a function
  - `state() -> str`: current state name

## BOB (Building on Basics)
- Fail-fast behavior reduces wasted work when a dependency is known-bad.
- Cooldown bounds the probing frequency during outages.
- Half-open probing supports recovery detection without sudden full traffic restoration.
- Determinism is achieved by injecting a clock and avoiding global time dependencies.
- Backward time deltas are clamped to preserve monotonic behavior.

## CMS (Code Modeling System)
Python module + CLI:
- `lcrc_breaker.breaker` (circuit breaker implementation)
- `lcrc_breaker.cli` (entrypoint: `lcrc-breaker`)

CLI commands:
- `call`: run a function-like scenario (success/fail) through the breaker
- `simulate`: run a scripted sequence against a deterministic clock (optionally JSON)

## LCRCb (Beauty detector)
- Unit tests (stdlib `unittest`)
- Deterministic clock-driven tests (no sleeps)
- Explicit validation and defined edge-case handling (clock going backwards)
- State transition invariants (thresholds, cooldown, probing semantics)

## Run locally
From this directory (Python 3.12+):

```bash
python3.12 -m venv .venv
. .venv/bin/activate
python -m pip install -U pip
python -m pip install -e .
python -m unittest -v

# simulate a sequence: ok ok fail fail fail ... with dt steps
lcrc-breaker simulate --cooldown 2 --failure-threshold 3 --success-threshold 2 \
  --dt 0.1 --seq ok,ok,fail,fail,fail,call,call,wait:2.0,ok,ok

# JSON output
lcrc-breaker simulate --cooldown 2 --failure-threshold 3 --success-threshold 2 \
  --dt 0.1 --seq ok,fail,fail,fail,call,wait:2.0,ok,ok --json

# Docker (optional)
The container runs the unit test suite by default.

docker build -t lcrc-fill-0003 .
docker run --rm lcrc-fill-0003

# run CLI inside the container
docker run --rm lcrc-fill-0003 lcrc-breaker simulate --cooldown 2 --failure-threshold 3 --success-threshold 2 \
  --dt 0.1 --seq ok,fail,fail,fail,call,wait:2.0,ok,ok --json

