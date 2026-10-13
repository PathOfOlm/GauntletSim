# Uncertainty Register — Corrupted Gauntlet (Phase 1)

Every unverified probability, quantity, delay, or generation rule that the simulator may need. **No invented exact values are treated as facts.** Defaults in `data/assumptions/defaults.json` are labeled assumptions only.

Sensitivity measurement (later phases): fix a strategy and seed set; vary one parameter across its plausible range; report win rate, median clear time, and death cause mix deltas.

| Assumption id | What is unknown | Configurable parameter | Plausible range | Sensitivity method |
|---------------|-----------------|------------------------|-----------------|-------------------|
| `A-EXPLORE-01` | Tick cost / animation to light a new room with the sceptre; whether lighting is instant on click. | `exploration.room_light_ticks` | 1–3 ticks | Vary light cost; measure prep completion rate and median prep leftover ticks. |
| `A-EXPLORE-02` | Exact room graph connectivity (which edges exist between adjacent cells; blocked doors). | `dungeon.edge_passable_probability` | 0.7–1.0 per orthogonal adjacency (or explicit graph model later) | Monte Carlo layouts; measure path length to demi-bosses and hub return time. |
| `A-GEN-NODES-01` | Probability distribution of node counts/types per resource room in Corrupted (only 0–5 and mixability verified). | `dungeon.node_count_weights` | Weights over {0,1,2,3,4,5}; type multinomial | Sweep weights; measure shard/material stock at T=750 and craft feasibility. |
| `A-GEN-FISH-01` | Which room is the guaranteed 3-fishing-spot room (inner ring vs any); placement algorithm. | `dungeon.guaranteed_fish_room_policy` | `inner_ring_uniform` \| `any_resource_uniform` | Compare policies; measure fishing route length and food readiness. |
| `A-DEMI-SPAWN-01` | Exact number/distribution of demi-bosses beyond cardinal guarantees; Corrupted-specific differences from ordinary. | `dungeon.demi_boss_extra_count` | 0–4 extras beyond 4 cardinals | Vary extras; measure T3 weapon completion rate before boss enter. |
| `A-DEMI-SPAWN-02` | Probability a cardinal room’s demi-boss is bear vs dragon vs dark beast. | `dungeon.demi_boss_type_weights` | Equal weights or [0.2–0.5] each (sum 1) | Vary imbalance; measure dual-style perfected weapon availability. |
| `A-MOB-STATS-01` | Exact Corrupted monster combat stats / HP / max hits (wiki: “increased stats”). | `combat.corrupted_mob_stat_scale` | 1.0–1.5× crystalline baselines | Scale mob toughness; measure prep DPS time and food used before boss. |
| `A-MOB-SPAWN-01` | Probability a resource room contains weak/strong/none monsters and counts. | `dungeon.mob_spawn_weights` | Categorical weights; 0–3 mobs/room | Sweep; measure frame acquisition time and shard income. |
| `A-GATHER-TICKS-01` | Ticks between successful gather rolls for ore/bark/linum/grym/fish inside Gauntlet. | `resources.gather_interval_ticks` | 2–6 ticks | Vary; measure materials collected in fixed prep window. |
| `A-GATHER-SUCCESS-01` | Success probability per gather roll (if not guaranteed). | `resources.gather_success_probability` | 0.5–1.0 | Vary; same metrics as gather ticks. |
| `A-FISH-ONETICK-01` | Conditions for 1-tick fish after vial fill (strategy page); reliability. | `resources.post_vial_fish_ticks` | 1–6 ticks | Toggle; measure fishing efficiency in prep routes. |
| `A-SHARD-QTY-CORRUPT-01` | Whether Corrupted monster shard quantities exactly match crystalline wiki table. | `resources.monster_shard_qty_override` | Use table as-is or ±10% on endpoints | Shift ranges; measure shard surplus/deficit at craft targets. |
| `A-PRAYER-DISABLE-01` | Chance that a magic-style Hunllef attack is the prayer-disabling variant. | `boss.prayer_disable_chance` | 0.05–0.35 per magic attack | Sweep; measure off-prayer damage taken and death rate. |
| `A-FLOOR-DMG-01` | Orange floor damage per tick (wiki “10–20 [confirmation needed]”; strategies also cite 10–25). | `boss.floor_damage_min` / `boss.floor_damage_max` | min 8–12; max 18–25 | Sweep; measure HP loss attributable to floors. |
| `A-FLOOR-PATTERN-01` | Exact tile pattern sets and crimson→orange delay ticks per phase. | `boss.floor_warn_ticks` / `boss.floor_pattern_ids` | warn 1–5 ticks; pattern ids opaque enum | Vary warn ticks; measure dodge failure rate. |
| `A-TORNADO-DMG-01` | Conflicting wiki tornado damage tables (Tornado page vs Hunllef page T1/T3). | `boss.tornado_damage_table` | Choose `tornado_page` \| `hunllef_page` or interpolate | Compare tables; measure tornado-death share. |
| `A-TORNADO-MOVE-01` | Tornado movement speed, pathing, and spawn positions. | `boss.tornado_move_tiles_per_tick` | 1–2 tiles/tick | Vary; measure tornado contact ticks. |
| `A-STOMP-TRIGGER-01` | Exact timing of “underneath when it tries to attack” relative to attack cooldown. | `boss.stomp_under_boss_policy` | `on_attack_tick` \| `any_overlap_tick` | Toggle; measure stomp frequency under pathing strategies. |
| `A-COMBAT-ACCURACY-01` | Full accuracy/max-hit formulas for corrupted weapons vs Hunllef and vs prep mobs. | `combat.use_standard_osrs_formula` + gear bonuses from wiki | Bonuses verified; hit rolls assumed standard OSRS | A/B formula flags; measure kill times. |
| `A-WEAPON-SPEED-01` | Attack speeds (ticks) for basic/attuned/perfected corrupted weapons. | `combat.weapon_attack_speed_ticks` | 4–5 typical; staff may differ | Vary; measure boss DPS. |
| `A-INV-START-SLOTS-01` | Exact free inventory slots after starting tools (28 − starting items). | `inventory.starting_occupied_slots` | 5–8 | Affects early pickup; measure drop/leave rates. |
| `A-COOK-BURN-01` | Whether paddlefish can burn and Cooking level interaction in Gauntlet. | `crafting.paddlefish_burn_probability` | 0.0–0.2 (0 if no-burn confirmed) | Vary; measure food yield. |
| `A-HUB-CRAFT-TICKS-01` | Singing-bowl craft duration per item beyond known 1-tick potion/cook cases. | `crafting.sing_ticks_per_item` | 1–3 ticks | Vary; measure end-of-prep craft backlog. |
| `A-RUN-ENERGY-01` | Exact run drain rates inside Gauntlet and stamina effect magnitude of egniol. | `player.run_drain_per_tile` / `player.egniol_stamina_duration_ticks` | drain community ranges; stamina 100–200 ticks | Vary; measure idle wait vs walk time. |
| `A-PRAYER-DRAIN-01` | Prayer drain rates for Protect + Rigour/Augury/Piety during boss. | `player.prayer_drain_per_tick` | Style-dependent 0.1–0.4 points/tick effective | Vary; measure egniol demand and prayer-drop deaths. |

## Resolved enough for rules JSON (not listed as open unknowns)

Prep seconds, tick length, Hunllef HP/stats/cycles, tornado counts/duration, crafting material/shard costs (post-22 Jul 2026), node yields, Corrupted inner-ring exception, egniol recipe, prayed/unprayed max-hit tables for listed armour sets — see `docs/mechanics-reference.md` and `data/rules/corrupted_gauntlet.json`.
