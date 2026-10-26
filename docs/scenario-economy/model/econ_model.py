"""Steady-state economic feasibility model for Augustus scenarios.

The model asks: at the moment of victory, can a city exist that meets every win goal
with the rules, terrain, trade and events of the map?  It solves one mixed-integer
linear program per map with scipy (HiGHS) and runs rule checks that are not linear.

Input: the dump directory made by dumper3 (dump.txt, compact.txt per map).
Engine numbers come from the dump (house and building models after load) or from the
constants below.  Each constant names its source in Augustus dae1899.
Values marked ASSUMPTION are not in the engine.  `--sens` runs them at x0.5 and x2.
"""
import argparse, collections, copy, json, math, os, re, sys
import numpy as np
from scipy.optimize import milp, LinearConstraint, Bounds

# ---------------------------------------------------------------- engine constants
FOOD_UNITS_PER_PERSON_MONTH = 0.5        # city/resource.c:530 calc_adjust_with_percentage(pop, 50)
UNITS_PER_LOAD = 100                     # game/resource.h:72 RESOURCE_ONE_LOAD
WORKER_SHARE_OF_PLEBS = 0.45             # city/labor.c:17 PLEB_PERCENTAGE (and 60% of ages 20-49, same value)
FIRST_PATRICIAN_LEVEL = 12               # city/finance.c:248 HOUSE_SMALL_VILLA
TAX_FACTOR = 0.06                        # city/finance.c:258: 12 * pop*mult/2 * rate/100
WAGE_DIVISOR = 10                        # city/finance.c:347 wages * employed / 10 / 12 per month
SCHOOL_AGE_SHARE = 10 / 64               # city/population.c:89 add_to_census age distribution, ages 0-14
ACADEMY_AGE_SHARE = 10 / 64              # ages 14-21
COVERAGE = {                             # city/culture.c, building/*.c *_COVERAGE
    'theater': 500, 'amphitheater': 1500, 'arena': 2500, 'tavern': 1000, 'school': 75, 'library': 800,
    'academy': 100, 'hospital': 1500, 'small_temple': 750, 'large_temple': 3000, 'oracle': 500,
    'grand_temple': 5000, 'pantheon': 1500}
CULTURE_POINTS = {'theater': 25, 'religion': 30, 'school': 15, 'academy': 10, 'library': 20}  # city/ratings.c:286
MONUMENT_CULTURE_BONUS = 6               # city/ratings.c:13
CULTURE_MONUMENTS = ['grand_temple_ceres', 'grand_temple_neptune', 'grand_temple_mercury', 'grand_temple_mars',
                     'grand_temple_venus', 'pantheon', 'colosseum', 'hippodrome']
LEVY_MONTH = {                           # city/finance.h:9-19
    'fort': 8, 'small_temple': 4, 'large_temple': 8, 'oracle': 4, 'tower': 2, 'lighthouse': 8, 'grand_temple': 44,
    'pantheon': 48, 'colosseum': 36, 'hippodrome': 72, 'small_mausoleum': 2, 'large_mausoleum': 2, 'nymphaeum': 4,
    'caravanserai': 8}
SALARY_PCT_FOR_RANK = [0, 2, 5, 8, 12, 20, 30, 40, 60, 80, 100]   # city/emperor.c:17
GIFT = [(20, 8, 3), (50, 4, 5), (100, 2, 10)]   # city/emperor.c:22 (base % of caesar salary, savings divisor, favor)
ENT_SOURCES = {  # building/house_service.c:95-139 entertainment points per house
    'theater': 10, 'tavern': 15, 'amphitheater': 15, 'arena': 20, 'colosseum': 25, 'hippodrome': 30,
    'colosseum_done': 5, 'hippodrome_done': 5, 'venus_module': 10}
TRIBUTE_FIXED = [(5000, 500), (3000, 400), (2000, 300), (1000, 225), (500, 150), (-1, 50)]
DAYS_PER_YEAR = 192                      # game/time.h:14 16 days x 12 months
TILES_PER_DAY = 50 / 15                  # game/time.h:13 50 ticks per day; figure/movement.c:319 15 ticks per tile
TRADER = {'LAND': {'delay': 4, 'units': 8}, 'SEA': {'delay': 30, 'units': 12}}  # empire/city.c:34-35, figuretype/trader.c:1004,1041
MAX_TRADERS, RESOURCES_TO_TRADER_RATIO = 3, 60                                   # empire/city.h:8, empire/city.c:33  # city/finance.c:541
RESERVOIR_RADIUS, FOUNTAIN_RADIUS = 10, 4    # map/water_supply.c:26-29; Neptune GT +2 / +1; desert fountain -1
SUPPLY_CHAIN = {'pottery': {'clay': 1}, 'furniture': {'timber': 1}, 'oil': {'olives': 1}, 'wine': {'vines': 1},
                'weapons': {'iron': 1}, 'bricks': {'clay': .5, 'sand': .5}}   # game/resource.c:92-102
MONUMENT_PHASES = {   # building/monument.c:63-117, per phase (1-based), architects not counted
    'grand_temple': [{'stone': 20}, {'timber': 8, 'concrete': 20}, {'timber': 8, 'marble': 16}, {'timber': 16, 'bricks': 28, 'marble': 12}],
    'pantheon': [{'stone': 20}, {'timber': 8, 'stone': 20}, {'timber': 16, 'concrete': 40}, {'timber': 16, 'marble': 32, 'gold': 16}],
    'lighthouse': [{'stone': 16}, {'timber': 8, 'stone': 16}, {'timber': 16, 'stone': 12}, {'timber': 8, 'bricks': 20, 'stone': 12}],
    'colosseum': [{'stone': 12}, {'timber': 8, 'concrete': 16}, {'timber': 12, 'stone': 16}, {'timber': 12, 'bricks': 16, 'marble': 20}],
    'hippodrome': [{'stone': 32}, {'timber': 16, 'concrete': 32}, {'timber': 16, 'stone': 32}, {'timber': 32, 'bricks': 32, 'marble': 48}],
    'large_temple': [{'stone': 4, 'concrete': 4}, {'marble': 2}],
    'oracle': [{'concrete': 2, 'marble': 2}],
    'small_mausoleum': [{'stone': 2, 'concrete': 4}, {'marble': 2}],
    'nymphaeum': [{'stone': 12, 'concrete': 4}, {'marble': 2}],
}
MONUMENT_RESOURCES = {   # building/monument.c:63-117 (phases summed; architects not counted)
    'grand_temple': {'stone': 20, 'timber': 32, 'concrete': 20, 'marble': 28, 'bricks': 28},
    'pantheon': {'stone': 40, 'timber': 40, 'concrete': 40, 'marble': 32, 'gold': 16},
    'lighthouse': {'stone': 56, 'timber': 32, 'bricks': 20},
    'colosseum': {'stone': 28, 'timber': 32, 'concrete': 16, 'bricks': 16, 'marble': 20},
    'hippodrome': {'stone': 64, 'timber': 64, 'concrete': 32, 'bricks': 32, 'marble': 48},
    'large_temple': {'stone': 4, 'concrete': 4, 'marble': 2},
}
# game/difficulty.c:18-23: money % (start funds, rescue loan, house tax multiplier), levies %
DIFFICULTY = {'very_easy': (300, 0), 'easy': (200, 0), 'normal': (150, 50), 'hard': (100, 100), 'very_hard': (75, 100)}
DIFF = {'level': 'hard'}
def dmoney(v):
    return int(v * DIFFICULTY[DIFF['level']][0] / 100)  # calc_adjust_with_percentage truncates
def dlevy(v):
    return v * DIFFICULTY[DIFF['level']][1] / 100
FOODS = ['wheat', 'vegetables', 'fruit', 'meat', 'fish']
GOODS = ['pottery', 'furniture', 'oil', 'wine']
INDUSTRY = {'wheat': 'wheat_farm', 'vegetables': 'vegetable_farm', 'fruit': 'fruit_farm', 'meat': 'pig_farm',
            'fish': 'wharf', 'clay': 'clay_pit', 'timber': 'timber_yard', 'olives': 'olive_farm',
            'vines': 'vines_farm', 'iron': 'iron_mine', 'marble': 'marble_quarry', 'gold': 'gold_mine',
            'sand': 'sand_pit', 'stone': 'stone_quarry', 'pottery': 'pottery_workshop',
            'furniture': 'furniture_workshop', 'oil': 'oil_workshop', 'wine': 'wine_workshop',
            'weapons': 'weapons_workshop', 'bricks': 'brickworks'}
FARMS = {'wheat', 'vegetables', 'fruit', 'meat', 'olives', 'vines'}
ROCK = {'iron', 'marble', 'gold', 'stone'}

# ---------------------------------------------------------------- assumptions
A = {
    # people that one walker service building serves (ASSUMPTION)
    'serve_market': 900, 'serve_prefecture': 700, 'serve_engineer': 900, 'serve_barber': 900,
    'serve_bathhouse': 1200, 'serve_doctor': 1200, 'serve_forum': 2000, 'serve_fountain_tiles': 50,
    'serve_granary_food_loads': 300, 'serve_warehouse_loads': 200,
    # land (ASSUMPTION)
    'road_overhead_houses': 0.45, 'road_overhead_buildings': 0.30,
    # resource sites (ASSUMPTION)
    'meadow_tiles_per_farm': 4, 'rock_sites_per_quarry': 6, 'water_tiles_per_claypit': 8, 'wharves_per_fish_point': 3,
    'tree_tiles_per_timber_yard': 12,
    # play (ASSUMPTION)
    'trade_walk_tiles': 25, 'trade_stop_days': 4, 'sea_trip_days': 60,
    'growth_per_year': 1500, 'tax_rate': 8, 'performer_buildings_per_venue': 0.3, 'forts': 4, 'weapons_per_fort_year': 4,
}
SENS_KEYS = [k for k in A if k.startswith('serve_') or k.endswith('per_farm') or k.startswith('road_')]


def num(v):
    m = re.match(r'\{?(-?\d+)(?:,(-?\d+))?', v or '')
    if not m:
        return 0
    a = int(m.group(1))
    return (a + int(m.group(2))) / 2 if m.group(2) else a


def attrs(s):
    return dict(re.findall(r'(\w+)=(\{[^}]*\}|\S+)', s))


def rn(r):
    return (r or '').split('|')[0]


