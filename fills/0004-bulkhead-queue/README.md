# Fill 0004 — Bulkhead & Bounded Queue

A compact, testable implementation of the Bulkhead concurrency pattern (bounded execution slots + waiting queue) with a small CLI for inspection and simulation.

## Accelerator
When a system experiences a massive traffic spike or slow downstream processing, unbounded concurrency will quickly deplete system memory, thread pools, and file descriptors.
A Bulkhead isolates resources and enforces strict concurrency limits. By bounding both active execution slots and the waiting queue, the system gracefully sheds excess load (fail-fast rejection) instead of crashing from resource starvation.

This Fill models a bounded concurrency gate with queueing semantics and deterministic simulation via CLI in both human-readable and JSON formats.

## MAPS (Model / Architecture / Patterns / Structure)
- Model: **Bulkhead / Bounded Queue**
  - Concurrency Gate:
    - `ACCEPTED`: slot acquired immediately; task executes
    - `QUEUED`: all active slots full; task waits in bounded queue
    - `REJECTED`: both active slots and queue are saturated (Load Shedding)
  - State variables:
    - `active_count`: number of tasks currently executing
    - `queue_count`: number of tasks waiting in line
- Parameters:
    - `max_concurrent`: maximum allowed simultaneous executions
    - `max_queue`: maximum allowed waiting tasks before rejection
- Operations:
    - `try_acquire() -> AdmissionResult`: non-blocking check for slot availability
    - `release() -> Optional[Callable]`: frees an active slot and promotes next queued task if available
    - `submit(fn) -> AdmissionResult`: executes or queues a task, raising an error if saturated

## BOB (Building on Basics)
- Resource isolation prevents localized slowness from cascading into total host failure.
- Bounded queues prevent Out-Of-Memory (OOM) crashes under sustained load spikes.
- Load Shedding (rejecting excess traffic instantly) maintains predictable latency for accepted tasks.
- Explicit slot release guarantees zero resource leaks in concurrent workflows.

## CMS (Code Modeling System)
Python module + CLI:
- `lcrc_bulkhead.bulkhead` (bulkhead and queue implementation)
- `lcrc_bulkhead.cli` (entrypoint: `lcrc-bulkhead`)

CLI commands:
- `check`: evaluate a single acquisition attempt against limits
- `simulate`: run a scripted sequence of acquisitions and releases (optionally JSON)

## LCRCb (Beauty detector)
- Unit tests (stdlib `unittest`)
- Zero external dependencies (pure Python standard library)
- Automatic queue promotion upon slot release
- Clear separation between non-blocking admission checking and task execution

## Run locally
From this directory (Python 3.12+):

```bash
python3.12 -m venv .venv
. .venv/bin/activate
python -m pip install -U pip
python -m pip install -e .
python -m unittest -v

# simulate a sequence: 2 active slots, 1 queue slot
lcrc-bulkhead simulate --max-concurrent 2 --max-queue 1 \
  --seq acquire,acquire,acquire,acquire,release,release

# JSON output
lcrc-bulkhead simulate --max-concurrent 2 --max-queue 1 \
  --seq acquire,acquire,acquire,acquire,release,release --json

# Docker (optional)
The container runs the unit test suite by default.

docker build -t lcrc-fill-0004 .
docker run --rm lcrc-fill-0004

# run CLI inside the container
docker run --rm lcrc-fill-0004 lcrc-bulkhead simulate --max-concurrent 2 --max-queue 1 \
  --seq acquire,acquire,acquire,acquire,release,release --json