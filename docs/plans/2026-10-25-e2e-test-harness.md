# End-to-end test harness: implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** a test mode in the Augustus program. It runs a text test file, which creates or loads a city and changes it. The test mode then runs exact ticks, draws in a hidden window, checks the state and the pixels, and exits with pass or fail.

**Architecture:** the C code is compiled only with `-DE2E_TESTS=ON`. `--test <file>` replaces the SDL main loop with a loop that runs the test commands and calls `game_tick_run()` and `game_draw()` directly. `tests/e2e/run.sh` runs each case file in a new process and compares the exit code with the `# expect:` line of the case.

**Tech Stack:** C99, SDL2, spng (`ext/spng`, used by `src/graphics/screenshot.c`), CMake, POSIX shell.

**Spec:** `docs/superpowers/specs/2026-10-25-e2e-test-harness-design.md`

## Context

Augustus has no automated tests. The spec gives the reasons, the decisions of the user and the acceptance tests A1–A7. Read the spec before you start a task.

## Global Constraints

- Write all prose and code comments in Simplified Technical English (`CLAUDE.md`).
- All test-mode code is inside `#ifdef E2E_TESTS`, or in files that only the `E2E_TESTS` option compiles. A build with `E2E_TESTS=OFF` has no test code and no new warnings (A7).
- Only SDL2. Do not change `src/platform/SDL3/`.
- Test mode does not read `augustus.ini` or the user settings. It uses `config_get_default_value()` for each key.
- Test mode loads HD sprites from `tests/e2e/hd/`, not from `~/caesar3/hd`.
- Exit codes: 0 = all checks pass, 1 = a check failed, 2 = a test file error or a setup error.
- The Caesar 3 data folder is `~/caesar3`. `run.sh` takes it from `C3_DATA`, default `~/caesar3`.
- The build folder for the harness is `build-e2e/`, separate from `build/`.
- Commits: Conventional Commits. Scope `game` for `src/game/e2e*.c`, `core`/`platform`/`scenario` for changes there, `claude` for `tests/` and docs.
- Do not change a savegame format without the steps in `src/game/save_version.h`.

## Review Focus

1. **A command that the parser does not know, or a missing argument.** Expected: exit 2 and `line N: <message>`, never a crash and never a silent skip. Test: `tests/e2e/cases/error_unknown_command.txt` (Task 1).
2. **A `load` of a savegame that does not exist, or a map size that is not valid.** Expected: exit 2 with the path. Test: `error_missing_save.txt` (Task 3).
3. **A capture region that is partly outside the map, or a zoom outside 50 to max.** Expected: exit 2 with the region and the valid range, not a black image that passes. Test: `error_capture_outside.txt` (Task 4).
4. **A first run of `check image` with no approved image.** Expected: exit 1, and the message tells Claude to run `--update-images`. The check never passes silently. Test: `image_missing_approved.txt` (Task 4).
5. **The GPU renderer is not available and SDL falls back to the software renderer.** Expected: exit 2 with `software renderer`. Test: run once with `SDL_RENDER_DRIVER=software` in Task 4, step 6.

---

## File structure

| File | Responsibility |
|---|---|
| `src/game/e2e.h` | Public entry: `int e2e_run(const char *test_file, const char *out_dir, int update_images);` |
| `src/game/e2e.c` | Parser, command table, run loop, log, exit code |
| `src/game/e2e_state.c`, `.h` | State-change commands and the query list for `check` and `dump` |
| `src/game/e2e_image.c`, `.h` | Capture, PNG write and read, approved-image compare, seam check, HD check |
| `src/platform/arguments.c`, `.h` | `--test`, `--out`, `--update-images` |
| `src/platform/SDL2/augustus.c` | Hidden window, call of `e2e_run()` in place of the main loop |
| `src/platform/SDL2/screen.c` | `SDL_WINDOW_HIDDEN` in test mode |
| `src/platform/SDL2/renderer.c` | HD draw counter |
| `src/core/random.c` | Seed for `random_from_stdlib()` in test mode |
| `src/core/image_hd.c` | HD folder override |
| `src/game/animation.c` | Animation timers from test ticks |
| `src/scenario/earthquake.c` | Store the custom earthquake delay counter |
| `CMakeLists.txt` | `E2E_TESTS` option, `E2E_FILES` list |
| `tests/e2e/run.sh` | Runs cases, compares exit codes, `--twice`, summary |
| `tests/e2e/sync_hd.sh` | Copies `~/caesar3/hd` to `tests/e2e/hd/` |
| `tests/e2e/cases/*.txt`, `saves/`, `images/`, `hd/`, `README.md` | The suite |

