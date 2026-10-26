# Chapter 5: Gods, military, natives, disasters and the scenario event system

Engine: Augustus, upstream commit `dae1899`. All paths are relative to `src/`.
Each rule cites `file:line`. "Unverified" marks a value that this chapter could not confirm in the code.

## 5.0 Clock and cadence reference

Most functions in this chapter have names that say "monthly". Many of them run more often. Use this table to convert.

| Rule | Value / formula | Cadence | Source |
|---|---|---|---|
| Ticks per day | 50 | - | game/time.h:13 |
| Days per month | 16 | - | game/time.h:14 |
| Months per year | 12 (192 days) | - | game/time.h:15 |
| God moods (`city_gods_calculate_moods(1)`) | runs | daily, tick 1 | game/tick.c:156 |
| Caesar anger, debt (`city_emperor_update`) | runs | daily, tick 4 | game/tick.c:159 |
| Formations: legions, enemies, herds (`formation_update_all`) | runs twice; deployed-morale check only in first call | daily, ticks 5 and 29 | game/tick.c:160, 177; figure/formation.c:876-889 |
| Native land and native anger (`map_natives_check_land(1)`) | runs | daily, tick 6 | game/tick.c:161 |
| Industry production (`new_day` = 1 at tick 20) | runs | daily, ticks 20 and 46 | game/tick.c:169, 193 |
| Building figure spawns (barracks, temples, mission post, huts) | runs; spawn counters count days | daily, tick 31 | game/tick.c:179 |
| Trade problem countdown (`city_trade_update`) | runs | daily, tick 32 | game/tick.c:180; city/trade.c:26-45 |
| Culture decay (offering counter `days_since_offering` +1, cap 125) | runs | daily, tick 35 | game/tick.c:183; building/house_service.c:46-48 |
| House goods consumption | day 0 for all houses; day 7 again for houses larger than 1x1 | twice/month | building/house_evolution.c:597-600 |
| Burning ruins | runs | daily, tick 43 | game/tick.c:190 |
| Fire and collapse risk | runs | daily, tick 44 | game/tick.c:191 |
| Games duration countdown | runs | daily, tick 47 | game/tick.c:194 |
| Scenario events | paused counters −1 day, then all events checked | daily (after tick 49) | game/tick.c:146-147 |
| Earthquake, gladiator revolt, emperor change | runs | every tick | game/tick.c:214-216 |
| Monthly order | health, random events, finance, food consumption (incl. mess hall), distant battle, invasions, requests, demand, prices, months-to-govern, morale at rest, messages, festival boost decay, industry stats | monthly | game/tick.c:84-100 |
| After month advance | festival update, games month counters, blessing timers | monthly | game/tick.c:117-120 |

### 5.0.1 Two random-number rules

| Rule | Value / formula | Cadence | Source |
|---|---|---|---|
| `random_between_from_stdlib(min, max)` | returns `min + rand() % (max − min)`; result is **min .. max−1**; returns `min` when `max ≤ min` | per call | core/random.c:109-117 |
| Effect on scenario ranges | invasion amount, invasion repeat interval (years), distant battle enemy strength, event repeat days and the Mars uprising size (3..9 gives 3..8) never reach the upper value, unless min = max | per call | scenario/invasion.c:466, 606, 634, 655; scenario/distant_battle.c:51; scenario/event/event.c:236 |
| Formula random `{a,b}` | calls `random_between_from_stdlib(a, b+1)`: result is **a .. b inclusive**; the order of a and b does not matter | per evaluation | scenario/event/formula.c:80-94 |
| Seed of stdlib random | `srand(time())` when the wall-clock second changes; results do not repeat after a reload | per call | core/random.c:99-107 |
| Game random (`random_byte`) | 7-bit value 0..127 | advanced every tick | core/random.c:61-64; game/tick.c:210 |

## 5.1 Gods

### 5.1.1 Target happiness (daily, tick 1)

| Rule | Value / formula | Cadence | Source |
|---|---|---|---|
| Base target | religion coverage % of that god (0..100) | daily | city/gods.c:302-305 |
| Coverage % | `min(100, raw / population × 100)` | daily (tick 33 recalculates) | city/culture.c:161, 171, 181, 191, 201 |
| Raw coverage per building | lararium 10 (all gods, counts built, not active), shrine 50 (own god, counts built), small temple 750, large temple 3000, oracle and small mausoleum 500 (all gods), nymphaeum and large mausoleum 750 (all gods), Pantheon 1500 (all gods), grand temple 5000 (own god) | - | city/culture.c:13-20, 147-201 |
| Festival term | `target += 12 − min(months_since_festival, 40)` (range +12 .. −28) | daily | city/gods.c:343-350 |
| Temple count used for "most / fewest temples" | small + large + grand temples of the god (shrines and oracles do not count) | daily | city/gods.c:311-329 |
| Most temples bonus | the single god with the most temples: target set to 100 if target ≥ 50, else target +50. A tie gives no bonus | daily | city/gods.c:330-335, 352-359 |
| Fewest temples penalty | the single god with the fewest temples: target −25. A tie gives no penalty | daily | city/gods.c:336-341, 360-362 |
| Jealous-gods option | the option `CONFIG_GP_CH_JEALOUS_GODS` turns the two rules above off | - | city/gods.c:352 |
| Minimum target by population | pop < 100: 50; < 200: 40; < 300: 30; < 400: 20; < 500: 10; else 0. Target bounded to [min, 100] | daily | city/gods.c:364-381 |
| Happiness step | happiness moves 1 point per day toward target | daily | city/gods.c:188-192 |
| Tutorial 1 | happiness never below 50 | daily | city/gods.c:193-197 |
| Flag reset | happiness > 50 clears `small_curse_done`; happiness < 50 clears `blessing_done` | daily | city/gods.c:198-203 |

### 5.1.2 Bolts (daily accrual for one random god)

| Rule | Value / formula | Cadence | Source |
|---|---|---|---|
| God selected each day | `random_byte() & 7` gives 0..7. Values 0..4 select a god; 5..7 select no god. Each god has a 1/8 chance per day, about 2 selections per month | daily | city/gods.c:206-207 |
| Wrath bolts reset | selected god with happiness ≥ 50: wrath bolts = 0 | daily | city/gods.c:209-210 |
| Wrath bolts gain (happiness < 40) | first, remove 1 happy bolt if any; else +1 (happiness 20..39), +2 (10..19), +5 (0..9). Happiness 40..49 gives no change | daily | city/gods.c:211-221 |
| Wrath cap | 50 | daily | city/gods.c:222-224 |
| Happy bolt chance (happiness ≥ 50), % | `(happiness − 50)/20 + 1`; plus, if months since this god's festival ≤ 24: `(24 − months)/6 + 1`. Roll 0..99 below chance gives +1 happy bolt | daily | city/gods.c:26-29, 225-234 |
| Happy bolt cap | 5 | daily | city/gods.c:235-237 |
| Example | happiness 100, festival this month: chance = 3 + 5 = 8 % per selection; about 0.16 bolts per month; about 31 months for 5 bolts (derived) | - | derived from city/gods.c:226-228 |

### 5.1.3 Monthly god resolution (day 0 of each month)

| Rule | Value / formula | Cadence | Source |
|---|---|---|---|
| Months since festival | +1 for every god | monthly | city/gods.c:245-247 |
| Fallback god | if the day-0 roll selected no god: the god with the most wrath bolts; if all have 0 wrath, the god with the lowest happiness below 40 | monthly | city/gods.c:248-252, 387-410 |
| Gods disabled setting | no blessing, no curse, no message | - | city/gods.c:253-255 |
| Blessing | happiness ≥ 50 and happy bolts ≥ 5: happy bolts = 0, blessing | monthly | city/gods.c:259-262 |
| Small curse | wrath ≥ 20, small curse not done since happiness was last > 50, and months since festival > 3: wrath = 0, happiness +12, small curse | monthly | city/gods.c:263-267 |
| Major curse | wrath ≥ 50 and months since festival > 3: wrath = 0, happiness +30, major curse | monthly | city/gods.c:268-279 |
| Original campaign protection | original campaign rank < 4: no major curse | monthly | city/gods.c:269-273 |
| Angry message | lowest happiness < 30: message ("unhappy", or "wrathful" if < 10), then 20 months of silence | monthly | city/gods.c:282-297 |

### 5.1.4 Blessings

| God | Effect | Duration | Source |
|---|---|---|---|
| Ceres | every farm in use: harvest progress set to maximum, curse cleared, `blessing_days_left = 16`. While blessed, the progress added per production update is doubled (workers counted twice) | 16 production days (1 month) | building/industry.c:379-395, 287-293 |
| Neptune | export income +50 % (`treasury += price/2` on every export, also native trader sales) | 12 months | city/gods.h:5; city/gods.c:70-72; city/finance.c:149-156; countdown city/gods.c:52-56 |
| Mercury | every staffed industry that has some raw material below 3 loads × raw amount: raw stock raised to 3 loads × raw amount; production in progress set to maximum | instant | building/industry.c:28, 397-424 |
| Mars | spirit of Mars power 10: the next enemy formation that has waited > 32 updates kills up to 10 enemy figures (not revolting gladiators) | until used | city/gods.c:78-80; figure/formation_enemy.c:451-473, 578-580 |
| Venus | festival sentiment boost +18; every age group from 25 years takes the count of the group 3 years older (city gets 3 years younger above 25); for 35 months the unemployment threshold for unhappiness is `5 + (months_left/12 + 1)` %; with the fixed-workers option, working share of plebs is `45 % + same bonus` | 35 months | city/gods.h:6; city/gods.c:82-86; city/population.c:332-355; city/sentiment.c:24, 188; city/labor.c:17, 219-225 |

