"""Builds viewer/data.js for viewer/index.html: every sprite of the three climates with its group, files, status and
check results. A north or south sprite is listed only when its image differs from the central climate's.
Check results are cached by file modification time (viewer/checks_cache.json).
usage: python build_viewer.py   (make.sh, terrain_make.sh and the viewer server run it)"""
import hashlib, json, os, re, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
TEX = os.path.dirname(HERE)
BL = os.path.join(TEX, 'blender')
sys.path.insert(0, TEX); sys.path.insert(0, BL)
from sg import SG, CLIMATES, GAME, orig_path, sub, variants
from check import checks
import attempt

HD = os.path.join(GAME, 'hd')
GROUP_H = os.path.join(TEX, '..', '..', 'src', 'core', 'image_group.h')   # tools/hd_sprites -> repo root
CATEGORIES = (('TERRAIN_', 'Terrain'), ('BUILDING_HOUSE', 'Housing'), ('BUILDING_', 'Buildings'), ('FIGURE_', 'Walkers'),
              ('EMPIRE_', 'Empire map'), ('MINIMAP_', 'Minimap'))


def category(name):
    return next((c for p, c in CATEGORIES if name.startswith('GROUP_' + p)), 'Interface')


def md5(path):
    with open(path, 'rb') as f:
        return hashlib.md5(f.read()).hexdigest()


def build():
    """all sprite data for the viewer"""
    sg = SG(GAME, 'C3')
    var = variants()
    var_sets = {c: set(v) for c, v in var.items()}
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
    recs = {c: SG(GAME, n).img for c, n in CLIMATES.items()}
    sprites = []
    jobs = [('c3', i) for i in range(1, len(sg.img))] + [(c, i) for c, ids in var.items() for i in ids]
    for c, i in jobs:
        orig = orig_path(c, i)
        if not os.path.exists(orig):
            continue
        r = recs[c][i]
        sp = dict(id=i, cl=c, w=r['w'], h=r['h'], g=group_of.get(i, 0), top=bool(r['top']),
                  tiles=(r['w'] + 2) // 60 if r['iso'] else 0)
        if c == 'c3':
            sp['same'] = [x for x in CLIMATES if x != 'c3' and i not in var_sets[x]]
        rel = f'{sub(c)}{i}'
        hd, hd8, top = (os.path.join(BL, 'out', f'{rel}{s}.png') for s in ('', '_8', '_top'))
        if os.path.exists(hd):
            ck = str(i) if c == 'c3' else f'{c}:{i}'
            key = f'{os.path.getmtime(hd)}:{os.path.getmtime(top) if os.path.exists(top) else 0}'
            if cache.get(ck, {}).get('key') != key:
                try:
                    res = checks(orig, hd, bool(r['top']), top if os.path.exists(top) else None)
                    cache[ck] = dict(key=key, checks={k: [bool(ok), msg] for k, (ok, msg) in res.items()})
                except Exception as e:
                    cache[ck] = dict(key=key, checks={'error': [False, str(e)]})
            sp['checks'] = cache[ck]['checks']
            sp['hd'] = f'../blender/out/{rel}.png'
            if os.path.exists(hd8):
                sp['hd8'] = f'../blender/out/{rel}_8.png'
            if os.path.exists(top):
                sp['hdtop'] = f'../blender/out/{rel}_top.png'
            sp['rendered'] = int(os.path.getmtime(hd))
        script = attempt.script_for(i)
        if script:
            sp['script'] = script
        atts = attempt.attempts(i, c)
        if atts:
            sp['attempts'] = [dict(stamp=a['stamp'], seed=a.get('seed'), ok=a['pass'],
                                   fails=[k for k, (ok, _) in a.get('checks', {}).items() if not ok],
                                   checks=a.get('checks', {}), files=a['files']) for a in atts]
        inst = os.path.join(HD, c, f'{i}.png')
        if os.path.exists(inst):
            sp['installed'] = True
            h = md5(inst)
            sp['installed_current'] = os.path.exists(hd) and h == md5(hd)
            for a in atts:
                f = os.path.join(attempt.attempt_dir(i, c), a['stamp'], f'{i}.png')
                if os.path.exists(f) and md5(f) == h:
                    sp['installed_attempt'] = a['stamp']; break
        sprites.append(sp)
    json.dump(cache, open(cache_path, 'w'))
    return dict(built=time.strftime('%Y-%m-%d %H:%M'), groups=groups, sprites=sprites,
                climates={c: len(v) for c, v in var.items()})


def main():
    data = build(); sprites = data['sprites']
    with open(os.path.join(HERE, 'data.js'), 'w') as f:
        f.write('window.C3DATA = ' + json.dumps(data, separators=(',', ':')) + ';\n')
    n_r = sum('hd' in s for s in sprites); n_i = sum(s.get('installed', False) for s in sprites)
    n_p = sum('checks' in s and all(ok for ok, _ in s['checks'].values()) for s in sprites)
    print(f'viewer: {len(sprites)} sprites, {n_r} rendered, {n_p} passing, {n_i} installed')


if __name__ == '__main__':
    main()
