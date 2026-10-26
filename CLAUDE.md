# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Writing rule

Write all prose in Simplified Technical English (STE) at all times. This includes chat responses, reports, summaries, documentation and code comments. Use short active sentences. Use one term for one concept. Keep the articles (a, an, the). Do not use metaphors, idioms or figurative language. State the fact, then stop. This rule overrides any style mode that drops articles or uses fragments.

## Project

Augustus is a C99 re-implementation of Caesar 3. It is a fork of Julius and adds gameplay changes. Augustus needs the original Caesar 3 data files at runtime. Augustus can load Caesar 3 savegames and Julius savegames. Caesar 3 and Julius cannot load Augustus savegames.

## Build

```sh
mkdir -p build && cd build
cmake ..                 # add -DSDL_VERSION=3 for SDL3, -DAV1_VIDEO_SUPPORT=ON for AV1 video
make -j
```

- The debug options `DRAW_FPS`, `DRAW_ROUTING`, `DRAW_HIGHWAY_TERRAIN`, `DRAW_ROAD_NETWORK_IDS` and `DRAW_TILE_COORDS` show debug overlays.
- The option `TARGET_PLATFORM` selects a cross-compile target: `vita`, `switch`, `android`, `ios` or `emscripten`.
- `.ci_scripts/run_cmake.sh` contains the CMake commands that CI uses for each platform.
- **`CMakeLists.txt` lists each source file explicitly** in lists such as `CORE_FILES`, `BUILDING_FILES` and `WINDOW_FILES`. Add each new `.c` file to the correct list.
- With GCC and Clang, the build uses `-Wall -Wextra -Wpedantic` and `-Werror=implicit-function-declaration`. With Clang, the build also uses `-Werror=incompatible-pointer-types -Werror=int-conversion -Wstrict-prototypes`. Write `void` for an empty parameter list.
- The repository has no automated tests. To verify a change, build it without new warnings and run the game.

## Architecture

The code is in `src/`, with one directory for each domain. Most modules keep their state in a file-static `data` struct. They expose plain functions with names in the form `<module>_<verb>()`.

- `platform/`: the entry point and the operating system layer. `platform/SDL2/augustus.c` and `platform/SDL3/augustus.c` contain `main()` and the main loop. Each SDL directory has its own `renderer.c`, `screen.c`, `sound_device.c` and input files. A change to the renderer or to the platform layer usually needs the same change in `SDL2/` and in `SDL3/`.
- `graphics/`: the drawing API, which does not depend on the platform. `graphics/renderer.h` defines `graphics_renderer_interface`, a table of function pointers. The SDL renderer registers this table with `graphics_renderer_set_interface()`. `graphics/window.h` defines the window stack. Each screen is a `window_type` with the callbacks `draw_background`, `draw_foreground`, `handle_input` and `get_tooltip`. `window_show()` opens a window and `window_go_back()` closes it.
- `window/`: the screens, for example advisors, editor dialogs, the city view and menus.
- `widget/`: UI parts that many screens use, for example the city map renderer, the sidebar, the minimap and input boxes.
- `game/`: the game lifecycle and the simulation loop.
  - `game/game.c` contains the init, run and draw functions.
  - `game/tick.c` runs the simulation. `advance_tick()` runs one subsystem for each tick number from 0 to 49. Then it advances the day, the month and the year.
  - `game/file_io.c` reads and writes savegames. `game/save_version.h` defines the save versions.
  - `game/settings.c` and `core/config.c` keep the user options.
- The simulation state is in these directories:
  - `city/`: city data, for example finance, population, labour, gods and trade.
  - `building/`: buildings and the logic for each building type.
  - `figure/` and `figuretype/`: walkers and the actions for each figure type.
  - `map/`: tile grids, for example terrain, routing, desirability and roads.
  - `empire/`, `scenario/` and `editor/`: the empire, scenario data and events, and the map editor.
- `core/`: low-level utilities. Examples: `buffer` (save serialization), `image` (image IDs and the load of the original `.sg2` and `.555` sprites), `string`, `io`, `random`, `config` and `log`.
- `assets/`: Augustus graphics that the original data does not have. XML files in `res/assets/Graphics/*.xml` describe the image groups. The code gets an image ID with `assets_get_image_id("<group>", "<name>")` or `assets_lookup_image_id(ASSET_*)`. Original Caesar 3 images use the numeric IDs in `core/image_group.h`.
- `translation/`: strings that only Augustus uses. To add a string, add a key to the `translation_key` enum in `translation/translation.h` and an English string in `translation/english.c`. Other languages use the English string when they do not have the key. Read a string with `translation_for(TR_KEY)`. Original game text comes from `lang_get_string(group, index)`.
- `ext/`: vendored dependencies, for example the SDL2 and SDL3 sources, miniz, spng, sxml, zip, easyav1 and tinyfiledialogs. Do not edit these files.

