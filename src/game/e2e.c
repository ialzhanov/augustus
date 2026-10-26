#include "e2e.h"

#include "core/encoding.h"
#include "core/image.h"
#include "core/image_hd.h"
#include "core/file.h"
#include "core/lang.h"
#include "core/random.h"
#include "core/time.h"
#include "game/animation.h"
#include "game/e2e_image.h"
#include "game/e2e_state.h"
#include "game/file.h"
#include "game/file_io.h"
#include "game/game.h"
#include "game/file_editor.h"
#include "game/tick.h"
#include "platform/renderer.h"
#include "game/time.h"
#include "scenario/allowed_building.h"
#include "scenario/editor_map.h"
#include "scenario/event/controller.h"
#include "scenario/event/import_xml.h"
#include "scenario/property.h"
#include "window/city.h"

#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>

#define MAX_LINE 1024
#define MAX_LINES 2000
#define MAX_MARKS 64
// A run command stops after 200 years
#define MAX_RUN_TICKS (GAME_TIME_TICKS_PER_DAY * GAME_TIME_DAYS_PER_MONTH * GAME_TIME_MONTHS_PER_YEAR * 200)
#define MAX_ARGS 32
#define MAX_MESSAGE 1024
#define DEFAULT_OUT_DIR "e2e-results"
#define DEFAULT_SEED 0
#define MAX_SAVE_PIECES 200
// The animation timers advance 20 ms for each test tick
#define MILLIS_PER_TICK 20

typedef int (*e2e_command_fn)(int argc, char **argv);

typedef struct {
    const char *name;
    e2e_command_fn run;
} e2e_command;

typedef enum {
    OP_EQ,
    OP_NE,
    OP_LE,
    OP_GE,
    OP_LT,
    OP_GT,
    OP_NONE
} compare_op;

static const char *OP_NAMES[] = { "==", "!=", "<=", ">=", "<", ">" };

typedef struct {
    char query[MAX_LINE];
    int value;
} mark_value;

static const int MAP_SIZES[] = { 40, 60, 80, 100, 120, 160 };
#define NUM_MAP_SIZES (sizeof(MAP_SIZES) / sizeof(int))

static struct {
    int active;
    int line;
    int num_lines;
    char lines[MAX_LINES][MAX_LINE];
    mark_value marks[MAX_MARKS];
    int num_marks;
    char test_dir[FILE_NAME_MAX];
    int update_images;
    time_millis clock;
    FILE *log;
    char test_name[FILE_NAME_MAX];
    char out_dir[FILE_NAME_MAX];
    char first_problem[MAX_MESSAGE];
} data;

static void set_test_dir(const char *test_file);

void e2e_set_active(const char *test_file)
{
    data.active = 1;
    set_test_dir(test_file);
    char hd_dir[FILE_NAME_MAX];
    snprintf(hd_dir, FILE_NAME_MAX, "%s/hd", data.test_dir);
    image_hd_set_base_dir(hd_dir);
}

int e2e_is_active(void)
{
    return data.active;
}

static void write_line(const char *text)
{
    printf("%s\n", text);
    fflush(stdout);
    if (data.log) {
        fprintf(data.log, "%s\n", text);
        fflush(data.log);
    }
}

static void remember_problem(const char *text)
{
    if (!data.first_problem[0]) {
        snprintf(data.first_problem, MAX_MESSAGE, "%s", text);
    }
}

void e2e_log(const char *format, ...)
{
    char text[MAX_MESSAGE];
    va_list args;
    va_start(args, format);
    vsnprintf(text, MAX_MESSAGE, format, args);
    va_end(args);
    write_line(text);
}

void e2e_error(const char *format, ...)
{
    char message[MAX_MESSAGE];
    va_list args;
    va_start(args, format);
    vsnprintf(message, MAX_MESSAGE, format, args);
    va_end(args);
    char text[MAX_MESSAGE + 32];
    snprintf(text, sizeof(text), "ERROR line %d: %s", data.line, message);
    write_line(text);
    remember_problem(text);
}

static int command_dump(int argc, char **argv);

void e2e_check_failed(const char *format, ...)
{
    char message[MAX_MESSAGE];
    va_list args;
    va_start(args, format);
    vsnprintf(message, MAX_MESSAGE, format, args);
    va_end(args);
    char text[MAX_MESSAGE + 32];
    snprintf(text, sizeof(text), "FAIL line %d: %s", data.line, message);
    write_line(text);
    if (!data.first_problem[0]) {
        // Keep the state at the first failure for the debugging
        char command[] = "dump";
        char name[] = "failure";
        char *words[] = { command, name };
        command_dump(2, words);
    }
    remember_problem(text);
}

