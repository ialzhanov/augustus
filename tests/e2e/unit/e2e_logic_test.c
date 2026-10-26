// Unit tests for src/game/e2e_logic.c. Build: cmake -DE2E_TESTS=ON, target e2e_logic_test.
// The program prints each failed check and exits with 1 when a check failed.

#include "game/e2e_logic.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int failures;
static int checks;

#define CHECK(condition) do { \
        checks++; \
        if (!(condition)) { \
            failures++; \
            printf("FAIL %s:%d: %s\n", __FILE__, __LINE__, #condition); \
        } \
    } while (0)

static void test_split_line(void)
{
    char line[] = "check  money\t>= 5   # comment";
    char *argv[E2E_MAX_ARGS];
    CHECK(e2e_split_line(line, argv) == 4);
    CHECK(strcmp(argv[0], "check") == 0);
    CHECK(strcmp(argv[2], ">=") == 0);
    CHECK(strcmp(argv[3], "5") == 0);

    char comment[] = "   # only a comment";
    CHECK(e2e_split_line(comment, argv) == 0);

    char too_many[256] = "";
    for (int i = 0; i <= E2E_MAX_ARGS; i++) {
        strcat(too_many, "w ");
    }
    CHECK(e2e_split_line(too_many, argv) == -1);
}

static void test_parse_int(void)
{
    int value = 0;
    CHECK(e2e_parse_int("12", &value) && value == 12);
    CHECK(e2e_parse_int("-3", &value) && value == -3);
    CHECK(!e2e_parse_int("12a", &value));
    CHECK(!e2e_parse_int("", &value));
    CHECK(!e2e_parse_int("mark", &value));
}

static void test_ops(void)
{
    CHECK(e2e_parse_op("==") == E2E_OP_EQ);
    CHECK(e2e_parse_op("!=") == E2E_OP_NE);
    CHECK(e2e_parse_op("<=") == E2E_OP_LE);
    CHECK(e2e_parse_op(">=") == E2E_OP_GE);
    CHECK(e2e_parse_op("<") == E2E_OP_LT);
    CHECK(e2e_parse_op(">") == E2E_OP_GT);
    CHECK(e2e_parse_op("=") == E2E_OP_NONE);
    CHECK(e2e_parse_op("=>") == E2E_OP_NONE);

    CHECK(e2e_compare(5, E2E_OP_EQ, 5) && !e2e_compare(5, E2E_OP_EQ, 6));
    CHECK(e2e_compare(5, E2E_OP_NE, 6) && !e2e_compare(5, E2E_OP_NE, 5));
    CHECK(e2e_compare(5, E2E_OP_LE, 5) && e2e_compare(4, E2E_OP_LE, 5) && !e2e_compare(6, E2E_OP_LE, 5));
    CHECK(e2e_compare(5, E2E_OP_GE, 5) && e2e_compare(6, E2E_OP_GE, 5) && !e2e_compare(4, E2E_OP_GE, 5));
    CHECK(e2e_compare(4, E2E_OP_LT, 5) && !e2e_compare(5, E2E_OP_LT, 5));
    CHECK(e2e_compare(6, E2E_OP_GT, 5) && !e2e_compare(5, E2E_OP_GT, 5));
    CHECK(!e2e_compare(5, E2E_OP_NONE, 5));
}

static void test_substitute(void)
{
    char result[64];
    e2e_substitute("capture s_{zoom}_{dx}_{dy} zoom {zoom}", 90, 7, -3, result, sizeof(result));
    CHECK(strcmp(result, "capture s_90_7_-3 zoom 90") == 0);

    e2e_substitute("no names", 1, 2, 3, result, sizeof(result));
    CHECK(strcmp(result, "no names") == 0);

    char small[8];
    e2e_substitute("abcdefghijkl", 1, 2, 3, small, sizeof(small));
    CHECK(strlen(small) < sizeof(small));
    e2e_substitute("{zoom}{zoom}{zoom}", 123456789, 0, 0, small, sizeof(small));
    CHECK(strlen(small) < sizeof(small));
}