### 5.1.5 Small curses

| God | Effect | Duration | Source |
|---|---|---|---|
| Ceres | every farm: progress 0, blessing cleared, no production; city mint too | 4 production days | building/industry.c:426-447, 281-286 |
| Neptune | if no sea route, no active shipyard and no active wharf: message only. Else: half of trade ships and half of fishing boats sink; sea trade problems 40 days; next flotsam shows a shipwreck | 40 days | city/gods.c:100-110; figuretype/water.c:335-370 |
| Mercury | the granary or warehouse (no plague) with the largest stock loses `BUILDING_STORAGE_QUANTITY_MAX / 2` = 16: 16 loads from a warehouse; 16 in the granary unit for a granary (granary unit unverified) | instant | building/granary.c:22, 646-695; building/storage.h:29 |
| Mars | local uprising of barbarians, see 5.4.12 | instant | city/gods.c:115-121; scenario/invasion.c:648-667 |
| Venus | festival sentiment boost −15; city health −10 | instant | city/gods.c:122-127 |

### 5.1.6 Major curses

| God | Effect | Duration | Source |
|---|---|---|---|
| Ceres | every farm and the city mint: progress 0, no production | 48 production days (3 months) | building/industry.c:437, 445 |
| Neptune | if no sea trade (same test as small curse): message only and the monthly routine stops. Else: all trade ships and fishing boats sink; sea trade problems 80 days | 80 days | city/gods.c:140-149; figuretype/water.c:315-333 |
| Mercury | the granary or warehouse with the largest stock burns down | instant | building/granary.c:679-684 |
| Mars | the legion with the largest weight (soldiers, ×2 for legionaries) sends all soldiers back to barracks (the soldiers leave the legion); `cursed_by_mars = 96`; this counter falls by 1 per formation update (2 per day), so the legion cannot recruit or move for 48 days. A local uprising follows (also when no legion exists) | 48 days | city/gods.c:155-163; figure/formation_legion.c:61-66, 128-130, 173-175, 303-331; figure/formation.c:623-628 |
| Venus | every house: happiness capped at 40, then −10; city health −50 (health ≥ 80), −40 (≥ 60), else −20; the next plague check with health < 40 forces plague | until next plague check | city/gods.c:164-177; city/sentiment.c:48-57, 70-82; city/health.c:196-201 |

### 5.1.7 Festivals

| Rule | Value / formula | Cadence | Source |
|---|---|---|---|
| Small festival cost | `population/20 + 10` Dn | at scheduling | city/festival.c:240 |
| Large festival cost | `population/10 + 20` Dn | at scheduling | city/festival.c:241 |
| Grand festival cost | `population/5 + 40` Dn | at scheduling | city/festival.c:242 |
| Grand festival wine | `population/500 + 1` loads; grand festival is not available when warehouse wine (plus Venus grand temple wine with Venus module 1) is lower | at scheduling | city/festival.c:232-250 |
| Payment | money is paid at once as "sundry"; wine is removed at once (first from the Venus grand temple with module 1, then from warehouses) | at scheduling | city/festival.c:150-165 |
| Delay | small 2 months, large 3 months, grand 4 months | monthly countdown | city/festival.c:139-148, 216-221 |
| Sentiment effect, first festival in a 12-month window | blessing/festival boost +6 (small), +9 (large), +18 (grand) | at festival | city/festival.c:170-176 |
| Sentiment effect, second festival in a 12-month window | +2 (small), +3 (large), +9 (grand); a third festival in the window gives no boost | at festival | city/festival.c:177-184 |
| Boost decay | boost × 0.84 each month (truncated to integer) | monthly | city/sentiment.c:23, 162-166; game/tick.c:97 |
| Boost use | boost is added to the sentiment of every house | at sentiment update (days 0 and 8) | city/sentiment.c:279, 348; game/tick.c:135-137 |
| God effect | the god's months since festival = 0 (target +12, higher happy bolt chance, no curse for 3 months) | at festival | city/festival.c:185-186; city/gods.c:263, 268 |
| Cooldown | none for the player; the 12-month windows only reduce the sentiment boost | - | city/festival.c:168-187 |
| Pantheon automatic festival | with a working Pantheon: each year one god receives a free small-size festival effect; god = `total_years % 5`; month (0-based): Ceres 3, Neptune 6, Mercury 4, Mars 2, Venus 3 | yearly | city/festival.c:15-21, 189-193, 223-229 |

### 5.1.8 Games (Colosseum events)

Field order: cost base, cost scaling, delay months, duration days, bonus months (city/games.h:9-23). Money comes from personal savings.

| Game | Money cost | Goods (× (3 + pop/1200)) | Delay / duration / bonus | Bonus effect | Source |
|---|---|---|---|---|---|
| Naval battle (id 1) | `1500 + 100 × (pop/1200)` | wine 1, timber 1 | 1 month / 32 days / 12 months | soldier move speed +25 % (legionary), +50 % (javelin), +75 % (mounted), +85 % (auxilia infantry), +60 % (archer); +1 distant battle strength factor for the next dispatch | city/games.c:29-33, 55-85, 194-199; figuretype/soldier.c:330-345; figure/formation_legion.c:220-222 |
| Imperial games (id 2) | `800 + 150 × (pop/1200)` | wheat 2, oil 1 | 1 / 32 / 12 | sentiment +15; favor +2 per month | city/games.c:34-37; city/sentiment.c:35, 168-178; city/ratings.c:18, 561-564 |
| Executions (id 3) | `800 + 150 × (pop/1200)` | meat 2 (or fish 2 if more fish is stored) | 1 / 32 / 12 | sentiment +20; no criminals; no gladiator revolt; Colosseum sends 2 lion tamers that hunt enemies | city/games.c:38-41, 71-81; city/sentiment.c:34; figuretype/crime.c:219-223; scenario/gladiator_revolt.c:19; building/figure.c:744-748 |
| Games cooldown | 0 (disabled) | - | - | - | city/festival.c:120-123 |


## 5.2 Grand temples and the Pantheon

### 5.2.1 General rules

| Rule | Value / formula | Cadence | Source |
|---|---|---|---|
| "Working" monument | construction finished, state in use, and workers ≥ full laborer count. Every base effect and every module needs a working monument; a monument with fewer than full workers gives no effect | each check | building/monument.c:772-799 |
| Module cost | 1000 Dn (construction expense) | once | window/building/culture.c:30, 1323 |
| Modules per monument | 1 (Caravanserai and Lighthouse can change); module needs a finished monument | - | building/monument.c:375-385 |
| Module test | grand temple module = `module % 2 + 1` on temple `module / 2`; Pantheon module = 1 or 2 | each check | building/monument.c:839-862 |
| Culture rating | +6 per active grand temple | yearly / rating update | city/ratings.c:17, 439-443 |
| Religion coverage | grand temple 5000 for its own god; Pantheon 1500 for every god | daily | city/culture.c:19-20, 159-160 |
| Monthly levy | grand temple 44 Dn; Pantheon 48 Dn; no levy before completion | monthly | city/finance.h:12-13; building/building.c:1003-1005 |

### 5.2.2 Base effects (no module)

| Monument | Effect | Source |
|---|---|---|
| Ceres grand temple | cart pushers from farms (wheat .. pig farm) move +50 % faster | figuretype/cartpusher.c:317-328 |
| Neptune grand temple | fountain range +1; reservoir range +2; well range +1; fountain laborers ÷ 2 (minimum 1); house sickness growth −5 per update; sea trade ships move +25 % faster | map/water_supply.c:346-374; building/building.c:1042-1048; city/health.c:267-270; figuretype/trader.c:125-133, 781 |
| Mercury grand temple | land traders (caravans, donkeys, native traders) move +25 % faster; land trader capacity 8 → 12 loads; sea trader capacity 12 → 18 loads. The code has a smaller bonus (+2 / +3) for partial staff, but a monument with partial staff is not "working", so the smaller bonus never applies | figuretype/trader.c:115-123, 1004-1055; building/monument.c:794-796 |
| Mars grand temple | maximum legions 6 → 10; works as a barracks (accepts weapons, recruits soldiers and tower sentries with the barracks delay table, without the troops-production scaling); mess hall sends a second supplier; a fort can be placed with no barracks | figure/formation.h:7; figure/formation.c:428-438; building/barracks.c:56-67; building/figure.c:1189-1249, 1862-1865; building/construction_warning.c:145 |
| Venus grand temple | market buyers deliver 12 instead of 8 × (house need) of each good; statues, gardens and temples: desirability value + max(1, value/4), step +1, range +1; house devolve delay 2 → 20 evolution checks | figure/service.c:404-409; map/desirability.c:115-121, 142-147; building/house_evolution.c:20-21, 578-582 |
| Pantheon | levy × 3/4 (integer: `levy/4 × 3`) for small and large temples, grand temples, oracle, nymphaeum and mausoleums; automatic festivals (5.1.7); contaminated water, iron mine collapse and clay pit flood are skipped when all five gods have happiness ≥ 60 | building/building.c:1014-1021; city/festival.c:223-229; scenario/random_event.c:161-174 |

### 5.2.3 Modules

