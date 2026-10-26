# Chapter 3: Population, migration, labour and sentiment

All source references are to `src/` at upstream commit `dae1899`. A reference has the form `file:line`.

Units and terms in this chapter:

- One game day is 50 ticks (`game/time.h:13`). One month is 16 days (`game/time.h:14`). One year is 12 months.
- "Pleb house" means a house from small tent to grand insula (building types 10 to 21). "Patrician house" means a house from small villa to luxury palace (building types 22 to 29) (`building/type.h:24-43`).
- House level numbers: small tent = 0, large tent = 1, small shack = 2, large shack = 3, small hovel = 4, large hovel = 5, small casa = 6, large casa = 7, small insula = 8, medium insula = 9, large insula = 10, grand insula = 11, small villa = 12, and so on to luxury palace = 19 (`building/type.h:244-252`).
- `calc_adjust_with_percentage(v, p)` = `p * v / 100`, integer division (`core/calc.c:22-25`). `calc_percentage(v, t)` = `100 * v / t`, integer division, 0 when `t` = 0 (`core/calc.c:27-35`).
- Food in granaries is stored in loads. Food in houses, markets, mess halls and the caravanserai is stored in units. One load = 100 units (`game/resource.h:72`, `building/granary.c:24-25`).

## 3.1 Daily and monthly order of operations

The simulation runs one subsystem per tick number (`game/tick.c:150-201`). The table lists only the ticks that this chapter uses.

| Tick / time | Function | What it does | Source |
|---|---|---|---|
| Tick 8 | `building_granaries_calculate_stocks` | Counts granary stock that "getting" granaries can take | `game/tick.c:163` |
| Tick 12 | `house_service_decay_houses_covered` | Decreases `houses_covered` of each building by 1 | `game/tick.c:165`, `building/house_service.c:64-75` |
| Tick 17 | `city_resource_calculate_food_stocks_and_supply_wheat` | Counts granary food; fills markets and mess halls with wheat when Rome supplies wheat | `game/tick.c:167`, `city/resource.c:500-514` |
| Tick 20 | `building_industry_update_production(1)` | Industry progress, strike countdown (new day) | `game/tick.c:169` |
| Tick 21 | `building_maintenance_check_rome_access` | Sets `distance_from_entry` for each building | `game/tick.c:170`, `building/maintenance.c:238-330` |
| Tick 22 | `house_population_update_room` | Recalculates housing capacity and free room | `game/tick.c:171`, `building/house_population.c:72-95` |
| Tick 23 | `house_population_update_migration` | Migration, yearly census update (when requested), worker count | `game/tick.c:172`, `building/house_population.c:194-229` |
| Tick 24 | `house_population_evict_overcrowded` | Makes homeless figures from houses with negative room | `game/tick.c:173`, `building/house_population.c:231-248` |
| Tick 25 | `city_labor_update` | Labour need, allocation, unemployment | `game/tick.c:174`, `city/labor.c:564-569` |
| Tick 31 | `building_figure_generate` | Labour seekers, service walkers, beggars, plebeians | `game/tick.c:179` |
| Tick 33 | `city_culture_update_coverage` | Also calculates school age and academy age | `game/tick.c:181`, `city/culture.c:213` |
| Tick 45 | `figure_generate_criminals` | Protesters, robbers, looters, rioters, strikers | `game/tick.c:192`, `figuretype/crime.c:219-280` |
| Tick 46 | `building_industry_update_production(0)` | Industry progress (second pass of the day) | `game/tick.c:193` |
| Day 0 and day 8 of each month | `city_sentiment_update` | Sentiment update (2 times each month) | `game/tick.c:135-137` |
| Each month | `city_health_update`, `scenario_random_event_process`, `city_finance_handle_month_change`, `city_resource_consume_food`, `city_sentiment_decrement_blessing_boost`, `building_industry_start_strikes` | Rome wage roll, taxes and wages, food consumption, festival boost decay, new strikes | `game/tick.c:82-100` |
| Each year | `city_population_request_yearly_update` | Sets a flag. Aging, deaths and births run at the next tick 23 | `game/tick.c:75`, `city/population.c:415-428` |

## 3.2 Population census

The city keeps a census array `at_age[0..99]`. The city population is the sum of this array (`city/population.c:75-84`). The census is separate from the house populations. A daily check removes census people when the houses hold fewer people (`city/population.c:430-436`, called from `city/sentiment.c:270`).

### 3.2.1 Age of new people

| Rule | Value / formula | Cadence | Source |
|---|---|---|---|
| Age of each immigrant or returning homeless person | `r = random_from_pool(i) & 0x3f` (0 to 63). If `r > 50`, age = `r - 30`. Else if `r < 10` and the person has an odd index in the batch, age = `r + 20`. Else age = `r`. | Each time people enter a house | `city/population.c:86-99` |
| Maximum immigrant age | 50 | - | `city/population.c:92-93` |
| Age of a newborn | 0 | Yearly | `city/population.c:364` |

Derived age distribution of immigrants. This assumes that the 6-bit pool value is uniform. The pool holds 7-bit random values (`core/random.c:31`, `core/random.c:47`).

| Age group | Share of immigrants |
|---|---|
| 0-9 | 7.8% |
| 10-19 | 15.6% |
| 20-29 | 37.5% |
| 30-39 | 21.9% |
| 40-49 | 15.6% |
| 50 | 1.6% |
| Mean age | about 27 |
| School age (0-13) | 14.1% |
| Academy age (14-20) | 11.7% |
| Working age (20-49) | 75.0% |
| Working age with "retire at 60" (20-59) | 76.6% |

### 3.2.2 Removal of people from the census

| Rule | Value / formula | Cadence | Source |
|---|---|---|---|
| Emigrants, homeless people, removed houses, troop requests | Random ages 0 to 63 from the pool. After 100 failed tries in a row, the code removes people from age 10 upward and wraps to age 0. | Per event | `city/population.c:101-132` |
| Troop request | Removes people from houses first, then the same number from the census | Per request | `city/population.c:211-217` |

### 3.2.3 Age groups

| Group | Ages | Source |
|---|---|---|
| School age | 0-13 | `city/population.c:259` |
| Academy age | 14-20 | `city/population.c:260` |
| Working age (default) | 20-49 (decades 2, 3, 4) | `city/population.c:219-227` |
| Working age with `CONFIG_GP_CH_RETIRE_AT_60` | 20-59 (decades 2 to 5) | `city/population.c:223-225` |
| Retired (default) | 60-99 | `city/population.c:229-237` |
| Retired with `CONFIG_GP_CH_RETIRE_AT_60` | 50-99 | `city/population.c:233-235` |

