# Corrupted Gauntlet video gap analysis (vs GauntletSim Phase 3.5)

**Date:** 2026-10-14  
**Scope:** Prep-first (Phase 3.5 fog agent). Boss notes are Phase 4 only.  
**Rule:** Corrupted-specific evidence only — no ordinary-Gauntlet inventions.

## Videos / sources reviewed

| # | Source | URL | Role |
|---|--------|-----|------|
| V1 | **Molleon OSRS** — *Corrupted Gauntlet Tier 2 Prep Guide (3 full runs)* | https://www.youtube.com/watch?v=2xr07bp3HrU | 3 full T2 prep runs; chapter marks **00:00** overview, **04:38** run 1, **16:46** run 2, **28:37** run 3 |
| V2 | **Gnomonkey** — *NEW CORRUPTED GAUNTLET IS FREE (Tier 1 + Tier 2 Prep)* | https://www.youtube.com/watch?v=CA6-2CqM_NQ | Post–Summer Sweep-Up (Jul 2026) live T2 prep + Hunllef; full auto-caption transcript used |
| V3 | **Tier 1 Prep Guide** — *The ONLY Tier 1 Prep Guide You Will Need* | https://www.youtube.com/watch?v=bxG1oslI6vY | T1-focused Corrupted prep (metadata; playback blocked in agent browser) |
| V4 | **Frank Gamer** written + embedded full run | https://frankgamer.com/2025/04/06/osrs-corrupted-gauntlet-guide-for-beginners/ | C-path learner method; updated for Jul 2026 Sweep-Up |
| W1 | OSRS Wiki — *The Gauntlet* + user prep | https://oldschool.runescape.wiki/w/The_Gauntlet · https://oldschool.runescape.wiki/w/User:Bimbini/cg/prep | Verified costs/stacking; **Bimbini 2-trip** method |

**Watching note:** Direct YouTube playback was blocked by bot-checks in the agent browser. Analysis uses (1) V2 full transcript, (2) V1 chapter metadata, (3) Frank/Bimbini/wiki text, (4) wiki stills under `media/video-review/`. Treat “seen clearly” as **transcript/wiki-confirmed**; prefer re-scrubbing V1/V2 in a human browser for frame-perfect timestamps.

### Stills (wiki / review)

- `/cursor/stores/self/media/video-review/wiki-2026-changes.webp`
- `/cursor/stores/self/media/video-review/wiki-starting-room.webp`
- `/cursor/stores/self/media/video-review/wiki-resource-nodes.webp`

---

## What the sim already gets right (prep)

| Item | Evidence | Sim |
|------|----------|-----|
| 7:30 Corrupted prep timer | Wiki / guides | `prep_ticks` 750 |
| Stackable ore/bark/linum | V2 + wiki 2026 | `ore_bark_linum_stackable` |
| Shards auto-inventory | V2 (“magnet”) + wiki | `shards_auto_inventory` |
| First weak kill → weapon frame | V2 + wiki | `first_weak_guarantees_weapon_frame` |
| T1 weapon 0 shards / T2 weapon 50 | Wiki 2026 | crafting rules |
| T2 armour mats 7/7/7 + shard table | Wiki / Bimbini | armour materials/shards |
| Hub bowl / range / pump | V2 + wiki | hub stations + path-before-action |
| Fog: light by entering, not omniscient map | V2/Frank “check rooms” | `FogKnowledge` + `LayoutFogProxy` |
| Guaranteed demi on N/E/S/W outer | V2 + wiki | map generator |
| Guaranteed fish room adj. boss | V2 (“triple fish surrounding boss”) | layout rule |
| Teleport crystal home | All guides | `teleport_to_start` |
| Egniol = grym + water vial + dust | Wiki / V2 | crafting path |
| Perfected bow/staff need orb/bowstring | All | demi → T3 parts |

---

## Gap list

Confidence: **seen clearly** (transcript/wiki) · **likely** (guides agree, not frame-locked) · **unclear** (needs re-watch / measurement).  
Kind: **rule** (encode as verified fact) · **assumption** (label + default) · **agent** (policy only) · **Phase 4** (boss).

