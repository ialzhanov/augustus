# All Roads Lead to Rome — design analysis

Campaign by Turgon for Augustus. 7 missions, 14 scenarios listed, 13 on disk.
Source: every `.mapx` loaded headless through Augustus's own loader (latest upstream `dae1899`),
events and messages exported with Augustus's own XML exporters, terrain counted tile by tile.
Raw data: made by `../tools/run3.sh` (not in the repository).
Terrain montage: `images/arlr_montage.png`.

Units: event `time` values are months. Repeat values are days (16 days = 1 month, 192 = 1 year).

---

## 1. Short answer

**A map is complicated** when many independent systems run at the same time and each one has its own
gate, cost, and failure. This campaign stacks six layers: terrain, forbidden buildings, a stat cap,
a custom economy, scripted military, and per-map rule text. The maps that feel hardest
(Londinium, Marcianopolis, Antiochia, Castra Regina) have all six layers active. The "easy" ones have two or three.

**A map is a good challenge** when the complication forces a decision the player can see, and the
penalty for a wrong decision is legible and recoverable. Complication that is only volume
(ship 32,000 food, hold 500,000 denarii) makes a map long, not good. Complication that is hidden,
contradicted by the briefing, or broken by a script bug makes a map unfair.

The central device of this campaign is the **stat cap**: the win target is high (often 100), and a
script holds one rating below it (65–90) until a task is done. That converts a side task into a
mandatory objective. The device works on 11 of 12 capped maps. It leaks on Gesoriacum (cap is above the win target).

---

## 2. Per-map data

Free = tiles with no tree, rock, water, shrub, cliff, ramp, or building (ready land).
Largest region = biggest connected free area at one elevation.
Cleared = the same count when trees and shrub are treated as clearable (only rock, water, cliffs, ramps, and native buildings block).

| # | Map | Size | Free | Largest region (share of free) | Cleared: largest share | Pop goal | Win targets C/P/Pe/F | Events | Vars | Forbidden at start | Max wave |
|---|-----|------|------|------|------|------|------|------|------|------|------|
| 1a | Nuceria | 160² | 24.7% | 2858 (45%) | 33% | 16000 | 85/100/100/100 | 31 | 8 | 10 | 50 |
| 1b | Aquileia | 160² | 40.6% | 3233 (31%) | 35% | 12000 | 85/100/85/100 | 46 | 7 | 10 | 120 (+170 scripted) |
| 2a | Leptis Magna | 160² | 42.8% | 6818 (62%) | 60% | 17000 | 90/100/100/75 | 30 | 10 | 26 | 130 |
| 2b | Cyrene | 120² | 51.5% | 4654 (63%) | 58% | 10000 | 100/100/85/85 | 34 | 20 | 4 | 160 |
| 3a | Gesoriacum | 100² | 32.8% | 1896 (58%) | 56% | (off) | 50/90/90/80, 45-yr limit | 31 | 5 | 20 | 130 |
| 3b | Londinium | 160² | 36.4% | 1568 (**17%**) | **16%** | 14000 | 55/65/65/65 | 80 | 18 | 23 | 200 (+280 scripted) |
| 4a | Complutum | 160² | 33.9% | 1123 (**13%**) | **9%** | 22000 | 100/100/–/100 | 47 | 18 | 38 | none |
| 4b | Narbo Martius | 120² | 31.1% | 1810 (40%) | 44% | 12000 | 70/100/90/90 | 33 | 14 | 6 | 200 (+310 scripted) |
| 5a | Antiochia | 160² | 20.3% | 3156 (61%) | 32% | 18000 | 100/100/100/100 | 65 | 24 | 10 | 50 |
| 5b | Palmyra | 160² | 44.0% | 2816 (25%) | 23% | 18000 | 80/80/80/80 | 56 | 20 | 12 | 150 |
| 6a | Noviomagus | 160² | 20.6% | 1943 (37%) | 43% | 18000 | 70/90/90/70 | 53 | 13 | 41 | 200 |
| 6b | Castra Regina | 160² | 34.3% | 4710 (54%) | 46% | 16000 | 50/75/100/70 | 47 | 21 | 38 | 200 (+589 scripted) |
| 7b | Marcianopolis | 160² | 23.4% | 1086 (18%) | 39% | 20000 | 100/100/–/100 | 40 | 45 | 36 | none (scripted natives) |

Missing: **Bysantium (7a)** is in `settings.xml` but has no file. Narbo Martius is labeled "work in progress".

---

## 3. What makes a map complicated — the six layers

