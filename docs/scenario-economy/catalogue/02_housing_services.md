# Chapter 2: Housing and City Services

Engine: Augustus, upstream commit `dae1899`. All paths are relative to `src/`. A citation `file.c:N` points to the line in that commit. A row marked **derived** is a calculation from cited values. It is not a separate rule in the code. A row marked **unverified** was not confirmed in the source.

## 2.0 Time base and daily schedule

The simulation runs one subsystem for each tick number of a day. Each subsystem in the table below therefore runs **once per game day**, not once per tick.

| Rule | Value / formula | Cadence | Source |
|---|---|---|---|
| Ticks per day | 50 | - | game/time.h:13 |
| Days per month | 16 | - | game/time.h:14 |
| Months per year | 12 | - | game/time.h:15 |
| Plague duration update (houses, docks, warehouses, granaries) | tick 9 | daily | game/tick.c:164 |
| `houses_covered` decay | tick 12 | daily | game/tick.c:165 |
| Road access and distance from Rome entry | tick 21 | daily | game/tick.c:170 |
| House room (capacity) update | tick 22 | daily | game/tick.c:171 |
| Labour allocation | tick 25 | daily | game/tick.c:174 |
| Reservoir, aqueduct and fountain ranges | tick 27 | daily | game/tick.c:175 |
| House water, well and latrine access | tick 28 | daily | game/tick.c:176 |
| Building figure spawn (all walkers) | tick 31 | daily | game/tick.c:179 |
| Entertainment show countdown and city coverage % | tick 33 | daily | game/tick.c:181 |
| House service decay | tick 35 | daily | game/tick.c:183 |
| House entertainment, education, religion, health aggregates | tick 36 | daily | game/tick.c:184 |
| Desirability grid rebuild | tick 37 | daily | game/tick.c:185 |
| Building desirability value | tick 38 | daily | game/tick.c:186 |
| House evolution and goods consumption | tick 39 | daily | game/tick.c:187 |
| Burning ruins and fire spread | tick 43 | daily | game/tick.c:190 |
| Fire risk and collapse check | tick 44 | daily | game/tick.c:191 |
| Criminal generation | tick 45 | daily | game/tick.c:192 |
| Tax-collector coverage decay | tick 48 | daily | game/tick.c:195 |
| City culture averages | tick 49 | daily | game/tick.c:196 |
| City health update | first action of a new month | monthly | game/tick.c:85 |
| House food consumption | new month | monthly | game/tick.c:88 |

"Working" monument (grand temple, Pantheon, colosseum, hippodrome) means: finished, in use, and `num_workers ≥ laborers` (full staff). A grand temple module is active only while its temple is working (building/monument.c:772-799, 839-857). Every "GT working" rule in this chapter needs full staff.

The order inside one day is important: desirability (37) is rebuilt, then copied to buildings (38), then houses evolve (39) with these values.

## 2.1 House model table (all 20 levels)

The table shows the default values. The struct fields are described in building/properties.h:25-44. The engine copies the house rows into the runtime model with `houses[level] = properties[level + 10]` (building/properties.c:2381-2387).

Column key: **Ev** = evolve desirability. **Dv** = devolve desirability. **Ent** = entertainment points. **Wat** = water level (1 = well, 2 = latrines or fountain, 3 = fountain). **Rel** = number of gods. **Edu** = education level. **Bar** = barber. **Bth** = bathhouse. **Hlt** = health level (1 = doctor or hospital, 2 = doctor and hospital). **Food** = food types. **Pot/Oil/Fur** = goods (0/1). **Wine** = wine types (1 = any wine, 2 = two wine sources in the city). **Pros** = prosperity contribution. **Max** = max people. **Tax** = tax multiplier. **Emit** = the desirability that the house itself emits (value/step/step size/range). **Sz** = house size in tiles (side length).

| Lvl | House | Sz | Ev | Dv | Ent | Wat | Rel | Edu | Bar | Bth | Hlt | Food | Pot | Oil | Fur | Wine | Pros | Max | Tax | Emit | Source |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0 | Small Tent | 1 | -10 | -101 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 5 | 5 | 1 | -3/1/1/3 | properties.c:138 |
| 1 | Large Tent | 1 | -5 | -12 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 10 | 7 | 1 | -3/1/1/3 | properties.c:163 |
| 2 | Small Shack | 1 | 0 | -7 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 15 | 9 | 1 | -2/1/1/2 | properties.c:188 |
| 3 | Large Shack | 1 | 4 | -2 | 0 | 1 | 1 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 20 | 11 | 1 | -2/1/1/2 | properties.c:213 |
| 4 | Small Hovel | 1 | 8 | 2 | 0 | 2 | 1 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 25 | 13 | 2 | -2/1/1/2 | properties.c:238 |
| 5 | Large Hovel | 1 | 12 | 6 | 10 | 2 | 1 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 30 | 15 | 2 | -2/1/1/2 | properties.c:263 |
| 6 | Small Casa | 1 | 16 | 10 | 10 | 2 | 1 | 1 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 35 | 17 | 2 | -1/1/1/1 | properties.c:288 |
| 7 | Large Casa | 1 | 20 | 14 | 10 | 3 | 1 | 1 | 0 | 1 | 0 | 1 | 1 | 0 | 0 | 0 | 45 | 19 | 2 | -1/1/1/1 | properties.c:313 |
| 8 | Small Insula | 1 | 25 | 18 | 25 | 3 | 1 | 1 | 0 | 1 | 0 | 1 | 1 | 0 | 0 | 0 | 50 | 19 | 3 | 0/1/1/1 | properties.c:338 |
| 9 | Medium Insula | 1 | 32 | 22 | 25 | 3 | 1 | 1 | 0 | 1 | 1 | 1 | 1 | 0 | 1 | 0 | 58 | 20 | 3 | 0/1/1/1 | properties.c:363 |
| 10 | Large Insula | 2 | 40 | 29 | 25 | 3 | 1 | 2 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 0 | 65 | 84 | 3 | 0/0/0/0 | properties.c:388 |
| 11 | Grand Insula | 2 | 48 | 37 | 35 | 3 | 1 | 2 | 1 | 1 | 1 | 2 | 1 | 1 | 1 | 0 | 80 | 84 | 4 | 0/0/0/0 | properties.c:413 |
| 12 | Small Villa | 2 | 53 | 45 | 35 | 3 | 2 | 2 | 1 | 1 | 1 | 2 | 1 | 1 | 1 | 1 | 150 | 40 | 9 | 1/2/-1/2 | properties.c:438 |
| 13 | Medium Villa | 2 | 58 | 50 | 40 | 3 | 2 | 2 | 1 | 1 | 2 | 2 | 1 | 1 | 1 | 1 | 180 | 42 | 10 | 1/2/-1/2 | properties.c:463 |
| 14 | Large Villa | 3 | 63 | 55 | 45 | 3 | 2 | 3 | 1 | 1 | 2 | 2 | 1 | 1 | 1 | 1 | 400 | 90 | 11 | 2/2/-2/2 | properties.c:488 |
| 15 | Grand Villa | 3 | 68 | 60 | 50 | 3 | 3 | 3 | 1 | 1 | 2 | 3 | 1 | 1 | 1 | 1 | 600 | 100 | 11 | 2/2/-2/2 | properties.c:513 |
| 16 | Small Palace | 3 | 74 | 65 | 55 | 3 | 3 | 3 | 1 | 1 | 2 | 3 | 1 | 1 | 1 | 2 | 700 | 106 | 12 | 3/2/-1/6 | properties.c:538 |
| 17 | Medium Palace | 3 | 80 | 70 | 60 | 3 | 4 | 3 | 1 | 1 | 2 | 3 | 1 | 1 | 1 | 2 | 900 | 112 | 12 | 3/2/-1/6 | properties.c:563 |
| 18 | Large Palace | 4 | 90 | 76 | 70 | 3 | 4 | 3 | 1 | 1 | 2 | 3 | 1 | 1 | 1 | 2 | 1500 | 190 | 15 | 4/2/-1/6 | properties.c:588 |
| 19 | Luxury Palace | 4 | 100 | 85 | 80 | 3 | 4 | 3 | 1 | 1 | 2 | 3 | 1 | 1 | 1 | 2 | 1750 | 200 | 16 | 4/2/-1/6 | properties.c:613 |

Notes on the model table:

| Rule | Value / formula | Cadence | Source |
|---|---|---|---|
| Vacant lot is the same building type as a small tent | `BUILDING_HOUSE_VACANT_LOT = BUILDING_HOUSE_SMALL_TENT = 10`. A tent with 0 people is a vacant lot. | - | building/type.h:23-24 |
| Luxury palace cannot evolve | evolve desirability is forced to 1000 at level ≥ luxury palace | daily | building/house_evolution.c:38-40 |
| Small tent never devolves by desirability | devolve desirability = -101 (below the grid minimum of -100) | - | building/properties.c:144-145, map/desirability.c:38 |
| Goods amount consumed per event | the model value: pottery, oil, furniture = 1; wine = the `wine` value (1 or 2) | per consumption event | building/properties.c:2439-2453, building/house_evolution.c:559 |
| Allowed editor range for house fields | devolve/evolve -101..100; entertainment 0..116; water 0..3; religion 0..5; education 0..3; barber, bathhouse, pottery, oil, furniture 0..1; health 0..2; food 0..5; wine 0..2 | - | building/properties.c:44-62 |
| Scenario can change house model data | scenario action "change house model data" writes into the runtime model | on event | scenario/event/action_types.c:853-862 |
| Scenario can change building model data (desirability, cost, labourers) | scenario action "change model data" | on event | scenario/event/action_types.c:772-781 |
| Model data is saved in the scenario/savegame | building + house model arrays are written and read as raw buffers | on save/load | building/properties.c:2395-2424 |
| Grand garden and dolphin fountain have zero runtime model | `model_reset_buildings` sets them to `NOTHING` (all zero), so they emit no desirability by default | on reset | building/properties.c:2364-2379 |

## 2.2 House capacity, sizes, merging and expansion

