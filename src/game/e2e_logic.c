#include "e2e_logic.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

// The seam check compares each line with the parallel lines SEAM_NEAR to SEAM_FAR half pixels away
#define SEAM_NEAR 3
#define SEAM_FAR 6
#define SEAM_MIN_LINE_PIXELS 64
#define COLOR_DIFF (ALPHA_OPAQUE | 0x00ff00ff)

static const char *OP_NAMES[] = { "==", "!=", "<=", ">=", "<", ">" };

int e2e_split_line(char *line, char **argv)
{
    char *comment = strchr(line, '#');
    if (comment) {
        *comment = 0;
    }
    int argc = 0;
    for (char *word = strtok(line, " \t\r\n"); word; word = strtok(0, " \t\r\n")) {
        if (argc == E2E_MAX_ARGS) {
            return -1;
        }
        argv[argc++] = word;
    }
    return argc;
}

int e2e_parse_int(const char *text, int *value)
{
    char *end;
    long result = strtol(text, &end, 10);
    if (!*text || *end) {
        return 0;
    }
    *value = (int) result;
    return 1;
}

e2e_op e2e_parse_op(const char *text)
{
    for (int i = 0; i < E2E_OP_NONE; i++) {
        if (strcmp(text, OP_NAMES[i]) == 0) {
            return i;
        }
    }
    return E2E_OP_NONE;
}

int e2e_compare(int actual, e2e_op op, int expected)
{
    switch (op) {
        case E2E_OP_EQ: return actual == expected;
        case E2E_OP_NE: return actual != expected;
        case E2E_OP_LE: return actual <= expected;
        case E2E_OP_GE: return actual >= expected;
        case E2E_OP_LT: return actual < expected;
        case E2E_OP_GT: return actual > expected;
        default: return 0;
    }
}