### Layer 1: Geography as the puzzle
The terrain itself is the first rule, and several maps make one terrain feature the main task.

- **Nuceria**: the sea coast is behind the Lactaria mountains. Docks, wharves, and vine/wine are locked until
  the player opens 5 rock blockages. Each one needs 2 adjacent prefectures next to a 1-tile pond at a specific spot,
  8 timber, and a time gate (months 40–76). Some paths are false ("the mountains conceal many false paths").
- **Noviomagus**: the map is a swamp (32% water as scattered tiles). The player reclaims land by feeding
  10 work camps with stone, timber, clay, sand, and bricks. Each reclamation step needs 40–2000 units of one good.
  That is about 10,000 units total.
- **Londinium**: the largest free region is only 17% of free land. The land is cut into villages. Caravans are slow
  until the player opens 3 native "stairs" (caravanserai / Mars grand temple / 5 large temples), plus an optional
  lake bridge (tavern + wine + 30 months).
- **Complutum**: 73.5% of the map is above ground level and the largest region is 13% of free land. Trade traffic
  is blocked by 2 native villages that leave only after a Colosseum and a Pantheon.
- **Marcianopolis**: a native ring of 691 tiles holds the central farmland (forest is clearable; the ring is not). Farming there before the cemetery task
  costs −5 sentiment every day.

**Rule:** fragmentation (small largest region) raises complication more than low free land does. Leptis has 43%
free land in one 62% block and plays simply. Complutum has 34% free land split into eight blocks of 400–1100 tiles.
This holds when trees are cleared: Londinium stays at 16% and Complutum drops to 9%. Their walls are cliffs,
elevation steps, and water, which the player cannot remove. Marcianopolis is different: its forest fragments it (18%),
but clearing raises it to 39%. There the hard walls are the 691-tile native ring, which only scripts remove.

### Layer 2: The forbidden list and the unlock chain
Start-forbidden counts range from 4 (Cyrene) to 41 (Noviomagus). Then events unlock buildings in stages.

The chains get deep. Example, Complutum:
1. Meat comes only from the Tarraco-Rome route.
2. That route opens only at 160 Grand Insulae.
3. Luxury palaces need 4 food types (modifier). Without meat they cannot reach 4.
4. The forum (taxes) unlocks only with 2 luxury palaces on two named hills.
5. From the first grand temple, the player loses −3 favor per year until those palaces exist.

So taxes, favor, and the palace task all wait on the 160-insula task. The briefing lists each task. It does not show the chain.

**Rule:** dependency depth (how many tasks must finish before a key unlock) is the strongest single complexity driver
in this campaign.

### Layer 3: The stat cap
Every map except Londinium and Palmyra holds one rating under a cap with a repeating event:

| Map | Capped rating | Cap | Win target | Release condition |
|-----|-----|-----|-----|-----|
| Nuceria | favor | 80 | 100 | city treasury above 500,000 |
| Aquileia | favor | 80 | 100 | 50×320 wheat + 50×320 meat shipped from granaries |
| Leptis Magna | prosperity | 90 | 100 | Pantheon next to natives |
| Cyrene | favor | 75 | 85 | 20 large temples + Pantheon |
| Gesoriacum | favor | **90** | **80** | 2000 legionaries shipped |
| Complutum | prosperity | 80 | 100 | 5 grand temples + hippodrome + colosseum + pantheon + 160 grand insulae |
| Narbo Martius | prosperity | 90 | 100 | Pantheon (gold only from the mint) |
| Antiochia | prosperity | 85 | 100 | religion points ≥ 50×(pop/1000)+150 |
| Noviomagus | peace | 80 | 90 | grand temple in each of 3 villages |
| Castra Regina | favor | 65 | 70 | keep ≥ 60 towers |
| Marcianopolis | prosperity | 80 | 100 | sell ≥ 2500 goods in a year, 5 times |

The caps are enforced by `change_city_rating ... set_to_value` or `favor_add -10/-15` on a short repeat.
This is the campaign's main lever. It is effective because it is cheap to script and it makes the task non-optional.

### Layer 4: A custom economy per map
Each map rewrites prices at month 0 and adds one economic mechanic.

- **Cyrene silphium**: mission posts on native hills eat 4 olives per post per month. Every 32 olives give 1 "silphium"
  (vines, priced 900). It ships once per year, only if warehouse space exists. This is a real new production chain built from events.
