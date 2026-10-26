---
name: c3-hd-sprites
description: Remake Caesar III sprites as HD versions for the patched Augustus engine (Blender re-models, terrain, checks, install, progress viewer). Use when asked to remake, re-model, render, check, install or review an HD sprite, a sprite group (tents, houses, buildings, terrain, water), or to plan or parallelise the HD sprite work.
---

# Caesar III HD sprites

Remake an original Caesar III sprite as an HD (2x) image that the patched Augustus engine shows in place of the original. The original look must stay: same layout, orientation, colours and style. Only detail and material quality go up ("AAA, rich in detail" — never pale, bland or computer-generic).

## Where things are

| What | Path |
|---|---|
| Game (test install) | `~/caesar3` — `augustus.app` is the patched build; `augustus_pre_hd.app` is the unpatched backup |
| HD files the game loads | `~/caesar3/hd/<sg2 name>/<id>.png` (+ `<id>_top.png`); `c3` = central climate, also `c3_north`, `c3_south` |
| Engine source (this repo) | repo root (`src/core/image_hd.c`, renderer `draw_texture_advanced`); build: `cmake --build build -j8` |
| Pipeline (in this repo) | `tools/hd_sprites/` — setup: `python export_originals.py`, `./fetch_textures.sh` (see its README) |
| Decoder (paths below: relative to `tools/hd_sprites/`) | `sg.py` — `SG(~/caesar3, 'C3').decode(id)`, `.groups[g]` = first id of group g |
| Blender library | `blender/c3.py` — scene, camera, light, materials, props, grass, render, top pass |
| Sprite scripts | `blender/tent.py`, `blender/casa.py` (old standalone), `blender/terrain.py` |
| Build one sprite | `blender/make.sh SCRIPT ID [install]` — 8x render (+top), 2x file, sharpen, checks, viewer |
| Build terrain | `blender/terrain_make.sh [install] ID...` (central climate only) |
| Checks | `blender/check.py ORIG HD HAS_TOP [TOP]`; regression tests `blender/test_check.py` (run first by both build scripts) |
| Originals (PNG) | `originals/<id>.png` (all 8,698; gitignored, made by `export_originals.py`) |
| CC0 photo textures | `tex/<ambientCG id>/` (gitignored, `fetch_textures.sh`) (Fabric061, Ground108, Ground054, Ground037, Grass004, Grass001, Planks037A, RoofingTiles006, Plaster007, Rock064, Gravel023) |
| Progress viewer | `cd viewer/server && go run .` then http://127.0.0.1:8642 — attempts, install, uninstall, generate (new seed); `viewer/index.html` from disk is read-only |
| Attempts | every build is saved in `blender/out/attempts/<id>/<time>/` (`blender/attempt.py`); `C3_SEED=n` gives a new variation |
| Script registry | `blender/scripts.json`: add every new sprite script with its id range, else the viewer cannot generate it |
| Group names | `src/core/image_group.h` (repo root) (`GROUP_BUILDING_HOUSE_TENT = 26`, ...) |
| Python with PIL/numpy | `~/.local/share/uv/tools/mflux/bin/python` (system python3 has no PIL) |
| Blender | `/Applications/Blender.app/Contents/MacOS/Blender -b -P script.py -- OUT.png SCALE [top] -- ARGS` |

## Engine facts (do not break)

- HD file = original size x integer density (2..8). We install **2x**: the closest zoom is 200%, and 2:1 bilinear at 100% is clean. Larger densities only blur at 100% (no mipmaps).
- Isometric sprites: the engine keeps the footprint rows (bottom `30 n` px) and **masks them to the original stepped tile outline**; the top part (rows above `H - 15 n`) comes from `<id>_top.png` (building only, ground cut out) or from the full image. A sprite needs `_top.png` when the original has a top part (`SG.img[id]['top']`).
- `ATLAS_HD` textures are looked up by index only (`img->hd.atlas_id`). Never encode atlas types >= 8 in an image id: `type << 28` overflows a signed int (that crashed the game). A `_Static_assert` guards it.
- Restart the game after installing files. Rollback: delete `~/caesar3/hd/...` files.

## Camera and pixel mapping (all scripts)

