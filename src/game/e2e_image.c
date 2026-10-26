#include "e2e_image.h"

#include "city/view.h"
#include "core/file.h"
#include "core/image.h"
#include "core/image_group.h"
#include "game/e2e.h"
#include "graphics/renderer.h"
#include "map/grid.h"
#include "platform/renderer.h"
#include "window/city.h"

#include "spng/spng.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>

#define MAX_CAPTURES 128
#define MAX_NAME 128
#define MIN_ZOOM 50
#define COLOR_DIFF (ALPHA_OPAQUE | 0x00ff00ff)

// The seam check compares the mean luminance (0 to 255) of each line of slope +1/2 or -1/2
// (the tile edges) with the parallel lines 1.5 to 3 pixels away
#define SEAM_NEAR 3 // in half pixels
#define SEAM_FAR 6 // in half pixels
#define SEAM_MIN_LINE_PIXELS 64
// Measured on flat HD grass, zoom 50 to 200: at most 10.5 on 2b6e0ca02, 26 to 35 at most zooms without it
#define SEAM_THRESHOLD 16.0
#define SEAM_CROP_SIZE 32
#define SEAM_CROP_SCALE 8

typedef struct {
    char name[MAX_NAME];
    int width;
    int height;
    color_t *pixels;
    int draws[IMAGE_MAIN_ENTRIES][2]; // the draws of each main image without and with an HD texture
    // The view of the capture, for the seam check
    int zoom;
    int camera_x;
    int camera_y;
    int left;
    int top;
} capture;

typedef struct {
    const char *name;
    int group;
} group_name;

// The names are the names in core/image_group.h, in lowercase and without GROUP_. Add a group when a test needs it.
static const group_name GROUP_NAMES[] = {
    { "terrain_grass_1", GROUP_TERRAIN_GRASS_1 },
    { "terrain_meadow", GROUP_TERRAIN_MEADOW },
    { "terrain_shrub", GROUP_TERRAIN_SHRUB },
    { "terrain_tree", GROUP_TERRAIN_TREE },
};

#define NUM_GROUP_NAMES (sizeof(GROUP_NAMES) / sizeof(group_name))

static struct {
    capture captures[MAX_CAPTURES];
    int num_captures;
} data;

static capture *find_capture(const char *name)
{
    for (int i = 0; i < data.num_captures; i++) {
        if (strcmp(data.captures[i].name, name) == 0) {
            return &data.captures[i];
        }
    }
    return 0;
}

static capture *new_capture(const char *name, int width, int height)
{
    capture *c = find_capture(name);
    if (!c) {
        if (data.num_captures == MAX_CAPTURES) {
            return 0;
        }
        c = &data.captures[data.num_captures++];
        snprintf(c->name, MAX_NAME, "%s", name);
    }
    free(c->pixels);
    c->pixels = malloc(sizeof(color_t) * width * height);
    c->width = width;
    c->height = height;
    return c->pixels ? c : 0;
}

static int write_png(const char *filename, const color_t *pixels, int width, int height)
{
    size_t size = (size_t) width * height * 3;
    uint8_t *rgb = malloc(size);
    if (!rgb) {
        return 0;
    }
    for (int i = 0; i < width * height; i++) {
        rgb[i * 3 + 0] = (uint8_t) COLOR_COMPONENT(pixels[i], COLOR_BITSHIFT_RED);
        rgb[i * 3 + 1] = (uint8_t) COLOR_COMPONENT(pixels[i], COLOR_BITSHIFT_GREEN);
        rgb[i * 3 + 2] = (uint8_t) COLOR_COMPONENT(pixels[i], COLOR_BITSHIFT_BLUE);
    }
    FILE *fp = fopen(filename, "wb");
    spng_ctx *ctx = spng_ctx_new(SPNG_CTX_ENCODER);
    struct spng_ihdr ihdr = {
        .width = width,
        .height = height,
        .bit_depth = 8,
        .color_type = SPNG_COLOR_TYPE_TRUECOLOR
    };
    int ok = fp && ctx && !spng_set_png_file(ctx, fp) && !spng_set_ihdr(ctx, &ihdr) &&
        !spng_encode_image(ctx, rgb, size, SPNG_FMT_PNG, SPNG_ENCODE_FINALIZE);
    spng_ctx_free(ctx);
    if (fp) {
        fclose(fp);
    }
    free(rgb);
    return ok;
}

