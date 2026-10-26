"""Map preview: a 10 x 10 grass area with a pond, built from original tiles and from the installed HD tiles
exactly as the engine draws them (footprint masked to the tile shape). Writes out/terrain_map.png.
usage: python preview_map.py"""
import os
import random
from PIL import Image, ImageDraw
from check import engine_view

HD = os.path.expanduser('~/caesar3/hd/c3')
random.seed(3)
grass = [i for i in range(306, 364) if os.path.exists(f'{HD}/{i}.png')]
water = [i for i in range(364, 372) if os.path.exists(f'{HD}/{i}.png')]
N, S = 10, 2                                              # tiles, pixels per original pixel
layout = [[random.choice(water) if 3 <= x <= 6 and 3 <= y <= 6 else random.choice(grass) for x in range(N)] for y in range(N)]


def tile(i, hd):
    if not hd:
        return Image.open(f'../originals/{i}.png').convert('RGBA').resize((58 * S, 30 * S), Image.NEAREST)
    im = Image.open(f'{HD}/{i}.png').convert('RGBA')
    d = im.width // 58
    return engine_view(im, None, 58, 30, d, 1).resize((58 * S, 30 * S), Image.BILINEAR)


def mosaic(hd):
    img = Image.new('RGBA', ((N + 1) * 60 * S, (N + 2) * 30 * S), (30, 30, 30, 255))
    for y in range(N):
        for x in range(N):
            px = (x - y) * 30 * S + N * 30 * S
            py = (x + y) * 15 * S + 20 * S
            img.alpha_composite(tile(layout[y][x], hd), (px, py))
    return img


a, b = mosaic(False), mosaic(True)
m = Image.new('RGB', (a.width * 2 + 20, a.height + 30), (30, 30, 30))
dr = ImageDraw.Draw(m)
m.paste(a, (0, 30)); m.paste(b, (a.width + 20, 30))
dr.text((10, 8), 'ORIGINAL tiles (as at 200% zoom)', fill='yellow')
dr.text((a.width + 30, 8), 'NEW tiles as the engine draws them (200% zoom)', fill='lime')
m.save('out/terrain_map.png')
print(f'{len(grass)} grass, {len(water)} water tiles used')