| ID | Gap | Confidence | Kind | Impact on prep timing / route |
|----|-----|------------|------|-------------------------------|
| G01 | **Multi-trip / mid-prep hub craft** — players return mid-run to make T2 weapon + vials + partial armour, drop leftover mats at bowl, then go out again for demis/fish | seen clearly (Bimbini W1; Frank V4; V2 returns to craft then fishes more) | **agent** (+ small inv/state) | **Critical** — our fog agent is one gather → one craft; real route quality is 2-trip |
| G02 | **C-path / structured outer scouting** — C around boss, check cardinal demis, note fish/grym for later | seen clearly (Frank, Bimbini, community) | **agent** | **High** — fog frontier “nearest + boss-adj” ≠ meta route |
| G03 | **Fill vials at fishing spots** (not only water pump) | seen clearly (V2: “On these fishing spots, you can actually also fill your vials”) | **rule** | **High** — saves hub trips; enables potions while fishing |
| G04 | **Interleaved combat + gather** — hit mobs between resource clicks / kite while looting room | seen clearly (V2; Reddit/Fluffeh tips) | **assumption** (tick model) + **agent** | **High** — we spend full `prep_*_kill_ticks` then gather; real overlap cuts move/fight waste |
| G05 | **Monster drops: fish, grym, tele crystal** on weak/strong (not only shards/frames) | seen clearly (Frank V4; V2 “drop fish”; wiki) | **rule** | **High** — less dedicated fishing/grym pathing |
| G06 | **True prep combat** (HP, Protect Magic before demi rooms, can’t tank demis without pray) | seen clearly (V2: “Never enter… without mage pray”) | **assumption** → later **rule** | **Medium–High** — forces safer enter order; our clear is damage-free |
| G07 | **Drink egniol in prep for stamina** while running | likely (Bimbini: fill vials or risk stamina; egniol = stam+pray) | **agent** (API exists: `drink_egniol`) | **Medium–High** — run-energy already modeled; agent never sips in prep |
| G08 | **On-the-move potion crafting** (grind dust / make egniol while pathing, not only at hub) | seen clearly (Bimbini trip 2; Frank) | **agent** (+ maybe no-station craft ticks) | **Medium** — parallelizes wait time |
| G09 | **Drop tools as soon as that resource is done** (axe/pick/harp mid-run) | seen clearly (Bimbini) | **agent** | **Medium** — inv slots / fewer late drops |
| G10 | **Scout memory without picking up** (note fish/grym, gather later) | seen clearly (Frank) | **agent** | **Medium** — better second-trip planning under fog |
| G11 | **Crush unwanted T3 parts → 80 shards** | seen clearly (V2; Bimbini; wiki `crush_t3`) | **agent** (rule may exist) | **Medium** — shard shortfalls without extra strong kills |
| G12 | **Decant egniol 3×3 → 2×4-dose** (inv space) | likely (Frank: 3 leaves → two 4-dose) | **rule** + **agent** | **Medium** — final inv / food count |
| G13 | **Juggle / ground-drop fish & mats** at bowl between crafts | seen clearly (Bimbini; V2 drops frames/fish) | **agent** | **Medium** — capacity choreography |
| G14 | **Second teleport crystal craft (40/50 shards)** when free tele used | likely (Frank) | **rule** (cost) + **agent** | **Low–Medium** |
| G15 | **Combo / crystal paddlefish** (optional food) | wiki / guides | **rule** + **agent** | **Low** for timing |
| G16 | **Kill-time assumptions** (weak/strong/demi tick lumps) | unclear — needs timed V1 scrub | **assumption** | **High if wrong** — dominates fight bucket |
| G17 | **Gather interval / node yields** vs real click cadence | unclear — V2 shows plugin “7” cutoff | **assumption** | **Medium** |
| G18 | **Timer expiry → forced into Hunllef** | seen clearly (V2) | **Phase 4** / sim end | Prep end condition |
| G19 | **Wait at boss door for Hunllef corner** before enter | seen clearly (Bimbini; guides) | **Phase 4** | Boss start quality |
| G20 | **Hunllef: prayer switch, disable bolt, tornados, floor, stomp** | seen clearly (V2 end; Frank) | **Phase 4** | Out of Phase 3.5 |

---

## Top 10 missing items (by prep timing / route impact)

1. **G01 — Multi-trip mid-prep craft loop** (agent)  
2. **G02 — C-path / cardinal demi scouting policy** (agent)  
3. **G04 — Overlapped fight+gather tick model** (assumption + agent)  
4. **G03 — Fill vials at fishing spots** (rule)  
5. **G05 — Mob drops of fish/grym/tele** (rule)  
6. **G16 — Calibrate prep kill ticks from video** (assumption)  
7. **G06 — Prep combat threat / protect-before-demi** (assumption)  
8. **G07 — Sip egniol for stamina during prep** (agent)  
9. **G08 — Craft potions while moving** (agent)  
10. **G11 — Crush spare T3 parts for shards** (agent)

Items 1–2 alone explain most of the gap between “human T2 prep feels tight but reliable” and our single-pass fog sweep.

---

## Phase 4 boss gaps (brief)

From V2 + Frank (not implementing now):

- Enter with **Protect Missiles**; swap on style change  
- **Prayer-disable** mage projectile (re-enable immediately)  
- **Tornadoes** chase (true-tile plugin); count scales with HP  
- **Floor tiles** warn → damage; faster later  
- **Stomp** if under Hunllef  
- T2 armour reduces boss **and** floor/tornado damage (V2 commentary)  
- Optional: wait outside door until Hunllef is cornered (Bimbini)

---

## Follow-up patch list (proposed, not implemented)

| Priority | Change | Notes |
|----------|--------|-------|
| P0 | Agent: **2-trip loadout scenario** (craft mid-run, drop mats at bowl, second trip demis+fish) | Biggest route realism win |
| P0 | Agent: **C-path / cardinal demi priority** under fog | Match V4/W1 |
| P1 | Rule: **fill vial at fishing spot** (same ticks as pump or wiki value) | Unlock G03 |
| P1 | Rule: weak/strong **fish / grym / tele** drop tables | From wiki |
| P1 | Assumption: retune `prep_*_kill_ticks` from timed V1 runs | Record mm:ss kills |
| P2 | Agent: drink egniol when run energy low; crush spare orb/spike/bowstring | Uses existing APIs where present |
| P2 | Agent: drop tools when resource quota met | Bimbini |
| P3 | Rule: egniol decant 3→4 dose | Inv realism |
| P3 | Phase 4 stub: timer → enter boss; door wait | Separate PR |

---

## Method caveats

- **No invented ordinary-Gauntlet mechanics.**  
- YouTube **frame scrub incomplete** (bot wall); V2 transcript is strong Corrupted+2026 evidence; re-watch V1 chapters 04:38 / 16:46 / 28:37 for kill-time calibration.  
- Success-rate under fog (71/100) can **rise or fall** after multi-trip — measure again after P0.