| Module | Effect | Source |
|---|---|---|
| Ceres 1 (reduce food) | houses with Ceres temple access eat 40 % of population per month instead of 50 % | city/resource.c:516-531 |
| Ceres 2 (distribute food) | Ceres temples get a supplier; they fetch food (up to 600) and oil from storage; their priests distribute these goods to houses like a market | building/figure.c:1352-1355; building/temple.c:9, 28-57; figure/service.c:584-588 |
| Neptune 1 (hippodrome access) | each Neptune temple sends a charioteer every second priest spawn cycle (the temple works as a chariot maker) | building/figure.c:490-500, 1318-1326 |
| Neptune 2 (capacity and water) | houses with Neptune access: capacity + `(capacity + 1)/20` (about +5 %); the Neptune grand temple supplies reservoir range water in a radius equal to the reservoir radius | building/house_population.c:56-70; map/water_supply.c:231-235 |
| Mercury 1 (pottery, furniture) | all houses use 20 % less pottery and furniture | building/house_evolution.c:535-539 |
| Mercury 2 (oil, wine) | houses with Mercury access use 20 % less oil and wine | building/house_evolution.c:540-544 |
| Mars 1 (mess hall) | Mars temple priests collect food offerings from each house they pass: per food type the house holds, +house size (merged 1x1 house: +2) once every 16 days, temple cap 400 per type; the temple sends a priest with food (type with ≥ 100 stock) to the mess hall when the hall has ≤ 1600 of that type; fort levy × 3/4 | figure/service.c:346-367, 483-500, 602-606; building/monument.h:9; building/figure.c:1330-1350; building/temple.c:10, 60-72; building/building.c:1023-1028 |
| Mars 2 (all goods) | houses with Mars access use 10 % less wine, oil, pottery and furniture (adds to Mercury reductions) | building/house_evolution.c:545-551 |
| Venus 1 (distribute wine) | the Venus grand temple stores wine; Venus temples fetch wine from it (same road network, temple stock below baseline); Venus priests deliver this wine to taverns; the grand temple wine counts as one extra wine type for houses; grand festivals can use this wine | building/temple.c:14-26; figure/service.c:612-619; city/trade.c:17-23; city/festival.c:152-165, 234-238 |
| Venus 2 (desirability, entertainment) | houses with Venus access: villas and palaces desirability +4, range +1; tents +2, range 1; other houses +2 (range at least 1); entertainment +10 | map/desirability.c:90-106; building/house_service.c:136-139 |
| Pantheon 1 (destination priests) | every temple and grand temple sends one extra priest that walks to the Pantheon and gives its temple's coverage to houses on the path | building/figure.c:1240-1248, 1362-1370; figuretype/service.c:89-93, 141-149; figure/movement.c:322-324 |
| Pantheon 2 (housing evolution) | houses with Pantheon access use the desirability and goods/services requirements of one level lower | building/house_evolution.c:31-36, 54-63, 194-200, 507-513 |

### 5.2.4 How consumption reductions work

| Rule | Value / formula | Cadence | Source |
|---|---|---|---|
| Reduction r % for a good | the house consumes this good only in months where `(total_months × (100 − r)) % 100 < (100 − r)`; in other months it skips the good | per consumption | building/house_evolution.c:553-561 |
| Consumption days | day 0 for all houses; also day 7 for houses larger than 1x1 | 1 or 2 times per month | building/house_evolution.c:597-600 |

## 5.3 Levies (temples, forts, monuments)

| Building | Monthly levy (Dn, before difficulty) | Source |
|---|---|---|
| Fort (each of 5 types) | 8 | city/finance.c:29-33; city/finance.h:10 |
| Small temple, oracle, nymphaeum | 4 | city/finance.c:34-38, 44, 57; city/finance.h:9 |
| Large temple | 8 | city/finance.c:39-43; city/finance.h:18 |
| Small and large mausoleum | 2 | city/finance.c:55-56; city/finance.h:19 |
| Tower | 2 | city/finance.c:45; city/finance.h:11 |
| Lighthouse | 8 | city/finance.c:46; city/finance.h:14 |
| Grand temple | 44 | city/finance.c:47-51; city/finance.h:12 |
| Pantheon | 48 | city/finance.c:52; city/finance.h:13 |
| Colosseum | 36 | city/finance.c:53; city/finance.h:15 |
| Hippodrome | 72 | city/finance.c:54; city/finance.h:16 |
| Caravanserai | 8 | city/finance.c:58; city/finance.h:17 |
| Highway | `tiles/4 × 1`, ÷ 2 with a working highway station | city/finance.c:383-396; city/finance.h:20 |
| Difficulty multiplier on building levies | very easy 0 %, easy 0 %, normal 50 %, hard 100 %, very hard 100 % | game/difficulty.c:11, 19-23, 51-54; building/building.c:1030 |
| Payment | all levies are paid monthly | city/finance.c:371-400 |

## 5.4 Military

### 5.4.1 Forts and legions

| Rule | Value / formula | Cadence | Source |
|---|---|---|---|
| Fort types | legionaries, javelin, mounted, auxilia infantry, auxilia archers | - | city/finance.c:29-33 |
| Soldiers per fort | 16 maximum | each formation update | figure/formation.h:8; figure/formation.c:865-874 |
| Maximum legions | 6; 10 with a working Mars grand temple | - | figure/formation.h:7; figure/formation.c:428-438 |
| Morale of a new legion | 50 | at creation | figure/formation.c:132 |
| Recruit request | a fort asks for recruits only when the legion is at the fort, is not cursed by Mars and has fewer than 16 soldiers | daily | figure/formation_legion.c:61-80 |
| Soldier healing | a soldier at rest loses 1 damage point per formation update (2 per day) | 2 × daily | figure/formation_legion.c:422-434 |

### 5.4.2 Unit statistics

HP = `max_damage`. Blank cells are 0.

| Figure | HP | Attack | Defense | Missile defense | Missile attack | Missile delay | Source |
|---|---|---|---|---|---|---|---|
| Legionary | 150 | 10 | 2 | | 2 | 150 | figure/properties.c:70-78 |
| Javelin thrower | 80 | 4 | | | 4 | 100 | figure/properties.c:56-63 |
| Mounted auxiliary | 120 | 8 | | | | | figure/properties.c:64-69 |
| Auxilia infantry | 110 | 8 | 1 | 2 | | | figure/properties.c:509-515 |
| Auxilia archer | 90 | 6 | | | 4 | 50 | figure/properties.c:521-528 |
| Tower sentry | 50 | 6 | | | 6 | 50 | figure/properties.c:213-220 |
| Watchman | 50 | 6 | | | 6 | 50 | figure/properties.c:456 (row) |
| Ballista | 100 | | | | | 200 | figure/properties.c:361-365 |
| Prefect | 50 | 5 | | | | | figure/properties.c:50 (row) |
| Mess hall supplier | 70 | 8 | 1 | | | | figure/properties.c:425 (row) |
| Enemy 43 spear | 70 | 5 | | | 4 | 70 | figure/properties.c:221 (row) |
| Enemy 44 sword | 90 | 7 | 1 | 1 | | | figure/properties.c:229 (row) |
| Enemy 45 sword | 120 | 12 | 2 | 2 | | | figure/properties.c:237 (row) |
| Enemy 46 camel | 120 | 7 | 1 | | 5 | 70 | figure/properties.c:245 (row) |
| Enemy 47 elephant | 200 | 20 | 5 | 8 | 6 | 70 | figure/properties.c:254 (row) |
| Enemy 48 chariot | 120 | 15 | 4 | 4 | | | figure/properties.c:264 (row) |
| Enemy 49 fast sword | 90 | 7 | 1 | | | | figure/properties.c:272 (row) |
| Enemy 50 sword | 110 | 10 | 2 | 2 | | | figure/properties.c:279 (row) |
| Enemy 51 spear | 70 | 5 | | | 3 | 100 | figure/properties.c:287 (row) |
| Enemy 52 mounted archer | 100 | 6 | 1 | | 4 | 70 | figure/properties.c:295 (row) |
| Enemy 53 axe | 120 | 15 | 2 | | | | figure/properties.c:304 (row) |
| Revolting gladiator | 100 | 9 | 2 | | | | figure/properties.c:311 (row) |
| Caesar javelin | 90 | 4 | | | 4 | 100 | figure/properties.c:318 (row) |
| Caesar mounted | 100 | 8 | | | | | figure/properties.c:326 (row) |
| Caesar legionary | 150 | 13 | 2 | 2 | 2 | 150 | figure/properties.c:332 (row) |
| Native warrior | 40 | 6 | | | | | figure/properties.c:208-212 |
| Wolf | 80 | 8 (difficulty-adjusted, see 5.6.8) | | | | | figure/properties.c:392 (row) |

### 5.4.3 Barracks recruitment

| Rule | Value / formula | Cadence | Source |
|---|---|---|---|
| Spawn delay by staff | ≥ 100 %: 8; ≥ 75 %: 12; ≥ 50 %: 16; ≥ 25 %: 32; ≥ 1 %: 48 days; 0 %: none | daily counter | building/figure.c:1680-1694 |
| Food penalty | delay + (food stress − 20) when stress > 20 | daily | building/figure.c:1696-1699 |
| Troops production scaling (barracks only) | delay × 100 / troops `production_per_month` (default 100; change with action `change_production_rate` on troops) | daily | building/figure.c:1701-1706; game/resource.c:87 |
| Spawn rule | the counter must exceed the delay, so one recruit takes delay + 1 days | daily | building/figure.c:1708-1710 |
| Weapons | a legionary recruit needs 1 weapon in the barracks; other types need no weapons | per recruit | building/barracks.c:138-140, 180-184 |
| Weapon storage | 4 weapons maximum per barracks; cart pushers choose the barracks (or Mars grand temple) with distance + 8 × stored weapons lowest | - | building/barracks.h:7; building/barracks.c:21-75 |
| Target legion | barracks priority type first, then legionaries, then the closest fort; legions in a distant battle are skipped | per recruit | building/barracks.c:84-153 |
| No recruit needed | the barracks sends a tower sentry instead (tower or watchtower, by priority setting) | per spawn | building/figure.c:1718-1720; building/barracks.c:226-263 |
| Mars grand temple recruitment | same delay table 8/12/16/32/48 and the same food penalty; no troops-production scaling; also sends a priest | daily | building/figure.c:1189-1237 |

