# Uncertainty Register — Corrupted Gauntlet

Open assumptions after user answers + wiki recheck. Defaults in `data/assumptions/defaults.json` are labeled, not facts.

## User-confirmed / wiki-promoted (removed from open list)

| Topic | Outcome |
|-------|---------|
| Room light ticks | **1 tick** (user) → `timing.room_light_ticks` |
| Nodes per room | **0–5, mixable** (user + wiki verified bounds); distribution weights still open |
| Demi-boss types | **Equal / random** (user + Jagex “random”) → `enemies.demi_boss_type_uniform` |
| Demi-boss count | **4 guaranteed** at N/E/S/W (Jagex Summer Sweep-Up); extras “dotted around” edges/corners — count still open |
| Scorpion / Wolf stats | **Verified** on wiki → rules `enemies.combat_stats` |
| Ore gather | **Always** succeeds (Corrupt Deposit) |
| Fish gather | **Always** (already verified) |

## Open assumptions

| Id | Status | Unknown | Parameter | Range / default |
|----|--------|---------|-----------|-----------------|
| `A-GEN-NODES-01` | still_unknown | Node count **weights** (not the 0–5 bound) | `dungeon.node_count_weights` | weights over 0..5 |
| `A-DEMI-SPAWN-01` | constrained | Extra demi-bosses beyond 4 | `dungeon.demi_boss_extra_count` | 0–4 (default 2) |
| `A-MOB-SPAWN-01` | still_unknown | P(empty/weak/strong) per room | `dungeon.mob_spawn_weights` | categorical |
| `A-GATHER-TICKS-01` | still_unknown | Gather interval ticks | `resources.gather_interval_ticks` | 2–5 (default 3) |
| `A-GATHER-SUCCESS-01` | constrained | Bark/linum/grym success (ore+fish Always) | `resources.gather_success_probability_non_ore_fish` | 0.9–1.0 |
| `A-PRAYER-DISABLE-01` | still_unknown | Prayer-disable chance | `boss.prayer_disable_chance` | 0.05–0.35 (default 0.15) |
| `A-FLOOR-DMG-01/b` | constrained | Floor max 20 (wiki unconfirmed) vs 25 (Strategies) | `boss.floor_damage_*` | min 10; max 20–25 (default max 25) |
| `A-FLOOR-PATTERN-01` | still_unknown | Warn→orange ticks / patterns | `boss.floor_warn_ticks` | 1–4 |
| `A-TORNADO-DMG-01` | constrained | Hunllef vs Tornado page T1/T3 deltas | `boss.tornado_damage_hunllef_page_delta` | ignore vs swap |
| `A-TORNADO-MOVE-01` | still_unknown | Tornado pathing/speed/spawns | `boss.tornado_move_tiles_per_tick` | 1–2 |
| `A-COOK-BURN-01` | still_unknown | Burn rate below Cooking 47 | `crafting.paddlefish_burn_probability_below_47` | 0–0.2 |

## Wiki check notes (items user asked to verify)

3. **Extra demi-bosses:** Jagex news: “four demi-bosses with fixed locations” + “additional demi-bosses dotted around”; wiki: can spawn any edge/corner. **Extra count not stated.**
5. **Room mob odds:** wiki gives spawn *structure* (weak ≤3, strong pairs, demi alone/edges), not probabilities.
6. **Gather ticks:** not stated for Gauntlet; ore/fish drops listed as Always.
7. **Prayer disable:** wiki only says “a chance” on magic attacks — **no rate**.
8. **Floor damage:** Hunllef page 10–20 `[confirmation needed]`; Strategies **10–25**; talk-page claim of 25 unresolved on main page.
