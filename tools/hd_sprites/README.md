# HD sprite pipeline

Tools that remake Caesar III sprites as HD (2x) images for the HD sprite loader in `src/core/image_hd.c`.
The `c3-hd-sprites` skill (`.claude/skills/c3-hd-sprites/SKILL.md`) describes the workflow and the rules.

## Setup

1. Install Blender (`/Applications/Blender.app`) and a Python with Pillow and numpy.
   The scripts use `~/.local/share/uv/tools/mflux/bin/python`.
2. Put the Caesar III data files in `~/caesar3`.
3. Run `python export_originals.py` (all original sprites to `originals/`) and `./fetch_textures.sh` (CC0 textures to `tex/`).

## Layout

| Path | Content |
|---|---|
| `sg.py` | Reads the `.sg2` / `.555` sprite files |
| `export_originals.py` | Writes every original sprite to `originals/<id>.png` |
| `fetch_textures.sh` | Downloads the CC0 photo textures (ambientCG) to `tex/` |
| `blender/c3.py` | Shared Blender scene: camera, calibrated light, materials, props, grass, render, top pass |
| `blender/tent.py`, `blender/terrain.py` | Sprite scripts (tents 2779-2782; grass, water and shore tiles) |
| `blender/casa.py` | Older standalone casa script (from before `c3.py`; its camera scale is about 3% small) |
| `blender/make.sh SCRIPT ID [install]` | Renders one sprite at 8x, makes the 2x file, checks it, installs it when all checks pass |
| `blender/terrain_make.sh [install] ID...` | The same for terrain tiles (central climate) |
| `blender/check.py`, `blender/test_check.py` | Checks for an HD sprite, and their regression tests |
| `blender/calibrate.sh` | Calibrates the light gain and the grass colour |
| `blender/attempt.py` | Saves each build as an attempt (`blender/out/attempts/<id>/<time>/`); install / uninstall from the command line |
| `blender/scripts.json` | Which script builds which sprite ids (read by `attempt.py` and the viewer server) |
| `viewer/index.html` | Progress viewer; `viewer/build_viewer.py` rebuilds its data |
| `viewer/server/` | Go server for the viewer: live data, attempts, install, uninstall, generation jobs |

## Viewer

    cd tools/hd_sprites/viewer/server && go run .      # then open http://127.0.0.1:8642

The server listens on 127.0.0.1 only. In the sprite panel you can compare attempts with the original, install an attempt
(refused when its checks fail, unless you allow it), uninstall, and generate a new attempt with a new seed.
At most 2 renders run at a time (`-workers`). Opened from disk, `viewer/index.html` is read-only.

The build scripts and the viewer install into `~/caesar3/hd/<sg2 name>/`. Restart the game after an install.