- **Castra Regina towers**: towers cost stone and timber upkeep (2 of each per 5 towers per month). If upkeep fails for 6 months
  in a 7-month window, scripted collapse hits towers in the limes positions. The first grand temple chooses which finished goods
  the gods supply (workshops are forbidden).
- **Palmyra choices**: four binary choices (clay/sand, stone/timber, fish/iron, fruit/olives). Each choice re-prices goods and
  adds or removes trade lines. Building both sides of a pair is an instant loss.
- **Narbo residence**: one governor residence, built once, never rebuildable. Palace, villa, and house trade mint output against labor.
- **Complutum marble**: marble price starts at 450 and climbs +50 every ~8 months to 1250. Marble from a "shady company"
  comes only if the player keeps cavalry forts and accepts native raids.
- **Leptis rubber band**: if the yearly balance is high, gold price falls. If the treasury is low, olive, pottery, and furniture prices rise.
- **Antiochia religion score**: points = 2·small temples + 10·oracles + 10·small mausolea + 20·large mausolea + 20·nymphaea
  + 30·large temples + 60·grand temples, against 50 per 1000 citizens. The gap drives city sentiment up or down.

### Layer 5: Scripted military, often reactive
- Waves scale late to 200 attackers per point, and several maps add scripted multi-point attacks on top of the list
  (Castra Regina: up to 6 groups and 589 attackers at once, released only when no enemy is on the map).
- Londinium and Complutum fire invasions only when the player has more than N soldiers (60–140). A big army brings bigger attacks.
- Overlap: distant battles (army leaves) plus local waves in the same years on Aquileia, Gesoriacum, Noviomagus, and Castra Regina.
- Noviomagus month 140: the Teutoburg event destroys every fort and kills the army. The script refunds 1000 per fort and +20 favor.
- Extra barracks cost money every month (100 per extra barracks on most maps, 200 on Castra Regina, 100 per barracks plus 1 weapon each on Gesoriacum).

### Layer 5b: Hidden model changes
The scenario model data was read and compared with Augustus defaults. Verified changes:
Aquileia health buildings ×2 workers; Leptis entertainment 2–3× workers, lighthouse 75; Cyrene all temples ×2 workers;
Londinium barracks / academy / mess hall 60, armoury cost 50 → 500; Complutum luxury palace food types 3 → 4;
Narbo governor residences 20/40/80 workers; Antiochia temple desirability negative; Palmyra raw-material workers ×2;
Noviomagus mission post 60; Castra tower cost and workers ×2, barracks 75. Production-rate changes
(Gesoriacum marble/iron, Complutum workshops −50%) are stated in text and were not read from data.

### Layer 6: Rule text the player must read and remember
Every map opens with 3–4 messages: modifiers + bestow, forum/tax rules, savings rules, briefing.
The fixed rules change per mission: tax cap 12% → 10% → 8% → 6% → 4% (enforced by `tax_rate_set`).
Bestow purchases need a statue on one specific corner tile and a savings amount that rises across the campaign (3000 → 7500).
Salary stops after 50 years. A mint + governor's palace gives +5 per month.

---

## 4. What makes a good challenge — principles drawn from these maps

### P1. The constraint forces a decision, not only a quantity
Good: Palmyra's four choices, Narbo's one residence, Londinium's "pacify one invasion side" and "free one village",
Cyrene's two bestows, Castra's "which grand temple first". Each one has a real trade-off and a permanent result.

Weaker: Aquileia's 32,000 food and Nuceria's 500,000 treasury. They are pure volume. The player knows the answer
(more farms, more time) on day one. They make the map long, not deep.

### P2. The goal is visible
The author uses visible custom variables as a quest tracker (for example "Wheat Shipments: [2]/50", "Towers: [1]",
"Goods Sold this year: [21]"). This is the campaign's best legibility tool. Maps with this HUD read clearly even with many rules.
Antiochia also shows a sentiment status line that changes with the religion gap.

### P3. The penalty matches the error and can be recovered
- Good: Castra tower collapse (proportional, warned, rebuildable). Complutum −3 favor/year (slow, fixable).
- Harsh: Palmyra instant loss for building one wrong farm, quarry, or pit. One misclick ends a long game.
- Harsh: Marcianopolis −5 sentiment every day for any farm in the middle zone.
- Surprise: Teutoburg (Noviomagus month 140) has no warning before it fires. The explanation message arrives at month 187.

### P4. Escalation is paced against recovery time
Castra Regina only releases a new multi-attack when no enemy is on the map. That prevents stacking and gives a recovery window.
Londinium ties invasions to the player's army size. That is adaptive, but it also rewards keeping the army small.

