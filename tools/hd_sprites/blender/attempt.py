"""Attempts, install and uninstall of HD sprites (used by make.sh, terrain_make.sh and viewer/server.py).

Each build is saved as an attempt: out/attempts/<id>/<stamp>/ with the 2x files, the 8x render, the compare
sheet and meta.json (seed, script, time, checks). Installing copies an attempt to the game folder.

usage: python attempt.py save ID SEED SCRIPT          (after a build; reads out/<id>*.png and out/<id>_check.json)
       python attempt.py install ID [STAMP|latest] [force]
       python attempt.py uninstall ID
"""
import json, os, shutil, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'out')
ATTEMPTS = os.path.join(OUT, 'attempts')
GAME_HD = os.path.expanduser('~/caesar3/hd')
CLIMATES = ('c3', 'c3_north', 'c3_south')

# which script builds which sprites: blender/scripts.json (shared with viewer/server)
SCRIPTS = [(range(e['from'], e['to'] + 1), e['script']) for e in json.load(open(os.path.join(HERE, 'scripts.json')))['scripts']]


def script_for(i):
    for r, s in SCRIPTS:
        if i in r:
            return s
    return None


def climates_for(i):
    # terrain is coloured by the central climate's originals: other climates keep their own grass
    return ('c3',) if script_for(i) == 'terrain' else CLIMATES


def attempts(i):
    """attempts of sprite i, newest first: [{stamp, seed, script, time, checks, pass, files}]"""
    d = os.path.join(ATTEMPTS, str(i))
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


def save(i, seed, script):
    stamp = time.strftime('%Y%m%d-%H%M%S')
    d = os.path.join(ATTEMPTS, str(i), stamp)
    os.makedirs(d, exist_ok=True)
    for suffix in ('', '_top', '_8', '_cmp'):
        src = os.path.join(OUT, f'{i}{suffix}.png')
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(d, f'{i}{suffix}.png'))
    cj = os.path.join(OUT, f'{i}_check.json')
    checks = json.load(open(cj)) if os.path.exists(cj) else {}
    json.dump(dict(seed=seed, script=script, time=stamp, checks=checks), open(os.path.join(d, 'meta.json'), 'w'), indent=1)
    return stamp


def install(i, stamp='latest', force=False):
    """copy an attempt's 2x files to the game; refuses an attempt with failed checks unless force"""
    a = attempts(i)
    if not a:
        raise ValueError(f'sprite {i} has no attempts')
    att = a[0] if stamp == 'latest' else next((x for x in a if x['stamp'] == stamp), None)
    if att is None:
        raise ValueError(f'sprite {i} has no attempt {stamp}')
    if not att['pass'] and not force:
        fails = [k for k, (ok, _) in att['checks'].items() if not ok]
        raise ValueError(f'attempt {att["stamp"]} fails checks: {", ".join(fails) or "no check results"}')
    d = os.path.join(ATTEMPTS, str(i), att['stamp'])
    for c in climates_for(i):
        os.makedirs(os.path.join(GAME_HD, c), exist_ok=True)
        shutil.copy2(os.path.join(d, f'{i}.png'), os.path.join(GAME_HD, c, f'{i}.png'))
        top = os.path.join(GAME_HD, c, f'{i}_top.png')
        if os.path.exists(os.path.join(d, f'{i}_top.png')):
            shutil.copy2(os.path.join(d, f'{i}_top.png'), top)
        elif os.path.exists(top):
            os.remove(top)
    return att['stamp']


def uninstall(i):
    removed = 0
    for c in CLIMATES:
        for name in (f'{i}.png', f'{i}_top.png'):
            p = os.path.join(GAME_HD, c, name)
            if os.path.exists(p):
                os.remove(p); removed += 1
    return removed


if __name__ == '__main__':
    cmd, i = sys.argv[1], int(sys.argv[2])
    try:
        if cmd == 'save':
            print('attempt', save(i, int(sys.argv[3]), sys.argv[4]))
        elif cmd == 'install':
            print('installed', i, install(i, sys.argv[3] if len(sys.argv) > 3 else 'latest', 'force' in sys.argv[4:]))
        elif cmd == 'uninstall':
            print('removed', uninstall(i), 'files of', i)
    except ValueError as e:
        print('NOT done:', e); sys.exit(1)
