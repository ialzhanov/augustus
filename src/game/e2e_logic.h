#ifndef GAME_E2E_LOGIC_H
#define GAME_E2E_LOGIC_H

#ifdef E2E_TESTS

/**
 * @file
 * The logic of the end-to-end test mode that does not use the engine.
 * tests/e2e/unit/e2e_logic_test.c tests these functions.
 */

#include "graphics/color.h"

#include <stdint.h>

#define E2E_MAX_ARGS 32

// Measured on flat HD grass, zoom 50 to 200: at most 10.5 on 2b6e0ca02, 26 to 35 at most zooms without it
#define E2E_SEAM_THRESHOLD 16.0

typedef enum {
    E2E_OP_EQ,
    E2E_OP_NE,
    E2E_OP_LE,
    E2E_OP_GE,
    E2E_OP_LT,
    E2E_OP_GT,
    E2E_OP_NONE
} e2e_op;

typedef struct {
    int changed;
    int x_min;
    int y_min;
    int x_max;
    int y_max;
} e2e_image_diff;

typedef struct {
    int seams;
    double worst;
    int worst_x;
    int worst_y;
    int pixels;
} e2e_seam_result;

/**
 * Removes the comment (from '#') and splits the line on spaces and tabs.
 * @param line The line. The function changes it.
 * @param argv The words, at most E2E_MAX_ARGS
 * @return The number of words, or -1 when the line has more than E2E_MAX_ARGS words
 */
int e2e_split_line(char *line, char **argv);

/**
 * @return 1 when all of the text is a decimal integer, 0 otherwise
 */
int e2e_parse_int(const char *text, int *value);

/**
 * @return The op for "==", "!=", "<=", ">=", "<" or ">", or E2E_OP_NONE
 */
e2e_op e2e_parse_op(const char *text);

/**
 * @return 1 when "actual op expected" is true
 */
int e2e_compare(int actual, e2e_op op, int expected);

/**
 * Copies the text and replaces each {zoom}, {dx} and {dy} with its value.
 * The result is cut to result_size - 1 characters.
 */
void e2e_substitute(const char *text, int zoom, int dx, int dy, char *result, int result_size);

/**
 * Reads "mark", "mark + n" or "mark - n".
 * @param argc The number of words
 * @param argv The words; the first word must be "mark"
 * @param mark The value of the query at the mark
 * @param value The result
 * @return 1 when the words are a valid mark expression, 0 otherwise
 */
int e2e_apply_mark(int argc, char **argv, int mark, int *value);

/**
 * Compares two images. A pixel is changed when one colour channel differs by more than max_channel_diff.
 * @param diff_image 0, or an image of the same size: changed pixels become magenta, other pixels grey
 */
void e2e_diff_images(const color_t *actual, const color_t *approved, int width, int height,
    int max_channel_diff, color_t *diff_image, e2e_image_diff *result);

/**
 * Finds seams in an image of flat isometric terrain. For each line of slope +1/2 and -1/2 (a tile edge),
 * the function compares the mean luminance with the parallel lines 1.5 to 3 pixels away.
 * A line is a seam when it is darker or lighter than both sides by more than the threshold.
 * @param mask 1 for each pixel to use, 0 for each pixel to ignore
 * @return 0 when there is no memory, 1 otherwise
 */
int e2e_find_seams(const color_t *pixels, const uint8_t *mask, int width, int height, double threshold,
    e2e_seam_result *result);

/**
 * Gives the image ids of a group: from its first image to the first image of the next group, or to max_id.
 */
void e2e_group_range(const int *group_starts, int num_groups, int group, int max_id, int *first, int *end);

#endif // E2E_TESTS

#endif // GAME_E2E_LOGIC_H