| Rule | Value / formula | Cadence | Source |
|---|---|---|---|
| House capacity | `max_people` of the level | daily (tick 22) | building/house_population.c:56-58 |
| Merged 2x2 small house capacity | `max_people × 4` when `house_is_merged` | daily | building/house_population.c:60-62 |
| Neptune module 2 capacity bonus | `+ (max + 1) / 20` (about +5 %) for houses with Neptune temple access | daily | building/house_population.c:64-68 |
| House not reachable from Rome entry | room = −population, people are marked for eviction | daily | building/house_population.c:89-92 |
| House without road within 2 tiles | after > 4 daily checks, people become homeless and the house is removed | daily (tick 21) | building/maintenance.c:253-263 |
| House with road but no reachable road | after > 8 daily checks the house is removed | daily | building/maintenance.c:273-283 |
| Merge chance per house tile | merge is possible only if `map_random(tile) & 7 < 5` (5 of 8 tiles), unless config "all houses merge" is on | daily attempt | building/house.c:149-153 |
| Merge condition | the 2x2 block at the house anchor (x..x+1, y..y+1) has 4 tiles of in-use, unmerged houses of the **same level** | daily attempt | building/house.c:154-173 |
| Merge result | size 2, `house_is_merged = 1`; population, goods and happiness (population-weighted) are summed | on merge | building/house.c:112-131 |
| Levels that try to merge | small tent (only with people, or always with config "pre-merge vacant lots") through medium insula | daily | building/house_evolution.c:220-353 |
| Medium insula → large insula | needs a 2x2 area (4 tiles) | on evolve | building/house_evolution.c:355-360 |
| Medium villa → large villa | needs a 3x3 area (9 tiles) | on evolve | building/house_evolution.c:414-418 |
| Medium palace → large palace | needs a 4x4 area (16 tiles) | on evolve | building/house_evolution.c:476-480 |
| Expansion search order | 4 anchor directions; pass 1 = only houses of level ≤ own level; pass 2 = also clear land; pass 3 = also gardens (unless config "houses don't expand into gardens") | on evolve | building/house.c:176-253 |
| Expansion blocked | `no_space_to_expand = 1`; the house stays at its level | on evolve | building/house.c:254-255 |
| Absorbed houses | larger absorbed houses are split first; all people and goods move into the expanded house | on expand | building/house.c:371-450 |
| Large insula devolve | becomes a merged medium insula (2x2) if config "all houses merge" is on or `map_random & 7 < 5`; else it splits into 4 medium insulae with population/4 each | on devolve | building/house.c:453-462 |
| Large villa devolve (default) | becomes a 2x2 medium villa plus 5 separate 1x1 medium insulae; population and goods are divided by 6 | on devolve | building/house.c:515-554 |
| Large palace devolve (default) | becomes a 3x3 medium palace plus 7 separate 1x1 medium insulae; population and goods are divided by 8 | on devolve | building/house.c:556-598 |
| Patrician devolution fix (config) | large villa / large palace shrink by 1 tile side and keep all people and goods; the new corner is the first one with a road within 1 tile, else 2 tiles | on devolve | building/house.c:464-513, building/house_evolution.c:435-439, 497-501 |
| Other size changes | none: small villa (2) ↔ grand insula (2), grand villa (3) ↔ large villa (3), small palace (3) ↔ grand villa (3) only change type | on evolve/devolve | building/house_evolution.c:383-469 |

## 2.3 Evolution and devolution

| Rule | Value / formula | Cadence | Source |
|---|---|---|---|
| Evolution check frequency | every house, once per day; a house changes at most one level per day | daily (tick 39) | building/house_evolution.c:572-603 |
| Houses with plague | skip evolution and devolution | daily | building/house_evolution.c:594-596 |
| Desirability status | `des ≤ devolve` → DEVOLVE; else `des ≥ evolve` → EVOLVE; else NONE | daily | building/house_evolution.c:41-49 |
| Requirement check, current level | if the house fails any requirement of its **current** level → DEVOLVE (overrides desirability) | daily | building/house_evolution.c:201-202 |
| Requirement check, next level | if status is EVOLVE, the house must also meet all requirements of the **next** level | daily | building/house_evolution.c:203-205 |
| Requirement order (first failure stops) | water → entertainment → education → religion → barber → bathhouse → health → food types → pottery → oil → furniture → wine → second wine | daily | building/house_evolution.c:65-191 |
| Water level 3 | needs fountain water (`has_water_access`) | daily | building/house_evolution.c:67-70 |
| Water level 2 | fountain water, or latrines access; a well does not count | daily | building/house_evolution.c:71-72 |
| Water level 1 | fountain water, or well access; latrines do not count | daily | building/house_evolution.c:73-76 |
| Water text in the info panel | the evolve text for level 2 checks well **and** latrines; this is UI text only, not the rule | - | building/house_evolution.c:804-809 |
| Food types | count of food resources with stock > 0 in the house | daily | building/house_evolution.c:162-172 |
| Pottery, oil, furniture | house stock ≥ model value (1) | daily | building/house_evolution.c:174-182 |
| Wine | stock > 0; level 2 also needs ≥ 2 wine sources in the city | daily | building/house_evolution.c:183-190 |
| Wine sources in the city | (1 if any active wine workshop) + (1 if Venus module 1) + (number of empire cities that sell wine on open routes, function not opened) | daily (tick 32) | city/trade.c:18-23 |
| Devolve delay (normal) | a house devolves on the **3rd** consecutive daily DEVOLVE result; any other result resets the counter | daily | building/house_evolution.c:20, 209-218 |
| Devolve delay (Venus Grand Temple working) | devolves on the **21st** consecutive daily DEVOLVE result | daily | building/house_evolution.c:21, 578-582 |
| Evolve delay | none; EVOLVE is applied on the same day | daily | building/house_evolution.c:209-218 |
| Small tent | evolves to large tent only with people; never devolves | daily | building/house_evolution.c:220-233 |
| Large tent | only processed if population > 0 | daily | building/house_evolution.c:235-249 |
| Pantheon module 2 + house has Pantheon access | desirability thresholds and current-level requirements use level − 1; next-level requirements use the current level | daily | building/house_evolution.c:194-206, 509-513 |
| Pantheon access lifetime | Pantheon priest sets 96; decays 1 per day | daily | figure/service.c:160-163, building/house_service.c:45 |
| Map refresh after an expansion | land routing is rebuilt once after the pass | daily | building/house_evolution.c:604-606 |

## 2.4 Goods and food consumption

| Rule | Value / formula | Cadence | Source |
|---|---|---|---|
| Goods consumption days | day 0 of each month for every house; day 7 also for houses with `house_size > 1` | 1× or 2× per month | building/house_evolution.c:597-600 |
| 1x1 houses consume half | an unmerged 1x1 house consumes once per month; merged 2x2 houses (`house_size = 2`) consume twice | - | building/house_evolution.c:597-598, building/house.c:116 |
| Amount per event | 1 pottery, 1 oil, 1 furniture, `wine` (1 or 2) wine, only if the level uses the good; stock does not go below 0 | per event | building/house_evolution.c:520-529, 553-561 |
| Consumption reduction formula | with reduction r %, the event happens only if `(total_months × (100 − r)) % 100 < (100 − r)` | per event | building/house_evolution.c:557-560 |
| Mercury module 1 | pottery and furniture −20 % for **all** houses | per event | building/house_evolution.c:535-539 |
| Mercury module 2 | oil and wine −20 % for houses with Mercury temple access | per event | building/house_evolution.c:540-544 |
| Mars module 2 | wine, oil, pottery, furniture −10 % for houses with Mars temple access | per event | building/house_evolution.c:545-551 |
| Reductions stack | the r values are added before the test | per event | building/house_evolution.c:533-551 |
| r = 20 in practice (derived) | 1 of each 5 months skips the event | - | derived from house_evolution.c:558 |
| Food consumed per house per month | `population × 50 / 100` (integer) | monthly | city/resource.c:530 |
| Ceres module 1 | `population × 40 / 100` for houses with Ceres temple access | monthly | city/resource.c:519, 527-528 |
| Split by type | the amount is divided by the number of food types that the house holds now | monthly | city/resource.c:532-540 |
| Short stock | if a type has less than its share, the type goes to 0 but still counts as eaten | monthly | city/resource.c:557-561 |
| Houses whose level needs 0 food types | do not consume food | monthly | city/resource.c:548 |
| Rome supplies wheat (scenario flag) | each house gets wheat = its share; `num_foods = 1` | monthly | city/resource.c:543-547 |
| `num_foods` | number of types eaten this month; used by the health formula (2.11) | monthly | city/resource.c:542-562 |

## 2.5 Market and temple distribution to houses

| Rule | Value / formula | Cadence | Source |
|---|---|---|---|
| Who distributes | market trader (roaming) and market supplier (unless config "no supplier distribution"); Ceres and Venus small/large temple priests also call the market routine with the temple stock | each tile walked | figure/service.c:536-543, 584-588, 612-618 |
| Houses served | every house with people in the 5x5 area centred on the walker tile | each tile walked | figure/service.c:429-450 |
| Model used | the model of the **next** level (current + 1, max luxury palace) | per visit | figure/service.c:371-374, 385 |
| Food target per type | `4 × house_highest_population` | per visit | figure/service.c:375 |
| Food per visit | only the first accepted food type that the house has below target and the market has; the house gets the full target amount (or the market remainder); then the routine stops | per visit | figure/service.c:386-401 |
| Food only if next level needs food | skipped when the next level has 0 food types | per visit | figure/service.c:386 |
| Goods target | `8 × model value` (pottery, furniture, oil, wine); 12 × with Venus Grand Temple working | per visit | figure/service.c:404-426 |
| Goods amount | the difference to the target, limited by market stock | per visit | figure/service.c:329-344 |
| Market spawn delay (days) | 100 % workers: 2; ≥ 75 %: 5; ≥ 50 %: 10; ≥ 25 %: 20; ≥ 1 %: 30; 0 %: none | daily | building/figure.c:907-921 |
| Market supplier | one supplier at a time (`figure_id2`); spawns when a storage destination exists | daily | building/figure.c:879-898, 931-932 |
| Rome supplies wheat | every market and mess hall gets 200 wheat | daily (tick 17) | city/resource.c:503-512 |
| Venus module 1: wine to taverns | Venus temple priest fills each tavern in the 5x5 area up to 200 wine | each tile walked | figure/service.c:452-481, 616-618 |
| Mars module 1: offerings | Mars temple priest collects from each house with `days_since_offering ≥ 16`: for each food type that the house holds, + `house_size` units (2 for a merged 1x1) to the temple, temple max 400 per type; food is generated, not removed from the house | each tile walked | figure/service.c:346-367, building/monument.h:9 |
| `days_since_offering` | +1 per day, max 125 | daily | building/house_service.c:46-48 |