School age and academy age are recalculated at tick 33 each day (`city/culture.c:213`).

### 3.2.4 Yearly aging, deaths and births

The year change sets a flag (`game/tick.c:75`). The next tick 23 runs these steps in this sequence: aging and deaths, then births, then totals (`city/population.c:421-428`, `building/house_population.c:198`).

| Rule | Value / formula | Cadence | Source |
|---|---|---|---|
| Aging | Each age bucket moves up by 1 year. Age 0 becomes empty. | Yearly | `city/population.c:314-318` |
| People who reach 100 | The people in bucket 99 before the shift leave the census. The same number of people leave houses. | Yearly | `city/population.c:314`, `city/population.c:324` |
| Deaths per decade | `deaths = people_in_decade * DEATHS[health / 10][decade] / 100` | Yearly | `city/population.c:320-329` |
| Births per decade | `births = people_in_decade * BIRTHS[decade] / 100` | Yearly | `city/population.c:357-367` |
| Room limit on births | A newborn enters only a house that is in use, has `distance_from_entry > 0`, has `house_population > 0` and has free room. Births that do not fit are lost. | Yearly | `building/house_population.c:13-34` |
| Yearly statistics | `population_last_year`, `average_per_year` = sum of yearly populations / number of years. `lost_removal` resets to 0. | Yearly | `city/population.c:369-379` |

Birth rate table `BIRTHS_PER_AGE_DECENNIUM` (`city/population.c:10-12`):

| Decade (ages) | 0-9 | 10-19 | 20-29 | 30-39 | 40-49 | 50+ |
|---|---|---|---|---|---|---|
| Births per 100 people per year | 0 | 3 | 16 | 9 | 2 | 0 |

Death rate table `DEATHS_PER_HEALTH_PER_AGE_DECENNIUM` (`city/population.c:14-26`). The row is `city health / 10` (`city/population.c:322`). The values are deaths per 100 people per year.

| Health | 0-9 | 10-19 | 20-29 | 30-39 | 40-49 | 50-59 | 60-69 | 70-79 | 80-89 | 90-99 |
|---|---|---|---|---|---|---|---|---|---|---|
| 0-9 | 20 | 10 | 5 | 10 | 20 | 30 | 50 | 85 | 100 | 100 |
| 10-19 | 15 | 8 | 4 | 8 | 16 | 25 | 45 | 70 | 90 | 100 |
| 20-29 | 10 | 6 | 2 | 6 | 12 | 20 | 30 | 55 | 80 | 90 |
| 30-39 | 5 | 4 | 0 | 4 | 8 | 15 | 25 | 40 | 65 | 80 |
| 40-49 | 3 | 2 | 0 | 2 | 6 | 12 | 20 | 30 | 50 | 70 |
| 50-59 | 2 | 0 | 0 | 0 | 4 | 8 | 15 | 25 | 40 | 60 |
| 60-69 | 1 | 0 | 0 | 0 | 2 | 6 | 12 | 20 | 30 | 50 |
| 70-79 | 0 | 0 | 0 | 0 | 0 | 4 | 8 | 15 | 20 | 40 |
| 80-89 | 0 | 0 | 0 | 0 | 0 | 2 | 6 | 10 | 15 | 30 |
| 90-99 | 0 | 0 | 0 | 0 | 0 | 0 | 4 | 5 | 10 | 20 |
| 100 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 5 | 10 |

### 3.2.5 Other census rules

| Rule | Value / formula | Cadence | Source |
|---|---|---|---|
| Venus blessing: younger population | People of ages 28-99 become 3 years younger. Ages 25-27 receive the people from ages 28-30. Ages 97-99 become empty. | Per blessing | `city/population.c:332-355`, `city/gods.c:82-86` |
| Monthly population history | 2400 entries in a ring buffer | Monthly | `city/population.c:263-270`, `game/tick.c:117` |
| Population milestone messages | 500, 1000, 2000, 3000, 5000, 10000, 15000, 20000, 25000 | Daily check | `building/house_population.c:200-228` |
| People in tents | Houses with level <= large tent | Yearly and on request | `city/population.c:397-399` |
| People in tents and shacks | Houses with level <= large shack | Yearly and on request | `city/population.c:400-402` |
| People in villas and palaces | Houses with level >= small villa | Yearly and on request | `city/population.c:406-408` |

## 3.3 Housing capacity and entry point

| Rule | Value / formula | Cadence | Source |
|---|---|---|---|
| House capacity | `max_people` of the house level. Multiply by 4 for a merged house. | Daily (tick 22) | `building/house_population.c:56-70` |
| Neptune grand temple module 2 | Capacity + `(capacity + 1) / 20` for houses with Neptune temple access | Daily | `building/house_population.c:64-68` |
| Houses that count for capacity | Only houses with `distance_from_entry > 0` | Daily | `building/house_population.c:82-85` |
| House not connected to the entry point | Room is set to `-house_population`. All people are evicted at tick 24 as homeless figures. | Daily | `building/house_population.c:89-92`, `building/house_population.c:231-248` |
| Distance from entry | Road distance from the map entry point to a road tile within 2 tiles of the house | Daily (tick 21) | `building/maintenance.c:240-287` |
| House with no road within 2 tiles | After more than 4 checks, all people become homeless and the house is removed | Daily | `building/maintenance.c:253-263` |
| House with a road that the entry point cannot reach | `distance_from_entry` = 1 on the first check. After more than 8 checks, the house is removed. | Daily | `building/maintenance.c:273-283` |
| Lost immigrant | When an immigrant cannot find a route, the house `distance_from_entry` becomes 0 | Per event | `figuretype/migrant.c:152-156` |

House capacity and food values per level (`building/properties.c`). A scenario model file can change these values (`scenario/model_xml.c`, not read in detail).

