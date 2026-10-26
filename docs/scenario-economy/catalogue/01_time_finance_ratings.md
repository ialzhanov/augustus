# Chapter 1: Time, Finance, Ratings, Emperor and Empire

Source: Augustus upstream commit `dae1899`. All paths are relative to `src/`. "dn" means denarii.
Integer division truncates toward zero in every formula. `calc_adjust_with_percentage(v, p)` is `p * v / 100` (`core/calc.c:22-25`). `calc_percentage(v, t)` is `100 * v / t`, or 0 when `t` is 0 (`core/calc.c:27-35`).

## 1. Game time

| Rule | Value / formula | Cadence | Source |
|---|---|---|---|
| Ticks per day | 50 (tick 0 to 49) | - | `game/time.h:13` |
| Days per month | 16 (day 0 to 15) | - | `game/time.h:14` |
| Months per year | 12 (month 0 to 11, 0 = January) | - | `game/time.h:15` |
| Ticks per month | 800 | - | derived |
| Ticks per year | 9600 | - | derived |
| Tick rollover | tick >= 50: tick = 0, a new day starts | every tick | `game/time.c:42-49` |
| Day rollover | day >= 16: day = 0, a new month starts. `total_days` increases by 1 every day | every day | `game/time.c:51-59` |
| Month rollover | month >= 12: month = 0, a new year starts | every month | `game/time.c:61-68` |
| Total months | `total_days / 16` | on request | `game/time.c:75-78` |
| Total years | `total_months / 12` | on request | `game/time.c:80-83` |
| Start of a game | tick, day, month, total_days = 0; year = scenario start year | once | `game/time.c:13-20` |

### 1.1 Per-tick schedule (`advance_tick`, one call per tick)

Each subsystem in this table runs once per day, on the given tick of the day.

| Tick | Subsystem | Source |
|---|---|---|
| 0 | no action | `game/tick.c:152-153` |
| 1 | `city_gods_calculate_moods(1)` (god moods) | `game/tick.c:156` |
| 2 | `sound_music_update(0)` | `game/tick.c:157` |
| 3 | `widget_minimap_invalidate()` | `game/tick.c:158` |
| 4 | `city_emperor_update()`: debt state and Caesar invasion (see sections 4.4 and 4.5) | `game/tick.c:159` |
| 5 | `formation_update_all(0)` (non-legion formations) | `game/tick.c:160` |
| 6 | `map_natives_check_land(1)` | `game/tick.c:161` |
| 7 | `map_road_network_update()` | `game/tick.c:162` |
| 8 | `building_granaries_calculate_stocks()` | `game/tick.c:163` |
| 9 | `city_buildings_update_plague()` | `game/tick.c:164` |
| 10, 11 | no action | `game/tick.c:152-153` |
| 12 | `house_service_decay_houses_covered()` | `game/tick.c:165` |
| 13, 14, 15 | no action | `game/tick.c:152-153` |
| 16 | `city_resource_calculate_warehouse_stocks()` | `game/tick.c:166` |
| 17 | `city_resource_calculate_food_stocks_and_supply_wheat()` | `game/tick.c:167` |
| 18 | no action | `game/tick.c:152-153` |
| 19 | `building_dock_update_open_water_access()` | `game/tick.c:168` |
| 20 | `building_industry_update_production(1)` (production step with the "new day" flag; includes the city mint) | `game/tick.c:169` |
| 21 | `building_maintenance_check_rome_access()` | `game/tick.c:170` |
| 22 | `house_population_update_room()` | `game/tick.c:171` |
| 23 | `house_population_update_migration()` | `game/tick.c:172` |
| 24 | `house_population_evict_overcrowded()` | `game/tick.c:173` |
| 25 | `city_labor_update()` | `game/tick.c:174` |
| 26 | no action | `game/tick.c:152-153` |
| 27 | `map_water_supply_update_reservoir_fountain()` | `game/tick.c:175` |
| 28 | `map_water_supply_update_buildings()` | `game/tick.c:176` |
| 29 | `formation_update_all(1)` (legions) | `game/tick.c:177` |
| 30 | `widget_minimap_invalidate()` | `game/tick.c:178` |
| 31 | `building_figure_generate()` (walker spawn for all buildings, includes tax collectors) | `game/tick.c:179` |
| 32 | `city_trade_update()` | `game/tick.c:180` |
| 33 | `building_entertainment_run_shows()` and `city_culture_update_coverage()` (coverage percentages for the culture rating) | `game/tick.c:181` |
| 34 | `building_government_distribute_treasury()` (display only, see 2.4) | `game/tick.c:182` |
| 35 | `house_service_decay_culture()` | `game/tick.c:183` |
| 36 | `house_service_calculate_culture_aggregates()` | `game/tick.c:184` |
| 37 | `map_desirability_update()` | `game/tick.c:185` |
| 38 | `building_update_desirability()` | `game/tick.c:186` |
| 39 | `building_house_process_evolve_and_consume_goods()` | `game/tick.c:187` |
| 40 | `building_update_state()` | `game/tick.c:188` |
| 41 | no action | `game/tick.c:152-153` |
| 42 | `city_finance_spawn_tourist()` (only while games are active) | `game/tick.c:189` |
| 43 | `building_maintenance_update_burning_ruins()` | `game/tick.c:190` |
| 44 | `building_maintenance_check_fire_collapse()` | `game/tick.c:191` |
| 45 | `figure_generate_criminals()` | `game/tick.c:192` |
| 46 | `building_industry_update_production(0)` (second production step of the day; includes the city mint) | `game/tick.c:193` |
| 47 | `city_games_decrement_duration()` (games duration in days) | `game/tick.c:194` |
| 48 | `house_service_decay_tax_collector()` (tax coverage decay) | `game/tick.c:195` |
| 49 | `city_culture_calculate()` (house averages, show counts, festival costs) | `game/tick.c:196` |

### 1.2 Every tick (outside the tick switch)

| Subsystem | Cadence | Source |
|---|---|---|
| `random_generate_next()` | every tick | `game/tick.c:210` |
| `game_undo_reduce_time_available()` | every tick | `game/tick.c:211` |
| `figure_action_handle()` (all walkers move) | every tick | `game/tick.c:213` |
| `scenario_earthquake_process()` | every tick | `game/tick.c:214` |
| `scenario_gladiator_revolt_process()` | every tick | `game/tick.c:215` |
| `scenario_emperor_change_process()` | every tick | `game/tick.c:216` |
| `city_victory_check()` (win and loss) | every tick | `game/tick.c:217` |
| In the map editor, only `random_generate_next()` and `figure_action_handle()` run | every tick | `game/tick.c:205-209` |

### 1.3 Daily schedule (`advance_day`, after tick 49)

| Subsystem | Cadence | Source |
|---|---|---|
| Month rollover check; if a new month starts, `advance_month()` runs first | daily | `game/tick.c:131-133` |
| `city_sentiment_update()` | days 0 and 8 (2 times per month) | `game/tick.c:135-137` |
| `building_lighthouse_consume_timber()` | days 0 and 7 (2 times per month) | `game/tick.c:138-140` |
| `tutorial_on_day_tick()` | daily | `game/tick.c:141` |
| Yearly autosave, only with `CONFIG_GP_CH_YEARLY_AUTOSAVE` | month 11, day 15 | `game/tick.c:142-145` |
| `scenario_events_progress_paused(1)` and `scenario_events_process_all()` (scenario events, conditions and actions) | daily | `game/tick.c:146-147` |

### 1.4 Monthly schedule (`advance_month`, in this order)

