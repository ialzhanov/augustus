# Economic feasibility model for Augustus scenarios

## 1. Purpose

The model tests one question for each map: **can a city exist that meets every win goal with the rules, terrain, trade and events of the map?** It also tests the opposite question: **is the map too easy?** Signs of a map that is too easy are: the goals are reachable with no trade, with no tax, or with a very large surplus.

The model does not play the game. It computes the best city that the rules allow at the moment of victory, and the treasury on the way to that moment.

## 2. Files

| File | Content |
|---|---|
| `econ_model.py` | The model. Python 3.12, scipy 1.18 (HiGHS MILP). |
| `../tools/dumper3.c`, `../tools/patterns.inc` | Loads each map with the Augustus loader and prints all inputs. |
| `results/base.json`, `results/run_base.txt`, `results/results_table.md` | Results with default assumptions. |
| `results/worst.json` (worst case, very hard), `results/normal.json` (normal difficulty) | Results with worst-case assumptions. |
| `results/quiza_rome.txt`, `results/quiza_against.txt` | The two Quiza paths. |

Run: `venv/bin/python econ_model.py <dump dir> [map ...] [--worst] [--skip E36,E67] [--forbid reservoir] [--json out.json] [--no-buildup]`

`--skip` removes the events of the path that the player does not take. `--forbid` removes a building that a penalty event makes unusable.

## 3. Inputs per map (from the engine loader)

| Input | Source |
|---|---|
| Win goals, start funds, rank, salary, rescue loan, start favor and savings, climate | scenario data |
| House model table (20 levels) after the map's model changes | `model_get_house` |
| Building model table (cost, workers, size) after the map's model changes | `model_get_building` |
| Production per month and workers for every good | `game/resource.c`, model table |
| Allowed buildings, local resources | scenario data |
| Trade routes: land or sea, permit cost, quotas, future routes | empire data |
| Prices (default, or saved prices in a start save) | `empire/trade_prices.c` |
| Scheduled price changes, demand changes, requests, invasions | scenario data |
| All events with conditions and actions | scenario event export |
| Packed production sites: farms (3×3 next to meadow), quarries and mines (2×2 next to rock), timber yards (2×2 next to trees), clay pits (2×2, water within 3), sand pits (2×2, water within 9), wharves (2×2 with one edge on water) | greedy packing with the rules of `building/construction.c:1400-1433` |
| Usable land, fish points, coast, Rome wheat flag, start-save stockpiles | map data |

## 4. Scenario state at victory

1. **Events.** Start events run first, then the scheduled price and demand changes up to the victory year, then the other events. Allowed buildings, local resources, prices, quotas and future routes change as the events say. `--skip` removes the events of the other path of an exclusive choice.
2. **Price semantics.** `trade_price_set` adds the difference to both buy and sell price. A drop that brings the sell price to 0 or below gives 2/0 (`scenario/event/action_types.c:435-466`, `empire/trade_prices.c:148-161`).
3. **Event flows.** Repeating `money_add`, `savings_add`, `favor_add`, stockpile changes and request starts become yearly flows. 192 days per year (`game/time.h:14`). A flow applies when its conditions are true at victory. Building counts come from the solved plan; the model then solves again. A condition "fewer than N of building X" counts as avoidable: the player builds X.
4. **Caps.** These events become caps, not flows: "favor −100, then +X each month" (the Numidia pattern), and a repeating favor loss on "favor ≥ X". A tax set on "tax ≥ X" becomes a tax cap; a monthly tax set becomes a fixed tax.
5. **Penalty limits.** A large penalty on "forum ≥ N" limits forums to N−1, and tax comes only from the people those forums reach. A large penalty on "small temples ≥ N" makes the plan use large temples.

## 5. Rule checks (not linear)

| Check | Rule | Source |
|---|---|---|
| Highest house level | A level is possible only if every need can be met: water (well, latrine, fountain), number of gods with allowed temples, entertainment points, education, health, barber, bathhouse, food types, pottery, oil, furniture, wine, second wine. | house model; `building/house_evolution.c:140-190` |
| Entertainment points | theater 10; tavern 10 (+5 with food); amphitheater 10 (15 with gladiator school); arena 10 (20 with lion house); colosseum 15 (25 with lions) +5 when completed; hippodrome 30 +5; Venus module +10. Venues create their own performers. | `building/house_service.c:95-139`, `building/figure.c:593-740` |
| Water level 3 | Fountains need reservoir range. Reservoirs fill only next to water. Without usable reservoirs, the Neptune Grand Temple module 2 gives a zone of (7 + 2×12 + 2×fountain radius)² tiles. Desert climate: fountain radius −1. | `map/water_supply.c:192-373`, `building/figure.c:983` |
| Wine types | 1 for a local wine workshop + 1 for each open route that sells wine + 1 for the Venus module. | `city/trade.c:17-23` |
| Culture | Points: theater 25, religion 30 (all 5 gods covered), school 15, academy 10, library 20; +6 for each Grand Temple, Pantheon, colosseum or hippodrome. The plan uses coverage first and monuments only when needed. | `city/ratings.c:351` (update_culture_rating), `city/culture.c:124` |
| Favor | −2 per year; +1 if salary is below rank; gifts from savings (cost = savings / 8, 4, 2 + 20%, 50%, 100% of Caesar salary; favor +3, +5, +10); requests; event flows; caps. | `city/ratings.c:551` (update_favor_rating), `city/emperor.c:19,224` |
| Peace years | +2 per year for the first 2 years of peace, then +5 per year. | `city/ratings.c:522` (update_peace_rating) |
| Prosperity years | At most +11 per year (+5 profit, +1 unemployment under 5%, +1 two foods, +1 wages ≥ Rome + 2, +1 villas over 10%, +1 hippodrome). | `city/ratings.c:452` (update_prosperity_rating) |
| Monuments | Monuments that the culture plan or a favor cap needs. Materials per phase (with map changes) are costed at import price or local supply. A material with no source makes the monument impossible. | `building/monument.c:63-117` |