| House | Max people | Tax multiplier | Food types | Entertainment needed | Source lines |
|---|---|---|---|---|---|
| Small tent | 5 | 1 | 0 | 0 | 147-161 |
| Large tent | 7 | 1 | 0 | 0 | 172-186 |
| Small shack | 9 | 1 | 1 | 0 | 197-211 |
| Large shack | 11 | 1 | 1 | 0 | 222-236 |
| Small hovel | 13 | 2 | 1 | 0 | 247-261 |
| Large hovel | 15 | 2 | 1 | 10 | 272-286 |
| Small casa | 17 | 2 | 1 | 10 | 297-311 |
| Large casa | 19 | 2 | 1 | 10 | 322-336 |
| Small insula | 19 | 3 | 1 | 25 | 347-361 |
| Medium insula | 20 | 3 | 1 | 25 | 372-386 |
| Large insula | 84 | 3 | 1 | 25 | 397-411 |
| Grand insula | 84 | 4 | 2 | 35 | 422-436 |
| Small villa | 40 | 9 | 2 | 35 | 447-461 |
| Medium villa | 42 | 10 | 2 | 40 | 472-486 |
| Large villa | 90 | 11 | 2 | 45 | 497-511 |
| Grand villa | 100 | 11 | 3 | 50 | 522-536 |
| Small palace | 106 | 12 | 3 | 55 | 547-561 |
| Medium palace | 112 | 12 | 3 | 60 | 572-586 |
| Large palace | 190 | 15 | 3 | 70 | 597-611 |
| Luxury palace | 200 | 16 | 3 | 80 | 622-636 |

## 3.4 Migration

Migration runs once each day at tick 23 (`building/house_population.c:196`, `city/migration.c:120-124`).

### 3.4.1 Migration percentage from sentiment

| City sentiment | Migration percentage | Source |
|---|---|---|
| > 70 | +100 | `city/migration.c:13-14` |
| 61-70 | +75 | `city/migration.c:15-16` |
| 50-60 | +50 | `city/migration.c:17-18` |
| 41-49 | 0 | `city/migration.c:19-20` |
| 31-40 | -10 | `city/migration.c:21-22` |
| 21-30 | -25 | `city/migration.c:23-24` |
| 0-20 | -50 | `city/migration.c:25-26` |

### 3.4.2 Batch size, caps and blocks

| Rule | Value / formula | Cadence | Source |
|---|---|---|---|
| Population cap | Migration percentage = 0 when population >= 200000. Tutorial 1 cap: 80 until its tasks are done. Tutorial 2 cap: 150 before a granary, 520 before pottery. | Daily | `city/migration.c:32-36`, `game/tutorial.c:97-112` |
| Invasion block | When more than 3 enemies invade and the percentage is positive, the percentage becomes 0 | Daily | `city/migration.c:37-42` |
| Immigrants per batch | `12 * (percentage * adjust_immigration / 100) / 100`. Maximum 12 people each day at default adjustment. | Daily | `city/migration.c:48-50` |
| Emigrants per batch | `12 * (-percentage * adjust_emigration / 100) / 100`. Results: -10% gives 1, -25% gives 3, -50% gives 6. | Daily | `city/migration.c:58-60` |
| Emigration minimum population | Emigration happens only when population > 100 | Daily | `city/migration.c:57` |
| Direction change delay | After a batch, the code sets `immigration_duration` or `emigration_duration` to 2. When the sign changes, the first 2 daily updates only decrease this counter. | Daily | `city/migration.c:45-46`, `city/migration.c:51`, `city/migration.c:55-56`, `city/migration.c:61` |
| Small batch queue | A batch smaller than 4 goes to a queue. The queue is released when batch + queue >= 4. | Daily | `city/migration.c:87-115` |
| Partial immigration | When some people find a house, the rest of the batch is lost (not queued). When nobody finds a house, the whole batch counts as refused. | Daily | `city/migration.c:66-74` |
| First emigration message | Shown 1 time | Once | `city/migration.c:107-110` |
| Scenario event: change immigration or emigration | Sets `adjust_percentage_immigration` or `adjust_percentage_emigration`. Default 100. | Per event | `scenario/event/action_types.c:992-1003`, `city/data.c:32-33` |

What blocks immigration: only sentiment, the population cap, more than 3 invading enemies and the lack of free room in houses. Wages, unemployment, taxes, food and housing level act on migration only through sentiment (`city/migration.c:11-64`).

### 3.4.3 Advisor "no immigration" cause

| Rule | Value | Source |
|---|---|---|
| Cause mapping | Low mood cause no jobs, high taxes, low wages, squalor map to the same immigration cause. Other values give "low mood". | `city/migration.c:126-151` |
| Unreachable causes | `LOW_MOOD_CAUSE_NO_FOOD` and `LOW_MOOD_CAUSE_MANY_TENTS` are never set by `city/sentiment.c`. The "no food" and "many tents" immigration causes cannot appear. | `city/sentiment.c:414-431`, `city/migration.c:129-143` |
| "No room" check | True when total free room <= 0 | `city/migration.c:158-161` |
| When the cause is calculated | When the advisor window opens | `window/advisors.c:154` |

### 3.4.4 Where immigrants go

| Rule | Value / formula | Cadence | Source |
|---|---|---|---|
| Valid house | In use, not plague, `distance_from_entry > 0`, no immigrant already in transit to it | Per batch | `building/house_population.c:109-141` |
| First pass | Houses with room >= 8 receive 4 people each (or the remainder when <= 4). Houses are scanned from small tent to luxury palace type. | Per batch | `building/house_population.c:108-124` |
| Second pass | Houses with room 1 to 7 receive up to their room | Per batch | `building/house_population.c:125-141` |
| Immigrant figure start | Created at the map entry point. Waits `10 + (house_figure_generation_delay & 0x7f)` ticks, then walks. | Per figure | `figuretype/migrant.c:23-32`, `figuretype/migrant.c:125-138` |
| House without road access | Immigrant figure dies; nobody arrives | Per figure | `figuretype/migrant.c:130-137` |
| Arrival | People enter only up to the free room at arrival time. The census grows at arrival, not at creation. An empty lot becomes a small tent. | Per figure | `figuretype/migrant.c:159-181` |

### 3.4.5 Emigrants and homeless people