| Order | Subsystem | Source |
|---|---|---|
| 1 | `city_migration_reset_newcomers()` | `game/tick.c:84` |
| 2 | `city_health_update()` | `game/tick.c:85` |
| 3 | `scenario_random_event_process()` (see 2.11) | `game/tick.c:86` |
| 4 | `city_finance_handle_month_change()`: taxes, tourism, wages, interest, salary, levies, highway station (see 2.1) | `game/tick.c:87` |
| 5 | `city_resource_consume_food()` | `game/tick.c:88` |
| 6 | `scenario_distant_battle_process()` | `game/tick.c:89` |
| 7 | `scenario_invasion_process()` | `game/tick.c:90` |
| 8 | `scenario_request_process()` (Caesar requests, see 6) | `game/tick.c:91` |
| 9 | `scenario_demand_change_process()` | `game/tick.c:92` |
| 10 | `scenario_price_change_process()` | `game/tick.c:93` |
| 11 | `city_victory_update_months_to_govern()` | `game/tick.c:94` |
| 12 | `formation_update_monthly_morale_at_rest()` | `game/tick.c:95` |
| 13 | `city_message_decrease_delays()` | `game/tick.c:96` |
| 14 | `city_sentiment_decrement_blessing_boost()` | `game/tick.c:97` |
| 15 | `building_industry_advance_stats()` | `game/tick.c:98` |
| 16 | `building_industry_start_strikes()` | `game/tick.c:99` |
| 17 | `building_trim()` | `game/tick.c:100` |
| 18 | connectable buildings, roads, highways, water, marsh, beach tiles, land routing, message sort | `game/tick.c:102-109` |
| 19 | `game_time_advance_month()`. If the year ends: `advance_year()`. Else: `city_ratings_update(0, 1)` (monthly ratings) | `game/tick.c:111-115` |
| 20 | `city_population_record_monthly()` | `game/tick.c:117` |
| 21 | `city_festival_update()` | `game/tick.c:118` |
| 22 | `city_games_decrement_month_counts()` | `game/tick.c:119` |
| 23 | `city_gods_update_blessings()` | `game/tick.c:120` |
| 24 | `tutorial_on_month_tick()`, monthly autosave (if the setting is on), `city_weather_update()` | `game/tick.c:121-126` |

Order effects:
- The month finance pass (order 4) runs before the month counter advances (order 19). During the finance pass, `game_time_month()` is still the month that ends. Example: the December pass runs with month = 11. The tourism yearly reset at `month == 0` (`city/finance.c:411`) therefore runs at the end of January. (The advisor estimates in `city/finance.c:233-268` run only when an advisor window opens, `window/advisors.c:148-149`.)
- Ratings get a monthly update in 11 months and a yearly update in the 12th month. No month gets both (`game/tick.c:111-115`).

### 1.5 Yearly schedule (`advance_year`, in this order)

| Order | Subsystem | Source |
|---|---|---|
| 1 | `game_undo_disable()` | `game/tick.c:69` |
| 2 | `game_time_advance_year()` (the year number increases first) | `game/tick.c:70` |
| 3 | `city_message_clear_old_messages()` | `game/tick.c:72` |
| 4 | `scenario_empire_process_expansion()` (empire expansion, see 7) | `game/tick.c:74` |
| 5 | `city_population_request_yearly_update()` | `game/tick.c:75` |
| 6 | `city_finance_handle_year_change()`: archive, reset taxes, ledgers, copy to last year, pay tribute (see 2.7) | `game/tick.c:76` |
| 7 | `empire_city_reset_yearly_trade_amounts()` (trade route quotas reset) | `game/tick.c:77` |
| 8 | `building_maintenance_update_fire_direction()` | `game/tick.c:78` |
| 9 | `city_ratings_update(1, 0)` (yearly ratings) | `game/tick.c:79` |

Because the year number increases before the tribute and the ratings run, every "year == X" check in the yearly pass (milestones, victory) uses the new year.

## 2. Finance

### 2.1 Monthly finance pass (`city_finance_handle_month_change`)

| Order | Step | Formula | Source |
|---|---|---|---|
| 1 | Collect taxes | see 2.2 | `city/finance.c:270-343`, `city/finance.c:429` |
| 2 | Activate tourism venues | see 2.9 | `city/finance.c:402-425`, `city/finance.c:430` |
| 3 | Pay wages | `wages * workers_employed / 10 / 12` | `city/finance.c:345-351` |
| 4 | Pay interest | if treasury < 0: `(-treasury * 10 / 100) / 12` | `city/finance.c:353-360` |
| 5 | Pay salary | if treasury > -5000: `salary_amount` moves from the treasury to personal savings | `city/finance.c:362-369` |
| 6 | Pay building levies | see 2.5 | `city/finance.c:371-400` |
| 7 | Highway station consumes stone and sand | not a money flow | `city/finance.c:435`, `building/highway_station.c:77-97` |

### 2.2 Tax income

| Rule | Value / formula | Cadence | Source |
|---|---|---|---|
| Tax rate range | 0 to 25 % | on change | `city/finance.c:123-126` |
| Start tax rate | 7 % | game start | `city/data.c:22` |
| Taxed house | a house with `house_tax_coverage > 0` | monthly check | `city/finance.c:296` |
| House tax base | `house_population * difficulty_adjust_money(tax_multiplier)` | monthly | `city/finance.c:291-295` |
| Plebeian / patrician split | patrician if house level >= small villa | monthly | `city/finance.c:290` |
| Monthly tax collected (each class) | `tax_rate * (sum_of_house_tax_base / 2) / 100` | monthly | `city/finance.c:317-322` |
| Treasury change | plebeian part + patrician part | monthly | `city/finance.c:323`, `city/finance.c:334` |
| Uncovered houses | tax base goes to "uncollected" statistics only; no money | monthly | `city/finance.c:305-313`, `city/finance.c:327-332` |
| Percentage of taxed people | `100 * taxed / total` (plebs, patricians, all) | monthly | `city/finance.c:336-342` |
| Estimated tax income (advisor) | `taxes_this_year + (12 - month) * monthly_estimate` | on request | `city/finance.c:240-268` |
| Estimated wages (advisor) | `(12 - month) * monthly_wages + wages_so_far` | on request | `city/finance.c:233-238` |
| Yearly reset | taxes this year move to last year; per-house tax income resets to 0 | yearly | `city/finance.c:438-455` |

Exact formula, for each class separately: monthly tax = `rate * (sum / 2) / 100`, where `sum = Σ pop × m_adj` over covered houses. The division by 2 truncates first. Approximation: `rate × sum / 200`.

House tax multiplier (`tax_multiplier`) and prosperity value per house level. The scenario can change these values with a model XML file or with the "change house model data" event action (`scenario/model_xml.c:146`, `scenario/event/action_types.c:853`).

| House level | Prosperity value | Tax multiplier | Source (prosperity / tax) |
|---|---|---|---|
| Small tent | 5 | 1 | `building/properties.c:159` / `:161` |
| Large tent | 10 | 1 | `:184` / `:186` |
| Small shack | 15 | 1 | `:209` / `:211` |
| Large shack | 20 | 1 | `:234` / `:236` |
| Small hovel | 25 | 2 | `:259` / `:261` |
| Large hovel | 30 | 2 | `:284` / `:286` |
| Small casa | 35 | 2 | `:309` / `:311` |
| Large casa | 45 | 2 | `:334` / `:336` |
| Small insula | 50 | 3 | `:359` / `:361` |
| Medium insula | 58 | 3 | `:384` / `:386` |
| Large insula | 65 | 3 | `:409` / `:411` |
| Grand insula | 80 | 4 | `:434` / `:436` |
| Small villa | 150 | 9 | `:459` / `:461` |
| Medium villa | 180 | 10 | `:484` / `:486` |
| Large villa | 400 | 11 | `:509` / `:511` |
| Grand villa | 600 | 11 | `:534` / `:536` |
| Small palace | 700 | 12 | `:559` / `:561` |
| Medium palace | 900 | 12 | `:584` / `:586` |
| Large palace | 1500 | 15 | `:609` / `:611` |
| Luxury palace | 1750 | 16 | `:634` / `:636` |

Effective tax multiplier after `difficulty_adjust_money` (money % = 300 / 200 / 150 / 100 / 75, `game/difficulty.c:19-23`, `game/difficulty.c:41-44`):