The test file format is in spec section 7.2. Each case file starts with `# expect: pass`, `# expect: fail` or `# expect: error`. `run.sh` maps these to exit codes 0, 1 and 2.

---

### Task 1: Build option, test mode entry, parser, `run ticks`, `check`

**Files:**
- Modify: `CMakeLists.txt` (after line 218 add the option block, after the `GAME_FILES` list add `E2E_FILES`), `src/platform/arguments.c`, `src/platform/arguments.h`, `src/platform/SDL2/augustus.c`, `src/platform/SDL2/screen.c`
- Create: `src/game/e2e.h`, `src/game/e2e.c`, `src/game/e2e_state.h`, `src/game/e2e_state.c`, `tests/e2e/run.sh`, `tests/e2e/cases/smoke_money.txt`, `tests/e2e/cases/error_unknown_command.txt`, `tests/e2e/cases/fail_check.txt`

**Interfaces:**
- Produces:
  - `int e2e_run(const char *test_file, const char *out_dir, int update_images);` returns the exit code.
  - In `e2e.c`: `typedef int (*e2e_command_fn)(int argc, char **argv);`. A command returns `E2E_OK` (0), `E2E_CHECK_FAILED` (1) or `E2E_ERROR` (2). `void e2e_log(const char *format, ...);` writes to `<out>/<test>/log.txt` and to stdout. `void e2e_error(const char *format, ...);` adds `line N: `.
  - In `e2e_state.h`: `int e2e_query(int argc, char **argv, int *value);` returns 1 when the query name is known. The first queries: `money`, `tick`, `day`, `month`, `year`.
  - `augustus_args` gets `const char *test_file; const char *test_out_dir; int test_update_images;`.

- [ ] **Step 1: Write the case files**

`tests/e2e/cases/smoke_money.txt`:
```text
# expect: pass
load_map Caesar_Valencia        # any map in ~/caesar3/maps; the builder picks one that exists
check money > 0
run ticks 50
check tick < 50                  # a day has 50 ticks (0 to 49)
```
`error_unknown_command.txt`: `# expect: error` and the line `frobnicate 1`.
`fail_check.txt`: `# expect: fail`, a `load_map` line and `check money == -1`.

- [ ] **Step 2: Write `tests/e2e/run.sh`**

Usage: `tests/e2e/run.sh [--twice] [--update-images] [case ...]`. Defaults: all `tests/e2e/cases/*.txt`, binary `build-e2e/augustus.app/Contents/MacOS/augustus`, data `${C3_DATA:-$HOME/caesar3}`, results `build-e2e/e2e-results/`. For each case it prints `PASS <name>` or `FAIL <name>: expected <x>, got exit <n>: <last line of log.txt>`, writes `summary.txt` and exits 1 if one case did not match. `--twice` is Task 2.

- [ ] **Step 3: Run it and see it fail**

Run: `cmake -S . -B build-e2e -DE2E_TESTS=ON && cmake --build build-e2e -j8 && tests/e2e/run.sh`
Expected: three `FAIL` lines. The binary rejects `--test` as an unknown option.

- [ ] **Step 4: Implement**

- `CMakeLists.txt`: `option(E2E_TESTS "Build the end-to-end test mode." OFF)`. If on: `add_definitions(-DE2E_TESTS)` and append `E2E_FILES` to `SOURCE_FILES`.
- `arguments.c`: parse `--test FILE`, `--out DIR`, `--update-images`, inside `#ifdef E2E_TESTS`. Add them to the help text.
- `screen.c`: in test mode add `SDL_WINDOW_HIDDEN` to `flags` and do not add `SDL_WINDOW_FULLSCREEN_DESKTOP`. Window size 1280 × 800.
- `augustus.c` `setup()`: in test mode, directly after `pre_init()`, set each config key to `config_get_default_value()` (this undoes the `config_load()` in `game_pre_init()`), and set the display to windowed 1280 × 800 with `setting_set_display(0, 1280, 800)`. After `game_init()`, `main()` calls `exit_with_status(e2e_run(...))` and does not enter `main_loop()`.
- `e2e.c`: read the file line by line, strip `#` comments, split on spaces, look up the command, stop at the first `E2E_ERROR`. A failed check logs `FAIL line N: check <query> <op> <value>: actual <v>` and the run continues, so one run reports all failed checks. The exit code is the highest code of all commands.
- Commands in this task: `load_map <name>` (calls `game_file_start_scenario_by_name()`, then `window_city_show()`), `run ticks <n>` (calls `game_tick_run()` n times, then `game_draw()` once), `check <query> <op> <value>`.

