# End-to-end tests

The end-to-end tests run the real Augustus program in a test mode. Each test loads or makes a city, changes it, runs exact ticks, draws the city in a hidden window and checks the state and the pixels. Each test gives a pass or a fail. No person looks at a screenshot.

The design is in `docs/superpowers/specs/2026-10-25-e2e-test-harness-design.md`. The tests run only on macOS with SDL2.

## Build

```sh
cmake -S . -B build-e2e -DE2E_TESTS=ON
cmake --build build-e2e -j8
```

The option `E2E_TESTS` is `OFF` by default. A normal build has no test code.

## Run

```sh
tests/e2e/run.sh                      # all cases in tests/e2e/cases/
tests/e2e/run.sh monthly_food         # one case
tests/e2e/run.sh --twice              # each case two times; the dumps and the captures must be identical
tests/e2e/run.sh --update-images image_flat_grass   # write the captures as the approved images
```

`run.sh` prints `PASS <case>` or `FAIL <case>: expected <x>, got exit <n>: <last line of log.txt>` and exits with 1 when a case does not match.

| Variable | Default | Use |
|---|---|---|
| `C3_DATA` | `~/caesar3` | The Caesar 3 data folder |
| `E2E_BIN` | `build-e2e/augustus.app/Contents/MacOS/augustus` | The test binary |
| `E2E_RESULTS` | `build-e2e/e2e-results` | The results folder |
| `E2E_TIMEOUT` | `600` | The time limit for one case, in seconds |

One case can also run directly:

```sh
MallocPreScribble=1 MallocScribble=1 build-e2e/augustus.app/Contents/MacOS/augustus \
    --test tests/e2e/cases/monthly_food.txt --out /tmp/results ~/caesar3
```

The exit code is 0 when all checks pass, 1 when a check fails and 2 when the test file or the setup has an error. A crash gives another exit code, and no message box opens. At the first failed check, the test also writes `state_failure.json` and `state_failure.svx`. `run.sh` sets `MallocPreScribble` and `MallocScribble`: some save functions do not write all bytes of their buffers, and these variables make the bytes the same in each run.

## Tests of the tool

The tool has its own tests. Run them after a change to `src/game/e2e*.c`, to a test hook in the engine or to `run.sh`.

```sh
build-e2e/e2e_logic_test        # unit tests of src/game/e2e_logic.c (about 1 second)
tests/e2e/selftest.sh           # the unit tests, run.sh and the binary (about 20 seconds)
tests/e2e/selftest.sh --slow    # also builds the seam bug of 2b6e0ca02 and expects the seam case to fail
```

| Part | What it protects |
|---|---|
| `tests/e2e/unit/e2e_logic_test.c` | The parser, the ops, `mark`, the `{zoom}` replacement, the image compare and its tolerance, the seam finder (synthetic images with dark and light seams of a known depth), the HD group range |
| Cases that must fail (`check_continues`, `image_mismatch`, `hd_missing_meadow`, the `error_*` cases) | A failed check does not stop the test; the image check, the HD check and each error message |
| `selftest.sh`, fake binary | `run.sh`: the exit codes, `expect-log`, `expect-file`, the time limit, `--twice`, the `--update-images` guard |
| `selftest.sh`, real binary | Relative paths, the seed, a bad data folder, the software renderer, a crash with no message box, `--update-images`, no HD folder, the user options not written, no test code in the normal build |
| `selftest.sh --slow` | The seam case finds the real seam bug |

`selftest.sh` cannot check that the window stays hidden. Look at the screen once after a change to the window code.

## Results

```text
build-e2e/e2e-results/<case>/
  log.txt                every command, every check with its value, pass or fail
  stdout.txt             the program output
  state_<name>.json      from dump: the queries and a hash of each savegame piece
  state_<name>.svx       from dump: the savegame, to load in the game
  <capture>.png
  <capture>.actual.png, <capture>.approved.png, <capture>.diff.png   when check image fails
  <capture>.seam_1.png   when check seams fails: a 32 x 32 crop, 8 times larger
build-e2e/e2e-results/summary.txt
```

## Test file format

A test file is plain text with one command on each line. `#` starts a comment. The first line is `# expect: pass`, `# expect: fail` or `# expect: error`. `run.sh` compares it with the exit code 0, 1 or 2.

A case can also have `# expect-log: <text>` lines and `# expect-file: <name>` lines. Each text must be in `log.txt`, and each file must be in the results folder. Use them in each case that expects a failure or an error, so that the case does not pass for a different reason.

Names of buildings, house levels and resources are the names of the scenario event XML files (`src/scenario/event/parameter_data.c` and `src/game/resource.c`), for example `vacant_lot`, `granary`, `small_shack` and `wheat`. Tile coordinates are map coordinates from 0.

