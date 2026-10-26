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
| Build one sprite | `[C3_CLIMATE=c3_north] blender/make.sh SCRIPT ID [install]` — 8x render (+top), 2x file, sharpen, checks, viewer. `C3_CLIMATE` selects the original, the output and attempt folders. The sprite scripts (`c3.py` grass, `tent.py`) and the `edge` check (central grass reference) do not use the climate yet, so a north or south build fails its checks |
| Build terrain | `blender/terrain_make.sh [install] ID...` (`C3_CLIMATE=c3_north` or `c3_south` for the other climates) |
| Checks | `blender/check.py ORIG HD HAS_TOP [TOP]`; regression tests `blender/test_check.py` (run first by both build scripts) |
| Originals (PNG) | `originals/<id>.png` (central, 8,699) and `originals/c3_north/`, `originals/c3_south/` (722 and 746 images that differ from the central ones, list in `originals/climates.json`); gitignored, made by `export_originals.py` |
| CC0 photo textures | `tex/<ambientCG id>/` (gitignored, `fetch_textures.sh`) (Fabric061, Ground108, Ground054, Ground037, Grass004, Grass001, Planks037A, RoofingTiles006, Plaster007, Rock064, Gravel023) |
| Progress viewer | `cd viewer/server && go run .` then http://127.0.0.1:8642 — filters by status, climate, footprint, category, group; attempts, install, uninstall, generate (new seed); `viewer/index.html` from disk is read-only |
| Attempts | every build is saved in `blender/out/attempts/<id>/<time>/` (`blender/attempt.py`); `C3_SEED=n` gives a new variation |
| Script registry | `blender/scripts.json`: add every new sprite script with its id range, else the viewer cannot generate it |
| Group names | `src/core/image_group.h` (repo root) (`GROUP_BUILDING_HOUSE_TENT = 26`, ...) |
| Python with PIL/numpy | `~/.local/share/uv/tools/mflux/bin/python` (system python3 has no PIL) |
| Blender | `/Applications/Blender.app/Contents/MacOS/Blender -b -P script.py -- OUT.png SCALE [top] -- ARGS` |

## Engine facts (do not break)

