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
| `viewer/index.html` | Progress viewer (open from disk); `viewer/build_viewer.py` rebuilds its data |

The build scripts install into `~/caesar3/hd/<sg2 name>/`. Restart the game after an install.
