import re,glob,os,sys
os.chdir(sys.argv[1])
dirs=[d.rstrip('/') for d in sorted(glob.glob('*/'))]
saves={d[:-5] for d in dirs if d.endswith('_SAVE')}
dirs=[d for d in dirs if d not in saves]
print('| Map | Size | Usable % | Largest region % | Walk-connected % | Levels / ramps | Open square now→cleared | Water dist median / p90 | Land ≤10 from water % | Meadow | Rock sites | Entry→exit | Invasion pts reach (trees / cut) | Nearest invasion→center | Widest choke (trees / cut) | Natives→center |')
print('|'+'---|'*16)
for d in dirs:
    t=open(d+'/dump.txt').read()
    g=lambda p:(re.search(p,t,re.M) or [None,'-'])[1]
    inv=re.findall(r'^PATTERN inv\d+ \(\d+,\d+\) to_center dist=(-?\d+) choke_width=(\d+) \| trees_cleared dist=(-?\d+) choke_width=(\d+)',t,re.M)
    r1=[i for i in inv if i[0]!='-1']; r2=[i for i in inv if i[2]!='-1']
    dmin=min([int(i[0]) for i in r1],default=None); dmin2=min([int(i[2]) for i in r2],default=None)
    ch1=max([int(i[1]) for i in r1],default=0); ch2=max([int(i[3]) for i in r2],default=0)
    name=re.sub(r'_+',' ',d.replace('___The_City_to_',' ')).replace(' SAVE',' (save)')
    nat=g(r'native_min_walk_to_center=(-?\d+)')
    print(f"| {name} | {g(r'^MAP (\d+)x')} | {g(r'usable=\d+ \(([\d.]+)%')} | {g(r'largest=\d+ \(share ([\d.]+)%')} | {g(r'walk_connected_to_center=([\d.]+)')} | {g(r'levels=(\d+) ramp')} / {g(r'ramp_tiles=(\d+)')} | {g(r'now=(\d+)')}→{g(r'clearable=(\d+) now')} | {g(r'median=(\d+) p90')} / {g(r'p90=(\d+)')} | {g(r'within10=([\d.]+)')} | {g(r'meadow=(\d+) \(')} | {g(r'rock_edge_sites=(\d+)')} | {g(r'entry->exit walk=(-?\d+)').replace('-1','none')} | {len(r1)}/{len(inv)} / {len(r2)}/{len(inv)} | {dmin if dmin is not None else (str(dmin2)+' (cut)' if dmin2 is not None else '-')} | {ch1} / {ch2} | {'-' if nat=='-1' else nat} |")