## 2.6 Desirability

### 2.6.1 Grid calculation

| Rule | Value / formula | Cadence | Source |
|---|---|---|---|
| Grid rebuild | clear, then add every in-use building, then add terrain | daily (tick 37) | map/desirability.c:201-206 |
| Ring shape | ring at distance d = square ring at Chebyshev distance d around the building footprint | - | map/ring.c:11-45 |
| Step formula | for d = 1 .. range (range max 8): add `value` to every tile of ring d; after each `step` rings, `value += step_size` | - | map/desirability.c:50-69 |
| Own tiles | the building does not add to its own footprint (ring starts at d = 1) | - | map/desirability.c:57-59 |
| Tile limits | each tile value is clamped to −100 .. +100 after each addition | - | map/desirability.c:37-38, 44-45 |
| Unfinished monument | value, step, step size and range = 0 | daily | map/desirability.c:108-113 |
| Example (derived) | small temple 4/2/−1/6 gives +4, +4, +3, +3, +2, +2 at d = 1..6; garden 3/1/−1/3 gives +3, +2, +1 | - | derived from building/properties.c and map/desirability.c:50-69 |

### 2.6.2 Terrain sources

Only the terrain types in this table add desirability. Water, trees, rock and meadow add **nothing** to the grid.

| Terrain | Value/step/step size/range | Cadence | Source |
|---|---|---|---|
| Plaza (road with plaza flag) | plaza model: 4/1/−2/2 | daily | map/desirability.c:160-161, building/properties.c:704 |
| Earthquake fault (rock with flag) | vacant-lot model = small tent: −3/1/1/3 | daily | map/desirability.c:162-164 |
| Garden terrain / overgrown garden | gardens model: 3/1/−1/3 | daily | map/desirability.c:133-150, 165-167, 179-180 |
| Rubble | −2/1/1/2 | daily | map/desirability.c:181-182 |
| Highway | highway model: −4/1/2/2 | daily | map/desirability.c:183-189, building/properties.c:2046 |
| Marshland | −3/1/1/3 | daily | map/desirability.c:190-191 |
| Beach | +1/1/1/2 | daily | map/desirability.c:192-193 |
| Aqueduct | −2/1/1/2 | daily | map/desirability.c:194-195 |

### 2.6.3 Building desirability value

| Rule | Value / formula | Cadence | Source |
|---|---|---|---|
| Base | highest grid value over the building footprint | daily (tick 38) | building/building.c:805, map/desirability.c:213-228 |
| Close to water | +15 if a water terrain tile is within 3 tiles of the footprint | daily | building/building.c:807-809, 1094-1097, building/building.h:10-11 |
| Elevation bonus | elevation 0: 0; 1: +10; 2: +12; 3: +14; 4: +16; ≥ 5: +18 (anchor tile) | daily | building/building.c:783-793, 811 |
| Outskirts malus | −15 if any footprint tile has the editor "outskirts" flag | daily | building/building.c:813-815, building/building.h:13, editor/tool.c:340 |
| Clamp | −100 .. +100 | daily | building/building.c:818 |
| "Close to water" refresh | recalculated when a house is created, merged, split or expanded | on change | building/building.c:320, building/house.c:117, 401 |

### 2.6.4 Grand temple effects on desirability

| Rule | Value / formula | Cadence | Source |
|---|---|---|---|
| Venus GT working: statues, gardens, temples, ponds, trees, etc. (71 types with `venus_gt_bonus = 1`) | value += max(value / 4, 1); step += 1; range += 1 | daily | map/desirability.c:115-121, building/building.c:905-909 |
| Venus GT working: garden terrain | same bonus | daily | map/desirability.c:142-147 |
| Venus module 2: house with Venus temple access, level ≥ small villa | value + 4, range + 1 | daily | map/desirability.c:91-94 |
| Venus module 2: tents (level ≤ large tent) | value + 2, range = 1 (tent emits −1 at d = 1 only) | daily | map/desirability.c:95-99 |
| Venus module 2: other houses | value + 2; range at least 1 | daily | map/desirability.c:100-105 |

The full building desirability table is in Appendix 2.A.

## 2.7 Service coverage on houses

### 2.7.1 How a walker sets coverage

| Rule | Value / formula | Cadence | Source |
|---|---|---|---|
| Coverage moment | when `progress_on_tile` reaches 15, that is when the walker finishes a tile | per tile | figure/movement.c:316-323, 577-585 |
| Coverage area | 5x5 square centred on the walker tile (radius 2) | per tile | figure/service.c:21-40 |
| Houses affected | only houses with population > 0 (culture, health, market) | per tile | figure/service.c:32 |
| Prefect, engineer | affect every building in the 5x5 area (the tax collector uses the same routine but filters to houses with people) | per tile | figure/service.c:275-294, 320 |
| Value set | flag = 96 (`MAX_COVERAGE`) | per tile | figure/service.c:18, 86-193 |
| Decay | each flag −1 per day, minimum 0 | daily (tick 35) | building/house_service.c:7-45 |
| Coverage lifetime (derived) | 96 days = 6 months after the last visit | - | derived |
| Tax collector | sets `house_tax_coverage = 50` on houses with people only; −1 per day | daily (tick 48) | figure/service.c:318-327, building/house_service.c:53-62 |
| Missionary | sets native anger to 0 in a 9x9 area (radius 4) | per tile | figure/service.c:202-221 |

### 2.7.2 Walker that sets each flag

| House flag | Walker (building) | Source |
|---|---|---|
| theater | actor from a theater | figure/service.c:635-638 |
| amphitheater actor / gladiator | actor or gladiator from an amphitheater | figure/service.c:639-648 |
| colosseum gladiator / lion | gladiator or lion tamer from a colosseum | figure/service.c:649-651, 662-665 |
| arena gladiator / lion | gladiator or lion tamer from an arena | figure/service.c:652-661 |
| hippodrome | charioteer | figure/service.c:667-668 |
| tavern wine / tavern food | barkeep | figure/service.c:670-681 |
| school | school child | figure/service.c:547-548 |
| library | librarian | figure/service.c:553-554 |
| academy | teacher | figure/service.c:550-551 |
| barber | barber | figure/service.c:556-557 |
| bathhouse | bathhouse worker | figure/service.c:544-545 |
| clinic | doctor | figure/service.c:559-560 |
| hospital | surgeon | figure/service.c:562-563 |
| temple Ceres/Neptune/Mercury/Mars/Venus | priest of a small, large or grand temple of that god | figure/service.c:582-622 |
| all five gods + Pantheon access | Pantheon priest | figure/service.c:623-630 |

### 2.7.3 House aggregates (daily, tick 36)

| Value | Formula | Source |
|---|---|---|
| Entertainment | theater +10; tavern wine +10 (and tavern food +5 more, only with wine); amphitheater +10 (+15 with gladiator flag); max(arena, colosseum) where arena = 10 (20 with lion) and colosseum = 15 (25 with lion); hippodrome flag +30; finished hippodrome monument in city +5; finished colosseum monument in city +5; Venus module 2 with Venus access +10 | building/house_service.c:93-139 |
| Maximum entertainment (derived) | 10 + 15 + 15 + 25 + 30 + 5 + 5 + 10 = 115 | derived |
| Education | 0; school or library → 1; school and library → 2; school, library and academy → 3; academy alone → 0 | building/house_service.c:142-151 |
| Religion (`num_gods`) | count of the five god flags > 0 | building/house_service.c:154-169 |
| Health | clinic flag + hospital flag (0..2) | building/house_service.c:172-178 |

### 2.7.4 Walker roam lengths

Roam length counts game ticks of roaming. A walker crosses one tile in 15 movement steps (figure/movement.c:318-325). Highway tiles double the steps per tick (figure/movement.c:312-314).

| Walker | Max roam length | Steps per tick | Approx. tiles before return (derived) | Source |
|---|---|---|---|---|
| Priest, teacher, librarian, barber, bathhouse worker, doctor, surgeon | 384 | 1 | 25 | figuretype/service.c:59-70, 361-369 |
| Barkeep | 384 | 1 | 25 | figuretype/service.c:228-238 |
| Market trader | 384 | 1 | 25 | figuretype/service.c:472-483 |
| Labor seeker | 384 | 1 | 25 | figuretype/service.c:458-469 |
| School child | 192 | 2 | 25 | figuretype/service.c:178-202 |
| Missionary | 192 | 1 | 12 | figuretype/service.c:404-414 |
| Tax collector | 512 | 1 | 34 | figuretype/service.c:487-493 |
| Actor, gladiator, lion tamer | 512 | 1 | 34 | figuretype/entertainer.c:314, 331, 401-416 |
| Charioteer | 512 | 2 | 68 | figuretype/entertainer.c:314, 331 |
| Engineer, prefect | 640 | 1 | 42 | figuretype/maintenance.c:28, 84, 273, 333 |
| Entertainer going to a venue | dies after 3200 ticks | - | - | figuretype/entertainer.c:385-390 |

A school child dies at the end of its roam. Other roamers walk back to a road within 2 tiles of their building (figuretype/service.c:34-46, 196-201).

### 2.7.5 Spawn delays by worker percentage

`worker_percentage = num_workers × 100 / laborers` (building/figure.c:52-55). The delay counter advances by 1 per day. A walker appears when `counter > delay`, so the interval is delay + 1 days. For most buildings the counter does not advance while the walker of that building is alive.

