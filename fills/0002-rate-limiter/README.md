# Fill 0002 — Rate Limiter (Token Bucket)

A compact, testable implementation of a rate limiter based on the token bucket model, with a small CLI for inspection and simulation.

## Accelerator
Rate limiting is a control mechanism that bounds request throughput and burstiness in order to protect downstream systems, stabilize latency, and reduce cascading failure amplification.  
This Fill models a token bucket limiter with deterministic, test-friendly time control and a CLI that exposes behavior in both human-readable and JSON formats.

## MAPS (Model / Architecture / Patterns / Structure)
- Model: **Token Bucket**
  - State: current token count, last timestamp
  - Parameters:
    - `rate` (tokens/sec): refill rate
    - `capacity` (tokens): maximum burst size
    - `cost` (tokens): per-request cost (default: 1)
    - `start_full`: whether the bucket starts at full capacity
- Operations:
  - `allow(cost=1) -> bool`: consume tokens if available
  - `wait_time(cost=1) -> float`: minimum time until a request can be allowed
- Time handling:
  - Monotonic time is injected via a `clock` callable for determinism in tests
  - Backward time deltas are clamped to 0

## BOB (Building on Basics)
- Token bucket enables controlled bursts while enforcing an average rate limit
- A capacity bound prevents unbounded burst accumulation
- A cost parameter supports heterogeneous request weights
- Determinism is achieved by injecting a clock and avoiding global time dependencies
- Input validation prevents invalid configuration (non-positive rate/capacity, negative cost, etc.)

## CMS (Code Modeling System)
Python module + CLI:
- `lcrc_ratelimit.limiter` (token bucket implementation)
- `lcrc_ratelimit.cli` (entrypoint: `lcrc-ratelimit`)

CLI commands:
- `check`: single admission decision + remaining tokens
- `simulate`: repeated checks over a synthetic timeline (optionally JSON)

## LCRCb (Beauty detector)
- Unit tests (stdlib `unittest`)
- Deterministic clock-driven tests (no sleeps)
- Explicit validation and defined edge-case handling (clock going backwards, capacity capping)

## Run locally
From this directory (Python 3.12+; tested with 3.12 and in Docker):

```bash
python3.12 -m venv .venv
. .venv/bin/activate
python -m pip install -U pip
python -m pip install -e .
python -m unittest -v

# one-shot check
lcrc-ratelimit check --rate 5 --capacity 10 --cost 1

# simulation (human output)
lcrc-ratelimit simulate --rate 2 --capacity 5 --n 12 --interval 0.25

# simulation (JSON output)
lcrc-ratelimit simulate --rate 2 --capacity 5 --n 12 --interval 0.25 --json
```

## Docker (optional)
The container runs the unit test suite by default.
```bash
docker build -t lcrc-fill-0002 .
docker run --rm lcrc-fill-0002

# run CLI inside the container
docker run --rm lcrc-fill-0002 lcrc-ratelimit simulate --rate 2 --capacity 5 --n 12 --interval 0.25 --json
```