| Rule | Value / formula | Cadence | Source |
|---|---|---|---|
| Houses that emigrants leave | Only types below large insula (small tent to medium insula) | Per batch | `building/house_population.c:148` |
| Emigrants per house | Up to 4 per house per batch | Per batch | `building/house_population.c:156-167` |
| Census for emigrants | People leave the census when the emigrant figure is created. A house that loses all people becomes a vacant lot. | Per figure | `figuretype/migrant.c:34-46` |
| Overcrowded house | People above capacity become homeless at tick 24. If all people leave, the house is removed. | Daily | `building/house_population.c:231-248` |
| Homeless census | Homeless people leave the census at creation and return when they enter a house | Per figure | `figuretype/migrant.c:48-57`, `figuretype/migrant.c:324` |
| Homeless search | After more than 51 ticks, a homeless figure goes to the nearest house with room (not plague, connected, no immigrant in transit). If no house exists, it walks to the map exit point and searches again on its way. | Per figure | `figuretype/migrant.c:256-282`, `figuretype/migrant.c:333-357` |
| Homeless arrival capacity | Uses `max_people` (x4 when merged). It does not add the Neptune module bonus. | Per figure | `figuretype/migrant.c:309-320` |

## 3.5 Sentiment

City sentiment is the population-weighted average of house happiness, bounded 0 to 100 (`city/sentiment.c:407-412`). With no population, city sentiment equals the difficulty default.

### 3.5.1 Cadence and smoothing

| Rule | Value | Source |
|---|---|---|
| Update days | Day 0 and day 8 of each month (2 times per month) | `game/tick.c:135-137` |
| Maximum change per house per update | +/- 2 (`MAX_SENTIMENT_CHANGE`) | `city/sentiment.c:31`, `city/sentiment.c:350-353` |
| Empty house happiness | City sentiment + 10, bounded 0 to 100 | `city/sentiment.c:303-306` |
| House happiness range | 0 to 100 | `city/sentiment.c:353` |

### 3.5.2 Target happiness of one house

Target = default + tax term + wage term - unemployment term + squalor term + desirability bonus + entertainment bonus + food bonus + games bonus + festival boost (`city/sentiment.c:308-348`).

| Factor | Value / formula | Applies to | Source |
|---|---|---|---|
| Default (difficulty) | Very easy 80, easy 75, normal 70, hard 65, very hard 60 | All houses | `game/difficulty.c:19-23`, `city/sentiment.c:272` |
| Tax term (taxed house) | `d = base_tax - tax_rate`. If `d < 0`: `d * (12 - base_tax)`. Else: `d * (base_tax / 2)`. | Houses with tax collector coverage | `city/sentiment.c:195-201`, `city/sentiment.c:311-312` |
| Tax term (untaxed house) | Tax term at tax rate 0, divided by 2 | Houses without tax coverage | `city/sentiment.c:275`, `city/sentiment.c:313-314` |
| Base tax rate (difficulty) | Very easy 10, easy 9, normal 8, hard 7, very hard 6 | - | `game/difficulty.c:19-23` |
| Tax rate range | 0 to 25 | - | `city/finance.c:123-126` |
| Wage term | `w = city_wages - rome_wages`. If `w > 0`: `2 * w`. Else: `3 * w`. | Pleb houses only | `city/sentiment.c:180-184`, `city/sentiment.c:318-321` |
| Unemployment term | `unemployment% - (5 + venus_bonus)` when positive, else 0. Subtracted. | Pleb houses only | `city/sentiment.c:186-193`, `city/sentiment.c:318-321` |
| Squalor term | `level - average_level`. When negative: multiply by 3, then by the tier multiplier. Positive values are added without a multiplier. | All houses | `city/sentiment.c:236-243`, `city/sentiment.c:324-329` |
| Squalor tier multiplier | Small tent and large tent: 3. Small shack to small casa: 2. Large casa to grand insula: 1. Villas and palaces: 0. | - | `city/sentiment.c:286-297` |
| Desirability bonus | `(desirability - 50) / 2`, bounded 0 to `house_level + 1` | All houses | `city/sentiment.c:245-249`, `city/sentiment.c:331-334` |
| Entertainment bonus | `entertainment - required`, bounded 0 to 24 | All houses | `city/sentiment.c:251-255`, `city/sentiment.c:336-339` |
| Food variety bonus | `12 * (food_types_eaten - required)`, bounded 0 to 24. 0 when the level needs no food. | All houses | `city/sentiment.c:257-265`, `city/sentiment.c:341-344` |
| Executions games | +20 while active | All houses | `city/sentiment.c:34`, `city/sentiment.c:168-178` |
| Imperial games | +15 while active | All houses | `city/sentiment.c:35`, `city/sentiment.c:168-178` |
| Festival and blessing boost | Current value of `blessing_festival_boost` | All houses | `city/sentiment.c:348` |

Factors that are not in the sentiment formula: religion coverage, god mood, food shortage (other than the variety bonus), number of tents and health (`city/sentiment.c:268-455`). Gods and food act through other paths, for example Venus wrath and house devolution.

### 3.5.3 Average housing level (for squalor)

| Rule | Value / formula | Source |
|---|---|---|
| Weighted average | `sum(level * pop * weight) / sum(pop * weight)` | `city/sentiment.c:205-230` |
| Weights | Small tent to small casa: 1. Large casa to grand insula: 10. Small villa to grand villa: 20. Small palace to luxury palace: 30. | `city/sentiment.c:209-219` |
| Floor value | `sum(pop * weight) / 625`, bounded 0 (small tent) to 8 (small insula) | `city/sentiment.c:36`, `city/sentiment.c:231-232` |
| Result | The higher of the weighted average and the floor | `city/sentiment.c:233` |

### 3.5.4 Festival boost and other changes

| Rule | Value | Cadence | Source |
|---|---|---|---|
| Festival, first effect slot | Small +6, large +9, grand +18. Slot locks for 12 months. | Per festival | `city/festival.c:168-176` |
| Festival, second effect slot | Small +2, large +3, grand +9. Slot locks for 12 months. | Per festival | `city/festival.c:177-183` |
| Venus blessing | +18 to the boost | Per blessing | `city/gods.c:82-86` |
| Boost decay | Boost x 0.84 (truncated) | Monthly | `city/sentiment.c:23`, `city/sentiment.c:162-166`, `game/tick.c:97` |
| Venus wrath | Each house happiness capped at 40, then -10 | Per wrath | `city/gods.c:164-167` |
| Riot | Each house happiness raised to at least 30 | Per riot | `figuretype/crime.c:266` |
| Scenario event | Set or change all house happiness | Per event | `scenario/event/action_types.c:808-810` |

### 3.5.5 City low mood cause and messages

