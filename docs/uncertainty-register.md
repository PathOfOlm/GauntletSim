# Uncertainty Register — Corrupted Gauntlet

Every remaining unverified probability, quantity, delay, or generation rule. **No invented exact values are treated as facts.** Defaults in `data/assumptions/defaults.json` are labeled assumptions only.

**Research pass:** Phase 1 unknowns research (see Project store `docs/unknowns-research.md`). Status: `still_unknown` | `constrained` | `resolved` (removed from open list).

Sensitivity measurement (later phases): fix a strategy and seed set; vary one parameter across its plausible range; report win rate, median clear time, and death cause mix deltas.

## Open assumptions

| Assumption id | Status | What is unknown | Configurable parameter | Plausible range | Sensitivity method |
|---------------|--------|-----------------|------------------------|-----------------|-------------------|
| `A-EXPLORE-01` | still_unknown | Tick cost to light a room node with the sceptre | `exploration.room_light_ticks` | 1–3 ticks | Vary light cost; measure prep leftover ticks |
| `A-GEN-NODES-01` | still_unknown | Node count/type distribution per Corrupted resource room | `dungeon.node_count_weights` | Weights over {0..5} | Sweep; measure craft feasibility at T=750 |
| `A-DEMI-SPAWN-01` | constrained | Extra demi-boss count beyond 4 cardinals (extras edge/corner only; alone) | `dungeon.demi_boss_extra_count` | 0–4 | Vary; measure T3 weapon completion |
| `A-DEMI-SPAWN-02` | still_unknown | Bear vs dragon vs dark beast type weights | `dungeon.demi_boss_type_weights` | ~equal; each 0.25–0.4 | Vary imbalance; dual-style availability |
| `A-MOB-SPAWN-01` | constrained | P(empty/weak/strong) per room (weak ≤3; strong pairs; demi alone/edges) | `dungeon.mob_spawn_weights` | Categorical weights | Sweep; frame/shard income |
| `A-MOB-STATS-SCORPION-WOLF` | constrained | Exact Corrupted Scorpion/Wolf stats (other mobs now in rules) | `combat.scorpion_wolf_stats_pending` | Placeholder vs fetch-before-Phase-4 | N/A until ingested |
| `A-GATHER-TICKS-01` | constrained | Gather interval ticks (fish Always success; crystal-tool rates suggest ~2–5) | `resources.gather_interval_ticks` | 2–5 (default 3) | Vary; materials in prep window |
| `A-GATHER-SUCCESS-01` | constrained | Non-fish gather success (fish Always verified) | `resources.gather_success_probability` | 0.9–1.0 | Vary with gather ticks |
| `A-PRAYER-DISABLE-01` | still_unknown | Prayer-disable chance on magic-style attacks | `boss.prayer_disable_chance` | 0.05–0.35 | Sweep; off-prayer deaths |
| `A-FLOOR-DMG-01` / `01b` | constrained | Floor max may be 20 (wiki unconfirmed) or up to 25 (strategies/talk) | `boss.floor_damage_min/max` | min 10; max 20–25 | Sweep; floor HP loss |
| `A-FLOOR-PATTERN-01` | still_unknown | Exact patterns + crimson→orange delay (last-phase some tiles never orange) | `boss.floor_warn_ticks` | 1–4 | Vary warn ticks; dodge failures |
| `A-TORNADO-DMG-01` | constrained | Residual T1/T3 table conflict; **canonical = Tornado page** | `boss.tornado_damage_hunllef_page_delta` | ignore vs sensitivity swap | Compare death share |
| `A-TORNADO-MOVE-01` | still_unknown | Tornado speed, pathing, spawn positions | `boss.tornado_move_tiles_per_tick` | 1–2 | Vary; contact ticks |
| `A-COOK-BURN-01` | still_unknown | Burn rate **below** Cooking 47 (stop-burn at 47 verified) | `crafting.paddlefish_burn_probability_below_47` | 0.0–0.2 | Vary; food yield for low Cooking |

## Resolved in this research pass (promoted to rules / removed as open)

| Former id | Resolution |
|-----------|------------|
| `A-EXPLORE-02` | **strongly_supported:** orthogonal edges passable once lit (`topology.orthogonal_edges_passable_once_lit`) |
| `A-GEN-FISH-01` | **strongly_supported:** guaranteed 3-fish room is adjacent to Hunllef (`topology.guaranteed_fish_room_adjacent_to_boss`) |
| `A-SHARD-QTY-CORRUPT-01` | **verified:** Corrupted shards page matches prior ranges |
| `A-FISH-ONETICK-01` | **strongly_supported:** 1 tick after vial-fill click (`timing.post_vial_fish_ticks`) |
| `A-WEAPON-SPEED-01` | **verified:** bow rapid 4 / accurate 5; staff 4; halberd 4 (`combat.weapon_attack_speed_ticks`) |
| `A-HUB-CRAFT-TICKS-01` | **verified:** singing bowl crafts 1 tick |
| `A-INV-START-SLOTS-01` | **verified:** sceptre wielded; 5 inventory starters |
| `A-STOMP-TRIGGER-01` | **strongly_supported:** stomp when Hunllef tries to attack while player underneath |
| `A-COMBAT-ACCURACY-01` | **strongly_supported:** standard OSRS formulas; perfected staff max hit 39/40 exception verified |
| `A-MOB-STATS-01` | **verified** for rat/spider/bat/unicorn/bear/dragon/dark beast (exact stats in rules); scorpion/wolf pending |
| `A-RUN-ENERGY-01` / `01b` | **strongly_supported:** standard Energy formula; egniol acts as stamina → 200 ticks, ×0.3 drain |
| `A-PRAYER-DRAIN-01` | **verified:** Protect 12 / Rigour·Augury·Piety 24 drain effects (standard Prayer wiki) |
| Burn stop level | **verified:** paddlefish stop burning at Cooking 47 |

## Already resolved in Phase 1 scaffold

Prep seconds, tick length, Hunllef HP/stats/cycles, tornado counts/duration, crafting costs (post-22 Jul 2026), node yields, Corrupted inner-ring exception, egniol recipe, prayed/unprayed max-hit tables — see `docs/mechanics-reference.md`.