# ---------------------------------------------------------------- map loading
def load_map(d):
    t = open(os.path.join(d, 'dump.txt')).read()
    m = {'name': os.path.basename(d)}
    g = lambda p, f=int: f(re.search(p, t, re.M).group(1))
    w = re.search(r'^WIN pop=(\d):(\d+) culture=(\d):(\d+) prosperity=(\d):(\d+) peace=(\d):(\d+) favor=(\d):(\d+)', t, re.M)
    m['goal'] = {k: int(w.group(2 * i + 2)) if w.group(2 * i + 1) == '1' else 0
                 for i, k in enumerate(['pop', 'culture', 'prosperity', 'peace', 'favor'])}
    st = re.search(r'^START .*climate=(\d) rank=(\d+) salary=(\d+) funds=(\d+) rescue_loan=(\d+) .*start_favor=(\d+) savings=(\d+)', t, re.M)
    m['climate'], m['rank'], m['caesar_salary'], m['funds'], m['rescue_loan'], m['start_favor'], m['savings'] = map(int, st.groups())
    if 'SAVE' not in m['name']:
        m['funds'] = dmoney(m['funds'])        # city/data.c:40
    m['rescue_loan'] = dmoney(m['rescue_loan'])  # city/emperor.c:59
    m['houses'] = []
    for hm in re.finditer(r'^HOUSE (\d+) (.*)$', t, re.M):
        h = {k: int(v) for k, v in re.findall(r'(\w+)=(-?\d+)', hm.group(2))}
        h['level'] = int(hm.group(1))
        m['houses'].append(h)
    m['bmodel'] = {}
    for kv in re.search(r'^BMODEL (.*)$', t, re.M).group(1).split():
        k, v = kv.rsplit('=', 1)
        c, wk, sz = map(int, v.split(':'))
        for name in k.split('|'):
            m['bmodel'][name] = {'cost': c, 'workers': wk, 'size': sz}
    m['prod'] = {}
    for kv in re.search(r'^PRODUCTION \S+ (.*)$', t, re.M).group(1).split():
        k, v = kv.split('=')
        ind, pm, wk = map(int, v.split(':'))
        m['prod'][rn(k)] = {'loads_year': pm * 12 / 100, 'workers': wk}
    m['prices'] = {}
    for kv in re.search(r'^PRICES\(\w+\) buy/sell: (.*)$', t, re.M).group(1).split():
        k, v = kv.split('=')
        b, s = v.split('/')
        m['prices'][rn(k)] = [int(b), int(s)]
    m['local'] = set(rn(x) for x in re.search(r'^LOCAL can_produce:(.*)$', t, re.M).group(1).split())
    m['forbidden'] = set(re.search(r'^FORBIDDEN BUILDINGS:(.*)$', t, re.M).group(1).split())
    m['routes'] = {}
    for rm in re.finditer(r'^  route (\d+) (.+?) type=(\d) (LAND|SEA) open=\d cost=(\d+) \| sells:(.*?) \| buys:(.*)$', t, re.M):
        rid, name, typ, kind, cost, se, bu = rm.groups()
        p = lambda s: {rn(x.split('(')[0]): int(x.split('(')[1][:-1]) for x in s.split()}
        m['routes'][name] = {'id': int(rid), 'future': typ == '3', 'kind': kind, 'cost': int(cost),
                             'sells': p(se), 'buys': p(bu)}
    pat = lambda p: g(p, float)
    m['land'] = pat(r'usable=(\d+) \(') * 0.85   # ASSUMPTION: 85% of usable land can hold the city
    m['meadow'] = pat(r'^TERRAIN .* meadow=(\d+)')
    m['rock_sites'] = max(pat(r'rock_edge_sites=(\d+)'), pat(r'^TERRAIN .* rock=(\d+)') / 3)
    m['trees'] = pat(r'map tree=(\d+)')
    usable = pat(r'usable=(\d+) \(')
    m['water_near3'] = usable * pat(r'within3=([\d.]+)%') / 100
    m['fish_pts'] = g(r'fish_pts=(\d+)')
    m['coast'] = pat(r' coast=(\d+)')
    sm = re.search(r'^SITES farm=(\d+) rock=(\d+) timber=(\d+) clay=(\d+) sand=(\d+) wharf=(\d+)', t, re.M)
    m['sites'] = dict(zip(['farm', 'rock', 'timber', 'clay', 'sand', 'wharf'], map(int, sm.groups())))
    m['rome_wheat'] = int(re.search(r'rome_wheat=(\d)', t).group(1))
    ss = re.search(r'^SAVE stock:(.*)$', t, re.M)
    m['stock'] = {rn(k): int(v) for k, v in re.findall(r'(\S+)=(\d+)', ss.group(1))} if ss else {}
    m['requests'] = []
    for rq in re.finditer(r'^  req year\+(\d+) month=\d+ (\S+) (\d+)-(\d+) deadline=\d+m favor=(\d+)', t, re.M):
        m['requests'].append({'year': int(rq.group(1)), 'res': rn(rq.group(2)), 'amount': (int(rq.group(3)) + int(rq.group(4))) / 2,
                              'favor': int(rq.group(5))})
    m['price_changes'] = [(int(a), rn(r), (1 if sg == '+' else -1) * int(v)) for a, r, sg, v in
                          re.findall(r'^  price year\+(\d+) month=\d+ (\S+) ([+-])(\d+)', t, re.M)]
    m['demand_changes'] = [(int(a), int(rid), rn(r), int(v), b == '1') for a, r, rid, v, b in
                           re.findall(r'^  dem year\+(\d+) month=\d+ (\S+) route=(\d+) amount=(-?\d+) buys=(\d)', t, re.M)]
    m['invasion_max'] = max([int(x) for x in re.findall(r'^  inv .* amount=\d+-(\d+)', t, re.M)] or [0])
    m['events'] = []
    for line in open(os.path.join(d, 'compact.txt')):
        if not line.startswith('E'):
            continue
        em = re.match(r'(E\d+) (?:\[[^\]]*\] )?(?:rep(\S+)-(\S+)d x(\S+) )?IF (.*?) => (.*)$', line.strip())
        if not em:
            continue
        eid, rmin, rmax, rcount, cond, acts = em.groups()
        conds = [] if cond == 'always' else [c.strip() for c in cond.split(' & ')]
        m['events'].append({'id': eid, 'repeat_days': (num(rmin) + num(rmax)) / 2 if rmin and rmin != 'None' else 0,
                            'count': rcount, 'conds': conds,
                            'acts': [(a.split(' ')[0], attrs(a)) for a in acts.split(' ; ') if a]})
    return m


# ---------------------------------------------------------------- scenario state at victory
def apply_events(m, skip, opts_year=40, timed_only=False):
    """Apply allowed-building, resource, trade and price events in id order (skip = ids of the other path)."""
    allowed = set(m['bmodel']) - m['forbidden']
    local = set(m['local'])
    prices = copy.deepcopy(m['prices'])
    routes = copy.deepcopy(m['routes'])
    notes = []

    def shift(r, adj):
        if r not in prices:
            return
        if adj < 0 and prices[r][1] <= -adj:
            prices[r] = [2, 0]
        else:
            prices[r][0] += adj
            prices[r][1] += adj
    def is_start(e):
        return not e['conds'] or all(re.fullmatch(r'time check=(gte|eq|gt) value=\{?[01](,[01]\})?', c) for c in e['conds'])
    def is_timed(e):
        ok = True
        for c in e['conds']:
            mm = re.fullmatch(r'time check=(?:gte|eq|gt) value=\{?(\d+)(?:,\d+\})?', c)
            if not mm or int(mm.group(1)) > opts_year * 12: ok = False
        return ok
    rest = [e for e in m['events'] if not is_start(e) and (not timed_only or is_timed(e))]
    ordered = [e for e in m['events'] if is_start(e)] + [None] + rest
    for e in ordered:
        if e is None:
            # scheduled price and demand changes up to the victory year
            for yr, r, v in sorted(m['price_changes']):
                if yr <= opts_year: shift(r, v)
            byid = {ro['id']: nm for nm, ro in routes.items()}
            for yr, rid, r, v, buys in sorted(m['demand_changes']):
                if yr <= opts_year and rid in byid:
                    routes[byid[rid]]['buys' if buys else 'sells'][r] = max(v, 0)
            continue
        if e['id'] in skip:
            continue
        for n, a in e['acts']:
            if n == 'change_allowed_buildings':
                names = [a.get('building')]
                if names[0] == 'workshops':
                    names = [INDUSTRY[x] for x in ['pottery', 'furniture', 'oil', 'wine', 'weapons']]
                for b in names:
                    (allowed.add if a.get('allowed') == 'true' else allowed.discard)(b)
            elif n == 'change_resource_produced':
                (local.add if a.get('produced') == 'true' else local.discard)(rn(a.get('resource')))
            elif n == 'empire_map_convert_future_trade_city' and a.get('target_city') in routes:
                routes[a['target_city']]['future'] = False
            elif n in ('trade_route_amount', 'trade_route_add_new_resource') and a.get('target_city') in routes:
                side = 'buys' if (a.get('buying') or a.get('add_as_buying')) == 'true' else 'sells'
                routes[a['target_city']][side][rn(a.get('resource'))] = max(num(a.get('amount')), 0)
            elif n == 'trade_price_set' and rn(a.get('resource')) in prices:
                r = rn(a['resource'])
                shift(r, num(a['amount']) - prices[r][0 if a.get('set_buy_price') == 'true' else 1])
            elif n == 'trade_price_adjust':
                shift(rn(a.get('resource')), num(a.get('amount')))
            elif n == 'trade_set_buy_price_only' and rn(a.get('resource')) in prices:
                prices[rn(a['resource'])][0] = max(1, num(a['amount']))
            elif n == 'trade_set_sell_price_only' and rn(a.get('resource')) in prices:
                prices[rn(a['resource'])][1] = max(1, num(a['amount']))
            elif n == 'change_trade_route_open_price':
                for rname, ro in routes.items():
                    if rname == a.get('target_city'):
                        ro['cost'] = num(a.get('amount')) if a.get('set_to_value') == 'true' else ro['cost'] + num(a.get('amount'))
    return allowed, local, prices, routes, notes