static void test_apply_mark(void)
{
    int value = 0;
    char *plain[] = { "mark" };
    char *plus[] = { "mark", "+", "1000" };
    char *minus[] = { "mark", "-", "24" };
    char *times[] = { "mark", "*", "2" };
    char *no_number[] = { "mark", "+" };
    char *not_mark[] = { "money" };
    CHECK(e2e_apply_mark(1, plain, 100, &value) && value == 100);
    CHECK(e2e_apply_mark(3, plus, 100, &value) && value == 1100);
    CHECK(e2e_apply_mark(3, minus, 100, &value) && value == 76);
    CHECK(!e2e_apply_mark(3, times, 100, &value));
    CHECK(!e2e_apply_mark(2, no_number, 100, &value));
    CHECK(!e2e_apply_mark(1, not_mark, 100, &value));
}

static color_t rgb(int red, int green, int blue)
{
    return ALPHA_OPAQUE | (red << COLOR_BITSHIFT_RED) | (green << COLOR_BITSHIFT_GREEN) | (blue << COLOR_BITSHIFT_BLUE);
}

static void test_diff_images(void)
{
    enum { W = 20, H = 10 };
    color_t a[W * H];
    color_t b[W * H];
    color_t diff[W * H];
    for (int i = 0; i < W * H; i++) {
        a[i] = b[i] = rgb(100, 120, 40);
    }
    e2e_image_diff result;
    e2e_diff_images(a, b, W, H, 0, diff, &result);
    CHECK(result.changed == 0);

    b[2 * W + 3] = rgb(110, 120, 40); // red + 10
    b[7 * W + 15] = rgb(100, 120, 45); // blue + 5
    e2e_diff_images(a, b, W, H, 0, diff, &result);
    CHECK(result.changed == 2);
    CHECK(result.x_min == 3 && result.y_min == 2 && result.x_max == 15 && result.y_max == 7);
    CHECK(diff[2 * W + 3] == (ALPHA_OPAQUE | 0x00ff00ff));
    CHECK(diff[0] != (ALPHA_OPAQUE | 0x00ff00ff));

    e2e_diff_images(a, b, W, H, 5, 0, &result);
    CHECK(result.changed == 1); // only the pixel that differs by 10
    e2e_diff_images(a, b, W, H, 10, 0, &result);
    CHECK(result.changed == 0);

    b[0] = a[0] & ~COLOR_CHANNEL_ALPHA; // the alpha channel does not count
    e2e_diff_images(a, b, W, H, 10, 0, &result);
    CHECK(result.changed == 0);
}

// A grass-like image: random green pixels, with the same seed in each run
static void make_grass(color_t *pixels, int width, int height)
{
    uint32_t state = 12345;
    for (int i = 0; i < width * height; i++) {
        state = state * 1103515245u + 12345u;
        int noise = (int) ((state >> 16) % 61) - 30;
        pixels[i] = rgb(70 + noise, 120 + noise, 30 + noise / 2);
    }
}

// Changes the luminance of the tile edges: the lines y = x / 2 + c and y = -x / 2 + c, c = phase + n * spacing
static void draw_tile_edges(color_t *pixels, int width, int height, int spacing, int phase, int change)
{
    for (int slope = -1; slope <= 1; slope += 2) {
        for (int c = phase - width; c < height + width; c += spacing) {
            for (int x = 0; x < width; x++) {
                int y = (slope * x) / 2 + c;
                if (y < 0 || y >= height) {
                    continue;
                }
                color_t p = pixels[y * width + x];
                int red = COLOR_COMPONENT(p, COLOR_BITSHIFT_RED) + change;
                int green = COLOR_COMPONENT(p, COLOR_BITSHIFT_GREEN) + change;
                int blue = COLOR_COMPONENT(p, COLOR_BITSHIFT_BLUE) + change;
                red = red < 0 ? 0 : red > 255 ? 255 : red;
                green = green < 0 ? 0 : green > 255 ? 255 : green;
                blue = blue < 0 ? 0 : blue > 255 ? 255 : blue;
                pixels[y * width + x] = rgb(red, green, blue);
            }
        }
    }
}