const char *e2e_out_dir(void)
{
    return data.out_dir;
}

const char *e2e_test_dir(void)
{
    return data.test_dir;
}

const char *e2e_test_name(void)
{
    return data.test_name;
}

int e2e_update_images(void)
{
    return data.update_images;
}

static void join_args(int argc, char **argv, char *text, int length)
{
    text[0] = 0;
    for (int i = 0; i < argc; i++) {
        if (i > 0) {
            strncat(text, " ", length - strlen(text) - 1);
        }
        strncat(text, argv[i], length - strlen(text) - 1);
    }
}

static int parse_int(const char *text, int *value)
{
    char *end;
    long result = strtol(text, &end, 10);
    if (!*text || *end) {
        return 0;
    }
    *value = (int) result;
    return 1;
}

static compare_op parse_op(const char *text)
{
    for (int i = 0; i < OP_NONE; i++) {
        if (strcmp(text, OP_NAMES[i]) == 0) {
            return i;
        }
    }
    return OP_NONE;
}

static int compare(int actual, compare_op op, int expected)
{
    switch (op) {
        case OP_EQ: return actual == expected;
        case OP_NE: return actual != expected;
        case OP_LE: return actual <= expected;
        case OP_GE: return actual >= expected;
        case OP_LT: return actual < expected;
        case OP_GT: return actual > expected;
        default: return 0;
    }
}

// The test clock replaces the real clock, so the animation frames are the same in each run
static void advance_clock(void)
{
    data.clock += MILLIS_PER_TICK;
    time_set_millis(data.clock);
    game_animation_update();
}

static void run_ticks(int ticks)
{
    for (int i = 0; i < ticks; i++) {
        advance_clock();
        game_tick_run();
    }
    game_draw();
}

// Runs ticks until the function returns 1. Returns 0 when the limit is reached first.
static int run_until(int (*is_done)(void))
{
    for (int i = 0; i < MAX_RUN_TICKS; i++) {
        if (is_done()) {
            game_draw();
            return 1;
        }
        advance_clock();
        game_tick_run();
    }
    return 0;
}

static int start_month;
static int until_year;
static int until_month;

static int is_new_month(void)
{
    return game_time_month() != start_month;
}

static int is_until_date(void)
{
    return game_time_year() == until_year && game_time_month() == until_month;
}

// Gives the path of a file in tests/e2e/<folder>/, or the name itself when it has a folder
static void get_test_path(const char *folder, const char *name, char *path)
{
    if (strchr(name, '/')) {
        snprintf(path, FILE_NAME_MAX, "%s", name);
    } else {
        snprintf(path, FILE_NAME_MAX, "%s/%s/%s", data.test_dir, folder, name);
    }
}

static void show_city(void)
{
    window_city_show();
    scenario_events_process_all();
}

static int command_load_map(int argc, char **argv)
{
    if (argc < 2) {
        e2e_error("load_map needs a scenario name");
        return E2E_ERROR;
    }
    char name_utf8[FILE_NAME_MAX];
    join_args(argc - 1, argv + 1, name_utf8, FILE_NAME_MAX);
    uint8_t name[FILE_NAME_MAX];
    encoding_from_utf8(name_utf8, name, FILE_NAME_MAX);
    scenario_set_name(name);
    scenario_set_custom(2);
    scenario_set_player_name(lang_get_string(9, 5));
    if (!game_file_start_scenario_by_name(name)) {
        e2e_error("cannot load the scenario map '%s'", name_utf8);
        return E2E_ERROR;
    }
    show_city();
    e2e_log("loaded map %s", name_utf8);
    return E2E_OK;
}