| Base multiplier | Very easy | Easy | Normal | Hard | Very hard |
|---|---|---|---|---|---|
| 1 | 3 | 2 | 1 | 1 | **0** |
| 2 | 6 | 4 | 3 | 2 | 1 |
| 3 | 9 | 6 | 4 | 3 | 2 |
| 4 | 12 | 8 | 6 | 4 | 3 |
| 9 | 27 | 18 | 13 | 9 | 6 |
| 10 | 30 | 20 | 15 | 10 | 7 |
| 11 | 33 | 22 | 16 | 11 | 8 |
| 12 | 36 | 24 | 18 | 12 | 9 |
| 15 | 45 | 30 | 22 | 15 | 11 |
| 16 | 48 | 32 | 24 | 16 | 12 |

On very hard, tents and shacks pay no tax, because `75 * 1 / 100 = 0`.

Tax rate effect on sentiment (detail is in the sentiment chapter): `diff = base_tax - tax`; if `diff < 0` then `diff * (12 - base_tax)`, else `diff * (base_tax / 2)` (`city/sentiment.c:25`, `city/sentiment.c:194-200`). `base_tax` per difficulty = 10 / 9 / 8 / 7 / 6 (`game/difficulty.c:19-23`).

### 2.3 Tax collectors (forum and senate)

| Rule | Value / formula | Cadence | Source |
|---|---|---|---|
| Spawn buildings | forum and senate spawn a tax collector | tick 31, daily | `building/figure.c:1392-1431` |
| One collector at a time | no new collector while one exists | - | `building/figure.c:1401-1403` |
| Spawn delay by staffing | 100 % workers: 0; >= 75 %: 1; >= 50 %: 3; >= 25 %: 7; >= 1 %: 15; 0 %: no spawn. A collector spawns when the counter exceeds the delay | daily | `building/figure.c:1408-1426` |
| Road access | the building needs road access | - | `building/figure.c:1405` |
| Roam length | 512 steps, then return | per walker | `figuretype/service.c:493`, `figuretype/service.c:535-547` |
| Service area | houses within 2 tiles of the walker get service | per step | `figure/service.c:274-279` |
| Coverage set | a visited house with population > 0 gets `house_tax_coverage = 50` | per visit | `figure/service.c:318-327` |
| Coverage decay | `house_tax_coverage - 1` per day | tick 48, daily | `building/house_service.c:53-62` |
| Coverage duration | 50 days = 3.125 months after the last visit | derived | - |
| No minimum level | a house of any level pays tax when covered | - | `city/finance.c:296` |

### 2.4 Forum and senate treasury display

`building_government_distribute_treasury()` divides the treasury into units: forum = 1 unit, senate = 8 units. It writes the share into `tax_income_or_storage` of each staffed forum and senate. It moves no money (`building/government.c:7-34`). It runs on tick 34 daily.

### 2.5 Building levies (monthly)

| Building | Base levy per month (dn) | Source |
|---|---|---|
| Fort (archers, legionaries, javelin, mounted, auxilia infantry) | 8 | `city/finance.h:10`, `city/finance.c:29-33` |
| Small temple (each god) | 4 | `city/finance.h:9`, `city/finance.c:34-38` |
| Large temple (each god) | 8 | `city/finance.h:18`, `city/finance.c:39-43` |
| Oracle | 4 | `city/finance.c:44` |
| Tower | 2 | `city/finance.h:11`, `city/finance.c:45` |
| Lighthouse | 8 | `city/finance.h:14`, `city/finance.c:46` |
| Grand temple (each god) | 44 | `city/finance.h:12`, `city/finance.c:47-51` |
| Pantheon | 48 | `city/finance.h:13`, `city/finance.c:52` |
| Colosseum | 36 | `city/finance.h:15`, `city/finance.c:53` |
| Hippodrome | 72 | `city/finance.h:16`, `city/finance.c:54` |
| Small mausoleum | 2 | `city/finance.h:19`, `city/finance.c:55` |
| Large mausoleum | 2 (uses the small mausoleum value) | `city/finance.c:56` |
| Nymphaeum | 4 | `city/finance.c:57` |
| Caravanserai | 8 | `city/finance.h:17`, `city/finance.c:58` |
| Highway | 1 per 4 highway tiles: `(highway_tiles / 4) * 1` | `city/finance.h:20`, `city/finance.c:383-392` |

Levy modifiers (`building_get_levy`, `building/building.c:997-1031`):

| Rule | Value / formula | Source |
|---|---|---|
| Unfinished monument | levy 0 | `building/building.c:1003-1005` |
| Building not in use (for example mothballed), or secondary part of a multi-part building | levy 0. A mothballed fort or temple pays no levy | `building/building.c:1006-1011` |
| Working Pantheon | temples, grand temples, oracle, nymphaeum, mausoleums: `(levy / 4) * 3` | `building/building.c:1014-1021` |
| Mars grand temple module 1 (mess hall) | forts: `(levy / 4) * 3` | `building/building.c:1023-1028` |
| Difficulty | `levy * levies% / 100`; levies % = 0 / 0 / 50 / 100 / 100 (very easy to very hard) | `building/building.c:1030`, `game/difficulty.c:19-23`, `game/difficulty.c:51-54` |
| Working highway station | the highway levy is halved | `city/finance.c:393-395` |
| Highway levy and difficulty | the highway levy has no difficulty adjustment | `city/finance.c:392-396` |

On very easy and easy, buildings pay no levies. On normal, buildings pay half. The highway levy is paid on every difficulty.

### 2.6 Wages, interest, salary and debt limit

| Rule | Value / formula | Cadence | Source |
|---|---|---|---|
| Wage range | 0 to 100 dn | on change | `city/labor.c:177-181` |
| Start wage and Rome wage | 30 and 30 | game start | `city/data.c:20-21` |
| Monthly wages | `wages * workers_employed / 10 / 12` | monthly | `city/finance.c:347` |
| Wage rate paid this year | sum of the monthly wage rate; the prosperity rating uses `/12` | monthly | `city/finance.c:350`, `city/ratings.c:473` |
| Interest | treasury < 0: `(-treasury * 10 / 100) / 12` per month (10 % per year) | monthly | `city/finance.c:353-360` |
| Salary | treasury > -5000: pay `salary_amount`; it goes to personal savings | monthly | `city/finance.c:362-369` |
| "Out of money" limit | treasury <= -5000 | continuous | `city/finance.c:108-111` |
| Effects of "out of money" | no construction, no festival, no salary, no mint gold purchase | continuous | `building/construction.c:914`, `building/construction.c:1204`, `window/hold_festival.c:56`, `city/finance.c:364`, `building/industry.c:183` |

### 2.7 Year-end finance (`city_finance_handle_year_change`)

Order: archive finance history (6 years), reset taxes, trade ledger year change, copy this year to last year, pay tribute (`city/finance.c:653-661`).

Tribute (`pay_tribute`, `city/finance.c:505-567`). "Income" and "expenses" are the totals of the year that ended. Income = donated + taxes + exports + miscellaneous. Expenses = sundries + salary + interest + construction + wages + levies + imports.

| Condition | Tribute | Other effect | Source |
|---|---|---|---|
| Treasury <= 0 | 0 | `tribute_not_paid_last_year = 1`; `tribute_not_paid_total_years + 1` | `city/finance.c:524-528` |
| Income <= expenses, population > 2000 | 200 | not-paid counter = 0 | `city/finance.c:529-534` |
| Income <= expenses, population > 1000 | 100 | not-paid counter = 0 | `city/finance.c:535-536` |
| Income <= expenses, population <= 1000 | 0 | not-paid counter = 0 | `city/finance.c:537-538` |
| Profit, population > 5000 | max(500, 25 % of profit) | not-paid counter = 0 | `city/finance.c:542-543`, `city/finance.c:555-558` |
| Profit, population > 3000 | max(400, 25 % of profit) | same | `city/finance.c:544-545` |
| Profit, population > 2000 | max(300, 25 % of profit) | same | `city/finance.c:546-547` |
| Profit, population > 1000 | max(225, 25 % of profit) | same | `city/finance.c:548-549` |
| Profit, population > 500 | max(150, 25 % of profit) | same | `city/finance.c:550-551` |
| Profit, population <= 500 | max(50, 25 % of profit) | same | `city/finance.c:552-553` |
| Payment | treasury − tribute (the treasury can go negative) | yearly | `city/finance.c:561` |

