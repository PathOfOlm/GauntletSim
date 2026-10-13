# GauntletSim

Offline, stdlib-first Python simulator for the **Corrupted Gauntlet** (Old School RuneScape). No LLMs, RL, or GPU dependencies.

**Phase 1 (current):** mechanics research, uncertainty register, machine-readable rules/assumptions, config skeleton, and a CLI status entrypoint. Dungeon/player/combat/boss gameplay arrive in later phases.

## Requirements

- Python **3.11+** (developed against 3.12)
- Standard library for running the app
- `pytest` only for tests

## Setup (Windows / PyCharm)

1. Clone this repo and open the project folder in PyCharm.
2. Create a venv (PyCharm: *File → Settings → Project → Python Interpreter → Add Interpreter → Virtualenv*).
3. In the PyCharm terminal (or Command Prompt):

```bat
python -m pip install -e ".[dev]"
```

Or, stdlib-only run without install (from the repo root, with the project root on `PYTHONPATH`):

```bat
set PYTHONPATH=%CD%
python -m gauntletsim.main
```

PowerShell:

```powershell
$env:PYTHONPATH = (Get-Location).Path
python -m gauntletsim.main
```

## Run

```bash
python -m gauntletsim.main
```

Expected: a Phase 1 status summary (rule counts, assumption counts, unresolved unknowns) and exit code 0.

## Tests

```bash
python -m pytest
```

## Layout

| Path | Purpose |
|------|---------|
| `docs/mechanics-reference.md` | Sourced Corrupted Gauntlet mechanics |
| `docs/uncertainty-register.md` | Unverified quantities → assumption ids |
| `docs/architecture.md` | Module map and future sim/CRN design |
| `data/rules/corrupted_gauntlet.json` | Verified / strongly supported constants |
| `data/assumptions/defaults.json` | Labeled assumption defaults + ranges |
| `gauntletsim/` | Package (`game_rules`, `config`, `main`) |
| `tests/` | Phase 1 pytest suite |
| `results/` | Reserved for later batch outputs |

## Accuracy policy

Prefer `unknown` + a configurable assumption over inventing wiki-incomplete numbers. Rules JSON rejects unknown keys and forbids `inferred`/`unknown` confidence on stored constants.
