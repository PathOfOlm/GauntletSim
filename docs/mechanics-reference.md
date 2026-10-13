# Corrupted Gauntlet — Mechanics Reference (Phase 1)

**Scope:** Corrupted Gauntlet only. Ordinary Gauntlet facts are cited only when the wiki states they are shared or when Corrupted-specific pages are silent and a shared rule is strongly supported.

**Confidence levels:** `verified` | `strongly_supported` | `inferred` | `unknown`

**Sources (ids used in JSON):**

| Source id | URL |
|-----------|-----|
| `wiki-gauntlet` | https://oldschool.runescape.wiki/w/The_Gauntlet |
| `wiki-corrupted-hunllef` | https://oldschool.runescape.wiki/w/Corrupted_Hunllef |
| `wiki-tornado-cg` | https://oldschool.runescape.wiki/w/Tornado_(Corrupted_Gauntlet) |
| `wiki-egniol` | https://oldschool.runescape.wiki/w/Egniol_potion |
| `wiki-shards` | https://oldschool.runescape.wiki/w/Crystal_shards_(The_Gauntlet) |
| `wiki-game-tick` | https://oldschool.runescape.wiki/w/Game_tick |
| `wiki-strategies` | https://oldschool.runescape.wiki/w/The_Gauntlet/Strategies |
| `wiki-corrupted-shards` | https://oldschool.runescape.wiki/w/Corrupted_shards |
| `wiki-paddlefish` | https://oldschool.runescape.wiki/w/Paddlefish |
| `wiki-energy` | https://oldschool.runescape.wiki/w/Energy |
| `wiki-stamina` | https://oldschool.runescape.wiki/w/Stamina_potion |
| `wiki-prayer` | https://oldschool.runescape.wiki/w/Prayer |
| `wiki-crystal-sceptre` | https://oldschool.runescape.wiki/w/Crystal_sceptre |

---

## 1. Dungeon topology

### R-TOPO-01 — 7×7 room grid

| Field | Value |
|-------|-------|
| Statement | The Gauntlet map is a 7×7 grid of rooms. The Corrupted Gauntlet uses the same topology with Corrupted content. |
| Source | https://oldschool.runescape.wiki/w/The_Gauntlet |
| Confidence | `verified` (grid stated for Gauntlet); `strongly_supported` for Corrupted sharing the grid |
| Intended module | `dungeon` |
| Test id | `test_rules_topology_grid` |

### R-TOPO-02 — Start adjacent to boss room

| Field | Value |
|-------|-------|
| Statement | The player starts adjacent to the centre room that contains the boss. The boss room always lies directly adjacent to the starting room. |
| Source | https://oldschool.runescape.wiki/w/The_Gauntlet |
| Confidence | `verified` |
| Intended module | `dungeon` |
| Test id | `test_rules_start_adjacent_boss` |

### R-TOPO-03 — Resource rooms vs special rooms

| Field | Value |
|-------|-------|
| Statement | Each room except the starting room and boss room contains resource nodes and/or monsters. |
| Source | https://oldschool.runescape.wiki/w/The_Gauntlet |
| Confidence | `verified` |
| Intended module | `dungeon` |
| Test id | `test_rules_resource_rooms` |

### R-TOPO-04 — Room lighting / exploration

| Field | Value |
|-------|-------|
| Statement | The crystal/corrupted sceptre is required to light nodes (visit new rooms). Exact adjacency graph, door count, and lighting tick cost are not fully specified for simulation. |
| Source | https://oldschool.runescape.wiki/w/The_Gauntlet |
| Confidence | `strongly_supported` (sceptre required); door/lighting timing `unknown` → see uncertainty register `A-EXPLORE-01` |
| Intended module | `dungeon` / `player` |
| Test id | `test_rules_sceptre_required` |

---

## 2. Exploration & prep timing

### R-PREP-01 — Corrupted prep timer

| Field | Value |
|-------|-------|
| Statement | Corrupted Gauntlet preparation time is 7 minutes 30 seconds (vs 10 minutes for ordinary Gauntlet). When the timer expires the player is teleported into the boss room. The player may enter early manually. |
| Source | https://oldschool.runescape.wiki/w/The_Gauntlet |
| Confidence | `verified` |
| Intended module | `sim` / `player` |
| Test id | `test_rules_prep_seconds` |