void e2e_substitute(const char *text, int zoom, int dx, int dy, char *result, int result_size)
{
    static const char *NAMES[] = { "{zoom}", "{dx}", "{dy}" };
    int values[] = { zoom, dx, dy };
    int length = 0;
    while (*text && length < result_size - 1) {
        int replaced = 0;
        for (int i = 0; i < 3 && !replaced; i++) {
            size_t name_length = strlen(NAMES[i]);
            if (strncmp(text, NAMES[i], name_length) == 0) {
                int written = snprintf(result + length, result_size - length, "%d", values[i]);
                length = written < result_size - length ? length + written : result_size - 1;
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

int e2e_apply_mark(int argc, char **argv, int mark, int *value)
{
    int change;
    if (argc < 1 || strcmp(argv[0], "mark") != 0) {
        return 0;
    }
    if (argc == 1) {
        *value = mark;
        return 1;
    }
    if (argc == 3 && e2e_parse_int(argv[2], &change) && (strcmp(argv[1], "+") == 0 || strcmp(argv[1], "-") == 0)) {
        *value = argv[1][0] == '+' ? mark + change : mark - change;
        return 1;
    }
    return 0;
}

static int channel_diff(color_t a, color_t b, int shift)
{
    return abs((int) COLOR_COMPONENT(a, shift) - (int) COLOR_COMPONENT(b, shift));
}

static int max_channel_diff_of(color_t a, color_t b)
{
    int red = channel_diff(a, b, COLOR_BITSHIFT_RED);
    int green = channel_diff(a, b, COLOR_BITSHIFT_GREEN);
    int blue = channel_diff(a, b, COLOR_BITSHIFT_BLUE);
    int max = red > green ? red : green;
    return max > blue ? max : blue;
}

static color_t grey_of(color_t c)
{
    int grey = (COLOR_COMPONENT(c, COLOR_BITSHIFT_RED) + COLOR_COMPONENT(c, COLOR_BITSHIFT_GREEN) +
        COLOR_COMPONENT(c, COLOR_BITSHIFT_BLUE)) / 3;
    // A light grey, so that the magenta pixels are easy to see
    grey = 128 + grey / 2;
    return ALPHA_OPAQUE | (grey << COLOR_BITSHIFT_RED) | (grey << COLOR_BITSHIFT_GREEN) | (grey << COLOR_BITSHIFT_BLUE);
}

void e2e_diff_images(const color_t *actual, const color_t *approved, int width, int height,
    int max_channel_diff, color_t *diff_image, e2e_image_diff *result)
{
    result->changed = 0;
    result->x_min = width;
    result->y_min = height;
    result->x_max = -1;
    result->y_max = -1;
    for (int y = 0; y < height; y++) {
        for (int x = 0; x < width; x++) {
            int i = y * width + x;
            if (max_channel_diff_of(actual[i], approved[i]) > max_channel_diff) {
                result->changed++;
                result->x_min = x < result->x_min ? x : result->x_min;
                result->y_min = y < result->y_min ? y : result->y_min;
                result->x_max = x > result->x_max ? x : result->x_max;
                result->y_max = y > result->y_max ? y : result->y_max;
                if (diff_image) {
                    diff_image[i] = COLOR_DIFF;
                }
            } else if (diff_image) {
                diff_image[i] = grey_of(actual[i]);
            }
        }
    }
}

static double luminance(color_t c)
{
    return (COLOR_COMPONENT(c, COLOR_BITSHIFT_RED) * 299 + COLOR_COMPONENT(c, COLOR_BITSHIFT_GREEN) * 587 +
        COLOR_COMPONENT(c, COLOR_BITSHIFT_BLUE) * 114) / 1000.0;
}

static double side_mean(const double *sum, const int *count, int line, int direction, int num_lines)
{
    double total = 0;
    int lines = 0;
    for (int d = SEAM_NEAR; d <= SEAM_FAR; d++) {
        int k = line + d * direction;
        if (k >= 0 && k < num_lines && count[k] >= SEAM_MIN_LINE_PIXELS) {
            total += sum[k] / count[k];
            lines++;
        }
    }
    return lines ? total / lines : -1;
}

int e2e_find_seams(const color_t *pixels, const uint8_t *mask, int width, int height, double threshold,
    e2e_seam_result *result)
{
    memset(result, 0, sizeof(e2e_seam_result));
    // A pixel x y is on line k = 2y - slope * x + width of the line family with the slope +1/2 or -1/2
    int num_lines = 2 * height + 2 * width + 1;
    double *sum = calloc(num_lines, sizeof(double));
    int *count = calloc(num_lines, sizeof(int));
    int *min_x = calloc(num_lines, sizeof(int));
    if (!sum || !count || !min_x) {
        free(sum);
        free(count);
        free(min_x);
        return 0;
    }
    int worst_slope = 0, worst_line = 0;
    for (int slope = -1; slope <= 1; slope += 2) {
        memset(sum, 0, num_lines * sizeof(double));
        memset(count, 0, num_lines * sizeof(int));
        for (int y = 0; y < height; y++) {
            for (int x = 0; x < width; x++) {
                if (mask[y * width + x]) {
                    int k = 2 * y - slope * x + width;
                    sum[k] += luminance(pixels[y * width + x]);
                    if (!count[k] || x < min_x[k]) {
                        min_x[k] = x;
                    }
                    count[k]++;
                }
            }
        }
        for (int k = 0; k < num_lines; k++) {
            if (count[k] < SEAM_MIN_LINE_PIXELS) {
                continue;
            }
            result->pixels += count[k];
            double before = side_mean(sum, count, k, -1, num_lines);
            double after = side_mean(sum, count, k, 1, num_lines);
            if (before < 0 || after < 0) {
                continue;
            }
            double mean = sum[k] / count[k];
            double darker = (before < after ? before : after) - mean;
            double lighter = mean - (before > after ? before : after);
            double dip = darker > lighter ? darker : lighter;
            if (dip > threshold) {
                result->seams++;
            }
            if (dip > result->worst) {
                result->worst = dip;
                worst_slope = slope;
                worst_line = k;
                // The middle of the line: count[k] pixels, one in each second column
                result->worst_x = min_x[k] + count[k] - 1;
            }
        }
    }
    free(sum);
    free(count);
    free(min_x);
    result->worst_y = (worst_line - width + worst_slope * result->worst_x) / 2;
    return 1;
}

void e2e_group_range(const int *group_starts, int num_groups, int group, int max_id, int *first, int *end)
{
    *first = group_starts[group];
    *end = max_id;
    for (int other = 0; other < num_groups; other++) {
        if (group_starts[other] > *first && group_starts[other] < *end) {
            *end = group_starts[other];
        }
    }
}