// Reads a PNG file. The caller frees the pixels.
static color_t *read_png(const char *filename, int *width, int *height)
{
    FILE *fp = fopen(filename, "rb");
    if (!fp) {
        return 0;
    }
    spng_ctx *ctx = spng_ctx_new(0);
    struct spng_ihdr ihdr;
    size_t size;
    color_t *pixels = 0;
    uint8_t *rgba = 0;
    if (ctx && !spng_set_png_file(ctx, fp) && !spng_get_ihdr(ctx, &ihdr) &&
        !spng_decoded_image_size(ctx, SPNG_FMT_RGBA8, &size)) {
        rgba = malloc(size);
        pixels = malloc(sizeof(color_t) * ihdr.width * ihdr.height);
        if (rgba && pixels && !spng_decode_image(ctx, rgba, size, SPNG_FMT_RGBA8, 0)) {
            for (unsigned int i = 0; i < ihdr.width * ihdr.height; i++) {
                pixels[i] = ALPHA_OPAQUE | (rgba[i * 4] << COLOR_BITSHIFT_RED) |
                    (rgba[i * 4 + 1] << COLOR_BITSHIFT_GREEN) | (rgba[i * 4 + 2] << COLOR_BITSHIFT_BLUE);
            }
            *width = ihdr.width;
            *height = ihdr.height;
        } else {
            free(pixels);
            pixels = 0;
        }
    }
    free(rgba);
    spng_ctx_free(ctx);
    fclose(fp);
    return pixels;
}

static int is_on_map(int x_pixels, int y_pixels)
{
    view_tile tile;
    if (!city_view_pixels_to_view_tile(x_pixels, y_pixels, &tile)) {
        return 0;
    }
    int grid_offset = city_view_tile_to_grid_offset(&tile);
    return grid_offset && map_grid_is_inside(map_grid_offset_to_x(grid_offset), map_grid_offset_to_y(grid_offset), 1);
}

int e2e_capture(const char *name, int x, int y, int zoom, int dx, int dy, int width, int height)
{
    int max_zoom = city_view_get_max_scale();
    if (zoom < MIN_ZOOM || zoom > max_zoom) {
        e2e_error("the zoom %d is outside the range %d to %d", zoom, MIN_ZOOM, max_zoom);
        return E2E_ERROR;
    }
    if (!map_grid_is_inside(x, y, 1)) {
        e2e_error("the camera tile %d %d is outside the map", x, y);
        return E2E_ERROR;
    }
    city_view_set_scale(zoom);
    city_view_go_to_grid_offset(map_grid_offset(x, y));
    if (dx || dy) {
        int camera_x, camera_y;
        city_view_get_camera_in_pixels(&camera_x, &camera_y);
        city_view_set_camera_from_pixel_position(camera_x + dx, camera_y + dy);
    }

    int viewport_x, viewport_y, viewport_width, viewport_height;
    city_view_get_viewport(&viewport_x, &viewport_y, &viewport_width, &viewport_height);
    width = width ? width : viewport_width;
    height = height ? height : viewport_height;
    // ponytail: a capture is at most the size of the viewport; join several draws when a test needs more
    if (width <= 0 || height <= 0 || width > viewport_width || height > viewport_height) {
        e2e_error("the capture size %d x %d is not in the range 1 x 1 to %d x %d (the city viewport)",
            width, height, viewport_width, viewport_height);
        return E2E_ERROR;
    }
    int left = viewport_x + (viewport_width - width) / 2;
    int top = viewport_y + (viewport_height - height) / 2;
    int right = left + width - 1;
    int bottom = top + height - 1;
    if (!is_on_map(left, top) || !is_on_map(right, top) || !is_on_map(left, bottom) || !is_on_map(right, bottom)) {
        e2e_error("the capture %s (%d x %d at camera %d %d, zoom %d) is partly outside the map", name,
            width, height, x, y, zoom);
        return E2E_ERROR;
    }

    capture *c = new_capture(name, width, height);
    if (!c) {
        e2e_error("no memory for the capture %s", name);
        return E2E_ERROR;
    }
    c->zoom = zoom;
    city_view_get_camera_in_pixels(&c->camera_x, &c->camera_y);
    c->left = left;
    c->top = top;
    platform_renderer_e2e_reset_counts();
    window_city_draw_all();
    for (int id = 0; id < IMAGE_MAIN_ENTRIES; id++) {
        c->draws[id][0] = platform_renderer_e2e_count(id, 0);
        c->draws[id][1] = platform_renderer_e2e_count(id, 1);
    }
    if (!graphics_renderer()->save_screen_buffer(c->pixels, left, top, width, height, width)) {
        e2e_error("the renderer cannot read the pixels of %s", name);
        return E2E_ERROR;
    }
    char filename[FILE_NAME_MAX];
    snprintf(filename, FILE_NAME_MAX, "%s/%s.png", e2e_out_dir(), name);
    if (!write_png(filename, c->pixels, width, height)) {
        e2e_error("cannot write %s", filename);
        return E2E_ERROR;
    }
    e2e_log("capture %s: %d x %d at camera %d %d, zoom %d, offset %d %d", name, width, height, x, y, zoom, dx, dy);
    return E2E_OK;
}