| Building | 100 % | ≥ 75 % | ≥ 50 % | ≥ 25 % | ≥ 1 % | Notes | Source |
|---|---|---|---|---|---|---|---|
| Default (theater, actor colony, gladiator school, bathhouse, school, library, academy, barber, doctor, hospital, work camp, architect guild, caravanserai, lighthouse, depot) | 3 | 7 | 15 | 29 | 44 | 0 % → no walker | building/figure.c:125-141 |
| Tavern | 6 | 14 | 30 | 58 | 88 | default × 2; needs ≥ 20 wine | building/figure.c:1270-1285 |
| Engineer post, prefecture, senate/forum (tax), mission post | 0 | 1 | 3 | 7 | 15 | | building/figure.c:355-372, 390-407, 1407-1423, 1446-1462 |
| Amphitheater | 3 | 7 | 15 | 29 | 44 | | building/figure.c:551-567 |
| Lion house | 5 | 10 | 20 | 35 | 60 | | building/figure.c:464-480 |
| Chariot maker | 7 | 15 | 30 | 60 | 90 | | building/figure.c:508-524 |
| Hippodrome | 7 | 15 | 30 | 50 | 80 | | building/figure.c:642-658 |
| Colosseum, arena | 6 | 12 | 20 | 40 | 70 | | building/figure.c:711-727 |
| Market (trader) | 2 | 5 | 10 | 20 | 30 | | building/figure.c:907-930 |
| Temple (small, large, grand, Pantheon) | 3 | 7 | 10 | 15 | 20 | 7 if the temple model has 0 labourers | building/figure.c:1296-1317 |
| Grand temple of Mars | 8 | 12 | 16 | 32 | 48 | + (food stress − 20) if food stress > 20; also spawns soldiers | building/figure.c:1195-1238 |

Other spawn rules:

| Rule | Value / formula | Source |
|---|---|---|
| School | spawns 4 school children at once | building/figure.c:1040-1059 |
| Bathhouse | needs reservoir range on its footprint, else no walker and a problem flag | building/figure.c:983, 988-1010 |
| Temple priest | the priest is created only if the temple has no live priest; the counter still resets | building/figure.c:1313-1328 |
| Neptune module 1 | Neptune temples also spawn a charioteer every 2nd priest cycle (hippodrome coverage) | building/figure.c:1318-1326 |
| Ceres module 2 / Venus module 1 | Ceres / Venus temples spawn a supplier that fetches food / wine | building/figure.c:1352-1360 |
| Pantheon module 1 | every temple keeps one extra priest that walks to the Pantheon | building/figure.c:1362-1370 |
| Venue walkers do not need shows | theater, amphitheater, arena, colosseum, hippodrome spawn their roamer with no check of show days | building/figure.c:540-619, 621-688, 700-758 |

### 2.7.6 `houses_covered` and labor seekers

| Rule | Value / formula | Cadence | Source |
|---|---|---|---|
| `houses_covered` increase | + number of houses with people that the walker serviced on a tile | per tile | figure/service.c:715-721 |
| Cap | 300 | - | figure/service.c:718-720 |
| Decay | −1 per day (to 0); towers and watchtowers excluded | daily (tick 12) | building/house_service.c:64-76 |
| Problem flag | building has a problem icon if `houses_covered ≤ 0` | daily | building/figure.c:57-62 |
| Labor seeker spawn threshold 50 | most service buildings (actor colony, gladiator school, lion house, chariot maker, market, bathhouse, school, library, academy, barber, doctor, hospital, temple, senate/forum, industry, wharf, shipyard, dock, armoury, tower) | daily | building/figure.c:421, 442, 463, 507, 906, 1000, 1030, 1082, 1113, 1134, 1155, 1176, 1295, 1406, 1484, 1512, 1536, 1570, 2087, 333 |
| Labor seeker spawn threshold 100 | warehouse, granary, engineer post, prefecture, grand temple of Mars, barracks, military academy, work camp, architect guild, mess hall, caravanserai, lighthouse, highway station, watchtower, depot | daily | building/figure.c:282, 311, 354, 389, 1194, 1679, 1736, 1745, 1769, 1839, 1874, 1892, 1913, 1987, 2034 |
| Venues (theater, amphitheater, hippodrome, colosseum, arena, tavern) | labor seeker when `houses_covered ≤ 50` | daily | building/figure.c:548-550, 601-603, 639-641, 708-710, 1267-1269 |
| One labor seeker at a time | stored in `figure_id2` | - | building/figure.c:78-89 |
| Labor seeker coverage | counts houses only; sets no house flag | per tile | figure/service.c:83-84, 526-528 |
| Config "global labour" | `houses_covered = 2 × threshold` (or 100) if the building has a route to Rome, else 0 | daily | building/figure.c:69-77, 94-100 |
| Mission post | `houses_covered = 100` with a route to Rome | daily | building/figure.c:1440-1445 |
| Labour allocation needs coverage | a building outside engineering and water categories gets workers only if `houses_covered > 0`; when workers are short they are shared in proportion to `houses_covered` (details in the labour chapter) | daily (tick 25) | city/labor.c:264-271, 395-420, 480-500 |

## 2.8 Water

| Rule | Value / formula | Cadence | Source |
|---|---|---|---|
| Well radius | 2 (3 with Neptune GT working) | daily | map/water_supply.c:27, 366-374 |
| Well requirements | none: no workers, no water source | daily | map/water_supply.c:93-97 |
| Well gives | `has_well_access` to every building in the area | daily | map/water_supply.c:40-54 |
| Latrines radius | 3 (Neptune GT has no effect) | daily | map/water_supply.c:28, 376-379 |
| Latrines requirement | `num_workers > 0` (model: 2 labourers) | daily | map/water_supply.c:56-70, building/properties.c:2219 |
| Fountain radius | 4; 3 in desert climate; +1 with Neptune GT working | daily | map/water_supply.c:29, 346-354 |
| Fountain requirement | its tile is in reservoir range **and** `num_workers > 0` (model: 4 labourers) | daily | map/water_supply.c:252-258 |
| House fountain water | any house tile in fountain range → `has_water_access` | daily (tick 28) | map/water_supply.c:74-87 |
| Reservoir radius | 10 around the 3x3 reservoir; 12 with Neptune GT working | daily | map/water_supply.c:26, 225-229, 356-364 |
| Reservoir fill from nature | a water terrain tile in the 5x5 area around the reservoir (1 tile margin) | daily | map/water_supply.c:197-206 |
| Reservoir fill from aqueduct | a full reservoir fills connected aqueducts; an aqueduct fills a reservoir at a non-corner edge tile; repeat until no change | daily | map/water_supply.c:125-190, 207-223 |
| Neptune module 2 | the Neptune GT (7x7) acts as a reservoir: reservoir range radius 10 (12) around it | daily | map/water_supply.c:231-235 |
| Bathhouse water | needs reservoir range on its footprint (not fountain range) | daily (tick 31) | building/figure.c:978-994 |
| Ponds, large statues, colosseum | "has water" from reservoir range (animation/graphics) | daily | map/water_supply.c:260-297 |
| Fountain graphic level | desirability > 60: 3; > 40: 2; > 20: 1 | daily | map/water_supply.c:242-250 |
| Climate effect on water | only the desert fountain radius (−1) | - | map/water_supply.c:348 |
| Contaminated water event | if enabled, population > 200 and cooldown passed: city health −40 (health > 80), −30 (> 60), else −20 | monthly roll | scenario/random_event.c:92-111 |
| Contaminated water chance | 2 of the 128 entries of the monthly random-event table; skipped if Pantheon is working and all gods have happiness ≥ 60 | monthly | scenario/random_event.c:31-39, 170-190 |
| Random event cooldown (months) | very easy 36, easy 30, normal 24, hard 18, very hard 12 | - | game/difficulty.c:18-24 |

## 2.9 Health and sickness

### 2.9.1 House health level

| Component | Value | Source |
|---|---|---|
| House level | level, capped at 10 | city/health.c:309 |
| Clinic and hospital | +50 | city/health.c:312-313 |
| Hospital only | +40 | city/health.c:314-315 |
| Clinic only | +30 | city/health.c:316-317 |
| Bathhouse | +15 | city/health.c:320-322 |
| Barber | +10 | city/health.c:324-326 |
| Fountain water or latrines | +10 | city/health.c:328-331 |
| Mausoleums (city-wide) | small mausoleum +2 each, large mausoleum +5 each; total 0..10 | city/health.c:333-336 |
| Diet | +10 × `num_foods` | city/health.c:338-339 |
| Cap | 40 if the level needs food and `num_foods = 0`; else 100 | city/health.c:340-343 |

### 2.9.2 City health rating

| Rule | Value / formula | Cadence | Source |
|---|---|---|---|
| Small city | population < 200 (or tutorial 1/2): health = 50, target = 50, no sickness updates | monthly | city/health.c:388-392 |
| Target | `Σ(pop × house_health / 100) × 100 / Σ pop` | monthly | city/health.c:413-426 |
| Movement | health moves 2 points per month toward the target | monthly | city/health.c:427-437 |
| Range | 0..100 | - | city/health.c:33-36, 438 |
| City hospital coverage % | `min(100, 1500 × active hospitals × 100 / population)` | daily (tick 33) | city/culture.c:223-224, city/culture.h:21 |
| Hospital coverage bonus | `coverage / 20 × 5` (0..25) | monthly | city/health.c:396 |

### 2.9.3 House sickness level

| Rule | Value / formula | Cadence | Source |
|---|---|---|---|
| Range | 0..100 (`MAX_SICKNESS_LEVEL`); medium ≥ 60, high ≥ 90 | - | city/health.h:12-14 |
| Change only if already sick | the monthly change applies only to houses with `sickness_level > 0` and no plague | monthly | city/health.c:257 |
| Population offset | `clamp((pop − 1) / 1000, 0, 10)` | monthly | city/health.c:395 |
| Delta | `10 − (house_health / 10) × 2 + offset`; if offset = 10 and house health = 100, delta = −1 | monthly | city/health.c:260-265 |
| Neptune GT working | delta − 5 | monthly | city/health.c:267-270 |
| Positive delta reduction | `p = H − H × delta × 5 / 100 + H × hospital_bonus / 100` (H = city health); `delta −= delta × p / 100` | monthly | city/health.c:272-278 |
| Marshland | +5 sickness once per month if any marsh tile is within 3 tiles of the house | monthly | city/health.c:22-23, 370-383 |
| Spread by cart pushers | carts, warehousemen, dockers, native traders, lighthouse/highway suppliers from or to a sick building: each house with people in the 5x5 area, 1/16 chance per tile, gets `1 + dest_sickness / 10` if it has 0 | per tile | figure/service.c:42-60, 195-200, 565-578 |
| Trade and docks | traders and dockers add +1 sickness to docks/warehouses (max 200) | per delivery | city/health.c:84-95, figuretype/trader.c:519, figuretype/docker.c:502 |
| Storage buildings decay | sickness −= sickness × min(100, H + H × hospital_bonus / 100) / 100 | monthly | city/health.c:284-300 |

