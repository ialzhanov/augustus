import re,glob,os,sys,collections
os.chdir(sys.argv[1])
dirs=[d.rstrip('/') for d in sorted(glob.glob('*/'))]
saves={d[:-5] for d in dirs if d.endswith('_SAVE')}
dirs=[d for d in dirs if d not in saves]
def camp(d): return 'RC' if d.startswith('RC') else 'CN' if d.startswith('CN') else 'AR'
types=[l.split() for l in open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'event_types.txt'))]
cond_names=[n for t,n in types if t.startswith('CONDITION')]; act_names=[n for t,n in types if t.startswith('ACTION')]
cu=collections.defaultdict(lambda: collections.Counter()); au=collections.defaultdict(lambda: collections.Counter())
cm=collections.defaultdict(set); am=collections.defaultdict(set)
for d in dirs:
    for line in open(d+'/compact.txt'):
        if not line.startswith('E'): continue
        m=re.match(r'E\S+(?: \[[^\]]*\])?(?: rep\S+ x\S+)? IF (.*?) => (.*)$',line.strip())
        if not m: continue
        conds,acts=m.groups()
        for c in re.findall(r'(?:^|& |OR\(|\| )([a-z_]+) ',conds+' '):
            cu[c][camp(d)]+=1; cm[c].add(d)
        for a in acts.split(' ; '):
            a=a.split(' ')[0]
            if a: au[a][camp(d)]+=1; am[a].add(d)
def show(title,names,u,mm):
    print(f'== {title}: name | uses AR/RC/CN | maps')
    for n in sorted(set(names)|set(u), key=lambda n:-sum(u[n].values())):
        c=u[n]; print(f'{n:34s} {c["AR"]:4d} {c["RC"]:4d} {c["CN"]:4d}  maps={len(mm[n])}' + ('' if n in names else '  (not in engine list)'))
show('CONDITIONS',cond_names,cu,cm); show('ACTIONS',act_names,au,am)
print('maps', len(dirs), collections.Counter(camp(d) for d in dirs))
