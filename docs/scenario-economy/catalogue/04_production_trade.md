# Chapter 4: Production, Storage, Logistics and Trade

Source: Augustus upstream commit `dae1899`. All paths are relative to `src/`. A citation `file:N` is a line number. A citation `file:N-M` is a line range.

## 4.0 Read this first

| Rule | Value / formula | Cadence | Source |
|---|---|---|---|
| Ticks per day | 50 | fixed | game/time.h:13 |
| Days per month | 16 | fixed | game/time.h:14 |
| Months per year | 12 | fixed | game/time.h:15 |
| One cartload ("load") | 100 units | fixed | game/resource.h:72 |
| Industry production step | `building_industry_update_production()` runs at tick 20 and tick 46 of each day, so 2 steps per day | 2 per day | game/tick.c:169, game/tick.c:193 |
| Building figure spawn (cart pushers, market buyers, dockers, work camp workers) | `building_figure_generate()` runs at tick 31 | 1 per day | game/tick.c:179 |
| Trade update and trader generation | `city_trade_update()` runs at tick 32 | 1 per day | game/tick.c:180 |
| Granary "getting" stock cache | `building_granaries_calculate_stocks()` at tick 8 | 1 per day | game/tick.c:163 |
| Warehouse stock cache | tick 16 | 1 per day | game/tick.c:166 |
| Food stock calculation and "Rome supplies wheat" refill | tick 17 | 1 per day | game/tick.c:167 |
| House goods consumption | tick 39, on day 0 (all houses) and day 7 (houses larger than 1x1) | 2 per month (1 for 1x1) | game/tick.c:187, building/house_evolution.c:598 |
| Monthly industry statistics and strikes | `building_industry_advance_stats()`, `building_industry_start_strikes()` | 1 per month | game/tick.c:98-99 |
| Yearly trade quota reset | `empire_city_reset_yearly_trade_amounts()` | 1 per year | game/tick.c:77 |

Scenario overrides. The tables in this chapter give the **default** values. A scenario can change these values:

- Production per month for each resource is saved in the scenario and the save (game/resource.c:361-376).
- Building cost and laborers come from model data that the scenario can change (building/properties.c:2409-2437).
- Monument phase costs can be changed by a scenario (building/monument.c:274-291).
- Trade prices can be changed by scenario price changes and events (scenario/price_change.c:62-70, scenario/event/action_types.c:458, scenario/event/action_types.c:544).
- Trade route limits come from the empire data (empire/city.c:359-377, empire/trade_route.c:147-157, empire/trade_route.c:214-221).

## 4.1 Production formula

| Rule | Value / formula | Cadence | Source |
|---|---|---|---|
| Max progress of an industry | `max = 16 * 2 * laborers * 100 / production_per_month` (integer division) | per check | building/industry.c:72-77, core/calc.c:27-31 |
| City Mint max progress | Uses the denarii rate (200) for both denarii mode and gold mode | per check | building/industry.c:74-75 |
| Progress per production step | `+= num_workers` | 2 per day | building/industry.c:290, building/industry.c:301 |
| Progress cap | Progress cannot exceed `max` | per step | building/industry.c:303-306 |
| Days per load at full staff | `1600 / production_per_month`. The laborer count cancels out. The real cycle rounds up to the next daily spawn check. | derived | building/industry.c:76, building/industry.c:290 |
| Days per load at partial staff | `1600 * laborers / (production_per_month * num_workers)` | derived | same |
| Loads per month at full staff | `production_per_month / 100` | derived | same |
| Northern climate | Wheat production per month is halved (160 → 80) | always | game/resource.c:335-337 |
| Production requires | Building in use, `houses_covered > 0` (labor access), `num_workers > 0`, no strike, enough raw material in stock | per step | building/industry.c:243-273 |
| Output | When `progress >= max`, the next daily spawn check (tick 31)  creates 1 cart pusher with 1 load and resets progress to 0 | 1 per day check | building/figure.c:1488-1496, building/industry.c:340-352 |
| One cart pusher limit | A producer does not spawn a new cart pusher while its old cart pusher is alive. Progress stays capped at `max` while it waits. | per day | building/figure.c:1485-1487 |
| Cart pusher start delay | The cart pusher waits 30 ticks before it selects a destination | per trip | building/figure.c:1495, figuretype/cartpusher.c:369-372 |
| Road needed | The producer needs road access to spawn the cart pusher | per day | building/figure.c:1483 |
| Average production statistic | 12-month rolling average, used for the efficiency display only | 1 per month | building/industry.c:26, building/industry.c:579-605 |

Logistics consequence. A producer makes a new load only after its previous cart pusher is gone. If the round trip of the cart pusher takes longer than "days per load", the real output is lower than the table value.

## 4.2 Industry table (default values)

Days per load = `1600 / P` at full staff. "Input per output" is in units (100 units = 1 load).