def event_rules(m, skip):
    """Read caps, fixed values and recurring flows that events create."""
    r = {'tax_cap': None, 'tax_fixed': None, 'favor_caps': [], 'rating_set': [], 'rome_wages': 30, 'flows': [],
         'stock_flows': collections.Counter(), 'cond_flows': [], 'one_off_money': 0, 'one_off_savings': 0}
    wages = []
    for e in m['events']:
        if e['id'] in skip:
            continue
        acts = dict((n, a) for n, a in e['acts'])
        for n, a in e['acts']:
            if n == 'tax_rate_set':
                tc = [c for c in e['conds'] if c.startswith('tax_rate')]
                if tc:
                    r['tax_cap'] = num(a['amount']) if r['tax_cap'] is None else min(r['tax_cap'], num(a['amount']))
                elif e['repeat_days']:
                    r['tax_fixed'] = num(a['amount'])
                else:
                    r['tax_cap'] = num(a['amount']) if r['tax_cap'] is None else min(r['tax_cap'], num(a['amount']))
            if n == 'change_rome_wages':
                wages.append((e, num(a.get('formula')), a.get('set_to_value') == 'true'))
            if n == 'change_city_rating' and a.get('set_to_value') == 'true':
                r['rating_set'].append((e['id'], a.get('rating'), num(a.get('amount')), e['conds']))
        fav = [num(x.get('amount')) for n, x in e['acts'] if n == 'favor_add']
        e['is_cap'] = False
        if e['repeat_days'] and fav and min(fav) <= -100 and max(fav) > 0:
            # favor_add -100 then +X every month: favor is held at X (Numidia pattern)
            r['favor_caps'].append((e['id'], max(fav), [c for c in e['conds'] if 'stats_favor' not in c]))
            e['is_cap'] = True
        else:
            th = re.findall(r'stats_favor check=(gte|gt) value=(\d+)', ' '.join(e['conds']))
            if e['repeat_days'] and fav and sum(fav) < 0 and th:
                cap = int(th[0][1]) - (1 if th[0][0] == 'gte' else 0)
                r['favor_caps'].append((e['id'], cap, [c for c in e['conds'] if 'stats_favor' not in c]))
                e['is_cap'] = True
        if e['repeat_days'] and not e.get('is_cap'):
            per_year = 192 / e['repeat_days']
            if e['count'] not in ('inf', 'None'):
                per_year = 0  # finite repeats are one-off over a few years
            for n, a in e['acts']:
                if n in ('money_add', 'savings_add', 'favor_add'):
                    r['flows'].append({'id': e['id'], 'kind': n, 'per_year': per_year * num(a.get('formula') or a.get('amount')),
                                       'conds': e['conds']})
                elif n == 'change_resource_stockpiles':
                    r['flows'].append({'id': e['id'], 'kind': 'stock:' + rn(a.get('resource')),
                                       'per_year': per_year * num(a.get('amount')) / UNITS_PER_LOAD * (1 if abs(num(a.get('amount'))) > 50 else 100),
                                       'conds': e['conds']})
                elif n == 'request_immediately_start':
                    r['flows'].append({'id': e['id'], 'kind': 'request:' + a.get('request_id', ''), 'per_year': per_year,
                                       'conds': e['conds']})
        else:
            for n, a in e['acts']:
                if n == 'money_add':
                    r['one_off_money'] += num(a.get('formula'))
                if n == 'savings_add':
                    r['one_off_savings'] += num(a.get('formula'))
    # Rome wages at victory: population steps reached by the goal
    base = 30
    for e, v, is_set in wages:
        pc = [int(x) for x in re.findall(r'city_population check=g\w* value=(\d+)', ' '.join(e['conds']))]
        if pc and pc[0] > m['goal']['pop']:
            continue
        base = v if is_set else base + v
    r['rome_wages'] = base
    return r


def eval_cond(c, state):
    """True / False / None (unknown) for one condition at the victory state."""
    mm = re.match(r'(\w+) (.*)$', c)
    if not mm:
        return None
    kind, rest = mm.groups()
    a = attrs(rest)
    chk, val = a.get('check'), num(a.get('value'))
    def cmp(x):
        return {'gte': x >= val, 'gt': x > val, 'lte': x <= val, 'lt': x < val, 'eq': x == val, 'neq': x != val}.get(chk)
    if kind == 'time':
        return True
    if kind == 'city_population':
        return cmp(state['pop']) if a.get('class', 'all') == 'all' else None
    if kind.startswith('stats_'):
        key = kind[6:]
        return cmp(state['ratings'].get(key, 0)) if key in state['ratings'] else None
    if kind == 'building_count_active' or kind == 'building_count_any':
        b = a.get('building')
        cur = state['counts'].get(b, 0)
        if chk in ('lt', 'lte') and cmp(cur):
            state.setdefault('avoidable', set()).add(f'build {b} (>= {val})')
            return False  # the player can build it and stop the event
        if b in state['counts']:
            return cmp(cur)
        if state['counts']:
            return cmp(0)
        return None
    if kind == 'count_own_troops':
        return cmp(state['troops'])
    if kind == 'tax_rate':
        return cmp(state['tax'])
    if kind == 'money':
        return cmp(5000)
    return None


# ---------------------------------------------------------------- non-linear rule checks
def level_feasibility(m, allowed, local, routes, water3):
    """Highest house level that the allowed buildings can serve, and why higher levels fail."""
    open_routes = {n: r for n, r in routes.items() if not r['future']}
    sells = set(g for r in open_routes.values() for g, q in r['sells'].items() if q > 0)

    def can_make(g):
        ind = INDUSTRY.get(g)
        if g in SUPPLY_CHAIN:
            if ind not in allowed:
                return False
            return all(can_make(x) or x in sells for x in SUPPLY_CHAIN[g])
        if g not in local or ind not in allowed:
            return False
        if g in FARMS:
            return m['sites']['farm'] > 0
        if g in ROCK:
            return m['sites']['rock'] > 0
        if g == 'fish':
            return m['fish_pts'] > 0 and 'shipyard' in allowed and m['sites']['wharf'] > 0
        if g in ('clay', 'sand', 'timber'):
            return m['sites'][g] > 0
        return True
    avail = {g: can_make(g) or g in sells for g in FOODS + GOODS + ['clay', 'sand', 'stone', 'marble', 'timber', 'iron']}
    food_types = sum(avail[f] for f in FOODS)
    wine_types = (1 if can_make('wine') else 0) + sum(1 for r in open_routes.values() if r['sells'].get('wine', 0) > 0)
    gods = sum(1 for god in ['ceres', 'neptune', 'mercury', 'mars', 'venus']
               if {'small_temple_' + god, 'large_temple_' + god, 'grand_temple_' + god} & allowed)
    # building/figure.c:593-740: theaters, amphitheaters, arenas, colosseum and hippodrome create their own
    # performers; gladiator schools and lion houses only add the second show (days1)
    ent = 0
    if 'theater' in allowed: ent += 10
    if 'tavern' in allowed and avail['wine']: ent += 15 if any(avail[f] for f in FOODS) else 10
    if 'amphitheater' in allowed: ent += 15 if 'gladiator_school' in allowed else 10
    best_arena = 0
    if 'arena' in allowed: best_arena = 20 if 'lion_house' in allowed else 10
    if 'colosseum' in allowed:
        best_arena = max(best_arena, 25 if 'lion_house' in allowed else 15)
        ent += ENT_SOURCES['colosseum_done']
    ent += best_arena
    if 'hippodrome' in allowed: ent += ENT_SOURCES['hippodrome'] + ENT_SOURCES['hippodrome_done']
    if 'grand_temple_venus' in allowed: ent += ENT_SOURCES['venus_module']
    water = 1 if 'well' in allowed else 0
    if 'latrines' in allowed or ('fountain' in allowed and water3): water = 2
    if 'fountain' in allowed and water3: water = 3
    edu = ('school' in allowed) + ('library' in allowed) + (('academy' in allowed) if 'school' in allowed and 'library' in allowed else 0)
    health = ('doctor' in allowed) + ('hospital' in allowed)
    caps = {'food_types': food_types, 'wine_types': wine_types, 'gods': gods, 'entertainment': ent, 'water': water,
            'education': edu, 'health': health, 'barber': 'barber' in allowed,
            'bathhouse': 'bathhouse' in allowed and water3}
    ok_levels, block = [], {}
    for h in m['houses']:
        why = []
        if h['water'] > water: why.append(f"water {h['water']}>{water}")
        if h['religion'] > gods: why.append(f"gods {h['religion']}>{gods}")
        if h['ent'] > ent: why.append(f"entertainment {h['ent']}>{ent}")
        if h['edu'] > edu: why.append(f"education {h['edu']}>{edu}")
        if h['health'] > health: why.append(f"health {h['health']}>{health}")
        if h['barber'] and not caps['barber']: why.append('barber banned')
        if h['bath'] and not caps['bathhouse']: why.append('bathhouse impossible')
        if h['food'] > food_types: why.append(f"food types {h['food']}>{food_types}")
        for gd in GOODS:
            if h[gd] and not avail[gd]: why.append(f'no {gd}')
        if h['wine'] > 1 and wine_types < 2: why.append('second wine missing')
        if why:
            block[h['level']] = why
        else:
            ok_levels.append(h['level'])
    max_level = max([l for l in ok_levels if all(x in ok_levels for x in range(l + 1))] or [0])
    return max_level, block, caps, avail


def culture_plan(m, allowed, caps, goal):
    """Cheapest set of culture components (labour per 1000 people) that reaches the culture goal."""
    bm = m['bmodel']
    comps = {}
    if 'theater' in allowed:
        comps['theater'] = 1000 / COVERAGE['theater'] * bm['theater']['workers']
    if caps['gods'] == 5:
        comps['religion'] = 5 * 1000 / COVERAGE['small_temple'] * bm['small_temple_ceres']['workers']
    if 'school' in allowed:
        comps['school'] = 1000 * SCHOOL_AGE_SHARE / COVERAGE['school'] * bm['school']['workers']
    if 'academy' in allowed:
        comps['academy'] = 1000 * ACADEMY_AGE_SHARE / COVERAGE['academy'] * bm['academy']['workers']
    if 'library' in allowed:
        comps['library'] = 1000 / COVERAGE['library'] * bm['library']['workers']
    mons = [x for x in CULTURE_MONUMENTS if x in allowed]
    best = None
    names = list(comps)
    for mask in range(1 << len(names)):
        sel = [names[i] for i in range(len(names)) if mask >> i & 1]
        pts = sum(CULTURE_POINTS[s] for s in sel)
        need_mon = max(0, math.ceil((goal - pts) / MONUMENT_CULTURE_BONUS))
        if need_mon > len(mons):
            continue
        cost = sum(comps[s] for s in sel)
        if best is None or (need_mon, cost) < (best[2], best[1]):
            best = (sel, cost, need_mon)
    max_culture = sum(CULTURE_POINTS[s] for s in comps) + MONUMENT_CULTURE_BONUS * len(mons)
    return best, min(100, max_culture), mons