// Makes an empty map in the same way as the map editor, then starts it as a game
static int command_new_map(int argc, char **argv)
{
    static const char *CLIMATE_NAMES[] = { "central", "northern", "desert" };
    int size;
    int size_index = -1;
    if ((argc == 2 || argc == 3) && parse_int(argv[1], &size)) {
        for (unsigned int i = 0; i < NUM_MAP_SIZES; i++) {
            if (MAP_SIZES[i] == size) {
                size_index = i;
            }
        }
    }
    int climate = argc == 3 ? -1 : CLIMATE_CENTRAL;
    for (int i = 0; argc == 3 && i < 3; i++) {
        if (strcmp(argv[2], CLIMATE_NAMES[i]) == 0) {
            climate = i;
        }
    }
    if (size_index < 0 || climate < 0) {
        e2e_error("new_map needs: new_map 40|60|80|100|120|160 [central|northern|desert]");
        return E2E_ERROR;
    }
    game_file_editor_create_scenario(size_index);
    scenario_change_climate(climate);
    scenario_editor_set_entry_point(0, size / 2);
    scenario_editor_set_exit_point(size - 1, size / 2);
    for (building_type type = BUILDING_ANY; type < BUILDING_TYPE_MAX; type++) {
        scenario_allowed_building_set(type, 1);
    }
    char map_file[FILE_NAME_MAX];
    snprintf(map_file, FILE_NAME_MAX, "%s/new_map.mapx", data.out_dir);
    if (!game_file_editor_write_scenario(map_file)) {
        e2e_error("cannot write %s", map_file);
        return E2E_ERROR;
    }
    // The editor load of the climate graphics clears the main images, also when it stops
    // before the end, so the next normal load returns early. Force the load of the game
    // graphics and the HD sprites.
    image_load_climate(climate, 0, 1, 0);
    uint8_t name[FILE_NAME_MAX];
    encoding_from_utf8("new_map", name, FILE_NAME_MAX);
    scenario_set_name(name);
    scenario_set_custom(2);
    scenario_set_player_name(lang_get_string(9, 5));
    if (!game_file_start_scenario_from_path(name, map_file)) {
        e2e_error("cannot start the new map %s", map_file);
        return E2E_ERROR;
    }
    show_city();
    e2e_log("new map %d x %d, %s", size, size, CLIMATE_NAMES[climate]);
    return E2E_OK;
}

static int command_load(int argc, char **argv)
{
    if (argc != 2) {
        e2e_error("load needs: load <savegame>");
        return E2E_ERROR;
    }
    char path[FILE_NAME_MAX];
    get_test_path("saves", argv[1], path);
    if (game_file_load_saved_game(path) != 1) {
        e2e_error("cannot load the savegame %s", path);
        return E2E_ERROR;
    }
    show_city();
    e2e_log("loaded %s", path);
    return E2E_OK;
}

static int command_save(int argc, char **argv)
{
    if (argc != 2) {
        e2e_error("save needs: save <savegame>");
        return E2E_ERROR;
    }
    char path[FILE_NAME_MAX];
    get_test_path("saves", argv[1], path);
    if (!game_file_write_saved_game(path)) {
        e2e_error("cannot write the savegame %s", path);
        return E2E_ERROR;
    }
    e2e_log("saved %s", path);
    return E2E_OK;
}

static int command_events(int argc, char **argv)
{
    if (argc != 2) {
        e2e_error("events needs: events <xml file>");
        return E2E_ERROR;
    }
    char path[FILE_NAME_MAX];
    get_test_path("events", argv[1], path);
    if (!scenario_events_xml_parse_file(path)) {
        e2e_error("cannot import the events in %s", path);
        return E2E_ERROR;
    }
    e2e_log("imported events %s", path);
    return E2E_OK;
}

// capture <name> camera x y zoom z [offset dx dy] [size w h]
static int command_capture(int argc, char **argv)
{
    int camera[2], zoom = 0, offset[2] = { 0, 0 }, size[2] = { 0, 0 };
    int ok = argc >= 7 && strcmp(argv[2], "camera") == 0 && parse_int(argv[3], &camera[0]) &&
        parse_int(argv[4], &camera[1]) && strcmp(argv[5], "zoom") == 0 && parse_int(argv[6], &zoom);
    for (int i = 7; ok && i < argc; i += 3) {
        int *target = strcmp(argv[i], "offset") == 0 ? offset : strcmp(argv[i], "size") == 0 ? size : 0;
        ok = target && i + 2 < argc && parse_int(argv[i + 1], &target[0]) && parse_int(argv[i + 2], &target[1]);
    }
    if (!ok) {
        e2e_error("capture needs: capture <name> camera x y zoom z [offset dx dy] [size w h]");
        return E2E_ERROR;
    }
    return e2e_capture(argv[1], camera[0], camera[1], zoom, offset[0], offset[1], size[0], size[1]);
}