| Building | Size | Cost | Workers | Output | P (per month) | Days per load (full staff) | Loads per month | Input per output | Placement rule | Source |
|---|---|---|---|---|---|---|---|---|---|---|
| Wheat farm | 3 | 40 | 10 | Wheat | 160 (80 northern) | 10 (20 northern) | 1.6 (0.8) | none | Meadow tile within 1 tile of the 3x3 footprint | building/properties.c:1263, game/resource.c:65, building/construction.c:675-681, building/construction.c:1401-1405 |
| Vegetable farm | 3 | 40 | 10 | Vegetables | 80 | 20 | 0.8 | none | Meadow, same | building/properties.c:1271, game/resource.c:66 |
| Fruit farm | 3 | 40 | 10 | Fruit | 80 | 20 | 0.8 | none | Meadow, same | building/properties.c:1279, game/resource.c:67 |
| Olive farm | 3 | 40 | 10 | Olives | 80 | 20 | 0.8 | none | Meadow, same | building/properties.c:1287, game/resource.c:72 |
| Vines farm | 3 | 40 | 10 | Vines | 80 | 20 | 0.8 | none | Meadow, same | building/properties.c:1295, game/resource.c:73 |
| Pig farm | 3 | 40 | 10 | Meat | 80 | 20 | 0.8 | none | Meadow, same | building/properties.c:1303, game/resource.c:68 |
| Clay pit | 2 | 40 | 10 | Clay | 80 | 20 | 0.8 | none | Water or beach tile within 3 tiles | building/properties.c:1335, game/resource.c:70, building/construction.c:692-693, building/construction.c:1416-1420 |
| Timber yard | 2 | 40 | 10 | Timber | 80 | 20 | 0.8 | none | Tree or shrub tile within 1 tile | building/properties.c:1327, game/resource.c:71, building/construction.c:689-690, building/construction.c:1411-1415 |
| Iron mine | 2 | 50 | 10 | Iron | 80 | 20 | 0.8 | none | Rock tile within 1 tile (entry and exit flag tiles do not count) | building/properties.c:1319, game/resource.c:74, building/construction.c:683-687, building/construction.c:1406-1410, map/terrain.c:257-269 |
| Marble quarry | 2 | 50 | 10 | Marble | 40 | 40 | 0.4 | none | Rock, same | building/properties.c:1311, game/resource.c:75 |
| Stone quarry | 2 | 60 | 10 | Stone | 80 | 20 | 0.8 | none | Rock, same | building/properties.c:2063, game/resource.c:78 |
| Gold mine | 2 | 100 | 30 | Gold | 20 | 80 | 0.2 | none (no denarii cost) | Rock, same | building/properties.c:2055, game/resource.c:76 |
| Sand pit | 2 | 40 | 10 | Sand | 120 | 13.3 (14 with integer rounding) | 1.2 | none | Water or beach tile within 9 tiles | building/properties.c:2071, game/resource.c:77, building/construction.c:698-699, building/construction.c:1421-1425 |
| Pottery workshop | 2 | 40 | 10 | Pottery | 40 | 40 | 0.4 | 100 clay | road access | building/properties.c:1375, game/resource.c:79, game/resource.c:93 |
| Furniture workshop | 2 | 40 | 10 | Furniture | 40 | 40 | 0.4 | 100 timber | road access | building/properties.c:1367, game/resource.c:80, game/resource.c:94 |
| Oil workshop | 2 | 50 | 10 | Oil | 40 | 40 | 0.4 | 100 olives | road access | building/properties.c:1351, game/resource.c:81, game/resource.c:95 |
| Wine workshop | 2 | 45 | 10 | Wine | 40 | 40 | 0.4 | 100 vines | road access | building/properties.c:1343, game/resource.c:82, game/resource.c:96 |
| Weapons workshop | 2 | 50 | 10 | Weapons | 40 | 40 | 0.4 | 100 iron | road access | building/properties.c:1359, game/resource.c:83, game/resource.c:97 |
| Brickworks | 2 | 80 | 10 | Bricks | 60 | 26.7 | 0.6 | 50 sand + 50 clay | road access | building/properties.c:2079, game/resource.c:85, game/resource.c:100-101 |
| Concrete maker | 2 | 60 | 10 | Concrete | 120 | 13.3 with reservoir range; 26.7 with fountain or well only; never without water | 1.2 / 0.6 / 0 | 50 sand | road access; water source (see 4.4) | building/properties.c:2088, game/resource.c:84, game/resource.c:99 |
| City Mint (denarii mode) | 3 | 250 | 40 | 100 Dn into treasury | 200 | 8.5 (strict `progress > max`, 17 steps) | 1.88 (≈188 Dn) | 20 gold units per 100 Dn | monument (see 4.5) | building/properties.c:2097, game/resource.c:86, game/resource.c:98, building/industry.c:155-221 |
| City Mint (gold mode) | 3 | 250 | 40 | 1 load gold | uses 200 | 8 | 2 | 600 Dn per load | monument | building/industry.c:181-195 |
| Wharf | 2 | 60 | 6 | Fish | 100 (display only) | see 4.6 | see 4.6 | none | water | building/properties.c:1083, game/resource.c:69 |

Supply chain definition: game/resource.c:92-102. A raw material is a resource that is not food, is not a good in a supply chain, and is lower than denarii in the enum (game/resource.c:109-113).

## 4.3 Farm rules, blessings, curses, strikes, mothballing

| Rule | Value / formula | Cadence | Source |
|---|---|---|---|
| Farm types | Wheat, vegetable, fruit, olive, vines, pig farm | — | building/industry.c:30-33 |
| Meadow | Placement rule only. Production does not read meadow or any fertility value. | at placement | building/construction.c:1401-1405, building/industry.c:235-311 |
| Timber yard tree depletion | None. Production does not read tree tiles. | — | building/industry.c:235-311 |
| Farm crop image | Crop image shows `progress * 100 / max` percent | per step | building/industry.c:79-83 |
| Ceres blessing (farms) | Each farm in use: progress = max (instant harvest), curse cleared, `blessing_days_left = 16` | on blessing | city/gods.c:68, building/industry.c:379-395 |
| Farm blessing effect | While `blessing_days_left > 0`, farm progress per step is doubled (`+= 2 * num_workers`) | 16 days | building/industry.c:287-293 |
| Ceres small curse | All farms: progress = 0, blessing cleared, `curse_days_left = 4`; City Mint progress = 0, curse 4 days | on curse | city/gods.c:98, building/industry.c:426-447 |
| Ceres large curse | Same, `curse_days_left = 48` | on curse | city/gods.c:138, building/industry.c:437 |
| Curse effect | No progress while `curse_days_left > 0`; counter decreases by 1 per day | daily | building/industry.c:281-286 |
| Mercury blessing (workshops) | Each staffed workshop (incl. brickworks, concrete maker, City Mint): each raw material stock that is above 0 and below `3 * raw_amount` is set to `3 * raw_amount`; if progress > 0, progress = max | on blessing | city/gods.c:76, building/industry.c:28, building/industry.c:397-424 |
| Mercury small curse | The fullest granary or warehouse loses 16 loads | on curse | city/gods.c:113, building/granary.c:22, building/granary.c:646-695 |
| Mercury large curse | The fullest granary or warehouse is destroyed by fire | on curse | city/gods.c:153, building/granary.c:679-684 |
| Strike start check | Only if sentiment < 55 | 1 per month | building/industry.c:607-611 |
| Strike chance | `(60 - sentiment)^2 / 36` percent | 1 per month | building/industry.c:612-616 |
| Buildings that strike | `population / 2000`, bounded 1..12, random industries | on strike | building/industry.c:617, building/industry.c:85-120 |
| Strike duration | 48 days; -1 per day; -3 extra per day if sentiment > 50; ends at once if sentiment > 65 | daily | building/industry.c:93, building/industry.c:247-257 |
| Strike effect | No progress | per step | building/industry.c:267 |
| Mothball (per building) | State becomes MOTHBALLED, `num_workers = 0`. Production loop skips it (state not IN_USE). | on toggle | building/building.c:966-975, building/industry.c:243 |
| Mothball (per resource, advisor) | Industries for that resource get no workers (food production and industry labor categories) | labor update | city/labor.c:233-243, city/labor.c:259-262 |
| Stockpile flag (per building) | Storable output goes to a warehouse first | per trip | building/industry.c:322-325, figuretype/cartpusher.c:191-198 |
| Random iron mine collapse | 4 of 128 per month, if enabled, after cooldown; destroys first iron mine (or costs 250 Dn with config) | 1 per month | scenario/random_event.c:113-130, scenario/random_event.c:31-40 |
| Random clay pit flood | 5 of 128 per month, if enabled, after cooldown; destroys first clay pit (or 250 Dn with config) | 1 per month | scenario/random_event.c:132-149 |
| Pantheon + all gods happiness >= 60 | Skips mine collapse and clay flood events | 1 per month | scenario/random_event.c:161-174 |