- [ ] **Step 5: Run and see it pass**

Run: `cmake --build build-e2e -j8 && tests/e2e/run.sh`
Expected: three `PASS` lines. No window shows on the screen.

- [ ] **Step 6: Check the normal build**

Run: `cmake --build build -j8 2>&1 | grep -c warning`
Expected: the same count as on `master`.

- [ ] **Step 7: Commit**

`feat(game): add end-to-end test mode with check and run commands`

---

### Task 2: Same result in each run

**Files:**
- Modify: `src/core/random.c`, `src/core/random.h`, `src/game/animation.c`, `src/game/e2e.c`, `src/scenario/earthquake.c`, `src/game/save_version.h` (only if the counter goes into the save), `tests/e2e/run.sh`
- Create: `tests/e2e/cases/determinism_city.txt`

**Interfaces:**
- Consumes: `e2e_run`, the command table (Task 1).
- Produces: `void random_set_test_seed(uint32_t seed);` in `random.h`, inside `#ifdef E2E_TESTS`. `seed <n>` command. `dump <name>` command, which writes `state_<name>.json` with every query from `e2e_query` and a hash of the building and figure arrays.

- [ ] **Step 1: Write the case and the `--twice` mode**

`determinism_city.txt`: `# expect: pass`, `load_map` of a map with invasions or crime, `seed 1234`, `run ticks 5000`, `dump end`.
`run.sh --twice`: run each case two times into two result folders and compare every `state_*.json` and every `*.png` with `cmp`. A difference is a `FAIL` with the file name.

- [ ] **Step 2: Run and see it fail**

Run: `tests/e2e/run.sh --twice determinism_city`
Expected: `FAIL determinism_city: state_end.json differs` (the hash differs, because `random_from_stdlib()` reads the clock), or `seed` is an unknown command.

- [ ] **Step 3: Implement**

- `random.c`: with a test seed set, `random_from_stdlib()` calls `srand(seed)` once and does not read `time()`. `random_set_test_seed()` also sets `iv1` and `iv2` from the seed.
- `animation.c`: in test mode `game_animation_update()` uses a test clock that advances 20 ms for each test tick, not `time_get_millis()`.
- `earthquake.c`: the `static int custom_delay` in `scenario_earthquake_process()` moves into `data`, and `scenario_earthquake_save_state()` / `load_state()` write and read it. Follow `src/game/save_version.h`: a new version, a `SAVE_GAME_LAST_*` marker, a read with a `version >` check and a default of 0. This change is a game fix, so it goes in its own commit: `fix(scenario): save the custom earthquake delay counter`.

- [ ] **Step 4: Run and see it pass**

Run: `tests/e2e/run.sh --twice`
Expected: all `PASS`.

- [ ] **Step 5: Commit** (two commits: the earthquake fix, then `feat(game): make e2e runs repeatable with a fixed seed`)

---

### Task 3: State commands, queries and base savegames

**Files:**
- Modify: `src/game/e2e_state.c`, `src/game/e2e_state.h`, `src/game/e2e.c`
- Create: `tests/e2e/cases/make_flat_meadow.txt`, `make_small_city.txt`, `monthly_food.txt`, `monthly_pottery.txt`, `event_money_runs.txt`, `event_money_not_runs.txt`, `error_missing_save.txt`, `tests/e2e/events/money_bonus.xml`, `tests/e2e/saves/` (output of the `make_*` cases)

**Interfaces:**
- Consumes: the command table, `e2e_query` (Task 1), `seed`, `dump` (Task 2).
- Produces: the commands of spec section 7.2 groups Start, Options, Change state, Time and State checks. The `make_*` cases write `tests/e2e/saves/flat_meadow.svx` and `small_city.svx`.