### R-PREP-02 — Game tick length

| Field | Value |
|-------|-------|
| Statement | One OSRS game tick equals 0.6 seconds. Simulator time should be tick-indexed. |
| Source | https://oldschool.runescape.wiki/w/Game_tick |
| Confidence | `verified` |
| Intended module | `sim` |
| Test id | `test_rules_tick_seconds` |

### R-PREP-03 — Prep duration in ticks

| Field | Value |
|-------|-------|
| Statement | 7:30 = 450 seconds ⇒ 750 ticks at 0.6 s/tick. |
| Source | Derived from R-PREP-01 + R-PREP-02 |
| Confidence | `verified` (arithmetic from verified inputs) |
| Intended module | `sim` |
| Test id | `test_rules_prep_ticks` |

---

## 3. Resources

### R-RES-01 — Node types and yields

| Field | Value |
|-------|-------|
| Statement | Resource nodes (Corrupted variants use Corrupted item names; yields match wiki Gauntlet table): Crystal/Corrupted Deposit → 3 ore; Linum Tirinum → 3 linum; Phren Roots → 3 bark; Grym Root → 1 grym leaf; Fishing Spot → 4 raw paddlefish. Nodes require no skill level. |
| Source | https://oldschool.runescape.wiki/w/The_Gauntlet |
| Confidence | `verified` for yields/types; Corrupted item renaming `strongly_supported` |
| Intended module | `resources` |
| Test id | `test_rules_node_yields` |

### R-RES-02 — Nodes per room

| Field | Value |
|-------|-------|
| Statement | Each resource room contains zero to five resource nodes; rooms may mix node types. |
| Source | https://oldschool.runescape.wiki/w/The_Gauntlet |
| Confidence | `verified` |
| Intended module | `dungeon` / `resources` |
| Test id | `test_rules_nodes_per_room` |

### R-RES-03 — Corrupted inner-ring generation

| Field | Value |
|-------|-------|
| Statement | Ordinary Gauntlet guarantees inner 3×3 resource mitigation (4 rooms with ≥3 deposits/linum/phren/weak monsters). **This does not apply to Corrupted Gauntlet**, except one room is guaranteed to contain 3 fishing spots. |
| Source | https://oldschool.runescape.wiki/w/The_Gauntlet |
| Confidence | `verified` |
| Intended module | `dungeon` |
| Test id | `test_rules_corrupted_inner_ring` |

### R-RES-04 — Gathering shard chance

| Field | Value |
|-------|-------|
| Statement | Gathering from deposit/linum/phren/grym/fishing may reward shards: quantity 10–30 at rarity 1/3 (wiki table for Gauntlet; Corrupted uses corrupted shards). |
| Source | https://oldschool.runescape.wiki/w/Crystal_shards_(The_Gauntlet) |
| Confidence | `strongly_supported` for Corrupted (same table; Corrupted shards noted on page) |
| Intended module | `resources` |
| Test id | `test_rules_gather_shard_chance` |

### R-RES-05 — Cooked paddlefish heal

| Field | Value |
|-------|-------|
| Statement | Cooked paddlefish heals 20 Hitpoints. Filling vials and cooking paddlefish occur in one tick (0.6 s). |
| Source | https://oldschool.runescape.wiki/w/The_Gauntlet |
| Confidence | `verified` |
| Intended module | `crafting` / `player` |
| Test id | `test_rules_paddlefish_heal` |

### R-RES-06 — Crystal/corrupted paddlefish

| Field | Value |
|-------|-------|
| Statement | Crystal/corrupted paddlefish heal 16 Hitpoints and can be eaten without delay (karambwan-like). Recipe: cooked paddlefish + 10 shards. |
| Source | https://oldschool.runescape.wiki/w/The_Gauntlet ; https://oldschool.runescape.wiki/w/Crystal_shards_(The_Gauntlet) |
| Confidence | `verified` |
| Intended module | `crafting` |
| Test id | `test_rules_crystal_paddlefish` |

---

## 4. Enemies

### R-MOB-01 — Monster tiers (Corrupted names)