## 4.4 Workshops: raw material delivery and stock

| Rule | Value / formula | Cadence | Source |
|---|---|---|---|
| Raw material per output | Consumed when a new production starts: 100 units (most), 50 sand + 50 clay (bricks), 50 sand (concrete), 20 gold (mint) | per output | building/industry.c:353-363, game/resource.c:92-102 |
| Delivery size | 1 load (100 units) per cart | per delivery | building/industry.c:465-473 |
| "With room" limit | A cart pusher from a raw producer delivers only to a workshop with less than 2 loads (200 units) of that raw material | per trip | building/industry.c:497-537, figuretype/cartpusher.c:209-214 |
| Workshop choice | Nearest workshop by chess distance; +20 tiles penalty if it already holds some stock | per trip | building/industry.c:522-529 |
| Warehouse to workshop | Warehouseman priority 2 uses the "with room" rule; priority 6 delivers to any workshop with no stock limit (distance + current stock) | per trip | figuretype/cartpusher.c:697-709, figuretype/cartpusher.c:757-768, building/industry.c:539-577 |
| Stockpiled raw material | Not delivered to workshops | per trip | building/industry.c:499-501 |
| Non-storable output gate | Concrete (flags NONE) does not start production unless a monument on the same road network needs it | per step | game/resource.c:84, building/industry.c:275-279 |
| Concrete cart pusher | Waits for a monument destination; dies after 300 ticks; retries every 30 ticks | per trip | figuretype/cartpusher.c:25, figuretype/cartpusher.c:215-225, figuretype/cartpusher.c:375-383 |
| Concrete water access | 2 if a tile in reservoir range; else 1 if fountain range or well access; else 0 | 1 per day | building/figure.c:1471-1480 |
| Concrete progress | `num_workers * water / 2`, minimum 1 if staffed and water = 1 | per step | building/industry.c:294-300 |
| City Mint gold intake | Accepts gold only when finished, in denarii mode, with < 200 gold units | per trip | building/industry.c:483-489 |

## 4.5 City Mint and gold

| Rule | Value / formula | Cadence | Source |
|---|---|---|---|
| Mint needs | An active Senate, the mint in use, labor access, workers | per step | building/industry.c:155-169 |
| Denarii mode input check | No progress if gold < 20 units | per step | building/industry.h:8, building/industry.c:171-174 |
| Denarii per output | 100 (`DENARII_MINTED_PER_PRODUCTION`) | per output | building/industry.c:21, building/industry.c:200-215 |
| Gold per output | 20 units | per output | building/industry.c:216-219 |
| Denarii from 1 load of gold | 5 outputs = 500 Dn | derived | same |
| Governor share | If a governor house exists and salary > 5: `10 * salary / 100` Dn (min 1) go to personal savings; rest to treasury | per output | building/industry.c:203-215 |
| Gold mode cost | 600 Dn (`DENARII_COST_PER_GOLD`) charged when a new gold production starts at progress 0. No start if out of money. | per load | building/industry.c:22, building/industry.c:181-187 |
| Gold mode output | 1 load of gold by cart pusher | per load | building/industry.c:327-346 |
| Curse | Ceres curse sets mint progress 0 and `curse_days_left` 4 or 48 | on curse | building/industry.c:442-446 |
| Gold mine | Normal raw producer, 20/month, no denarii cost | — | game/resource.c:76, building/industry.c:235-311 |

## 4.6 Wharf, shipyard and fishing boat

| Rule | Value / formula | Cadence | Source |
|---|---|---|---|
| Shipyard boat build | Progress per day: +10 (100% staff), +8 (≥75%), +6 (≥50%), +4 (≥25%), +2 (≥1%) | 1 per day | building/figure.c:1540-1551 |
| Boat ready | Progress ≥ 160 → boat spawns; at full staff 16 days = 1 month | per boat | building/figure.c:1552-1560 |
| One boat per shipyard at a time | No build while its boat is alive | per day | building/figure.c:1537-1539 |
| Boat assignment | New boat waits 50 ticks, then goes to a wharf that has no boat | per boat | figuretype/water.c:205-222 |
| Wait at wharf before trip | `5 * (102 - pct_workers)` ticks; at 100% staff = 10 ticks; no trip while the wharf still holds an uncollected fish load | per trip | figuretype/water.c:268-288 |
| Fishing time | 200 ticks at the fishing point (4 days) | per trip | figuretype/water.c:244-253 |
| Target | Closest scenario fishing point | per trip | figuretype/water.c:280-285 |
| Catch | +1 fish load at the wharf on return; production statistic +100 | per trip | figuretype/water.c:290-299 |
| Fish cart | Next daily spawn check creates a cart pusher with 1 fish load | 1 per day | building/figure.c:1516-1527 |
| Boat speed | 1 tick per tick (15 ticks per tile); +10% with a working Lighthouse | continuous | figuretype/water.c:168-183, figure/movement.c:455-469 |
| Wharf production per month 100 | Used only for the efficiency percentage (not capped at 100%) | display | building/industry.c:63-68 |

Fish output per month = 800 / (trip ticks), where trip ticks = 10 (wait) + 200 (fishing) + 2 × 15 × (tiles to the fishing point), at full staff, plus the cart pusher wait. This is derived, not a constant.

## 4.7 Cart pushers (producer to storage)

| Rule | Value / formula | Cadence | Source |
|---|---|---|---|
| Loads per trip | 1 | per trip | building/figure.c:1496 |
| Speed | 1 tick of movement per game tick; 15 ticks per tile | continuous | figuretype/cartpusher.c:386, figure/movement.c:309-344 |
| Ceres Grand Temple | Farm cart pushers move +50% | continuous | figuretype/cartpusher.c:317-328 |
| Terrain | Roads and highways only | continuous | figuretype/cartpusher.c:344 |
| Destination priority (all producers) | 1 warehouse if stockpiled; 2 granary (food only); 3 workshop with room; 4 (non-storable) monument; 5 warehouse; 6 granary forced | per trip | figuretype/cartpusher.c:184-247 |
| Farms deliver close (config) | Farm and wharf carts skip a granary or warehouse 64 or more tiles away | per trip | figuretype/cartpusher.c:167-182 |
| Unload time | Warehouse: 11 ticks; granary, workshop, monument: 6 ticks | per trip | figuretype/cartpusher.c:456-521 |
| Reroute timeout | 120 ticks without arrival → choose destination again | per trip | figure/movement.h:6, figuretype/cartpusher.c:394-398 |
| Storage acceptance needs full staff | Warehouse and granary accept deliveries only at 100% workers | per check | building/warehouse.c:639-645, building/granary.c:444-450 |