## 6. The optimization (one MILP per map)

**Variables:** houses per level (levels 0–9 as 1×1 or merged 2×2); local production of each good; imports and exports per route and good; route opening (binary).

| Constraint | Formula | Source |
|---|---|---|
| Population | goal ≤ Σ houses × people ≤ 1.05 × goal (3000 when the map has no population goal) | |
| Prosperity cap | Σ houses × (house prosperity − goal) ≥ 0. The cap is the average value per house. | `city/ratings.c:503` (calculate_max_prosperity) |
| Tents rule | people in levels 0–3 ≤ 30% of all people (else −1 prosperity each year) | `city/ratings.c:480` |
| Water zone | tiles of houses that need fountains ≤ the Neptune zone (only when reservoirs are not usable) | |
| Labour | 0.45 × plebeians ≥ workers of services + industry + storage + barracks + monuments | `city/labor.c:17` |
| Goods balance | production + imports + event stock ≥ exports + house use + workshop input + requests + soldiers' weapons | `game/resource.c:92-102` |
| House goods use | value × 12 per year (×2 for houses larger than 1×1), in 1/100 load | `building/house_evolution.c:572-600` |
| Food | 0.5 units per person per month (6 per year = 0.06 loads); the j-th food type feeds houses that need ≥ j types, at a share of 1/types | `city/resource.c:516-570` |
| Route quota | import or export of a good on a route ≤ quota × open | `empire/trade_route.c` |
| Trader throughput | per route and direction ≤ trips per year × loads per trader. Land: trips = min(192 / 4, slots × 192 / trip days); trip = 2 × walk / 3.33 tiles per day + stop days. Sea: one ship per 30 days at most, 12 loads. slots = min(3, quotas / 60 + 1) | `empire/city.c:33-35,421-470`, `figuretype/trader.c:508,1004,1041`, `game/time.h:13`, `figure/movement.c:319` |
| Land | house tiles × 1.45 + industry tiles × 1.30 + 60 tiles per 1000 people ≤ 85% of usable land | |
| Sites | farms ≤ packed farm sites; quarries and mines ≤ rock sites; timber, clay, sand, wharves ≤ their packed sites; wharves also ≤ 3 × fish points | packed counts |
| Money | tax + exports + event money ≥ imports + wages + levies + salary + tribute + request denarii + route permits / 10 years | `city/finance.c` |
| Tax | 0.06 × rate × Σ people × house tax multiplier per year | `city/finance.c:240-262` |
| Wages | wage × workers / 10 per year; wage = Rome wage at victory + 2 | `city/finance.c:345-350` |
| Levies | small temple 4, large temple 8, Grand Temple 44, fort 8, colosseum 36, hippodrome 72 per month (all values in `city/finance.h:9-19`) | |
| Tribute | fixed by population (50 to 500), or 25% of profit | `city/finance.c:505-560` |
| Budget (build-up only) | route permits + industry buildings + 0.9 per person ≤ treasury + rescue loan | |

**Objective:** maximise the yearly surplus.

**Diagnosis when there is no plan:** the model removes one constraint group at a time. A group whose removal gives a plan is a blocker. An elastic solve with the goals kept hard shows the smallest change that gives a plan.

**Extra runs:** the same plan with no trade (is the map too easy?), with the tent mix allowed, and the lowest tax rate that still balances the budget.

**Build-up:** the plan at 25%, 50%, 75% and 100% of the population goal. Stages before 100% use only start and timed events, no prosperity or culture goal, and a budget limit. Population grows by 1500 per year. The treasury pays new build cost at the start of each stage and earns the mean surplus over the stage.

## 7. Assumptions (not in the engine)

| Assumption | Default | Worst case |
|---|---|---|
| People served per market / prefecture / engineer / barber / bathhouse / doctor / forum | 900 / 700 / 900 / 900 / 1200 / 1200 / 2000 | half of default |
| House tiles per fountain | 50 | 25 |
| Food loads per granary per year; loads per warehouse per year | 300; 200 | 150; 100 |
| Road overhead (houses; other buildings) | 45%; 30% | same |
| Usable land share | 85% | same |
| Wharves per fish point | 3 | 1.5 |
| Walk from entry to the trade warehouses | 25 tiles | 60 tiles |
| Caravan stop (16 loads at 11 ticks each, plus walk between warehouses) | 4 days | 8 days |
| Sea trip (river entry to dock and back, with docking) | 60 days | 120 days |
| Tax rate (unless a map caps or fixes it) | 8% | 8% |
| Forts | max invasion size / 40, at most 6 (0 if forts are banned) | same |
| Weapons per fort per year | 4 | 4 |
| Population growth per year (build-up) | 1500 | 800 |
| City services, storage and roads build cost | 0.9 per person | same |

## 8. Known limits

- The model checks a steady state at victory and a coarse build-up. It does not simulate months, walkers or desirability on the map.
- Desirability is not modelled. A plan with a few palaces among many low houses meets the prosperity cap in the model, but in the game palaces need high desirability around them.
- Exclusive choices need `--skip`. Without it the model applies both paths together.
- Events with quest variables (custom variables) are listed, not applied.
- Sentiment, crime, fire, disease and combat losses are not modelled.
- The trader-throughput limit depends on the walk distance and the sea trip time. Section 7 gives the default and worst values.