Command details that the builder needs:
- `new_map <size> [climate]`: `game_file_editor_create_scenario(size)`, set the climate, set an entry point and an exit point, allow all buildings (`scenario_allowed_building_set()`), write the scenario to `<out>/new_map.mapx` with `game_file_editor_write_scenario()`, then start it as a game. The size is one of the editor sizes (40, 60, 80, 100, 120, 160). Other values: exit 2.
- `place <building> at x y`: `building_construction_place_building(type, x, y, 1)`. Building names use the XML names in `src/scenario/event/parameter_data.c`, so that test files and event files use one term. Fail with exit 2 when the engine rejects the place.
- `set stock <building id> <resource> <amount>` and `set house <id> <resource> <amount>`: write the building storage or the house inventory.
- `set house <id> level <xml house name>` (`building_house_change_to()`), `set house <id> population <n>`, `set money <n>`, `set favor <n>`, `date <year offset> <month> <day>`, `variable <name> <value>`, `config <key> <value>`.
- `events <xml file>`: `scenario_events_xml_parse_file()`.
- `cheat <text>`: `game_cheat_parse_command()`.
- `save <file>`: `game_file_write_saved_game()`. `load <file>`: `game_file_load_saved_game()`.
- `run days|months <n>`, `run month_end` (run until `game_time_month()` changes, then 1 more tick), `run until <year offset> <month>`.
- `mark`, and the `mark` operand in `check`.
- Queries: `population`, `favor`, `stock <id> <resource>`, `city_stock <resource>`, `building_count <name>`, `building <id> state`, `house <id> level`, `house <id> population`, `house <id> <resource>`, `event <id> executions`, `variable <name>`, `terrain x y`.

- [ ] **Step 1: Write the cases**

`monthly_food.txt` (the rule is in `src/city/resource.c:516-570`: a house eats `population × 50 / 100` of each available food type, divided by the number of types):
```text
# expect: pass
load small_city.svx
seed 1
date 0 0 1
set house 1 level small_shack    # food_types must be >= 1; tents eat nothing (resource.c:525). Confirm the level with model_get_house().
set house 1 population 40
set house 1 wheat 200
run month_end
check house 1 level == small_shack
check house 1 population == 40   # the house in small_city has no road to the entry, so no migrants come
check house 1 wheat == 180       # 40 x 50 / 100 = 20
```
`monthly_pottery.txt`: the same, with the pottery rule in `src/building/house_evolution.c:520-600`. Put the expected value and the source line in a comment.
`tests/e2e/events/money_bonus.xml`:
```xml
<?xml version="1.0"?>
<!DOCTYPE events>
<events version="2">
    <event id="0">
        <conditions>
            <money check="gte" value="5000"/>
        </conditions>
        <actions>
            <money_add formula="1000"/>
        </actions>
    </event>
</events>
```
`event_money_runs.txt`: `load small_city.svx`, `events money_bonus.xml`, `set money 6000`, `mark`, `run months 1`, `check event 0 executions == 1`, `check money >= mark + 1000` (wages and taxes also change the money; `small_city` has no workers and no tax, so the builder can use `==` if the run confirms it).
`event_money_not_runs.txt`: the same with `set money 100` and `check event 0 executions == 0`.
`error_missing_save.txt`: `# expect: error`, `load no_such.svx`.

- [ ] **Step 2: Run and see them fail**

Run: `tests/e2e/run.sh`
Expected: the new cases fail with `unknown command`.

- [ ] **Step 3: Implement the commands and queries, then run `make_flat_meadow` and `make_small_city` to create the savegames**

`make_flat_meadow.txt`: `new_map 80`, `terrain meadow 0 0 79 79`, `save flat_meadow.svx`. `make_small_city.txt`: `new_map 60`, one house, one market, one granary and one warehouse, no road to the entry point, `save small_city.svx`. `save` writes to `tests/e2e/saves/` when the file name has no folder.

- [ ] **Step 4: Run and see them pass**

Run: `tests/e2e/run.sh && tests/e2e/run.sh --twice`
Expected: all `PASS`.

- [ ] **Step 5: Commit**

`feat(game): add e2e state commands, queries and base savegames`

---

### Task 4: Capture and approved-image compare

**Files:**
- Create: `src/game/e2e_image.c`, `src/game/e2e_image.h`, `tests/e2e/cases/image_flat_meadow.txt`, `image_missing_approved.txt`, `error_capture_outside.txt`
- Modify: `src/game/e2e.c`, `CMakeLists.txt` (`E2E_FILES`)

**Interfaces:**
- Consumes: the command table, `save_screen_buffer` in `graphics_renderer()`, `city_view_set_scale()`, `city_view_go_to_grid_offset()`, `window_city_draw_all()`.
- Produces:
  - `int e2e_capture(const char *name, int x, int y, int zoom, int dx, int dy, int width, int height);` keeps the pixels in memory under the name and writes `<out>/<test>/<name>.png`.
  - `const color_t *e2e_capture_pixels(const char *name, int *width, int *height);`
  - `int e2e_check_image(const char *name, int max_channel_diff, int max_pixels);` default `max_channel_diff` = 0, `max_pixels` = 0.
  - Commands `capture` and `check image`.

