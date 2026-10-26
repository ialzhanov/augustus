"""Export every image of the three climates to originals/: the central climate to originals/<id>.png, north and south
to originals/<climate>/<id>.png (only the images that differ from the central climate, listed in originals/climates.json).
Skips existing files. usage: python export_originals.py"""
import os, sys
from multiprocessing import Pool
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from sg import SG, CLIMATES, GAME, orig_path, write_variants

sg = {}


def init():
    for c, name in CLIMATES.items():
        sg[c] = SG(GAME, name)


def one(job):
    c, i = job
    path = orig_path(c, i)
    if os.path.exists(path):
        return 1
    try:
        if sg[c].raw(i) is None:
            return 0
        sg[c].decode(i).save(path)
        return 1
    except Exception as e:
        print(f'{c} {i}: {e}')
        return 0


if __name__ == '__main__':
    var = write_variants()
    n = len(SG(GAME, 'C3').img)
    jobs = [('c3', i) for i in range(1, n)] + [(c, i) for c, ids in var.items() for i in ids]
    for c in CLIMATES:
        os.makedirs(os.path.dirname(orig_path(c, 1)), exist_ok=True)
    with Pool(8, initializer=init) as p:
        done = sum(p.imap_unordered(one, jobs, chunksize=64))
    print(f'{done} of {len(jobs)} images exported ({", ".join(f"{c}: {len(v)}" for c, v in var.items())} climate variants)')