### 5.4.4 Military academy

| Rule | Value / formula | Cadence | Source |
|---|---|---|---|
| Use | a new recruit walks first to the closest academy that has full workers | per recruit | building/barracks.c:155-199 |
| Training flag | one trained recruit sets `has_military_training` for the whole legion | per recruit | figuretype/soldier.c:483-484 |
| Morale cap | legionaries 80 → 90; other player types 60 → 70 | - | figure/formation.c:455-465 |
| Distant battle strength factor | legionary 2 → 3; other types 1 → 2 | at dispatch | figure/formation_legion.c:214-219 |

### 5.4.5 Morale

| Rule | Value / formula | Cadence | Source |
|---|---|---|---|
| Morale cap | legionary 80 (90 trained); javelin, mounted, infantry, archer 60 (70 trained); Caesar legionary 100; barbarian, Numidian, Gaul, Celt, Goth 80; Greek, Carthaginian 90; other enemies 70; plus the mess hall modifier | each change | figure/formation.c:455-485 |
| Mess hall modifier | `clamp((food_types − 1) × 5, 0, 10)`; +5 if stress < 3; −stress/3 if stress > 20; result clamped to −30 .. +15 | monthly | figure/formation.c:554-579 |
| Legion at fort | morale +5; low-morale counters reset | monthly | figure/formation.c:581-594; game/tick.c:95 |
| Legion away from fort, no recent fight | months from home +1; above 3: morale −5 per month | monthly | figure/formation.c:595-603 |
| Deployed legion with morale ≤ 20 (first time) | all legions −5, all enemies +10 | daily (tick 5) | figure/formation.c:530-534, 882-884 |
| Enemy formation with morale ≤ 20 (first time) | all legions +5, all enemies −10 | daily (tick 5) | figure/formation.c:541-544 |
| Low-morale counters | morale ≤ 10: very-low counter +1; ≤ 20: low counter +1 (counted per day despite the "months" name) | daily | figure/formation.c:535-549 |
| Low morale result | a formation with either counter > 0 flees (legion to fort; enemy figures get the fleeing state) | 2 × daily | figure/formation.c:379-382; figure/formation_legion.c:391-401; figure/formation_enemy.c:647-658 |
| Legion move order blocked | very-low counter > 0 or low counter > 1; with low counter = 1, the order gives +10 morale | per order | figure/formation_legion.c:108-117 |
| Morale loss per death | `pct = 100/(soldiers + 1)`: < 8: −4; < 10: −6; < 14: −8; < 20: −10; < 30: −12; else −16 | per death | figure/formation.c:487-506 |
| Distant battle loss | morale −75 for each legion in the battle | per battle | figure/formation_legion.c:247-250 |

### 5.4.6 Soldiers' food (mess hall)

| Rule | Value / formula | Cadence | Source |
|---|---|---|---|
| Food per soldier | `4 + difficulty adjustment` per month: very easy 1, easy 1, normal 2, hard 4, very hard 5 | monthly | city/resource.h:7; game/difficulty.c:13, 19-23, 56-59; city/resource.c:584-585 |
| Soldiers counted | soldiers in legions that are not in a distant battle | monthly | city/military.c:55-75 |
| Consumption | food is taken from each type in proportion to its stock; a mothballed mess hall gives no food | monthly | city/resource.c:573-627 |
| Missing % | `100 − stored × 100 / required` when stock < required, else 0; 100 when soldiers exist and no mess hall exists | monthly | city/resource.c:613-622, 693-697 |
| Food stress | `stress = (missing % + stress)/2`, cap 100 | monthly | city/resource.c:704-712 |
| Warning | stress > 50: "soldiers starving" message (once until stress < 20) | monthly | city/resource.c:698-708 |
| Effects of stress | morale cap modifier (5.4.5); recruitment delay + (stress − 20) | - | figure/formation.c:572-574; building/figure.c:1696-1699 |
| Months of food (advisor) | `stored / (soldiers × 4)` (no difficulty term) | display | city/military.c:174-183 |

### 5.4.7 Walls, towers, gatehouses and watchtowers

| Rule | Value / formula | Cadence | Source |
|---|---|---|---|
| Tower crew | a tower with workers gets a tower sentry from a barracks; when it has a sentry, it creates a ballista | daily | building/figure.c:328-344; building/barracks.c:208-263 |
| Ballista range | 15 tiles; fires every 200 ticks | per tick | figuretype/wall.c:22, 81-91; figure/properties.c:361-365 |
| Tower sentry range | 10 tiles; missile every 50 ticks | per tick | figuretype/wall.c:131, 276-278 |
| Watchtower | spawns watchmen only after a barracks sentry arrives; spawn delay by staff 10/20/30/40/60 days | daily | building/figure.c:1979-2007 |
| Watchtower archer range | 12 tiles | per tick | figuretype/wall.c:23, 479-489 |
| Enemy routing classes | wall = wall class; gatehouse = gatehouse class; most buildings = attackable building class; forts = fort class; warehouses, fort ground, gates, bridges, roadblocks = passable; native buildings = blocked; aqueduct, garden, access ramp, rubble = clearable; trees, rock, shrub, water and other not-clear terrain = blocked; road, highway, beach = passable | at routing update | map/routing_terrain.c:148-243 |
| `TERRAIN_IMPASSABLE_ENEMY` | tree, rock, water, shrub, garden, elevation, rubble, marshland. Used to choose formation destination tiles | per move order | map/terrain.h:56-57; figure/formation_enemy.c:426 |
| Invasion entry tile | elevation, rock or tree: the invasion does not start; water without road (bridge): does not start; building, aqueduct, gatehouse or wall on the tile: destroyed | at spawn | scenario/invasion.c:416-428 |

### 5.4.8 Scheduled invasions (scenario editor list)

| Rule | Value / formula | Cadence | Source |
|---|---|---|---|
| Fields | year (offset from start year), type, amount min/max, from (invasion point), attack type, month, repeat times, repeat interval min/max (years) | - | scenario/invasion.h:23-41 |
| Types | 1 local uprising, 2 enemy army, 3 Caesar, 4 distant battle, 5 Mars natives | - | scenario/types.h:5-10 |
| Defaults | year 1, amount 1..1, type 2, from 8 (random point), attack random | - | scenario/invasion.h:8-13 |
| Month | random 2..9 (0-based: March to October), chosen at scenario start and again at each repeat | at start / repeat | scenario/invasion.c:205-217, 476 |
| Warnings | for each enemy-army or Caesar invasion, the engine takes the next empire invasion path (round-robin) and creates one warning per battle icon of years 1..7 on that path; `months_to_go = 12 × year + month − 12 × icon_year` | at start | scenario/invasion.c:151-203 |
| Warning messages | when `months_to_go ≤ 0`: icon year > 2: "distant battle" message; > 1: "enemies closing"; else "enemies at the door" | monthly | scenario/invasion.c:582-597 |
| Launch | when game year ≥ start year + year and month ≥ invasion month: every warning of this invasion is closed; only a warning with icon year ≤ 1 starts the attack | monthly | scenario/invasion.c:598-626 |
| Consequence for maps | an enemy army or Caesar invasion starts only through a year-1 battle icon on an empire invasion path. With no invasion path, no warning exists and the invasion never starts | - | scenario/invasion.c:159-162, 598-605 |
| Amount | random `min .. max−1`, then × difficulty enemy % (very easy 40, easy 60, normal 80, hard 100, very hard 120), cap 150 | at launch | scenario/invasion.c:337-340, 606; game/difficulty.c:8, 19-23, 46-49 |
| Enemy type | scenario enemy id mapped to one of 11 nations | - | scenario/invasion.c:41-62, 609 |
| Composition | per nation: % of type 1 / type 2 (leftovers go to type 1); barbarian 100 fast sword; Numidian 40 fast sword / 60 spear; Gaul 50 sword / 50 axe; Celt 80 sword / 20 chariot; Goth 50 fast sword / 50 mounted archer; Pergamum 30 sword / 70 spear; Seleucid 50/50 sword/spear; Etruscan 50/50; Greek 80/20; Egyptian 80 sword / 20 camel; Carthaginian 90 sword / 10 elephant; Caesar 100 legionary | at launch | scenario/invasion.c:68-87, 345-349 |
| Formations per type | ≤ 16 soldiers: 1; ≤ 32: 2; else 3. A formation holds at most 16 figures; what happens to extra soldiers when one type has more than 48 is unverified | at launch | scenario/invasion.c:299-316 |
| Entry point | `from` 0..7 = fixed point; 8 = random: 0..1 if ≤ 2 points defined, 0..3 if ≤ 4, else 0..7; an undefined point moves to the next defined one; no point: map exit; Caesar: map entry | at launch | scenario/invasion.c:363-403 |
| Arrival stagger | each soldier waits `200 × formation_seq + 10 × index + 10` ticks before it enters | at launch | scenario/invasion.c:450 |
| Repeat | times −1 = infinite, else times −1; next year += random `interval_min .. interval_max − 1`; month re-rolled; warnings rebuilt from the current date | at launch | scenario/invasion.c:461-568, 622-624 |
| Local uprising | no warnings; starts when year and month are exactly equal; barbarian troops; repeats without warnings | monthly | scenario/invasion.c:627-644 |