- [ ] **Step 1: Write the cases**

`image_flat_meadow.txt`: `# expect: pass`, `load flat_meadow.svx`, `seed 1`, `capture meadow camera 40 40 zoom 100`, `check image meadow`.
`image_missing_approved.txt`: `# expect: fail`, a capture with a name that has no approved image, `check image nothing_here`. The log must contain `run with --update-images`.
`error_capture_outside.txt`: `# expect: error`, `capture x camera 79 79 zoom 100 size 2000 2000`.

- [ ] **Step 2: Run and see them fail**

Expected: `unknown command capture`.

- [ ] **Step 3: Implement**

- Capture: set the scale and the camera, call `window_city_draw_all()`, then read the city viewport with `graphics_renderer()->save_screen_buffer()`. The renderer draws into `render_texture` (`src/platform/SDL2/renderer.c:1416-1424`), so the read does not depend on the window being visible. Confirm this: capture the same view in the normal visible game with the screenshot hotkey and compare the pixels once by hand during development. Write the result in `tests/e2e/README.md`.
- In test mode, after `platform_renderer_init()`, `SDL_GetRendererInfo()` must not report `SDL_RENDERER_SOFTWARE`. Else exit 2 with `software renderer`.
- PNG write and read with spng, in the same way as `src/graphics/screenshot.c:114-216`.
- Compare: at a failure write `<name>.actual.png`, `<name>.approved.png` and `<name>.diff.png` (changed pixels in magenta, other pixels as grey) and log the count and the bounding box.
- `--update-images` writes the capture to `tests/e2e/images/<test>/<name>.png` and the check passes.

- [ ] **Step 4: Approve the first image and run**

Run: `tests/e2e/run.sh --update-images image_flat_meadow && tests/e2e/run.sh && tests/e2e/run.sh --twice`
Expected: all `PASS`.

- [ ] **Step 5: Check the software renderer refusal**

Run: `SDL_RENDER_DRIVER=software tests/e2e/run.sh image_flat_meadow`
Expected: `FAIL ... got exit 2: software renderer`.

- [ ] **Step 6: Commit**

`feat(game): add e2e capture and approved image compare`

---

### Task 5: Pinned HD sprites and the HD check

**Files:**
- Modify: `src/core/image_hd.c`, `src/core/image_hd.h`, `src/platform/SDL2/renderer.c`, `src/game/e2e_image.c`, `src/game/e2e.c`
- Create: `tests/e2e/sync_hd.sh`, `tests/e2e/hd/` (copied files), `tests/e2e/cases/hd_flat_meadow.txt`

**Interfaces:**
- Produces:
  - `void image_hd_set_base_dir(const char *dir);` in `image_hd.h`, inside `#ifdef E2E_TESTS`. `build_dir_name()` uses it in place of `HD_BASE_DIR`. `e2e_run()` sets it to the absolute path of `tests/e2e/hd` before it loads a map (the climate load calls `image_hd_load()`).
  - In `renderer.c`, inside `#ifdef E2E_TESTS`: `void platform_renderer_e2e_reset_counts(void);` and `int platform_renderer_e2e_count(int image_group, int is_hd);`. `draw_texture_advanced` adds one to the count of the image group for each draw.
  - Command `check hd <capture> [group]`.

- [ ] **Step 1: Write `sync_hd.sh` and the case**

`sync_hd.sh`: `rsync -a --delete ~/caesar3/hd/ tests/e2e/hd/` and print the file count and the size.
`hd_flat_meadow.txt`: `# expect: pass`, `load flat_meadow.svx`, `capture meadow camera 40 40 zoom 100`, `check hd meadow terrain`. The group names are the names in `src/core/image_group.h`, written in lowercase without the `GROUP_` prefix.

- [ ] **Step 2: Run and see it fail**

Expected: `unknown command check hd`.

- [ ] **Step 3: Implement, run `sync_hd.sh`, run the suite**

Run: `tests/e2e/sync_hd.sh && tests/e2e/run.sh`
Expected: `hd_flat_meadow` passes. `image_flat_meadow` fails, because the approved image was made with the live HD folder. Run `tests/e2e/run.sh --update-images image_flat_meadow` and look at `git diff --stat tests/e2e/images`: one image changes.

