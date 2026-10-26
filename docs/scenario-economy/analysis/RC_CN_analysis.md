# Terrain, economy and map-maker tools: Reconquered, Conquering Numidia and All Roads Lead to Rome

Scope: 35 maps. These are the 20 Reconquered missions, the 2 Conquering Numidia missions and the 13 All Roads Lead to Rome (ARLR) maps. For the 6 Reconquered missions that the campaign starts from a save (RC08, RC10, RC11, RC14, RC17, RC19), the data comes from the `.svx` file that `Settings.xml` names, not from the `.mapx` file.

Method: a headless dumper links against Augustus `dae1899` (upstream HEAD, 2026-10-24). It loads every map with the engine's own loader. It measures terrain with the engine's routing rules, exports all events and messages, and prints trade routes, prices, requests, invasions and forbidden buildings. The dumper and scripts are in `../tools/`. The raw per-map output is not in the repository; `../tools/run3.sh` makes it again. The annotated map images are `images/reconquered_1-12.png` (RC01–RC12) and `images/reconquered_13-20_numidia.png` (RC13–RC20, CN01, CN02). Colors: blue is water, dark green is forest, grey is rock, brown lines are cliffs, light green is meadow and dark brown lines are roads. Red squares are invasion points, magenta is the entry point, cyan is the exit point and white is the measured center.

Limits:
- The "center" is the tile with the most open space in the largest flat region. It is a reference point, not the place where a player builds.
- Choke width is the width of the widest path from an invasion point to the center, in tiles. A value of 1 means that all paths pass through a gap of one tile.
- Export capacity is an upper limit. It assumes that every route is open and that every quota is filled at the start price. It ignores land-trade policies and caravanserai bonuses.
- On Londinium (save), Caesarea, Tingis and Damascus the center is next to the map edge where invasion points are. The "Nearest invasion→center" column therefore does not measure exposure on these maps. The report uses the point count and the choke widths instead.
- The "after quota events" column applies route-amount events and demand changes in file order, not in date order.
- No map was played. All claims come from map data and engine source.

---

## 1. Short answer

**Terrain.** Map size and the amount of free land do not make a map hard. Usable land is 52–78% on every map. Nine terrain patterns make maps hard:

1. The land is split into parts.
2. Cliffs leave only a few ramps to cross.
3. Buildable land is far from water.
4. A required resource site, such as meadow, rock or water for clay, is missing.
5. Forest covers the start area.
6. Forest blocks enemies, so clearing it opens invasion paths.
7. Invasion zones are on a separate bank, so the player decides with bridges whether enemies can reach the city.
8. Many invasion points arrive over approaches that are too wide to wall.
9. Native villages are next to the best building land.

The strongest maps combine two or three of these patterns with a script that changes them. Examples: Damascus has water rights that cost 5000 denarii. Lindum clears native villages when houses reach marked areas. Quiza has a coastal flood zone that a lighthouse removes.

**Economy.** Trade limits income more than tax does. Tax gives 0.4–1.7 denarii per plebeian per year at 7%. Trade quotas allow 4–9 denarii per citizen per year on 28 of 35 maps. Reconquered makes this cap tight in three ways:
- A month-1 event resets 8–16 prices on 19 of 20 missions. It lowers the sell price of the main exports and raises the buy price of imports the map cannot produce.
- Route permits cost 2–4 times the start funds.
- Monthly drains apply: upkeep events, tax caps, wage rises and requests.

Conquering Numidia uses the same tools with stronger values. Igilgili marble costs 3000 denarii, and favor is held at 70 until the patron Grand Temple stands.

**Tools.** The engine has 33 event conditions and 56 event actions. The three campaigns use 21 conditions and 45 actions. Reconquered relies on a small, fixed set: allowed buildings, custom messages, price set, variables and requests. ARLR uses the widest set. Numidia uses status variables as state machines and building-count checks as choices.

**Defects.** The most serious defect is in Igilgili (CN01). The Oracle reward says gold costs 50 denarii, but the engine sets gold to 2/0. The cause is how `trade_price_set` works.

---

## 2. Terrain patterns

Engine rules that the metrics use:
- A reservoir fills only when water is within one tile of it (`src/map/water_supply.c:201`).
- A farm needs meadow within one tile of its footprint. A quarry or mine needs rock within one tile. A clay pit needs water or beach within 3 tiles (`src/building/construction.c:1400-1433`).
- Walkers and enemies pass ramps, roads and beach. Cliffs, rock, water and marsh block them. Trees and shrubs block enemies (`src/map/routing_terrain.c:110-245`, `TERRAIN_IMPASSABLE_ENEMY` in `src/map/terrain.h`).
- Marsh gives −3 desirability in range 3 and +5 sickness to buildings within 3 tiles (`src/map/desirability.c:190`, `src/city/health.c:370`). No map in the three campaigns has marsh or beach tiles.

### 2.1 Metrics per map