### P5. The cap must bind
A cap only makes a task mandatory if it sits below the win target. Gesoriacum's favor lock is at 90 and its win favor is 80,
so the 2000-legionary task is not required to win (see §5). Every other capped map binds correctly.

### P6. The briefing and the script must agree
Players plan from the text. Each mismatch below costs trust even when it makes the map easier.

### P7. Substitutes keep a target reachable when its normal source is forbidden
Theaters are forbidden on several maps that still demand culture 70–100. In Augustus each monument adds +6 culture
(`MONUMENT_CULTURE_BONUS`), and theaters give at most 25. So the culture target turns into a monument target.
On Marcianopolis (culture 100, no theaters until 1750 exports/year) the player needs about 5 monuments for the last 25 points.
This makes the "Allow all 5 Grand Temples" setting **required**, not suggested, on Marcianopolis and Complutum
(Complutum's prosperity task demands 5 grand temples by name).

---

## 5. Defects found (verified in the data and engine source)

Ordered by impact.

1. **Marcianopolis will not load in the installed game.** It is saved as scenario format v29. The installed Augustus
   (`4.0.0.1500-95e120d80`) reads up to v26. It needs a newer Augustus build. It also uses `quota_fill` and `kill_walkers_in_area`, which are new features.
2. **Castra Regina — "Training Haste" bestow is inverted.** E7 charges −200/month per extra barracks. E50 adds +200/month
   while the bestow is NOT bought. Net: the 2nd barracks is free without the bestow, and costs 200/month after the player pays 7000 for it.
3. **Castra Regina — "Artisan Support" bestow buys itself.** E53 checks `small_statue >= 0`, which is always true. The first time
   savings reach 7000, 6000 is taken automatically. This blocks saving for the other 7000 bestows. Its reward (E40) adds furniture
   twice and pottery zero times.
4. **Narbo Martius — Governor House makes barracks unstaffable.** E20 runs every day and adds +30 barracks workers with
   `set_to_value=false`. `change_model_data` adds to the current value, so the demand grows each day until the engine maximum.
   (Palace and villa set the value first, so they are stable.)
5. **Gesoriacum — the favor cap does not bind the win target.** The favor lock fires at ≥90 favor. Win favor is 80. The briefing says
   "favor is locked at 75" and "deliver 2000 legionaries to complete this scenario". Win criteria do not read the legionary counter.
   Culture 50 is reachable without the 1600-legionary unlock (large temples 30 + school 15 + academy 10 + Mars GT 6).
   Part of the task is probably still needed indirectly: prosperity 90 needs high housing, and colosseum/arena (800 shipped)
   and theaters (1600 shipped) are the only entertainment beyond taverns. Not verified in play. The full 2000 is not required.
6. **Leptis Magna — three formulas are stored as errors and evaluate to 0.** `4,5` (wage rise), `(-3500,-3500)` (theater bestow cost),
   `(5,5)` (mint savings). Effect: no Rome wage rises, the theater bestow is free, and the mint gives nothing.
   Cause: the formula checker rejects a comma outside `{}`. Only Leptis was saved with the error flag.
7. **Range formulas never randomize.** 11 maps use `(a,b)` or `a,b` where `{a,b}` was meant (plague severity `(-35,-50)`, wage rises `3,4`,
   marble price `50,60`). The engine evaluates them as the first number. All intended randomness in those events is fixed at the minimum.
   If these maps are re-saved in a newer editor, they may also flip to the error state of item 6.
8. **Palmyra — the patrician ban only checks luxury palaces.** E0 writes 8 house counts into the same variable. Each write replaces the last,
   so `patric` = luxury palace count only. Villas and smaller palaces anywhere are not detected. The "you will lose" warning is not scripted.
9. **Marcianopolis — theft works for 2 of 15 goods.** E12 sets `steal` to 1–15, but only E13 (clay) and E14 (timber) test `steal`.
   E15–E26 test other variables that never change. The briefing says "4 random kinds of goods".
10. **Castra Regina — tower collapse is location-bound.** E3 and E57 collapse towers only inside ~36 fixed grid rectangles
    (the intended limes line). A tower built outside those rectangles never collapses when upkeep fails.
    Upkeep is still taken for all towers, so the exploit is "build the 60 towers off-line", not "skip upkeep".
11. **Castra Regina — weather fix can be lost.** Immigration goes back to 50% if the highway station or caravanserai is lost.
    The 80% event fires only once.
12. **Unshown messages with real content.** Castra `concrete` (the only explanation of the weather/immigration task), Noviomagus `scouts`
    (map guidance) and `reduced trades` (an 80-patrician task that has no script), Narbo `defend` (tower bonus with no script),
    Leptis `rule` (tower limits with no script), Palmyra `donations`, Aquileia `wheat5` (there is no event for 40 meat shipments).
13. **Briefing vs script mismatches.**
    - Leptis: plaza at culture 80 (text) vs 70 (script); bestow 3250 vs 3500.
    - Cyrene: patrician reward 2000 vs 2500. "Only one bestow" is not enforced.
    - Gesoriacum: arch income 100 vs 150. Barracks money fee is not in the text (100 per barracks, first included).
    - Narbo: bestow +2 (purchase text) vs +4 (script).
    - Noviomagus: bestows 7000 (text) vs 6000 (script).
    - Castra: academy bestow 6000 (text), needs 7000, takes 6500.
    - Nuceria: two different tax/barracks rule texts exist. The shown one says 100 per extra barracks, which matches the script.
    - Londinium: "two mission posts = lose" is not scripted. The script destroys the extra posts.
    - Castra Regina: barracks / academy / mess hall need 75 workers in the model data. The text says 50.
    - Antiochia: the text says small temples give bad desirability. Model data also sets large temples 14 → −10
      and halves grand temple and Pantheon desirability (20 → 10). The text does not state this.
14. **Engine noise, not campaign bugs.** "Formula ID mismatch" and "Text ID mismatch" on every map: upstream saves N−1 entries under
    an N header. It is benign. Exporter writes `check_formulas` with a duplicate `formula` attribute (Antiochia). It is cosmetic.

---

## 6. Ranking: complication vs challenge quality

Complication = layers active × dependency depth × rule count. Quality = P1–P6 above, minus defects.

| Map | Complication | Challenge quality | Why |
|-----|-----|-----|-----|
| Londinium | very high | high | Branching mission-post choices, fragmented land, adaptive invasions, clear tracker. Risk: small-army strategy avoids most waves. |
| Marcianopolis | very high | medium | Trade-volume goal is new and tracked. Native ring holds the best land; 20k pop goal. Will not load in current build; theft bug; −5/day zone penalty. |
| Antiochia | high | high | Religion score is a real optimization, visible in the HUD. Hand grenade costs 100,000. |
| Castra Regina | high | medium-low | Tower-upkeep limes is an excellent idea. Three bestow bugs damage it. |
| Noviomagus | high | medium | Swamp reclamation is the strongest geography puzzle. Teutoburg is unannounced. Key hint message is never shown. |
| Palmyra | high | medium | Four permanent choices are the cleanest decisions in the campaign. Instant-loss penalty is harsh. Patrician rule leak. |
| Complutum | high | high | Deepest dependency chain. Each task is shown. The marble side quest is optional with a clear cost. |
| Cyrene | medium | high | Silphium chain is elegant. Small map. 20 large temples at double labor is the real cost. |
| Narbo Martius | medium | medium (WIP) | Residence choice is good. Governor House bug breaks one branch. |
| Aquileia | medium | medium | Mostly volume (32,000 food). Good overlap of plague, waves, and distant battles. |
| Gesoriacum | medium | low-medium | Strong theme. The cap does not bind, so the core task is optional. 45-year time limit is the real pressure. |
| Leptis Magna | low-medium | medium | Route-opening chain (≈42,500 dn) gates all beautification. Three dead formulas make it easier than intended. |
| Nuceria | low-medium | medium | Mountain-pass puzzle is good. 500,000 treasury for favor is a grind. |

**Main gap between the two axes:** the most complicated maps are not always the best challenges. Londinium, Antiochia,
and Complutum convert complication into decisions. Castra Regina and Marcianopolis have equal complication, but defects
or harsh penalties turn part of it into frustration.

---

## 7. Recipe for a hard and fair map (from this campaign)

1. Pick one geography problem and make it the main task (pass, swamp, fragmented villages).
2. Put one rating cap below the win target. Tie it to that task. Check the cap number against the win number.
3. Add one custom economy rule that changes what is valuable (silphium, tower upkeep, binary resource choice).
4. Give one or two permanent choices with real trade-offs. Make a wrong choice expensive, not fatal.
5. Show every task in a visible variable line with a counter.
6. Scale military by time, and release new waves only when the map is clear.
7. Test each formula: use `{a,b}` for ranges. Re-open the map and check that no formula exports as `Error`.
8. Diff the briefing numbers against the script numbers before release.