World: 1 tile = 1 x 1 units, tile centre at origin, +z up. Orthographic 2:1 camera from (+x, -y), elevation 30 deg. Screen-left faces = -y, screen-right faces = +x. For an `n x n` building in a `W x H` sprite, tile centre row `c = H - 15 n`:

    x_s = W/2 + 29 (x + y)        y_s = c + 15 (x - y) - 35.5 z
    world from pixel (ground):    s = (x_s + 0.5 - W/2) / 29,  d = (y_s + 0.5 - c) / 15,  x = (s + d)/2,  y = (s - d)/2

`c3.render(W, H, tiles=n)` sets this camera. Use `px()` in `tent.py` as the model for converting measured pixels.

## Workflow for one sprite

1. **Look at the original** (`originals/<id>.png`) at 12x with a pixel grid (nearest upscale + a grid line every 5 px). List every object: position (pixel of its base), size in px, colour.
2. **Measure, never guess**: positions via the formula above; heights from `35.5 px = 1 unit`; colours by sampling the original's pixels (sRGB) and converting with `c3.GAIN` (see `canvas()` in `tent.py`: `lin(srgb) * GAIN / photo_mean`, x0.7 for surfaces facing the sun).
3. **Write the script** from `template_sprite.py` in this skill folder: ground (grass from tile 306 via `'grass'` material, plane **1.12** so the stepped outline has no gaps), the model, props from `c3` (amphora, bowl_pot, sack, basket, blanket_roll, stool, firepit, straw, rock, block, rubble), grass tufts `c3.grass(count, open_ground)`, `c3.render(W, H)`.
4. **Orientation**: decide which way fronts/doors face from the original (screen lower-left = -y, lower-right = +x). The `mirror` check fails a mirrored layout.
5. **Build**: `blender/make.sh myscript.py ID`. Read the check output and `blender/out/ID_cmp.png` (original | game size | 8x).
6. **Iterate** until all checks pass AND it looks rich in the 8x view. Fix the cause, not the threshold.
7. **Register** the script in `blender/scripts.json`. **Install** from the viewer (pick the best attempt) or with `make.sh myscript.py ID install` (copies only when all checks pass).

## Checks (`check.py`) and the fault each one caught

| Check | Fails when | Past fault |
|---|---|---|
| size, top | not 2..8x, missing/wrong `_top.png` | engine refuses / walkers hidden |
| spill, coverage | pixels outside / missing vs the original shape | stones past the tile edge, roof too small |
| seam | footprint not fully opaque | dark lines between terrain tiles |
| rim | edge band brighter/darker than in the original | light rim on grass tiles |
| structure, mirror | blurred brightness layout differs / mirrored fits better | tents facing the wrong way |
| edge | front-edge grass differs from terrain grass (or own original) | grass colour mismatch between tiles |
| colour, contrast | mean colour off / local contrast < 0.6 or > 1.5 x | pale, bland or noisy sprites |
| clip | content cut at the top edge | casa roof above the frame |

Add a test to `test_check.py` for every new fault class, then a check. Never loosen a limit to pass a sprite.

## Lessons (each cost an iteration)

- Colours chosen by eye were 2-3x too bright (pale). Always sample the original.
- Procedural noise looks like camouflage; use the CC0 photo textures (`c3.m_photo`) and add seams/dirt/bleach as multipliers.
- Props must be the original's size (3-5 game px = 0.08-0.12 units); small props vanish at game size.
- Sharpening above ~80% (`post.py`) creates crunchy halos; fix contrast in materials and light instead.
- Generated mask images: Cycles does not see pixels edited in memory — save to PNG and load (`terrain.py save_image`).
- Masks and colour layouts must extend past the tile edge (fill transparent corners), else the edge gets a rim.
- Light is calibrated (`c3.LIGHT`, `c3.GAIN`, `GRASS_CAL`, terrain/water CAL). After changing light, run `blender/calibrate.sh` and recalibrate terrain.
- One sprite group shares one script with a `VARIANTS` dict (see `tent.py`).

## Parallel work

- Split by sprite group (one agent = one group/script). Shared files (`c3.py`, `check.py`) change only with tests (`test_check.py`) and a note to the others.
- GPU: run at most 2 Blender renders at a time on this Mac (M3 Pro, 18 GB).
- Walkers (4,802 animation frames) and interface (2,305) need a separate decision (rigged characters / AI upscale / keep) before work starts.
- Report progress through the viewer (`build_viewer.py` runs after each build).
