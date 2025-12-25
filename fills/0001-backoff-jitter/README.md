# Fill 0001 — Backoff + Jitter

A compact, testable implementation of retry delays: capped exponential backoff with jitter.

## Accelerator
Retries are inevitable. Uncontrolled retries are how you DDoS yourself: a thundering herd of clients can retry in lockstep and amplify outages.  
This Fill models retry delays the way real systems do: exponential growth, a hard cap, and jitter.

## MAPS (Model / Architecture / Patterns / Structure)
- Input: attempt number (0-based: 0..N-1), base, factor, cap
- Output: delay in seconds (capped exponential, optionally jittered)
- Jitter modes:
  - `none` — deterministic delay
  - `full` — uniform `[0, delay]`
  - `equal` — `delay/2 + uniform [0, delay/2]`

## BOB (Building on Basics)
- Exponential backoff reduces retry pressure as failures persist
- A cap prevents “runaway” waiting times
- Jitter breaks synchronization and reduces herd effects
- Determinism via seed (reproducible delays)
- Retry runner uses injected `sleep()` for testability

## CMS (Code Modeling System)
Python module + tiny CLI:
- `lcrc_backoff.backoff`
- `lcrc_backoff.cli` (entrypoint: `lcrc-backoff`)

## LCRCb (Beauty detector)
- Unit tests (stdlib `unittest`)
- Seeded RNG for reproducibility
- Explicit validation / errors

## Run locally
From this directory (Python 3.12+; tested with 3.13 locally + in Docker):

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -U pip
python -m pip install -e .
python -m unittest -v

# human output
lcrc-backoff --max-attempts 6 --base 0.5 --cap 10 --seed 42

# JSON output (policy + delays)
lcrc-backoff --max-attempts 6 --base 0.5 --cap 10 --seed 42 --json
```

## Docker (optional)
By default, the container runs the test suite (`python -m unittest -v`).

```bash
docker build -t lcrc-fill-0001 .
docker run --rm lcrc-fill-0001
docker run --rm lcrc-fill-0001 lcrc-backoff --max-attempts 6 --base 0.5 --cap 10 --seed 42 --json
```