static int command_seed(int argc, char **argv)
{
    int seed;
    if (argc != 2 || !parse_int(argv[1], &seed)) {
        e2e_error("seed needs: seed <n>");
        return E2E_ERROR;
    }
    random_set_test_seed((uint32_t) seed);
    return E2E_OK;
}

// Writes state_<name>.json with the queries and a hash of each savegame piece.
// The savegame is kept as state_<name>.svx, so a failed test can be loaded in the game.
static int command_dump(int argc, char **argv)
{
    if (argc != 2) {
        e2e_error("dump needs: dump <name>");
        return E2E_ERROR;
    }
    char save_file[FILE_NAME_MAX];
    snprintf(save_file, FILE_NAME_MAX, "%s/state_%s.svx", data.out_dir, argv[1]);
    if (!game_file_write_saved_game(save_file)) {
        e2e_error("cannot write %s", save_file);
        return E2E_ERROR;
    }
    char json_file[FILE_NAME_MAX];
    snprintf(json_file, FILE_NAME_MAX, "%s/state_%s.json", data.out_dir, argv[1]);
    FILE *fp = fopen(json_file, "w");
    if (!fp) {
        e2e_error("cannot write %s", json_file);
        return E2E_ERROR;
    }
    uint32_t hashes[MAX_SAVE_PIECES];
    int num_pieces = game_file_io_hash_saved_game(hashes, MAX_SAVE_PIECES);
    fprintf(fp, "{\n");
    e2e_state_write_queries(fp);
    fprintf(fp, "  \"save_piece_hashes\": [");
    for (int i = 0; i < num_pieces; i++) {
        fprintf(fp, "%s\"%08x\"", i ? ", " : "", hashes[i]);
    }
    fprintf(fp, "]\n}\n");
    fclose(fp);
    e2e_log("dump %s: %s", argv[1], json_file);
    return E2E_OK;
}

static int command_run(int argc, char **argv)
{
    int count;
    if (argc == 2 && strcmp(argv[1], "month_end") == 0) {
        start_month = game_time_month();
        if (!run_until(is_new_month)) {
            e2e_error("the month did not end");
            return E2E_ERROR;
        }
        run_ticks(1);
        return E2E_OK;
    }
    if (argc == 4 && strcmp(argv[1], "until") == 0 &&
        parse_int(argv[2], &until_year) && parse_int(argv[3], &until_month)) {
        until_year += scenario_property_start_year();
        if (!run_until(is_until_date)) {
            e2e_error("the date was not reached");
            return E2E_ERROR;
        }
        return E2E_OK;
    }
    if (argc != 3 || !parse_int(argv[2], &count) || count < 0) {
        e2e_error("run needs: run ticks|days|months <n>, run month_end or run until <year offset> <month>");
        return E2E_ERROR;
    }
    if (strcmp(argv[1], "ticks") == 0) {
        run_ticks(count);
    } else if (strcmp(argv[1], "days") == 0) {
        run_ticks(count * GAME_TIME_TICKS_PER_DAY);
    } else if (strcmp(argv[1], "months") == 0) {
        for (int i = 0; i < count; i++) {
            start_month = game_time_month();
            run_until(is_new_month);
        }
    } else {
        e2e_error("unknown run mode '%s'", argv[1]);
        return E2E_ERROR;
    }
    return E2E_OK;
}

// Finds the first comparison word. Returns its index, or 0.
static int find_op(int argc, char **argv, compare_op *op)
{
    for (int i = 1; i < argc; i++) {
        *op = parse_op(argv[i]);
        if (*op != OP_NONE) {
            return i;
        }
    }
    return 0;
}

static int split_line(char *line, char **argv);

// Stores the value of each query that a later check compares with "mark", up to the next mark.
static int command_mark(int argc, char **argv)
{
    if (argc != 1) {
        e2e_error("mark has no arguments, not '%s'", argv[1]);
        return E2E_ERROR;
    }
    data.num_marks = 0;
    for (int i = data.line; i < data.num_lines; i++) {
        char line[MAX_LINE];
        char *words[MAX_ARGS];
        snprintf(line, MAX_LINE, "%s", data.lines[i]);
        int count = split_line(line, words);
        if (count > 0 && strcmp(words[0], "mark") == 0) {
            break;
        }
        compare_op op;
        int op_index = count > 0 && strcmp(words[0], "check") == 0 ? find_op(count, words, &op) : 0;
        if (op_index < 2 || op_index + 1 >= count || strcmp(words[op_index + 1], "mark") != 0) {
            continue;
        }
        int value;
        if (data.num_marks < MAX_MARKS && e2e_query(op_index - 1, words + 1, &value)) {
            mark_value *mark = &data.marks[data.num_marks++];
            join_args(op_index - 1, words + 1, mark->query, MAX_LINE);
            mark->value = value;
        }
    }
    return E2E_OK;
}