| Rule | Value | Source |
|---|---|---|
| City low mood cause | The most negative of: unemployment term, taxed-house tax term, wage term, average squalor penalty per house | `city/sentiment.c:414-431` |
| House message threshold | A house below 80 happiness shows its worst factor | `city/sentiment.c:363-404` |
| Mood message | Sentiment < 48 and falling. Below 35: "angry". Below 40: "unhappy". Else "disgruntled". Then 3 updates of delay. | `city/sentiment.c:433-452` |

## 3.6 Crime, riots and strikes

### 3.6.1 Criminals and rioters

`figure_generate_criminals` runs daily at tick 45 (`game/tick.c:192`).

| Rule | Value / formula | Source |
|---|---|---|
| Executions games active | No criminals | `figuretype/crime.c:221-223` |
| Candidate house | The house with the lowest happiness below 50. Houses at 50 or more reset their criminal flag. | `figuretype/crime.c:233-247` |
| Crime cooldown | 10 days after each crime event. Each daily call decreases it by 1 and does nothing else. | `city/sentiment.c:33`, `city/sentiment.c:144-154`, `figuretype/crime.c:248-251` |
| Tutorials 1 and 2 | No criminals | `figuretype/crime.c:253-255` |
| Chance roll | Crime happens when `random_byte() >= sentiment + 20`. `random_byte()` is 0 to 127. Chance = `(108 - sentiment) / 128` for sentiment below 108. | `figuretype/crime.c:256-257`, `core/random.c:47`, `core/random.c:61-64` |
| Effect of a successful roll | Candidate house happiness +5 | `figuretype/crime.c:258` |
| Lowest happiness <= 15 and people below 25 happiness >= 5% of population | Riot: `n = clamp(unhappy_pop / 100, 1, 20)` rioters, `n` looters, `n` robbers. All houses get happiness >= 30. | `figuretype/crime.c:259-266` |
| Lowest happiness <= 15, unhappy share < 5% | 3 looters and 3 robbers | `figuretype/crime.c:267-270` |
| Lowest happiness 16-29 | Looters: 2 when < 20, else 1 | `figuretype/crime.c:271-272` |
| Lowest happiness 30-44 | 1 robber | `figuretype/crime.c:273-274` |
| Lowest happiness 45-49 | 1 protester | `figuretype/crime.c:275-276` |
| Rioter cap | No new rioters when current rioters > population / 500 | `figuretype/crime.c:135-137` |
| Road needed | A road within 4 tiles (2 tiles for a protester) | `figuretype/crime.c:139`, `figuretype/crime.c:166`, `figuretype/crime.c:189`, `figuretype/crime.c:210` |
| Robber minimum treasury | Treasury >= 400 | `figuretype/crime.c:184-186` |
| Money stolen | `treasury / 40`. If > 400: `400 - random_byte() / 2`. Nothing when < 10. | `figuretype/crime.c:105-120` |
| Looter range | 120 tiles to a storage building | `figuretype/crime.c:34`, `figuretype/crime.c:55` |
| Looter in a granary | Removes up to 100 of one food type. A granary stores loads (max 32), so this empties that food type in that granary. | `figuretype/crime.c:93-95`, `building/granary.c:166-181` |
| Looter in a warehouse | Removes 1 load | `figuretype/crime.c:96-98` |

### 3.6.2 Strikes

| Rule | Value / formula | Cadence | Source |
|---|---|---|---|
| Strike start condition | Sentiment < 55 | Monthly | `building/industry.c:607-611`, `game/tick.c:99` |
| Strike chance | `(60 - sentiment)^2 / 36` percent. Strike when `rand() % 100 <= chance`. | Monthly | `building/industry.c:612-616` |
| Number of buildings | `clamp(population / 2000, 1, 12)` | Monthly | `building/industry.c:617` |
| Buildings that can strike | Any production building for a resource (farms, raw material producers, workshops) that is in use and not already on strike | Monthly | `building/industry.c:619-630` |
| Strike duration | 48 days | - | `building/industry.c:93`, `building/industry.c:116` |
| Daily countdown | -1 each day. Extra -3 when sentiment > 50. Strike ends at once when sentiment > 65. | Daily (tick 20) | `building/industry.c:251-262` |
| Effect | A striking building makes no progress | Twice daily | `building/industry.c:266-269` |
| Strike count kept | When a strike ends early by building loss, the daily check starts new strikes on non-food industries to keep `num_striking_industries` | Daily | `building/industry.c:122-136`, `building/industry.c:314-318` |
| Striker figures | Only for marble quarry to pottery workshop types. Other striking buildings show no protester. | Daily (tick 45) | `figuretype/crime.c:225-231` |

## 3.7 Labour

### 3.7.1 Patricians and plebeians

| Rule | Value | Source |
|---|---|---|
| Pleb houses | Small tent to grand insula | `building/house_population.c:177` |
| Patrician houses | Small villa to luxury palace | `building/house_population.c:184` |
| Who works | Only plebs. Patrician population never adds workers. | `city/labor.c:217-231` |
| Pleb share | `percentage_plebs = 100 * plebs / (plebs + patricians)` | `city/labor.c:220` |
| Tax per house per month | `house_pop * difficulty_money(tax_multiplier)`, summed per class, then `sum / 2 * tax_rate / 100` | `city/finance.c:270-332` |
| Tax class split | Patrician when level >= small villa | `city/finance.c:290` |
| Wages and unemployment sentiment | Pleb houses only | `city/sentiment.c:318-321` |
| Emigration | Only small tent to medium insula | `building/house_population.c:148` |
| Patrician devolution fix (`CONFIG_GP_CH_PATRICIAN_DEVOLUTION_FIX`, default on) | A large villa or grand villa that devolves is shrunk instead of the default devolve path | `core/config.c:185`, `building/house_evolution.c:435-439`, `building/house_evolution.c:497-501` |

### 3.7.2 Workers available

Calculated daily at tick 23 (`building/house_population.c:173-199`).

| Config path | Formula | Source |
|---|---|---|
| Default | `working_age = 60% of people aged 20-49` (20-59 with retire at 60). `workers_available = working_age * percentage_plebs / 100`. | `city/labor.c:226-230` |
| `CONFIG_GP_CH_FIXED_WORKERS` | `workers_available = plebs * (45 + venus_bonus) / 100` (`PLEB_PERCENTAGE` = 45) | `city/labor.c:17`, `city/labor.c:222-225` |
| Venus employment bonus | `months_left / 12 + 1` while the Venus blessing lasts (35 months): 3, then 2, then 1 | `city/gods.c:483-490`, `city/gods.h:6` |
| Percent in workforce (display) | `100 * workers_available / population` | `city/population.c:239-246` |