def favor_plan(m, rules, rank, requests_per_year_favor):
    """Highest favor that the city can hold each year from gifts, salary and requests."""
    salary_year = 12 * m['caesar_salary'] * SALARY_PCT_FOR_RANK[min(rank, 10)] / 100
    savings_income = salary_year + sum(f['per_year'] for f in rules['flows'] if f['kind'] == 'savings_add' and f['per_year'] > 0)
    gift_gain = 0
    for base, div, fav in GIFT:
        # steady state: savings S with yearly income I; a gift every year costs S/div + base% of caesar salary
        cost_fixed = base * m['caesar_salary'] / 100
        # S grows by I - (S/div + cost_fixed); steady S* = div*(I - cost_fixed); affordable if S* >= cost
        s_star = div * (savings_income - cost_fixed)
        if s_star > 0:
            gift_gain = max(gift_gain, fav)
    yearly = -2 + gift_gain + requests_per_year_favor
    return {'salary_year': salary_year, 'savings_income': savings_income, 'gift_gain': gift_gain, 'yearly_net': yearly}


# ---------------------------------------------------------------- MILP
def build_and_solve(m, allowed, local, prices, routes, rules, caps, avail, max_level, water3_tiles, culture, opts, A):
    bm, prod = m['bmodel'], m['prod']
    goal = m['goal']
    houses = [h for h in m['houses'] if h['level'] <= max_level]
    # house variants: (level, size, people, tiles)
    variants = []
    for h in houses:
        l = h['level']
        if l <= 9:
            variants.append((l, 1, h['people'], 1))
            variants.append((l, 2, 4 * h['people'], 4))
        else:
            size = 2 if l <= 13 else 3 if l <= 17 else 4
            variants.append((l, size, h['people'], size * size))
    hm = {h['level']: h for h in houses}
    V = []  # variable names
    def var(n):
        V.append(n)
        return len(V) - 1
    hv = [var(f'house_{l}_{s}') for (l, s, p, t) in variants]
    open_routes = {n: r for n, r in routes.items() if not r['future']}
    goods_all = sorted(set(FOODS + GOODS + list(SUPPLY_CHAIN) + ['clay', 'timber', 'olives', 'vines', 'iron', 'sand',
                                                                    'stone', 'marble', 'gold']))
    def producible(g):
        ind = INDUSTRY.get(g)
        if ind not in allowed:
            return False
        if g in SUPPLY_CHAIN:
            return True
        if g not in local:
            return False
        if g in FARMS and m['sites']['farm'] <= 0: return False
        if g in ROCK and m['sites']['rock'] <= 0: return False
        if g == 'fish' and (m['fish_pts'] <= 0 or 'shipyard' not in allowed or m['sites']['wharf'] <= 0): return False
        if g == 'clay' and m['sites']['clay'] <= 0: return False
        if g == 'sand' and m['sites']['sand'] <= 0: return False
        if g == 'timber' and m['sites']['timber'] <= 0: return False
        return True
    pv = {g: var(f'prod_{g}') for g in goods_all if producible(g) and g in prod}
    iv, xv, ov = {}, {}, {}
    for rname, ro in open_routes.items():
        ov[rname] = var(f'open_{rname}')
        for g, q in ro['sells'].items():
            if q > 0 and g in prices: iv[(rname, g)] = var(f'imp_{rname}_{g}')
        for g, q in ro['buys'].items():
            if q > 0 and g in prices: xv[(rname, g)] = var(f'exp_{rname}_{g}')
    forts = opts.get('forts', A['forts'])
    n = len(V)
    rows, lo, hi, names = [], [], [], []
    cur_name = ['?']
    def row(coefs, l, h, name=None):
        r = np.zeros(n)
        for i, c in coefs:
            r[i] += c
        rows.append(r); lo.append(l); hi.append(h); names.append(name or cur_name[0])
    INF = np.inf
    pop_terms = [(hv[i], p) for i, (l, s, p, t) in enumerate(variants)]
    pleb_terms = [(hv[i], p) for i, (l, s, p, t) in enumerate(variants) if l < FIRST_PATRICIAN_LEVEL]
    cur_name[0] = 'population'
    # 1. population goal (and at most pop_cap x goal: the player does not need more)
    if goal['pop']:
        row(pop_terms, goal['pop'], goal['pop'] * opts.get('pop_cap', 1.05))
    else:
        row(pop_terms, opts.get('min_pop', 3000), INF)  # ASSUMPTION: a city of 3000 when the map has no population goal
    cur_name[0] = 'tents<=30%'
    # prosperity rule: more than 30% of people in tents and shacks gives -1 per year (city/ratings.c:480)
    if opts.get('standard', True):
        row([(hv[i], p * (0.3 - (1 if l <= 3 else 0))) for i, (l, s, p, t) in enumerate(variants)], 0, INF)
    # 2. prosperity cap = average house prosperity >= goal
    cur_name[0] = 'prosperity cap'
    if goal['prosperity']:
        row([(hv[i], hm[l]['prosperity'] - goal['prosperity']) for i, (l, s, p, t) in enumerate(variants)], 0, INF)
    cur_name[0] = 'water3 zone'
    # 3. water level 3 houses limited to the fountain zone
    if water3_tiles is not None:
        row([(hv[i], t) for i, (l, s, p, t) in enumerate(variants) if hm[l]['water'] >= 3], -INF, water3_tiles)
    # --- labour coefficients
    def pc(level_filter, per_people, workers):
        return [(hv[i], p / per_people * workers) for i, (l, s, p, t) in enumerate(variants) if level_filter(hm[l])]
    labour = []
    labour += pc(lambda h: True, A['serve_market'], bm['market']['workers'])
    labour += pc(lambda h: True, A['serve_prefecture'], bm['prefecture']['workers'])
    labour += pc(lambda h: True, A['serve_engineer'], bm['engineers_post']['workers'])
    labour += pc(lambda h: True, A['serve_forum'], bm['forum']['workers'])
    labour += pc(lambda h: h['barber'], A['serve_barber'], bm['barber']['workers'])
    labour += pc(lambda h: h['bath'], A['serve_bathhouse'], bm['bathhouse']['workers'])
    labour += pc(lambda h: h['health'] >= 1, A['serve_doctor'], bm['doctor']['workers'])
    labour += pc(lambda h: h['health'] >= 2, COVERAGE['hospital'], bm['hospital']['workers'])
    labour += [(hv[i], t / A['serve_fountain_tiles'] * bm['fountain']['workers'])
               for i, (l, s, p, t) in enumerate(variants) if hm[l]['water'] >= 3]
    # entertainment: theaters for houses that need entertainment, more venues for high levels
    labour += pc(lambda h: h['ent'] >= 10, COVERAGE['theater'], bm['theater']['workers'] * (1 + A['performer_buildings_per_venue']))
    labour += pc(lambda h: h['ent'] >= 25, COVERAGE['amphitheater'], bm['amphitheater']['workers'] * (1 + A['performer_buildings_per_venue']))
    labour += pc(lambda h: h['ent'] >= 45, COVERAGE['arena'], bm['arena']['workers'] * (1 + A['performer_buildings_per_venue']))
    labour += pc(lambda h: h['edu'] >= 1, COVERAGE['school'] / SCHOOL_AGE_SHARE, bm['school']['workers'])
    labour += pc(lambda h: h['edu'] >= 2, COVERAGE['library'], bm['library']['workers'])
    labour += pc(lambda h: h['edu'] >= 3, COVERAGE['academy'] / ACADEMY_AGE_SHARE, bm['academy']['workers'])
    temple = 'large_temple' if opts.get('large_temples') else 'small_temple'
    labour += pc(lambda h: h['religion'] >= 1, COVERAGE[temple], bm[temple + '_ceres']['workers'])
    # culture goal coverage for the whole city (labour per 1000 people)
    sel, cult_cost, need_mon = culture if culture else ([], 0, 0)
    labour += [(hv[i], p / 1000 * cult_cost) for i, (l, s, p, t) in enumerate(variants)]
    # industry labour
    for g, i in pv.items():
        labour.append((i, prod[g]['workers'] / prod[g]['loads_year']))
    # storage and food distribution labour
    food_need = [(hv[i], p * FOOD_UNITS_PER_PERSON_MONTH * 12 / UNITS_PER_LOAD) for i, (l, s, p, t) in enumerate(variants) if hm[l]['food'] > 0]
    labour += [(j, c / A['serve_granary_food_loads'] * bm['granary']['workers']) for j, c in food_need]
    for (rname, g), i in list(iv.items()) + list(xv.items()):
        labour.append((i, bm['warehouse']['workers'] / A['serve_warehouse_loads']))
    fixed_labour = forts * 0 + (bm['barracks']['workers'] if forts else 0) + need_mon * 50
    cur_name[0] = 'labour'
    # 4. labour supply: 45% of plebeians
    row([(i, -c) for i, c in labour] + [(i, WORKER_SHARE_OF_PLEBS * p) for i, p in pleb_terms], fixed_labour, INF)
    cur_name[0] = 'goods balance'
    # 5. resource balances (loads per year)
    demand = collections.defaultdict(list)
    for i, (l, s, p, t) in enumerate(variants):
        h = hm[l]
        cons = 2 if s > 1 else 1
        for gd in GOODS:
            if h[gd]:
                demand[gd].append((hv[i], h[gd] * cons * 12 / UNITS_PER_LOAD))
    food_terms = [(hv[i], p * FOOD_UNITS_PER_PERSON_MONTH * 12 / UNITS_PER_LOAD) for i, (l, s, p, t) in enumerate(variants) if hm[l]['food'] > 0]
    # requests averaged per year over the mission (scheduled) + template requests from events
    req_year = collections.Counter()
    years = max([r['year'] for r in m['requests'] if r['year'] < 900] or [20])
    for r in m['requests']:
        if r['year'] < 900:
            req_year[r['res']] += r['amount'] / years
    for f in rules['flows']:
        if f['kind'].startswith('request:'):
            rid = int(f['kind'].split(':')[1] or 0)
            if 0 < rid <= len(m['requests']):
                rq = m['requests'][rid - 1]
                req_year[rq['res']] += rq['amount'] * f['per_year']
    stock = collections.Counter()
    for f in rules['flows']:
        if f['kind'].startswith('stock:'):
            ok = all(eval_cond(c, opts['state']) is not False for c in f['conds'])
            if ok and all(eval_cond(c, opts['state']) is True for c in f['conds']):
                stock[f['kind'][6:]] += f['per_year'] / 100 if abs(f['per_year']) > 500 else f['per_year']
    raw_use = collections.defaultdict(list)
    for g, raws in SUPPLY_CHAIN.items():
        if g in pv:
            for rr, u in raws.items():
                raw_use[rr].append((pv[g], u))
    weapons_need = forts * A['weapons_per_fort_year']
    food_vars = []
    unobtainable = []
    for g in goods_all:
        terms = []
        if g in pv: terms.append((pv[g], 1))
        terms += [(i, 1) for (rname, gg), i in iv.items() if gg == g]
        terms += [(i, -1) for (rname, gg), i in xv.items() if gg == g]
        terms += [(i, -c) for i, c in demand.get(g, [])]
        terms += [(i, -c) for i, c in raw_use.get(g, [])]
        need = req_year.get(g, 0) - stock.get(g, 0) + (weapons_need if g == 'weapons' else 0)
        if g in FOODS:
            food_vars.append(terms)
            continue
        supply = [t for t in terms if t[1] > 0]
        if not supply and need > 0:
            unobtainable.append(g)
            continue
        if not terms and need <= 0:
            continue
        row(terms, need, INF, 'balance ' + g)
    cur_name[0] = 'food'
    # food: total and per type (each available type must give an equal share for the highest food need)
    if m['rome_wheat']:
        food_terms = []  # Rome supplies wheat: houses get one food type for free (city/resource.c:543)
    total_food = [t for ts in food_vars for t in ts]
    row(total_food + [(i, -c) for i, c in food_terms], sum(req_year.get(f, 0) - stock.get(f, 0) for f in FOODS), INF)
    k = max([hm[l]['food'] for l in hm] or [1])
    food_names = [g for g in goods_all if g in FOODS]
    avail_food = [f for f, ts in zip(food_names, food_vars) if ts]
    if k >= 2:
        cap = {}
        for f in avail_food:
            c_ = sum(q for ro in open_routes.values() for gg, q in ro['sells'].items() if gg == f)
            if f in pv:
                if f in FARMS: c_ += m['sites']['farm'] * prod[f]['loads_year']
                elif f == 'fish': c_ += min(m['sites']['wharf'], m['fish_pts'] * A['wharves_per_fish_point']) * prod[f]['loads_year']
            cap[f] = c_
        chosen = opts.get('food_set') or sorted(avail_food, key=lambda f: -cap[f])[:k]
        chosen = [f for f in chosen if f in avail_food]
        # the j-th food type feeds only houses that need at least j types, at a share of 1/f of their food
        for j, f in enumerate(chosen, start=1):
            ts = food_vars[food_names.index(f)]
            need_terms = [(hv[i], p * FOOD_UNITS_PER_PERSON_MONTH * 12 / UNITS_PER_LOAD / hm[l]['food'])
                          for i, (l, s_, p, t) in enumerate(variants) if hm[l]['food'] >= j]
            row(ts + [(i, -c_) for i, c_ in need_terms], 0, INF, f'food type {j} ({f})')
    cur_name[0] = 'quota'
    # 6. quotas per route, linked to route opening
    if opts.get('no_trade'):
        for i in ov.values():
            row([(i, 1)], 0, 0)
    for (rname, g), i in iv.items():
        row([(i, 1), (ov[rname], -open_routes[rname]['sells'][g])], -INF, 0)
    for (rname, g), i in xv.items():
        row([(i, 1), (ov[rname], -open_routes[rname]['buys'][g])], -INF, 0)
    cur_name[0] = 'trader capacity'
    # 6b. trader throughput per route and direction (loads per year)
    trader_cap = {}
    for rname, ro in open_routes.items():
        k = TRADER[ro['kind']]
        potential = sum(ro['sells'].values()) + sum(ro['buys'].values())
        slots = max(1, min(MAX_TRADERS, potential // RESOURCES_TO_TRADER_RATIO + 1))
        trip = (2 * A['trade_walk_tiles'] / TILES_PER_DAY + A['trade_stop_days']) if ro['kind'] == 'LAND' else A['sea_trip_days']
        trips = min(DAYS_PER_YEAR / k['delay'], slots * DAYS_PER_YEAR / trip)
        trader_cap[rname] = trips * k['units']
        ex = [(i, 1) for (r_, g), i in xv.items() if r_ == rname]
        im = [(i, 1) for (r_, g), i in iv.items() if r_ == rname]
        if ex: row(ex, -INF, trader_cap[rname], 'trader export ' + rname)
        if im: row(im, -INF, trader_cap[rname], 'trader import ' + rname)
    cur_name[0] = 'land'
    # 7. land
    land = [(hv[i], t * (1 + A['road_overhead_houses'])) for i, (l, s, p, t) in enumerate(variants)]
    for g, i in pv.items():
        ind = INDUSTRY[g]
        land.append((i, bm[ind]['size'] ** 2 * (1 + A['road_overhead_buildings']) / prod[g]['loads_year']))
    svc_tiles_per_1000 = 60  # ASSUMPTION: services, storage and temples per 1000 people
    land += [(hv[i], p / 1000 * svc_tiles_per_1000) for i, (l, s, p, t) in enumerate(variants)]
    row(land, -INF, m['land'] - need_mon * 49)
    cur_name[0] = 'sites'
    # 8. resource sites
    def site(gs, cap, nm):
        ts = [(pv[g], 1 / prod[g]['loads_year']) for g in gs if g in pv]
        if ts: row(ts, -INF, cap, 'sites ' + nm)
    sites = m['sites']
    site([g for g in FARMS], sites['farm'], 'farm')
    site([g for g in ROCK], sites['rock'], 'rock')
    site(['clay'], sites['clay'], 'clay')
    site(['sand'], sites['sand'], 'sand')
    site(['timber'], sites['timber'], 'timber')
    if m['fish_pts'] > 0:
        site(['fish'], min(sites['wharf'], m['fish_pts'] * A['wharves_per_fish_point']), 'wharf')
    cur_name[0] = 'money'
    # 9. money (per year)
    tax = opts['tax']
    money = []
    if opts.get('forum_max') is not None:
        # a penalty event limits forums: tax only from the people that the allowed forums reach
        taxed = opts['forum_max'] * A['serve_forum']
        tv = var('taxed_people_share')
        n = len(V)
        rows[:] = [np.append(r_, 0) for r_ in rows]
        row([(tv, 1)] + [(hv[i], -p * dmoney(hm[l]['tax'])) for i, (l, s, p, t) in enumerate(variants)], -INF, 0, 'forum reach')
        row([(tv, 1)], -INF, taxed * max(dmoney(hm[l]['tax']) for l in hm), 'forum reach')
        money += [(tv, TAX_FACTOR * tax)]
    else:
        money += [(hv[i], TAX_FACTOR * tax * p * dmoney(hm[l]['tax'])) for i, (l, s, p, t) in enumerate(variants)]
    money += [(i, prices[g][1]) for (rname, g), i in xv.items()]
    money += [(i, -prices[g][0]) for (rname, g), i in iv.items()]
    wage = opts['wage']
    money += [(i, -c * wage / WAGE_DIVISOR) for i, c in labour]
    # temple levies (small temples for house religion) per person
    money += [(hv[i], -p / COVERAGE[temple] * dlevy(LEVY_MONTH[temple]) * 12) for i, (l, s, p, t) in enumerate(variants) if hm[l]['religion'] >= 1]
    for i in ov.values():
        money.append((i, 0))
    fixed_cost = (wage / WAGE_DIVISOR * fixed_labour + forts * dlevy(LEVY_MONTH['fort']) * 12 + need_mon * dlevy(LEVY_MONTH['grand_temple']) * 12
                  + opts['salary_year'] + opts['tribute'] - opts['event_money_year'] + req_year.get('denarii', 0))
    # route opening: amortised over the amortisation period
    amort = opts.get('amort_years', 10)
    money += [(ov[r], -open_routes[r]['cost'] / amort) for r in ov]
    row(money, fixed_cost, INF)
    cur_name[0] = 'budget'
    if opts.get('budget') is not None:
        # cumulative build cost: route permits + industry buildings + services per person (ASSUMPTION 0.9 dn/person)
        cap_terms = [(ov[r], open_routes[r]['cost']) for r in ov]
        cap_terms += [(i, bm[INDUSTRY[g]]['cost'] / prod[g]['loads_year']) for g, i in pv.items()]
        cap_terms += [(hv[i], p * 0.9) for i, (l, s_, p, t) in enumerate(variants)]
        row(cap_terms, -INF, opts['budget'], 'budget')
    # objective: maximise surplus (money row) minus a tiny house count term
    c = np.zeros(n)
    for i, v in money:
        c[i] -= v
    integrality = np.zeros(n)
    lb, ub = np.zeros(n), np.full(n, np.inf)
    for i in ov.values():
        integrality[i] = 1
        ub[i] = 1
    res = milp(c, constraints=LinearConstraint(np.array(rows), lo, hi), integrality=integrality, bounds=Bounds(lb, ub),
               options={'time_limit': 30})
    out = {'status': res.status, 'message': res.message}
    if res.x is None and opts.get('diagnose', True):
        # remove one constraint group at a time; a group whose removal makes the plan feasible is a blocker
        groups = sorted(set(nm.split(' ')[0] if nm.startswith(('trader', 'balance', 'sites')) else nm for nm in names) | set(nm for nm in names if nm.startswith('sites')) - {'population', 'prosperity cap'} - {'population'})
        blockers = []
        for gname in groups:
            keep = [j for j, nm in enumerate(names) if not (nm == gname or nm.startswith(gname + ' '))]
            r3 = milp(c, constraints=LinearConstraint(np.array(rows)[keep], np.array(lo)[keep], np.array(hi)[keep]),
                      integrality=integrality, bounds=Bounds(lb, ub), options={'time_limit': 20})
            if r3.x is not None:
                blockers.append(gname)
        out['blockers'] = blockers
    if res.x is None:
        # elastic solve: one slack per row, minimise total slack (scaled by row size)
        M = np.array(rows); k = len(rows)
        A2 = np.hstack([M, np.eye(k), -np.eye(k)])
        c2 = np.concatenate([np.zeros(n), np.ones(k), np.ones(k)])
        hard = {'population', 'prosperity cap', 'tents<=30%'}
        ubs = np.full(2 * k, np.inf)
        for j in range(k):
            if names[j] in hard:
                ubs[j] = ubs[k + j] = 0  # goals stay hard: find what else must change
            c2[n + j] = c2[n + k + j] = 1.0
        integ2 = np.concatenate([integrality, np.zeros(2 * k)])
        r2 = milp(c2, constraints=LinearConstraint(A2, lo, hi), integrality=integ2,
                  bounds=Bounds(np.concatenate([lb, np.zeros(2 * k)]), np.concatenate([ub, ubs])),
                  options={'time_limit': 30})
        if r2.x is not None:
            sl = r2.x[n:n + k] - r2.x[n + k:]
            viol = collections.defaultdict(float)
            for j in range(k):
                if abs(sl[j]) > 1e-3:
                    viol[names[j]] += sl[j]
            out['violations'] = {nm: round(v, 1) for nm, v in sorted(viol.items(), key=lambda kv: -abs(kv[1]))[:6]}
        return out
    x = res.x
    val = lambda terms: sum(x[i] * c_ for i, c_ in terms)
    out['pop'] = val(pop_terms)
    out['plebs'] = val(pleb_terms)
    out['workers_needed'] = val(labour) + fixed_labour
    out['workers_available'] = WORKER_SHARE_OF_PLEBS * out['plebs']
    out['surplus'] = val(money) - fixed_cost
    nh = sum(x[i] for i in hv)
    out['prosperity_cap'] = min(100, sum(x[hv[i]] * hm[l]['prosperity'] for i, (l, s, p, t) in enumerate(variants)) / nh) if nh else 0
    out['houses'] = {f'{l}x{s}': round(x[hv[i]], 1) for i, (l, s, p, t) in enumerate(variants) if x[hv[i]] > 0.05}
    out['prod'] = {g: round(x[i], 1) for g, i in pv.items() if x[i] > 0.05}
    out['imports'] = {f'{r}:{g}': round(x[i], 1) for (r, g), i in iv.items() if x[i] > 0.05}
    out['exports'] = {f'{r}:{g}': round(x[i], 1) for (r, g), i in xv.items() if x[i] > 0.05}
    out['open'] = [r for r, i in ov.items() if x[i] > 0.5]
    out['tax_income'] = val([(hv[i], TAX_FACTOR * tax * p * dmoney(hm[l]['tax'])) for i, (l, s, p, t) in enumerate(variants)])
    out['export_income'] = val([(i, prices[g][1]) for (rname, g), i in xv.items()])
    out['import_cost'] = val([(i, prices[g][0]) for (rname, g), i in iv.items()])
    out['land_used'] = val(land) + need_mon * 49
    out['land'] = m['land']
    out['fixed_cost'] = fixed_cost
    out['need_mon'] = need_mon
    P = out['pop']
    lvl_pop = collections.Counter()
    for i, (l, s_, p, t) in enumerate(variants):
        lvl_pop[l] += x[hv[i]] * p
    need = lambda f: sum(v for l, v in lvl_pop.items() if f(hm[l]))
    cnt = {}
    cnt['library'] = math.ceil(max(need(lambda h: h['edu'] >= 2), P if 'library' in sel else 0) / COVERAGE['library'])
    cnt['school'] = math.ceil(max(need(lambda h: h['edu'] >= 1), P if 'school' in sel else 0) * SCHOOL_AGE_SHARE / COVERAGE['school'])
    cnt['academy'] = math.ceil(max(need(lambda h: h['edu'] >= 3), P if 'academy' in sel else 0) * ACADEMY_AGE_SHARE / COVERAGE['academy'])
    cnt['theater'] = math.ceil(max(need(lambda h: h['ent'] >= 10), P if 'theater' in sel else 0) / COVERAGE['theater'])
    nt = math.ceil(max(need(lambda h: h['religion'] >= 1), 5 * P if 'religion' in sel else 0) / COVERAGE[temple])
    cnt['small_temples'] = 0 if opts.get('large_temples') else nt
    cnt['large_temples'] = nt if opts.get('large_temples') else 0
    cnt['forum'] = math.ceil(P / A['serve_forum']) if opts.get('forum_max') is None else opts['forum_max']
    for g, i in pv.items():
        cnt[INDUSTRY[g]] = math.ceil(x[i] / prod[g]['loads_year'])
    cnt['workshops'] = sum(cnt.get(INDUSTRY[g], 0) for g in SUPPLY_CHAIN)
    out['counts'] = cnt
    out['trader_cap'] = {r: round(v) for r, v in trader_cap.items()}
    out['unobtainable_requests'] = unobtainable
    out['food_set'] = opts.get('food_set')
    capex = sum(open_routes[r]['cost'] for r in out['open'])
    for b, k in cnt.items():
        if b in bm: capex += k * bm[b]['cost']
    capex += P / 1000 * 900  # ASSUMPTION: walker services, storage, roads and water per 1000 people
    capex += need_mon * 2500
    out['capex'] = capex
    return out


def water3_zone(m, allowed):
    """None = no limit (reservoirs work); a number = tiles inside the Neptune GT module 2 zone; 0 = no fountain water."""
    water_ok = m['coast'] > 0 or m['water_near3'] > 0
    if 'reservoir' in allowed and water_ok:
        return None
    if 'grand_temple_neptune' in allowed and 'fountain' in allowed:
        fr = FOUNTAIN_RADIUS - (1 if m['climate'] == 2 else 0) + 1
        side = 7 + 2 * (RESERVOIR_RADIUS + 2) + 2 * fr
        return side * side - 49
    return 0


def monument_materials(m, kind):
    """Material list of a monument after change_monument_resources events (map specific)."""
    phases = [dict(p) for p in MONUMENT_PHASES.get(kind, [])]
    for e in m['events']:
        for n, a in e['acts']:
            if n != 'change_monument_resources':
                continue
            mt = a.get('monument_type', '')
            if not (mt == kind or (kind == 'grand_temple' and mt.startswith('grand_temple')) or (kind == 'large_temple' and mt.startswith('large_temple'))):
                continue
            st = int(num(a.get('stage'))) - 1
            if 0 <= st < len(phases):
                phases[st][rn(a.get('resource'))] = num(a.get('amount'))
    tot = collections.Counter()
    for p in phases:
        tot.update(p)
    return dict(tot)


def material_cost(m, mats, prices, local_ok, sells):
    """Cost of a material list: import price if a route sells it, else local labour cost (0), else impossible."""
    cost, missing = 0, []
    for r, q in mats.items():
        if r == 'concrete':
            if 'sand' in local_ok or 'sand' in sells:
                cost += q * 0.5 * (prices['sand'][0] if 'sand' not in local_ok else 0)
                continue
            missing.append('concrete (no sand)')
            continue
        if r in local_ok:
            continue
        if r in sells and r in prices:
            cost += q * prices[r][0]
        else:
            missing.append(r)
    return cost, missing


def solve_best(m, allowed, local, prices, routes, rules, caps, avail, max_level, water3, culture, opts, A):
    import itertools
    k = max([h['food'] for h in m['houses'] if h['level'] <= max_level] or [1])
    foods = [f for f in FOODS if avail.get(f)]
    if k < 2 or len(foods) < 2:
        return build_and_solve(m, allowed, local, prices, routes, rules, caps, avail, max_level, water3, culture, opts, A)
    best = None
    for combo in itertools.combinations(foods, min(k, len(foods))):
        for order in set(itertools.permutations(combo)) if k <= 3 else [combo]:
            r = build_and_solve(m, allowed, local, prices, routes, rules, caps, avail, max_level, water3, culture,
                                dict(opts, food_set=list(order), diagnose=False), A)
            if r.get('surplus') is not None and (best is None or r['surplus'] > best['surplus']):
                best = r
    if best is None:
        best = build_and_solve(m, allowed, local, prices, routes, rules, caps, avail, max_level, water3, culture, opts, A)
    return best


def analyse(m, skip=(), opts_in=None, A=A):
    opts_in = opts_in or {}
    allowed, local, prices, routes, notes = apply_events(m, set(skip))
    allowed -= set(m.get('forbid_extra', []))
    rules = event_rules(m, set(skip))
    goal = m['goal']
    report = {'map': m['name'], 'goal': goal, 'skip': list(skip), 'funds': m['funds'], 'sites': m['sites'],
              'rome_wheat': m['rome_wheat'], 'stock': m['stock']}
    # water level 3 zone
    water_ok = m['coast'] > 0 or m['water_near3'] > 0
    reservoir = 'reservoir' in allowed and water_ok
    nep = 'grand_temple_neptune' in allowed
    fr = FOUNTAIN_RADIUS - (1 if m['climate'] == 2 else 0) + (1 if nep else 0)
    if reservoir:
        water3 = None
    elif nep and 'fountain' in allowed:
        side = 7 + 2 * (RESERVOIR_RADIUS + 2) + 2 * fr
        water3 = side * side - 49
        report['water3_note'] = f'reservoirs not usable; Neptune GT module 2 zone {side}x{side} tiles'
    else:
        water3 = 0
    max_level, block, caps, avail = level_feasibility(m, allowed, local, routes, water3 != 0)
    report['max_level'] = max_level
    report['blocked_above'] = block.get(max_level + 1)
    report['caps'] = caps
    hm = {h['level']: h for h in m['houses']}
    report['prosperity_ceiling'] = min(100, hm[max_level]['prosperity'])
    culture, max_culture, mons = culture_plan(m, allowed, caps, goal['culture'])
    report['max_culture'] = max_culture
    report['culture_plan'] = culture
    # tax rate
    tax = A['tax_rate']
    if rules['tax_cap'] is not None: tax = min(tax, rules['tax_cap'])
    if rules['tax_fixed'] is not None: tax = rules['tax_fixed']
    if 'tax' in opts_in: tax = opts_in['tax']
    report['tax'] = tax
    report['rome_wages'] = rules['rome_wages']
    wage = rules['rome_wages'] + 2
    # victory state for condition evaluation
    counts = collections.Counter()
    state = {'pop': goal['pop'], 'ratings': {'prosperity': goal['prosperity'], 'culture': goal['culture'], 'peace': goal['peace'],
             'favor': goal['favor']}, 'counts': counts, 'troops': A['forts'] * 16, 'tax': tax}
    # recurring money flows at victory
    ev_money = 0; ev_savings = 0; ev_favor = 0; unknown = []
    for f in rules['flows']:
        if f['kind'] not in ('money_add', 'savings_add', 'favor_add'):
            continue
        vals = [eval_cond(c, state) for c in f['conds']]
        if False in vals:
            continue
        if None in vals:
            unknown.append((f['id'], f['kind'], round(f['per_year']), f['conds']))
            continue
        if f['kind'] == 'money_add': ev_money += f['per_year']
        elif f['kind'] == 'savings_add': ev_savings += f['per_year']
        else: ev_favor += f['per_year']
    report['event_money_year'] = round(ev_money)
    report['event_favor_year'] = round(ev_favor, 1)
    report['unknown_flows'] = unknown
    forum_max = None
    for f in rules['flows']:
        big = (f['kind'] == 'money_add' and f['per_year'] <= -500) or (f['kind'] == 'favor_add' and f['per_year'] <= -5)
        if big:
            for c in f['conds']:
                mm = re.match(r'building_count_active check=gte value=(\d+) building=forum', c)
                if mm:
                    forum_max = int(mm.group(1)) - 1 if forum_max is None else min(forum_max, int(mm.group(1)) - 1)
    if forum_max is not None:
        report['forum_max'] = forum_max
    large_temples = False
    for f in rules['flows']:
        big = (f['kind'] == 'money_add' and f['per_year'] <= -500) or (f['kind'] == 'favor_add' and f['per_year'] <= -5)
        if big and any(re.match(r'building_count_active check=gte value=\d+ building=small_temples', c) for c in f['conds']):
            large_temples = True
    report['large_temples'] = large_temples
    fort_ok = bool({'fort_legionaries', 'fort_javelin', 'fort_mounted'} & allowed)
    forts = min(6, math.ceil(m['invasion_max'] / 40)) if fort_ok and m['invasion_max'] else 0
    state['troops'] = forts * 16
    rank = m['rank'] + max(0, sum(1 for e in m['events'] for n, a in e['acts'] if n == 'change_rank') * 0)
    salary_year = 12 * m['caesar_salary'] * SALARY_PCT_FOR_RANK[min(rank, 10)] / 100
    tribute = next(v for p, v in TRIBUTE_FIXED if goal['pop'] > p)
    opts = {'tax': tax, 'wage': wage, 'salary_year': salary_year, 'tribute': tribute, 'event_money_year': ev_money,
            'state': state, 'forts': opts_in.get('forts', forts), 'pop_cap': opts_in.get('pop_cap', 1.05),
            'standard': opts_in.get('standard', True), 'no_trade': opts_in.get('no_trade', False),
            'forum_max': forum_max, 'large_temples': large_temples}
    res = solve_best(m, allowed, local, prices, routes, rules, caps, avail, max_level, water3, culture, opts, A)
    if res.get('counts'):
        counts.update(res['counts'])
        ev2 = 0; unknown2 = []; fav2 = 0
        for f in rules['flows']:
            if f['kind'] not in ('money_add', 'savings_add', 'favor_add'):
                continue
            vals = [eval_cond(c, state) for c in f['conds']]
            if False in vals:
                continue
            if None in vals:
                unknown2.append((f['id'], f['kind'], round(f['per_year']), f['conds']))
                continue
            if f['kind'] == 'money_add': ev2 += f['per_year']
            elif f['kind'] == 'favor_add': fav2 += f['per_year']
        if ev2 != ev_money:
            opts['event_money_year'] = ev2
            res = solve_best(m, allowed, local, prices, routes, rules, caps, avail, max_level, water3, culture, opts, A)
        ev_money, ev_favor = ev2, fav2
        report['event_money_year'] = round(ev2); report['event_favor_year'] = round(fav2, 1); report['unknown_flows'] = unknown2
    report['lp'] = res
    report['forts'] = opts['forts']
    report['avoidable'] = sorted(state.get('avoidable', []))
    # lowest tax rate that keeps the budget positive
    if opts_in.get('extra', True):
        lo_t, hi_t = 0, int(opts['tax'])
        def ok(tx):
            return solve_best(m, allowed, local, prices, routes, rules, caps, avail, max_level, water3, culture,
                                   dict(opts, tax=tx), A).get('surplus') is not None
        if ok(hi_t):
            while lo_t < hi_t:
                mid = (lo_t + hi_t) // 2
                if ok(mid): hi_t = mid
                else: lo_t = mid + 1
            report['min_tax'] = hi_t
        else:
            report['min_tax'] = None
    # too-easy tests: no trade at all, and the tent mix
    if opts_in.get('extra', True):
        r_nt = solve_best(m, allowed, local, prices, routes, rules, caps, avail, max_level, water3, culture,
                               dict(opts, no_trade=True), A)
        report['surplus_no_trade'] = r_nt.get('surplus')
        r_tent = solve_best(m, allowed, local, prices, routes, rules, caps, avail, max_level, water3, culture,
                                 dict(opts, standard=False), A)
        report['surplus_tent_mix'] = r_tent.get('surplus')
    # favor
    req_favor = sum(r['favor'] for r in m['requests'] if r['year'] < 900) / max(1, max([r['year'] for r in m['requests'] if r['year'] < 900] or [20]))
    fp = favor_plan(m, rules, rank, req_favor)
    fp['yearly_net'] += ev_favor
    report['favor'] = fp
    report['favor_caps'] = rules['favor_caps']
    report['rating_set'] = rules['rating_set']
    # years to reach goals (lower bounds)
    years = {}
    if goal['peace']:
        years['peace'] = 2 + max(0, math.ceil((goal['peace'] - 4) / 5))
    if goal['prosperity']:
        bonus = 5 + 1 + 1 + 1 + 1 + (1 if 'hippodrome' in allowed else 0)
        years['prosperity'] = math.ceil(goal['prosperity'] / bonus)
    if goal['favor']:
        gap = goal['favor'] - m['start_favor']
        years['favor'] = math.ceil(gap / fp['yearly_net']) if fp['yearly_net'] > 0 else (0 if gap <= 0 else None)
    report['years_min'] = years
    # verdict
    problems = []
    if goal['prosperity'] and report['prosperity_ceiling'] < goal['prosperity']:
        problems.append(f"prosperity: best house level {max_level} gives {report['prosperity_ceiling']} < goal {goal['prosperity']}")
    if goal['culture'] and max_culture < goal['culture']:
        problems.append(f"culture: max {max_culture} < goal {goal['culture']}")
    if res.get('status') not in (0, 1) or res.get('x') is False:
        problems.append(f"economy LP: {res.get('message')}")
    if goal['favor'] and years.get('favor') is None:
        problems.append('favor: no yearly gain')
    for eid, cap, conds in rules['favor_caps']:
        if goal['favor'] > cap:
            note = f'favor capped at {cap} by {eid} while {" & ".join(conds)}'
            for c in conds:
                mm = re.match(r'money check=lte value=(\d+)', c)
                if mm and res.get('surplus'):
                    note += f' -> treasury above {mm.group(1)} needs about {int(mm.group(1)) / res["surplus"]:.1f} years of surplus'
            report.setdefault('requirements', []).append(note)
    # monuments the win needs: culture plan + grand temples named in favor caps
    need = []
    for eid, cap, conds in rules['favor_caps']:
        for c in conds:
            mm = re.search(r'building=(grand_temple_\w+|pantheon)', c)
            if mm and goal['favor'] > cap: need.append(mm.group(1))
    sel, cc, nmon = culture if culture else ([], 0, 0)
    need += [x for x in mons if x not in need][:max(0, nmon - len(need))]
    open_r = {n_: r_ for n_, r_ in routes.items() if not r_['future']}
    sells = set(g_ for r_ in open_r.values() for g_, q in r_['sells'].items() if q > 0)
    local_ok = set(g_ for g_ in local if INDUSTRY.get(g_) in allowed)
    if 'bricks' in [x for x in SUPPLY_CHAIN] and 'brickworks' in allowed and (('clay' in local_ok or 'clay' in sells) and ('sand' in local_ok or 'sand' in sells)):
        local_ok.add('bricks')
    mon_rep = []
    total_mat = 0
    for x in need:
        kind = 'grand_temple' if x.startswith('grand_temple') else x
        mats = monument_materials(m, kind)
        c_, miss = material_cost(m, mats, prices, local_ok, sells)
        total_mat += c_
        mon_rep.append({'monument': x, 'materials': mats, 'import_cost': round(c_), 'missing': miss})
        if miss:
            problems.append(f'{x} cannot be built: no source for {miss}')
    report['monuments'] = mon_rep
    report['monument_material_cost'] = round(total_mat)
    report['problems'] = problems
    return report


def build_up(m, skip, report, A=A):
    """Treasury over the build-up: the plan at 25/50/75/100% of the population goal with the conditions of each stage."""
    P = m['goal']['pop'] or 3000
    growth = A.get('growth_per_year', 1500)  # ASSUMPTION: people that immigration adds per year
    stages = []
    prev_capex, treasury, t_prev, s_prev = 0, m['funds'], 0, 0
    low, low_year = treasury, 0
    for f in (0.25, 0.5, 0.75, 1.0):
        year = f * P / growth
        mm = copy.deepcopy(m)
        mm['goal'] = dict(m['goal'], pop=int(f * P), prosperity=0 if f < 1 else m['goal']['prosperity'],
                          culture=0 if f < 1 else m['goal']['culture'])
        allowed, local, prices, routes, _ = apply_events(mm, set(skip), opts_year=int(year) + 1, timed_only=f < 1)
        allowed -= set(m.get('forbid_extra', []))
        rules = event_rules(mm, set(skip))
        water3 = water3_zone(m, allowed)
        ml, block, caps, avail = level_feasibility(mm, allowed, local, routes, water3 != 0)
        culture, _, _ = culture_plan(mm, allowed, caps, mm['goal']['culture'])
        tax = report['tax']
        state = {'pop': mm['goal']['pop'], 'ratings': {}, 'counts': collections.Counter(), 'troops': 0, 'tax': tax}
        opts = {'tax': tax, 'wage': report['rome_wages'] + 2, 'salary_year': report['lp'].get('fixed_cost', 0) * 0 + 12 * m['caesar_salary'] * SALARY_PCT_FOR_RANK[min(m['rank'], 10)] / 100,
                'tribute': 0 if f < 1 else next(v for p_, v in TRIBUTE_FIXED if P > p_), 'event_money_year': report['event_money_year'] if f == 1 else 0,
                'state': state, 'forts': report['forts'] if f == 1 else 0, 'diagnose': False}
        opts['budget'] = treasury + prev_capex + m.get('rescue_loan', 0)
        r = solve_best(mm, allowed, local, prices, routes, rules, caps, avail, ml, water3, culture, opts, A)
        if r.get('surplus') is None:
            opts['diagnose'] = True
            r = build_and_solve(mm, allowed, local, prices, routes, rules, caps, avail, ml, water3, culture, opts, A)
        sur = r.get('surplus')
        capex = r.get('capex', prev_capex)
        # treasury: spend new capex at the stage start, earn the mean surplus over the interval
        treasury -= max(0, capex - prev_capex)
        if treasury < low: low, low_year = treasury, t_prev
        if sur is not None:
            treasury += (s_prev + sur) / 2 * (year - t_prev)
        stages.append({'share': f, 'year': round(year, 1), 'max_level': ml, 'surplus': None if sur is None else round(sur),
                       'blockers': r.get('blockers'), 'budget': round(opts['budget']),
                       'capex': round(capex), 'treasury_end': round(treasury)})
        prev_capex, t_prev, s_prev = capex, year, sur or 0
    return {'stages': stages, 'lowest_treasury': round(low), 'lowest_at_year': round(low_year, 1)}


def relax(m, skip, A0):
    """If the LP is infeasible, find which single relaxation makes it feasible."""
    tries = {
        'tax +50%': dict(tax=None, scale_tax=1.5),
        'no forts': dict(forts=0),
        'service densities x2': dict(svc=2),
        'land x2': dict(land=2),
        'sites x2': dict(sites=2),
    }
    out = {}
    for name, t in tries.items():
        A1 = dict(A0)
        mm = copy.deepcopy(m)
        o = {}
        if 'forts' in t: o['forts'] = 0
        if t.get('svc'):
            for k in A1:
                if k.startswith('serve_'): A1[k] *= 2
        if t.get('land'): mm['land'] *= 2
        if t.get('sites'):
            for k in ['meadow', 'rock_sites', 'water_near3', 'trees']: mm[k] *= 2
            mm['fish_pts'] *= 2
        if t.get('scale_tax'): o['tax'] = A1['tax_rate'] * 1.5
        o['extra'] = False
        r = analyse(mm, skip, o, A1)
        out[name] = r['lp'].get('status')
    return out


def fmt(r):
    lp = r['lp']
    g = r['goal']
    lines = [f"## {r['map']}" + (f" (skip {','.join(r['skip'])})" if r['skip'] else '')]
    lines.append(f"goals pop {g['pop']} culture {g['culture']} prosperity {g['prosperity']} peace {g['peace']} favor {g['favor']}")
    lines.append(f"max house level {r['max_level']} (prosperity value {r['prosperity_ceiling']}); next level blocked by: {r['blocked_above']}")
    lines.append(f"caps: {r['caps']}" + (f"; {r['water3_note']}" if r.get('water3_note') else ''))
    lines.append(f"culture max {r['max_culture']}, plan {r['culture_plan']}")
    lines.append(f"tax {r['tax']}%, Rome wage {r['rome_wages']}, event money {r['event_money_year']}/yr, event favor {r['event_favor_year']}/yr")
    if lp.get('surplus') is not None:
        lines.append(f"LP: surplus {lp['surplus']:.0f}/yr | tax {lp['tax_income']:.0f} exports {lp['export_income']:.0f} imports {lp['import_cost']:.0f} fixed {lp['fixed_cost']:.0f}")
        lines.append(f"    pop {lp['pop']:.0f} plebs {lp['plebs']:.0f} workers {lp['workers_needed']:.0f}/{lp['workers_available']:.0f} land {lp['land_used']:.0f}/{lp['land']:.0f} prosperity cap {lp['prosperity_cap']:.0f}")
        lines.append(f"    houses {lp['houses']}")
        lines.append(f"    prod {lp['prod']}")
        lines.append(f"    exports {lp['exports']}")
        lines.append(f"    imports {lp['imports']}")
        lines.append(f"    routes opened {lp['open']}")
    else:
        lines.append(f"LP: infeasible; single blockers {lp.get('blockers')}; minimal slack {lp.get('violations')}")
    if lp.get('capex') is not None:
        lines.append(f"    build cost {lp['capex']:.0f} vs start funds {r['funds']} -> payback {lp['capex'] / lp['surplus'] if lp['surplus'] > 0 else float('inf'):.1f} yr; lowest tax that balances: {r.get('min_tax')}%")
    if r.get('avoidable'): lines.append(f"    drains avoided by: {r['avoidable']}")
    if lp.get('unobtainable_requests'): lines.append(f"    requests that the city cannot fill (favor loss): {lp['unobtainable_requests']}")
    if lp.get('food_set'): lines.append(f"    food types used (in order): {lp['food_set']}")
    if r.get('monuments'): lines.append(f"    monuments needed: {r['monuments']}")
    lines.append(f"    sites (packed): {r.get('sites')}; Rome wheat {r.get('rome_wheat')}; start stock {r.get('stock')}")
    lines.append(f"forts assumed {r['forts']}; surplus with no trade: {r.get('surplus_no_trade')}; surplus with the tent mix: {r.get('surplus_tent_mix')}")
    lines.append(f"favor: {r['favor']}; caps {r['favor_caps']}")
    if r['rating_set']: lines.append(f"rating set by events: {r['rating_set']}")
    lines.append(f"years (lower bound): {r['years_min']}")
    if r['unknown_flows']: lines.append(f"flows with quest conditions (not applied): {r['unknown_flows'][:8]}")
    for q in r.get('requirements', []): lines.append('REQUIREMENT: ' + q)
    if r.get('forum_max') is not None: lines.append(f"forums limited to {r['forum_max']} by a penalty event (tax only within their reach)")
    lines.append('PROBLEMS: ' + ('; '.join(r['problems']) if r['problems'] else 'none'))
    return '\n'.join(lines)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('dumpdir')
    ap.add_argument('maps', nargs='*')
    ap.add_argument('--skip', default='')
    ap.add_argument('--json', default='')
    ap.add_argument('--worst', action='store_true', help='worst-case assumptions')
    ap.add_argument('--difficulty', default='hard', choices=list(DIFFICULTY))
    ap.add_argument('--no-buildup', action='store_true')
    ap.add_argument('--forbid', default='', help='buildings that a penalty event makes unusable')
    args = ap.parse_args()
    dirs = args.maps or sorted(d for d in os.listdir(args.dumpdir) if os.path.isdir(os.path.join(args.dumpdir, d)))
    saves = {d[:-5] for d in dirs if d.endswith('_SAVE')}
    dirs = [d for d in dirs if d not in saves]
    DIFF['level'] = args.difficulty
    if args.worst:
        for k in list(A):
            if k.startswith('serve_'): A[k] *= 0.5
        A.update(trade_walk_tiles=60, trade_stop_days=8, sea_trip_days=120, growth_per_year=800)
        for k in ('meadow_tiles_per_farm', 'rock_sites_per_quarry', 'water_tiles_per_claypit', 'tree_tiles_per_timber_yard'):
            A[k] *= 2
        A['wharves_per_fish_point'] = 1.5
    summary = []
    for d in dirs:
        m = load_map(os.path.join(args.dumpdir, d))
        m['forbid_extra'] = [x for x in args.forbid.split(',') if x]
        r = analyse(m, [s for s in args.skip.split(',') if s])
        lp = r['lp']
        rec = {'map': d, 'goal': r['goal'], 'max_level': r['max_level'], 'prosperity_ceiling': r['prosperity_ceiling'],
               'max_culture': r['max_culture'], 'surplus': lp.get('surplus'), 'tax_income': lp.get('tax_income'),
               'export_income': lp.get('export_income'), 'import_cost': lp.get('import_cost'), 'workers': lp.get('workers_needed'),
               'workers_available': lp.get('workers_available'), 'land_used': lp.get('land_used'), 'land': lp.get('land'),
               'capex': lp.get('capex'), 'min_tax': r.get('min_tax'), 'no_trade': r.get('surplus_no_trade'),
               'tent_mix': r.get('surplus_tent_mix'), 'blockers': lp.get('blockers'), 'favor': r['favor'],
               'favor_caps': r['favor_caps'], 'requirements': r.get('requirements', []), 'problems': r['problems'],
               'years': r['years_min'], 'tax': r['tax'], 'forts': r['forts'], 'forum_max': r.get('forum_max'),
               'trader_cap': lp.get('trader_cap'), 'monuments': r.get('monuments'), 'sites': m['sites'], 'exports': lp.get('exports'), 'imports': lp.get('imports'),
               'houses': lp.get('houses'), 'unobtainable': lp.get('unobtainable_requests'), 'event_money': r['event_money_year']}
        summary.append(rec)
        print(fmt(r))
        if args.no_buildup:
            print(); continue
        bu = build_up(m, [s for s in args.skip.split(',') if s], r)
        rec['buildup'] = bu
        print('build-up:', ' | '.join(f"{int(st['share']*100)}% y{st['year']} lvl{st['max_level']} budget {st['budget']} surplus {st['surplus']} capex {st['capex']} treasury {st['treasury_end']}" + (f" BLOCKED by {st['blockers']}" if st['surplus'] is None else '') for st in bu['stages']),
              f"| lowest treasury {bu['lowest_treasury']} at year {bu['lowest_at_year']}")
        print()
    if args.json:
        json.dump(summary, open(args.json, 'w'), default=lambda o: float(o) if hasattr(o, '__float__') else str(o), indent=1)