// Reads the value of a check: a number, a name, "mark", "mark + n" or "mark - n"
static int parse_value(int argc, char **argv, const char *query, int *value)
{
    if (argc == 1 && (parse_int(argv[0], value) || e2e_lookup_value_name(argv[0], value))) {
        return 1;
    }
    if (strcmp(argv[0], "mark") != 0) {
        return 0;
    }
    int found = 0;
    for (int i = 0; i < data.num_marks; i++) {
        if (strcmp(data.marks[i].query, query) == 0) {
            *value = data.marks[i].value;
            found = 1;
        }
    }
    int change;
    if (!found) {
        return 0;
    }
    if (argc == 1) {
        return 1;
    }
    if (argc == 3 && parse_int(argv[2], &change) && (strcmp(argv[1], "+") == 0 || strcmp(argv[1], "-") == 0)) {
        *value += argv[1][0] == '+' ? change : -change;
        return 1;
    }
    return 0;
}

// check image <name> [max channel difference [max pixels]]
// check hd <capture> [image group]
static int check_hd(int argc, char **argv)
{
    if (argc != 3 && argc != 4) {
        e2e_error("check hd needs: check hd <capture> [image group]");
        return E2E_ERROR;
    }
    return e2e_check_hd(argv[2], argc == 4 ? argv[3] : 0);
}

static int check_image(int argc, char **argv)
{
    int limits[2] = { 0, 0 };
    if (argc < 3 || argc > 5 || (argc > 3 && !parse_int(argv[3], &limits[0])) ||
        (argc > 4 && !parse_int(argv[4], &limits[1]))) {
        e2e_error("check image needs: check image <capture> [max channel difference [max pixels]]");
        return E2E_ERROR;
    }
    return e2e_check_image(argv[2], limits[0], limits[1]);
}

static int command_check(int argc, char **argv)
{
    if (argc >= 2 && strcmp(argv[1], "image") == 0) {
        return check_image(argc, argv);
    }
    if (argc >= 2 && strcmp(argv[1], "hd") == 0) {
        return check_hd(argc, argv);
    }
    if (argc >= 2 && strcmp(argv[1], "seams") == 0) {
        int region[4];
        if (argc != 8 || strcmp(argv[3], "region") != 0 || !parse_int(argv[4], &region[0]) ||
            !parse_int(argv[5], &region[1]) || !parse_int(argv[6], &region[2]) || !parse_int(argv[7], &region[3])) {
            e2e_error("check seams needs: check seams <capture> region x1 y1 x2 y2");
            return E2E_ERROR;
        }
        return e2e_check_seams(argv[2], region[0], region[1], region[2], region[3]);
    }
    compare_op op = OP_NONE;
    int op_index = find_op(argc, argv, &op);
    if (op_index < 2 || op_index == argc - 1) {
        e2e_error("check needs: check <query> <op> <value>");
        return E2E_ERROR;
    }
    char text[MAX_MESSAGE];
    join_args(argc - 1, argv + 1, text, MAX_MESSAGE);
    char query[MAX_MESSAGE];
    join_args(op_index - 1, argv + 1, query, MAX_MESSAGE);
    int actual;
    if (!e2e_query(op_index - 1, argv + 1, &actual)) {
        e2e_error("unknown query or wrong arguments: '%s'", query);
        return E2E_ERROR;
    }
    int expected;
    if (!parse_value(argc - op_index - 1, argv + op_index + 1, query, &expected)) {
        e2e_error("the value of '%s' is not a number, a known name or a mark expression", text);
        return E2E_ERROR;
    }
    if (compare(actual, op, expected)) {
        e2e_log("ok   line %d: check %s: actual %d", data.line, text, actual);
        return E2E_OK;
    }
    e2e_check_failed("check %s: actual %d, expected %d", text, actual, expected);
    return E2E_CHECK_FAILED;
}

