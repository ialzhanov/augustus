import re,glob,os,sys
os.chdir(sys.argv[1])
rows=[]
for f in sorted(glob.glob('*/dump.txt')):
    t=open(f).read(); k=f.split('/')[0][:22]
    def g(p,i=1):
        m=re.search(p,t,re.M); return m.group(i) if m else '-'
    inv=re.findall(r'^PATTERN inv\d+ to_region dist=(-?\d+) choke=(\d+) \| cut dist=(-?\d+) choke=(\d+)',t,re.M)
    reach=[i for i in inv if i[0]!='-1']; reach2=[i for i in inv if i[2]!='-1']
    rows.append([k,g(r'^MAP (\d+)x'),g(r'climate=(\d)'),g(r'usable=\d+ \(([\d.]+)%'),g(r'largest=\d+ \(share ([\d.]+)%'),
      g(r'walk_connected_to_center=([\d.]+)'),g(r'levels=(\d+) ramp'),g(r'ramp_tiles=(\d+)'),g(r'clearable=(\d+) now'),g(r'now=(\d+)'),
      g(r'median=(\d+) p90'),g(r'p90=(\d+)'),g(r'within10=([\d.]+)'),
      g(r'meadow=(\d+) \('),g(r'rock_edge_sites=(\d+)'),g(r'entry->region walk=(-?\d+)'),g(r'entry->exit walk=(-?\d+)'),
      f"{len(reach)}/{len(inv)}",f"{len(reach2)}/{len(inv)}",str(min([int(i[0]) for i in reach],default=-1)),
      str(min([int(i[2]) for i in reach2],default=-1)),
      ",".join(i[1] for i in inv), ",".join(i[3] for i in inv), g(r'native_min_walk_to_center=(-?\d+)'), g(r'WIN pop=1:(\d+)')])
print('\t'.join('map sz cl use% lrg% walk% lev ramp sqC sqN wmed wp90 w10% mead rock en>r en>x inv inv_cut dinv dinv_cut chokes chokes_cut nat pop'.split()))
for r in rows: print('\t'.join(r))
