# End-to-end test harness: design

Date: 2026-10-25. Engine base: `master` at `1bd9f0620`.

## 1. Intent

Augustus has no automated tests. To check a feature now, a person plays the game until the city reaches the right state, then looks at the screen. This is slow, and the result depends on the person.

The harness lets Claude, with no person present, do these steps:

1. Take a savegame.
2. Change the state in the savegame.
3. Run the game for an exact number of ticks.
4. Draw the city with the real renderer.
5. Check the engine state and the pixels.
6. Get a definite pass or fail.

The tests stay in the repository. Claude runs all of them again after each change, in the same way as end-to-end tests.

The user stated the main rule: **if a person still has to check the results by hand, the tool has failed.** Each test must end with a pass or a fail that a program decides.

## 2. Goals

- **G1. Autonomy.** One command runs one test or all tests. The command opens no menu, waits for no input and shows no window on the screen. Claude starts it, reads the output and decides the next step without the user.
- **G2. Any state.** A test starts from a base savegame and changes it: it places buildings, sets terrain, stock, money, the date, event state and custom variables, and imports scenario events.
- **G3. Exact time.** A test runs an exact number of ticks, days or months, or runs to a set date.
- **G4. Definite checks.** A test checks engine data (money, stock, buildings, event state, terrain) and pixels (comparison with an approved image, seam check, HD sprite use). Each check gives pass or fail with a clear message.
- **G5. Same result in each run.** The same code and the same test give the same state and the same pixels in each run.
- **G6. Real rendering.** Captures use the same SDL2 renderer and GPU path as the game that the player runs, at any zoom level and camera position.
- **G7. Data for Claude.** Each run writes the captures, the difference images and a state dump to a results folder. Claude reads these files to find the cause of a failure.

### Main use cases (from the user)

| Use case | What the test does |
|---|---|
| Scenario events | Import or edit an event, set up its condition (for example a building count or a stock level), run, then check that the event ran and that its actions changed the state. |
| Monthly goods use | Set up houses, markets and stock, run to the end of the month, then check the stock change against the rules in `docs/scenario-economy/catalogue/`. |
| HD sprite rendering | Draw known terrain, buildings and figures at many zoom levels and camera offsets. Check for seams between tiles, check that the HD sprite is drawn and not the original sprite, and compare with approved images. The user found the last bug of this type: seams between flat terrain tiles at some zoom levels (fixed in `2b6e0ca02`). |

Other cases, for example the earthquake and other disasters, use the same commands. The design does not depend on one of them.

## 3. Non-goals

- CI on GitHub, Linux or Windows. The harness runs only on the user's Mac for now.
- SDL3. The Mac build uses SDL2 (`build/CMakeCache.txt`: `SDL_VERSION=2`).
- Tests that click menus or dialogs. The harness tests the simulation and the city view, not the UI screens.
- The map editor.
- Performance tests and fuzz tests.

## 4. Anti-goals (the design has failed if one of these is true)

- A person, or Claude, must look at a screenshot to decide pass or fail.
- A test gives a different result on a second run with the same code (a flaky test).
- The test mode changes the game for a player who does not use it.
- An approved image changes without an explicit approval step that shows in `git diff`.

## 5. Decisions of the user

- The start state is **a base savegame that Claude changes**, not a city built from an empty map.
- The tests are a regression suite in the repository. Claude runs all tests after each change.
- The suite runs only on this Mac.
- Claude drives the whole process without supervision.
- A pass or a fail must be definite (section 4).
- The tests use **a pinned copy of the HD sprite files in the repository**, not the live `~/caesar3/hd` folder (section 7.6.1).

## 6. Facts from the code that the design depends on