| Field | Value |
|-------|-------|
| Statement | Nine monster types in three tiers (Corrupted variants): Weak — spiders/rats/bats; Strong — unicorns/scorpions/wolves; Demi-bosses — bears/dragons/dark beasts (combat level 172 for crystalline counterparts; Corrupted have increased stats). |
| Source | https://oldschool.runescape.wiki/w/The_Gauntlet |
| Confidence | `verified` for categories; exact Corrupted combat stats `unknown` → `A-MOB-STATS-01` |
| Intended module | `combat` / `dungeon` |
| Test id | `test_rules_monster_tiers` |

### R-MOB-02 — Monster drops (shared structure)

| Field | Value |
|-------|-------|
| Statement | Monsters may drop shards, weapon frames, raw paddlefish, grym leaves, teleport crystals. First bear → spike (T3 halberd); first dragon → orb (T3 staff); first dark beast → bowstring (T3 bow). Duplicate demi-bosses can guarantee a missing T3 component. First weak kill guarantees a weapon frame (22 Jul 2026 update). |
| Source | https://oldschool.runescape.wiki/w/The_Gauntlet |
| Confidence | `verified` for drop types/guarantees; Corrupted item renaming `strongly_supported` |
| Intended module | `combat` / `inventory` |
| Test id | `test_rules_monster_drops` |

### R-MOB-03 — Shard drop quantities (monster)

| Field | Value |
|-------|-------|
| Statement | Wiki shard table (Gauntlet crystalline): weak 20–30 always; strong 80–100 always; demi-boss 50–60 always. Corrupted uses corrupted shards; quantities assumed same pending confirmation. |
| Source | https://oldschool.runescape.wiki/w/Crystal_shards_(The_Gauntlet) |
| Confidence | `strongly_supported` |
| Intended module | `combat` |
| Test id | `test_rules_monster_shard_qty` |

### R-MOB-04 — Demi-boss spawn (post-22 Jul 2026)

| Field | Value |
|-------|-------|
| Statement | North/east/south/west-most rooms from the centre now have a guaranteed random demi-boss spawn. Demi-bosses can spawn in any edge or corner room. Attack range reduced 16→10. |
| Source | https://oldschool.runescape.wiki/w/The_Gauntlet (Changes 22 July 2026) |
| Confidence | `verified` for update text; exact Corrupted spawn count/distribution details still partially `unknown` → `A-DEMI-SPAWN-01` |
| Intended module | `dungeon` |
| Test id | `test_rules_demi_spawn_cardinals` |

---

## 5. Crafting

### R-CRAFT-01 — Weapon tiers

| Field | Value |
|-------|-------|
| Statement | Weapons: bow / halberd / staff × basic / attuned / perfected. Basic = weapon frame (+ 0 shards post-22 Jul 2026). Attuned = basic + 50 shards. Perfected = attuned + spike/orb/bowstring. |
| Source | https://oldschool.runescape.wiki/w/The_Gauntlet ; Changes 22 July 2026 |
| Confidence | `verified` |
| Intended module | `crafting` |
| Test id | `test_rules_weapon_costs` |

### R-CRAFT-02 — Armour material + shard costs

| Field | Value |
|-------|-------|
| Statement | Armour ore/linum/bark: T1 each piece 1/1/1; T2 body 2/2/2, helm/legs 1/1/1; T3 each piece 2/2/2. Shards: T1 each 50; T2 body 100, helm/legs 50; T3 each 100. |
| Source | https://oldschool.runescape.wiki/w/The_Gauntlet ; https://oldschool.runescape.wiki/w/Crystal_shards_(The_Gauntlet) |
| Confidence | `verified` |
| Intended module | `crafting` |
| Test id | `test_rules_armour_costs` |

### R-CRAFT-03 — Utility crafts

| Field | Value |
|-------|-------|
| Statement | Vial = 10 shards; teleport crystal = 50 shards; escape crystal = 200 shards; crystal/corrupted paddlefish = cooked fish + 10 shards. |
| Source | https://oldschool.runescape.wiki/w/Crystal_shards_(The_Gauntlet) |
| Confidence | `verified` |
| Intended module | `crafting` |
| Test id | `test_rules_utility_crafts` |