| Map | Size | Usable % | Largest region % | Walk-connected % | Levels / ramps | Open square now→cleared | Water dist median / p90 | Land ≤10 from water % | Meadow | Rock sites | Entry→exit | Invasion pts reach (trees / cut) | Nearest invasion→center | Widest choke (trees / cut) | Natives→center |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| RC01 Ostia | 40 | 78.0 | 86.7 | 86.7 | 1 / 0 | 5→13 | 6 / 10 | 95.3 | 91 | 173 | 41 | 0/0 / 0/0 | - | 0 / 0 | - |
| RC02 Brundisium | 60 | 76.1 | 82.1 | 85.9 | 2 / 4 | 7→15 | 10 / 18 | 52.7 | 260 | 468 | 62 | 0/0 / 0/0 | - | 0 / 0 | - |
| RC03 Capua | 80 | 72.3 | 55.0 | 73.8 | 2 / 8 | 7→11 | 6 / 12 | 82.5 | 371 | 573 | 93 | 0/0 / 0/0 | - | 0 / 0 | - |
| RC04 Tarentum | 80 | 75.8 | 84.0 | 84.0 | 1 / 0 | 9→19 | 9 / 27 | 58.2 | 159 | 625 | 76 | 3/3 / 3/3 | 27 | 1 / 17 | - |
| RC05 Tarraco | 80 | 66.3 | 21.0 | 53.0 | 3 / 40 | 9→13 | 4 / 8 | 99.0 | 0 | 62 | 106 | 0/0 / 0/0 | - | 0 / 0 | - |
| RC06 Syracusae | 100 | 71.9 | 45.9 | 84.9 | 3 / 28 | 13→13 | 13 / 27 | 40.3 | 227 | 1249 | 158 | 3/3 / 3/3 | 29 | 5 / 11 | - |
| RC07 Miletus | 100 | 60.7 | 85.9 | 91.2 | 3 / 20 | 9→15 | 16 / 37 | 37.6 | 218 | 896 | 84 | 2/2 / 2/2 | 80 | 3 / 7 | - |
| RC08 Mediolanum (save) | 160 | 67.3 | 66.4 | 78.7 | 4 / 80 | 13→19 | 13 / 60 | 41.7 | 335 | 1041 | 204 | 8/8 / 8/8 | 40 | 3 / 13 | - |
| RC09 Lugdunum | 100 | 66.7 | 23.8 | 46.8 | 3 / 20 | 9→13 | 11 / 19 | 49.2 | 470 | 663 | 112 | no invasions | - | - | 77 |
| RC10 Carthago (save) | 120 | 70.3 | 84.1 | 94.6 | 3 / 40 | 11→15 | 10 / 23 | 52.0 | 329 | 1082 | 186 | 0/6 / 6/6 | 77 (cut) | 0 / 3 | 10 |
| RC11 Tarsus (save) | 120 | 63.6 | 38.0 | 89.0 | 4 / 56 | 13→13 | 10 / 35 | 51.4 | 0 | 233 | 185 | 2/2 / 2/2 | 91 | 1 / 1 | - |
| RC12 Tingis | 120 | 73.5 | 47.0 | 80.1 | 3 / 76 | 11→15 | 12 / 24 | 44.7 | 534 | 505 | 138 | 4/4 / 4/4 | 10 | 3 / 11 | - |
| RC13 Valencia | 160 | 58.7 | 46.5 | 83.7 | 5 / 84 | 9→17 | 10 / 22 | 53.4 | 1432 | 2054 | 200 | 3/3 / 3/3 | 29 | 1 / 11 | - |
| RC14 Lutetia (save) | 160 | 69.7 | 54.5 | 93.9 | 4 / 56 | 9→13 | 9 / 27 | 53.8 | 1096 | 2228 | 228 | 7/7 / 7/7 | 86 | 1 / 5 | 39 |
| RC15 Caesarea | 120 | 73.8 | 83.0 | 90.7 | 3 / 12 | 13→15 | 11 / 21 | 48.1 | 228 | 1219 | 124 | 8/8 / 8/8 | 9 | 3 / 13 | - |
| RC16 Damascus | 120 | 76.9 | 90.4 | 98.6 | 3 / 28 | 13→13 | 18 / 51 | 26.9 | 581 | 2095 | 71 | 5/5 / 5/5 | 13 | 3 / 13 | 6 |
| RC17 Londinium (save) | 160 | 75.2 | 49.8 | 83.6 | 4 / 100 | 9→15 | 12 / 29 | 45.3 | 525 | 1599 | 232 | 8/8 / 8/8 | 7 | 1 / 15 | 10 |
| RC18 Sarmizegetusa | 120 | 73.6 | 61.3 | 98.4 | 3 / 68 | 11→13 | 15 / 34 | 33.7 | 818 | 1900 | 156 | 4/4 / 4/4 | 24 | 3 / 11 | 43 |
| RC19 Lindum (save) | 160 | 73.0 | 35.3 | 74.8 | 4 / 116 | 11→13 | 22 / 49 | 26.1 | 561 | 1481 | 168 | 8/8 / 8/8 | 76 | 1 / 5 | 34 |
| RC20 Massilia | 160 | 58.3 | 38.4 | 80.3 | 3 / 76 | 13→15 | 15 / 33 | 34.4 | 0 | 1678 | 143 | 6/6 / 6/6 | 66 | 3 / 5 | - |
| CN01 Igilgili | 100 | 60.8 | 75.2 | 90.7 | 6 / 36 | 7→13 | 18 / 40 | 21.9 | 159 | 230 | 85 | 3/3 / 3/3 | 24 | 1 / 5 | 54 |
| CN02 Quiza | 120 | 51.6 | 52.2 | 69.0 | 6 / 56 | 7→13 | 10 / 18 | 54.3 | 0 | 0 | 133 | 5/5 / 5/5 | 61 | 1 / 3 | 19 |
| AR Aquileia | 160 | 72.0 | 35.4 | 38.8 | 5 / 84 | 11→13 | 3 / 6 | 99.1 | 2985 | 333 | 167 | 0/4 / 0/4 | - | 0 / 0 | - |
| AR Antiochia | 160 | 76.7 | 31.5 | 60.9 | 5 / 76 | 9→15 | 30 / 64 | 18.2 | 0 | 928 | 203 | 2/2 / 2/2 | 12 | 1 / 13 | 24 |
| AR Castra Regina | 160 | 72.2 | 46.3 | 86.1 | 6 / 128 | 9→21 | 16 / 32 | 32.1 | 313 | 2602 | 175 | 4/4 / 4/4 | 49 | 1 / 3 | 25 |
| AR Complutum | 160 | 73.3 | 9.4 | 41.5 | 6 / 168 | 7→13 | 13 / 26 | 38.9 | 1785 | 457 | 292 | 0/2 / 2/2 | 98 (cut) | 0 / 1 | - |
| AR Cyrene | 120 | 66.1 | 57.6 | 94.2 | 5 / 56 | 13→15 | 13 / 26 | 38.7 | 311 | 420 | 215 | 3/3 / 3/3 | 42 | 3 / 5 | 66 |
| AR Gesoriacum | 100 | 66.6 | 55.8 | 96.6 | 4 / 48 | 11→17 | 26 / 48 | 19.2 | 272 | 275 | 97 | 1/1 / 1/1 | 82 | 1 / 5 | - |
| AR Leptis Magna | 160 | 53.7 | 60.0 | 97.8 | 5 / 116 | 17→19 | 14 / 37 | 39.2 | 537 | 428 | 279 | 2/2 / 2/2 | 177 | 1 / 1 | 78 |
| AR Londinium | 160 | 71.8 | 16.1 | 41.6 | 4 / 172 | 9→17 | 9 / 21 | 56.6 | 171 | 264 | none | 2/8 / 2/8 | 126 | 1 / 1 | 51 |
| AR Marcianopolis | 160 | 72.2 | 38.8 | 83.2 | 6 / 200 | 5→19 | 12 / 29 | 41.2 | 715 | 977 | 288 | 0/1 / 1/1 | 219 (cut) | 0 / 1 | 60 |
| AR Narbo Martius | 120 | 63.6 | 43.5 | 98.1 | 5 / 48 | 9→11 | 16 / 31 | 34.6 | 1037 | 156 | 155 | 3/3 / 3/3 | 147 | 1 / 1 | 135 |
| AR Noviomagus | 160 | 58.8 | 42.5 | 42.5 | 3 / 0 | 9→17 | 2 / 4 | 100.0 | 524 | 538 | 66 | 0/3 / 3/3 | 70 (cut) | 0 / 3 | 11 |
| AR Nuceria | 160 | 69.9 | 32.6 | 46.0 | 6 / 188 | 11→27 | 12 / 22 | 44.7 | 1179 | 662 | none | 0/1 / 0/1 | - | 0 / 0 | 88 |
| AR Palmyra | 160 | 73.3 | 22.8 | 38.2 | 6 / 400 | 9→19 | 18 / 39 | 28.4 | 276 | 1103 | 222 | 0/2 / 2/2 | 79 (cut) | 0 / 3 | 15 |

Column notes:
- "Largest region" is the largest flat area that is not split by cliffs or water, as a share of usable land.
- "Walk-connected" is the usable land that a walker can reach from the center over ramps and existing roads.
- "Open square" is the side of the largest square of free land. "Now" counts forest as blocked. "Cleared" counts forest as removed.
- "Entry→exit" is the walk distance in tiles. "None" means that no land path exists without a new bridge.

### 2.2 Pattern catalog

**T1. Split land.** The largest flat region holds less than a quarter of the usable land on Complutum (9%), ARLR Londinium (16%), Tarraco (21%), Palmyra (23%) and Lugdunum (24%). Each housing block must then have its own services, and the player must build roads to connect the parts. The baseline maps are Damascus (90%), Ostia (87%) and Miletus (86%).

**T2. Cliffs with few ramps.** A road crosses a cliff only on a ramp tile. Palmyra has 400 ramp tiles over 6 height levels, Marcianopolis 200 and Nuceria 188. Many ramps over many levels mean many small terraces with a fixed number of crossings. Ostia, Tarentum and Noviomagus have none.

**T3. Land far from water.** A reservoir needs water within one tile. Distance from water is therefore the length of aqueduct that the player must build and pay for. The hardest maps are ARLR Antiochia (median 30 tiles, 18% of land within 10 tiles of water), Lindum (22, 26%), Damascus (18, 27%) and Igilgili (18, 22%). Damascus has no water on its main region at all (coast = 0 tiles). Its event E4 sells the water rights to the native oases for 5000 denarii, so the terrain limit and the script act together. The baseline maps are Noviomagus (2), Aquileia (3) and Tarraco (4).