| Fact | Source |
|---|---|
| The command line takes only display options. The game cannot load a savegame from the command line. | `src/platform/arguments.c:82-138` |
| `game_run()` runs as many ticks as the real time allows. | `src/game/game.c:227-238`, `game_speed_get_elapsed_ticks()` |
| `game_animation_update()` uses the real clock. | `src/game/animation.c:22-24` |
| The savegame stores the random state of `random_generate_pool()`. A second generator, `random_from_stdlib()`, calls `srand(time())`. Game-state code calls it: scenario events and formulas, invasions, requests, distant battles, industry, crime, entertainers, race bets and empire objects. The weather and the clouds also call it, so it changes the pixels. | `src/core/random.c:53-115` |
| The custom earthquake keeps a delay counter in a function `static`. The savegame does not store it. | `src/scenario/earthquake.c:217` |
| A savegame loads with `game_file_load_saved_game()`. | `src/game/file.c:460` |
| The camera and the zoom: `city_view_go_to_grid_offset()`, `city_view_set_camera()`, `city_view_set_scale()`. The zoom range is 50% to `city_view_get_max_scale()`. | `src/city/view.c:424-620` |
| The full-city screenshot moves the camera and joins the parts into one image. | `src/graphics/screenshot.c:257-336` |
| The renderer reads pixels back with `SDL_RenderReadPixels` (`save_screen_buffer`). It can fall back to the software renderer. | `src/platform/SDL2/renderer.c:125-131, 1215-1218` |
| An image uses an HD texture when `img->hd.density` is not 0. | `src/platform/SDL2/renderer.c:525-526` |
| Scenario events import from XML. | `src/scenario/event/import_xml.c` |
| 21 cheat commands exist (money, invasion, curse, weather, destroy, monument phase and others). | `src/game/cheats.c:60-104` |
| The map dumper from the economy study links the engine objects and loads maps and savegames with no window. | `docs/scenario-economy/tools/dumper3.c` |
| The game data and the patched HD build are in `~/caesar3`. | `.claude/skills/c3-hd-sprites/SKILL.md` |

## 7. Design (calls by Claude unless marked)

### 7.1 Test mode in the game program

The harness is a test mode in the Augustus program, written in C, and compiled only with the CMake option `E2E_TESTS=ON` (default `OFF`). A normal build does not contain it. This meets anti-goal 3.

```sh
augustus --test tests/e2e/cases/seams_flat_meadow.txt --out <results dir> [--update-images] ~/caesar3
```

- The program runs one test file, writes the results and exits.
- Exit codes: 0 when all checks pass, 1 when a check fails, 2 when the test file or the setup has an error.
- Each test runs in a new process, so no file `static` state carries over from one test to the next.
- `tests/e2e/run.sh` runs all files in `tests/e2e/cases/`, prints one line for each test (`PASS` or `FAIL` and the first failed check) and exits with 1 if a test failed.

### 7.2 Test file format

The test file is plain text with one command on each line. `#` starts a comment. Claude and the user can read and edit it without the game. Example:

```text
# Houses at level 5 use pottery each month.
load small_city.svx
seed 1234
date 0 11 1                         # year offset, month, day
set stock warehouse 3 pottery 400
place house_level 5 at 40 52
mark
run month_end
check stock warehouse 3 pottery == mark - 24
capture houses camera 40 52 zoom 100
check image houses
```

Command groups:

| Group | Commands (the builder can rename them) |
|---|---|
| Start | `load <save>`, `load_map <scenario>`, `seed <n>` |
| Options | `config <key> <value>` |
| Change state | `place <building> at x y`, `clear x1 y1 x2 y2`, `terrain <type> x1 y1 x2 y2`, `set money`, `set stock`, `set favor`, `date`, `variable <name> <value>`, `events <xml file>`, `cheat <cheat command>`, `save <file>` |
| Time | `run ticks <n>`, `run days <n>`, `run months <n>`, `run month_end`, `run until <date>` |
| State checks | `check <query> <op> <value>`. The ops are `== != < <= > >=`. `mark` stores the value of each later query, so `mark - 24` is a change since the mark. |
| Captures | `capture <name> camera x y zoom z [offset dx dy] [overlay <type>] [size w h]` |
| Image checks | `check image <name> [tolerance]`, `check seams <name> region x1 y1 x2 y2`, `check hd <name> [group]` |
| Output | `dump <name>`: writes the full state to `state_<name>.json` |

