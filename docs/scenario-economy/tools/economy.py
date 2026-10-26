import re,glob,os,sys,collections
os.chdir(sys.argv[1])
DEF={}
for kv in re.search(r'^PRICES\(default\) buy/sell: (.*)$',open('Aquileia/dump.txt').read(),re.M).group(1).split():
    k,v=kv.split('='); b,s=v.split('/'); DEF[k.split('|')[0]]=[int(b),int(s)]
RAW_OF={'pottery':['clay'],'furniture':['timber'],'oil':['olives'],'wine':['vines'],'weapons':['iron'],'bricks':['clay','sand']}
def num(v):
    m=re.match(r'\{?(-?\d+)',v or ''); return int(m.group(1)) if m else 0
def attrs(s): return dict(re.findall(r'(\w+)=(\{[^}]*\}|\S+)',s))
dirs=[d.rstrip('/') for d in sorted(glob.glob('*/'))]
saves={d[:-5] for d in dirs if d.endswith('_SAVE')}
dirs=[d for d in dirs if d not in saves]
out=[]; MARG={}; WF={}
for d in dirs:
    t=open(d+'/dump.txt').read()
    prices={k:list(v) for k,v in DEF.items()}
    if '_SAVE' in d:
        for kv in re.search(r'^PRICES\(save\) buy/sell: (.*)$',t,re.M).group(1).split():
            k,v=kv.split('='); b,s=v.split('/'); prices[k.split('|')[0]]=[int(b),int(s)]
    routes={}
    for m in re.finditer(r'^  route (\d+) (.+?) type=(\d) (LAND|SEA) open=\d cost=(\d+) \| sells:(.*?) \| buys:(.*)$',t,re.M):
        rid,name,typ,kind,cost,sells,buys=m.groups()
        p=lambda s:{x.split('(')[0].split('|')[0]:int(x.split('(')[1][:-1]) for x in s.split()}
        routes[name]=dict(id=int(rid),type=int(typ),kind=kind,cost=int(cost),sells=p(sells),buys=p(buys))
    local=set(x.split('|')[0] for x in re.search(r'^LOCAL can_produce:(.*)$',t,re.M).group(1).split())
    importable=set(r for ro in routes.values() for r in ro['sells'])
    ev=[l for l in open(d+'/compact.txt') if l.startswith('E')]
    def apply_price(a,acts):
        r=a.get('resource','').split('|')[0]
        if r not in prices: return
        if acts=='trade_price_set':
            cur=prices[r][0 if a.get('set_buy_price')=='true' else 1]; adj=num(a['amount'])-cur
            if prices[r][1]+adj<=0 and adj<0: prices[r]=[2,0]
            else: prices[r][0]+=adj; prices[r][1]+=adj
        elif acts=='trade_price_adjust':
            adj=num(a.get('adjustment') or a.get('amount')); prices[r][0]+=adj; prices[r][1]+=adj
        elif acts=='trade_set_buy_price_only': prices[r][0]=num(a['amount'])
        elif acts=='trade_set_sell_price_only': prices[r][1]=num(a['amount'])
    start_events=0
    if True:
        for l in ev:
            m=re.match(r'E\S+ (?:\[[^\]]*\] )?(rep\S+ \S+ )?IF (.*?) => (.*)$',l.strip())
            if not m or m.group(1): continue
            if not (m.group(2).strip()=='always' or re.fullmatch(r'time check=(gte|eq) value=\{?[01](,[01]\})?',m.group(2).strip())): continue
            for a in m.group(3).split(' ; '):
                n=a.split(' ')[0]
                if n.startswith('trade_'): apply_price(attrs(a),n); start_events+=1
    # export capacity at start prices
    def cap(rs):
        tot=0; loc=0
        for ro in rs.values():
            for r,lim in ro['buys'].items():
                v=lim*prices.get(r,[0,0])[1]; tot+=v
                if r in local or any(x in local or x in importable for x in RAW_OF.get(r,['-'])): loc+=v
        return tot,loc
    tot,loc=cap(routes)
    # all route-amount increases from events / demand changes (ceiling)
    import copy
    r2=copy.deepcopy(routes); byid={ro['id']:n for n,ro in r2.items()}
    for l in ev:
        for a in re.findall(r'trade_route_amount ([^;]*)',l):
            A=attrs(a); n=A.get('target_city'); r=A.get('resource','').split('|')[0]
            if n in r2: r2[n]['buys' if A.get('buying')=='true' else 'sells'][r]=max(num(A['amount']),0)
        for a in re.findall(r'trade_route_add_new_resource ([^;]*)',l):
            A=attrs(a); n=A.get('target_city'); r=A.get('resource','').split('|')[0]
            if n in r2: r2[n]['buys' if A.get('add_as_buying')=='true' else 'sells'][r]=num(A['amount'])
    bad_dem=[]
    for m in re.finditer(r'^  dem year\+\d+ month=\d+ (\S+) route=(\d+) amount=(-?\d+) buys=(\d)',t,re.M):
        r,rid,amt,b=m.group(1).split('|')[0],int(m.group(2)),int(m.group(3)),m.group(4)
        if rid not in byid: bad_dem.append(f'route{rid}:{r}'); continue
        r2[byid[rid]]['buys' if b=='1' else 'sells'][r]=amt
    tot2,loc2=cap(r2)
    costs=sum(ro['cost'] for ro in routes.values() if ro['type']!=1)
    pop=num(re.search(r'WIN pop=\d:(\d+)',t).group(1))
    funds=num(re.search(r'funds=(\d+)',t).group(1))
    req_den=sum(int(m.group(1)) for m in re.finditer(r'^  req .* denarii (\d+)-',t,re.M) if not re.search(r'year\+99\d',m.group(0)))
    reqs=len(re.findall(r'^  req ',t,re.M))
    np=len(re.findall(r'^  price ',t,re.M)); nev=sum(l.count('trade_price')+l.count('trade_set_') for l in ev)
    spread={r:(prices[r][0]-prices[r][1]) for r in prices}
    changed={r:f"{prices[r][0]}/{prices[r][1]}" for r in prices if prices[r]!=DEF[r]}
    nroutes=len(routes)
    rome=[n for n in routes if n.startswith('Rome')]
    mg=[]
    for prod,raws in RAW_OF.items():
        rc=sum(prices[r][0] for r in raws)/len(raws)
        loc_raw=all(r in local for r in raws)
        mg.append(f"{prod}={prices[prod][1]}-{int(rc)}{'(raw local)' if loc_raw else ''}")
    MARG[d]=' '.join(mg)
    buyers=collections.defaultdict(int)
    for ro in r2.values():
        for r,lim in ro['buys'].items(): buyers[r]+=lim
    wf=[]
    for r,(b_,s_) in prices.items():
        if r not in DEF or DEF[r][1]==0: continue
        prod = r in local or any(x in local or x in importable for x in RAW_OF.get(r,['-']))
        if buyers[r] and prod and s_>=1.5*DEF[r][1]: wf.append(f"{r}: sell {s_} vs default {DEF[r][1]}, buyers {buyers[r]}/yr")
        if s_<=0: wf.append(f"{r}: price {b_}/{s_}")
    WF[d]=wf
    out.append((d,pop,funds,nroutes,costs,tot,loc,tot2,loc2,start_events,np,nev,reqs,req_den,bad_dem,changed))
print('map pop funds routes open_cost exp_cap_start(local) exp_cap_max(local) per_cap_start start_price_actions sched_price_changes price_actions_in_events requests req_denarii')
for o in out:
    d,pop,funds,nr,costs,tot,loc,tot2,loc2,se,np,nev,reqs,rd,bd,ch=o
    print(f"{d[:22]:22s} pop={pop:<6} funds={funds:<6} routes={nr:<2} opencost={costs:<6} exp={tot}({loc}) max={tot2}({loc2}) perCap={loc/pop if pop else 0:.2f}->{loc2/pop if pop else 0:.2f} startPx={se} sched={np} evPx={nev} req={reqs} reqDen={rd}" + (f" BAD_DEMAND={bd}" if bd else ''))
    print('   start prices changed:', ' '.join(f'{k}={v}' for k,v in ch.items()))
    print('   margins sell(product)-buy(raw):', MARG[d])
    if WF[d]: print('   EXPORT WINDFALL / ZERO:', '; '.join(WF[d]))