### 5.4.9 Attack types and targets

| Attack type | Target list, in priority order (closest building of the first type found) | Source |
|---|---|---|
| 0 food chain | granary, warehouse, market, wheat, vegetable, fruit, olive, vine, pig farm | figure/formation_enemy.c:27-31 |
| 1 gold stores | senate, forum | figure/formation_enemy.c:32-35 |
| 2 best buildings | governor's palace, villa, house; then houses from luxury palace down to small tent | figure/formation_enemy.c:36-48 |
| 3 troops | military academy, prefecture | figure/formation_enemy.c:49-51 |
| 4 random | a new random choice of 0..3 each time a target is set | figure/formation_enemy.c:251-256 |
| Fallback | when no building of the list exists: the rioter target list | figure/formation_enemy.c:259-262 |
| Retreat | no target and all figures inside the city: "enemies leaving" message, army retreats | figure/formation_enemy.c:687-690 |
| Legion avoidance | `enemy_army_is_stronger_than_legions()` tests `enemy_strength > 2 × legion_strength`. At this commit no code adds legion strength (`enemy_army_totals_add_legion_formation` has no caller), so the test is true whenever enemies exist. Every enemy army then has `ignore_roman_soldiers = 1`: it does not seek legions and marches to its building target | figure/enemy_army.c:64-82, 124-127; figure/formation.c:776-805; figure/formation_enemy.c:629-633, 678-680, 500-503 |
| Event action target "natives" | the editor label "natives" maps to type 2 (best buildings) | scenario/event/parameter_data.c:772-778 |

### 5.4.10 Caesar's legions

| Rule | Value / formula | Cadence | Source |
|---|---|---|---|
| Anger warning | favor ≤ 10 and no countdown: warning, countdown 192 days (1 year) | daily (tick 4) | city/emperor.c:140-148 |
| Attack size | 1st 32, 2nd 64, 3rd 96, later 144 (then × difficulty enemy %, cap 150) | at countdown end | city/emperor.c:149-171; scenario/invasion.c:337-340 |
| Siege duration counter | 192 days | daily | city/emperor.c:166 |
| Retreat | favor ≥ stop value and counter < 176: army retreats. Stop value: 20 / 22 / 24 / 27 / 30 (very easy .. very hard) | daily | city/emperor.c:111-116; game/difficulty.c:15, 19-23 |
| Pause | favor ≥ pause value: army pauses. Pause value: 16 / 17 / 18 / 20 / 22 | daily | city/emperor.c:117-124; game/difficulty.c:14, 19-23 |
| Victory over Caesar | killed Caesar legionaries ≥ stored size: favor +10 if favor < stop value | daily | city/emperor.c:125-139 |
| Victory reachability | the stored size is the unadjusted size (32/64/96/144), but the spawned count is size × difficulty enemy % (cap 150), and only removed Caesar legionaries are counted. On very easy, easy and normal (40/60/80 %) the count cannot reach the stored size, so the +10 favor and "respect" message do not occur | - | city/emperor.c:163-169, 415-418; figure/figure.c:128-130; scenario/invasion.c:337-340 |
| Scenario or event Caesar attack | `city_emperor_force_attack(size)`: attack starts at once with the given size; the flag `cheated_invasion` = 1 turns off the favor retreat and pause logic for this attack. The flag is a file-static variable and is not in the save (behavior after reload: unverified) | at launch | city/emperor.c:28, 106-108, 420-431; scenario/invasion.c:619-621, 729-733 |

### 5.4.11 Distant battles

| Rule | Value / formula | Cadence | Source |
|---|---|---|---|
| Start | invasion of type 4 in its year and month, when no distant battle is active: enemy strength random `min .. max−1`; months until battle 24 | monthly | scenario/distant_battle.c:41-58; city/military.c:198-207 |
| Travel times | Roman and enemy travel months come from the empire map army objects | at scenario load | scenario/distant_battle.c:29-39 |
| Roman strength | sum over legions marked for empire service with ≥ 1 soldier: soldiers × factor; factor legionary 2 (3 trained), others 1 (2 trained), +1 with the naval battle games bonus; cap 255 | at dispatch | figure/formation_legion.c:202-245 |
| Roman travel | each month the remaining travel falls by 1, or by 2 when the Romans are behind the enemy; minimum 1 | monthly | city/military.c:209-238 |
| No troops sent | favor −50; city becomes foreign | at battle | city/military.c:289-292 |
| Troops too late (> 2 months away) | favor −25; city foreign; troops return | at battle | city/military.c:293-297 |
| Roman strength < enemy | favor −10; city foreign; all sent soldiers die | at battle | city/military.c:259-261, 298-303 |
| Victory | favor +25; triumphal arch earned; loss % by advantage `(R − E)/R`: < 10 %: 70; < 25 %: 50; < 50 %: 25; < 75 %: 15; < 100 %: 10; < 150 %: 5; else 0. The advantage cannot exceed 100 %, so the minimum loss is 5 % | at battle | city/military.c:262-282, 304-312 |
| Foreign city | 24 months, then the city is retaken | monthly | city/military.c:247-253, 334-340 |

### 5.4.12 Mars uprising and other invasion sources

| Rule | Value / formula | Cadence | Source |
|---|---|---|---|
| Mars uprising size | original campaign mission 0..19: table 0,0,0,0,0,3,3,3,0,6,6,6,6,6,9,9,9,9,9,9; other scenarios with ≥ 1 invasion entry: random 3..8; no invasion entry: no uprising | at curse | scenario/invasion.c:64-66, 648-661 |
| Mars uprising troops | barbarians, random point, food chain target, then × difficulty enemy % | at curse | scenario/invasion.c:662 |
| Event action invasion | see action 28 in 5.7.6 | - | scenario/invasion.c:697-759 |

## 5.5 Natives

| Rule | Value / formula | Cadence | Source |
|---|---|---|---|
| Native buildings | created from editor images at game start: hut, alternative huts, large huts, meeting center, crops, decoration, monument, watchtower, well, palisade | at start | map/natives.c:111-242 |
| Initial anger | meeting center and huts start at anger 100 (hostile) | at start | map/natives.c:209, 218, 229 |
| Native land radius | building size × 3: 1x1 hut 3 tiles, 2x2 meeting center or large hut 6 tiles | daily | map/natives.c:367-375 |
| Anger growth | a native building with anger < 100 gains +1 per day; native land is marked only around buildings with anger ≥ 100 | daily (tick 6) | map/natives.c:360-390 |
| Pacification | a missionary resets anger to 0 for huts, large huts, meeting centers and native watchtowers within 4 tiles of each tile it walks on. Without a new visit, anger is back at 100 after 100 days | per missionary step | figure/service.c:202-221 |
| Mission post coverage | the mission post shows 100 % houses covered when it is connected to Rome | daily | building/figure.c:1433-1445 |
| Attack trigger | an angry building (anger ≥ 100) has a non-native building, aqueduct, wall or garden inside its native land, and the natives are not retreating: native attack for 2 days | daily | map/natives.c:40-73, 379-384; city/military.c:82-85 |
| Attack restart | when the 2-day counter is 0, the native formation's low-morale counter is cleared, so a new attack can start | daily | city/military.c:87-95 |
| Warrior spawn | each hut with a meeting center spawns 1 native when its counter exceeds 4 (one native per hut at a time) | daily | building/figure.c:1615-1632 |
| Warrior behavior | in peace: walks to its meeting center and back. During an attack: walks to the native formation target | per tick | figuretype/native.c:55-92 |
| Attack target | the non-native building closest to the main meeting center (forts, warehouses, roadblocks, gates, bridges and native buildings excluded); if none, a wall, aqueduct or garden tile on native land; if none, the natives retreat | daily | figure/formation_enemy.c:273-385, 722-724 |
| Native trader spawn | a meeting center with anger < 100 sends a trader when its counter exceeds 8 days | daily | building/figure.c:1655-1672 |
| Native trader trade | goes to the closest storage that allows natives; buys 1 unit at a time of an export-status resource; pays the sell price as export income (Neptune blessing applies); each unit counts 3 against the land trade capacity (8, or 12 with the Mercury grand temple), so one trip buys up to 3 (or 4) units | per trip | figuretype/trader.c:608-700; city/finance.c:149-156 |
| Resource choice | the code compares the stock with the resource id (`resources[r] > highest_resource`), not with the best stock; the result is usually a high-index export resource that has stock | per visit | figuretype/trader.c:203-216 |
| Native warrior stats | HP 40, attack 6 | - | figure/properties.c:208-212 |

## 5.6 Disasters and random events

### 5.6.1 Monthly random event roll

| Rule | Value / formula | Cadence | Source |
|---|---|---|---|
| Roll | `random_byte()` (0..127) indexes a 128-entry table | monthly | scenario/random_event.c:31-40, 175 |
| Rome raises wages | 3/128 (2.3 %) | monthly | scenario/random_event.c:31-40 |
| Rome lowers wages | 3/128 (2.3 %) | monthly | same |
| Land trade disrupted | 5/128 (3.9 %) | monthly | same |
| Sea trade disrupted | 4/128 (3.1 %) | monthly | same |
| Contaminated water | 2/128 (1.6 %) | monthly | same |
| Iron mine collapse | 4/128 (3.1 %) | monthly | same |
| Clay pit flood | 5/128 (3.9 %) | monthly | same |
| No event | 102/128 | monthly | same |
| Scenario flags | each event needs its scenario flag | - | scenario/random_event.c:44, 55, 66, 82, 94, 115, 134 |
| Cooldown (trade, water, mine, clay pit) | months since the last event of the same kind must exceed: very easy 36, easy 30, normal 24, hard 18, very hard 12 | monthly | game/difficulty.c:16, 19-23; scenario/random_event.c:68, 84, 96, 116, 135 |
| Wage cooldown | 12 months for raise and lower together | monthly | scenario/random_event.c:29, 45, 56 |
| Pantheon protection | water, mine and clay pit events are skipped when a working Pantheon exists and all gods have happiness ≥ 60 | monthly | scenario/random_event.c:161-174, 189-203 |