## 4.8 Warehouses

| Rule | Value / formula | Cadence | Source |
|---|---|---|---|
| Cost / workers | 70 Dn, 6 workers | — | building/properties.c:1053 |
| Spaces | 8 spaces per warehouse | — | building/warehouse.c:85, building/warehouse.c:178 |
| Loads per space | 4; one resource per space | — | building/warehouse.c:25, building/warehouse.c:217-223 |
| Loads per warehouse | 32 | — | building/storage.h:29, building/warehouse.c:195 |
| Per-resource limit | 4 to 32 in steps of 8 (or 4 with config). Default 32. | player | building/storage.h:28-37, building/storage.c:97-100, building/storage.c:314-339 |
| Storage states | Not accepting (0), Accepting (1), Getting (2), Maintaining (3) | player | building/storage.h:18-24 |
| Accepting | Accepts while amount < limit | per check | building/storage.c:227-231 |
| Getting | Fetches from other warehouses while amount ≤ limit; other buildings cannot take from it | per check | building/storage.c:233-237, building/warehouse.c:427-438 |
| Maintaining | Keeps stock; markets, traders and workshops do not take it | per check | building/storage.c:239-243, building/warehouse.c:103-114 |
| Empty all | Warehouse accepts nothing; warehouseman takes 4 loads per trip to another warehouse | per trip | building/warehouse.c:476-478, figuretype/cartpusher.c:28, figuretype/cartpusher.c:736-756 |
| Warehouseman task needs | ≥ 50% workers | 1 per day | building/warehouse.c:774-777 |
| Warehouseman task order | 1 empty all; 2 getting (only if ≥ 4 loads free for the resource); 3 raw material to workshop; 4 food to granary | 1 per day | building/warehouse.c:772-850 |
| Getting trip | Up to 4 loads from the source warehouse; source score = distance − 4 × stored loads | per trip | figuretype/cartpusher.c:964-975, building/warehouse.c:691-720 |
| Delivery trip | 1 load (raw material, food, weapons) | per trip | figuretype/cartpusher.c:686-734 |
| Choice of warehouse for storing | Nearest (chess distance) on same road network that accepts and has space | per trip | building/warehouse.c:652-676 |
| Permissions (toggle per building) | Market, traders, dock, quartermaster, worker, barkeep, caravanserai, lighthouse, armoury, work camp, natives, Caesar | player | building/storage.h:44-57 |
| Plague | No add or remove | while plague | building/warehouse.c:259-261, building/warehouse.c:476 |
| Caesar requests | Taken first from non-getting warehouses with Caesar permission | on request | building/warehouse.c:527-560 |
| "Warehouses don't accept" config | New warehouses start with all resources not accepted | at build | building/storage.c:102-106 |

## 4.9 Granaries

| Rule | Value / formula | Cadence | Source |
|---|---|---|---|
| Cost / workers | 100 Dn, 6 workers | — | building/properties.c:1045 |
| Capacity | 32 loads, shared by all foods | — | building/storage.h:29, building/granary.c:697-711 |
| Per-food limit | Same states and limits as warehouses | player | building/granary.c:309-333 |
| Accepts | Food only, at 100% staff, with road access | per check | building/granary.c:438-461, building/granary.c:120-125 |
| Rome supplies wheat | No granary storage; the wheat stock of markets and the mess hall is set to 200 units each day | 1 per day | building/granary.c:488-490, city/resource.c:500-514 |
| Getting granary trip | Up to 8 loads of one food (16 with config) | per trip | building/granary.c:336-371 |
| Getting source | Granaries that hold > 1 load of non-getting food; on same road network unless "go offroad" config | 1 per day cache | building/granary.c:406-436, building/granary.c:572-614 |
| Granaryman task needs | ≥ 50% workers | 1 per day | building/granary.c:373-378 |
| Empty all | 8 loads per trip | per trip | figuretype/cartpusher.c:27, figuretype/cartpusher.c:560 |
| Normal delivery out | 1 load per trip | per trip | figuretype/cartpusher.c:560 |
| Granary blessing function | `building_granary_bless()` adds 6 loads of each available food to the emptiest granary, but no code calls it, so it has no effect | never | building/granary.c:616-644, building/granary.h:264 |

## 4.10 Cart depot

| Rule | Value / formula | Cadence | Source |
|---|---|---|---|
| Cost / workers | 100 Dn, 15 workers | — | building/properties.c:2107 |
| Carts | 3 (≥75% staff), 2 (≥50%), 1 (>0%) | 1 per day | building/figure.c:2036-2044 |
| Cart spawn delay | Default spawn delay (see 4.18) | daily counter | building/figure.c:2063-2077 |
| Capacity per trip | 16 loads (food), 4 loads (other) | per trip | figuretype/depot.c:25-26, figuretype/depot.c:396-398 |
| Load / unload time | 11 ticks each | per stop | figuretype/depot.c:29, figuretype/depot.c:375, figuretype/depot.c:416 |
| Order conditions | Never; always; source has ≥ threshold; destination has < threshold. Source must have > 0. | per check | figuretype/depot.c:102-135 |
| Wait at source | With "destination less than" the cart waits until source has ≥ 4 | per check | figuretype/depot.c:388-393 |
| Terrain | Prefers roads and highways; any terrain with "caravans move off road" config | continuous | figuretype/depot.c:287-291 |

## 4.11 Markets and distribution to houses

| Rule | Value / formula | Cadence | Source |
|---|---|---|---|
| Cost / workers | 40 Dn, 5 workers | — | building/properties.c:1037 |
| Market trader (roamer) spawn | Delay counter > 2 (100%), 5 (≥75%), 10 (≥50%), 20 (≥25%), 30 (≥1%) days | daily counter | building/figure.c:907-930 |
| Market buyer spawn | When no buyer is alive, 1 buyer per day check | 1 per day | building/figure.c:879-898, building/figure.c:932 |
| Food stock cap per type | 800 units (8 loads) | per trip | figuretype/supplier.h:6, figuretype/supplier.c:70-73 |
| Food per trip | Up to 8 loads total from one granary, over the foods the market accepts | per trip | figuretype/supplier.c:83-117 |
| Goods per trip | 2 loads | per trip | figuretype/supplier.c:297-305 |
| Fetch order | 1 a needed item with stock 0; 2 the smallest stock below 50 units; 3 the food with smallest stock below 600 units | per trip | building/market.c:68-92, building/distribution.h:14, building/market.c:8 |
| Goods demand | A good is fetched only while `accepted_goods > 1`. A house visit that needs it sets it to 11. Each buyer spawn decreases it by 1. | per visit / spawn | building/market.c:44-47, figure/service.c:411-426, building/distribution.c:70-77 |
| Market range (config) | 40 tiles max to the source storage, else map width | per trip | building/market.h:6, building/market.c:99 |
| Buyer source | Nearest granary (food) or warehouse (goods) on same road network with permission and stock; ignores stockpiled goods and maintaining warehouses | per trip | building/distribution.c:144-222 |
| Coverage area | Houses within 2 tiles of each tile the market trader walks | per tile | figure/service.c:429-450 |
| Food to house | One food type per visit: `4 * house_highest_population` units, or what the market has | per visit | figure/service.c:375-402 |
| Goods to house | Up to `goods_no * model.amount` per good; `goods_no` = 8, or 12 with a working Venus Grand Temple | per visit | figure/service.c:404-426 |
| House food consumption | `50% of population` units per month, split over the food types it holds; 40% with Ceres GT module 1 and Ceres temple access | 1 per month | city/resource.c:516-571 |
| House goods consumption | Model amount per good on day 0 and day 7 (1x1 houses: day 0 only). Reductions: Mercury module 1 −20% pottery/furniture; Mercury module 2 −20% oil/wine (Mercury temple access); Mars module 2 −10% all goods (Mars temple access) | 2 per month | building/house_evolution.c:531-562, building/house_evolution.c:598 |