static int is_on_tile_edge(int x, int y, int spacing, int phase)
{
    for (int slope = -1; slope <= 1; slope += 2) {
        for (int d = -1; d <= 1; d++) {
            int c = y + d - (slope * x) / 2 - phase;
            if (((c % spacing) + spacing) % spacing == 0) {
                return 1;
            }
        }
    }
    return 0;
}

static void test_find_seams(void)
{
    enum { W = 320, H = 240, SPACING = 15, PHASE = 4 };
    color_t *pixels = malloc(sizeof(color_t) * W * H);
    uint8_t *mask = malloc(W * H);
    memset(mask, 1, W * H);
    e2e_seam_result result;

    make_grass(pixels, W, H);
    CHECK(e2e_find_seams(pixels, mask, W, H, E2E_SEAM_THRESHOLD, &result));
    CHECK(result.seams == 0);
    CHECK(result.pixels > 0);
    CHECK(result.worst < E2E_SEAM_THRESHOLD / 2);

    // The old seam bug made the tile edges 26 to 35 darker
    draw_tile_edges(pixels, W, H, SPACING, PHASE, -40);
    CHECK(e2e_find_seams(pixels, mask, W, H, E2E_SEAM_THRESHOLD, &result));
    CHECK(result.seams > 0);
    CHECK(result.worst > E2E_SEAM_THRESHOLD);
    CHECK(result.worst_x >= 0 && result.worst_x < W && result.worst_y >= 0 && result.worst_y < H);
    CHECK(is_on_tile_edge(result.worst_x, result.worst_y, SPACING, PHASE));

    // Light seams count too
    make_grass(pixels, W, H);
    draw_tile_edges(pixels, W, H, SPACING, PHASE, 40);
    CHECK(e2e_find_seams(pixels, mask, W, H, E2E_SEAM_THRESHOLD, &result));
    CHECK(result.seams > 0);

    // A small change of the edges, as on the fixed code, is not a seam
    make_grass(pixels, W, H);
    draw_tile_edges(pixels, W, H, SPACING, PHASE, -8);
    CHECK(e2e_find_seams(pixels, mask, W, H, E2E_SEAM_THRESHOLD, &result));
    CHECK(result.seams == 0);

    // Only the masked pixels count: dark edges outside the mask are not seams
    make_grass(pixels, W, H);
    draw_tile_edges(pixels, W, H, SPACING, PHASE, -40);
    memset(mask, 0, W * H);
    CHECK(e2e_find_seams(pixels, mask, W, H, E2E_SEAM_THRESHOLD, &result));
    CHECK(result.seams == 0 && result.pixels == 0);

    free(pixels);
    free(mask);
}

static void test_group_range(void)
{
    // Group 0 is not used. Groups 1, 2 and 3 start at 10, 30 and 20.
    int starts[] = { 0, 10, 30, 20 };
    int first, end;
    e2e_group_range(starts, 4, 1, 100, &first, &end);
    CHECK(first == 10 && end == 20);
    e2e_group_range(starts, 4, 3, 100, &first, &end);
    CHECK(first == 20 && end == 30);
    e2e_group_range(starts, 4, 2, 100, &first, &end);
    CHECK(first == 30 && end == 100);
}

int main(void)
{
    test_split_line();
    test_parse_int();
    test_ops();
    test_substitute();
    test_apply_mark();
    test_diff_images();
    test_find_seams();
    test_group_range();
    printf("%d checks, %d failed\n", checks, failures);
    return failures ? 1 : 0;
}
