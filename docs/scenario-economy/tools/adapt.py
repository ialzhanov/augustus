import re,glob,os,sys,collections
os.chdir(sys.argv[1])
dirs=[d.rstrip('/') for d in sorted(glob.glob('*/'))]
saves={d[:-5] for d in dirs if d.endswith('_SAVE')}
dirs=[d for d in dirs if d not in saves]
DEF={}
for kv in re.search(r'^PRICES\(default\) buy/sell: (.*)$',open('Aquileia/dump.txt').read(),re.M).group(1).split():
    k,v=kv.split('='); b,s=v.split('/'); DEF[k.split('|')[0]]=int(s) or 1
NATIVE={'native_hut','native_crops','native_meeting','native_hut_alt','native_watchtower','native_monument','native_decoration','native_well','native_large_hut_alt','native_hut_alt_2'}
def num(v):
    m=re.match(r'\{?(-?\d+)',v or ''); return int(m.group(1)) if m else 0
def attrs(s): return dict(re.findall(r'(\w+)=(\{[^}]*\}|\S+)',s))
rows=[]
for d in dirs:
    t=open(d+'/dump.txt').read()
    lim={}
    for m in re.finditer(r'^  route (\d+) (.+?) type=\d (?:LAND|SEA) open=\d cost=\d+ \| sells:(.*?) \| buys:(.*)$',t,re.M):
        rid,name,se,bu=m.groups()
        for side,s_ in (('sells',se),('buys',bu)):
            for x in s_.split(): lim[(name,side,x.split('(')[0].split('|')[0])]=int(x.split('(')[1][:-1])
        lim[('id',int(rid))]=name
    c=collections.Counter(); ex=collections.defaultdict(list)
    for m in re.finditer(r'^  dem year\+(\d+) month=\d+ (\S+) route=(\d+) amount=(-?\d+) buys=(\d)',t,re.M):
        y,r,rid,a,b=m.groups(); r=r.split('|')[0]; name=lim.get(('id',int(rid)))
        old=lim.get((name,'buys' if b=='1' else 'sells',r),0)
        if int(a)<old: c['quota_cut']+=1; ex['quota_cut'].append(f'y{y} {name} {r} {old}->{a}')
    for m in re.finditer(r'^  price year\+(\d+) month=\d+ (\S+) ([+-])(\d+)',t,re.M):
        y,r,sg,a=m.groups(); r=r.split('|')[0]
        if int(a)>=0.2*DEF.get(r,1): c['big_price_step']+=1; ex['big_price_step'].append(f'y{y} {r} {sg}{a}')
    for l in open(d+'/compact.txt'):
        if not l.startswith('E'): continue
        m=re.match(r'E\S+ (?:\[[^\]]*\] )?(rep\S+ \S+ )?IF (.*?) => (.*)$',l.strip())
        if not m: continue
        cond=m.group(2).strip(); start=cond=='always' or re.fullmatch(r'time check=(gte|eq) value=\{?[01](,[01]\})?',cond)
        if start: continue
        eid=l.split()[0]
        for a in m.group(3).split(' ; '):
            n=a.split(' ')[0]; A=attrs(a)
            if n=='trade_route_amount':
                old=lim.get((A.get('target_city'),'buys' if A.get('buying')=='true' else 'sells',A.get('resource','').split('|')[0]),0)
                if num(A.get('amount'))<old: c['quota_cut']+=1; ex['quota_cut'].append(f"{eid} {A.get('target_city')} {A.get('resource')} {old}->{num(A.get('amount'))}")
            elif n=='change_allowed_buildings' and A.get('allowed')=='false': c['reban']+=1; ex['reban'].append(f"{eid} {A.get('building')}")
            elif n=='change_resource_produced' and A.get('produced')=='false': c['resource_lost']+=1; ex['resource_lost'].append(f"{eid} {A.get('resource')}")
            elif n=='building_force_collapse' and A.get('building') not in NATIVE: c['collapse_player']+=1; ex['collapse_player'].append(f"{eid} {A.get('building')}")
            elif n=='change_terrain': c['terrain']+=1; ex['terrain'].append(eid)
            elif n in('trade_price_set','trade_price_adjust','trade_set_buy_price_only','trade_set_sell_price_only'): c['price_event']+=1; ex['price_event'].append(f"{eid} {A.get('resource')}")
            elif n in('trade_problems_land','trade_problems_sea'): c['trade_problem']+=1; ex['trade_problem'].append(eid)
            elif n=='change_trade_route_open_price': c['permit_change']+=1
            elif n in('change_model_data','change_production_rate','change_house_model_data'): c['model']+=1; ex['model'].append(f"{eid} {A.get('building') or A.get('resource')}")
            elif n=='empire_map_convert_future_trade_city': c['new_partner']+=1
            elif n=='change_resource_produced' and A.get('produced')=='true': c['resource_gain']+=1
    rows.append((d,c,ex))
keys=['quota_cut','big_price_step','price_event','trade_problem','reban','resource_lost','collapse_player','terrain','model','new_partner','resource_gain','permit_change']
w={'quota_cut':2,'big_price_step':1,'price_event':1,'trade_problem':1,'reban':2,'resource_lost':3,'collapse_player':2,'terrain':2,'model':1,'new_partner':1,'resource_gain':1,'permit_change':1}
rows.sort(key=lambda r:-sum(r[1][k]*w[k] for k in keys))
print('map | '+' | '.join(keys)+' | score')
for d,c,ex in rows:
    print(f"{d[:24]:24s} | "+' | '.join(str(c[k]) for k in keys)+f" | {sum(c[k]*w[k] for k in keys)}")
print()
for d,c,ex in rows:
    print('##',d)
    for k in ('quota_cut','reban','resource_lost','collapse_player','terrain','model','big_price_step'):
        if ex[k]: print('  ',k,':',', '.join(ex[k][:14]))