### R-CRAFT-04 — Egniol potion

| Field | Value |
|-------|-------|
| Statement | Fill vial → add grym leaf → unfinished; grind 10 shards → 10 dust; add dust → egniol (3). Restores prayer via ⌊PrayerLevel/4⌋+7 (wiki math shown as ×1/4), 40% run energy, and stamina effect. Creation is 1 tick. |
| Source | https://oldschool.runescape.wiki/w/Egniol_potion |
| Confidence | `verified` for recipe/effects table; formula notation interpreted from restore table |
| Intended module | `crafting` / `player` |
| Test id | `test_rules_egniol` |

### R-CRAFT-05 — Crush T3 components

| Field | Value |
|-------|-------|
| Statement | Spike/orb/bowstring can be crushed to 80 shards (confirmation dialogue ≥1 tick). |
| Source | https://oldschool.runescape.wiki/w/Crystal_shards_(The_Gauntlet) |
| Confidence | `verified` |
| Intended module | `crafting` |
| Test id | `test_rules_crush_t3` |

---

## 6. Inventory & starting loadout

### R-INV-01 — Starting tools

| Field | Value |
|-------|-------|
| Statement | Player starts **wielding** the sceptre; inventory starts with axe, pickaxe, harpoon, pestle and mortar, and one teleport crystal (5 slots). Tool storage can re-obtain tools. |
| Source | https://oldschool.runescape.wiki/w/The_Gauntlet |
| Confidence | `verified` |
| Intended module | `inventory` / `player` |
| Test id | `test_rules_starting_items` |

### R-INV-02 — No external items

| Field | Value |
|-------|-------|
| Statement | Players cannot bring items into the Gauntlet; gear is stored for the duration. Pre-applied boosts are cleared on entry. |
| Source | https://oldschool.runescape.wiki/w/The_Gauntlet |
| Confidence | `verified` |
| Intended module | `player` |
| Test id | `test_rules_no_external_items` |

### R-INV-03 — Inventory capacity

| Field | Value |
|-------|-------|
| Statement | Standard OSRS inventory is 28 slots. Ore/bark/linum are stackable (22 Jul 2026). Shards auto-enter inventory and are stackable. Exact slot accounting for Corrupted run not wiki-specialized. |
| Source | https://oldschool.runescape.wiki/w/The_Gauntlet (Changes); general OSRS inventory |
| Confidence | `strongly_supported` for 28 slots; stackability `verified` |
| Intended module | `inventory` |
| Test id | `test_rules_inventory_capacity` |

---

## 7. Combat ticks & Corrupted Hunllef

### R-BOSS-01 — Boss identity & stats

| Field | Value |
|-------|-------|
| Statement | Corrupted Hunllef: combat level 894, size 5×5, Hitpoints 1000, Attack/Strength/Defence/Magic/Ranged 240 each, attack speed 5 ticks (3.0 s), aggressive, poison/venom immune. Aggressive bonuses Atk +90 / Str +112 / Mage Atk +90 / Mage Str +112 / Range Atk +90 / Range Str +112. Defence bonuses +20 across styles. |
| Source | https://oldschool.runescape.wiki/w/Corrupted_Hunllef |
| Confidence | `verified` |
| Intended module | `boss` / `combat` |
| Test id | `test_rules_hunllef_stats` |

### R-BOSS-02 — Standard attacks & first style

| Field | Value |
|-------|-------|
| Statement | Uses magic and ranged standard attacks. First attack style is always Ranged. |
| Source | https://oldschool.runescape.wiki/w/Corrupted_Hunllef |
| Confidence | `verified` |
| Intended module | `boss` |
| Test id | `test_rules_hunllef_first_style` |

### R-BOSS-03 — Attack style cycle

| Field | Value |
|-------|-------|
| Statement | Every fourth attack (standard, prayer-disabling, or tornado; excluding stomp) switches standard attack style. Animation precedes the switch. |
| Source | https://oldschool.runescape.wiki/w/Corrupted_Hunllef |
| Confidence | `verified` |
| Intended module | `boss` |
| Test id | `test_rules_attack_style_cycle` |

### R-BOSS-04 — Protection prayer cycle

