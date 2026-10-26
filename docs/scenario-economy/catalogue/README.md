# Augustus engine catalogue: cadences, rules and requirements

Source: Augustus upstream commit `dae1899` (2026-10-24), `src/`. Every row cites `file:line`.

Chapters:
1. Time, finance, ratings, emperor and empire (`01`)
2. Housing and city services (`02`)
3. Population, migration, labour and sentiment (`03`)
4. Production, storage, logistics and trade (`04`)
5. Gods, military, natives, disasters and the scenario event system (`05`)

The tables in chapters 1–5 were written by five agents from the source. Each row has a citation. I checked the rows of the summary table below in the source myself, except the row marked "agent chapter 4". In the chapters, rows marked "unverified" could not be confirmed.

## Key cadences and limits

| Rule | Value | Source |
|---|---|---|
| Ticks per day / days per month / months per year | 50 / 16 / 12 (192 days per year) | game/time.h:13-14 |
| Walker speed at speed 1 | 15 ticks per tile = 3.33 tiles per day | figure/movement.c:319 |
| Scenario events | checked once per day; repeats counted in days (16 per month) | chapter 5.7.1 |
| Trader generation | checked once per day (tick 32) for each open route | game/tick.c:180, empire/city.c:495 |
| New trader delay | land 4 days, sea 30 days | empire/city.c:34-35 |
| Traders in the city per route | min(3, total route quotas / 60 + 1) | empire/city.c:33, 442; empire/city.h:8 |
| Loads per trader | caravan 8, ship 12; +4 / +6 with a fully staffed Mercury Grand Temple | figuretype/trader.c:1004-1055 |
| Caravan trading speed | 1 load per 11 ticks | figuretype/trader.c:508-511 |
| Sea limit per route | at most 192 / 30 = 6.4 ships per year = 77 loads in each direction | derived from the rows above |
| Trade problems | duration in days, −1 per day; −2 per day with a working lighthouse (sea) or caravanserai (land) | city/trade.c:24-42 |
| Wine types | 1 for a working wine workshop + 1 for each open route that sells wine + 1 for the Venus module | city/trade.c:17-23 |
| Production at full staff | loads per month = production_per_month / 100: wheat 1.6; other farms, clay, timber, iron, marble, stone 0.8; fish 1.0; sand 1.2; gold 0.2; workshops 0.4; bricks 0.6; concrete 1.2 | game/resource.c:65-87; building/industry.c:72 |
| Production at partial staff | progress grows by the number of workers each update, so output scales with workers | building/industry.c:280-300 |
| Inputs | 1 raw load per good; bricks 0.5 clay + 0.5 sand; concrete 0.5 sand | game/resource.c:92-102 |
| One load | 100 units | game/resource.h:72 |
| Food per person | 0.5 units per month (6 per year); split equally across the food types in the house | city/resource.c:516-570 |
| Goods use per house | model value per month; houses larger than 1×1 use goods twice per month | building/house_evolution.c:572-600 |
| Market delivery to a house | food up to 4 × house population per type; goods up to 8 × model value (12 with Venus) | figure/service.c:371-428 |
| Workers | 45% of plebeians (levels below small villa) | city/labor.c:17, 217-231 |
| Wages | wage × employed workers / 10 per year, paid monthly | city/finance.c:345-350 |
| Tax | per month: people × (house tax multiplier × difficulty money %) / 2 × tax rate %, for houses with tax coverage | city/finance.c:240-262 |
| Interest on debt | 10% per year of the debt, paid monthly | city/finance.c:353-358 |
| Tribute (yearly) | loss: 0 / 100 / 200 by population; profit: max(fixed 50–500 by population, 25% of profit); none when in debt | city/finance.c:505-560 |
| Immigration batch | 12 people per batch (scaled by a percentage) | city/migration.c:48 |
| Devolve delay | 2 (20 with the Venus Grand Temple) | building/house_evolution.c:20-21 |
| Prosperity | yearly change of at most +11; capped by the average prosperity value per house | city/ratings.c:452, 503 |
| Peace | yearly +2 in the first 2 years of peace, then +5 | city/ratings.c:522 |
| Favor | yearly −2, salary and milestone effects; monthly +2 during imperial games | city/ratings.c:551 |
| Culture | monthly; theater 25, religion 30, school 15, academy 10, library 20, +6 per monument | city/ratings.c:351 |
| Water ranges | well 2, latrines 3, fountain 4, reservoir 10. Neptune Grand Temple: well +1, fountain +1, reservoir +2. Desert: fountain −1. Module 2 gives reservoir range around the temple | map/water_supply.c:26-29, 232, 346-378 |
| Fountain water | a fountain works only inside reservoir range | building/figure.c:983 |
| Entertainment points | theater 10; tavern 10 (+5 food); amphitheater 10 (15 with both shows); arena 10/20; colosseum 15/25, +5 when built; hippodrome 30, +5 when built; Venus module +10 | building/house_service.c:95-139 |
| Difficulty (very easy … very hard) | money % 300/200/150/100/75 (start funds, rescue loan, house tax multiplier); levies % 0/0/50/100/100; base tax 10/9/8/7/6 | game/difficulty.c:18-23 |
| Warehouse capacity | 8 spaces × 4 loads = 32 loads | agent chapter 4 |

