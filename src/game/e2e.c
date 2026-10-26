#include "e2e.h"

#include "core/encoding.h"
#include "core/file.h"
#include "core/lang.h"
#include "game/e2e_state.h"
#include "game/file.h"
#include "game/game.h"
#include "game/tick.h"
#include "scenario/event/controller.h"
#include "scenario/property.h"
#include "window/city.h"

#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>

#define MAX_LINE 1024
#define MAX_ARGS 32
#define MAX_MESSAGE 1024
#define DEFAULT_OUT_DIR "e2e-results"

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

static struct {
    int active;
    int line;
    int update_images;
    FILE *log;
    char test_name[FILE_NAME_MAX];
    char out_dir[FILE_NAME_MAX];
    char first_problem[MAX_MESSAGE];
} data;

void e2e_set_active(void)
{
    data.active = 1;
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

static void run_ticks(int ticks)
{
    for (int i = 0; i < ticks; i++) {
        game_tick_run();
    }
    game_draw();
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
    window_city_show();
    scenario_events_process_all();
    e2e_log("loaded map %s", name_utf8);
    return E2E_OK;
}

static int command_run(int argc, char **argv)
{
    int count;
    if (argc != 3 || !parse_int(argv[2], &count) || count < 0) {
        e2e_error("run needs: run ticks <n>");
        return E2E_ERROR;
    }
    if (strcmp(argv[1], "ticks") == 0) {
        run_ticks(count);
        return E2E_OK;
    }
    e2e_error("unknown run mode '%s'", argv[1]);
    return E2E_ERROR;
}

static int command_check(int argc, char **argv)
{
    int op_index = 0;
    compare_op op = OP_NONE;
    for (int i = 1; i < argc; i++) {
        op = parse_op(argv[i]);
        if (op != OP_NONE) {
            op_index = i;
            break;
        }
    }
    if (op_index < 2 || op_index != argc - 2) {
        e2e_error("check needs: check <query> <op> <value>");
        return E2E_ERROR;
    }
    char text[MAX_MESSAGE];
    join_args(argc - 1, argv + 1, text, MAX_MESSAGE);
    int actual;
    if (!e2e_query(op_index - 1, argv + 1, &actual)) {
        char query[MAX_MESSAGE];
        join_args(op_index - 1, argv + 1, query, MAX_MESSAGE);
        e2e_error("unknown query or wrong arguments: '%s'", query);
        return E2E_ERROR;
    }
    int expected;
    if (!parse_int(argv[argc - 1], &expected)) {
        e2e_error("the value '%s' is not a number", argv[argc - 1]);
        return E2E_ERROR;
    }
    if (compare(actual, op, expected)) {
        e2e_log("ok   line %d: check %s: actual %d", data.line, text, actual);
        return E2E_OK;
    }
    char message[MAX_MESSAGE * 2];
    snprintf(message, sizeof(message), "FAIL line %d: check %s: actual %d", data.line, text, actual);
    write_line(message);
    remember_problem(message);
    return E2E_CHECK_FAILED;
}

static const e2e_command COMMANDS[] = {
    { "load_map", command_load_map },
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

static int run_file(FILE *fp)
{
    int result = E2E_OK;
    char line[MAX_LINE];
    char *argv[MAX_ARGS];
    while (fgets(line, MAX_LINE, fp)) {
        data.line++;
        int argc = split_line(line, argv);
        if (argc == 0) {
            continue;
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
        int command_result = command->run(argc, argv);
        if (command_result == E2E_ERROR) {
            return E2E_ERROR;
        }
        if (command_result > result) {
            result = command_result;
        }
    }
    return result;
}

int e2e_run(const char *test_file, const char *out_dir, int update_images)
{
    data.update_images = update_images;
    set_test_name(test_file);
    open_log(out_dir ? out_dir : DEFAULT_OUT_DIR);
    e2e_log("test %s", test_file);

    int result;
    FILE *fp = fopen(test_file, "r");
    if (fp) {
        result = run_file(fp);
        fclose(fp);
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