### 5.6.2 Random event effects

| Event | Effect | Source |
|---|---|---|
| Rome raises wages | Rome wages + 1..4, cap scenario maximum | city/labor.c:188-198 |
| Rome lowers wages | Rome wages − 1..4, floor scenario minimum | city/labor.c:200-210 |
| Land trade disrupted | needs a land route; 48 days of land trade problems | scenario/random_event.c:64-78 |
| Sea trade disrupted | needs a sea route; 48 days of sea trade problems | scenario/random_event.c:80-90 |
| Trade problem countdown | −1 per day; −2 per day with a fully working caravanserai (land) or lighthouse (sea) | city/trade.c:26-45 |
| Trade problem effect | empire cities do not send new traders of that kind | empire/city.c:455-466 |
| Contaminated water | needs population > 200; city health −40 (health > 80), −30 (> 60), else −20 | scenario/random_event.c:92-111 |
| Iron mine collapse | destroys the first iron mine; with option "random collapses take money": −250 Dn instead (only if an iron mine exists) | scenario/random_event.c:113-130 |
| Clay pit flood | same rule for the first clay pit | scenario/random_event.c:132-149 |

### 5.6.3 Earthquake

| Rule | Value / formula | Cadence | Source |
|---|---|---|---|
| Date | scenario year; month random 2..9 (0-based) | at start | scenario/earthquake.c:40-43 |
| Small | 25 + 0..31 steps; 1 step per 10 ticks (5 to 11 days) | per tick | scenario/earthquake.c:49-52, 249-256 |
| Medium | 100 + 0..63 steps; 1 step per 8 ticks (16 to 26 days) | per tick | scenario/earthquake.c:53-56 |
| Large | 250 + 0..127 steps; 1 step per 6 ticks (30 to 45 days) | per tick | scenario/earthquake.c:57-60 |
| Spread | each step moves one of 4 arms 1 tile in a random direction; rock, water, elevation and access ramp stop the arm | per step | scenario/earthquake.c:69-76, 257-283; map/terrain.h:63 |
| Tile effect | the building on the tile is destroyed (all parts of a multi-part building), the terrain becomes earthquake ground; roads, highways, gardens, walls, aqueducts on it are removed | per step | scenario/earthquake.c:78-138 |
| Custom earthquake | uses tiles marked in the editor; delay 10 + 1..15 ticks (right-left pattern, 1 tile per step) or 10 + 1..90 ticks (random pattern, up to 5 tiles per step) | per tick | scenario/earthquake.c:154-236 |

### 5.6.4 Gladiator revolt

| Rule | Value / formula | Cadence | Source |
|---|---|---|---|
| Date | scenario year; month random 3..6 (0-based) | at start | scenario/gladiator_revolt.c:35-41 |
| Condition | at least one active gladiator school and no executions games bonus | at start date | scenario/gladiator_revolt.c:17-26 |
| Duration | until the month that is 3 months after the start month | monthly | scenario/gladiator_revolt.c:28-33, 53-58 |
| Effect | every gladiator that walks to a venue, roams or returns becomes a hostile gladiator (HP 100, attack 9, defense 2) | per tick | figuretype/entertainer.c:320-330 |
| Event action | starts a new revolt now (also when the scenario flag is off) | at action | scenario/gladiator_revolt.c:72-88 |

### 5.6.5 Emperor change

| Rule | Value / formula | Cadence | Source |
|---|---|---|---|
| Date | scenario year; month random 1..8 (0-based) | at start | scenario/emperor_change.c:16-21 |
| Effect | favor set to 50; message | once | scenario/emperor_change.c:23-35; city/ratings.c:249-252 |

### 5.6.6 Fire and collapse

| Rule | Value / formula | Cadence | Source |
|---|---|---|---|
| Skip | no check when population < 10 | daily (tick 44) | building/maintenance.c:177-179 |
| Match day | each building matches the global random value with chance 1/8 per day | daily | building/maintenance.c:176, 188 |
| Damage risk | +1 per day; +3 on a match day (average +1.25 per day); small and large tents: always 0 | daily | building/maintenance.c:190-196 |
| Collapse | damage risk > 200 | daily | building/maintenance.c:197-201 |
| Fire risk increase (match day only) | non-house +5; empty house 0; up to large shack +10; up to grand insula +5; villas and palaces +2; northern climate: 0; desert: +3 more. Average per day = value / 8 | daily | building/maintenance.c:203-226 |
| Fire | fire risk > 100 | daily | building/maintenance.c:227-230 |
| Fire-proof buildings | skipped | daily | building/maintenance.c:182 |
| Reset | a prefect resets fire risk to 0; an engineer resets damage risk to 0 | per visit | figure/service.c:304, 312 |
| Burning ruin | becomes rubble after 32 days; tries to spread every 8 days (4 in desert) with chance 1/4, to the yearly fire direction or its two neighbours | daily (tick 43) | building/maintenance.c:38-115 |

### 5.6.7 Flotsam

| Rule | Value / formula | Cadence | Source |
|---|---|---|---|
| Flotsam | 20 floating objects on maps with river entry, river exit and the flotsam flag; visual only. After a Neptune curse, one object shows a shipwreck | at start, then loops | figuretype/water.c:35-118 |

### 5.6.8 Herds and wolves

| Rule | Value / formula | Cadence | Source |
|---|---|---|---|
| Herd points | 4 maximum | - | scenario/data.h:11 |
| Herd by climate | central: 10 sheep; northern: 8 wolves; desert: 12 zebras | at start | figuretype/animal.c:74-104 |
| Wolf respawn | a wolf pack below its size adds 1 wolf when its counter exceeds 32 formation updates (about 16 days); the option "disable infinite wolves" stops it | 2 × daily | figure/formation_herd.c:27, 168-190, 249-261 |
| Wolf attack value | 8 (hard, very hard); normal 6; easy 4; very easy 2 | per attack | figure/properties.c:392 (row); game/difficulty.c:61-69; figure/combat.c:76-78 |
| Wolf hunt radius | 6 tiles | per move | figure/formation_herd.c:149 |

## 5.7 Scenario event system

### 5.7.1 Event life cycle

| Rule | Value / formula | Cadence | Source |
|---|---|---|---|
| States | 0 undefined, 1 disabled, 2 active, 3 paused, 4 deleted | - | scenario/event/data.h:18-24 |
| Check cadence | every day: first all paused counters −1 day, then every event is checked in list order | daily | game/tick.c:146-147; scenario/event/controller.c:540-566 |
| Extra checks | once when the mission briefing closes (scenario start, day 0), and after "replay map" | once | window/mission_briefing.c:462; window/pause_menu.c:105; widget/top_menu.c:897 |
| Event without actions | never fires | - | scenario/event/event.c:175-177 |
| Condition groups | all groups must pass. "All" group: every condition must be met. "Any" group: at least one condition must be met (an empty "any" group passes) | per check | scenario/event/event.c:170-198 |
| Event without conditions | fires at the first check | - | scenario/event/event.c:170-198 |
| Unknown condition type | counts as met | per check | scenario/event/condition_handler.c:98-100 |
| Actions | all actions run in list order; a failed action does not stop the others | at fire | scenario/event/event.c:245-256 |
| Repeat test | repeat allowed when `repeat_days_min > 0`, `max ≥ min`, and (`execution_count < max_repeats` or `max_repeats ≤ 0`) | at fire | scenario/event/event.c:164-168 |
| After firing | `execution_count + 1`; repeatable: paused for random `min .. max−1` days (exactly `min` when min = max); else disabled | at fire | scenario/event/event.c:228-243 |
| Pause end | when `days_until_active` reaches 0 the event is active and is checked the same day; a pause of N days gives the next check N days later | daily | scenario/event/event.c:200-216 |
| Repeat unit | stored in days; the editor shows days, months (× 16) or years (× 192); `repeat_interval` only selects the display unit | - | scenario/event/data.h:186-188; window/editor/scenario_event_details.c:772-810 |
| Old scenarios | repeat values in months are converted × 16 | at load | scenario/event/event.c:73-76 |
| New event default | display unit = days | - | scenario/event/controller.c:220 |

### 5.7.2 Comparison codes

| Code | XML text | Test | Source |
|---|---|---|---|
| 1 | eq | value = target | scenario/event/data.h:142; scenario/event/condition_comparison_helper.c:8-9 |
| 2 | lte | value ≤ target | condition_comparison_helper.c:10-11 |
| 3 | gte | value ≥ target | condition_comparison_helper.c:12-13 |
| 4 | neq | value ≠ target | condition_comparison_helper.c:14-15 |
| 5 | lt | value < target | condition_comparison_helper.c:16-17 |
| 6 | gt | value > target | condition_comparison_helper.c:18-19 |
| Other | - | false | condition_comparison_helper.c:20-21 |

### 5.7.3 Formulas