| Field | Value |
|-------|-------|
| Statement | Every sixth off-prayer player attack (including 0-damage hits) changes Hunllef’s protection prayer to the style of that sixth hit. |
| Source | https://oldschool.runescape.wiki/w/Corrupted_Hunllef |
| Confidence | `verified` |
| Intended module | `boss` |
| Test id | `test_rules_prayer_cycle` |

### R-BOSS-05 — Stomp

| Field | Value |
|-------|-------|
| Statement | If the player is underneath Hunllef when it tries to attack, it stomps for up to 68 typeless damage. Stomp does not count toward the 4-attack style cycle. |
| Source | https://oldschool.runescape.wiki/w/Corrupted_Hunllef |
| Confidence | `verified` |
| Intended module | `boss` / `combat` |
| Test id | `test_rules_stomp` |

### R-BOSS-06 — Prayer-disabling attack

| Field | Value |
|-------|-------|
| Statement | During magic-style attacks, Hunllef has a chance to use a prayer-disabling attack (distinct colour/sound). Exact probability is unknown. |
| Source | https://oldschool.runescape.wiki/w/Corrupted_Hunllef |
| Confidence | `verified` that it exists; probability `unknown` → `A-PRAYER-DISABLE-01` |
| Intended module | `boss` |
| Test id | `test_rules_prayer_disable_exists` |

### R-BOSS-07 — Tornado counts & duration

| Field | Value |
|-------|-------|
| Statement | Tornadoes chase the player and despawn after 20 ticks (12.0 s). Counts by Hunllef HP: >66% → 2; 33–66% → 3; <33% → 4. |
| Source | https://oldschool.runescape.wiki/w/Tornado_(Corrupted_Gauntlet) ; https://oldschool.runescape.wiki/w/Corrupted_Hunllef |
| Confidence | `verified` |
| Intended module | `boss` |
| Test id | `test_rules_tornado_counts` |

### R-BOSS-08 — Tornado damage by armour

| Field | Value |
|-------|-------|
| Statement | Tornado damage per tick while co-located, by full armour set (Tornado page): none 15–30; T1 14–25; T2 10–20; T3 8–15. Note: Corrupted Hunllef page lists slightly different T1/T3 ranges — see uncertainty `A-TORNADO-DMG-01`. |
| Source | https://oldschool.runescape.wiki/w/Tornado_(Corrupted_Gauntlet) |
| Confidence | `strongly_supported` (primary tornado page); cross-page conflict noted |
| Intended module | `boss` / `combat` |
| Test id | `test_rules_tornado_damage` |

### R-BOSS-09 — Floor tiles

| Field | Value |
|-------|-------|
| Statement | Floor tiles highlight crimson then turn orange; standing on orange deals damage each tick. Pattern sets/speeds by HP: 1000–667 slow set 1; 666–333 medium set 2; ≤332 rapid set 3. Exact damage range wiki-marked confirmation needed (10–20 on boss page). |
| Source | https://oldschool.runescape.wiki/w/Corrupted_Hunllef |
| Confidence | `verified` for phases; damage `unknown`/`inferred` → `A-FLOOR-DMG-01`; pattern layouts `unknown` → `A-FLOOR-PATTERN-01` |
| Intended module | `boss` |
| Test id | `test_rules_floor_phases` |

### R-BOSS-10 — Prayed max hits by armour tier sum

| Field | Value |
|-------|-------|
| Statement | With correct protection prayer, Corrupted Hunllef max hit by armour tier sum: 0→16; full T1 (3)→13; full T2 (6)→10; full T3 (9)→8. Tier-sum appears to drive reduction (e.g. T3+T1+T2 = 6 matches full T2). |
| Source | https://oldschool.runescape.wiki/w/The_Gauntlet ; https://oldschool.runescape.wiki/w/Corrupted_Hunllef |
| Confidence | `verified` for listed combinations; general tier-sum model `strongly_supported` |
| Intended module | `combat` / `boss` |
| Test id | `test_rules_prayed_max_hits` |

### R-BOSS-11 — Unprayed max hits