With the default immigrant age mix, 75% of immigrants are aged 20-49 (section 3.2.1). The default path then gives about 60% x 75% = 45% of pleb immigrants as workers. Births and aging change this share over time.

### 3.7.3 Labour categories

Building to category mapping (`city/labor.c:33-130`):

| Category | Buildings |
|---|---|
| Industry and commerce | Olive farm, vines farm, market, warehouse, dock, marble quarry, iron mine, timber yard, clay pit, all workshops, gold mine, city mint, sand pit, stone quarry, concrete maker, brickworks, depot |
| Food production | Granary, shipyard, wheat, vegetable, fruit and pig farm, wharf |
| Engineering | Engineers post, workcamp, architect guild, highway station |
| Water | Fountain |
| Prefectures | Prefecture |
| Military | All forts, gatehouse, tower, military academy, barracks, mess hall, watchtower, armoury |
| Entertainment | Amphitheater, theater, hippodrome, colosseum, gladiator school, lion house, actor colony, chariot maker, tavern, arena |
| Health and education | Doctor, hospital, bathhouse, barber, school, academy, library, mission post, latrines |
| Governance and religion | All temples, grand temples, pantheon, senate, forum, oracle, lighthouse, caravanserai |

Workers per building (`model->laborers`, `building/properties.c`). Forts, gatehouse, oracle and walls have 0.

| Building | Workers | Line |
|---|---|---|
| Amphitheater | 12 | 644 |
| Theater | 8 | 652 |
| Hippodrome | 150 | 661 |
| Colosseum | 100 | 670 |
| Gladiator school, lion house | 8 | 678, 686 |
| Actor colony | 5 | 694 |
| Chariot maker | 10 | 702 |
| Doctor | 5 | 822 |
| Hospital | 30 | 830 |
| Bathhouse | 10 | 838 |
| Barber | 2 | 846 |
| School | 10 | 858 |
| Academy | 30 | 866 |
| Library | 20 | 875 |
| Prefecture | 6 | 884 |
| Tower | 6 | 915 |
| Small temple | 2 | 926-970 |
| Large temple | 5 | 983-1035 |
| Market | 5 | 1043 |
| Granary | 6 | 1051 |
| Warehouse | 6 | 1060 |
| Shipyard | 10 | 1073 |
| Dock | 12 | 1081 |
| Wharf | 6 | 1089 |
| Mission post | 20 | 1122 |
| Engineers post | 5 | 1131 |
| Senate | 30 | 1153 |
| Forum | 6 | 1161 |
| Fountain | 4 (half, minimum 1, with a working Neptune grand temple) | 1198, `building/building.c:1038-1050` |
| Military academy | 20 | 1226 |
| Barracks | 10 | 1235 |
| Each farm | 10 | 1269-1309 |
| Marble quarry, iron mine, timber yard, clay pit | 10 | 1317-1341 |
| Each original workshop | 10 | 1349-1381 |
| Workcamp | 20 | 1398 |
| Grand temple, pantheon | 50 | 1410-1458, 1750 |
| Architect guild | 12 | 1760 |
| Mess hall | 10 | 1770 |
| Lighthouse | 20 | 1780 |
| Tavern | 8 | 1797 |
| Arena | 25 | 1815 |
| Watchtower | 8 | 1965 |
| Caravanserai | 20 | 1975 |
| Gold mine | 30 | 2061 |
| Stone quarry, sand pit, brickworks, concrete maker | 10 | 2069-2095 |
| City mint | 40 | 2105 |
| Depot | 15 | 2114 |
| Armoury | 6 | 2217 |
| Latrines | 2 | 2226 |
| Highway station | 12 | 2276 |

### 3.7.4 Which buildings need workers

| Rule | Value | Source |
|---|---|---|
| Engineering and water | Always counted, also without labour access | `city/labor.c:264-267` |
| Latrines | Always counted | `city/labor.c:251-253` |
| Other categories | Counted only when `houses_covered > 0` | `city/labor.c:269-271` |
| Hippodrome | Only the main part counts | `city/labor.c:255-258` |
| Mothballed industry | A food or industry building whose output resource is mothballed does not count | `city/labor.c:233-243`, `city/labor.c:259-262` |

### 3.7.5 Labour access (`houses_covered`)

| Rule | Value / formula | Cadence | Source |
|---|---|---|---|
| Labour seeker spawn | When `houses_covered <= min_houses`. `min_houses` is 50 or 100, by building type. Only 1 seeker per building. | Daily (tick 31) | `building/figure.c:64-104` |
| Labour seeker roam | Roads only, 384 tiles | Per figure | `figuretype/service.c:458-470` |
| Labour seeker coverage | Each tile step adds the number of occupied houses within 2 tiles | Per tile | `figure/service.c:21-40`, `figure/service.c:526-527` |
| Cap | `houses_covered` <= 300 | Per tile | `figure/service.c:716-720` |
| Decay | -1 per day | Daily (tick 12) | `building/house_service.c:64-75` |
| No population | No labour seeker when population <= 0 | - | `building/figure.c:66-68` |
| `CONFIG_GP_CH_GLOBAL_LABOUR` | No seeker figure. `houses_covered = 2 * min_houses` (or 100) when the building has `distance_from_entry > 0`, else 0. Houses spawn cosmetic plebeian figures. | Daily | `building/figure.c:69-77`, `building/figure.c:94-99`, `building/figure.c:2167-2172` |

### 3.7.6 Allocation of workers

`city_labor_update` runs daily at tick 25 (`city/labor.c:564-569`).