**T4. A missing resource site.** No meadow means no farms. Meadow is 0 on Tarraco, Tarsus, Massilia, Quiza and Antiochia. The maps use this together with their scripts:
- Tarsus forbids every farm.
- Caesarea has 228 meadow tiles but forbids farms. Its food comes from a caravanserai subsidy (E6: 64 fruit every 5 months for 1 favor).
- Quiza has 0 meadow and 0 rock. All farms and the dock start forbidden, and food comes from fish only.
- Igilgili forbids all farms, the marble quarry, the iron mine, the timber yard and the clay pit. Stone and sand are its only raw exports.

A map can lock a resource by terrain or by rule. The terrain lock is permanent. The rule lock can open later, for example through `change_resource_produced` (Tarentum wheat after a Ceres temple, Lugdunum vines after a Ceres Grand Temple, Sarmizegetusa fish after a Ceres Grand Temple).

**T5. Forest at the start.** The open square at the start is only 5–7 tiles on Ostia, Brundisium, Capua, Igilgili, Quiza, Complutum and Marcianopolis. Clearing raises it to 13–19 tiles. The player must pay for clearing before the first large block fits. This cost is small, but it slows the first years.

**T6. Forest as a wall against enemies.** Enemies cannot walk through trees. On five maps no invasion point reaches the center until the player clears forest:
- Carthago (save): 0 of 6 points reach the center with the forest, 6 of 6 without it.
- ARLR Noviomagus: 0 of 3, then 3 of 3.
- ARLR Palmyra: 0 of 2, then 2 of 2.
- ARLR Complutum: 0 of 2, then 2 of 2.
- ARLR Marcianopolis: 0 of 1, then 1 of 1.

Timber and building land therefore cost defence. No message on these maps states this rule. It is the strongest hidden terrain mechanic in the data.

**T7. Invasion zones on a separate bank.** Some invasion points are on land that no path connects to the main region:
- ARLR Aquileia: 4 points on a north bank of 5848 tiles, with 11 scheduled invasions.
- ARLR Nuceria: 1 point on a zone of 2596 tiles, with 10 scheduled invasions.
- ARLR Londinium: 6 of 8 points on a zone of 6001 tiles.

The invaders reach the city only if the player builds a bridge or builds on their bank. The player therefore chooses the exposure. This is a good design device when the map tells the player about it. These maps do not.

**T8. Exposure: number and width of the approaches.** Caesarea, Mediolanum, Londinium (save) and Lindum each have 8 invasion points. With forest cleared, the widest approach is 13–17 tiles on Tarentum, Londinium, Caesarea, Damascus and Mediolanum. A wall line cannot close approaches of that width cheaply. The opposite case is Tarsus, Narbo Martius and Leptis Magna. There the approaches are 1 tile wide and 91–177 tiles long, so one gatehouse or fort holds them.

**T9. Natives next to the city.** Native buildings are 6 walk tiles from the center on Damascus and 10 on Carthago and Londinium (save). Natives block the best land until the player builds a mission post or a script removes them. The scripts in these campaigns use native removal as a reward:
- Sarmizegetusa E3: 10 small mausoleums.
- Lindum E6–E8: insulae inside marked areas.
- Quiza E21–E24: a storm surge after a Nymphaeum.
- Carthago E21: crops removed at month 1.
- Igilgili E20: a small mausoleum in the stone circle.

**T10. Script zones on the terrain.** Some maps use `building_force_collapse` and `building_count_area` rectangles as invisible zones:
- Quiza E22 collapses every reservoir in six coastal rectangles each month for the whole mission. E25 collapses clay pits and workshops in the same rectangles until a lighthouse stands. Together they work as a flood zone. 195 reservoir sites with water are left outside the rectangles, so the later reservoir unlock still works.
- Igilgili E19–E22 and Lindum E6–E8 test for a building inside a rectangle.

`change_terrain` is used only in ARLR (48 actions on 5 maps). `terrain_in_area` is never used.

**Combined effect.** The maps that the analysis rates hardest in terrain stack 3 or more patterns:
- ARLR Palmyra: T1, T2, T3 and T6.
- ARLR Complutum: T1, T2 and T6.
- Lindum: T1, T3, T8 and T9, with a script on T9.
- Damascus: T3, T8 and T9, with scripts on T3 and T9.
- Quiza: T4, T5 and T10, with a script on T10.

Reconquered missions 1–7 use at most one pattern each. This is a deliberate learning curve.

---

## 3. Economy

### 3.1 Trade caps income

Tax income per year is about 0.06 × population × house tax multiplier × tax rate in percent (`src/city/finance.c:240-262`). House multipliers are 1–4 for plebeian houses and 9–16 for patrician houses. At 7%, a plebeian pays about 0.4–1.7 denarii per year and a patrician 3.8–6.7.

Export income cannot be more than the sum, over all routes, of each quota (units per year) times the sell price. The table gives this cap at the prices that apply after the start events.