### 2.9.4 Disease and plague

| Rule | Value / formula | Cadence | Source |
|---|---|---|---|
| House reaches 100 sickness, city health < 40 | house destroyed by plague | monthly | city/health.c:131-136 |
| House reaches 100 sickness, city health ≥ 40 | kills `pop − pop × health / 100` (min 1); house gets plague | monthly | city/health.c:137-154 |
| Dock/warehouse/granary reaches 100 | building gets plague; granary loses half its food; warehouse loses all food and half its wine and oil | monthly | city/health.c:53-82, 164-171 |
| Plague duration | building plague ends when `sickness_duration` reaches 99 (+1 per day) | daily (tick 9) | city/buildings.c:194-214 |
| Doctor treatment | a doctor within 4 tiles sets duration to at least 95 | per tick | figuretype/service.c:330-339 |
| City epidemic gate | only if no house reached 100 this month and city health < 40 | monthly | city/health.c:187-195 |
| City epidemic chance | `rand(0..63) ≤ 40 − health`; Venus curse forces it | monthly | city/health.c:196-204 |
| Sick people | `total_pop × (7 + rand(0..3)) / 100`; city health +10 | monthly | city/health.c:206-210 |
| Deaths | sick − total hospital workers; houses without clinic access are destroyed first, then any house from tents upward | monthly | city/health.c:211-252 |

## 2.10 Entertainment

### 2.10.1 Points and supply buildings

| Venue | Points to a house | Supply building | What the supply adds | Source |
|---|---|---|---|---|
| Theater | 10 | actor colony (actor sets 32 show days) | no extra points; show days only | building/house_service.c:95-97, figuretype/entertainer.c:157-166 |
| Amphitheater | 10 | gladiator school (gladiator show, days1) and actor colony (actor show, days2) | an actor sets the gladiator flag only if days1 > 0; a gladiator sets it only if days2 > 0. The venue roamer is a gladiator when days1 > 0, else an actor. Result: the venue roamer gives 15 only when **both** shows run; one show alone gives 10 | building/house_service.c:106-112, figure/service.c:639-648, building/figure.c:571-575 |
| Arena | 10 | lion house (lion show, days1) | both gladiator and lion tamer check days1: 20 instead of 10 while the lion show runs | building/house_service.c:114-116, figure/service.c:652-661 |
| Colosseum (monument) | 15 | lion house (lion show, days1) and gladiator school (gladiator show, days2) | a gladiator sets the lion flag only if days1 > 0; a lion tamer sets it only if days2 > 0. The venue roamer is a lion tamer when days1 > 0, else a gladiator. Result: the venue roamer gives 25 only when **both** shows run; one show alone gives 15 | building/house_service.c:118-120, figure/service.c:649-665, building/figure.c:735-739 |
| Arena and colosseum together | the house gets the larger value, not the sum | - | building/house_service.c:122 |
| Hippodrome (monument) | 30 | chariot maker (chariot show days1 = 32) | no extra points; show days drive races | building/house_service.c:124-126 |
| Finished colosseum in city | +5 to every house | - | - | building/house_service.c:81, 132-134 |
| Finished hippodrome in city | +5 to every house | - | - | building/house_service.c:82, 128-130 |
| Tavern | 10 with wine; +5 more with meat or fish | wine (and meat or fish) in stock | - | building/house_service.c:99-104, figure/service.c:670-681 |
| Venus module 2 | +10 for houses with Venus access | - | - | building/house_service.c:136-139 |

| Rule | Value / formula | Cadence | Source |
|---|---|---|---|
| Show days | the supply walker sets 32 days on arrival; −1 per day | daily (tick 33) | figuretype/entertainer.c:150-180, building/entertainment.c:16-37 |
| Show slots | theater days1 = actor; amphitheater days1 = gladiator, days2 = actor; colosseum/arena days1 = lion, days2 = gladiator; hippodrome days1 = chariot | - | figuretype/entertainer.c:157-178 |
| Supply walker destination | the venue with the lowest `2 × days_left + distance` on the same road network | per walker | figuretype/entertainer.c:88-148 |
| Actor destinations | theater, amphitheater | - | figuretype/entertainer.c:92-97 |
| Gladiator destinations | amphitheater, colosseum, arena | - | figuretype/entertainer.c:92-97 |
| Lion tamer destinations | colosseum, arena | - | figuretype/entertainer.c:92-97 |
| Charioteer destinations | hippodrome | - | figuretype/entertainer.c:92-97 |
| Supply walker on the way | also gives coverage of the destination venue while it walks, with the same per-walker show rule | per tile | figure/service.c:505-513 |
| Tavern stock use per barkeep | −20 wine; −20 meat and −20 fish if both are present, else −40 of the one present | per spawn | building/figure.c:1278-1283 |

### 2.10.2 City coverage capacities

| Building | People covered | Upgrade bonus (people) | Upgrade condition (building desirability) | Source |
|---|---|---|---|---|
| Theater | 500 | +700 | > 45 | city/culture.h:7-8, building/figure.c:589 |
| Amphitheater | 1500 | +500 | > 45 | city/culture.h:9-10, building/figure.c:536 |
| Tavern | 1000 | +500 | > 45 | city/culture.h:11-12, building/figure.c:1257 |
| Arena | 2500 | +500 | > 45 | city/culture.h:13-14, building/figure.c:695 |
| Colosseum | 100 % when the monument works, else 0 % | - | - | city/culture.c:140-144 |
| Hippodrome | 100 % when the monument works, else 0 % | - | - | city/culture.c:134-138 |
| Coverage % | `min(100, people × 100 / city population)` | - | - | city/culture.c:119-132 |
| Average entertainment coverage | (hippodrome + colosseum + amphitheater + theater + tavern) / 5 | - | - | city/culture.c:69-72 |

Upgrade counts use `upgrade_level > 0` on active or created buildings (building/count.c:172-181).

### 2.10.3 Festivals (sentiment boost)

| Rule | Value / formula | Cadence | Source |
|---|---|---|---|
| First festival in 12 months | small +6, large +9, grand +18 to the festival sentiment boost | on festival | city/festival.c:168-176 |
| Second festival in 12 months | small +2, large +3, grand +9 | on festival | city/festival.c:177-183 |
| Boost decay | boost × 0.84 | monthly | city/sentiment.c:23, 162-166 |

The use of the boost in the sentiment formula is in the sentiment chapter (city/sentiment.c:348, not analysed here).

## 2.11 Education

| Building | People covered | Upgrade bonus | Upgrade condition | Age group used | Source |
|---|---|---|---|---|---|
| School | 75 | +150 | desirability > 40 | ages 0–13 | city/culture.h:15-16, building/figure.c:1018, city/population.c:259 |
| Library | 800 | +900 | desirability > 50 | whole population | city/culture.h:17-18, building/figure.c:1069, city/culture.c:217-218 |
| Academy | 100 | +50 | desirability ≥ 60 | ages 14–20 | city/culture.h:19-20, building/figure.c:1100, city/population.c:260 |
| Coverage % | `min(100, people × 100 / age group)` | - | - | - | city/culture.c:215-220 |

House education level rules are in 2.7.3.

## 2.12 Religion

### 2.12.1 House religion

Only a priest sets a god flag on a house. Lararia, shrines, oracles, nymphaea and mausoleums spawn no priest. They raise only the city coverage % (2.12.2).

| Rule | Value / formula | Source |
|---|---|---|
| Gods per house | number of god flags > 0 (0..5) | building/house_service.c:154-169 |
| Small/large temple priest | the god of the temple | figure/service.c:584-619 |
| Grand temple priest | the god of the temple | figure/service.c:589-622 |
| Pantheon priest | all five gods + Pantheon access | figure/service.c:623-630 |
| Grand temples and Pantheon spawn with | the temple spawn routine (table 2.7.5) | building/figure.c:2325-2330 |

### 2.12.2 City religion coverage per god

`raw = 10 × lararia + 500 × (oracles + small mausoleums) + 750 × (nymphaea + large mausoleums) + 50 × shrines of the god + 750 × small temples + 3000 × large temples + 1500 × Pantheon + 5000 × grand temple of the god`. Coverage % = `min(100, raw × 100 / population)` (city/culture.c:152-201).

| Building | People per building | Gods | Count rule | Source |
|---|---|---|---|---|
| Lararium | 10 | all five | total (built), no workers needed | city/culture.c:13, 148 |
| Shrine | 50 | own god | total (built) | city/culture.c:14, 156 |
| Small temple | 750 | own god | active (workers) | city/culture.c:15, 157 |
| Large temple | 3000 | own god | active | city/culture.c:16, 158 |
| Oracle | 500 | all five | active (finished) | city/culture.c:17, 147, 154 |
| Small mausoleum | 500 | all five | active (finished) | city/culture.c:150, 154 |
| Nymphaeum | 750 | all five | active (finished) | city/culture.c:18, 149, 155 |
| Large mausoleum | 750 | all five | active (finished) | city/culture.c:151, 155 |
| Pantheon | 1500 | all five | active | city/culture.c:19, 159 |
| Grand temple | 5000 | own god | active | city/culture.c:20, 160 |
| City religion coverage | average of the five god %s | - | - | city/culture.c:204-210 |

"Active" for oracle, nymphaeum and mausoleums means the monument is finished (building/building.c:839-844). The effect of coverage on god moods is in the religion chapter (not analysed here).

## 2.13 Fire, collapse, crime

### 2.13.1 Risk accumulation

