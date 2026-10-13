# GauntletSim Architecture (Phase 1)

Phase 1 delivers research, machine-readable rules/assumptions, config, and a CLI status entrypoint. Gameplay modules below are **interfaces / planned seams only** — not implemented this milestone.

## Module map

| Module / path | Responsibility | Phase |
|---------------|----------------|-------|
| `docs/mechanics-reference.md` | Sourced mechanics with confidence tags | 1 |
| `docs/uncertainty-register.md` | Open unknowns ↔ assumption ids | 1 |
| `data/rules/corrupted_gauntlet.json` | Verified / strongly supported constants | 1 |
| `data/assumptions/defaults.json` | Labeled defaults + ranges | 1 |
| `gauntletsim/game_rules.py` | Load/validate JSON; typed accessors | 1 |
| `gauntletsim/config.py` | Account profile + sim parameters | 1 |
| `gauntletsim/main.py` | CLI: status + `--phase2` dungeon ASCII | 1–2 |
| `gauntletsim/room.py` | Coord, Room, kinds, node/mob enums | 2 |
| `gauntletsim/map_generator.py` | Seeded 7×7 layout (fish, demis, nodes) | 2 |
| `gauntletsim/pathfinding.py` | BFS on discovered rooms | 2 |
| `gauntletsim/player.py` | Position, light/move ticks | 2 |
| `gauntletsim/dungeon.py` | Mutable dungeon state | 2 |
| `gauntletsim/visualization.py` | ASCII map | 2 |
| `gauntletsim/simulation.py` | Phase 2 exploration stub | 2 |
| `gauntletsim/rng.py` | Named seeded RNG streams | 2 |
| `resources` (future) | Gather ticks, shard rolls, deplete nodes | 3 |
| `inventory` (future) | Slots, tools, HP/prayer/run | 3–4 |
| `crafting` (future) | Singing bowl, cook, potions | 3 |
| `combat` (future) | Tick combat vs mobs | 4 |
| `boss` (future) | Corrupted Hunllef subsystem | 4 |
| `strategy` (future) | Prep/boss policies A–D | 5 |
| `montecarlo` (future) | Batches, CRN, reports → `results/` | 6–7 |

```text
docs/mechanics ──► data/rules/*.json ──┐
docs/uncertainty ► data/assumptions/* ─┼► game_rules ──► main / tests
config (account + sim) ────────────────┘
```

## Tick / simulation data flow (planned)

1. **Config** loads account stats (required fields; Magic/Ranged default 85) and sim params (seed, prep ticks, logging).
2. **GameRules** merges verified rules + assumption defaults (assumptions never overwrite verified keys silently; they live in a separate namespace).
3. **DungeonGen(seed)** builds room graph and contents (Phase 2+).
4. **Sim loop** advances integer ticks `t = 0 .. prep_ticks` then boss phase until win/loss.
5. Each tick: strategy observes state → emits action → world applies deterministic transitions + RNG draws from seeded streams.
6. **EpisodeResult** records outcome, ticks, death cause, gear, and assumption fingerprint → `results/` later.

Phase 2 implements step 3 (dungeon gen) + exploration movement and ASCII viz. Crafting/combat remain later.

## Strategy interface (placeholder)

Strategies are pure decision policies over observable state. Names reserved for Phase 5:

```text
StrategyId = prep_rushed_t2 | prep_t2t3_hybrid | prep_safe_t3 | boss_two_style_swap | ...
```

Conceptual contract (not implemented):

```python
class Strategy(Protocol):
    def decide(self, state: SimState, rng: RandomStream) -> Action: ...
```

No LLM/RL agents in-tree.

## Common random numbers (Monte Carlo, later)

To compare strategies fairly:

- Split RNG into **named streams**: `dungeon_layout`, `gather`, `combat_hits`, `boss_specials`, `floor`, `tornado`.
- Derive each stream from `master_seed` + stream id (e.g. SHA256 or `random.Random((master_seed, stream_id))` pattern).
- When comparing strategy A vs B on scenario `i`, reuse the **same stream seeds** so layout and exogenous rolls match; only decision-dependent branches diverge.
- Log `master_seed`, stream salts, rules version, and assumption fingerprint with every batch.

Phase 1 only documents this; `SimConfig.master_seed` is the hook.

## Design constraints

- Stdlib-first; pytest for tests only.
- Accuracy over completeness: unknown → assumption id, never a silent magic number in rules JSON.
- Reject unknown JSON keys at load time to catch typos early.