| Group | Commands |
|---|---|
| Start | `new_map <40\|60\|80\|100\|120\|160> [central\|northern\|desert]`, `load <save>`, `load_map <scenario>`, `seed <n>` |
| Options | `config <key in augustus.ini> <value>` |
| Change state | `place <building> at x y [to x2 y2]`, `clear x1 y1 x2 y2`, `terrain <grass\|meadow\|trees\|rocks\|water\|shrub> x1 y1 x2 y2`, `set money <n>`, `set favor <n>`, `set stock <building id> <resource> <amount>`, `set house <id> level <level>`, `set house <id> population <n>`, `set house <id> <resource> <amount>`, `date <year offset> <month 0-11> <day 0-15>`, `variable <name> <value>`, `events <xml file>`, `cheat <cheat command>`, `save <file>` |
| Time | `run ticks <n>`, `run days <n>`, `run months <n>`, `run month_end`, `run until <year offset> <month>` |
| State checks | `check <query> <op> <value>`. The ops are `== != < <= > >=`. The value is a number, a building or house level name, `mark`, `mark + n` or `mark - n`. |
| Marks | `mark` stores the value of each query that a later check compares with `mark`, up to the next `mark`. |
| Captures | `capture <name> camera x y zoom z [offset dx dy] [size w h]` |
| Image checks | `check image <name> [max channel difference [max pixels]]`, `check seams <name> region x1 y1 x2 y2`, `check hd <name> [image group]` |
| Repeat | `repeat zoom <from> <to> <step> offsets <dx,dy> ...` up to `end`. The lines can use `{zoom}`, `{dx}` and `{dy}`. |
| Output | `dump <name>` |

Queries: `money`, `population`, `favor`, `tick`, `day`, `month`, `year`, `stock <building id> <resource>`, `city_stock <resource>`, `building_count <building>`, `building <id> state`, `building <id> type`, `house <id> level`, `house <id> population`, `house <id> <resource>`, `event <id> executions`, `variable <name>`, `terrain x y <terrain type>` (1 or 0).

Notes:

- `load`, `save` and `events` use `tests/e2e/saves/` and `tests/e2e/events/` when the name has no folder.
- A warehouse stock is in cart loads (at most 4 in each of 8 spaces). A granary stock is in units of 1.
- `run month_end` runs until the month changes, then 1 more tick.
- A capture is at most the size of the city viewport (1118 x 776 in the 1280 x 800 window). A capture that is partly outside the map, or a zoom outside 50 to the maximum, is an error.
- `check hd` without a group fails when no image was drawn with an HD texture. With a group, it also fails when an image of the group was drawn without an HD texture. The group names are in `GROUP_NAMES` in `src/game/e2e_image.c`.
- `check seams` (the code is in `src/game/e2e_logic.c`) compares each tile edge line (slope +1/2 or -1/2) with the parallel lines 1.5 to 3 pixels away. The limit is 16 (on a luminance scale of 0 to 255). On flat HD grass the worst line differs by at most 10.5 now, and by 26 to 35 at most zooms without the fix in `2b6e0ca02`.

## Base savegames

The files in `tests/e2e/saves/` come from the recipe cases `make_flat_grass.txt` and `make_small_city.txt`. A full run makes them again. After a save version change, the new files show in `git diff`; commit them with the change.

- `flat_grass.svx`: an 80 x 80 map with grass on all tiles. The grass images have HD sprites; the meadow images do not.
- `small_city.svx`: a 60 x 60 map with a house (building 1), a well, a market, a granary (building 4), a warehouse (building 5) and a road from the house to the entry point. A house with no road to the entry is removed after some days.

## Approved images

`check image <name>` compares the capture with `tests/e2e/images/<case>/<name>.png`. When there is no approved image, the check fails and tells you to run with `--update-images`. `--update-images` is the only way to change an approved image. Look at the new image, then commit it with the change that caused it.

## Pinned HD sprites

The test mode loads the HD sprites from `tests/e2e/hd/`, not from `~/caesar3/hd`. The result of a test depends only on the repository and the original Caesar 3 data.

```sh
tests/e2e/sync_hd.sh                       # copy ~/caesar3/hd to tests/e2e/hd/
tests/e2e/run.sh                           # image checks that use changed sprites fail
tests/e2e/run.sh --update-images <case>    # approve the new captures after a look
```

Commit the HD files and the new approved images together.

## Hidden window

The renderer draws the city into a render texture, and the capture reads that texture. A capture with a visible window (a build without `SDL_WINDOW_HIDDEN`) gave a PNG that is byte-identical to the capture with the hidden window (a flat meadow capture, checked on 2026-10-26). The test mode stops with exit code 2 when SDL uses the software renderer, because a software capture does not show the defects of the GPU texture filter.
