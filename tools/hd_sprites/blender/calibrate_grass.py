"""Linear-light ratio tile 306 / plain grass render (whole tile). usage: python calibrate_grass.py RENDER.png"""
import sys
import numpy as np
from PIL import Image
def lin(a):
    c = a / 255.0
    return np.where(c > 0.04045, ((c + 0.055) / 1.055) ** 2.4, c / 12.92)
o = np.asarray(Image.open('../originals/306.png').convert('RGBA'), float)
r = np.asarray(Image.open(sys.argv[1]).convert('RGBA').resize((58, 30), Image.LANCZOS), float)
m = (o[..., 3] > 0) & (r[..., 3] > 250)
print(','.join(f'{v:.3f}' for v in lin(o[m][:, :3]).mean(0) / lin(r[m][:, :3]).mean(0)))