- Each climate (`c3`, `c3_north`, `c3_south`) has its own sprites. A north or south image that differs from the central one (720-750 per climate, some with another size) needs its own HD file. A central attempt installs only to the climates whose image is the same (`sg.climates_of`, `blender/attempt.py targets`).

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
- Ground around a building: take the yard (non-green pixels) and its light colours from the original (`tent.py` yard mask), so `structure` matches. Keep the yard mask 0 from tile distance 0.8, and do not put a transparent plane over the edge grass: a fully transparent plane still made the edge grass darker (`edge` failed).
- Tall buildings cast shadows over the tile edge, where the engine cuts them. Use `c3.render(..., edge_fade=True)`: shadows fade out toward the front edges.
- Do not edit a `.sh` script while a batch runs it: bash reads the file during the run.
- 3D grass tufts make the ground darker (about 50% at full density). They grow only on clearly green pixels, so a terrain tile had fewer tufts in its meadow centre than at its edge: light centre, dark edge, `edge` failed on 29 tiles. `terrain.py` lightens the ground where the tuft density is low (`C3_TUFT_SHADE`). Scatter density that follows a mask needs the same compensation.
- Roads (591-639) use `terrain.py` paved mode: one Voronoi mesh of laid stones, colour per stone from the original. Plaza (3140-3147) uses mosaic mode (square grid, ~0.75 px stones). 1-2 px grass verges render too light; `verge_lock()` sets each verge pixel's 8x8 block mean to the original colour.
- `edge` compares our image and the original at the SAME pixels (where the original is green, else ours). It once skipped verges that had lost their green (<= 10 green px): never let a check pass by finding nothing to measure.
- Flat single-colour sprites (245 black, 733) keep their originals: nothing to remake.
- Earthquake cracks (444-475) use `terrain.py` crack mode: the darkest pixels (limit per tile, 474/475 have only grey cracks) sink into a height-field ground mesh with rock ribs on the walls. The mesh goes past the tile edge by more than the floor sinks on screen, else a chasm at a back edge leaves a transparent gap (`seam`). Lit 3D walls are lighter than the painted dark walls: 473 failed `rim`.
- Shore tiles (825-844) use `terrain.py` shore mode through `make.sh terrain.py ID` (it has a top pass): rocks from stone blobs in the water, walls from `WALLS` (boxes fitted to the stone pixels, one height per tile). The layout under the models is filled from the pixels around them. A 45 degree box shows one shaded front face; posts and corners are 0 degree boxes (lit left face, dark right face).
- `edge_fade` removes the shadows near the tile edge, so the edge band gets lighter: rocks failed `rim` with it.
- `rim` once measured the two images on different pixels: a top part stays opaque at the tile edge, the footprint does not. The original itself measured 1.09. It now uses the same pixels in both (test in `test_check.py`).
- `make.sh` keeps the Blender log of each pass in `out/<id>_blender*.log`: some renders fail with no "rror:" line.
- - Trees and shrubs (254-261, 274-305) use `terrain.py` tree mode: `foliage.py` splits the canopy into circles (a sphere of radius R shows as a circle of 41 R px); each becomes a crown of leaf clusters in the original's screen-space colours, with a trunk or a leaf column to the ground. Dense tiles get undergrowth clusters; tiles with single trees on grass (`OPEN_GROUND`) do not: the colour rule takes the tree shadow for foliage, and lit clusters there doubled the contrast. Leaf clusters shade each other: `LEAF_CAL` 1.3.
- Meadow (262-273): tall blades at the foot of each light yellow vertical run of pixels.
- Sprites higher than wide: Blender fits `ortho_scale` to the larger side. `c3.render` corrects it; `test_camera.py` (run in Blender) checks a half-tile ground and a pole in three frame shapes. A full-tile ground did not show the fault (the frame cut it).
- - Rocks (201-244, 534-547) and rubble (658-665, 734, 743, 752, 761, 770): `terrain.py` rock mode, boulder piles on the crown circles (`keep_low=True`). Painted rocks have softer shading than the light gives: `ROCK_SHADE` (base 0.6, emission 0.2). `edge_fade` keeps their long shadows off the edge grass.
- Gardens (3148-3154): path and curbs flat, hedges and beds as undergrowth clusters (sharp vegetation mask, no blur: purple flowers blurred into the hedge green). Undergrowth heights stay inside the original alpha above each pixel (spill).
- Entry/exit flags (863-870): pole and arrow plank measured from the white and red/blue pixels.
- Never use `bpy.ops` in a loop: each op updates the whole scene (6000 pebbles: > 30 min). Build one mesh with numpy (`instances`, `build_tufts`) or copy a template mesh (`c3.rock`).
- A 3x3 rock render uses about 4 GB: memory got low with other renders; watch `PhysMem`.
- A module name used twice is a silent fault: `SHORE` was also the shore mask image, so `shore()` ran on every tile (flags lost their top part).
- - zsh does not split an unquoted variable into words: `./terrain_make.sh $ids` gives one argument. Use `${=ids}`.

## Parallel work

- Split by sprite group (one agent = one group/script). Shared files (`c3.py`, `check.py`) change only with tests (`test_check.py`) and a note to the others.
- GPU: terrain renders run well as 4-6 shards at the same time (CPU-bound, about 4 tiles a minute with 4 shards). Building renders need more GPU memory: 9 renders at the same time gave `Command buffer not completed. status = 5`. 3 terrain shards and 4 tent jobs at the same time also failed (14 of 20 tent jobs). 3 tent jobs alone also failed sometimes. Keep at most 2 Blender renders in total when building sprites are among them (server default `-workers 2`); terrain alone can run 4-6 shards, and check free memory (`top -l 1 | grep PhysMem`).
- A failed render saves no attempt (`make.sh`, `terrain_make.sh`; test: `blender/test_make.sh`).
- Paved and mosaic renders need much GPU memory: run them alone or at most 2 at a time.
- Wait for a batch by PID (`cmd & echo $! >> pids`, then `kill -0`), never with `pgrep -f '<text>'`: the pattern matches the waiting shell itself.
- Walkers (4,802 animation frames) and interface (2,305) need a separate decision (rigged characters / AI upscale / keep) before work starts.
- Report progress through the viewer (`build_viewer.py` runs after each build).