| Rule | Value / formula | Cadence | Source |
|---|---|---|---|
| Checks skipped | city population < 10 | daily (tick 44) | building/maintenance.c:177-179 |
| Excluded buildings | fire-proof buildings; hippodrome secondary parts | daily | building/maintenance.c:182-187 |
| Random match | `(id + map_random(tile)) & 7 == global random & 7` (1 in 8 per day) | daily | building/maintenance.c:176, 188 |
| Damage risk | +1 per day; +3 on a random match | daily | building/maintenance.c:190 |
| Tents | damage risk is reset to 0 (level ≤ large tent) | daily | building/maintenance.c:194-196 |
| Collapse | damage risk > 200 | daily | building/maintenance.c:197-201 |
| Fire increase (only on a random match) | non-house +5; empty house 0; tent/shack (≤ large shack) +10; hovel..grand insula +5; villa and palace +2 | daily | building/maintenance.c:203-215 |
| Climate | northern: fire increase = 0; desert: +3 | daily | building/maintenance.c:219-223 |
| Fire | fire risk > 100 | daily | building/maintenance.c:227-230 |
| Days to collapse (derived) | about 200 / 1.25 = 160 days (10 months) without an engineer | - | derived |
| Engineer / work-camp architect | sets `damage_risk = 0` on every building in the 5x5 area | per tile | figure/service.c:296-305, 683-696 |
| Prefect | sets `fire_risk = 0` on every building in the 5x5 area | per tile | figure/service.c:307-316, 697-703 |
| Fire-proof houses | none of the house rows set `fire_proof` | - | building/properties.c:138-637 |

### 2.13.2 Burning ruins and rubble

| Rule | Value / formula | Cadence | Source |
|---|---|---|---|
| House on fire | its people are removed from the population | on fire | building/destruction.c:54-56 |
| Fire duration start | `(house_figure_generation_delay & 7) + 1` (1..8) | on fire | building/destruction.c:95 |
| Ruin becomes rubble | fire duration > 32 | daily (tick 43) | building/maintenance.c:57-64 |
| Spread interval | every 8 days (every 4 days in desert) | daily | building/maintenance.c:69-77 |
| Spread chance | additional 1 in 4 check | daily | building/maintenance.c:78-80 |
| Spread target | the first non-fire-proof building in the yearly fire direction, then the two neighbouring directions | daily | building/maintenance.c:38-41, 81-110 |
| Rubble desirability | −2/1/1/2 | daily | map/desirability.c:181-182 |

### 2.13.3 Criminals and rioters

| Rule | Value / formula | Cadence | Source |
|---|---|---|---|
| Executions games active | no criminals | daily (tick 45) | figuretype/crime.c:221-223 |
| Candidate house | the house with the lowest happiness below 50 | daily | figuretype/crime.c:233-247 |
| Cooldown | 10 days after a crime | daily | city/sentiment.c:33, 144-154, figuretype/crime.c:248-251 |
| Crime gate | `random_byte (0..127) ≥ city sentiment + 20` | daily | figuretype/crime.c:256-257, core/random.c:61-64 |
| Side effect | the candidate house happiness +5 | on crime | figuretype/crime.c:258 |
| Happiness ≤ 15 and ≥ 5 % of people below 25 happiness | rioters, looters and robbers, each `clamp(unhappy / 100, 1, 20)` | on crime | figuretype/crime.c:259-266 |
| Happiness ≤ 15, fewer unhappy | 3 looters and 3 robbers | on crime | figuretype/crime.c:267-269 |
| Happiness 16..29 | 1 looter (2 if < 20) | on crime | figuretype/crime.c:271-272 |
| Happiness 30..44 | 1 robber | on crime | figuretype/crime.c:273-274 |
| Happiness 45..49 | protester | on crime | figuretype/crime.c:275-276 |
| Rioter limit | no new rioters if rioters > population / 500 | on crime | figuretype/crime.c:135-137 |
| Robber limit | needs treasury ≥ 400 | on crime | figuretype/crime.c:184-186 |
| Robber theft | treasury / 40; if > 400 then 400 − rand(0..63) | on theft | figuretype/crime.c:105-120 |
| Looter theft | granary −100 of one food; warehouse −1 load | on theft | figuretype/crime.c:89-103 |
| Rioter target | destroys an adjacent building; skips houses below small casa, storage, forts, water buildings, market, granary, forum, senate, native buildings and fire-proof buildings (except gatehouse and palisades) | per tile | figuretype/crime.c:499-557 |
| Strikers | industry buildings on strike produce protesters | daily | figuretype/crime.c:225-231 |
| Prefect sees happiness | the prefect records the lowest happiness it passes (used for its behaviour) | per tile | figure/service.c:313-315, 697-702 |

## 2.14 Grand temple and Pantheon modules: summary for housing

| Effect | Rule | Source |
|---|---|---|
| Venus GT working (base) | devolve delay 21 days; goods target 12 instead of 8; statue/garden/temple desirability bonus | building/house_evolution.c:578-582, figure/service.c:406-409, map/desirability.c:115-121 |
| Venus module 1 | Venus temples distribute wine to houses and taverns; counts as one wine source | building/figure.c:1357-1360, figure/service.c:612-618, city/trade.c:19-21 |
| Venus module 2 | +10 entertainment and house desirability bonus for houses with Venus access | building/house_service.c:136-139, map/desirability.c:90-106 |
| Neptune GT working (base) | well +1, fountain +1, reservoir +2 radius; sickness delta −5 | map/water_supply.c:346-374, city/health.c:267-270 |
| Neptune module 1 | Neptune temples send charioteers (hippodrome coverage) | building/figure.c:1318-1326 |
| Neptune module 2 | GT acts as a reservoir; +5 % house capacity with Neptune access | map/water_supply.c:231-235, building/house_population.c:64-68 |
| Ceres module 1 | houses with Ceres access eat 40 % instead of 50 % of population | city/resource.c:519-531 |
| Ceres module 2 | Ceres temples fetch and distribute food | building/figure.c:1352-1355, figure/service.c:584-588 |
| Mercury module 1 | pottery and furniture consumption −20 % (all houses) | building/house_evolution.c:535-539 |
| Mercury module 2 | oil and wine consumption −20 % (houses with Mercury access) | building/house_evolution.c:540-544 |
| Mars module 1 | Mars temples collect food offerings for the mess hall | figure/service.c:602-608, building/figure.c:1330-1350 |
| Mars module 2 | all goods consumption −10 % (houses with Mars access) | building/house_evolution.c:545-551 |
| Pantheon working (base) | temple/oracle/mausoleum levies × 3/4; skips bad random events when all gods ≥ 60 happiness | building/building.c:1014-1020, scenario/random_event.c:174 |
| Pantheon module 1 | each temple keeps one destination priest to the Pantheon | building/figure.c:1240-1248, 1362-1370 |
| Pantheon module 2 | houses with Pantheon access use level − 1 for devolve and current requirements | building/house_evolution.c:194-206 |
| Finished colosseum / hippodrome monument | +5 entertainment each to every house; 100 % city coverage | building/house_service.c:128-134, city/culture.c:134-144 |

## 2.15 Unverified items

- `empire_city_count_wine_sources()` rules (empire chapter).
- The use of the festival boost, `house_happiness` and crime in the sentiment formula (sentiment chapter).
- The effect of religion coverage % on god moods (religion chapter).
- Worker allocation details beyond `percentage_houses_covered` (labour chapter).
- Tourist and beggar behaviour.

## Appendix 2.A Building desirability and labour table (defaults)

Columns: size, cost, desirability value, step, step size, range, labourers. Source: the `.building_model_data` line of each entry in building/properties.c. The runtime model can differ: grand garden and dolphin fountain are zero at runtime (building/properties.c:2367-2379), and a scenario can change any value (scenario/event/action_types.c:772-781).