| Map | Pop goal | Start funds | Routes | Sum of route open costs | Export cap at start prices (dn/yr) | Export cap after quota events | Cap per citizen | Requests incl. templates (denarii from dated requests) |
|---|---|---|---|---|---|---|---|---|
| RC01 Ostia | 1250 | 6600 | 2 | 800 | 6510 | 9810 | 5.21 → 7.85 | 14 (2750) |
| RC02 Brundisium | 2400 | 8500 | 5 | 4100 | 26270 | 28745 | 10.95 → 11.98 | 11 (1500) |
| RC03 Capua | 4500 | 9500 | 5 | 5300 | 23020 | 24420 | 5.12 → 5.43 | 12 (4500) |
| RC04 Tarentum | 4500 | 10000 | 5 | 8050 | 34300 | 34300 | 7.62 → 7.62 | 8 (500) |
| RC05 Tarraco | 5000 | 9000 | 5 | 7600 | 24415 | 24415 | 4.88 → 4.88 | 12 (600) |
| RC06 Syracusae | 7000 | 10000 | 5 | 8500 | 35960 | 35960 | 5.14 → 5.14 | 11 (2000) |
| RC07 Miletus | 6500 | 9500 | 5 | 8325 | 33970 | 38366 | 5.23 → 5.90 | 10 (1250) |
| RC08 Mediolanum (save) | 8000 | 12500 | 6 | 31000 | 47790 | 54310 | 5.97 → 6.79 | 15 (4000) |
| RC09 Lugdunum | 8000 | 9500 | 6 | 13525 | 54305 | 54305 | 6.79 → 6.79 | 13 (3750) |
| RC10 Carthago (save) | 8000 | 12500 | 7 | 39750 | 41671 | 44775 | 5.21 → 5.60 | 12 (5500) |
| RC11 Tarsus (save) | 8250 | 14500 | 7 | 26600 | 56800 | 68920 | 6.88 → 8.35 | 10 (0) |
| RC12 Tingis | 11000 | 10000 | 5 | 10000 | 48620 | 48620 | 4.42 → 4.42 | 17 (6000) |
| RC13 Valencia | 12000 | 10000 | 10 | 20260 | 157300 | 157300 | 13.11 → 13.11 | 20 (9300) |
| RC14 Lutetia (save) | 12000 | 12000 | 8 | 25850 | 70205 | 76970 | 5.85 → 6.41 | 20 (8750) |
| RC15 Caesarea | 8500 | 16000 | 7 | 20550 | 66490 | 67810 | 7.82 → 7.98 | 13 (2250) |
| RC16 Damascus | 12500 | 10000 | 8 | 46275 | 78302 | 79758 | 6.26 → 6.38 | 20 (13250) |
| RC17 Londinium (save) | 17500 | 12500 | 8 | 24175 | 122835 | 130475 | 7.02 → 7.46 | 20 (9750) |
| RC18 Sarmizegetusa | 11000 | 18500 | 5 | 16450 | 43430 | 36910 | 3.95 → 3.36 | 20 (14750) |
| RC19 Lindum (save) | 16000 | 16000 | 9 | 32950 | 92780 | 118245 | 5.80 → 7.39 | 20 (8750) |
| RC20 Massilia | 18000 | 14500 | 10 | 35400 | 114812 | 127307 | 6.38 → 7.07 | 20 (11500) |
| CN01 Igilgili | 8000 | 5000 | 12 | 20150 | 55872 | 58512 | 6.98 → 7.31 | 13 (3500) |
| CN02 Quiza | 10000 | 9000 | 12 | 31800 | 59680 | 61840 | 5.97 → 6.18 | 14 (4500) |
| AR Antiochia | 18000 | 15000 | 11 | 72200 | 113683 | 128628 | 6.32 → 7.15 | 18 (27000) |
| AR Aquileia | 12000 | 11000 | 9 | 35200 | 78740 | 81690 | 6.56 → 6.81 | 8 (0) |
| AR Castra Regina | 16000 | 11000 | 8 | 19050 | 144430 | 149430 | 9.03 → 9.34 | 15 (13000) |
| AR Complutum | 22000 | 10000 | 10 | 22950 | 154200 | 167950 | 7.01 → 7.63 | 11 (20000) |
| AR Cyrene | 10000 | 10500 | 7 | 17750 | 45615 | 43600 | 4.56 → 4.36 | 21 (5000) |
| AR Gesoriacum | 6000 | 8000 | 5 | 6200 | 14045 | 22375 | 2.34 → 3.73 | 6 (0) |
| AR Leptis Magna | 17000 | 10000 | 11 | 46250 | 134065 | 148040 | 7.89 → 8.71 | 9 (0) |
| AR Londinium | 14000 | 18000 | 5 | 6000 | 39250 | 69300 | 2.80 → 4.95 | 8 (0) |
| AR Marcianopolis | 20000 | 12500 | 21 | 178800 | 1042180 | 1042180 | 52.11 → 52.11 | 21 (33500) |
| AR Narbo Martius | 12000 | 10500 | 9 | 26450 | 90460 | 102010 | 7.54 → 8.50 | 9 (0) |
| AR Noviomagus | 18000 | 8500 | 5 | 9800 | 26935 | 33830 | 1.50 → 1.88 | 21 (0) |
| AR Nuceria | 16000 | 11500 | 16 | 123200 | 98245 | 95545 | 6.14 → 5.97 | 20 (0) |
| AR Palmyra | 18000 | 14000 | 6 | 32000 | 55792 | 183872 | 3.10 → 10.22 | 12 (2500) |

What the table shows:
- On 28 of 35 maps the cap is 4–9 denarii per citizen per year. That is several times the tax that one plebeian pays. The player cannot fix a weak economy with more housing alone. The player must open the right routes and fill the quotas.
- The tightest caps are ARLR Noviomagus (1.5), ARLR Gesoriacum (2.3), ARLR Londinium (2.8), ARLR Palmyra (3.1) and Sarmizegetusa (3.95). On these maps tax, local services and event income carry the budget.
- Sarmizegetusa and ARLR Cyrene have lower caps after events than before. Events remove quotas, so the economy becomes tighter later.
- ARLR Palmyra rises from 3.1 to 10.2 after events. Its four either-or resource choices each open large quotas.
- Valencia (13.1) and Brundisium (11.0) are the open trade maps of Reconquered. ARLR Marcianopolis (52) is a pure trade map with 21 routes and quotas of 80–140.

**Route permits cost more than the start funds.** Opening every route costs 2–4 times the start funds on Mediolanum (31,000 against 12,500), Carthago (39,750 against 12,500), Damascus (46,275 against 10,000) and Igilgili (20,150 against 5000). The player must choose the order in which to open routes. Scripts change permit costs as rewards or penalties:
- Mediolanum E7: trade league membership.
- Carthago E3 and E10: Utica costs 100 during the civil-war choice, then 25,000.
- Damascus: Far East costs 18,000.

### 3.2 Prices as a constraint

Prices are not stored in `.mapx` files. Every scenario starts with the engine default prices (`src/empire/trade_prices.c:106`). A map changes prices in three ways:
1. Scheduled price changes, which add the same amount to the buy and sell price (`src/scenario/price_change.c:63-68`).
2. Event actions.
3. A start save. Mediolanum and Carthago carry prices that their month-1 events had already set.

**The Reconquered start-price event.** On 19 of 20 missions (all except Ostia) an event at month 1 runs 8–16 `trade_price_set` actions. In the Mediolanum and Carthago saves this event has already run. The pattern is the same on every map:
- **The sell price of the map's main exports goes down.** Marble falls from 140 to 90–110 on Brundisium, Tarraco, Mediolanum and Valencia. Pottery falls from 140 to 85–105. Furniture falls from 150 to 83–110. Weapons fall from 180 to 94–130. Bricks fall from 150 to 76–100.
- **The buy price of goods that the terrain cannot supply goes up:**
  - Damascus: clay 340, bricks 750 and sand 128. The map has no water near its land, so clay pits are almost impossible (T3).
  - Tingis: marble 960 and stone 340. The map has no local quarry.
  - Londinium: marble 870, oil 630 and vines 267.
  - Massilia: gold 2500 and stone 275.
  - Tarsus: wine 800 and oil 360.
  - Lindum: marble 650 and gold 875.
- **The workshop margin becomes small.** At default prices, pottery and furniture earn 100 denarii per unit over the raw material, and bricks 115. After the event, pottery earns 35–65 (for example Brundisium 105 against 40 and Londinium 85 against 49), furniture 27–54 and bricks 40–55. On Damascus, pottery sells for 160 but imported clay costs 340, so pottery from imported clay loses 180 per unit. A workshop makes 4.8 units per year, so one pottery or furniture workshop earns about 150–300 denarii per year, against about 480 at default prices.

The price event therefore uses prices as a second terrain layer. A good that the terrain cannot supply becomes very expensive. A good that the terrain supplies well becomes cheap to sell.

**Engine semantics of `trade_price_set`.** This action does not set one price. It computes the difference between the target and the current buy price (with `set_buy_price=true`) or sell price (with `false`). It then adds that difference to both prices (`src/scenario/event/action_types.c:435-466`). If a price drop would bring the sell price to 0 or below, the engine sets the prices to 2/0 (`src/empire/trade_prices.c:148-161`). The actions `trade_set_buy_price_only` and `trade_set_sell_price_only` set one price. Reconquered uses `trade_price_set` 217 times and the `_only` actions 0 times. Usually this keeps the default spread between buy and sell, so it does no harm. In Igilgili it breaks the reward (§5, D1).

**Price events as rewards and penalties:**
- Tingis E6 lowers marble to 360 when favor reaches 90.
- Lindum E25 lowers furniture, weapons and pottery when the player selects the economic path.
- Massilia E20 raises marble by 65 when a forum is built, and E21 lowers pottery and wine at 20,000 denarii.
- Igilgili E23 lowers gold by 100 each year.
- Quiza E54 lowers fish by 1 each year for 15 years, and E66 lowers oil by 200 on the "against Rome" path.

### 3.3 Fixed drains and caps