The tribute uses the treasury check before the profit check. A city in debt pays no tribute but gets favor and prosperity penalties (see 3.2 and 3.4).

### 2.8 Other income and expense flows

| Flow | Formula | Ledger line | Source |
|---|---|---|---|
| Export | treasury + price | exports | `city/finance.c:149-152` |
| Neptune blessing on exports | + `price / 2` extra while active | exports | `city/finance.c:153-156` |
| Import | treasury − price | imports | `city/finance.c:143-147` |
| Construction | treasury − cost | construction | `city/finance.c:191-195` |
| Sundry (festivals, money requests, route opening, mint gold, collapse fees) | treasury − cost | sundries | `city/finance.c:185-189` |
| Theft | added to stolen and to sundries | sundries | `city/finance.c:173-177` |
| Donation from personal savings, rescue loan | treasury + amount | donated | `city/finance.c:179-183` |
| Miscellaneous (tourism, mint, "money add" event) | treasury + amount | income total via `misc_this_year` | `city/finance.c:102-106` |
| Cheat | if treasury < 5000: +1000 | cheated | `city/finance.c:159-165` |

### 2.9 Tourism

| Rule | Value / formula | Cadence | Source |
|---|---|---|---|
| Tourist spawn | only while games are active: delay += `random_byte % culture_rating`; spawn when delay > 500 | tick 42, daily | `city/finance.c:1011-1024` |
| Venue income per visit | tavern 2, theater 1, amphitheater 1, arena 2, colosseum 4, hippodrome 5, each grand temple 3, pantheon 3 | per visit | `city/finance.c:61-74` |
| Venue active | in use and staffed | monthly | `city/finance.c:407-410` |
| Redundant venue (engine quirk) | the counter `tourism_modifiers[i].count` increases by 1 for each active venue each month and is never reset (file-static, not saved; it restarts at 0 only when the game program restarts). A venue gives no tourism income when `count * coverage > population`. Result: tavern (1000), theater (500), amphitheater (1500) and arena (2500) venues stop giving tourism income after some months and stay disabled. Venues with coverage 0 (colosseum, hippodrome, grand temples, Pantheon) always give income | monthly | `city/finance.c:61-74`, `city/finance.c:414-422` |
| Visit cooldown | a tourist pays again at the same building type after 96 ticks | per visit | `figure/service.c:19`, `figure/service.c:251-264` |
| Payment | `tourism_income` to treasury as miscellaneous income | per visit | `figure/service.c:267-272` |

### 2.10 City mint

| Rule | Value / formula | Cadence | Source |
|---|---|---|---|
| Requirement | a senate exists; the mint is in use, staffed and has road coverage (`houses_covered > 0`) | each production step | `building/industry.c:155-169` |
| Gold per 100 dn | 20 units of gold (one load = 100 units, so 1 load = 500 dn) | per cycle | `building/industry.h:8`, `game/resource.h:72` |
| Laborers | 40 | - | `building/properties.c:2105` |
| Max progress | `100 * (16 * 2 * laborers) / production_per_month(denarii=200)` = 640 at 40 laborers | - | `building/industry.c:72-77`, `game/resource.c:86` |
| Progress per step | + `num_workers` | 2 steps per day (ticks 20 and 46) | `building/industry.c:188`, `building/industry.c:197`, `building/industry.c:313` (call in `building_industry_update_production`), `game/tick.c:169`, `game/tick.c:193` |
| Cycle | at full staff a cycle completes on the 17th step (progress must exceed 640): 8.5 days, about 188 dn per month | derived | `building/industry.c:200-202` |
| Output per cycle | 100 dn | per cycle | `building/industry.c:21`, `building/industry.c:215` |
| Personal savings share | only with a governor's house and salary > 5: `salary_amount * 10 / 100` (minimum 1); the treasury gets `100 − share` | per cycle | `building/industry.c:203-215` |
| Reverse mode (dn to gold) | 600 dn sundry at the start of each cycle; no purchase when out of money | per cycle | `building/industry.c:22`, `building/industry.c:181-193` |
| Curse | a cursed mint skips steps on new days while `curse_days_left > 0` | daily | `building/industry.c:176-179` |

### 2.11 Random events with money or wage effects

`scenario_random_event_process()` runs monthly. It reads `RANDOM_EVENT_PROBABILITY[random_byte()]` from a 128-entry table (`scenario/random_event.c:31-40`, `scenario/random_event.c:171-176`). Each event also needs its scenario flag and a cooldown.

| Event | Chance per month | Effect | Cooldown | Source |
|---|---|---|---|---|
| Rome raises wages | 3/128 | Rome wage + `1 + (random & 3)` (1 to 4), cap at scenario max wage | > 12 months since the last wage change | `scenario/random_event.c:29`, `scenario/random_event.c:42-51`, `city/labor.c:188-198` |
| Rome lowers wages | 3/128 | Rome wage − 1 to 4, floor at scenario min wage | > 12 months | `scenario/random_event.c:53-62`, `city/labor.c:200-210` |
| Land trade disrupted | 5/128 | land trade problem for 48 days | > difficulty cooldown | `scenario/random_event.c:64-79` |
| Sea trade disrupted | 4/128 | sea trade problem for 48 days | > difficulty cooldown | `scenario/random_event.c:81-90` |
| Contaminated water | 2/128 | health −40 / −30 / −20; needs population > 200 | > difficulty cooldown | `scenario/random_event.c:92-111` |
| Iron mine collapse | 4/128 | destroys one iron mine, or with `CONFIG_GP_CH_RANDOM_COLLAPSES_TAKE_MONEY` costs 250 dn sundry | > difficulty cooldown | `scenario/random_event.c:113-130` |
| Clay pit flood | 5/128 | destroys one clay pit, or with the config option costs 250 dn sundry | > difficulty cooldown | `scenario/random_event.c:132-149` |
| Pantheon protection | a working Pantheon with all gods at happiness >= 60 blocks contaminated water, mine collapse and pit flood | - | `scenario/random_event.c:161-174`, `scenario/random_event.c:189-200` |

Difficulty cooldown (months) = 36 / 30 / 24 / 18 / 12 (very easy to very hard) (`game/difficulty.c:19-23`, `game/difficulty.c:81-84`).

### 2.12 Start money and rescue loan

| Rule | Value / formula | Source |
|---|---|---|
| Start treasury (scenario) | `difficulty_adjust_money(initial_funds)` | `city/data.c:38-42` (function at line 38) |
| Start treasury (campaign mission) | `difficulty_adjust_money(carried treasury)` | `city/data.c:44-47` |
| Editor defaults for a new map | initial funds 1000, rescue loan 500, Caesar salary 100, start year −500 | `scenario/editor.c:66-69` |
| Rescue loan | `difficulty_adjust_money(rescue_loan)`, booked as donation | `city/emperor.c:59-60` |
| Start personal savings | 0 in a custom scenario; the stored value for the rank in a campaign (not verified in detail) | `city/emperor.c:33`, `city/emperor.c:40-41`, `scenario/scenario.c:723-727` |

## 3. Ratings

All four ratings have the range 0 to 100. Update order in `city_ratings_update`: culture, favor, prosperity cap; then, in the yearly pass only, prosperity and peace (`city/ratings.c:659-668`).

| Rating | When it changes | Source |
|---|---|---|
| Culture | recalculated from zero at each monthly and yearly update (12 times per year) | `city/ratings.c:661`, `game/tick.c:79`, `game/tick.c:114` |
| Favor | monthly effects 11 times per year, yearly effects once per year, plus events at any time | `city/ratings.c:551-657` |
| Prosperity cap | recalculated monthly and yearly | `city/ratings.c:663` |
| Prosperity | changes once per year, plus bailout and event actions | `city/ratings.c:664-666` |
| Peace | changes once per year, plus event actions | `city/ratings.c:664-667` |
| Start values | culture, prosperity and peace start at 0 (`memset`); favor starts at the scenario start favor | `city/data.c:13-15`, `city/emperor.c:32` |