static const e2e_command COMMANDS[] = {
    { "new_map", command_new_map },
    { "load", command_load },
    { "load_map", command_load_map },
    { "save", command_save },
    { "events", command_events },
    { "place", e2e_command_place },
    { "clear", e2e_command_clear },
    { "terrain", e2e_command_terrain },
    { "set", e2e_command_set },
    { "date", e2e_command_date },
    { "variable", e2e_command_variable },
    { "config", e2e_command_config },
    { "cheat", e2e_command_cheat },
    { "mark", command_mark },
    { "capture", command_capture },
    { "seed", command_seed },
    { "dump", command_dump },
    { "run", command_run },
    { "check", command_check },
};

#define NUM_COMMANDS (sizeof(COMMANDS) / sizeof(e2e_command))

static const e2e_command *find_command(const char *name)
{
    for (unsigned int i = 0; i < NUM_COMMANDS; i++) {
        if (strcmp(COMMANDS[i].name, name) == 0) {
            return &COMMANDS[i];
        }
    }
    return 0;
}

// Removes the comment and splits the line on spaces. Returns -1 for too many words.
static int split_line(char *line, char **argv)
{
    char *comment = strchr(line, '#');
    if (comment) {
        *comment = 0;
    }
    int argc = 0;
    for (char *word = strtok(line, " \t\r\n"); word; word = strtok(0, " \t\r\n")) {
        if (argc == MAX_ARGS) {
            return -1;
        }
        argv[argc++] = word;
    }
    return argc;
}

// The test file is in tests/e2e/cases/, so the test folder is two levels up
static void set_test_dir(const char *test_file)
{
    snprintf(data.test_dir, FILE_NAME_MAX, "%s", test_file);
    for (int i = 0; i < 2; i++) {
        char *slash = strrchr(data.test_dir, '/');
        if (slash) {
            *slash = 0;
        } else {
            snprintf(data.test_dir, FILE_NAME_MAX, "%s", i ? "." : "..");
        }
    }
}

static void set_test_name(const char *test_file)
{
    const char *name = strrchr(test_file, '/');
    name = name ? name + 1 : test_file;
    snprintf(data.test_name, FILE_NAME_MAX, "%s", name);
    char *extension = strrchr(data.test_name, '.');
    if (extension) {
        *extension = 0;
    }
}

static void open_log(const char *out_dir)
{
    mkdir(out_dir, 0755);
    snprintf(data.out_dir, FILE_NAME_MAX, "%s/%s", out_dir, data.test_name);
    mkdir(data.out_dir, 0755);
    char log_file[FILE_NAME_MAX];
    snprintf(log_file, FILE_NAME_MAX, "%s/log.txt", data.out_dir);
    data.log = fopen(log_file, "w");
}

static int read_file(FILE *fp)
{
    while (fgets(data.lines[data.num_lines], MAX_LINE, fp)) {
        if (++data.num_lines == MAX_LINES) {
            e2e_error("the test file has more than %d lines", MAX_LINES);
            return 0;
        }
    }
    return 1;
}

// Runs one line of the test file. An empty line or a comment returns E2E_OK.
static int run_line(const char *text)
{
    char line[MAX_LINE];
    char *argv[MAX_ARGS];
    snprintf(line, MAX_LINE, "%s", text);
    int argc = split_line(line, argv);
    if (argc == 0) {
        return E2E_OK;
    }
    if (argc < 0) {
        e2e_error("the line has more than %d words", MAX_ARGS);
        return E2E_ERROR;
    }
    const e2e_command *command = find_command(argv[0]);
    if (!command) {
        e2e_error("unknown command '%s'", argv[0]);
        return E2E_ERROR;
    }
    return command->run(argc, argv);
}

// Replaces each {zoom}, {dx} and {dy} in the text
static void substitute(const char *text, int zoom, int dx, int dy, char *result)
{
    static const char *NAMES[] = { "{zoom}", "{dx}", "{dy}" };
    int values[] = { zoom, dx, dy };
    int length = 0;
    while (*text && length < MAX_LINE - 12) {
        int replaced = 0;
        for (int i = 0; i < 3 && !replaced; i++) {
            size_t name_length = strlen(NAMES[i]);
            if (strncmp(text, NAMES[i], name_length) == 0) {
                length += snprintf(result + length, MAX_LINE - length, "%d", values[i]);
                text += name_length;
                replaced = 1;
            }
        }
        if (!replaced) {
            result[length++] = *text++;
        }
    }
    result[length] = 0;
}