## 4.12 Trade routes, quotas and trader generation

| Rule | Value / formula | Cadence | Source |
|---|---|---|---|
| Route opening | Pays `cost_to_open` Dn; also removes route resource costs from warehouses (then granaries for food) | on open | empire/city.c:474-493 |
| Quota storage | Each route has `buys.limit/traded` (city buys = player exports) and `sells.limit/traded` (city sells = player imports) | — | empire/trade_route.c:12-21, empire/trade_route.c:159-169 |
| Legacy quota steps | 0 → 15 → 25 → 40 (and back) | editor | empire/trade_route.c:232-252 |
| Quota reached | Trade stops for that resource when `traded >= limit` | per trade | empire/trade_route.c:271-275 |
| Quota reset | All open routes: traded = 0 at year change; old year saved to history (7 years) | 1 per year | game/tick.c:77, empire/city.c:348-357, empire/trade_route.c:10, empire/trade_route.c:295-311 |
| Trader generation check | Once per day per open city | 1 per day | game/tick.c:180, city/trade.c:48, empire/city.c:495-517 |
| Delay after an attempt | Land 4 days, sea 30 days. The counter decreases first, so one attempt every 5 days (land) or 31 days (sea). | per attempt | empire/city.c:34-35, empire/city.c:423-428 |
| Trade potential | Sum of route limits of all resources the city buys or sells | per attempt | empire/city.c:430-439 |
| Max traders per city | `clamp(potential / 60 + 1, 1, 3)` | per attempt | empire/city.c:33, empire/city.c:442, empire/city.h:8 |
| Sea trader needs | Working dock (in use, workers > 0, no plague), river entry, no sea trade problem | per attempt | empire/city.c:454-461, building/dock.c:511-515 |
| Land trader needs | No land trade problem | per attempt | empire/city.c:462-469 |
| No working dock message | Message repeats after a delay of 384. The code comment says 1 year. The unit is not verified. | — | empire/city.c:503-506 |
| Export allowed | Storable; quota not reached; stock > "export over" amount; trade status EXPORT; city buys it | per trade | empire/empire.c:335-361 |
| Export stock count | Warehouses only for food, unless "allow exporting from granaries" config | per trade | empire/empire.c:346-350 |
| Import allowed | Storable; city sells it; status IMPORT; quota not reached; stock < "import over" amount (0 = no limit) | per trade | empire/empire.c:377-437 |
| Import/export over range | 0..100 loads | player | city/resource.c:233-246 |
| Stockpile toggle | Removes EXPORT status; restores it when turned off | player | city/resource.c:253-263 |

## 4.13 Trade prices and policies

| Rule | Value / formula | Cadence | Source |
|---|---|---|---|
| Default prices `{buy, sell}` | Wheat 28/22, Vegetables 38/30, Fruit 38/30, Meat 44/36, Fish 44/36, Clay 40/30, Timber 50/35, Olives 42/34, Vines 44/36, Iron 60/40, Marble 200/140, Gold 350/250, Sand 30/24, Stone 40/30, Pottery 180/140, Furniture 200/150, Oil 180/140, Wine 215/160, Weapons 250/180, Bricks 200/150. Concrete has no price (not storable). | — | game/resource.c:65-85, game/resource.h:124-127 |
| "Buy" price | Price the player pays for 1 imported load: `buy * (100 + buy_factor) / 100` | per load | empire/trade_prices.c:119-122 |
| "Sell" price | Price the player gets for 1 exported load: `sell * (100 + sell_factor) / 100` | per load | empire/trade_prices.c:129-132 |
| Import payment | Treasury − price; recorded as imports | per load | building/warehouse.c:364-365, city/finance.c:143-147 |
| Export payment | Treasury + price; +50% extra while Neptune blessing is active | per load | building/warehouse.c:400-401, city/finance.c:149-157 |
| Neptune blessing | Export bonus lasts 12 months | on blessing | city/gods.c:72, city/gods.h:5, city/gods.c:54-56 |
| Price change (scenario) | `buy += amount; sell += amount`. If a decrease ≥ current sell price: buy = 2, sell = 0. No decrease when sell ≤ 0. | on event | empire/trade_prices.c:148-162 |
| Price set (event) | Minimum 1 | on event | empire/trade_prices.c:11, empire/trade_prices.c:164-184 |
| Scheduled price change | Fires in its year and month; month is random 2..9 if set at load | 1 per month check | scenario/price_change.c:40-71 |
| Policy cost | 500 Dn per change | on change | city/trade_policy.h:4, window/advisor/trade.c:284-286 |
| Land policy 1 | Export price +20%, import price +10% | continuous | city/trade_policy.h:5-6, empire/trade_prices.c:60-104 |
| Land policy 2 | Export price −0%, import price −20% | continuous | city/trade_policy.h:7-8, empire/trade_prices.c:68-70, empire/trade_prices.c:91-93 |
| Land policy 3 | +4 loads per caravan; caravanserai food need +20% | continuous | city/trade_policy.h:9-10, figuretype/trader.c:1022-1037, city/resource.c:636-640 |
| Sea policy 1, 2, 3 | Same percentages with the Lighthouse; policy 3: +4 loads per ship, lighthouse timber use +20% | continuous | empire/trade_prices.c:71-78, empire/trade_prices.c:94-101, figuretype/trader.c:1057-1072, building/lighthouse.c:59-64 |
| Policy needs | Caravanserai (land) or Lighthouse (sea) fully functional; otherwise factor 0 | continuous | empire/trade_prices.c:39-58 |
| Half bonus at partial staff | Code gives half the percent at 1-99% staff, but "fully functional" needs 100% staff, so this branch has no effect | — | empire/trade_prices.c:26-37, building/monument.c:772-799 |