### 3.1 Culture rating

Culture = sum of the five point tables + monument bonus, bounded 0 to 100. Population 0 gives culture 0 (`city/ratings.c:351-358`, `city/ratings.c:448`).

Points for each coverage percentage (coverage is bounded at 100):

| Coverage % | Theater | Religion | School | Academy | Library | Source |
|---|---|---|---|---|---|---|
| >= 100 | 25 | 30 | 15 | 10 | 20 | `city/ratings.c:360-437` |
| > 85 | 18 | 22 | 10 | 7 | 14 | same |
| > 70 | 12 | 14 | 6 | 4 | 8 | same |
| > 50 | 8 | 9 | 4 | 2 | 4 | same |
| > 30 | 3 | 3 | 1 | 1 | 2 | same |
| <= 30 | 0 | 0 | 0 | 0 | 0 | same |
| Maximum | 25 | 30 | 15 | 10 | 20 | total 100 |

| Bonus | Value | Source |
|---|---|---|
| Each active grand temple (5 gods), Pantheon, Colosseum, Hippodrome | +6 each (`MONUMENT_CULTURE_BONUS`), maximum +48 | `city/ratings.c:17`, `city/ratings.c:439-446` |
| Config option `CONFIG_GP_CH_MONUMENTS_BOOST_CULTURE_RATING` | **no effect.** No game code reads this key. The +6 bonus always applies | `core/config.c:74` (only reference outside UI and translations) |

Coverage calculation (`city_culture_update_coverage`, tick 33, daily):

| Coverage | Formula | Source |
|---|---|---|
| Theater | `100 * (500 * active_theaters + 700 * upgraded_theaters) / population` | `city/culture.c:130`, `city/culture.c:264-267`, `city/culture.h:7-8` |
| Library | `100 * (800 * active + 900 * upgraded) / population` | `city/culture.c:217-218`, `city/culture.h:17-18` |
| School | `100 * (75 * active + 150 * upgraded) / school_age_population` | `city/culture.c:215-216`, `city/culture.h:15-16` |
| Academy | `100 * (100 * active + 50 * upgraded) / academy_age_population` | `city/culture.c:219-220`, `city/culture.h:19-20` |
| Religion | average of the 5 god coverages | `city/culture.c:204-210` |
| One god coverage (people) | lararium 10 × all larariums + 500 × (oracles + small mausoleums) + 750 × (nymphaeums + large mausoleums) + shrine 50 × shrines of the god + small temple 750 + large temple 3000 + Pantheon 1500 + grand temple 5000 (of the god); then `100 * people / population` | `city/culture.c:13-20`, `city/culture.c:147-161` |
| Count rule | larariums and shrines count all built (`building_count_total`); other buildings count active only | `city/culture.c:148`, `city/culture.c:156` |

Other coverage values that the culture rating does not use: tavern 1000 (+500 upgraded), amphitheater 1500 (+500), arena 2500 (+500), hospital 1500; colosseum and hippodrome give 100 % when working (`city/culture.h:9-14`, `city/culture.h:21`, `city/culture.c:129-144`).

### 3.2 Prosperity rating

| Rule | Value / formula | Cadence | Source |
|---|---|---|---|
| Prosperity cap | average of the house prosperity values (table in 2.2) over all houses with a non-zero state | monthly and yearly | `city/ratings.c:503-520` |
| No houses | cap 0 | - | `city/ratings.c:517-519` |
| Yearly change | prosperity + sum of the rows below, then `min(cap)`, then bound 0 to 100 | yearly | `city/ratings.c:494-498` |
| Unemployment < 5 % | +1 | yearly | `city/ratings.c:456-457` |
| Unemployment >= 15 % | −1 | yearly | `city/ratings.c:458-459` |
| Made money | +5 if `construction_last_year + treasury > treasury_at_last_prosperity_update`, else −1 | yearly | `city/ratings.c:168-172`, `city/ratings.c:462-467` |
| Food variety | +1 if the largest number of food types that one house ate in the last monthly food pass is >= 2 | yearly | `city/ratings.c:469-471`, `city/resource.c:563-565`, `city/resource.c:682-685` |
| Wages >= Rome + 2 | +1 (average wage = yearly sum of monthly wage rates / 12) | yearly | `city/ratings.c:473-475` |
| Wages < Rome | −1 | yearly | `city/ratings.c:476-477` |
| Tents and shacks > 30 % of population | −1 (house level <= large shack) | yearly | `city/ratings.c:480-482`, `city/population.c:400-402` |
| Villas and palaces > 10 % of population | +1 (house level >= small villa) | yearly | `city/ratings.c:483-485`, `city/population.c:406-408` |
| Tribute not paid last year | −1 | yearly | `city/ratings.c:487-489` |
| Hippodrome shows > 0 | +1 | yearly | `city/ratings.c:491-493` |
| Maximum yearly gain | +10 | derived | - |
| Maximum yearly loss | −5 (unemployment, money, wages, tents, tribute) | derived | - |
| Bailout (rescue loan) | −3 at once, floor 0 | once per game | `city/ratings.c:66-73`, `city/emperor.c:66` |

The "made money" test adds back the construction spending of the year. Construction therefore does not count as a loss. The test compares the treasury after the tribute payment with the treasury at the previous yearly update (`city/ratings.c:467`).

House prosperity values above 100 (villas and palaces) raise the average, but the rating is bounded at 100.

### 3.3 Peace rating

| Rule | Value / formula | Cadence | Source |
|---|---|---|---|
| Base change | +2 if `years_of_peace < 2`, else +5 | yearly | `city/ratings.c:525-529` |
| Any protester during the year | −1 (each protester spawn records one "criminal") | yearly | `city/ratings.c:530-532`, `figuretype/crime.c:204-213` |
| Any riot during the year | −5 | yearly | `city/ratings.c:533-535`, `figuretype/crime.c:132-154` |
| Buildings destroyed by enemies | −1 per building, maximum −12 | yearly | `city/ratings.c:75-102`, `city/ratings.c:536-538`, `building/destruction.c:330-346` |
| Not counted as destroyed | tents, prefecture, engineer post, well, forts, fort ground, gatehouse, tower, watchtower, palisade, palisade gate | - | `city/ratings.c:77-94` |
| Years of peace | reset to 0 after a riot or a destroyed building; else + 1 | yearly | `city/ratings.c:539-543` |
| Counters reset | criminals, rioters and destroyed buildings reset to 0 after each yearly update | yearly | `city/ratings.c:544-546` |

### 3.4 Favor rating (Caesar)

