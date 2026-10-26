"""Timeline of trade conditions per map: which export earns most per worker each year."""
import re,glob,os,sys,collections,copy
os.chdir(sys.argv[1])
IND={'wheat':'wheat_farm','vegetables':'vegetable_farm','fruit':'fruit_farm','meat':'pig_farm','fish':'wharf','clay':'clay_pit','timber':'timber_yard','olives':'olive_farm','vines':'vines_farm','iron':'iron_mine','marble':'marble_quarry','gold':'gold_mine','sand':'sand_pit','stone':'stone_quarry','pottery':'pottery_workshop','furniture':'furniture_workshop','oil':'oil_workshop','wine':'wine_workshop','weapons':'weapons_workshop','bricks':'brickworks'}
FARMS={'wheat','vegetables','fruit','meat','olives','vines'}; ROCK={'iron','marble','gold','stone'}
CHAIN={'pottery':{'clay':1},'furniture':{'timber':1},'oil':{'olives':1},'wine':{'vines':1},'weapons':{'iron':1},'bricks':{'clay':.5,'sand':.5}}
def num(v):
    m=re.match(r'\{?(-?\d+)',v or ''); return int(m.group(1)) if m else 0
def attrs(s): return dict(re.findall(r'(\w+)=(\{[^}]*\}|\S+)',s))
def rn(r): return (r or '').split('|')[0]
dirs=[d.rstrip('/') for d in sorted(glob.glob('*/'))]
saves={d[:-5] for d in dirs if d.endswith('_SAVE')}
dirs=[d for d in dirs if d not in saves]
OUT=[]
for d in dirs:
    t=open(d+'/dump.txt').read()
    tag='(save)' if '_SAVE' in d else '(default)'
    P={}
    for kv in re.search(r'^PRICES\(\w+\) buy/sell: (.*)$',t,re.M).group(1).split():
        k,v=kv.split('='); b,s=v.split('/'); P[rn(k)]=[int(b),int(s)]
    PROD={}
    for kv in re.search(r'^PRODUCTION \S+ (.*)$',t,re.M).group(1).split():
        k,v=kv.split('='); ind,pm,w=map(int,v.split(':')); PROD[rn(k)]=(pm*12/100,w)
    local=set(rn(x) for x in re.search(r'^LOCAL can_produce:(.*)$',t,re.M).group(1).split())
    routes={}
    for m in re.finditer(r'^  route (\d+) (.+?) type=(\d) (?:LAND|SEA) open=\d cost=\d+ \| sells:(.*?) \| buys:(.*)$',t,re.M):
        rid,name,typ,se,bu=m.groups()
        p=lambda s:{rn(x.split('(')[0]):int(x.split('(')[1][:-1]) for x in s.split()}
        routes[name]=dict(id=int(rid),active=typ!='3',sells=p(se),buys=p(bu))
    byid={r['id']:n for n,r in routes.items()}
    forb=set(re.search(r'^FORBIDDEN BUILDINGS:(.*)$',t,re.M).group(1).split())
    meadow=int(re.search(r'connected: meadow=(\d+)',t).group(1)); rocks=int(re.search(r'rock_edge_sites=(\d+)',t).group(1))
    fishpts=int(re.search(r'fish_pts=(\d+)',t).group(1))
    def terrain_ok(g):
        if g in FARMS: return meadow>0
        if g in ROCK: return rocks>0
        if g=='fish': return fishpts>0
        return True
    timed=collections.defaultdict(list)   # month -> list of (kind,args)
    cond=[]                               # player-paced trade changes
    for m in re.finditer(r'^  dem year\+(\d+) month=(\d+) (\S+) route=(\d+) amount=(-?\d+) buys=(\d)',t,re.M):
        y,mo,r,rid,a,b=m.groups()
        if int(rid) in byid: timed[int(y)*12+int(mo)].append(('quota',byid[int(rid)],'buys' if b=='1' else 'sells',rn(r),int(a)))
    for m in re.finditer(r'^  price year\+(\d+) month=(\d+) (\S+) ([+-])(\d+)',t,re.M):
        y,mo,r,sg,a=m.groups(); timed[int(y)*12+int(mo)].append(('shift',rn(r),int(a)*(1 if sg=='+' else -1)))
    for l in open(d+'/compact.txt'):
        if not l.startswith('E'): continue
        m=re.match(r'E\S+ (?:\[[^\]]*\] )?(rep\S+ \S+ )?IF (.*?) => (.*)$',l.strip())
        if not m: continue
        c=m.group(2).strip(); acts=[]
        for a in m.group(3).split(' ; '):
            n=a.split(' ')[0]; A=attrs(a)
            if n=='trade_route_amount' and A.get('target_city') in routes: acts.append(('quota',A['target_city'],'buys' if A.get('buying')=='true' else 'sells',rn(A.get('resource')),max(num(A.get('amount')),0)))
            elif n=='trade_route_add_new_resource' and A.get('target_city') in routes: acts.append(('quota',A['target_city'],'buys' if A.get('add_as_buying')=='true' else 'sells',rn(A.get('resource')),num(A.get('amount'))))
            elif n=='trade_price_set': acts.append(('set','buy' if A.get('set_buy_price')=='true' else 'sell',rn(A.get('resource')),num(A.get('amount'))))
            elif n=='trade_price_adjust': acts.append(('shift',rn(A.get('resource')),num(A.get('amount') or A.get('adjustment'))))
            elif n=='trade_set_buy_price_only': acts.append(('only',0,rn(A.get('resource')),num(A.get('amount'))))
            elif n=='trade_set_sell_price_only': acts.append(('only',1,rn(A.get('resource')),num(A.get('amount'))))
            elif n=='empire_map_convert_future_trade_city' and A.get('target_city') in routes: acts.append(('open',A['target_city']))
            elif n=='change_resource_produced': acts.append(('local',rn(A.get('resource')),A.get('produced')=='true'))
            elif n=='change_allowed_buildings': acts.append(('allow',A.get('building'),A.get('allowed')=='true'))
        if not acts: continue
        tm=re.fullmatch(r'time check=(?:gte|eq|gt) value=\{?(\d+)(?:,\d+\})?',c)
        if re.fullmatch(r'stats_prosperity check=gte value=1[05]',c): timed[24]+=acts
        elif c=='always': timed[0]+=acts
        elif tm and not m.group(1): timed[int(tm.group(1))]+=acts
        else: cond.append((l.split()[0],acts))
    def apply(a):
        k=a[0]
        if k=='quota': routes[a[1]][a[2]][a[3]]=a[4]
        elif k=='shift' and a[1] in P:
            if a[2]<0 and P[a[1]][1]<=-a[2]: P[a[1]]=[2,0]
            else: P[a[1]][0]+=a[2]; P[a[1]][1]+=a[2]
        elif k=='set' and a[2] in P:
            adj=a[3]-P[a[2]][0 if a[1]=='buy' else 1]
            apply(('shift',a[2],adj))
        elif k=='only' and a[2] in P: P[a[2]][a[1]]=max(a[3],1)
        elif k=='open': routes[a[1]]['active']=True
        elif k=='local': (local.add if a[2] else local.discard)(a[1])
        elif k=='allow':
            if a[1]=='workshops': names=['pottery_workshop','furniture_workshop','oil_workshop','wine_workshop','weapons_workshop']
            else: names=[a[1]]
            for nm in names: (forb.discard if a[2] else forb.add)(nm)
    def evaluate():
        buyers=collections.Counter(); sellers=set()
        for ro in routes.values():
            if not ro['active']: continue
            for r,q in ro['buys'].items(): buyers[r]+=q
            for r,q in ro['sells'].items():
                if q>0: sellers.add(r)
        res={}
        for g,q in buyers.items():
            if q<=0 or g not in P or g not in PROD: continue
            yr,w=PROD[g]
            if g in CHAIN:
                best=None
                # each input either local (labour) or imported (cost)
                opts=[]
                ok=True; cost=0; workers=w
                if IND[g] in forb: continue
                for r,u in CHAIN[g].items():
                    if r in local and IND[r] not in forb and terrain_ok(r): workers+=PROD[r][1]*u*yr/PROD[r][0]
                    elif r in sellers: cost+=u*yr*P[r][0]
                    else: ok=False
                if not ok: continue
                profit=P[g][1]*yr-cost
            else:
                if g not in local or IND.get(g) in forb or not terrain_ok(g): continue
                profit=P[g][1]*yr; workers=w
            if workers<=0: continue
            res[g]=(profit/workers, q*profit/yr)   # per worker per year, quota-limited per year
        return res
    for a in timed.get(0,[])+timed.get(1,[]): apply(a)
    years=[]; prev=None; prevbig=None; changes=[]; bigchanges=[]
    months=sorted(k for k in timed if k>1)
    for y in range(0,51):
        for mo in [k for k in months if y*12-12<k<=y*12] if y>0 else []:
            for a in timed[mo]: apply(a)
        r=evaluate()
        if not r: continue
        top=max(r,key=lambda g:r[g][0]); big=max(r,key=lambda g:r[g][1])
        if prev and top!=prev: changes.append(f'y{y}:{prev}->{top}')
        if prevbig and big!=prevbig: bigchanges.append(f'y{y}:{prevbig}->{big}')
        if y==0: start=(top,round(r[top][0]),big,round(r[big][1]))
        prev,prevbig=top,big
    end=(top,round(r[top][0]),big,round(r[big][1]))
    # player-paced: apply conditional events and see if top changes
    r0=evaluate(); top0=max(r0,key=lambda g:r0[g][0]) if r0 else None
    nc=sum(len(a) for _,a in cond)
    for _,acts in cond:
        for a in acts: apply(a)
    r1=evaluate(); top1=max(r1,key=lambda g:r1[g][0]) if r1 else None; big1=max(r1,key=lambda g:r1[g][1]) if r1 else None
    OUT.append((d,start,end,changes,bigchanges,nc,len(cond),top1,big1,sorted(r1.items(),key=lambda kv:-kv[1][0])[:4] if r1 else []))
for d,start,end,ch,bch,nc,ne,t1,b1,top4 in sorted(OUT,key=lambda o:-(len(o[3])+len(o[4]))):
    print(f"## {d}\n  start best/worker={start[0]}({start[1]}/w) biggest={start[2]}({start[3]}/yr) | timed end best={end[0]} biggest={end[2]}")
    print(f"  timed changes best/worker: {len(ch)} {' '.join(ch)}")
    print(f"  timed changes biggest earner: {len(bch)} {' '.join(bch)}")
    print(f"  player-paced trade actions: {nc} in {ne} events -> after all: best={t1} biggest={b1} | top4/worker: "+', '.join(f'{g}={v[0]:.0f}' for g,v in top4))