| Device | Maps |
|---|---|
| Subsidy of 100 denarii per month until prosperity 10. Workshops stay locked until prosperity 10. | RC02–RC20 (all except Ostia) |
| Workshops locked until prosperity 15 | CN01, CN02 |
| Monthly upkeep per building count | Miletus: −25 per 16 soldiers, −75 per library or academy. Massilia: −30 per 5 small temples, −150 statues, −150 second wine route. |
| Corruption drain that grows with population | Valencia E15–E17. The mint reduces it but does not stop it, and the message says this. |
| Tax limit | Londinium E15: tax ≥5% gives −5 favor and resets the tax to 4%. Lutetia E15: the tax resets to 5% every month. Igilgili E24 (Nymphaeum path): the tax is capped at 5%. |
| Penalty for a forbidden count | Damascus: 2 forums give −20 favor and −1500 each year. Tarsus: more than 10 small temples give −20 favor and −1000 each year. Valencia: −2 favor per forum per year. |
| Rome wage rises tied to population | 23 maps. Reconquered sets wages to 33–45 by population steps. |
| Requests started by events from template requests in years 997–999 | 27 maps |
| Timber consumed by iron mines | Tarraco E3–E7 |
| Spoilage | Miletus E9: −8 fish per month after the first 32 fish |

---

## 4. Inventory of map-maker tools

### 4.1 Scenario settings (editor, no events)

| Tool | What it controls | Example of use in these campaigns |
|---|---|---|
| Terrain painting | Land, water, forest, rock, meadow, cliffs, ramps, marsh, beach | All patterns in §2. Marsh and beach are unused. |
| Entry, exit and river points | Where immigrants, traders and boats enter | The Lugdunum entry is cut from the main region. |
| Invasion, herd and fish points | Where enemies, wolves and fish appear | Quiza has 8 fish points and no herds. |
| Pre-placed buildings | Native huts, meeting houses, crops, roads | Lindum has 72 huts and 98 crops. |
| Start save (`.svx`) instead of `.mapx` | Pre-built warehouses, statues and monuments, stock, prices, savings, events already run | Mediolanum, Carthago, Tarsus, Lutetia, Londinium, Lindum |
| Win criteria | Population, culture, prosperity, peace, favor, time limit, survival | Igilgili requires peace 100 and favor 100. |
| Start funds, rank, salary, savings, rescue loan, Rome wheat | The opening budget | The Quiza campaign demotes the player to citizen, with salary 100 and no rescue loan. |
| Allowed buildings | Per-building ban list | 26–41 bans per map in ARLR |
| Local resources | Which raw materials the city can produce | Igilgili: olives, sand and stone only |
| Custom empire (XML) | Map of trade cities | Both Numidia missions |
| Trade routes | Partner, land or sea, permit cost, quotas, future cities | §3.1 |
| Scheduled invasions | Year, month, size, type, point, repeat | 20 per Reconquered mission (14 on Caesarea) |
| Scheduled requests | Goods or denarii, deadline, favor, repeat | Template requests at year 997–999 are never reached by time. Events start them. |
| Demand changes | Quota change on a route at a date | 13 on Quiza |
| Price changes | Price rise or fall at a date | 67 on ARLR Marcianopolis |
| Random events | Sea or land trade problems, wage changes, bad water, mine collapse, clay pit flood, flotsam | Bad water on Miletus, Caesarea, Londinium, Lindum and Quiza |
| Earthquake, gladiator revolt, emperor change | Fixed disasters | The Tarentum earthquake point |
| Custom messages and custom variables | Briefings, quest text, visible counters | ARLR shows counters on 11 maps. Reconquered shows none. |

### 4.2 Event conditions (33 in the engine, 21 used)

Count of uses per campaign (ARLR / Reconquered / Numidia):

| Condition | AR | RC | CN | Use |
|---|---|---|---|---|
| variable_check | 294 | 100 | 52 | Quest state, choices, timers |
| time | 140 | 140 | 15 | Start events, delays, schedules |
| building_count_active | 65 | 92 | 42 | Quest goals, upkeep per building |
| city_population | 30 | 69 | 12 | Unlocks and wage steps |
| stats_prosperity | 38 | 41 | 2 | The Reconquered subsidy and workshop gate |
| building_count_area | 72 | 4 | 4 | Zones (T10) |
| building_count_any | 48 | 6 | 15 | Grand Temple choice checks |
| resource_stored_count | 25 | 28 | 6 | Deliveries "stockpile X and it is sent" |
| count_own_troops | 20 | 24 | 5 | Military funding, reactive invasions |
| stats_favor | 18 | 1 | 2 | Favor caps and rewards |
| trade_route_open | 11 | 7 | 3 | Choices by route (Carthago Utica) |
| savings | 19 | 0 | 0 | Bestows bought with personal savings |
| check_formulas | 16 | 0 | 0 | Compound checks (Leptis) |
| money | 4 | 9 | 0 | Rewards at a treasury level |
| tax_rate | 10 | 1 | 1 | Tax caps |
| rome_wages | 9 | 0 | 0 | |
| trade_sell_price | 3 | 0 | 1 | Price floor (Igilgili gold) |
| resource_storage_available | 4 | 0 | 0 | |
| stats_culture | 4 | 0 | 0 | |
| stats_peace | 1 | 0 | 0 | |
| (no condition) | 26 | 0 | 4 | Start events |

Never used: `difficulty`, `population_unemployed`, `stats_health`, `request_is_ongoing`, `trade_route_price`, `terrain_in_area`, `enemies_in_city`, `land_trade_problem_duration`, `sea_trade_problem_duration`, `months_since_last_festival`, `desirability_in_area`, `population_in_area`, `figures_in_area`.

### 4.3 Event actions (56 in the engine, 45 used)

| Action | AR | RC | CN | Use |
|---|---|---|---|---|
| change_allowed_buildings | 272 | 243 | 45 | Unlock chains |
| show_custom_message | 244 | 163 | 24 | Quest text |
| trade_price_set | 145 | 217 | 25 | Start prices, price rewards |
| change_variable | 176 | 66 | 39 | Quest state |
| change_monument_resources | 205 | 0 | 0 | Custom monument costs |
| building_force_collapse | 119 | 8 | 55 | Penalties, zones, native removal |
| change_resource_stockpiles | 61 | 59 | 12 | Deliveries, upkeep in goods, rewards |
| change_variable_visibility | 109 | 0 | 0 | On-screen counters |
| invasion_start_immediate | 67 | 33 | 7 | Reactive and late repeating invasions |
| money_add | 22 | 64 | 3 | Subsidy, upkeep, ransom |
| request_immediately_start | 16 | 56 | 7 | Repeating requests |
| variable_city_property | 76 | 0 | 0 | Read a city stat into a variable |
| trade_route_amount | 30 | 27 | 18 | Quota rewards and cuts |
| favor_add | 39 | 22 | 10 | Favor rewards, caps, penalties |
| trade_route_add_new_resource | 52 | 0 | 4 | New goods on a route |
| change_terrain | 48 | 0 | 0 | Terrain changed by a script |
| empire_map_convert_future_trade_city | 27 | 17 | 3 | New partners as rewards |
| change_rome_wages | 17 | 19 | 10 | Wage steps |
| change_resource_produced | 28 | 8 | 1 | Local resource unlocks |
| trade_price_adjust | 23 | 9 | 4 | Relative price changes |
| savings_add | 29 | 4 | 3 | Personal rewards |
| change_model_data | 26 | 0 | 0 | Building costs, workers, desirability |
| cause_blessing | 0 | 0 | 20 | Numidia: one blessing per 10 workshops or 10 wharves |
| tax_rate_set | 10 | 2 | 2 | Tax caps |
| change_rank | 13 | 0 | 0 | |
| change_city_rating | 9 | 3 | 0 | Rating locks and set values |
| change_trade_route_open_price | 7 | 4 | 0 | Permit rewards and penalties |
| change_pop_sentiment | 8 | 0 | 0 | |
| lose | 7 | 0 | 0 | |
| city_health | 4 | 2 | 0 | Plague (Miletus) |
| change_god_sentiment | 6 | 0 | 0 | |
| trade_problems_land / trade_problems_sea | 2 / 0 | 2 / 1 | 1 / 1 | Blockades, bandits |
| change_production_rate | 5 | 0 | 0 | |
| move_camera | 4 | 0 | 0 | |
| gladiator_revolt | 0 | 1 | 2 | |
| cause_major_curse | 3 | 0 | 0 | |
| trade_set_buy_price_only / trade_set_sell_price_only | 3 / 2 | 0 / 0 | 0 / 0 | Single-price set |
| change_immigration_percentage | 3 | 0 | 0 | |
| variable_formula | 2 | 0 | 0 | |
| send_standard_message, kill_walkers_in_area, send_city_warning | 1 each | 0 | 0 | |