| Step | Rule | Source |
|---|---|---|
| 1. Need per category | Sum of `building_get_laborers` for buildings that need workers | `city/labor.c:275-299` |
| 2. Enough workers | When total need <= workers available, every category receives its full need. `workers_employed = need`. | `city/labor.c:309-313` |
| 3. User priorities | Categories with player priority 1 to 9 receive their full need in priority order until workers run out | `city/labor.c:317-330` |
| 4. Default round-robin | Categories without a priority receive workers in rounds. Per round: engineering 3, water 1, prefectures 3, military 2, food 4, industry 2, entertainment 1, health and education 1, governance and religion 1. | `city/labor.c:135-145`, `city/labor.c:331-359` |
| 5. Shortage result | `workers_employed = workers_available`. `workers_needed` = unfilled need. | `city/labor.c:361-365` |
| Unemployment | `unemployed = available - employed`. `unemployment% = 100 * unemployed / available`. | `city/labor.c:367-369` |
| Senate display | Falls at once. Rises by at most 5 points per day. Max 100. | `city/labor.c:376-386` |
| Building weight | `percentage_houses_covered = 100 * 100 * houses_covered / category_total_houses_covered` (in 1/100 of a percent) | `city/labor.c:396-421` |
| Per building, full category | Building receives its full `laborers` | `city/labor.c:505-507` |
| Per building, short category, pass 1 | `num_workers = category_allocated * weight / 100 / 100`, max `laborers` | `city/labor.c:496-504` |
| Per building, pass 2 | Remaining workers fill buildings to full `laborers`, in building type order. Military buildings get no pass 2. | `city/labor.c:510-548` |
| Fountains (water) | A share of fountains equal to the unfilled percentage gets 0 workers. The others share the allocated workers equally. The start fountain rotates each day. | `city/labor.c:423-468` |
| "Workers needed" message | When need changes from 0 to more than 0, after the scenario start year | `city/labor.c:388-393` |

### 3.7.7 How worker percentage scales output

| Building group | Rule | Cadence | Source |
|---|---|---|---|
| Production (farms, raw materials, workshops) | Progress += `num_workers` per pass. Farms under Ceres blessing get double. Concrete maker: x water access / 2. No progress when `houses_covered <= 0`, `num_workers <= 0` or on strike. | 2 passes per day (ticks 20 and 46) | `building/industry.c:240-310` |
| Production cycle length | `max_progress = 100 * 32 * laborers / production_per_month`. A fully staffed building completes `production_per_month / 100` cycles per month. | - | `building/industry.c:73-77`, `game/resource.c:332-339` |
| Wheat in northern climate | Production per month / 2 | - | `game/resource.c:335-337` |
| Service walker delay (default) | Workers >= 100%: 3 days. >= 75%: 7. >= 50%: 15. >= 25%: 29. >= 1%: 44. 0%: no walker. A walker spawns when the counter exceeds the delay. | Daily (tick 31) | `building/figure.c:125-141` |
| Granary | < 50% workers: not operating, no tasks, food not counted in city stock. < 100%: counted as understaffed. | Daily | `city/resource.c:454-470`, `building/granary.c:373-377` |

### 3.7.8 Wages

| Rule | Value / formula | Cadence | Source |
|---|---|---|---|
| Initial city wage and Rome wage | 30 and 30 | New game | `city/data.c:20-21` |
| City wage range | 0 to 100 | Player change | `city/labor.c:177-181` |
| Wage cost | `wages * workers_employed / 10 / 12` | Monthly | `city/finance.c:345-351` |
| Rome raises wages (random event) | Event value 1 in a 128-entry table, 3 entries: 3/128 chance per month | Monthly | `scenario/random_event.c:31-40`, `scenario/random_event.c:177-179` |
| Rome lowers wages (random event) | Event value 2, 3 entries: 3/128 chance per month | Monthly | `scenario/random_event.c:31-40`, `scenario/random_event.c:180-182` |
| Event conditions | Scenario flag `raise_wages` or `lower_wages` on, and more than 12 months since the last change | Monthly | `scenario/random_event.c:29`, `scenario/random_event.c:42-62` |
| Step size | `1 + (random_byte_alt() & 3)` = 1 to 4 | Per event | `city/labor.c:188-210` |
| Rome wage limits | Scenario `min_wages` and `max_wages`. Defaults 5 and 45 when 0. | - | `city/labor.c:190-207`, `scenario/scenario.c:449-460` |
| Scenario event: change Rome wages | Set or add a value. Minimum 1. Resets the 12-month cooldown. | Per event | `scenario/event/action_types.c:298-339` |
| Sentiment effect | See section 3.5.2 (+2 per point above Rome, -3 per point below) | 2 times per month | `city/sentiment.c:180-184` |

### 3.7.9 Beggars and cosmetic plebeians

| Rule | Value / formula | Source |
|---|---|---|
| Beggar spawn condition | Unemployment > 6%, pleb houses only | `building/figure.c:43`, `building/figure.c:2174-2178` |
| Houses per beggar | Unemployment < 9: `40 - u`. < 12: `30 - u`. < 15: `25 - u`. < 18: `24 - u`. < 21: `23 - u`. Else 3. | `building/figure.c:152-170` |
| Beggar check per house | Every 17 days per house | `building/figure.c:173-190` |
| Plebeian spawn (global labour only) | Every 17 days per house: chance `25 + (u - 5)` %, max 50, divided by 4 for unmerged houses (min 1) | `building/figure.c:192-224` |

## 3.8 Food supply at city level

### 3.8.1 Granaries

| Rule | Value | Source |
|---|---|---|
| Capacity | 32 loads (`FULL_GRANARY`, `BUILDING_STORAGE_QUANTITY_MAX`) | `building/granary.h:8`, `building/storage.h:29`, `building/building.c:260` |
| Accepted goods | Food resources only | `building/granary.c:120-124` |
| Getting deliveryman load | Max 8 loads. 16 with `CONFIG_GP_CH_GRANARIES_GET_DOUBLE`. | `building/granary.c:350-358` |
| Getting while stockpiled | Off by default. `CONFIG_GP_CH_ENABLE_GETTING_WHILE_STOCKPILED` allows it. | `building/granary.c:394-396`, `core/config.c:196` |
| Plague | A granary with plague gives no food and accepts no food | `building/granary.c:35-45`, `building/granary.c:166-169`, `building/granary.c:309-313` |

### 3.8.2 City food stock

Calculated daily at tick 17 and again at the monthly consumption (`city/resource.c:435-498`, `city/resource.c:682-684`).

| Rule | Value / formula | Source |
|---|---|---|
| City food stock | Sum of food in operating granaries (road access and >= 50% workers), in units (loads x 100) | `city/resource.c:447-484` |
| Food needed per month (advisor) | 50% of population, in units | `city/resource.c:485-486` |
| Months of supply | `stock / food_needed` | `city/resource.c:487-493` |
| Rome supplies wheat | 1 food type, 12 months of supply. Each market and mess hall in use is set to 200 wheat units each day. | `city/resource.c:494-513` |

### 3.8.3 House food consumption