| Field | Value |
|-------|-------|
| Statement | Without correct protection prayer, max hits: no armour 68; full T1 55; full T2 45; full T3 35. |
| Source | https://oldschool.runescape.wiki/w/Corrupted_Hunllef |
| Confidence | `verified` |
| Intended module | `combat` / `boss` |
| Test id | `test_rules_unprayed_max_hits` |

### R-BOSS-12 — Shared mechanics with Crystalline

| Field | Value |
|-------|-------|
| Statement | Wiki states both Crystalline and Corrupted Hunllef use the same mechanics (cycles, floors, tornadoes); Corrupted has higher HP/stats/damage tables. |
| Source | https://oldschool.runescape.wiki/w/Corrupted_Hunllef |
| Confidence | `verified` |
| Intended module | `boss` |
| Test id | `test_rules_shared_mechanics` |

---

## 8. Starting room facilities

### R-HUB-01 — Hub objects

| Field | Value |
|-------|-------|
| Statement | Starting room contains: recipe bookstands, range, singing bowl, teleport platform (abandon), tool storage, water pump. |
| Source | https://oldschool.runescape.wiki/w/The_Gauntlet |
| Confidence | `verified` |
| Intended module | `dungeon` / `crafting` |
| Test id | `test_rules_hub_objects` |

---

## 9. Unknowns research promotions (post Phase 1 scaffold)

### R-TOPO-05 — Orthogonal connectivity once lit

| Field | Value |
|-------|-------|
| Statement | Adjacent rooms are reached by lighting doorway nodes with the sceptre; the 7×7 grid is treated as fully orthogonally connected once rooms are lit (no evidence of permanently blocked adjacent edges). |
| Source | https://oldschool.runescape.wiki/w/Crystal_sceptre ; https://oldschool.runescape.wiki/w/The_Gauntlet/Strategies |
| Confidence | `strongly_supported` |
| Intended module | `dungeon` |
| Test id | `test_rules_orthogonal_edges` |

### R-TOPO-06 — Guaranteed fish room location

| Field | Value |
|-------|-------|
| Statement | In Corrupted Gauntlet, one room **adjacent to the Hunllef** is guaranteed to have at least three fishing spots (12 paddlefish). |
| Source | https://oldschool.runescape.wiki/w/The_Gauntlet/Strategies (Corrupted section) |
| Confidence | `strongly_supported` |
| Intended module | `dungeon` |
| Test id | `test_rules_fish_room_adjacent` |

### R-RES-07 — Corrupted shard quantities

| Field | Value |
|-------|-------|
| Statement | Corrupted monster always-drops: weak 20–30; strong 80–100; demi-boss 50–60. Gathering nodes: 10–30 at 1/3. Confirmed on Corrupted shards page (not borrowed from crystalline-only tables). |
| Source | https://oldschool.runescape.wiki/w/Corrupted_shards |
| Confidence | `verified` |
| Intended module | `resources` / `combat` |
| Test id | `test_rules_corrupted_shard_qty` |

### R-RES-08 — Paddlefish burn stop level

| Field | Value |
|-------|-------|
| Statement | Paddlefish can burn; stop burning at Cooking level 47. Burn rate below 47 remains unknown (`A-COOK-BURN-01`). |
| Source | https://oldschool.runescape.wiki/w/Paddlefish |
| Confidence | `verified` |
| Intended module | `crafting` |
| Test id | `test_rules_paddlefish_stop_burn` |

### R-MOB-05 — Corrupted mob combat stats

| Field | Value |
|-------|-------|
| Statement | Exact wiki stats for all nine Corrupted mobs (including scorpion + wolf). Weak rooms spawn up to 3; mid-level always spawn in pairs; demi-bosses spawn alone on map edges. |
| Source | Corrupted monster wiki pages (see `data/rules` source ids) |
| Confidence | `verified` |
| Intended module | `combat` / `dungeon` |
| Test id | `test_rules_corrupted_mob_stats` |

### R-TOPO-07 — Demi-boss guarantees (Summer Sweep-Up)

| Field | Value |
|-------|-------|
| Statement | Exactly four guaranteed demi-bosses at north/east/south/west-most rooms from centre; type random (uniform). Additional demi-bosses may appear on other edge/corner rooms (count unknown → `A-DEMI-SPAWN-01`). |
| Source | https://secure.runescape.com/m=news/summer-sweep-up-gear--pvm-changes?oldschool=1 ; wiki Changes 22 Jul 2026 |
| Confidence | `verified` (four guarantees); extras `unknown` |
| Intended module | `dungeon` |
| Test id | `test_rules_demi_guaranteed_count` |

