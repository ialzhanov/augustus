"""Attempts, install and uninstall of HD sprites (used by make.sh, terrain_make.sh and viewer/build_viewer.py).

Each build is saved as an attempt: out/attempts/[<climate>/]<id>/<stamp>/ with the 2x files, the 8x render, the
compare sheet and meta.json (seed, script, time, checks). The central climate (c3) has no climate folder.
Installing copies an attempt to the game folder of each climate that shows this image (sg.climates_of): a central
attempt also goes to north and south when their image is the same; a north or south attempt goes only to its climate.

usage: python attempt.py save ID SEED SCRIPT [CLIMATE]   (after a build; reads out/[climate/]<id>*.png and <id>_check.json)
       python attempt.py install ID [STAMP|latest] [force] [CLIMATE]
       python attempt.py uninstall ID [CLIMATE]
"""
import json, os, shutil, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from sg import CLIMATES, climates_of, sub, variants

OUT = os.path.join(HERE, 'out')
ATTEMPTS = os.path.join(OUT, 'attempts')
GAME_HD = os.path.expanduser('~/caesar3/hd')

# which script builds which sprites: blender/scripts.json (shared with viewer/server)
SCRIPTS = [(range(e['from'], e['to'] + 1), e['script']) for e in json.load(open(os.path.join(HERE, 'scripts.json')))['scripts']]


def script_for(i):
    for r, s in SCRIPTS:
        if i in r:
            return s
    return None


def targets(i, climate='c3'):
    """the climate folders an attempt of (climate, i) installs to"""
    return climates_of(i, variants()) if climate == 'c3' else [climate]


def attempt_dir(i, climate='c3'):
    return os.path.join(ATTEMPTS, f'{sub(climate)}{i}')


def attempts(i, climate='c3'):
    """attempts of sprite i, newest first: [{stamp, seed, script, time, checks, pass, files}]"""
    d = attempt_dir(i, climate)
    out = []
    if not os.path.isdir(d):
        return out
    for stamp in sorted(os.listdir(d), reverse=True):
        m = os.path.join(d, stamp, 'meta.json')
        if os.path.exists(m):
            meta = json.load(open(m))
            meta['stamp'] = stamp
            meta['pass'] = bool(meta.get('checks')) and all(ok for ok, _ in meta['checks'].values())
            meta['files'] = sorted(f for f in os.listdir(os.path.join(d, stamp)) if f.endswith('.png'))
            out.append(meta)
    return out


def save(i, seed, script, climate='c3'):
    stamp = time.strftime('%Y%m%d-%H%M%S')
    d = os.path.join(attempt_dir(i, climate), stamp)
    os.makedirs(d, exist_ok=True)
    out = os.path.join(OUT, sub(climate))
    for suffix in ('', '_top', '_8', '_cmp'):
        src = os.path.join(out, f'{i}{suffix}.png')
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(d, f'{i}{suffix}.png'))
    cj = os.path.join(out, f'{i}_check.json')
    checks = json.load(open(cj)) if os.path.exists(cj) else {}
    json.dump(dict(seed=seed, script=script, climate=climate, time=stamp, checks=checks), open(os.path.join(d, 'meta.json'), 'w'), indent=1)
    return stamp


def install(i, stamp='latest', force=False, climate='c3'):
    """copy an attempt's 2x files to the game; refuses an attempt with failed checks unless force"""
    a = attempts(i, climate)
    if not a:
        raise ValueError(f'sprite {climate} {i} has no attempts')
    att = a[0] if stamp == 'latest' else next((x for x in a if x['stamp'] == stamp), None)
    if att is None:
        raise ValueError(f'sprite {climate} {i} has no attempt {stamp}')
    if not att['pass'] and not force:
        fails = [k for k, (ok, _) in att['checks'].items() if not ok]
        raise ValueError(f'attempt {att["stamp"]} fails checks: {", ".join(fails) or "no check results"}')
    d = os.path.join(attempt_dir(i, climate), att['stamp'])
    for c in targets(i, climate):
        os.makedirs(os.path.join(GAME_HD, c), exist_ok=True)
        shutil.copy2(os.path.join(d, f'{i}.png'), os.path.join(GAME_HD, c, f'{i}.png'))
        top = os.path.join(GAME_HD, c, f'{i}_top.png')
        if os.path.exists(os.path.join(d, f'{i}_top.png')):
            shutil.copy2(os.path.join(d, f'{i}_top.png'), top)
        elif os.path.exists(top):
            os.remove(top)
    return att['stamp']


def uninstall(i, climate='c3'):
    removed = 0
    for c in targets(i, climate):
        for name in (f'{i}.png', f'{i}_top.png'):
            p = os.path.join(GAME_HD, c, name)
            if os.path.exists(p):
                os.remove(p); removed += 1
    return removed


if __name__ == '__main__':
    cmd, i = sys.argv[1], int(sys.argv[2])
    rest = sys.argv[3:]
    climate = rest.pop() if rest and rest[-1] in CLIMATES else 'c3'
    try:
        if cmd == 'save':
            print('attempt', save(i, int(rest[0]), rest[1], climate))
        elif cmd == 'install':
            print('installed', climate, i, install(i, rest[0] if rest else 'latest', 'force' in rest[1:], climate))
        elif cmd == 'uninstall':
            print('removed', uninstall(i, climate), 'files of', climate, i)
    except ValueError as e:
        print('NOT done:', e); sys.exit(1)