Monthly (`game/tick.c:88`, `city/resource.c:516-571`).

| Rule | Value / formula | Source |
|---|---|---|
| Amount per food type | `house_pop * 50 / 100`. With Ceres grand temple module 1 and Ceres temple access: `house_pop * 40 / 100`. | `city/resource.c:525-531` |
| Split | The amount is divided by the number of food types that the house holds | `city/resource.c:532-540` |
| Consumption | Each held type loses the amount. When a type has less, it drops to 0 and still counts as eaten. | `city/resource.c:549-562` |
| Houses that need 0 food types (tents) | Eat nothing | `city/resource.c:548` |
| Rome supplies wheat | House wheat is set to the amount; 1 food type counts as eaten | `city/resource.c:543-547` |
| Food shortage effect on sentiment | Only through the food variety bonus. No direct penalty. | `city/sentiment.c:257-265` |

### 3.8.4 Markets

| Rule | Value | Source |
|---|---|---|
| Market supplier stock target | 800 units per food type | `figuretype/supplier.h:6`, `figuretype/supplier.c:64-72` |
| Fetch priority | 1. A good the market does not have. 2. The smallest stock below 50 units. 3. Food below 600 units. | `building/market.c:68-92`, `building/distribution.h:14`, `building/market.c:8` |
| Market range | 40 tiles with `CONFIG_GP_CH_MARKET_RANGE` (default on). Else the full map width. | `building/market.h:6`, `building/market.c:97-99`, `core/config.c:205` |
| Rome supplies wheat | Markets do not fetch food | `building/market.c:53-54`, `figuretype/supplier.c:60-62` |

### 3.8.5 Mess hall and soldiers

| Rule | Value / formula | Cadence | Source |
|---|---|---|---|
| Food per soldier | `FOOD_PER_SOLDIER_MONTHLY` = 4 units, plus difficulty: very easy -3, easy -3, normal -2, hard 0, very hard +1 | Monthly | `city/resource.h:7`, `game/difficulty.c:19-23`, `game/difficulty.c:56-59` |
| Food required | Soldiers in city x adjusted food per soldier | Monthly | `city/resource.c:584-585` |
| Advisor "months stored" | Uses the raw value 4 without the difficulty change | On display | `city/military.c:174-182` |
| Consumption split | Each food type pays in proportion to its share of the stock | Monthly | `city/resource.c:602-611` |
| Missing food % | `100 - 100 * stock / required` when stock < required, else 0 | Monthly | `city/resource.c:613-622` |
| Soldiers but no mess hall | Missing food = 100% | Monthly | `city/resource.c:693-697` |
| Food stress | `(missing% + previous_stress) / 2`, max 100 | Monthly | `city/resource.c:704-712` |
| Mess hall stock target | 1600 units. x1.5 with 10 legions. x2 above 10 legions (cheat). | - | `figuretype/supplier.h:7`, `figuretype/supplier.c:26-37` |
| Mess hall fetch range | 40 tiles | - | `building/mess_hall.c:6`, `building/mess_hall.c:13-14` |
| Legion max morale modifier | `+5 * (food_types - 1)` (0 to 10), +5 when stress < 3, `-stress / 3` when stress > 20. Total bounded -30 to +15. | Monthly | `figure/formation.c:554-579` |
| Barracks recruitment delay | + `(stress - 20)` days when stress > 20 | Daily | `building/figure.c:1211-1214`, `building/figure.c:1697-1699` |

### 3.8.6 Caravanserai

| Rule | Value / formula | Cadence | Source |
|---|---|---|---|
| Food required | 30 units per open land trade route (`FOOD_PER_LAND_ROUTE_MONTHLY`) | Monthly | `city/resource.h:8`, `building/caravanserai.c:24-31` |
| Land trade policy 3 | +20% food required | Monthly | `city/trade_policy.h:10`, `city/resource.c:636-640` |
| Condition | Only when the caravanserai is working | Monthly | `city/resource.c:631-633` |
| Stock target | 1600 units | - | `figuretype/supplier.h:8` |

## 3.9 Config options that change these rules

`core/config.c:160-230` lists the defaults. An option that is not in that list has default 0 (off).

| Option | Effect | Default | Source |
|---|---|---|---|
| `CONFIG_GP_CH_RETIRE_AT_60` | Ages 50-59 count as working age, not as retired | Off | `city/population.c:223-236` |
| `CONFIG_GP_CH_FIXED_WORKERS` | Workers = 45% (+ Venus bonus) of pleb population. Ignores age. | Off | `city/labor.c:222-225` |
| `CONFIG_GP_CH_GLOBAL_LABOUR` | No labour seekers. Each building connected to the entry point has labour access. | Off | `building/figure.c:69-77`, `building/figure.c:94-99` |
| `CONFIG_GP_CH_HOUSING_DO_NOT_SPAWN_PLEBIANS` | Stops cosmetic plebeians (global labour only) | Off | `building/figure.c:2169-2170` |
| `CONFIG_GP_CH_GRANARIES_GET_DOUBLE` | Getting load 16 instead of 8 | Off | `building/granary.c:350-358` |
| `CONFIG_GP_CH_ENABLE_GETTING_WHILE_STOCKPILED` | Granaries get stockpiled food | Off | `core/config.c:196`, `building/granary.c:394` |
| `CONFIG_GP_CH_MARKET_RANGE` | Market fetch range 40 tiles | On | `core/config.c:205`, `building/market.c:97-99` |
| `CONFIG_GP_CH_PATRICIAN_DEVOLUTION_FIX` | Devolving large and grand villas shrink | On | `core/config.c:185`, `building/house_evolution.c:435`, `building/house_evolution.c:497` |
| `CONFIG_GP_FIX_IMMIGRATION_BUG` | No effect. No game code reads this option. | - | `core/config.h:14`, `core/config.c:24` |
| `CONFIG_GP_FIX_100_YEAR_GHOSTS` | No effect. No game code reads this option. | - | `core/config.h:15`, `core/config.c:25` |

## 3.10 Unverified items

- Scenario model files can override house and building values (`scenario/model_xml.c`). This chapter did not read the override rules.
- The `CONFIG_GP_CH_GLOBAL_LABOUR` coverage value for each building type depends on the `min_houses` argument at each `spawn_labor_seeker` call (`building/figure.c:282-1194`). This chapter did not list the value per building type.
- The age shares in section 3.2.1 assume a uniform random pool.