const color_t *e2e_capture_pixels(const char *name, int *width, int *height)
{
    capture *c = find_capture(name);
    if (!c) {
        return 0;
    }
    *width = c->width;
    *height = c->height;
    return c->pixels;
}

// The images of a group are from its first image to the first image of the next group
static void get_group_range(int group, int *first, int *end)
{
    *first = image_group(group);
    *end = IMAGE_MAIN_ENTRIES;
    for (int other = 0; other < IMAGE_MAX_GROUPS; other++) {
        int start = image_group(other);
        if (start > *first && start < *end) {
            *end = start;
        }
    }
}

int e2e_check_hd(const char *name, const char *group)
{
    capture *c = find_capture(name);
    if (!c) {
        e2e_error("no capture has the name %s", name);
        return E2E_ERROR;
    }
    int first = 0;
    int end = IMAGE_MAIN_ENTRIES;
    if (group) {
        const group_name *found = 0;
        for (unsigned int i = 0; i < NUM_GROUP_NAMES; i++) {
            if (strcmp(GROUP_NAMES[i].name, group) == 0) {
                found = &GROUP_NAMES[i];
            }
        }
        if (!found) {
            e2e_error("unknown image group '%s' (add it to GROUP_NAMES in src/game/e2e_image.c)", group);
            return E2E_ERROR;
        }
        get_group_range(found->group, &first, &end);
    }
    int hd = 0, original = 0;
    char original_ids[MAX_NAME] = { 0 };
    for (int id = first; id < end; id++) {
        hd += c->draws[id][1];
        original += c->draws[id][0];
        if (c->draws[id][0] && strlen(original_ids) < MAX_NAME - 8) {
            snprintf(original_ids + strlen(original_ids), MAX_NAME - strlen(original_ids), " %d", id);
        }
    }
    const char *what = group ? group : "all images";
    if (!hd || (group && original)) {
        e2e_check_failed("check hd %s %s: %d draws with HD, %d draws without HD (images:%s)",
            name, what, hd, original, original_ids);
        return E2E_CHECK_FAILED;
    }
    e2e_log("ok   check hd %s %s: %d draws with HD, %d draws without HD", name, what, hd, original);
    return E2E_OK;
}

static double luminance(color_t c)
{
    return (COLOR_COMPONENT(c, COLOR_BITSHIFT_RED) * 299 + COLOR_COMPONENT(c, COLOR_BITSHIFT_GREEN) * 587 +
        COLOR_COMPONENT(c, COLOR_BITSHIFT_BLUE) * 114) / 1000.0;
}

