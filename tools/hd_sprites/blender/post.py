"""Sharpen a rendered HD sprite in place (the game shows it scaled down; this keeps the original's crisp contrast).
Transparent pixels are first filled with the nearest opaque colour, so the sprite edge gets no dark halo.
usage: python post.py IMAGE.png [...]"""
import sys
from PIL import Image, ImageFilter
for path in sys.argv[1:]:
    im = Image.open(path).convert('RGBA'); a = im.getchannel('A')
    fill = im.copy()
    for _ in range(6):                                     # grow colours into the transparent area
        fill = Image.alpha_composite(fill.filter(ImageFilter.MaxFilter(3)), fill)
    rgb = Image.composite(im, fill, a.point(lambda v: 255 if v > 0 else 0)).convert('RGB')
    rgb = rgb.filter(ImageFilter.UnsharpMask(radius=1.5, percent=80, threshold=2))
    out = rgb.convert('RGBA'); out.putalpha(a); out.save(path)