Never used: `change_house_model_data`, `hide_trade_route`, `change_goal`, `rename_city`, `trade_route_set_open`, `change_resource_cost`, `change_climate`, `win`, `change_variable_color`, `cause_minor_curse`, `lock_trade_route`, `change_weather`.

### 4.4 Idioms that the authors build from these tools

| Idiom | How it works | Examples |
|---|---|---|
| Start event | An event with no condition, or with `time ≥ 1`, sets prices, stock and bans | Reconquered E-"time 1", Numidia E0 [Startpreise] |
| Gate | A ban plus an unlock event on a stat | Workshops at prosperity 10 (RC) or 15 (CN) |
| Delivery quest | `resource_stored_count ≥ N` then `change_resource_stockpiles −N` | Ostia drought, Brundisium elections, Lindum wall |
| Staged quest | A stage counter variable with x5 repeats per stage | Lindum Hadrian's Wall, 4 stages |
| Exclusive choice | A status variable is set by the first building or route, and other options give a penalty | Igilgili stone circle (4 options), Quiza Status 4/5/6, Lindum military or economic path, Carthago Utica, Lindum Neptune or Ceres |
| Rating or stat cap | A monthly event resets a value above a limit | Igilgili and Quiza favor at 70 until the patron Grand Temple. Londinium tax at 4%. |
| Timer | A repeat-x-N event counts months into a variable | Quiza MonthCounter, MonthCounterNatives, MonthCounterRome |
| Template requests | Requests in year 997–999 that only events start | 27 maps |
| Upkeep | Repeating `money_add` with negative values, conditioned on building counts | Miletus, Massilia |
| Zone | Force-collapse or area-count rectangles | Quiza coast, Igilgili circle, Lindum native areas |
| Reactive invasion | `count_own_troops` triggers attacks | Lindum military path, ARLR Londinium, ARLR Complutum |

---

## 5. Defects (verified in data and engine source)

| ID | Map | Defect | Evidence |
|---|---|---|---|
| D1 | CN01 Igilgili | The Oracle reward says "it is worth importing gold for 50 dn". E0 sets the gold buy price to 1000, so gold becomes 1000/900. E19 then sets the buy price to 50, which is a shift of −950. Because 900 ≤ 950, the engine sets gold to **2/0**. Gold becomes almost free, and the mint path earns much more than the author intended. | `action_types.c:435-466`, `trade_prices.c:154-156` |
| D2 | CN01 Igilgili | The Large Mausoleum message says that gold falls 50 denarii per year to 500. E23 lowers it 100 per year while the sell price is above 500. | E23 `trade_price_adjust amount=-100` |
| D3 | CN01 Igilgili | The punishment event E18 has `favor_add amount=0`, which has no effect. The same event in Quiza uses −100. | E18 |
| D4 | RC05 Tarraco | The message says that every 3 iron mines use 1 timber **per month**. E3–E6 repeat every 32 days, which is 2 months. E7 (15 mines) has no repeat, so it takes 1 timber one time only. | E3–E7 `rep32-32d`, E7 without repeat |
| D5 | RC03 Capua | A demand change in year 2 changes olives on route 0. Route 0 is not a trade route, so the change does not reach a partner. | `DEMAND_CHANGES dem year+2 olives route=0` |
| D6 | CN02 Quiza | The wage formula E9 is `{37,35}`. It gives a random wage of 35–37 (test values 35, 37, 37). The steps before and after use equal bounds, so 37 is probably the intended value. | `FORMULA id=247` |
| D7 | RC08 Mediolanum | The `.mapx` and the start save differ. The save forbids all workshops, concrete and brickworks, and has 2000 savings. The campaign loads the save, so the `.mapx` is out of date. In the save, E1 and E17 both ran, so the start stock of marble, stone and sand was given twice. | `SAVE executed_events: E1 E9 E17` |
| D8 | ARLR Aquileia, Nuceria, Londinium | Invasion points are on banks that no path connects to the main region (T7). Scheduled invasions (11 and 10) reach the city only through a bridge that the player builds. No message states this. This is a design gap, not a bug. | §2.2 T7 |
| D9 | Five maps | Enemies cannot pass forest (T6), so clearing forest opens invasion paths. No message states this rule. | §2.2 T6 |

Checked and **not** defects:
- Valencia E16 continues after the mint is built. The message says that the mint "reduces" corruption.
- Igilgili's Nymphaeum path closes the Rome route and caps tax at 5%. The StoneCircle message states both.
- Quiza collapses reservoirs inside the coastal rectangles for the whole mission, with no message about it. 195 reservoir sites with water are left outside them, so the permanent ban does not block the reservoir reward.
- Reconquered range formulas all use `{a,b}` and evaluate at random, including reversed ranges such as `{-130,-245}`.

---

## 6. Reconquered: mission by mission

| # | Mission | Main terrain pattern | Main economic or script device |
|---|---|---|---|
| 1 | Ostia | None (open baseline) | Drought delivery quest. A permanent 100 denarii subsidy. Prosperity is set to 35 when the population goal, a theater and a school are met. |
| 2 | Brundisium | T5 forest at the start | Subsidy and workshop gate are introduced. Election delivery. Clay and sand bonus from 5 clay pits. |
| 3 | Capua | T1 (55%) | Cart-depot quest gives +2 of 4 farm goods per month. A colosseum raises quotas. Weapon requests start. |
| 4 | Tarentum | T8 open approaches (17 wide) | Funding per 16 soldiers. A caravanserai opens 2 routes. A Ceres temple unlocks wheat. |
| 5 | Tarraco | T1 (21%), T4 no meadow | Iron mines use timber upkeep (D4). A villa gives 4000 savings. 12 weapon workshops give +2 iron. |
| 6 | Syracusae | T8 narrow chokes (1–5) | A sea blockade until a lighthouse. Salvage after 48 soldiers. A choice to absorb unemployment. |
| 7 | Miletus | T3 (median 16) | Plague. Wine for health. Fish spoilage. Upkeep for troops, libraries and academies. |
| 8 | Mediolanum (save) | T8 (8 points), T3 p90 60 | Recruitment cap before month 60. Trade-league permit. 150-soldier late invasions. |
| 9 | Lugdunum | T1 (24%), the entry has no land path to the largest region | Mint income. Native gift unlocks mission posts. Vines after a Ceres Grand Temple. Fort pay. |
| 10 | Carthago (save) | T6 forest wall, T9 natives at 10 | Civil-war choice through the Utica permit price (100, then 25,000). Caesarean invasions on one side only. |
| 11 | Tarsus (save) | T4 (no meadow, farms banned) | The Crassus caravanserai bargain with a delayed penalty. A small temple cap. Free raw goods per mine. |
| 12 | Tingis | T8 (4 approaches, up to 11 wide) | Marble 960 and stone 340. Price relief at 90 favor. Bog iron from 10 clay or sand pits. |
| 13 | Valencia | T2 (5 levels) | The widest trade (13 denarii per citizen). A corruption drain that grows with population. Patrician entertainment unlock. |
| 14 | Lutetia (save) | T9 natives | Tax fixed at 5%. Rome wine route through a lighthouse. Mission posts after 80 soldiers. |
| 15 | Caesarea | T4 (farms banned), T8 (8 points, up to 13 wide) | Food subsidy for favor. Pirate ransom until a lighthouse and 80 soldiers. |
| 16 | Damascus | T3 (no coast), T9 (natives at 6) | Water rights for 5000 denarii. Clay 340 and bricks 750. Forum penalty. Far East route for 18,000. |
| 17 | Londinium (save) | T8 (8 points, up to 15 wide) | Tax capped at 4%. Gladiator revolts until a colosseum. Vegetables made into oil. Marble 870 and oil 630. |
| 18 | Sarmizegetusa | T9 natives | Natives removed after 10 mausoleums. Bandit trade problems until a Mars Grand Temple. Fish after a Ceres Grand Temple. The lowest trade cap (3.4). |
| 19 | Lindum (save) | T1 (35%), T3 (median 22), T9 | Military or economic path. Hadrian's Wall staged delivery. Neptune or Ceres choice. Weapons upkeep after the wall. |
| 20 | Massilia | T4 (no meadow) | Garum sale for fish. Temple upkeep. A statue unlock with permanent upkeep. Second wine route for 150 per month. |

