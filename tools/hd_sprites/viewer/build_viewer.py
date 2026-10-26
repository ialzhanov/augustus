"""Builds viewer/data.js for viewer/index.html: every C3 sprite with its group, files, status and check results.
Check results are cached by file modification time (viewer/checks_cache.json).
usage: python build_viewer.py   (make.sh and terrain_make.sh run it after each build)"""
import hashlib, json, os, re, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
TEX = os.path.dirname(HERE)
BL = os.path.join(TEX, 'blender')
sys.path.insert(0, TEX); sys.path.insert(0, BL)
from sg import SG
from check import checks

GAME = os.path.expanduser('~/caesar3')
HD = os.path.join(GAME, 'hd', 'c3')
GROUP_H = os.path.join(TEX, '..', '..', 'src', 'core', 'image_group.h')   # tools/hd_sprites -> repo root


def category(name):
    if name.startswith('GROUP_TERRAIN_'):
        return 'Terrain'
    if name.startswith('GROUP_BUILDING_HOUSE'):
        return 'Housing'
    if name.startswith('GROUP_BUILDING_'):
        return 'Buildings'
    if name.startswith('GROUP_FIGURE_'):
        return 'Walkers'
    return 'Interface & other'


def md5(path):
    with open(path, 'rb') as f:
        return hashlib.md5(f.read()).hexdigest()


def main():
    sg = SG(GAME, 'C3')
    names = {}
    for line in open(GROUP_H):
        m = re.search(r'(GROUP_\w+) = (\d+),', line)
        if m:
            names[int(m.group(2))] = m.group(1)
    starts = sorted((sg.groups[g], g) for g in range(1, 300) if sg.groups[g] and g in names)
    group_of = {}
    groups = []
    for k, (s, g) in enumerate(starts):
        e = starts[k + 1][0] if k + 1 < len(starts) else len(sg.img)
        if e <= s:
            continue
        groups.append(dict(id=g, name=names[g][6:], category=category(names[g]), start=s, end=e))
        for i in range(s, e):
            group_of[i] = g

    cache_path = os.path.join(HERE, 'checks_cache.json')
    cache = json.load(open(cache_path)) if os.path.exists(cache_path) else {}
    sprites = []
    for i in range(1, len(sg.img)):
        r = sg.img[i]
        orig = os.path.join(TEX, 'originals', f'{i}.png')
        if not os.path.exists(orig):
            continue
        hd, hd8, top = (os.path.join(BL, 'out', f'{i}{s}.png') for s in ('', '_8', '_top'))
        inst = os.path.join(HD, f'{i}.png')
        sp = dict(id=i, w=r['w'], h=r['h'], g=group_of.get(i, 0), top=bool(r['top']))
        if os.path.exists(hd):
            key = f'{i}:{os.path.getmtime(hd)}:{os.path.getmtime(top) if os.path.exists(top) else 0}'
            if cache.get(str(i), {}).get('key') != key:
                try:
                    res = checks(orig, hd, bool(r['top']), top if os.path.exists(top) else None)
                    cache[str(i)] = dict(key=key, checks={k: [bool(ok), msg] for k, (ok, msg) in res.items()})
                except Exception as e:
                    cache[str(i)] = dict(key=key, checks={'error': [False, str(e)]})
            sp['checks'] = cache[str(i)]['checks']
            sp['hd'] = f'../blender/out/{i}.png'
            if os.path.exists(hd8):
                sp['hd8'] = f'../blender/out/{i}_8.png'
            if os.path.exists(top):
                sp['hdtop'] = f'../blender/out/{i}_top.png'
            sp['rendered'] = int(os.path.getmtime(hd))
        if os.path.exists(inst):
            sp['installed'] = True
            sp['installed_current'] = os.path.exists(hd) and md5(inst) == md5(hd)
        sprites.append(sp)
    json.dump(cache, open(cache_path, 'w'))
    data = dict(built=time.strftime('%Y-%m-%d %H:%M'), groups=groups, sprites=sprites)
    with open(os.path.join(HERE, 'data.js'), 'w') as f:
        f.write('window.C3DATA = ' + json.dumps(data, separators=(',', ':')) + ';\n')
    n_r = sum('hd' in s for s in sprites); n_i = sum(s.get('installed', False) for s in sprites)
    n_p = sum('checks' in s and all(ok for ok, _ in s['checks'].values()) for s in sprites)
    print(f'viewer: {len(sprites)} sprites, {n_r} rendered, {n_p} passing, {n_i} installed')


if __name__ == '__main__':
    main()