## 4.14 Land traders (caravans)

| Rule | Value / formula | Cadence | Source |
|---|---|---|---|
| Caravan | 1 leader + 2 donkeys | per trader | figuretype/trader.c:135-151 |
| Initial wait | `random_byte & 50` ticks, then waits until > 50 ticks | per trader | figuretype/trader.c:46, figuretype/trader.c:141, figuretype/trader.c:484-490 |
| Loads per caravan | 8; +4 with a working Mercury Grand Temple; +4 with land policy 3 → max 16 | per trader | figuretype/trader.c:1004-1039 |
| Speed | 15 ticks per tile; +25% with working Mercury Grand Temple | continuous | figuretype/trader.c:115-123, figuretype/trader.c:494 |
| Terrain | Prefers roads/highways; any terrain with config | continuous | figuretype/trader.c:469-473 |
| Trade step | Every 11 ticks at a storage: 1 buy (export) + 1 sell (import) at most | per step | figuretype/trader.c:508-545 |
| Leave storage | When neither a buy nor a sell happens in a step | per step | figuretype/trader.c:540-544 |
| Resource choice at a storage | The resource with the lowest quota fill percent | per step | figuretype/trader.c:270-322 |
| Granary use | Caravans sell food to granaries; buy from granaries only with "allow exporting from granaries" config | per step | figuretype/trader.c:163-201, figuretype/trader.c:227-229 |
| Storage choice score | `(sell_score + buy_score) * distance_score / 100` | per choice | figuretype/trader.c:324-435 |
| Sell score | Σ min(remaining import quota, free space, remaining capacity) × price multiplier (multiplier = 100; sell scaler is 0) | per choice | figuretype/trader.c:59, figuretype/trader.c:93-105, figuretype/trader.c:375-384 |
| Buy score | Σ min(remaining export quota, stock, remaining capacity) × `clamp(100 + 80·log10(sell_price/80), 50, 300)` | per choice | figuretype/trader.c:52-60, figuretype/trader.c:100-102, figuretype/trader.c:387-395 |
| Distance score | `clamp(100 + 200·log10(80 / d), 50, 300)`, d = chess distance trader→storage + storage→exit | per choice | figuretype/trader.c:51, figuretype/trader.c:58, figuretype/trader.c:397-405 |
| Storages skipped | Not in use, plague, no road access, recently visited, no trader permission | per choice | figuretype/trader.c:361-365 |

## 4.15 Native traders

| Rule | Value / formula | Cadence | Source |
|---|---|---|---|
| Capacity for scoring | `8 / 3 + 1` = 3 | per choice | figuretype/trader.c:326-327 |
| Trade | Buys 1 load of the exported resource the storage holds most; counts as 3 loads | every 11 ticks | figuretype/trader.c:663-685 |
| Price | Export (sell) price, land rates | per load | figuretype/trader.c:680-681 |
| Quota | No quota for natives | — | figuretype/trader.c:340-342 |
| Permission | "Natives" storage permission | per stop | figuretype/trader.c:670 |

## 4.16 Sea traders, docks and dockers

| Rule | Value / formula | Cadence | Source |
|---|---|---|---|
| Dock cost / workers | 100 Dn, 12 workers | — | building/properties.c:1075 |
| Ship cargo | 12 loads; +6 with working Mercury Grand Temple; +4 with sea policy 3 → max 22 | per ship | figuretype/trader.c:1041-1075 |
| Ship speed | 15 ticks per tile; +25% with working Neptune Grand Temple | continuous | figuretype/trader.c:125-133, figuretype/trader.c:781 |
| Initial wait | Same as caravans (≤ 51 ticks) | per ship | figuretype/trader.c:153-161, figuretype/trader.c:793-813 |
| Anchored check | Every 41 ticks the ship asks to dock | per check | figuretype/trader.c:857-907 |
| Dockers per dock | 3 (≥75% staff), 2 (≥50%), 1 (>0%) | 1 per day | building/figure.c:1571-1611 |
| Docker trip | 1 load per trip; import first, then export | per trip | figuretype/docker.c:354-360, figuretype/docker.c:419, figuretype/docker.c:451 |
| Import destination | Granary (food) preferred; else warehouse with score distance + (32 − 2 × free space) | per trip | figuretype/docker.c:109-184 |
| Export source | Warehouse with score distance + (32 − 2 × stock); granary +31 penalty (config only) | per trip | figuretype/docker.c:117-123, figuretype/docker.c:186-243 |
| Resource order | Dockers cycle through storable resources in enum order | per trip | city/trade.c:91-111, figuretype/docker.c:137-140 |
| How long a ship stays | Moored until the dock stops working, stops accepting, or the counter of ticks in which every docker was idle reaches 10 (the counter is not reset while moored) | per tick | figuretype/trader.c:746-767, figuretype/trader.c:930-985 |
| Forward to another dock | A moored ship queues elsewhere only if it still has ≥ 1/3 of capacity to trade | per check | figuretype/trader.c:1077-1094 |
| Ship leaves | To the river exit or entry, whichever is closer and reachable | on leave | figuretype/trader.c:945-974 |
| Dock accepts ship | The route is allowed at the dock, and the dock accepts at least one resource the city trades | per check | building/dock.c:77-93 |

## 4.17 Trade problems, Caravanserai and Lighthouse

| Rule | Value / formula | Cadence | Source |
|---|---|---|---|
| Land trade problem | Duration −1 per day; −2 per day with fully functional Caravanserai | 1 per day | city/trade.c:26-33 |
| Sea trade problem | Duration −1 per day; −2 per day with fully functional Lighthouse | 1 per day | city/trade.c:34-39 |
| Effect | No new caravans (land) or ships (sea) | per attempt | empire/city.c:457, empire/city.c:464 |
| Random land problem | 48 days; event chance 5/128 per month; needs a land route and cooldown | 1 per month | scenario/random_event.c:64-78, scenario/random_event.c:31-40 |
| Random sea problem | 48 days; chance 4/128 per month | 1 per month | scenario/random_event.c:80-90 |
| Neptune small curse | Sinks half of the ships; sea problem 40 days | on curse | city/gods.c:101-110 |
| Neptune large curse | Sinks all ships; sea problem 80 days | on curse | city/gods.c:141-149 |
| Events | Scenario events can start land/sea problems with any duration | on event | scenario/event/action_types.c:562, scenario/event/action_types.c:577 |
| Caravanserai | Size 4, 500 Dn, 20 workers | — | building/properties.c:1967 |
| Caravanserai fully functional | Finished, 100% staff, total food ≥ monthly need | per check | building/caravanserai.c:62-75, building/monument.c:783-799 |
| Caravanserai food need | 30 units per open land route per month (+20% with land policy 3) | 1 per month | city/resource.h:8, building/caravanserai.c:24-31, city/resource.c:629-680 |
| Caravanserai food stock | Up to 1600 units per food type | per trip | figuretype/supplier.h:8 |
| Lighthouse | Size 3, 1000 Dn, 20 workers; open water within 9 tiles | — | building/properties.c:1772, building/construction.c:695-696, building/construction.c:1426-1433 |
| Lighthouse fully functional | Finished, 100% staff, timber > 100 units | per check | building/lighthouse.c:15-20, building/lighthouse.c:37-44 |
| Lighthouse timber use | 20 units on day 0 and day 7 (40 per month); +20% with sea policy 3 | 2 per month | building/lighthouse.c:14, building/lighthouse.c:54-74, game/tick.c:138-140 |
| Lighthouse timber stock | Max 500 units; supplier brings 100 units per trip | per trip | building/lighthouse.c:13, building/lighthouse.c:24-26, figuretype/supplier.c:336-337 |
| Lighthouse fishing bonus | Fishing boats +10% speed | continuous | figuretype/water.c:168-174 |