- [ ] **Step 4: Check that the HD check can fail**

Run once with `tests/e2e/hd/` renamed away: `hd_flat_meadow` must exit 1. Rename it back.

- [ ] **Step 5: Commit**

`feat(game): load pinned hd sprites in e2e mode and check hd use` (the HD files go in the same commit)

---

### Task 6: Seam check and the seam regression (A1)

**Files:**
- Modify: `src/game/e2e_image.c`, `src/game/e2e.c`
- Create: `tests/e2e/cases/seams_flat_meadow.txt`

**Interfaces:**
- Consumes: `e2e_capture`, `e2e_capture_pixels` (Task 4).
- Produces: `int e2e_check_seams(const char *capture, int x1, int y1, int x2, int y2);`, command `check seams <capture> region x1 y1 x2 y2`, and a `repeat zoom <from> <to> <step> offsets <dx,dy> ...` block that repeats the lines up to `end` for each zoom and each camera offset, with `{zoom}` and `{dx}` `{dy}` put into the capture name.

- [ ] **Step 1: Write the case**

```text
# expect: pass
load flat_meadow.svx
repeat zoom 50 200 5 offsets 0,0 7,3
capture seam_{zoom}_{dx}_{dy} camera 40 40 zoom {zoom} offset {dx} {dy}
check seams seam_{zoom}_{dx}_{dy} region 30 30 50 50
end
```

- [ ] **Step 2: Run and see it fail**

Expected: `unknown command repeat`.

- [ ] **Step 3: Implement the seam check**

Algorithm (the spec leaves the method to the builder; this is the plan's choice):
1. For each tile in the region, compute the screen positions of its four diamond edges from the camera, the zoom and the tile size of 58 × 30 pixels at 100%.
2. For each pixel `p` on an edge line, take the mean luminance of the pixels 2 to 3 pixels away from the line on each side.
3. `p` is a seam pixel if its luminance differs from both side means by more than 24 (on a scale of 0 to 255), in the same direction.
4. The check fails if one edge has a run of 6 or more seam pixels next to each other.
5. At a failure, log the zoom, the offset, the tile and the screen position, and write `<capture>.seam_<n>.png`: a 32 × 32 crop, enlarged 8 times.

- [ ] **Step 4: Run on master and see it pass**

Run: `tests/e2e/run.sh seams_flat_meadow`
Expected: `PASS`. If it fails, lower the threshold only after you look at the crop. A seam on master is a real bug, so report it and do not hide it.

- [ ] **Step 5: Show that the check finds the old bug**

Run: `git show 2b6e0ca02 -- src/core/image_hd.c | git apply -R`, build, `tests/e2e/run.sh seams_flat_meadow`, then `git checkout src/core/image_hd.c` and build again.
Expected: `FAIL` with seams at some zoom levels in 80–150%. Write the failed zoom list in the commit message.

- [ ] **Step 6: Commit**

`feat(game): add e2e seam check and flat meadow seam regression`

---

### Task 7: README and the full check

**Files:**
- Create: `tests/e2e/README.md`

- [ ] **Step 1: Write the README**

The README tells how to build (`cmake -S . -B build-e2e -DE2E_TESTS=ON`), how to run, the case file format (copy the table of spec section 7.2 with the final command names), how to approve images, how to use `sync_hd.sh`, and the result of the pixel check from Task 4, step 3.

- [ ] **Step 2: Run the full acceptance check**

Run: `tests/e2e/run.sh && tests/e2e/run.sh --twice && cmake --build build -j8`
Expected: all `PASS`, no window on the screen during the run (A6), and the normal build has the same warning count as `master` (A7).

- [ ] **Step 3: Commit**

`docs(claude): add e2e test harness readme`

## Verification

| Acceptance test (spec section 8) | Proof |
|---|---|
| A1 seam regression | Task 6, steps 4 and 5 |
| A2 monthly goods use | `monthly_food`, `monthly_pottery` (Task 3) |
| A3 event | `event_money_runs`, `event_money_not_runs` (Task 3) |
| A4 same result | `run.sh --twice` (Tasks 2–7) |
| A5 clear failure | `fail_check`, `error_unknown_command`, `error_missing_save`, `error_capture_outside` |
| A6 no window | Task 1, step 5 and Task 7, step 2 |
| A7 normal build | Task 1, step 6 and Task 7, step 2 |