| Rule | Value / formula | Cadence | Source |
|---|---|---|---|
| Range | 0 to 100 | - | `city/ratings.c:120-123`, `city/ratings.c:655` |
| Start favor | difficulty value: 70 / 60 / 50 / 50 / 40 (very easy to very hard) | scenario start | `game/difficulty.c:19-23`, `scenario/scenario.c:718`, `scenario/scenario.c:724`, `scenario/scenario.c:731`, `city/emperor.c:32` |
| Open play with "reset favor monthly" | favor = 50 at each update; all other favor rules in this function are skipped | monthly and yearly | `city/ratings.c:553-556` |
| Imperial games active | +2 per monthly update for 12 months (not in the yearly update) | monthly | `city/ratings.c:18`, `city/ratings.c:561-565`, `city/games.c:207-211` |
| Yearly decay | −2; not in tutorial 1, tutorial 2, or after victory ("continue governing") | yearly | `city/ratings.c:570-572` |
| Tribute not paid, first year | −3 | yearly | `city/ratings.c:574-576` |
| Tribute not paid, second year in a row | −5 | yearly | `city/ratings.c:577-578` |
| Tribute not paid, third year or more | −8 | yearly | `city/ratings.c:579-581` |
| Salary higher than rank | −(delta + high-salary punishment); delta = rank for salary paid − player rank | yearly | `city/ratings.c:584-591`, `city/ratings.c:596-598` |
| High-salary punishment | 0 / 0 / 1 / 3 / 5 (very easy to very hard) | yearly | `game/difficulty.c:19-23`, `game/difficulty.c:86-89` |
| Salary lower than rank | +1 (not when the player rank is 0) | yearly | `city/ratings.c:592-595` |
| Rank for salary paid | lowest rank `i` where last year's salary <= `salary_for_rank(i) * 12` | yearly | `city/emperor.c:357-366` |
| Milestone met (25 %, 50 %, 75 %) | +5 if every enabled goal is >= `goal * pct / 100` | yearly, in the milestone year | `city/ratings.c:600-644` |
| Milestone missed | −2 | yearly | `city/ratings.c:640-643` |
| Request delivered on time | + request favor (default 8) | event | `scenario/request.c:146-148` |
| Request delivered late | + request favor / 2 | event | `scenario/request.c:149-151` |
| Request deadline missed | − extension disfavor (default 3) | event | `scenario/request.c:167-171` |
| Request ignored after extension | − ignored disfavor (default 5) | event | `scenario/request.c:173-178` |
| Gift | see 4.3 | event | `city/emperor.c:224-282` |
| Second debt (after the bailout) | −5 | event | `city/emperor.c:67-71` |
| 12 months more in debt | −10 (only when no Caesar soldiers are in the city) | event | `city/emperor.c:80-86` |
| 24 months more in debt | favor capped at 10 (only when no Caesar soldiers are in the city) | event | `city/emperor.c:96-101` |
| Caesar army defeated | +10 if favor < the "stop attack" threshold | event | `city/emperor.c:125-139` |
| Distant battle: no troops sent | −50 | event | `city/military.c:289-292` |
| Distant battle: troops too late | −25 | event | `city/military.c:293-297` |
| Distant battle: troops too weak | −10 | event | `city/military.c:298-302` |
| Distant battle won | +25 | event | `city/military.c:304-306` |
| Emperor change | favor = 50 | event | `city/ratings.c:249-252`, `scenario/emperor_change.c:23-35` |
| Scenario action "favor add" | + formula value | event | `scenario/event/action_types.c:237-243` |
| Favor trend | compares favor with last year's value: falling, same or rising (for the advisor text) | yearly | `city/ratings.c:646-653` |

Favor penalty explanation thresholds (advisor text only): salary penalty >= 8, tribute unpaid >= 3 years, ignored request penalty >= 5, salary penalty >= 5, tribute unpaid >= 2 years, ignored request penalty >= 3, salary penalty >= 3, tribute unpaid last year, salary penalty >= 2, milestone penalty, any salary penalty, rising, same (`city/ratings.c:300-341`).

## 4. Emperor

### 4.1 Ranks and salary

| Rank | Index | Salary % of Caesar salary | Salary at Caesar salary 100 | Source |
|---|---|---|---|---|
| Citizen | 0 | 0 | 0 | `city/emperor.c:17` |
| Clerk | 1 | 2 | 2 | same |
| Engineer | 2 | 5 | 5 | same |
| Architect | 3 | 8 | 8 | same |
| Quaestor | 4 | 12 | 12 | same |
| Procurator | 5 | 20 | 20 | same |
| Aedile | 6 | 30 | 30 | same |
| Praetor | 7 | 40 | 40 | same |
| Consul | 8 | 60 | 60 | same |
| Proconsul | 9 | 80 | 80 | same |
| Caesar | 10 | 100 | 100 | same |

Rank names come from the original game text (`window/set_salary.c:66-69`, text group 52, index rank + 4); the names in this table are the standard Caesar 3 names (names unverified in source text files).

| Rule | Value / formula | Source |
|---|---|---|
| Salary per month | `caesar_salary * pct[rank] / 100` | `city/emperor.c:289-292` |
| Caesar salary base | scenario value; 0 means 100 | `city/emperor.c:35-38` |
| Start rank (custom scenario) | scenario player rank, capped at 10 for the salary | `city/emperor.c:39-48` |
| Player sets salary rank | any of the 11 ranks; not possible after victory | `window/set_salary.c:102-111` |
| Salary is too high | salary rank > player rank gives a yearly favor penalty (see 3.4) | `city/ratings.c:584-599` |
| Promotion / demotion by event | rank +1 (code 11), −1 (code 12) or a set rank; the salary rank is set to the new rank | `city/emperor.c:294-327`, `scenario/event/action_types.c:830-835` |
| Continue governing after victory | salary rank and salary set to 0 | `city/victory.c:170-179` |

### 4.2 Personal savings

| Flow | Value / formula | Source |
|---|---|---|
| Salary | + salary per month while treasury > −5000 | `city/finance.c:362-369` |
| Mint share | see 2.10 | `building/industry.c:203-214` |
| Donation to the city | any amount up to savings − active bet | `city/emperor.c:386-408` |
| Gift to Caesar | − gift cost | `city/emperor.c:281` |
| Games | − games money cost (see 5.2) | `city/games.c:119` |
| Race bet won | + bet × 4 while games are active, else + bet × 2 | `city/race_bet.c:17-23` |
| Race bet lost | − bet (floor 0) | `city/race_bet.c:24-29` |
| Scenario action "savings add" | + formula value, floor 0 | `scenario/event/action_types.c:341-347`, `city/emperor.c:373-379` |

### 4.3 Gifts to Caesar

| Gift | Cost formula | Source |
|---|---|---|
| Modest | `savings / 8 + 20 * caesar_salary / 100` | `city/emperor.c:23`, `city/emperor.c:219` |
| Generous | `savings / 4 + 50 * caesar_salary / 100` | `city/emperor.c:24`, `city/emperor.c:220` |
| Lavish | `savings / 2 + 100 * caesar_salary / 100` | `city/emperor.c:25`, `city/emperor.c:221` |
| Affordability | cost <= savings − active race bet | `city/emperor.c:211-214` |

Favor gain depends on the overdose counter (`gift_overdose_penalty`):

| Gift number within the period | Modest | Generous | Lavish | Source |
|---|---|---|---|---|
| 1st (counter 0) | +3 | +5 | +10 | `city/emperor.c:236-244` |
| 2nd (counter 1) | +1 | +3 | +5 | `city/emperor.c:245-253` |
| 3rd (counter 2) | 0 | +1 | +3 | `city/emperor.c:254-262` |
| 4th (counter 3) | 0 | 0 | +1 | `city/emperor.c:263-271` |
| 5th and later (counter 4) | 0 | 0 | 0 | `city/emperor.c:236-272` |

| Rule | Value | Source |
|---|---|---|
| Months since gift | set to 0 at each gift; + 1 at each ratings update (12 per year) | `city/emperor.c:274`, `city/ratings.c:557` |
| Overdose reset | counter = 0 when months since gift >= 12 | `city/ratings.c:558-560` |
| Gift cost is paid even with 0 favor gain | yes | `city/emperor.c:281` |

### 4.4 Debt and the rescue loan

`update_debt_state()` runs daily on tick 4 (`city/emperor.c:51-104`, `game/tick.c:159`). The debt state never returns to 0 during a game (only `city_data_init` clears it, `city/data.c:13-15`).

| State | Trigger | Effect | Source |
|---|---|---|---|
| Any | treasury >= 0 | months in debt = −1; the state does not change | `city/emperor.c:53-56` |
| 0 → 1 | first day with treasury < 0 | rescue loan `difficulty_adjust_money(rescue_loan)` as donation; message; prosperity −3 | `city/emperor.c:57-66` |
| 1 → 2 | next day with treasury < 0 (also the next day if the loan did not cover the debt) | message; favor −5 | `city/emperor.c:67-71` |
| 2 → 3 | 12 months in debt in state 2 (counter + 1 on day 0 of each month while in debt) | message and favor −10 if no Caesar soldiers | `city/emperor.c:72-87` |
| 3 → 4 | 12 more months in debt | favor capped at 10 if no Caesar soldiers; this starts the Caesar invasion warning (see 4.5) | `city/emperor.c:88-102` |
| Counter restart | in states 2 and 3, if the treasury was >= 0 and goes below 0 again, the counter restarts at 0 and a message shows | `city/emperor.c:73-76`, `city/emperor.c:89-92` |
| Rescue loan | once per game | `city/emperor.c:57-66` |