Pattern of the campaign: missions 1–7 teach one device each. Missions 8–20 combine 2–3 devices. Every mission from 2 on uses the same three base devices: the subsidy and workshop gate, the month-1 price event, and template requests. This makes Reconquered consistent and readable. It also means that the price event, not the terrain, sets most of the economic difficulty.

## 7. Conquering Numidia

Both missions use more scripting per map than any other campaign. Igilgili has 48 events and Quiza 68. Both follow one plan: a patron Grand Temple, the other four Grand Temples and the Pantheon banned, and a status variable with 4–6 states.

**Igilgili (Mercury):**
- Terrain: little water (median distance 18 tiles, 22% of land within 10 tiles of water). Forest covers the start area (open square 7). Natives are 54 tiles from the center.
- Rules: all farms, quarries, mines, timber yards and clay pits are banned. Food comes only from imports. Rome sells 5 vegetables and 5 fish at 10 denarii per unit (the buy price), and the quota rises with each full fort (E4–E8). Auzia and Theveste supply wheat and fruit at 75 units per year, and 500 after a caravanserai (E10).
- Prices: marble 3000/2940 and gold 1000/900.
- Choice: the player builds one of four monuments in the stone circle:
  - Oracle: mint unlocked, gold set to 50 (2/0 in fact, D1).
  - Small mausoleum: mission posts unlocked, native attacks stop.
  - Nymphaeum: marble at 1000, Rome route closed, tax capped at 5%.
  - Large mausoleum: gold mines unlocked, gold quotas on 3 routes.
- Caps: favor is held at 70 until the Mercury Grand Temple stands. The win needs favor 100 and peace 100. Peace 100 takes many years without damage, and the map schedules 17 invasions.
- Blessings: Mercury gives one blessing per 10 active workshops, up to 10 blessings.

**Quiza (Neptune):**
- Terrain: no meadow and no rock. The river entry and exit points are adjacent, so no river crosses the map and water exists only on the coast. The coast is a flood zone: E22 bans reservoirs there for the whole mission, and E25 bans clay pits and workshops there until a lighthouse stands.
- Rules: reservoirs, aqueducts, fountains, the dock, all farms and the forum start banned. The player starts as a citizen with salary 100 and no rescue loan.
- Sequence:
  1. A library and 16 wheat plus 16 fish start the lighthouse task.
  2. The lighthouse unlocks the dock, and the Nymphaeum storm surge removes the natives.
  3. The Senate envoy (E33) starts a 12-month choice. If the player does not build a military academy, Rome's path applies: forum, academy and villas, with reservoirs still banned and a penalty if the player builds one. If the player builds it, the other path applies: water buildings, extra invasions, 48 fish per year to Rome and the Ostia route.
- Prices: fish falls 1 per year for 15 years. Oil falls 200 on the "against Rome" path.
- Assessment: Quiza is the best-designed choice in the three campaigns. The choice is visible and stated in messages, both paths have costs, and the terrain (no meadow, coast flood zone) makes fish the only economy.

## 8. Recipe from the data

1. Choose 2–3 terrain patterns from §2.2 and make a script interact with at least one of them. The script can pay to remove the pattern (Damascus water rights, Quiza lighthouse, Lindum native areas).
2. Use prices to make the terrain pattern matter in the economy. Make the missing good expensive and the abundant good cheap. Use the `_only` price actions when only one price must change.
3. Keep the export cap at 4–8 denarii per citizen per year. Use route permit costs of 2–3 times the start funds, so the order in which routes open is a real choice.
4. State hidden terrain rules in a message: forest blocks enemies, invasion points on a separate bank, and zones that collapse buildings.
5. Put exclusive choices into one status variable, and give each option a stated cost.

---

## 9. Adaptation test: does the map make the player change strategy?

Criterion: a strong map changes trade and conditions during the mission. The player must then change strategy: change the export and import settings, move workers to other industries, open other routes or change the food supply.

Method: `scripts/sim.py` rebuilds a timeline of trade conditions for every map. The timeline uses:
- the start prices and route quotas;
- scheduled price changes and demand changes;
- events that a time condition alone triggers.

For each year it computes two values for every good that the city can export (a route buys it, the building is allowed, and the terrain has the site):
- **best per worker:** the profit per worker per year. Workshop goods use the raw material from local production (its workers are counted) or from import (its buy price is counted).
- **biggest earner:** the profit per year when the whole quota is filled.

When the best good changes, the player must move workers or change trade settings. A change in year 2 is not counted, because it is the standard opening of workshops at prosperity 10 or 15. Events that depend on the player (population, buildings, variables) are counted separately as "player-triggered".

Limits: the model ignores permit costs, the order in which the player opens routes, the city's own consumption and the labour supply. It applies each repeating event one time. "After all player-triggered events" applies the events of exclusive choices together, so it shows the direction of change, not one real path.

### 9.1 Results