The state changes use the engine functions, for example `building_create()` and the storage functions, so that the state stays valid. Where an event action already makes the same change (money, stock, favor), the command calls that action handler and does not repeat the code.

The queries for `check` are a fixed list in C, for example `money`, `population`, `stock <building> <resource>`, `city_stock <resource>`, `building_count <type>`, `building <id> state`, `house <id> level`, `event <id> executions`, `variable <name>`, `terrain x y`, `favor` and `month`. The builder adds a query when a test needs it.

### 7.3 Base savegames

- The base savegames are in `tests/e2e/saves/`.
- Each base savegame has a recipe test file. The recipe loads a scenario map, makes the changes and ends with `save`. This lets Claude make the base savegame again after a save version change, and the recipe shows how the savegame was made.
- First set: a flat area of one terrain type for the rendering tests, a small city with houses, markets, a granary and a warehouse, and a map with scenario events.

### 7.4 Same result in each run (G5)

- The test mode calls `game_tick_run()` directly for each tick. It does not use the real clock or `game_speed_get_elapsed_ticks()`.
- `seed` sets the random state. In test mode, `random_from_stdlib()` uses the seed and does not read the clock. The savegame random state (`iv1`, `iv2`) also takes a value from the seed.
- The animation frame advances with the test ticks, not with the real clock. A capture then shows the same animation frame in each run.
- Test mode does not read the user's `augustus.ini` or the user's gameplay settings. It uses the built-in defaults. A test changes one option with `config <key> <value>`. The expected values in a test match the defaults unless the test sets an option. (Claude's call.)
- The custom earthquake delay counter moves into the saved earthquake state, or the test mode resets it at load. This is a defect in the game, and the builder fixes it in a separate commit with a save version increase if needed (see `CLAUDE.md`, savegame versioning).
- A check in the suite runs each test two times and compares the state dumps and the captures. A difference is a failure.

### 7.5 Rendering (G6)

- The test mode opens an SDL2 window with `SDL_WINDOW_HIDDEN` and the normal accelerated renderer, at a fixed size (default 1280 × 800) and display scale 100%. The window does not show on the screen.
- If the hidden window does not draw on macOS, the renderer draws to a target texture and reads that texture. The builder confirms which method gives the same pixels as the visible game.
- A capture draws the normal city window (`window_city`) with the given camera, zoom and overlay. It reads the city viewport with `save_screen_buffer` and writes a PNG.
- A capture can be larger than the window. The test mode then joins the parts, as the full-city screenshot does.
- The test fails with exit code 2 if the program falls back to the software renderer. A software capture does not show the GPU filter defects (for example the seam bug).

### 7.6 Image checks (G4, anti-goals 1 and 4)

**Comparison with an approved image.** `check image <name>` compares the capture with `tests/e2e/images/<test>/<name>.png`.
- The check fails if more than a set number of pixels differ by more than a set value in one colour channel. The defaults are strict, and a test can change them.
- At a failure, the harness writes `actual.png`, `approved.png` and `diff.png` (changed pixels in a strong colour, other pixels in grey) and prints the bounding box of the changes.
- `--update-images` writes the capture as the new approved image. This is the only way to change an approved image. The new image shows in `git diff` and goes into the commit of the change that caused it.
- When there is no approved image, the check fails and tells Claude to run with `--update-images`.

**Seam check.** `check seams <name> region x1 y1 x2 y2` needs no approved image.
- The test fills the region with one flat terrain type.
- The check finds the screen positions of the tile edges in the region, from the camera, the zoom and the tile size. It then looks for a line of pixels along an edge that is darker or lighter than the pixels on both sides of the line by more than a set value.
- A failure gives the zoom, the camera offset and the screen position, and writes a cropped and enlarged image of the seam.
- The builder chooses the exact method. It must meet the acceptance test in section 8 (A1).

**HD check.** `check hd <name> [group]` counts the images that the renderer drew in the capture with an HD texture and without one (`img->hd.density`). The check fails if an image of the given group was drawn without an HD texture. A counter in the SDL2 renderer, compiled only in test mode, supplies the numbers.

### 7.6.1 Pinned HD sprite files (decision of the user)

- `src/core/image_hd.c` loads HD files from `hd/` in the data folder (`HD_BASE_DIR`). In test mode, the HD folder is `tests/e2e/hd/` in the repository, not `~/caesar3/hd`.
- `tests/e2e/hd/` has the same layout as `~/caesar3/hd` (`c3/`, `c3_north/`, `c3_south/`). On 2026-10-25 it is 6.5 MB with 331 PNG files.
- `tests/e2e/sync_hd.sh` copies `~/caesar3/hd` into `tests/e2e/hd/`. A sprite change goes into one commit with the new HD files and the new approved images. `git diff` then shows both.
- The result of a test depends only on the repository and the original Caesar 3 data files.

### 7.7 Results folder (G7)

```text
<results dir>/<test name>/
  log.txt                every command, every check with its value, pass or fail
  state_<name>.json      from dump commands, and an automatic dump at the first failure
  <capture>.png
  <capture>.diff.png     only when an image check fails
  <capture>.seam_*.png   only when a seam check fails
<results dir>/summary.txt   one line for each test
```

### 7.8 Files

- `src/game/e2e*.c` (or a new `src/test/` directory): the parser, the commands, the queries and the image checks. Each new `.c` file goes in a file list in `CMakeLists.txt`, inside the `E2E_TESTS` option.
- `src/platform/arguments.c`, `src/platform/SDL2/augustus.c`: the `--test` option and the test loop, with `#ifdef` for `E2E_TESTS`.
- `src/platform/SDL2/renderer.c`: the HD draw counter, with `#ifdef`. SDL3 is a non-goal, so `src/platform/SDL3/` does not change. This breaks the rule that the two renderers stay the same, and the change is test-only code.
- `tests/e2e/cases/`, `tests/e2e/saves/`, `tests/e2e/images/`, `tests/e2e/hd/`, `tests/e2e/sync_hd.sh`, `tests/e2e/run.sh`, `tests/e2e/README.md`.

## 8. Acceptance tests

The harness is complete when all of these are true:

- **A1. Seam regression.** A test fills a region with flat meadow. It captures the region at each zoom from 50% to 200% in steps of 5%, with two camera offsets, and runs `check seams`. The test passes on `master`. With the `src/core/image_hd.c` part of `2b6e0ca02` reverted on the harness branch, the test fails at some zoom levels in the 80–150% range. The harness is not built on the old commit. (Claude's call.)
- **A2. Monthly goods use.** A test sets up houses, a market and a granary, runs to the end of the month and checks the change in food and goods against the rules in the catalogue.
- **A3. Event.** A test imports an XML event with a condition and an action, sets up the condition, runs and checks that the event ran and that its action changed the state. A second test checks that the event does not run when the condition is false.
- **A4. Same result.** `run.sh --twice` gives identical state dumps and identical captures for all tests.
- **A5. Clear failure.** A test with a check that cannot pass exits with code 1 and prints the check, the expected value and the actual value. A test file with a syntax error exits with code 2 and prints the line number.
- **A6. No window.** A full run of the suite shows no window on the screen and needs no input.
- **A7. Normal build.** A build with `E2E_TESTS=OFF` gives no new warnings and contains no test code.

## 9. Left to the builder

- The exact command names and the query list.
- The seam detection method and its threshold values, within A1.
- The hidden-window or target-texture method, within section 7.5.
- The default image tolerance.
- The JSON layout of the state dump.