| Rule | Value / formula | Cadence | Source |
|---|---|---|---|
| Operators | `+ − * / ^`, parentheses, unary minus, decimal numbers | - | scenario/event/formula.c:65-160 |
| Precedence | `^` (left to right), then `* /`, then `+ −` | - | scenario/event/formula.c:105-160 |
| Division by 0 | the result of the division is 0 | - | scenario/event/formula.c:133-136 |
| Custom variable | `[id]` or `[name]` (letters only); value read as integer | - | scenario/event/formula.c:18-22, 54-63, 74-79 |
| Random range | `{a,b}`: integer from a to b inclusive; a and b can be expressions | per evaluation | scenario/event/formula.c:80-94 |
| Result | rounded to nearest integer (x.5 rounds away from 0), then clamped to the parameter limits | per evaluation | scenario/event/formula.c:162-167, 255-256 |
| Static formula | no variable and no `{,}`: evaluated once when the formula is stored, then the stored value is used | once | scenario/event/formula.c:169-245, 252-254 |
| Dynamic formula | contains a variable or a random range: evaluated at every use | per use | scenario/event/formula.c:219, 235-237, 255-258 |
| Errors | comma outside braces, unbalanced braces, wrong comma count, `]` without `[`, unknown variable, letters outside `[ ]`: formula is an error and returns 0 | - | scenario/event/formula.c:177-234, 249-251 |
| Maximum length | 100 characters | - | scenario/event/data.h:15 |
| Invalid formula id | returns 0 | - | scenario/event/controller.c:156-164 |

### 5.7.4 Custom variables

| Rule | Value / formula | Cadence | Source |
|---|---|---|---|
| Value | 32-bit integer; name up to 64 bytes; display text up to 128 bytes | - | scenario/custom_variable.h:8-9; scenario/custom_variable.c:13-21 |
| Ids | start at 1; XML parameter range 0..99 | - | scenario/custom_variable.c:41; scenario/event/parameter_data.c:142-146 |
| Visibility and colour | changed by actions 34 and 50 | at action | scenario/event/action_types.c:114-120, 982-990 |

### 5.7.5 Condition types

Parameter limits come from scenario/event/parameter_data.c (line of the entry in column "Def."). "F" = formula.

| # | XML name | Parameters | Value tested | Def. | Source |
|---|---|---|---|---|---|
| 1 | time | check, value F [0..∞] | total months since the scenario start (`total_days / 16`) | 64 | condition_types.c:522-529; game/time.c:75-78 |
| 2 | difficulty | check, value 0..4 (very easy .. very hard) | difficulty setting | 68 | condition_types.c:357-364 |
| 3 | money | check, value F [−10000..∞] | treasury | 72 | condition_types.c:366-373 |
| 4 | savings | check, value F [0..∞] | personal savings | 76 | condition_types.c:468-475 |
| 5 | stats_favor | check, value F [0..100] | favor rating | 80 | condition_types.c:495-502 |
| 6 | stats_prosperity | check, value F [0..100] | prosperity rating | 84 | condition_types.c:513-520 |
| 7 | stats_culture | check, value F [0..100] | culture rating | 88 | condition_types.c:486-493 |
| 8 | stats_peace | check, value F [0..100] | peace rating | 92 | condition_types.c:504-511 |
| 9 | trade_sell_price | resource, check, value F [0..∞] | base sell price of the resource | 96 | condition_types.c:559-571 |
| 10 | population_unemployed | percentage (bool), check, value F | unemployed workers, or unemployment % | 101 | condition_types.c:375-384 |
| 11 | rome_wages | check, value F [0..10000] | Rome wages | 106 | condition_types.c:459-466 |
| 12 | city_population | check, value F, class | class 1 = all; a house type = people at that level; house group or patrician (villa..palace), plebeian (casa..grand insula), slums (tent..large hovel) = sum | 110 | condition_types.c:296-335 |
| 13 | building_count_active | check, value F, building | active count; menu groups (farms, raw materials, workshops, small/large/grand temples, trees, paths, parks), roads, highways, plazas, gardens, overgrown gardens, rubble and bridges count tiles or sets | 115 | condition_types.c:47-115 |
| 14 | stats_health | check, value F [0..100] | city health | 120 | condition_types.c:477-484 |
| 15 | count_own_troops | check, value F, in_city_only | all soldiers, or soldiers not in a distant battle | 124 | condition_types.c:337-346 |
| 16 | request_is_ongoing | request id, check_for_ongoing (bool) | request ongoing state | 129 | condition_types.c:386-393 |
| 17 | tax_rate | check, value F [0..25] | tax % | 133 | condition_types.c:573-580 |
| 18 | building_count_any | check, value F, building | same as 13 but counts all built (not only active) | 137 | condition_types.c:117-185 |
| 19 | variable_check | variable, check, value F | custom variable value | 142 | condition_types.c:348-355 |
| 20 | trade_route_open | route, check_for_open (bool) | route open state (invalid route: false) | 147 | condition_types.c:531-542 |
| 21 | trade_route_price | route, check, value F | route opening cost; 0 when the route is open | 151 | condition_types.c:544-557 |
| 22 | resource_stored_count | resource, check, value F, storage type (all / granaries / warehouses) | warehouse loads + granary food ÷ one load | 156 | condition_types.c:425-457 |
| 23 | resource_storage_available | resource, check, value F, storage type | free space for the resource; parameter 5 (respect settings) exists in the definition but the code does not read it | 162 | condition_types.c:395-423 |
| 24 | building_count_area | corner 1, corner 2, building, check, value F | count of the building type in the rectangle | 169 | condition_types.c:217-294 |
| 25 | check_formulas | formula 1, check, formula 2 | compares two formulas | 176 | condition_types.c:187-196 |
| 26 | terrain_in_area | corner 1, corner 2, terrain, check, value F | tiles in the rectangle with that terrain bit | 181 | condition_types.c:198-215 |
| 27 | enemies_in_city | check, value F | invading enemy figures | 188 | condition_types.c:582-589 |
| 28 | land_trade_problem_duration | check, value F | days of land trade problems left | 192 | condition_types.c:591-598 |
| 29 | sea_trade_problem_duration | check, value F | days of sea trade problems left | 196 | condition_types.c:600-607 |
| 30 | months_since_last_festival | check, god (or All), value F | months since the last festival (All) or since that god's festival | 200 | condition_types.c:609-621 |
| 31 | desirability_in_area | corner 1, corner 2, check, value F | mean desirability of the rectangle (integer division) | 205 | condition_types.c:623-640 |
| 32 | population_in_area | corner 1, corner 2, housing type, check, value F | people in houses of the type in the rectangle; a merged house counts once | 211 | condition_types.c:642-716 |
| 33 | figures_in_area | corner 1, corner 2, figure category, check, value F | figures of the category in the rectangle | 218 | condition_types.c:718-731 |

### 5.7.6 Action types

"F" = formula with the given clamp limits. "Set" = boolean `set_to_value` (true: set; false: add). Action functions are in scenario/event/action_types.c; the dispatch is in scenario/event/action_handler.c:10-124.