### 4.5 Caesar invasion

`process_caesar_invasion()` runs daily on tick 4 (`city/emperor.c:106-173`).

| Rule | Value / formula | Source |
|---|---|---|
| Warning | when no invasion countdown runs and favor <= 10: countdown = 192 days (12 months); first warning shows a message | `city/emperor.c:140-148` |
| Countdown | −1 per day; at 0 the army arrives. Favor changes during the countdown do not cancel it | `city/emperor.c:149-151` |
| Army size (before difficulty) | 1st invasion 32, 2nd 64, 3rd 96, 4th and later 144 | `city/emperor.c:153-162` |
| Difficulty on army size | `size * enemies% / 100`, enemies % = 40 / 60 / 80 / 100 / 120; maximum 150 | `scenario/invasion.c:337-340`, `game/difficulty.c:19-23`, `game/difficulty.c:46-49` |
| Invasion duration | 192 days | `city/emperor.c:166` |
| Retreat | favor >= "stop" threshold and at least 17 days of the siege passed (countdown < 176) | `city/emperor.c:111-116` |
| Pause | favor >= "pause" threshold: the army pauses while the countdown > 0 | `city/emperor.c:117-124` |
| Pause threshold | 16 / 17 / 18 / 20 / 22 (very easy to very hard) | `game/difficulty.c:19-23`, `game/difficulty.c:71-74` |
| Stop threshold | 20 / 22 / 24 / 27 / 30 | `game/difficulty.c:19-23`, `game/difficulty.c:76-79` |
| Army killed | +10 favor if favor < stop threshold; message by invasion count | `city/emperor.c:125-139` |
| Invasions disabled by cheat | no Caesar army starts | `scenario/invasion.c:669-673` |

### 4.6 Emperor change event

| Rule | Value | Source |
|---|---|---|
| Year | scenario start year + scenario emperor change year | `scenario/emperor_change.c:18` |
| Month | `1 + (random_byte & 7)`: month index 1 to 8 (February to September) | `scenario/emperor_change.c:19` |
| Check | every tick; fires once | `scenario/emperor_change.c:23-35`, `game/tick.c:216` |
| Effect | favor = 50; message | `scenario/emperor_change.c:30-32`, `city/ratings.c:249-252` |

## 5. Festivals and games (finance and favor side)

### 5.1 Festivals

| Rule | Value / formula | Source |
|---|---|---|
| Small festival cost | `population / 20 + 10` dn | `city/festival.c:240` |
| Large festival cost | `population / 10 + 20` dn | `city/festival.c:241` |
| Grand festival cost | `population / 5 + 40` dn and `population / 500 + 1` loads of wine | `city/festival.c:242-243` |
| Cost update | tick 49, daily | `city/culture.c:261`, `game/tick.c:196` |
| Payment | sundry, at the time of planning | `city/festival.c:150` |
| Delay | small 2 months, large 3 months, grand 4 months | `city/festival.c:139-148` |
| Favor effect | none | `city/festival.c:168-187` |

Festival sentiment and god effects are in the religion and sentiment chapter.

### 5.2 Games (Colosseum and Hippodrome)

Money is paid from personal savings, not from the treasury (`city/games.c:119`). Resource cost = `units * (3 + population / 1200)` loads (`city/games.c:82`).

| Game | Money cost (personal savings) | Resources (units) | Delay | Duration | Bonus months | Source |
|---|---|---|---|---|---|---|
| Naval battle (id 1) | `1500 + 100 * (population / 1200)` | wine 1, timber 1 | 1 month | 32 days | 12 | `city/games.c:30-33` |
| Imperial games (id 2) | `800 + 150 * (population / 1200)` | wheat 2, oil 1 | 1 month | 32 days | 12 (+2 favor per monthly update) | `city/games.c:34-37`, `city/ratings.c:561-565` |
| Executions / animal games (id 3) | `800 + 150 * (population / 1200)` | meat 2 or fish 2 (the larger stock) | 1 month | 32 days | 12 | `city/games.c:38-41`, `city/games.c:71-81` |
| Duration countdown | −1 per day | - | - | tick 47 | - | `city/games.c:159-167` |
| Bonus countdown | −1 per month | - | - | - | - | `city/games.c:135-157` |

## 6. Caesar requests

| Rule | Value / formula | Cadence | Source |
|---|---|---|---|
| Defaults for a new request | denarii, amount 1, deadline 2 years, extension 24 months, favor 8, extension disfavor 3, ignored disfavor 5 | - | `scenario/request.h:6-13`, `scenario/request.c:26-37` |
| Old savegames (Caesar 3) | extension 24 months, disfavor 3 and 5, no repeat | - | `scenario/request.c:532-541` |
| Start month | `(random_byte & 7) + 2`: month index 2 to 9 (March to October) | at scenario start and at each repeat | `scenario/request.c:92`, `scenario/request.c:112` |
| Start year | scenario start year + request year | monthly check | `scenario/request.c:194-201` |
| Requested amount | random between min and max, chosen when the request becomes visible | once per occurrence | `scenario/request.c:47` |
| Deadline | `12 * deadline_years` months | - | `scenario/request.c:93`, `scenario/request.c:113` |
| Month counter | −1 per month while visible | monthly | `scenario/request.c:161-162` |
| Reminder | message when 12 months remain | monthly | `scenario/request.c:164-166` |
| Deadline missed | state "overdue"; new deadline = extension months; favor − extension disfavor | monthly | `scenario/request.c:167-172` |
| Extension missed | state "ignored"; favor − ignored disfavor; repeat is scheduled | monthly | `scenario/request.c:173-180` |
| Dispatch | goods leave the warehouses (then granaries for food); money is a sundry; troops remove population and weapons | on player action | `scenario/request.c:209-234` |
| Arrival delay | `(random_byte & 3) + 1` months (1 to 4) | - | `scenario/request.c:217` |
| Arrival on time | favor + request favor | monthly | `scenario/request.c:146-148` |
| Arrival late (dispatched while overdue) | favor + request favor / 2 | monthly | `scenario/request.c:149-151` |
| Money request check | treasury must be strictly greater than the amount | on display | `city/request.c:31-37` |
| Goods availability | warehouses first; food also counts granaries | on display | `city/resource.c:92-108` |
| `CONFIG_GP_CH_STORAGE_REQUESTS_RESPECT_MAINTAIN` | goods that a storage keeps ("maintain") do not count as available | on display | `city/resource.c:97-98`, `scenario/request.c:48-51` |
| Repeat | after delivery or after "ignored": new year = current game year offset + random(interval min, interval max); repeat count −1; count −1 means infinite | per occurrence | `scenario/request.c:105-121`, `scenario/request.h:16` |
| Repeat with interval 0 (engine quirk) | the fire check needs year and month to be equal (`scenario/request.c:198-199`). The repeat is scheduled during the month pass of month M. If the new random month is <= M in the same year, the request never fires | - | `scenario/request.c:110-113`, `scenario/request.c:198-201` |
| Scenario action "start request" | the request starts at once with a full deadline | event | `scenario/request.c:353-378` |
| Tutorial year adjustment | the tutorial can move or block the request year (not verified in detail) | - | `scenario/request.c:195-197` |

## 7. Empire and trade routes (finance side)

| Rule | Value / formula | Source |
|---|---|---|
| Open a route | cost = `cost_to_open` of the city, paid as sundry; plus any route resource costs (loads, from warehouses, then granaries for food) | `empire/city.c:474-493` |
| Money check | the player dialog checks resources only. It does not check the treasury, so the treasury can go negative | `window/empire.c:3208-3227` |
| Route cost source | empire object `trade_route_cost` | `empire/object.c:393`, `empire/object.c:480` |
| Scenario action "adjust route open price" | set or add; minimum 0 | `scenario/event/action_types.c:583-606`, `empire/city.c:334-345` |
| Scenario action "open route" | opens the route, with or without cost | `scenario/event/action_types.c:608-622` |
| Yearly quota reset | traded amounts of open routes reset each year | `empire/city.c:348-357`, `game/tick.c:77` |
| Empire expansion | after year `start_year + expansion_year` (strictly greater), once; not for a custom empire | `scenario/empire.c:18-36` |
| Export and import money | see 2.8 | `city/finance.c:143-157` |