## Savegame versioning (important)

A change that adds or changes saved state must follow the guide at the top of `src/game/save_version.h`:

- Increase `SAVE_GAME_CURRENT_VERSION`. Add a `SAVE_GAME_LAST_*` marker that names the state before the change.
- Write and read the new field in the same position in the save and load functions of the module, for example in `building/state.c` or `figure/figure.c`. Increase the `*_CURRENT_BUFFER_SIZE` constant. Do not change a `*_ORIGINAL_BUFFER_SIZE` constant.
- Read the new field only when the version is high enough (`if (version > SAVE_GAME_LAST_...)`). Set a default value for older savegames.
- A new building type or figure type always needs a new save version, also when it adds no fields.

## Branching, commits and pull requests

These rules apply to this fork (`ialzhanov/augustus`). A pull request to upstream (`Keriew/augustus`) follows the upstream style: a short free-form subject with the PR number, for example `update korean.c (#1967)`.

Make all changes on a branch from `master`. Do not commit directly to `master`. Use a Claude Code native worktree under `.claude/worktrees/` for each branch.

### Branch names

Use a semantic prefix and a short kebab-case description:

- `feat/<description>`: a new feature
- `fix/<description>`: a bug fix
- `refactor/<description>`: a change in structure with no change in behavior
- `docs/<description>`: documentation only
- `chore/<description>`: tooling, dependencies or build configuration
- `test/<description>`: tests only

Examples: `feat/hd-sprites`, `fix/minimap-palisade-update`.

### Commit messages (Conventional Commits)

Format: `<type>(<scope>): <subject>`

- **Types:** `feat`, `fix`, `refactor`, `docs`, `chore`, `test`, `perf`, `style`, `build`, `ci`.
- **Scope:** the `src/` directory that the change affects: `assets`, `building`, `city`, `core`, `editor`, `empire`, `figure`, `figuretype`, `game`, `graphics`, `input`, `map`, `platform`, `scenario`, `sound`, `translation`, `widget`, `window`. Use `cmake`, `ci` or `claude` for changes outside `src/`.
- **Subject:** imperative mood, lowercase, no period at the end, fewer than 70 characters.
- For a change that breaks savegame compatibility, put `!` after the scope (`feat(building)!:`) and add `BREAKING CHANGE:` in the body.

Examples:

- `feat(core): load hd sprite atlases`
- `fix(widget): update minimap after a native palisade is placed`
- `docs(claude): port code standards`

### Pull requests

A pull request targets `master`. Fill in each section of `.github/PULL_REQUEST_TEMPLATE.md` before you request a review. Reviews follow `REVIEW.md`.

- Do not rebase `master`.
- Before a push, check the branch with `git rev-parse --abbrev-ref HEAD`.
- To push a rebased branch, use `git push --force-with-lease`. Do not use `--force`.

## Coding conventions

- Copy the existing pattern in the same module. Do not make a new pattern when the module already has one.
- When the user says "similar to X", copy the structure of X exactly.

## Common mistakes to avoid

- Do not add saved state without an increase of `SAVE_GAME_CURRENT_VERSION` and a new `SAVE_GAME_LAST_*` marker.
- Do not add a `buffer_write_*` call without the matching `buffer_read_*` call in the same position.
- Do not add a `buffer_read_*` call for a new field without a `version >` check.
- Do not add a field to a save buffer without an increase of the `*_CURRENT_BUFFER_SIZE` constant.
- Do not add a new building type or figure type without an increase of the save version.
- Do not change one SDL renderer without the same change in the other: `src/platform/SDL2/` and `src/platform/SDL3/`.
- Do not add a `.c` file without an entry in the correct file list in `CMakeLists.txt`.
- Do not add a `TR_` key without an English string in `src/translation/english.c`.
- Do not edit files in `ext/`.

## Working with plans

- Plans are in `docs/plans/`. A plan gives the implementation steps in sequence, with exact file paths and code.
- When the user asks you to implement a plan, read all of the plan first. Then do the steps in the given sequence.
- When the user asks you to make a plan, write a Markdown file in `docs/plans/` with these sections: Context, Architecture (if applicable), numbered implementation steps with file paths and code, and Verification.
- Do not skip or reorder the steps of a plan. The steps have dependencies.
