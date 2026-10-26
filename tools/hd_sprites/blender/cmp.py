"""usage: python cmp.py RENDER.png ORIG.png OUT.png -> original | new (game size, 8x nearest) | new full render"""
import sys
from PIL import Image
r, o = Image.open(sys.argv[1]).convert('RGBA'), Image.open(sys.argv[2]).convert('RGBA')
n = r.resize(o.size, Image.LANCZOS)
n.save(sys.argv[1].replace('.png', '_game.png'))
Z = 8
ims = [o.resize((o.width * Z, o.height * Z), Image.NEAREST), n.resize((o.width * Z, o.height * Z), Image.NEAREST), r]
s = Image.new('RGBA', (sum(i.width for i in ims) + 40, max(i.height for i in ims)), (45, 45, 45, 255))
x = 0
for i in ims:
    s.alpha_composite(i, (x, 0)); x += i.width + 20
s.save(sys.argv[3])