## 8. Victory and loss

`city_victory_check()` runs every tick (`game/tick.c:217`). Open play has no victory check unless an event forces a win or a loss (`city/victory.c:124-126`).

| Rule | Value / formula | Source |
|---|---|---|
| Rating goals | culture, prosperity, peace, favor: rating >= goal | `city/victory.c:49-72` |
| Population goal | population >= goal | `city/victory.c:73-78` |
| Goal limits | ratings 0 to 100, years 0 to 999, population 0 to 99999 | `scenario/criteria.c:7-22` |
| Win | all enabled goals met, at least one goal enabled, and no survival time | `city/victory.c:44-82`, `city/victory.c:98-101` |
| Maximum year | start year + time limit years, or start year + survival years, else start year + 1000000 | `scenario/criteria.c:108-117` |
| Time limit | at year >= maximum year: loss | `city/victory.c:86-89` |
| Survival time | before the maximum year: no win. At the maximum year: win if no other goal is enabled or all goals are met; else loss | `city/victory.c:90-101` |
| The year check | runs at the year rollover (January of the maximum year) | `game/tick.c:70`, `city/victory.c:86` |
| Military loss 1 | invading enemies > 2 + own soldiers and population < highest population / 4: loss | `city/victory.c:106-110` |
| Military loss 2 | invading enemies > 0 and population <= 0: loss | `city/victory.c:111-115` |
| No goals | no win and no loss (state "none") | `city/victory.c:116-118` |
| Continue governing | after a win, the player can continue for a chosen number of months; the counter decreases monthly; at 0 the win shows again | `city/victory.c:129-131`, `city/victory.c:163-179`, `game/tick.c:94` |
| Loss sequence | first a "fired" message, then the mission-end window | `city/victory.c:139-147` |
| Scenario actions "win" and "lose" | force the state | `city/victory.c:29-37`, `scenario/event/action_types.c:816-828` |
| Debt | debt alone does not end the game. It leads to favor loss and a Caesar invasion (see 4.4 and 4.5) | `city/emperor.c:51-104` |

### 8.1 Milestones

| Rule | Value | Source |
|---|---|---|
| Milestone years | start year + milestone25 / milestone50 / milestone75 year | `scenario/criteria.c:94-106` |
| Editor defaults | 10, 20, 30 years | `scenario/editor.c:71-73` |
| Check | yearly favor update in the milestone year (the year that just started) | `city/ratings.c:600-610` |
| Target | each enabled goal (culture, prosperity, peace, favor, population) >= `goal * pct / 100` | `city/ratings.c:611-637` |
| Result | +5 favor if all are met, else −2 favor | `city/ratings.c:638-643` |

## 9. Difficulty modifiers

Table in `game/difficulty.c:6-24`. Columns: very easy, easy, normal, hard, very hard.

| Field | VE | E | N | H | VH | Use | Source of use |
|---|---|---|---|---|---|---|---|
| money % | 300 | 200 | 150 | 100 | 75 | start treasury, rescue loan, house tax multiplier | `city/data.c:40`, `city/data.c:46`, `city/emperor.c:59`, `city/finance.c:248`, `city/finance.c:292` |
| enemies % | 40 | 60 | 80 | 100 | 120 | invasion army size (also Caesar), maximum 150 | `scenario/invasion.c:337-340` |
| starting favor | 70 | 60 | 50 | 50 | 40 | start favor | `scenario/scenario.c:718`, `:724`, `:731` |
| sentiment | 80 | 75 | 70 | 65 | 60 | default sentiment | `city/sentiment.c:272` |
| levies % | 0 | 0 | 50 | 100 | 100 | building levies (not highway) | `building/building.c:1030` |
| base tax rate | 10 | 9 | 8 | 7 | 6 | tax sentiment reference | `city/sentiment.c:197` |
| food per soldier | −3 | −3 | −2 | 0 | +1 | added to the monthly soldier food use | `city/resource.c:585` |
| favor to pause Caesar | 16 | 17 | 18 | 20 | 22 | Caesar army pause | `city/emperor.c:117` |
| favor to stop Caesar | 20 | 22 | 24 | 27 | 30 | Caesar army retreat; +10 favor rule | `city/emperor.c:111`, `city/emperor.c:130` |
| random event cooldown (months) | 36 | 30 | 24 | 18 | 12 | trade, water, mine, pit events | `scenario/random_event.c:68`, `:84`, `:96`, `:116`, `:135` |
| high salary punishment | 0 | 0 | 1 | 3 | 5 | yearly favor penalty for high salary | `city/ratings.c:590`, `city/ratings.c:597` |
| wolf attack | 2 | 4 | 6 | default | default | wolf attack value | `game/difficulty.c:61-69`, `figure/combat.c:77` |

Scenario events can test the difficulty (`scenario/event/condition_types.c:357`).

## 10. Configuration options that change numbers in this chapter

| Option | Effect | Source |
|---|---|---|
| `CONFIG_GP_CH_YEARLY_AUTOSAVE` | autosave on month 11, day 15 | `game/tick.c:142-145` |
| `CONFIG_GP_CH_RANDOM_COLLAPSES_TAKE_MONEY` | an iron mine collapse or a clay pit flood costs 250 dn sundry instead of a destroyed building | `scenario/random_event.c:117-121`, `scenario/random_event.c:136-140` |
| `CONFIG_GP_CH_STORAGE_REQUESTS_RESPECT_MAINTAIN` | Caesar requests do not count goods that storages keep | `city/resource.c:97-98`, `scenario/request.c:48` |
| `CONFIG_GP_CH_FIXED_WORKERS` | workforce = plebs × fixed percentage (+ Venus bonus) instead of 60 % of working-age people × pleb share; this changes `workers_employed` and therefore the wage bill | `city/labor.c:222-230` |
| `CONFIG_GP_CH_MONUMENTS_BOOST_CULTURE_RATING` | no effect in this commit (see 3.1) | `core/config.c:74` |

The other `CONFIG_GP_*` options change logistics, walkers, housing or construction. They are out of scope for this chapter. `CONFIG_GP_FIX_IMMIGRATION_BUG` and `CONFIG_GP_FIX_100_YEAR_GHOSTS` have no references outside the config files.

## 11. Scenario event actions that change numbers in this chapter

Scenario events run daily (`game/tick.c:146-147`).

| Action | Effect | Source |
|---|---|---|
| Change city rating | set or add prosperity or peace (culture and favor are not supported by this action) | `scenario/event/action_types.c:71-97` |
| Favor add | favor + value | `scenario/event/action_types.c:237-243` |
| Money add | treasury + value (miscellaneous income) | `scenario/event/action_types.c:275-281` |
| Savings add | personal savings + value, floor 0 | `scenario/event/action_types.c:341-347` |
| Rome wages | set or add the Rome wage; minimum 1; resets the wage-change cooldown | `scenario/event/action_types.c:298-339` |
| Tax rate set | tax rate, bounded 0 to 25 | `scenario/event/action_types.c:681-688` |
| Change rank | rank +1, −1 or set | `scenario/event/action_types.c:830-835` |
| Request start | see 6 | `scenario/event/action_types.c:283` |
| Route open, route price | see 7 | `scenario/event/action_types.c:583-622` |
| Win, lose | see 8 | `scenario/event/action_types.c:816-828` |
| Change house model data | changes house tax multiplier and prosperity values | `scenario/event/action_types.c:853` |

## Items not verified

- The rank names in 4.1 come from the original language file. The source only shows the text index (`window/set_salary.c:68`).
- `scenario_property_player_rank`, the campaign personal-savings table (`game/settings.c:413-416`) and `tutorial_adjust_request_year` were not read in detail.
- The mint cycle length (8.5 days) assumes a full staff of 40 workers and no curse.