| Map | Best export per worker over time | Biggest earner over time | Timed switches after year 2 | Player-triggered trade actions |
|---|---|---|---|---|
| AR Marcianopolis | fish → bricks (y3) → fish (y7) → bricks (y13) → fish (y14) → bricks (y17) | marble → wine (y9), then bricks and wine alternate 7 times to y36 | 13 | 11 |
| AR Antiochia | timber → bricks | marble and bricks alternate 6 times (y4–y44) | 5 | 17 |
| AR Noviomagus | iron → timber (y10) → iron (y14) | stone → weapons (y18) → furniture (y22) → weapons (y28) → furniture (y37) | 6 | 33 |
| AR Palmyra | wine → marble (y3) → wine (y5) → marble (y12) | marble → gold (y17) → marble (y20) | 5 | 70 |
| AR Complutum | sand | iron → sand (y7) → iron (y40) → sand (y44) | 3 | 27 |
| CN01 Igilgili | weapons → sand (y4) → weapons (y10) | stone → oil | 2 | 32 |
| RC07 Miletus | fish | wine → oil (y9) → wine (y11) → oil (y14) | 3 | 2 |
| RC12 Tingis | weapons | pottery → bricks (y9) → pottery (y13) | 2 | 3 |
| AR Aquileia | weapons → iron (y6) | weapons → iron (y6) → weapons (y7) | 3 | 18 |
| RC16 Damascus | weapons → iron (y3) → weapons (y23) | iron | 2 | 2 |
| AR Cyrene | weapons → pottery (y6) → iron (y40) | oil | 2 | 15 |
| AR Londinium | bricks → sand (y11) | pottery → bricks (y6) | 2 | 34 |
| RC04 Tarentum | furniture → iron (y11) | bricks | 1 | 4 |
| RC02 Brundisium | furniture → wheat (y9) | wheat | 1 | 26 |
| AR Nuceria | oil | oil → vegetables (y12), after the oil quota cuts | 1 | 31 |
| RC10 Carthago (save) | fish | weapons → fish (y4) | 1 | 12 |
| RC15 Caesarea | sand → vines (y16) | stone | 1 | 2 |
| AR Leptis Magna | bricks → fish (y24) | oil | 1 | 37 |
| RC01 Ostia | wheat | clay ↔ timber (y3) | 1 | 22 |
| RC05 Tarraco, RC06 Syracusae, RC08 Mediolanum, RC09 Lugdunum, RC11 Tarsus, RC13 Valencia, RC14 Lutetia, RC17 Londinium, RC18 Sarmizegetusa, RC19 Lindum, RC20 Massilia, CN02 Quiza, AR Castra Regina, AR Narbo Martius, AR Gesoriacum | no change | no change | 0 | 2–30 |

Player-triggered events change the best export on these maps:
- Palmyra: marble → bricks.
- Lindum: timber → fish per worker, and pottery → wine as the biggest earner. These come from the Neptune or Ceres choice and the wall rewards.
- Quiza: fish → wine per worker, after the second wine type is added on one path.
- Nuceria: oil → olives, and vegetables → fruit.
- ARLR Londinium: bricks → weapons.
- Aquileia: iron → bricks.
- Syracusae: olives → weapons.
- Castra Regina: marble → sand.
- Tarsus: marble → fish.

### 9.2 What the results show

- **Five ARLR maps meet the criterion on a timer.** On Marcianopolis, Antiochia, Noviomagus, Palmyra and Complutum the best export changes 3–13 times during the mission. The cause is scheduled price changes in both directions (11 reversals on Marcianopolis, 7 on Complutum, 5 on Noviomagus). The player who sets the trade settings in year 5 and leaves them is wrong by year 15.
- **Reconquered mostly does not meet it.** 11 of 20 missions have no timed change of the best export after the workshop gate. The cause is that Reconquered's scheduled price changes go in one direction. They raise import prices (marble, stone, oil) and do not change which export is best. Miletus (wine and oil alternate 3 times) and Tingis (pottery and bricks alternate 2 times) are the exceptions. They use small up-and-down price steps on two goods that are close in value.
- **Reconquered uses player-triggered changes instead.** Rewards raise quotas (Capua colosseum, Massilia temples, Lindum wall stages) and open routes (Tarentum caravanserai, Carthago lighthouse). These add options. Except on Lindum, they do not change which industry is best.
- **Numidia changes strategy through choices, not timers.** The Igilgili stone circle and the Quiza envoy choice change prices, quotas and legal buildings in one step. Quiza has no timed change at all: fish stays best until the player picks a path.
- **Other forced adjustments.** These do not change the best export, but they make the player change trade settings or labour:
  - Trade problems that stop land or sea trade for a period: Syracusae blockade until a lighthouse, Sarmizegetusa bandits until a Mars Grand Temple, Igilgili sea problems and Quiza land problems until the patron Grand Temple. The player must move trade to the other route type during these periods.
  - Food supply that depends on trade settings: Igilgili (Rome food quotas grow with each fort, caravanserai raises wheat and fruit from 75 to 500), Caesarea (fruit subsidy for favor), Quiza (fish converted to wheat and fruit).
  - Labour cost: wage steps with population on 23 maps, and worker-count changes through model data on ARLR Antiochia and Narbo Martius.

### 9.3 Design rules from the data

1. **Use price changes in both directions on two or three goods that are close in value.** Miletus does this with wine and oil, and Marcianopolis with bricks and wine. A rise on the import side only (the Reconquered pattern) increases costs, but it does not make the player change strategy.
2. **Cut the quota of the current best export, and open a new one in the same step.** Nuceria cuts oil from 35 to 15 and from 45 to 20. The biggest earner then changes from oil to vegetables.
3. **Give the player a choice that changes the economy.** Palmyra, the Igilgili stone circle, the Quiza envoy and Lindum's Neptune or Ceres choice each change which industry is best. Choices also make the change the player's decision, which is more readable than a timer.
4. **Make trade problems temporary and tie them to a task.** The player then runs two trade setups: one during the problem and one after the task removes it.
5. **Tie terrain to the economy.** Examples: a resource whose site is far from water (Damascus clay), a forest that blocks enemies and also gives timber (T6), and land that becomes available in stages (the Noviomagus swamp).

### 9.4 Play styles that are not standard

| Style | How the map forces it | Maps |
|---|---|---|
| A city with no farms (food imported only) | Farms banned or no meadow | Igilgili, Caesarea, Tarsus |
| A city with no piped water | Reservoirs banned or collapsed | Quiza (coast for the whole mission) |
| Low tax | Tax caps, forum penalties | Londinium 4%, Lutetia 5%, Damascus forum, Igilgili Nymphaeum path |
| A small army | Attacks are triggered by own troop count | ARLR Londinium, ARLR Complutum, Lindum military path, Mediolanum before month 60 |
| An army that pays | Funding or food per fort | Tarentum, Lugdunum, Igilgili |
| A city that keeps its forest | Forest blocks enemies (T6), not stated | Carthago, Noviomagus, Palmyra, Complutum, Marcianopolis |
| A city that does not bridge | Invaders on a separate bank (T7), not stated | Aquileia, Nuceria, ARLR Londinium |
| A few small temples | Temple count cap | Tarsus |

Two of these styles (keeping the forest, not building a bridge) come from terrain alone and are never stated. Stated in a message, they would be the strongest terrain-driven play styles in the three campaigns.

### 9.5 Tools for adaptation that the campaigns do not use

| Goal | Tools | Example |
|---|---|---|
| The best export changes | `trade_route_amount` to 0 on one route and a new resource on another route at the same time. Price reversals with `trade_set_sell_price_only`. | Oil quotas fall in year 12 and wine opens on a new route. The player must convert the workshops. |
| A resource runs out | `change_resource_produced false` on a timer or a count of mines | The ore of a mine area runs out after N years, and a new area opens with `change_terrain` (rock added). |
| Land moves | `change_terrain` to flood, drain or open land. `building_force_collapse` in the zone that changes. | A river shifts after a flood event, and the district on the old bank must move. |
| A route closes | `lock_trade_route`, `hide_trade_route`, `trade_route_set_open` (all unused) | A war closes the main sea route for 5 years. A land route through an exposed pass opens instead. |
| The rules change | `change_allowed_buildings false`, `change_house_model_data` (unused), `change_model_data` | A new law bans large insulae, so housing must change to villas. |
| The climate changes | `change_climate`, `change_weather` (both unused) | A drought changes the climate for the rest of the mission, so farms lose output and imports grow. |
| A terrain quest | `terrain_in_area`, `desirability_in_area`, `population_in_area` (all unused) | "Keep this forest standing" (trees counted in an area) as an alternative to walls. |

The unused tools in §4.2 and §4.3 are mostly the ones that change conditions. That is why the campaigns rarely make the player rebuild.