## 4.18 Spawn delay table (service-style buildings)

| Rule | Value / formula | Cadence | Source |
|---|---|---|---|
| Default spawn delay | Counter must exceed 3 (100% staff), 7 (≥75%), 15 (≥50%), 29 (≥25%), 44 (≥1%) days | daily counter | building/figure.c:125-141 |
| Used by | Work camp, Architect guild, Caravanserai supplier, Lighthouse supplier, Depot carts | — | building/figure.c:1749, building/figure.c:1773, building/figure.c:1875, building/figure.c:1893, building/figure.c:2063 |

## 4.19 Monuments: phases and resource costs (loads)

Phase *n* needs the resources listed in row *n*. The last phase number is "finished". "Arch." = number of architect visits for the phase. Resources must all be delivered before an architect can work on the phase.

| Monument | Phase 1 | Phase 2 | Phase 3 | Phase 4 | Phase 5 | Total resources | Source |
|---|---|---|---|---|---|---|---|
| Grand Temple (each of 5) | 1 arch., 20 stone | 1 arch., 8 timber, 20 concrete | 1 arch., 8 timber, 16 marble | 1 arch., 16 timber, 28 bricks, 12 marble | 4 arch. | 20 stone, 32 timber, 20 concrete, 28 marble, 28 bricks; 8 arch. | building/monument.c:63-73 |
| Pantheon | 1 arch., 20 stone | 1 arch., 8 timber, 20 stone | 1 arch., 16 timber, 40 concrete | 1 arch., 16 timber, 32 marble, 16 gold | 4 arch. | 40 stone, 40 timber, 40 concrete, 32 marble, 16 gold; 8 arch. | building/monument.c:75-85 |
| Lighthouse | 1 arch., 16 stone | 1 arch., 8 timber, 16 stone | 1 arch., 16 timber, 12 stone | 4 arch., 8 timber, 20 bricks, 12 stone | finished | 56 stone, 32 timber, 20 bricks; 7 arch. | building/monument.c:87-96 |
| Colosseum | 1 arch., 12 stone | 1 arch., 8 timber, 16 concrete | 1 arch., 12 timber, 16 stone | 4 arch., 12 timber, 16 bricks, 20 marble | finished | 28 stone, 32 timber, 16 concrete, 16 bricks, 20 marble; 7 arch. | building/monument.c:98-107 |
| Hippodrome | 1 arch., 32 stone | 1 arch., 16 timber, 32 concrete | 1 arch., 16 timber, 32 stone | 4 arch., 32 timber, 32 bricks, 48 marble | finished | 64 stone, 64 timber, 32 concrete, 32 bricks, 48 marble; 7 arch. | building/monument.c:109-118 |
| Oracle | 1 arch., 2 concrete, 2 marble | 1 arch. | finished | — | — | 2 concrete, 2 marble; 2 arch. | building/monument.c:120-127 |
| Small mausoleum | 1 arch., 2 stone, 4 concrete | 1 arch., 2 marble | finished | — | — | 2 stone, 4 concrete, 2 marble | building/monument.c:129-136 |
| Large temple (each of 5) | 1 arch., 4 stone, 4 concrete | 1 arch., 2 marble | finished | — | — | 4 stone, 4 concrete, 2 marble | building/monument.c:138-145 |
| Nymphaeum | 1 arch., 12 stone, 4 concrete | 1 arch., 2 marble | finished | — | — | 12 stone, 4 concrete, 2 marble | building/monument.c:147-154 |
| Large mausoleum | 1 arch., 8 stone, 4 concrete | 1 arch., 4 marble | finished | — | — | 8 stone, 4 concrete, 4 marble | building/monument.c:156-163 |
| Caravanserai | 1 arch., 12 stone | 1 arch., 8 timber, 12 bricks, 12 stone | finished | — | — | 24 stone, 8 timber, 12 bricks | building/monument.c:165-172 |
| City Mint | 1 arch., 8 stone | 1 arch., 4 bricks, 4 iron, 4 timber | finished | — | — | 8 stone, 4 bricks, 4 iron, 4 timber | building/monument.c:174-181 |
| Triumphal arch | 1 arch., 12 stone, 8 timber | 3 arch., 32 marble, 12 bricks | finished | — | — | 12 stone, 8 timber, 32 marble, 12 bricks | building/monument.c:183-190 |

| Rule | Value / formula | Cadence | Source |
|---|---|---|---|
| Limited to one per city | Grand Temples, Pantheon, Lighthouse, Caravanserai, Colosseum, Hippodrome, City Mint | at build | building/monument.c:387-405 |
| Phase advance | When all resources and architects for the phase are delivered; resources for the next phase are loaded | per architect | building/monument.c:470-493, building/monument.c:593-628 |
| Delivery unit | Each delivered load decreases the need by 1 | per load | building/monument.c:293-311 |
| Halted construction | A mothballed (halted) monument receives no deliveries and no architects | per check | building/monument.c:419-423, building/monument.c:919-933 |
| "Working" monument | Finished, in use, and `num_workers >= laborers` (100% staff). All monument bonuses use this check. | per check | building/monument.c:772-799 |
| Monument choice | Nearest unfinished monument on the same road network that still needs the resource after in-transit deliveries | per trip | building/monument.c:407-447 |
| Stockpiled resource | Not delivered to monuments | per trip | building/monument.c:409-411 |

## 4.20 Work camps and architects

