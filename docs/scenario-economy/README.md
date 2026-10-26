# Scenario economy: engine catalogue, campaign analysis and feasibility model

This folder holds the work of a study of three custom campaigns for Augustus:
- All Roads Lead to Rome (ARLR, 13 maps)
- Reconquered Campaign (20 maps)
- Conquering Numidia (2 maps)

The study asks three questions:
1. Which rules and numbers of the engine control a city economy?
2. What makes a map hard, and what makes a good challenge?
3. Do the constraints of a map still let the player win, and is any map too easy?

All engine references are to Augustus upstream commit `dae1899` (2026-10-24). They use paths in `src/`.

## Contents

| Path | Content |
|---|---|
| `catalogue/README.md` | Summary of key cadences and limits (traders, production, food, labour, tax, ratings, water, difficulty) |
| `catalogue/01_time_finance_ratings.md` | Time and tick schedule, finance, ratings, emperor, victory rules, difficulty |
| `catalogue/02_housing_services.md` | House levels, evolution, desirability, services, water, health, entertainment, education, religion, fire, collapse, crime |
| `catalogue/03_population_labour.md` | Census, migration, sentiment, labour, wages, food distribution |
| `catalogue/04_production_trade.md` | Industries, storage, markets, trade, traders, prices, monuments, transport |
| `catalogue/05_gods_military_events.md` | Gods, Grand Temple modules, military, natives, disasters, the scenario event system (all 33 conditions and 56 actions, and what events cannot do) |
| `analysis/ARLR_analysis.md` | All Roads Lead to Rome: complication layers, challenge principles, defects |
| `analysis/RC_CN_analysis.md` | Reconquered and Numidia: terrain patterns, economy, map-maker tool inventory, defects, adaptation test |
| `analysis/images/` | Annotated terrain maps |
| `model/MODEL.md` | Feasibility model: inputs, constraints with sources, assumptions, limits |
| `model/econ_model.py` | The model (Python 3.12, scipy) |
| `model/results/` | Results for all 35 maps (hard difficulty, normal difficulty, worst case) and the two Quiza paths |
| `tools/` | Headless map dumper (C, links against an Augustus build) and analysis scripts |

## How to run

1. Build Augustus (see `../../CLAUDE.md`). Compile `tools/dumper3.c` against the object files of that build, then link it with SDL2, SDL2_mixer and zlib. `dumper3.c` includes `patterns.inc`.
2. Run `S=<work dir> GAME=<Caesar 3 data dir> tools/run3.sh`. The script loads every campaign map and start save, and writes `dump.txt`, `events.xml`, `messages.xml` and `compact.txt` for each map.
3. Run `python model/econ_model.py <dump dir> [map ...] [--difficulty hard] [--worst] [--skip E36,E67] [--forbid reservoir] [--json out.json]`.

## Main results

- On all 35 maps, the steady-state economy can meet every win goal at hard difficulty. The limits that matter are rule caps (favor caps until a Grand Temple stands or a quest ends) and time (peace 100 needs at least 22 years without damage).
- Trade is the main income on all maps. On every map except Valencia, the goals are impossible without trade.
- On Igilgili, Tarsus, Caesarea and Cyrene, food is the limit. Igilgili, Tarsus and Caesarea import all their food, and the trader throughput (8 or 12 loads per trader, at most 3 traders, one new ship per 30 days) caps the imports. These maps fail under worst-case assumptions.
- `trade_price_set` moves both the buy and the sell price. In Igilgili, this sets gold to 2/0 instead of the stated 50.
- `change_goal` in add mode adds the culture goal, not the goal that it changes.