// repeat zoom <from> <to> <step> offsets <dx,dy> ... runs the lines up to "end" for each zoom and offset
static int run_repeat(int argc, char **argv)
{
    int zoom[3];
    int offsets[MAX_ARGS][2];
    int num_offsets = 0;
    int ok = argc >= 7 && strcmp(argv[1], "zoom") == 0 && parse_int(argv[2], &zoom[0]) &&
        parse_int(argv[3], &zoom[1]) && parse_int(argv[4], &zoom[2]) && zoom[2] > 0 && zoom[0] <= zoom[1] &&
        strcmp(argv[5], "offsets") == 0;
    for (int i = 6; ok && i < argc; i++) {
        ok = sscanf(argv[i], "%d,%d", &offsets[num_offsets][0], &offsets[num_offsets][1]) == 2;
        num_offsets++;
    }
    if (!ok) {
        e2e_error("repeat needs: repeat zoom <from> <to> <step> offsets <dx,dy> ..., with from <= to and step > 0");
        return E2E_ERROR;
    }
    int first_line = data.line;
    int end_line = first_line;
    while (end_line < data.num_lines) {
        char line[MAX_LINE];
        char *words[MAX_ARGS];
        snprintf(line, MAX_LINE, "%s", data.lines[end_line]);
        int count = split_line(line, words);
        if (count > 0 && strcmp(words[0], "end") == 0) {
            break;
        }
        if (count > 0 && strcmp(words[0], "repeat") == 0) {
            e2e_error("a repeat block cannot have a repeat block in it");
            return E2E_ERROR;
        }
        end_line++;
    }
    if (end_line == data.num_lines) {
        e2e_error("the repeat block has no end line");
        return E2E_ERROR;
    }
    int result = E2E_OK;
    for (int z = zoom[0]; z <= zoom[1]; z += zoom[2]) {
        for (int o = 0; o < num_offsets; o++) {
            for (int i = first_line; i < end_line; i++) {
                char line[MAX_LINE];
                substitute(data.lines[i], z, offsets[o][0], offsets[o][1], line);
                data.line = i + 1;
                int line_result = run_line(line);
                if (line_result == E2E_ERROR) {
                    return E2E_ERROR;
                }
                if (line_result > result) {
                    result = line_result;
                }
            }
        }
    }
    data.line = end_line + 1;
    return result;
}

static int run_lines(void)
{
    int result = E2E_OK;
    while (data.line < data.num_lines) {
        char line[MAX_LINE];
        char *argv[MAX_ARGS];
        snprintf(line, MAX_LINE, "%s", data.lines[data.line]);
        data.line++;
        int argc = split_line(line, argv);
        int line_result = argc > 0 && strcmp(argv[0], "repeat") == 0 ?
            run_repeat(argc, argv) : run_line(data.lines[data.line - 1]);
        if (line_result == E2E_ERROR) {
            return E2E_ERROR;
        }
        if (line_result > result) {
            result = line_result;
        }
    }
    return result;
}

int e2e_run(const char *test_file, const char *out_dir, int update_images)
{
    data.update_images = update_images;
    set_test_name(test_file);
    set_test_dir(test_file);
    open_log(out_dir ? out_dir : DEFAULT_OUT_DIR);
    e2e_log("test %s", test_file);
    // Without a seed command, the tests also use a fixed seed
    random_set_test_seed(DEFAULT_SEED);

    int result;
    FILE *fp = platform_renderer_is_software() ? 0 : fopen(test_file, "r");
    if (platform_renderer_is_software()) {
        // A software capture does not show the defects of the GPU texture filter
        e2e_error("SDL uses the software renderer: the tests need the GPU renderer");
        result = E2E_ERROR;
    } else if (fp) {
        int has_read = read_file(fp);
        fclose(fp);
        result = has_read ? run_lines() : E2E_ERROR;
    } else {
        e2e_error("cannot open the test file %s", test_file);
        result = E2E_ERROR;
    }

    static const char *RESULT_NAMES[] = { "pass", "fail", "error" };
    if (result == E2E_OK) {
        e2e_log("result: pass");
    } else {
        e2e_log("result: %s: %s", RESULT_NAMES[result], data.first_problem);
    }
    if (data.log) {
        fclose(data.log);
        data.log = 0;
    }
    return result;
}
