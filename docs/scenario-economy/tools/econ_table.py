import re,sys
L=open(sys.argv[1]).read().split('\n')
print('| Map | Pop goal | Start funds | Routes | Sum of route open costs | Export cap at start prices (dn/yr) | Export cap after quota events | Cap per citizen | Requests (denarii) |')
print('|---|---|---|---|---|---|---|---|---|')
for l in L:
    m=re.match(r'(\S+)\s+pop=(\d+)\s+funds=(\d+)\s+routes=(\d+)\s+opencost=(\d+)\s+exp=\d+\((\d+)\) max=\d+\((\d+)\) perCap=([\d.]+)->([\d.]+) .*req=(\d+) reqDen=(\d+)',l)
    if m:
        d,pop,f,r,oc,e,mx,p1,p2,rq,rd=m.groups()
        d=re.sub(r'_+',' ',d).replace(' The C','').replace(' The City','').replace(' SAVE',' (save)').strip()
        print(f'| {d} | {pop} | {f} | {r} | {oc} | {e} | {mx} | {p1} → {p2} | {rq} ({rd}) |')
