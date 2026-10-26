"""Export every C3.sg2 image to originals/<id>.png (skips existing files). usage: python export_originals.py"""
import os, sys
from multiprocessing import Pool
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from sg import SG

sg = None


def init():
    global sg
    sg = SG(os.path.expanduser('~/caesar3'), 'C3')


def one(i):
    path = os.path.join(HERE, 'originals', f'{i}.png')
    if os.path.exists(path):
        return 1
    try:
        r = sg.img[i]
        if r['off'] is None or not r['w'] or not r['h']:
            return 0
        sg.decode(i).save(path)
        return 1
    except Exception:
        return 0


if __name__ == '__main__':
    os.makedirs(os.path.join(HERE, 'originals'), exist_ok=True)
    n = len(SG(os.path.expanduser('~/caesar3'), 'C3').img)
    with Pool(8, initializer=init) as p:
        done = sum(p.imap_unordered(one, range(1, n), chunksize=64))
    print(f'{done} of {n - 1} images exported')