// Marks the pixels of the capture that show a tile in the region
static uint8_t *region_mask(const capture *c, int x1, int y1, int x2, int y2)
{
    uint8_t *mask = calloc((size_t) c->width * c->height, 1);
    if (!mask) {
        return 0;
    }
    city_view_set_scale(c->zoom);
    city_view_set_camera_from_pixel_position(c->camera_x, c->camera_y);
    for (int y = 0; y < c->height; y++) {
        for (int x = 0; x < c->width; x++) {
            view_tile tile;
            if (!city_view_pixels_to_view_tile(c->left + x, c->top + y, &tile)) {
                continue;
            }
            int grid_offset = city_view_tile_to_grid_offset(&tile);
            int tile_x = map_grid_offset_to_x(grid_offset);
            int tile_y = map_grid_offset_to_y(grid_offset);
            mask[y * c->width + x] = grid_offset && tile_x >= x1 && tile_x <= x2 && tile_y >= y1 && tile_y <= y2;
        }
    }
    return mask;
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

static void write_seam_crop(const capture *c, int center_x, int center_y, int number)
{
    int size = SEAM_CROP_SIZE * SEAM_CROP_SCALE;
    color_t *crop = malloc(sizeof(color_t) * size * size);
    if (!crop) {
        return;
    }
    for (int y = 0; y < size; y++) {
        for (int x = 0; x < size; x++) {
            int source_x = center_x - SEAM_CROP_SIZE / 2 + x / SEAM_CROP_SCALE;
            int source_y = center_y - SEAM_CROP_SIZE / 2 + y / SEAM_CROP_SCALE;
            int inside = source_x >= 0 && source_x < c->width && source_y >= 0 && source_y < c->height;
            crop[y * size + x] = inside ? c->pixels[source_y * c->width + source_x] : ALPHA_OPAQUE;
        }
    }
    char filename[FILE_NAME_MAX];
    snprintf(filename, FILE_NAME_MAX, "%s/%s.seam_%d.png", e2e_out_dir(), c->name, number);
    write_png(filename, crop, size, size);
    free(crop);
}

int e2e_check_seams(const char *name, int x1, int y1, int x2, int y2)
{
    capture *c = find_capture(name);
    if (!c) {
        e2e_error("no capture has the name %s", name);
        return E2E_ERROR;
    }
    uint8_t *mask = region_mask(c, x1, y1, x2, y2);
    // A pixel x y is on line k = 2y - slope * x + width of the line family with the slope +1/2 or -1/2
    int num_lines = 2 * c->height + 2 * c->width + 1;
    double *sum = calloc(num_lines, sizeof(double));
    int *count = calloc(num_lines, sizeof(int));
    int *min_x = calloc(num_lines, sizeof(int));
    if (!mask || !sum || !count || !min_x) {
        free(mask);
        free(sum);
        free(count);
        free(min_x);
        e2e_error("no memory for the seam check");
        return E2E_ERROR;
    }
    double worst = 0;
    int worst_slope = 0, worst_line = 0, worst_x = 0, pixels = 0, seams = 0;
    for (int slope = -1; slope <= 1; slope += 2) {
        memset(sum, 0, num_lines * sizeof(double));
        memset(count, 0, num_lines * sizeof(int));
        for (int y = 0; y < c->height; y++) {
            for (int x = 0; x < c->width; x++) {
                if (mask[y * c->width + x]) {
                    int k = 2 * y - slope * x + c->width;
                    sum[k] += luminance(c->pixels[y * c->width + x]);
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
            pixels += count[k];
            double before = side_mean(sum, count, k, -1, num_lines);
            double after = side_mean(sum, count, k, 1, num_lines);
            if (before < 0 || after < 0) {
                continue;
            }
            double mean = sum[k] / count[k];
            double darker = (before < after ? before : after) - mean;
            double lighter = mean - (before > after ? before : after);
            double dip = darker > lighter ? darker : lighter;
            if (dip > SEAM_THRESHOLD) {
                seams++;
            }
            if (dip > worst) {
                worst = dip;
                worst_slope = slope;
                worst_line = k;
                // The middle of the line: count[k] pixels, one in each second column
                worst_x = min_x[k] + count[k] - 1;
            }
        }
    }
    free(mask);
    free(sum);
    free(count);
    free(min_x);
    if (!pixels) {
        e2e_error("the capture %s shows no tile of the region %d %d to %d %d", name, x1, y1, x2, y2);
        return E2E_ERROR;
    }
    int worst_y = (worst_line - c->width + worst_slope * worst_x) / 2;
    if (seams) {
        write_seam_crop(c, worst_x, worst_y, 1);
        e2e_check_failed("check seams %s: %d seam lines (zoom %d), the worst line is %.1f darker or lighter "
            "than its neighbours (limit %.1f) at pixel %d %d; see %s.seam_1.png",
            name, seams, c->zoom, worst, SEAM_THRESHOLD, worst_x, worst_y, name);
        return E2E_CHECK_FAILED;
    }
    e2e_log("ok   check seams %s: no seam line (zoom %d), the worst line differs by %.1f (limit %.1f)",
        name, c->zoom, worst, SEAM_THRESHOLD);
    return E2E_OK;
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

static void get_approved_path(const char *name, char *path)
{
    snprintf(path, FILE_NAME_MAX, "%s/images/%s/%s.png", e2e_test_dir(), e2e_test_name(), name);
}

static int update_approved(const capture *c, const char *path)
{
    char folder[FILE_NAME_MAX];
    snprintf(folder, FILE_NAME_MAX, "%s/images", e2e_test_dir());
    mkdir(folder, 0755);
    snprintf(folder, FILE_NAME_MAX, "%s/images/%s", e2e_test_dir(), e2e_test_name());
    mkdir(folder, 0755);
    if (!write_png(path, c->pixels, c->width, c->height)) {
        e2e_error("cannot write the approved image %s", path);
        return E2E_ERROR;
    }
    e2e_log("approved image updated: %s", path);
    return E2E_OK;
}

int e2e_check_image(const char *name, int max_channel_diff, int max_pixels)
{
    capture *c = find_capture(name);
    if (!c) {
        e2e_error("no capture has the name %s", name);
        return E2E_ERROR;
    }
    char approved_path[FILE_NAME_MAX];
    get_approved_path(name, approved_path);
    if (e2e_update_images()) {
        return update_approved(c, approved_path);
    }
    int width, height;
    color_t *approved = read_png(approved_path, &width, &height);
    if (!approved) {
        e2e_check_failed("check image %s: no approved image %s: run with --update-images to approve the capture",
            name, approved_path);
        return E2E_CHECK_FAILED;
    }
    if (width != c->width || height != c->height) {
        free(approved);
        e2e_check_failed("check image %s: the capture is %d x %d and the approved image is %d x %d",
            name, c->width, c->height, width, height);
        return E2E_CHECK_FAILED;
    }
    color_t *diff = malloc(sizeof(color_t) * width * height);
    int changed = 0;
    int x_min = width, y_min = height, x_max = -1, y_max = -1;
    for (int y = 0; y < height; y++) {
        for (int x = 0; x < width; x++) {
            int i = y * width + x;
            if (max_channel_diff_of(c->pixels[i], approved[i]) > max_channel_diff) {
                changed++;
                x_min = x < x_min ? x : x_min;
                y_min = y < y_min ? y : y_min;
                x_max = x > x_max ? x : x_max;
                y_max = y > y_max ? y : y_max;
                if (diff) {
                    diff[i] = COLOR_DIFF;
                }
            } else if (diff) {
                diff[i] = grey_of(c->pixels[i]);
            }
        }
    }
    int result = E2E_OK;
    if (changed > max_pixels) {
        char filename[FILE_NAME_MAX];
        snprintf(filename, FILE_NAME_MAX, "%s/%s.actual.png", e2e_out_dir(), name);
        write_png(filename, c->pixels, width, height);
        snprintf(filename, FILE_NAME_MAX, "%s/%s.approved.png", e2e_out_dir(), name);
        write_png(filename, approved, width, height);
        if (diff) {
            snprintf(filename, FILE_NAME_MAX, "%s/%s.diff.png", e2e_out_dir(), name);
            write_png(filename, diff, width, height);
        }
        e2e_check_failed("check image %s: %d pixels differ by more than %d (allowed: %d), in the box %d %d to %d %d",
            name, changed, max_channel_diff, max_pixels, x_min, y_min, x_max, y_max);
        result = E2E_CHECK_FAILED;
    } else {
        e2e_log("ok   check image %s: %d pixels differ by more than %d (allowed: %d)",
            name, changed, max_channel_diff, max_pixels);
    }
    free(diff);
    free(approved);
    return result;
}