### R-EXPLORE-01 — Room light ticks

| Field | Value |
|-------|-------|
| Statement | Lighting a new room with the sceptre costs **1 tick** (user-confirmed; consistent with single click-to-enter lighting). |
| Source | User confirmation; https://oldschool.runescape.wiki/w/Crystal_sceptre |
| Confidence | `strongly_supported` |
| Intended module | `dungeon` / `player` |
| Test id | `test_rules_room_light_ticks` |

### R-CRAFT-06 — Singing bowl craft ticks

| Field | Value |
|-------|-------|
| Statement | Creating/upgrading corrupted weapons at the singing bowl takes 1 tick (0.6 s). |
| Source | https://oldschool.runescape.wiki/w/Corrupted_bow_(perfected) (and staff/halberd perfected) |
| Confidence | `verified` |
| Intended module | `crafting` |
| Test id | `test_rules_sing_ticks` |

### R-COMBAT-01 — Weapon attack speeds

| Field | Value |
|-------|-------|
| Statement | Corrupted bow: Accurate/Longrange 5 ticks, Rapid 4 ticks. Corrupted staff Accurate: 4 ticks. Corrupted halberd: 4 ticks (unlike normal halberds at 7). Perfected staff max hit 39 (40 with Augury/Mystic Vigour), independent of Magic level. |
| Source | Corrupted weapon wiki pages |
| Confidence | `verified` |
| Intended module | `combat` |
| Test id | `test_rules_weapon_speeds` |

### R-INV-04 — Starting slot accounting

| Field | Value |
|-------|-------|
| Statement | Player starts **wielding** the sceptre; inventory starts with axe, pickaxe, harpoon, pestle and mortar, teleport crystal → **5** occupied inventory slots. |
| Source | https://oldschool.runescape.wiki/w/The_Gauntlet |
| Confidence | `verified` |
| Intended module | `inventory` |
| Test id | `test_rules_starting_slots` |

### R-PLAYER-01 — Egniol stamina + run/prayer drain

| Field | Value |
|-------|-------|
| Statement | Egniol “acts as a stamina potion” → 70% run-drain reduction for 2 minutes (200 ticks) under standard Energy rules; egniol restores 40% run (not stamina’s 20%). Prayer drain effects: Protect 12; Rigour/Augury/Piety 24 (standard Prayer wiki). Corrupted armour prayer bonus is 0 on wiki gear tables. |
| Source | https://oldschool.runescape.wiki/w/Egniol_potion ; https://oldschool.runescape.wiki/w/Stamina_potion ; https://oldschool.runescape.wiki/w/Energy ; https://oldschool.runescape.wiki/w/Prayer |
| Confidence | `verified` (egniol acts as stamina; prayer drain effects); `strongly_supported` (stamina duration/multiplier apply inside Gauntlet) |
| Intended module | `player` |
| Test id | `test_rules_egniol_stamina_prayer` |

### R-BOSS-13 — Stomp trigger wording

| Field | Value |
|-------|-------|
| Statement | Stomp occurs if the player is underneath when Hunllef **tries to attack** → model as `on_attack_tick`, not continuous overlap. |
| Source | https://oldschool.runescape.wiki/w/Corrupted_Hunllef |
| Confidence | `strongly_supported` |
| Intended module | `boss` |
| Test id | `test_rules_stomp_trigger` |

---

## Cross-cutting notes

- Prefer `unknown` + assumption id over inventing exact generation probabilities, gather tick rates, or prayer-disable rates.
- Ordinary Gauntlet inner-ring mitigation must **not** be applied to Corrupted simulations.
- July 22 2026 update materially changed shard ranges, crafting costs, demi-boss spawns, and stackability — Phase 1 rules reflect post-update wiki text.
- Tornado damage: prefer `Tornado_(Corrupted_Gauntlet)` page as canonical; Hunllef page has small T1/T3 conflicts (`A-TORNADO-DMG-01`).