| Building | Size | Cost | Value | Step | Step size | Range | Labourers | Source |
|---|---|---|---|---|---|---|---|---|
| CLEAR_LAND | - | 2 | 0 | 0 | 0 | 0 | 0 | building/properties.c:93 |
| REPAIR_LAND | - | 3 | 0 | 0 | 0 | 0 | 0 | building/properties.c:99 |
| ROAD | 1 | 4 | 0 | 0 | 0 | 0 | 0 | building/properties.c:106 |
| WALL | 1 | 12 | 0 | 0 | 0 | 0 | 0 | building/properties.c:118 |
| DRAGGABLE_RESERVOIR | 1 | 30 | -6 | 1 | 2 | 3 | 0 | building/properties.c:125 |
| AQUEDUCT | 1 | 8 | -2 | 1 | 1 | 2 | 0 | building/properties.c:135 |
| AMPHITHEATER | 3 | 100 | 4 | 1 | -1 | 4 | 12 | building/properties.c:643 |
| THEATER | 2 | 50 | 2 | 1 | -1 | 2 | 8 | building/properties.c:651 |
| HIPPODROME | 5 | 3500 | -3 | 1 | 1 | 3 | 150 | building/properties.c:660 |
| COLOSSEUM | 5 | 1500 | -3 | 1 | 1 | 3 | 100 | building/properties.c:669 |
| GLADIATOR_SCHOOL | 3 | 75 | -3 | 1 | 1 | 3 | 8 | building/properties.c:677 |
| LION_HOUSE | 3 | 75 | -3 | 1 | 1 | 3 | 8 | building/properties.c:685 |
| ACTOR_COLONY | 3 | 50 | 2 | 1 | -1 | 2 | 5 | building/properties.c:693 |
| CHARIOT_MAKER | 3 | 75 | -3 | 1 | 1 | 3 | 10 | building/properties.c:701 |
| PLAZA | 1 | 15 | 4 | 1 | -2 | 2 | 0 | building/properties.c:709 |
| GARDENS | 1 | 12 | 3 | 1 | -1 | 3 | 0 | building/properties.c:720 |
| FORT_LEGIONARIES | 3 | 1000 | -20 | 2 | 2 | 8 | 0 | building/properties.c:740 |
| FORT_JAVELIN | 3 | 1000 | -20 | 2 | 2 | 8 | 0 | building/properties.c:750 |
| FORT_MOUNTED | 3 | 1000 | -20 | 2 | 2 | 8 | 0 | building/properties.c:760 |
| FORT_ARCHERS | 3 | 1000 | -20 | 2 | 2 | 8 | 0 | building/properties.c:770 |
| FORT_AUXILIA_INFANTRY | 3 | 1000 | -20 | 2 | 2 | 8 | 0 | building/properties.c:780 |
| SMALL_STATUE | 1 | 12 | 3 | 1 | -1 | 3 | 0 | building/properties.c:791 |
| MEDIUM_STATUE | 2 | 60 | 10 | 1 | -2 | 4 | 0 | building/properties.c:802 |
| LARGE_STATUE | 3 | 150 | 14 | 2 | -2 | 5 | 0 | building/properties.c:813 |
| DOCTOR | 1 | 30 | 0 | 0 | 0 | 0 | 5 | building/properties.c:821 |
| HOSPITAL | 3 | 300 | -2 | 1 | 1 | 2 | 30 | building/properties.c:829 |
| BATHHOUSE | 2 | 50 | 4 | 1 | -1 | 4 | 10 | building/properties.c:837 |
| BARBER | 1 | 25 | 2 | 1 | -1 | 2 | 2 | building/properties.c:845 |
| SCHOOL | 2 | 50 | -2 | 1 | 1 | 2 | 10 | building/properties.c:857 |
| ACADEMY | 3 | 100 | 4 | 1 | 1 | 4 | 30 | building/properties.c:865 |
| LIBRARY | 2 | 75 | 4 | 1 | -1 | 4 | 20 | building/properties.c:874 |
| PREFECTURE | 1 | 30 | -2 | 1 | 1 | 2 | 6 | building/properties.c:883 |
| TRIUMPHAL_ARCH | 3 | 0 | 18 | 2 | 3 | 5 | 0 | building/properties.c:891 |
| GATEHOUSE | 2 | 100 | -4 | 1 | 1 | 3 | 0 | building/properties.c:903 |
| TOWER | 2 | 150 | -8 | 1 | 2 | 3 | 6 | building/properties.c:914 |
| SMALL_TEMPLE_CERES | 2 | 50 | 4 | 2 | -1 | 6 | 2 | building/properties.c:925 |
| SMALL_TEMPLE_NEPTUNE | 2 | 50 | 4 | 2 | -1 | 6 | 2 | building/properties.c:936 |
| SMALL_TEMPLE_MERCURY | 2 | 50 | 4 | 2 | -1 | 6 | 2 | building/properties.c:947 |
| SMALL_TEMPLE_MARS | 2 | 50 | 4 | 2 | -1 | 6 | 2 | building/properties.c:958 |
| SMALL_TEMPLE_VENUS | 2 | 50 | 4 | 2 | -1 | 6 | 2 | building/properties.c:969 |
| LARGE_TEMPLE_CERES | 3 | 150 | 14 | 2 | -2 | 5 | 5 | building/properties.c:982 |
| LARGE_TEMPLE_NEPTUNE | 3 | 150 | 14 | 2 | -2 | 5 | 5 | building/properties.c:995 |
| LARGE_TEMPLE_MERCURY | 3 | 150 | 14 | 2 | -2 | 5 | 5 | building/properties.c:1008 |
| LARGE_TEMPLE_MARS | 3 | 150 | 14 | 2 | -2 | 5 | 5 | building/properties.c:1021 |
| LARGE_TEMPLE_VENUS | 3 | 150 | 14 | 2 | -2 | 5 | 5 | building/properties.c:1034 |
| MARKET | 2 | 40 | -2 | 1 | 1 | 6 | 5 | building/properties.c:1042 |
| GRANARY | 3 | 100 | -4 | 1 | 2 | 2 | 6 | building/properties.c:1050 |
| WAREHOUSE | 1 | 70 | -5 | 2 | 2 | 3 | 6 | building/properties.c:1059 |
| SHIPYARD | 2 | 100 | -8 | 2 | 2 | 3 | 10 | building/properties.c:1072 |
| DOCK | 3 | 100 | -8 | 2 | 2 | 3 | 12 | building/properties.c:1080 |
| WHARF | 2 | 60 | -8 | 2 | 2 | 3 | 6 | building/properties.c:1088 |
| GOVERNORS_HOUSE | 3 | 150 | 12 | 2 | -2 | 3 | 0 | building/properties.c:1096 |
| GOVERNORS_VILLA | 4 | 400 | 20 | 2 | -3 | 4 | 0 | building/properties.c:1104 |
| GOVERNORS_PALACE | 5 | 750 | 28 | 2 | -4 | 5 | 0 | building/properties.c:1112 |
| MISSION_POST | 2 | 100 | -3 | 1 | 1 | 2 | 20 | building/properties.c:1121 |
| ENGINEERS_POST | 1 | 30 | 0 | 1 | 1 | 1 | 5 | building/properties.c:1130 |
| LOW_BRIDGE | 1 | 40 | 0 | 0 | 0 | 0 | 0 | building/properties.c:1137 |
| SHIP_BRIDGE | 1 | 100 | 0 | 0 | 0 | 0 | 0 | building/properties.c:1144 |
| SENATE | 5 | 400 | 8 | 2 | -1 | 8 | 30 | building/properties.c:1152 |
| FORUM | 2 | 75 | 3 | 2 | -1 | 2 | 6 | building/properties.c:1160 |
| NATIVE_HUT | 1 | 50 | 0 | 0 | 0 | 0 | 0 | building/properties.c:1169 |
| NATIVE_MEETING | 2 | 50 | 0 | 0 | 0 | 0 | 0 | building/properties.c:1179 |
| RESERVOIR | 3 | 80 | -6 | 1 | 2 | 3 | 0 | building/properties.c:1188 |
| FOUNTAIN | 1 | 15 | 0 | 0 | 0 | 0 | 4 | building/properties.c:1197 |
| WELL | 1 | 5 | -1 | 1 | 2 | 1 | 0 | building/properties.c:1206 |
| NATIVE_CROPS | 1 | 0 | 0 | 0 | 0 | 0 | 0 | building/properties.c:1216 |
| MILITARY_ACADEMY | 3 | 1000 | -3 | 1 | 1 | 3 | 20 | building/properties.c:1225 |
| BARRACKS | 3 | 150 | -6 | 1 | 1 | 3 | 10 | building/properties.c:1234 |
| ORACLE | 2 | 200 | 8 | 2 | -1 | 6 | 0 | building/properties.c:1253 |
| BURNING_RUIN | 1 | 0 | -1 | 1 | 1 | 2 | 0 | building/properties.c:1260 |
| WHEAT_FARM | 3 | 40 | -2 | 1 | 1 | 2 | 10 | building/properties.c:1268 |
| VEGETABLE_FARM | 3 | 40 | -2 | 1 | 1 | 2 | 10 | building/properties.c:1276 |
| FRUIT_FARM | 3 | 40 | 2 | 1 | 1 | 2 | 10 | building/properties.c:1284 |
| OLIVE_FARM | 3 | 40 | 2 | 1 | 1 | 2 | 10 | building/properties.c:1292 |
| VINES_FARM | 3 | 40 | 2 | 1 | 1 | 2 | 10 | building/properties.c:1300 |
| PIG_FARM | 3 | 40 | -2 | 1 | 1 | 2 | 10 | building/properties.c:1308 |
| MARBLE_QUARRY | 2 | 50 | -6 | 1 | 1 | 4 | 10 | building/properties.c:1316 |
| IRON_MINE | 2 | 50 | -6 | 1 | 1 | 4 | 10 | building/properties.c:1324 |
| TIMBER_YARD | 2 | 40 | -4 | 1 | 1 | 3 | 10 | building/properties.c:1332 |
| CLAY_PIT | 2 | 40 | -3 | 1 | 1 | 2 | 10 | building/properties.c:1340 |
| WINE_WORKSHOP | 2 | 45 | -1 | 1 | 1 | 1 | 10 | building/properties.c:1348 |
| OIL_WORKSHOP | 2 | 50 | -4 | 1 | 1 | 2 | 10 | building/properties.c:1356 |
| WEAPONS_WORKSHOP | 2 | 50 | -4 | 1 | 1 | 2 | 10 | building/properties.c:1364 |
| FURNITURE_WORKSHOP | 2 | 40 | -4 | 1 | 1 | 2 | 10 | building/properties.c:1372 |
| POTTERY_WORKSHOP | 2 | 40 | -4 | 1 | 1 | 2 | 10 | building/properties.c:1380 |
| ROADBLOCK | 1 | 12 | 0 | 0 | 0 | 0 | 0 | building/properties.c:1388 |
| WORKCAMP | 3 | 150 | -10 | 2 | 3 | 4 | 20 | building/properties.c:1397 |
| GRAND_TEMPLE_CERES | 7 | 2500 | 20 | 2 | -4 | 8 | 50 | building/properties.c:1409 |
| GRAND_TEMPLE_NEPTUNE | 7 | 2500 | 20 | 2 | -4 | 8 | 50 | building/properties.c:1421 |
| GRAND_TEMPLE_MERCURY | 7 | 2500 | 20 | 2 | -4 | 8 | 50 | building/properties.c:1433 |
| GRAND_TEMPLE_MARS | 7 | 2500 | 20 | 2 | -4 | 8 | 50 | building/properties.c:1445 |
| GRAND_TEMPLE_VENUS | 7 | 2500 | 20 | 2 | -4 | 8 | 50 | building/properties.c:1457 |
| SMALL_POND | 2 | 60 | 10 | 1 | -2 | 4 | 0 | building/properties.c:1484 |
| LARGE_POND | 3 | 150 | 14 | 2 | -2 | 5 | 0 | building/properties.c:1495 |
| PINE_TREE | 1 | 12 | 3 | 1 | -1 | 3 | 0 | building/properties.c:1505 |
| FIR_TREE | 1 | 12 | 3 | 1 | -1 | 3 | 0 | building/properties.c:1515 |
| OAK_TREE | 1 | 12 | 3 | 1 | -1 | 3 | 0 | building/properties.c:1525 |
| ELM_TREE | 1 | 12 | 3 | 1 | -1 | 3 | 0 | building/properties.c:1535 |
| FIG_TREE | 1 | 12 | 3 | 1 | -1 | 3 | 0 | building/properties.c:1545 |
| PLUM_TREE | 1 | 12 | 3 | 1 | -1 | 3 | 0 | building/properties.c:1555 |
| PALM_TREE | 1 | 12 | 3 | 1 | -1 | 3 | 0 | building/properties.c:1565 |
| DATE_TREE | 1 | 12 | 3 | 1 | -1 | 3 | 0 | building/properties.c:1575 |
| PINE_PATH | 1 | 12 | 3 | 1 | -1 | 3 | 0 | building/properties.c:1585 |
| FIR_PATH | 1 | 12 | 3 | 1 | -1 | 3 | 0 | building/properties.c:1595 |
| OAK_PATH | 1 | 12 | 3 | 1 | -1 | 3 | 0 | building/properties.c:1605 |
| ELM_PATH | 1 | 12 | 3 | 1 | -1 | 3 | 0 | building/properties.c:1615 |
| FIG_PATH | 1 | 12 | 3 | 1 | -1 | 3 | 0 | building/properties.c:1625 |
| PLUM_PATH | 1 | 12 | 3 | 1 | -1 | 3 | 0 | building/properties.c:1635 |
| PALM_PATH | 1 | 12 | 3 | 1 | -1 | 3 | 0 | building/properties.c:1645 |
| DATE_PATH | 1 | 12 | 3 | 1 | -1 | 3 | 0 | building/properties.c:1655 |
| PAVILION_BLUE | 1 | 12 | 3 | 1 | -1 | 3 | 0 | building/properties.c:1665 |
| PAVILION_RED | 1 | 12 | 3 | 1 | -1 | 3 | 0 | building/properties.c:1675 |
| PAVILION_ORANGE | 1 | 12 | 3 | 1 | -1 | 3 | 0 | building/properties.c:1685 |
| PAVILION_YELLOW | 1 | 12 | 3 | 1 | -1 | 3 | 0 | building/properties.c:1695 |
| PAVILION_GREEN | 1 | 12 | 3 | 1 | -1 | 3 | 0 | building/properties.c:1705 |
| GODDESS_STATUE | 1 | 12 | 3 | 1 | -1 | 3 | 0 | building/properties.c:1716 |
| SENATOR_STATUE | 1 | 12 | 3 | 1 | -1 | 3 | 0 | building/properties.c:1727 |
| OBELISK | 2 | 60 | 10 | 1 | -2 | 4 | 0 | building/properties.c:1737 |
| PANTHEON | 7 | 3500 | 20 | 2 | -4 | 8 | 50 | building/properties.c:1749 |
| ARCHITECT_GUILD | 2 | 200 | -8 | 1 | 2 | 4 | 12 | building/properties.c:1759 |
| MESS_HALL | 3 | 100 | -8 | 1 | 2 | 4 | 10 | building/properties.c:1769 |
| LIGHTHOUSE | 3 | 1000 | 6 | 1 | -1 | 4 | 20 | building/properties.c:1779 |
| TAVERN | 2 | 40 | -2 | 1 | 1 | 6 | 8 | building/properties.c:1796 |
| GRAND_GARDEN | 2 | 400 | 0 | 0 | 0 | 0 | 0 | building/properties.c:1805 |
| ARENA | 3 | 500 | -3 | 1 | 1 | 3 | 25 | building/properties.c:1814 |
| HORSE_STATUE | 3 | 150 | 14 | 2 | -2 | 5 | 0 | building/properties.c:1825 |
| DOLPHIN_FOUNTAIN | 2 | 60 | 10 | 1 | -2 | 4 | 0 | building/properties.c:1834 |
| HEDGE_DARK | 1 | 12 | 3 | 1 | -1 | 3 | 0 | building/properties.c:1844 |
| HEDGE_LIGHT | 1 | 12 | 3 | 1 | -1 | 3 | 0 | building/properties.c:1854 |
| LOOPED_GARDEN_WALL | 1 | 12 | 3 | 1 | -1 | 3 | 0 | building/properties.c:1864 |
| LEGION_STATUE | 2 | 60 | 10 | 1 | -2 | 4 | 0 | building/properties.c:1875 |
| DECORATIVE_COLUMN | 1 | 12 | 3 | 1 | -1 | 3 | 0 | building/properties.c:1885 |
| COLONNADE | 1 | 12 | 3 | 1 | -1 | 3 | 0 | building/properties.c:1895 |
| GARDEN_PATH | 1 | 12 | 3 | 1 | -1 | 3 | 0 | building/properties.c:1905 |
| LARARIUM | 1 | 45 | 4 | 1 | -1 | 3 | 0 | building/properties.c:1915 |
| NYMPHAEUM | 3 | 400 | 12 | 2 | -1 | 6 | 0 | building/properties.c:1927 |
| SMALL_MAUSOLEUM | 2 | 250 | -8 | 1 | 3 | 5 | 0 | building/properties.c:1940 |
| LARGE_MAUSOLEUM | 3 | 500 | -10 | 1 | 3 | 6 | 0 | building/properties.c:1952 |
| WATCHTOWER | 2 | 100 | -6 | 1 | 2 | 3 | 8 | building/properties.c:1964 |
| CARAVANSERAI | 4 | 500 | -10 | 2 | 3 | 4 | 20 | building/properties.c:1974 |
| ROOFED_GARDEN_WALL | 1 | 12 | 3 | 1 | -1 | 3 | 0 | building/properties.c:1984 |
| ROOFED_GARDEN_WALL_GATE | 1 | 12 | 0 | 0 | 0 | 0 | 0 | building/properties.c:1993 |
| PALISADE | 1 | 6 | 0 | 0 | 0 | 0 | 0 | building/properties.c:2004 |
| HEDGE_GATE_DARK | 1 | 12 | 0 | 0 | 0 | 0 | 0 | building/properties.c:2013 |
| HEDGE_GATE_LIGHT | 1 | 12 | 0 | 0 | 0 | 0 | 0 | building/properties.c:2022 |
| PALISADE_GATE | 1 | 12 | 0 | 0 | 0 | 0 | 0 | building/properties.c:2033 |
| GLADIATOR_STATUE | 1 | 12 | 3 | 1 | -1 | 3 | 0 | building/properties.c:2043 |
| HIGHWAY | 2 | 100 | -4 | 1 | 2 | 2 | 0 | building/properties.c:2052 |
| GOLD_MINE | 2 | 100 | -6 | 1 | 1 | 4 | 30 | building/properties.c:2060 |
| STONE_QUARRY | 2 | 60 | -6 | 1 | 1 | 4 | 10 | building/properties.c:2068 |
| SAND_PIT | 2 | 40 | -6 | 1 | 1 | 4 | 10 | building/properties.c:2076 |
| BRICKWORKS | 2 | 80 | -3 | 1 | 1 | 3 | 10 | building/properties.c:2085 |
| CONCRETE_MAKER | 2 | 60 | -3 | 1 | 1 | 3 | 10 | building/properties.c:2094 |
| CITY_MINT | 3 | 250 | -3 | 1 | 1 | 3 | 40 | building/properties.c:2104 |
| DEPOT | 2 | 100 | -3 | 1 | 1 | 2 | 15 | building/properties.c:2113 |
| LOOPED_GARDEN_GATE | 1 | 12 | 0 | 0 | 0 | 0 | 0 | building/properties.c:2122 |
| PANELLED_GARDEN_GATE | 1 | 12 | 0 | 0 | 0 | 0 | 0 | building/properties.c:2131 |
| PANELLED_GARDEN_WALL | 1 | 12 | 3 | 1 | -1 | 3 | 0 | building/properties.c:2141 |
| SHRINE_CERES | 1 | 45 | 4 | 1 | -1 | 3 | 0 | building/properties.c:2152 |
| SHRINE_MARS | 1 | 45 | 4 | 1 | -1 | 3 | 0 | building/properties.c:2163 |
| SHRINE_MERCURY | 1 | 45 | 4 | 1 | -1 | 3 | 0 | building/properties.c:2174 |
| SHRINE_NEPTUNE | 1 | 45 | 4 | 1 | -1 | 3 | 0 | building/properties.c:2185 |
| SHRINE_VENUS | 1 | 45 | 4 | 1 | -1 | 3 | 0 | building/properties.c:2196 |
| OVERGROWN_GARDENS | 1 | 12 | 3 | 1 | -1 | 3 | 0 | building/properties.c:2206 |
| ARMOURY | 2 | 50 | -5 | 1 | 1 | 4 | 6 | building/properties.c:2216 |
| LATRINES | 1 | 15 | 0 | 0 | 0 | 0 | 2 | building/properties.c:2225 |
| NATIVE_HUT_ALT | 1 | 50 | 0 | 0 | 0 | 0 | 0 | building/properties.c:2235 |
| NATIVE_DECORATION | 1 | 0 | 6 | 1 | -1 | 4 | 0 | building/properties.c:2245 |
| NATIVE_MONUMENT | 4 | 0 | 15 | 2 | -2 | 8 | 0 | building/properties.c:2255 |
| NATIVE_WATCHTOWER | 1 | 0 | -10 | 1 | 2 | 4 | 0 | building/properties.c:2265 |
| HIGHWAY_STATION | 3 | 200 | -2 | 1 | 1 | 3 | 12 | building/properties.c:2275 |
| WILLOW_TREE | 1 | 12 | 3 | 1 | -1 | 3 | 0 | building/properties.c:2285 |
| NATIVE_WELL | 1 | 0 | 0 | 0 | 0 | 0 | 0 | building/properties.c:2294 |
| NATIVE_LARGE_HUT_ALT | 2 | 50 | 0 | 0 | 0 | 0 | 0 | building/properties.c:2304 |
| NATIVE_HUT_ALT_2 | 1 | 50 | 0 | 0 | 0 | 0 | 0 | building/properties.c:2314 |
| NATIVE_LARGE_HUT_ALT_2 | 2 | 50 | 0 | 0 | 0 | 0 | 0 | building/properties.c:2324 |
| NATIVE_PALISADE | 1 | 0 | 0 | 0 | 0 | 0 | 0 | building/properties.c:2334 |
