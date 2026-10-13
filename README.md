# GauntletSim

Offline, stdlib-first Python simulator for the **Corrupted Gauntlet** (Old School RuneScape). No LLMs, RL, or GPU dependencies.

**Phase 3.5 (current):** Prep mechanics with OSRS-style tile pathing — walk/run ticks, room walls/doorways, gather/craft/fight tick buckets (`--phase3` / `--phase3.5`). Hunllef fight / agents later.

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

Expected: status summary (rule/assumption counts) and exit code 0.

Phase 2 dungeon + ASCII map:

```bash
python -m gauntletsim.main --phase2 --seed 1
python -m gauntletsim.main --phase2 --seed 1 --explore-fish
python -m gauntletsim.main --phase3 --seed 42
python -m gauntletsim.main --phase3.5 --seed 42
```

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