| # | XML name | Parameters | Exact effect | Def. (parameter_data.c) | Source (action_types.c) |
|---|---|---|---|---|---|
| 1 | favor_add | amount F [−100..100] | favor + amount | 233 | 237-243 |
| 2 | money_add | F [unlimited] | treasury + amount (miscellaneous income/expense) | 236 | 275-281 |
| 3 | savings_add | F [unlimited] | personal savings + amount | 239 | 341-347 |
| 4 | trade_price_adjust | resource, amount F [−10000..10000], show_message | buy and sell price both + amount. If amount < 0 and sell ≤ 0: fails. If amount < 0 and sell ≤ −amount: buy = 2, sell = 0 | 242 | 530-555; empire/trade_prices.c:148-162 |
| 5 | trade_problems_land | duration F [0..10000] days | land trade problems = duration; resets the random land-trade-event cooldown counter | 247 | 557-570 |
| 6 | trade_problems_sea | duration F [0..10000] days | sea trade problems = duration; resets the random sea-trade-event cooldown counter | 250 | 572-581 |
| 7 | trade_route_amount | route, resource, amount F [0..∞], show_message, buying | sets the yearly amount that the route city buys or sells | 253 | 624-662 |
| 8 | change_rome_wages | F [−10000..10000], Set | Rome wages set or + amount, minimum 1; resets the 12-month random wage cooldown | 260 | 298-339 |
| 9 | gladiator_revolt | - | starts a revolt now (5.6.4) | 264 | 245-250 |
| 10 | change_resource_produced | resource, produced (bool) | city can or cannot produce the resource | 266 | 140-150 |
| 11 | change_allowed_buildings | building, allowed (bool) | building available or not in menus | 270 | 60-69 |
| 12 | send_standard_message | text id | posts an original game message (ids from "population 500" to "road to Rome warning"); other ids do nothing | 274 | 421-431 |
| 13 | city_health | F [−100..100], Set | city health set or + amount | 277 | 199-211 |
| 14 | trade_price_set | resource, amount F [0..∞], set_buy_price, show_message | difference = amount − current base buy price (if set_buy_price) or base sell price; then **both** buy and sell move by that difference (same rules as action 4). The other price does not stay fixed | 281 | 433-469 |
| 15 | empire_map_convert_future_trade_city | city, show_message | a future trade city becomes a trade city | 287 | 213-235 |
| 16 | request_immediately_start | request id | starts the request now; fails in the first month (total months < 1) | 291 | 283-296 |
| 17 | show_custom_message | message id | posts the custom message | 294 | 664-679 |
| 18 | tax_rate_set | F [0..25] | tax rate set | 297 | 681-688 |
| 19 | change_variable | variable, value F [unlimited], Set | variable set or + value | 300 | 99-112 |
| 20 | change_trade_route_open_price | route, amount F [unlimited], Set, show_message | route opening cost set or + amount | 305 | 583-606 |
| 21 | change_city_rating | rating (peace or prosperity), amount F [−100..100], Set | peace or prosperity set or changed; other ratings do nothing | 311 | 71-97 |
| 22 | change_resource_stockpiles | resource, amount F [unlimited], storage type, respect_settings | amount > 0: adds goods (warehouses first, then granaries for "all"); amount < 0: removes (warehouses first) | 316 | 152-197 |
| 23 | trade_route_set_open | route, apply_cost | opens the route; with apply_cost the opening cost is paid (sundry) and the route resource costs (action 54) are taken from warehouses, then granaries for food | 322 | 608-622; empire/city.c:474-486 |
| 24 | trade_route_add_new_resource | route, resource, amount F [0..∞], add_as_buying, show_message | adds a new bought or sold resource to the route city; amount ≤ 0 fails | 326 | 495-528 |
| 25 | trade_set_buy_price_only | resource, amount F [0..∞] | buy price = amount, minimum 1 | 333 | 471-481; empire/trade_prices.c:11, 164-173 |
| 26 | trade_set_sell_price_only | resource, amount F [0..∞] | sell price = amount, minimum 1 | 337 | 483-493; empire/trade_prices.c:175-184 |
| 27 | building_force_collapse | corner 1, corner 2, building, destroy_all | collapses matching buildings in the rectangle (forts by the fort menu type); road, garden, highway, overgrown garden, rubble types remove that terrain; tiles with tree, rock, water, shrub, elevation, marshland or access ramp are skipped; burning ruins are skipped | 341 | 349-419 |
| 28 | invasion_start_immediate | invasion type (enemy army / caesar / natives = local uprising / mars), size F [1..200], point F [1..9], target type, enemy type | starts an attack now. Point 1..8 = invasion point; 9 = random. Enemy type: only "undefined" is offered (uses the scenario enemy; local uprising uses barbarians). Size × difficulty enemy %, cap 150. Caesar type uses `city_emperor_force_attack` | 347 | 252-273; scenario/invasion.c:697-759 |
| 29 | cause_blessing | god or All | runs the blessing (5.1.4) | 354 | 690-697; city/gods.c:492-502 |
| 30 | cause_minor_curse | god or All | runs the small curse (5.1.5); does not change happiness or bolts | 357 | 699-706; city/gods.c:504-521 |
| 31 | cause_major_curse | god or All | runs the major curse (5.1.6); does not change happiness or bolts | 360 | 708-715 |
| 32 | change_climate | climate | changes the scenario climate | 363 | 717-724 |
| 33 | change_terrain | corner 1, corner 2, terrain, add | add: a blocking terrain destroys buildings without rubble and replaces other blocking terrain; remove water: destroys water buildings | 366 | 726-770 |
| 34 | change_variable_visibility | variable, value (bool) | shows or hides the variable | 379 | 114-120 |
| 35 | variable_formula | variable, formula F [unlimited] | variable = formula result | 384 | 122-130 |
| 36 | variable_city_property | variable, property, up to 3 extra parameters | variable = a city value: difficulty, money, population, savings, last year net balance, resource stock, stats (favor, prosperity, culture, peace, health), service coverage, unemployment, population by house type, population by age, Rome wages, city wages, building count, own troops, enemy troops, terrain tiles, quota fill, opened routes | 388 | 132-138; scenario/event/parameter_city.c:332-390; scenario/event/parameter_data.c:946-969 |
| 37 | change_god_sentiment | god or All, amount F [−100..100], Set | god happiness set or changed, bounded 0..100 (target and bolts do not change) | 395 | 788-800; city/gods.c:412-436 |
| 38 | change_pop_sentiment | amount F [−100..100], Set | happiness of every house set or changed, bounded 0..100 | 400 | 802-814; city/sentiment.c:48-68 |
| 39 | win | - | forces victory | 404 | 816-821 |
| 40 | lose | - | forces defeat | 406 | 823-828 |
| 41 | change_rank | rank | sets the player rank | 408 | 830-835 |
| 42 | change_model_data | building model, data type, amount F [unlimited], Set | changes a building model value (cost, desirability, laborers, etc.), bounded to the limits of that data type | 372 | 772-786 |
| 43 | change_production_rate | resource (all, incl. troops), rate F [unlimited], Set | `production_per_month` set or + rate, minimum 0. For troops this scales barracks recruitment (5.4.3) | 411 | 837-851 |
| 44 | lock_trade_route | route, lock, show_message | lock: city becomes "distant Roman" and closed; unlock: city becomes a trade city and opens free of cost | 426 | 869-897 |
| 45 | change_house_model_data | housing level, data type, value F [0..∞], Set | changes a house model value, bounded to the limits of that data type | 418 | 853-867 |
| 46 | change_goal | win condition, value F [0..∞], Set | win goal set, or changed. **Side effect:** in add mode, every goal except culture adds the *culture* goal, not its own goal (`value + culture.goal`). Only enabled goals change. Value is clamped to the goal maximum | 431 | 899-945 |
| 47 | move_camera | grid offset | moves the view | 438 | 947-954 |
| 48 | change_weather | weather type, intensity F [0..∞] | starts weather | 441 | 956-964 |
| 49 | hide_trade_route | route, hide | hides or shows the route line | 446 | 966-980 |
| 50 | change_variable_color | variable, colour group | sets the display colour | 450 | 982-990 |
| 51 | change_immigration_percentage | value F [0..∞], change_immigration | sets the immigration % (true) or emigration % (false) adjustment | 454 | 992-1004 |
| 52 | change_monument_resources | monument, stage 1..5, resource, amount F [0..∞] | sets the resource need of one monument stage | 459 | 1006-1017 |
| 53 | rename_city | city, text | sets an empire city name (50 characters) | 465 | 1019-1030 |
| 54 | change_resource_cost | route, resource, amount F [0..∞] | sets the route cost value for that resource | 469 | 1032-1046 |
| 55 | kill_walkers_in_area | corner 1, corner 2, figure category | kills figures of that category in the rectangle | 474 | 1048-1058 |
| 56 | send_city_warning | text, play_fanfare | shows a custom warning text; optional fanfare | 479 | 1060-1071 |

### 5.7.7 Side effects for economic models

| Rule | Value / formula | Source |
|---|---|---|
| Price set moves both prices | `trade_price_set` keeps the buy–sell gap: it moves buy and sell by the same difference. To set one price only, use actions 25 or 26 | scenario/event/action_types.c:433-469; empire/trade_prices.c:148-162 |
| Price floor | `trade_price_adjust` and `trade_price_set` with a large negative difference give buy 2, sell 0; with sell already ≤ 0 they fail | empire/trade_prices.c:150-160 |
| Wage and trade actions reset random cooldowns | actions 5, 6 and 8 set the matching "months since last event" counter to 0, so the matching random event cannot occur during its cooldown | scenario/event/action_types.c:303, 561, 576; scenario/random_event.c:45, 56, 68, 84 |
| Curses by action do not reset gods | actions 30 and 31 do not reset wrath bolts or raise happiness, unlike the natural curses | city/gods.c:263-279, 504-521 |
| Range limits are exclusive in non-formula ranges | event repeat days, invasion amounts and repeat years use `min .. max−1` (5.0.1) | core/random.c:109-117 |
| Static formulas | a formula without a variable or `{,}` is computed once; changing a variable later does not change a static formula | scenario/event/formula.c:238-243, 252-254 |
| Change goal bug | relative change of a non-culture goal adds the culture goal | scenario/event/action_types.c:913-940 |

### 5.7.8 What events cannot do

The action dispatch (scenario/event/action_handler.c:10-124) is the complete list of 56 actions in 5.7.6. The items below have no action. They are derived from that list; each one names the nearest action that exists.

| Cannot | Nearest available action |
|---|---|
| Set culture or favor directly (`change_city_rating` only accepts peace and prosperity: action_types.c:71-97) | favor: `favor_add −100` then `favor_add +X`; culture: none |
| Build or place any building, house or native village | `building_force_collapse` removes; `change_terrain` changes terrain only |
| Create a new trade city or route, or move a route | `empire_map_convert_future_trade_city`, `lock_trade_route`, `trade_route_add_new_resource` |
| Set a price for one route only (prices are global) | `trade_set_buy_price_only`, `trade_set_sell_price_only` |
| Change trader frequency, trader loads, trader slots or trade policies | none (constants in empire/city.c:33-35, figuretype/trader.c) |
| Create a new Caesar request or change its amount | `request_immediately_start` only starts an existing request |
| Change the city wage that the player sets | `change_rome_wages` changes the Rome reference wage |
| Change the Caesar salary base or give a salary | `change_rank` (salary follows rank) |
| Change coverage capacities (theater 500, temple 750 and so on), walker ranges, food per person, storage capacity, immigration batch size | none (engine constants); `change_immigration_percentage` scales immigration |
| Select or change a Grand Temple module, or set monument progress | `change_monument_resources` changes material needs |
| Move entry, exit, river, invasion, fish or herd points | none |
| Read a player choice from a dialog | none: maps detect choices with building counts, route open state or variables |
| Check more often than once per day | none (5.7.1) |

Defects in existing actions (verified in source):
- `change_goal` in add mode adds the culture goal, not the goal it changes, for every goal except culture (action_types.c:899-945).
- `trade_price_set` moves both prices (5.7.7).
- `request_immediately_start` fails in the first month (action_types.c:283-296).
- `resource_storage_available` does not read its respect_settings parameter (condition_types.c:395-423).