| Rule | Value / formula | Cadence | Source |
|---|---|---|---|
| Work camp | Size 3, 150 Dn, 20 workers | — | building/properties.c:1391-1399 |
| Architect guild | Size 2, 200 Dn, 12 workers | — | building/properties.c:1752 |
| Work camp worker spawn | 1 worker at a time; default spawn delay (4 days at 100% staff) | daily counter | building/figure.c:1740-1762 |
| Loads per trip | Up to 4 (`CARTLOADS_PER_MONUMENT_DELIVERY`), limited by stock and remaining need; the foreman takes the loads from a warehouse and 1 slave per load carries them | per trip | figuretype/workcamp.h:6, figuretype/workcamp.c:45-80 |
| Source warehouse | Needs "work camp" permission and 100% warehouse staff; score = distance − 2 × stock | per trip | figuretype/workcamp.c:168-169, building/warehouse.c:722-770 |
| Resources carried | Storable, not stockpiled. Concrete is not storable, so concrete comes only from concrete maker cart pushers. | per trip | figuretype/workcamp.c:160-163, figuretype/cartpusher.c:215-225 |
| Delivery validity check | Every 60 ticks the walker checks that its delivery is still valid; else it dies | every 60 ticks | figuretype/workcamp.c:26, figuretype/workcamp.c:82-91 |
| Fallback task | If no monument needs anything, the worker supplies the Highway Station with stone or sand (up to 4 loads) | per trip | figuretype/workcamp.c:187-215, figuretype/workcamp.c:283-325 |
| Architect spawn | 1 architect at a time; default spawn delay; only if a monument needs architects (all resources for the phase delivered) | daily counter | building/figure.c:1764-1788, building/monument.c:422 |
| Architect work | 384 ticks at the monument (7.68 days), then the phase architect count −1 | per visit | figuretype/workcamp.c:547-562 |
| One architect per monument | The architect registers a placeholder delivery of 10, so a second architect does not go to the same monument | per visit | figuretype/workcamp.c:516-518 |
| Phase with 4 architects | 4 sequential visits ≈ 4 × (384 ticks + walk + spawn delay) | derived | same |

## 4.21 Grand Temple and other monument effects on the economy

| Rule | Value / formula | Cadence | Source |
|---|---|---|---|
| Ceres GT (base) | Farm cart pushers +50% speed | continuous | figuretype/cartpusher.c:317-328 |
| Ceres module 1 | Houses with Ceres temple access eat 40% of population instead of 50% | 1 per month | city/resource.c:519-531 |
| Ceres module 2 | Ceres temples distribute food (detail not in this chapter) | — | building/figure.c:1353 |
| Neptune GT (base) | Trade ships +25% speed | continuous | figuretype/trader.c:125-133 |
| Mercury GT (base) | Caravans +25% speed; +4 loads per caravan; +6 loads per ship | continuous | figuretype/trader.c:115-123, figuretype/trader.c:1008-1020, figuretype/trader.c:1044-1055 |
| Mercury module 1 | Pottery and furniture consumption −20% (all houses) | 2 per month | building/house_evolution.c:535-539 |
| Mercury module 2 | Oil and wine consumption −20% (houses with Mercury temple access) | 2 per month | building/house_evolution.c:540-544 |
| Mars module 2 | All four goods −10% (houses with Mars temple access) | 2 per month | building/house_evolution.c:545-551 |
| Reduction method | A good is consumed in a month only if `(total_months * (100 − r)) % 100 < 100 − r` | per consumption | building/house_evolution.c:557-560 |
| Venus GT (base) | Market gives houses 12 × model goods instead of 8 | per visit | figure/service.c:404-409 |
| Venus module 1 | The Venus GT makes wine: progress += 10 + population_with_venus_access / 800 per day; +1 wine load per 400 progress; max 16 loads stored | 1 per day | building/industry.c:20, building/industry.c:23, building/industry.c:138-153, building/industry.c:315-316 |
| Venus module 1 and wine types | +1 wine type available | 1 per day | city/trade.c:19-21 |
| Wine types available | 1 if any wine workshop is active, +1 Venus module 1, +1 per open route that sells wine | 1 per day | city/trade.c:17-23, empire/city.c:379-389 |

## 4.22 Movement, roads, highways and roadblocks

| Rule | Value / formula | Cadence | Source |
|---|---|---|---|
| Base walker speed | 15 movement ticks per tile; most logistics walkers get 1 movement tick per game tick | continuous | figure/movement.c:309-344 |
| Tiles per day at base speed | 50 / 15 ≈ 3.33 | derived | game/time.h:13 |
| Highway | Movement ticks ×2 on a highway tile (7.5 ticks per tile) | continuous | figure/movement.c:311-314 |
| Followers on highway | Donkeys, delivery boys, slaves move ×2 when the leader is on a highway | continuous | figure/movement.c:490-492, figure/movement.c:531-533 |
| Beach (no road) | −30% movement | continuous | figure/movement.c:295-307 |
| Percentage bonus | +P% adds one extra movement tick each time accumulated P reaches 100 | continuous | figure/movement.c:455-469 |
| Road speed bonus | None. A road tile does not change speed. | — | figure/movement.c:309-344 |
| Pathfinding cost | 2 per tile; 1 per tile along a highway in the highway direction | per route | map/routing.c:204-233, map/routing.c:195-202 |
| Highway levy | 1 Dn per month per 2x2 highway block; halved with a working Highway Station | 1 per month | city/finance.h:20, city/finance.c:383-396 |
| Highway cost | 100 Dn per 2x2 block | at build | building/properties.c:2046 |
| Highway Station | Size 3, 200 Dn, 12 workers | — | building/properties.c:2268 |
| Highway Station need | `ceil(highway blocks / 50)` loads of stone and of sand per month | 1 per month | building/highway_station.h:6-8, building/highway_station.c:28-42, building/highway_station.c:77-97, city/finance.c:435 |
| Highway Station stock cap | 6 months of need | — | building/highway_station.c:44-47 |
| Highway Station working | In use, workers > 0, stone and sand ≥ 1 month of need | per check | building/highway_station.c:49-66 |
| Roadblock | 12 Dn, 0 workers | — | building/properties.c:1383 |
| Roadblock effect | Blocks only roaming walkers without permission. Walkers with a destination (cart pushers, market buyers, traders, dockers) pass. | per tile | figure/movement.c:257-287, building/roadblock.h:8-20 |

## 4.23 Not verified or not covered

| Item | Status |
|---|---|
| `building_granary_bless()` | Verified: no caller in the source tree (dead code) (building/granary.c:616-644) |
| Ceres module 2 food distribution amounts | Not covered in this chapter |
| Exact docker ticks at storage | Dockers act on the first tick at the storage (`wait_ticks > 0`); unload time is effectively 1 tick (figuretype/docker.c:479-482, figuretype/docker.c:519-522) |
| "No working dock" message delay unit 384 | Code comment says 1 year; the unit of the message delay counter is not verified (empire/city.c:504-505) |
