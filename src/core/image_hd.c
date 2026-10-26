#include "image_hd.h"

#include "core/dir.h"
#include "core/file.h"
#include "core/image_packer.h"
#include "core/log.h"
#include "core/png_read.h"
#include "core/string.h"
#include "graphics/renderer.h"

#include <ctype.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define HD_BASE_DIR "hd"
#define MAX_DENSITY 8

typedef struct {
    image *target;
    color_t *pixels;
    int width;
    int height;
    int density;
} hd_part;

static color_t *read_png(const char *path, int *width, int *height)
{
    if (!png_load_from_file(path, 0) || !png_get_image_size(width, height)) {
        png_unload();
        return 0;
    }
    color_t *pixels = malloc(sizeof(color_t) * *width * *height);
    if (!pixels || !png_read(pixels, 0, 0, *width, *height, 0, 0, *width, 0)) {
        free(pixels);
        pixels = 0;
    }
    png_unload();
    return pixels;
}

static const int FOOTPRINT_X_START_PER_HEIGHT[] = {
    28, 26, 24, 22, 20, 18, 16, 14, 12, 10, 8, 6, 4, 2, 0,
    0, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24, 26, 28
};

static void mark_footprint_tile(uint8_t *mask, int width, int x_offset, int y_offset)
{
    for (int y = 0; y < FOOTPRINT_HEIGHT; y++) {
        int x_start = FOOTPRINT_X_START_PER_HEIGHT[y];
        for (int x = x_start; x < FOOTPRINT_WIDTH - x_start; x++) {
            mask[(y + y_offset) * width + x + x_offset] = 1;
        }
    }
}

// Keeps only the pixels of the original footprint shape (same tile layout as the .555 footprint data),
// grown by one original pixel. High-resolution images are drawn with linear filtering: at a zoom that is not
// a whole number the filter makes the outermost pixels partly transparent. The extra pixel puts that soft edge
// over the opaque pixels of the neighbour tile, so no dark line shows between tiles.
// Removed pixels keep their colour (only the alpha becomes 0), so the filter does not blend black into the edge.
static void mask_footprint(color_t *pixels, int width, int height, int density)
{
    int w = width / density;
    int h = height / density;
    uint8_t *mask = calloc(w * h, 1);
    if (!mask) {
        return;
    }
    int num_tiles = (w + 2) / (FOOTPRINT_WIDTH + 2);
    int x_start = (num_tiles - 1) * 30;
    for (int i = 0; i < num_tiles; i++) {
        for (int j = 0; j <= i; j++) {
            mark_footprint_tile(mask, w, -30 * i + x_start + 60 * j, FOOTPRINT_HALF_HEIGHT * i);
        }
    }
    for (int i = num_tiles - 2; i >= 0; i--) {
        for (int j = 0; j <= i; j++) {
            mark_footprint_tile(mask, w, -30 * i + x_start + 60 * j, FOOTPRINT_HALF_HEIGHT * (num_tiles * 2 - i - 2));
        }
    }
    uint8_t *grown = calloc(w * h, 1);
    if (!grown) {
        free(mask);
        return;
    }
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            grown[y * w + x] = mask[y * w + x] ||
                (x > 0 && mask[y * w + x - 1]) || (x < w - 1 && mask[y * w + x + 1]) ||
                (y > 0 && mask[(y - 1) * w + x]) || (y < h - 1 && mask[(y + 1) * w + x]);
        }
    }
    for (int y = 0; y < height; y++) {
        for (int x = 0; x < width; x++) {
            if (!grown[(y / density) * w + x / density]) {
                pixels[y * width + x] &= ~COLOR_CHANNEL_ALPHA;
            }
        }
    }
    free(grown);
    free(mask);
}

// Space around each image in the atlas, filled with copies of the image's edge pixels: linear filtering
// reads half a texel past the source rectangle, which would otherwise be the next image in the atlas
#define ATLAS_PADDING 2

static void extend_edges(color_t *buffer, int buffer_width, int x, int y, int width, int height)
{
    for (int row = 0; row < height; row++) {
        color_t *line = &buffer[(y + row) * buffer_width];
        for (int p = 1; p <= ATLAS_PADDING; p++) {
            line[x - p] = line[x];
            line[x + width - 1 + p] = line[x + width - 1];
        }
    }
    for (int p = 1; p <= ATLAS_PADDING; p++) {
        memcpy(&buffer[(y - p) * buffer_width + x - ATLAS_PADDING], &buffer[y * buffer_width + x - ATLAS_PADDING],
            sizeof(color_t) * (width + 2 * ATLAS_PADDING));
        memcpy(&buffer[(y + height - 1 + p) * buffer_width + x - ATLAS_PADDING],
            &buffer[(y + height - 1) * buffer_width + x - ATLAS_PADDING], sizeof(color_t) * (width + 2 * ATLAS_PADDING));
    }
}

static color_t *copy_rows(const color_t *src, int width, int y_start, int rows)
{
    color_t *dst = malloc(sizeof(color_t) * width * rows);
    if (dst) {
        memcpy(dst, &src[y_start * width], sizeof(color_t) * width * rows);
    }
    return dst;
}

// Returns the number of parts added: the image itself and, for isometric images, its top
static int load_image_parts(image *img, int image_id, const char *dir, hd_part *parts)
{
    char path[FILE_NAME_MAX];
    int width, height;
    snprintf(path, FILE_NAME_MAX, "%s/%d.png", dir, image_id);
    color_t *full = read_png(path, &width, &height);
    if (!full) {
        return 0;
    }
    int density = width / img->original.width;
    if (density < 2 || density > MAX_DENSITY ||
        width != img->original.width * density || height != img->original.height * density) {
        log_error("HD image has the wrong size, it must be the original size times 2 to 8", path, 0);
        free(full);
        return 0;
    }
    int added = 0;
    if (!img->is_isometric) {
        parts[added++] = (hd_part) { img, full, width, height, density };
        return added;
    }
    int footprint_height = img->height * density;
    color_t *footprint = copy_rows(full, width, height - footprint_height, footprint_height);
    if (footprint) {
        mask_footprint(footprint, width, footprint_height, density);
        parts[added++] = (hd_part) { img, footprint, width, footprint_height, density };
    }
    if (img->top) {
        int top_height = img->top->original.height * density;
        int top_width, top_file_height;
        snprintf(path, FILE_NAME_MAX, "%s/%d_top.png", dir, image_id);
        color_t *top = file_exists(path, NOT_LOCALIZED) ? read_png(path, &top_width, &top_file_height) : 0;
        if (top && (top_width != width || top_file_height != top_height)) {
            log_error("HD top image has the wrong size", path, 0);
            free(top);
            top = 0;
        }
        if (!top) {
            top = copy_rows(full, width, 0, top_height);
        }
        if (top) {
            parts[added++] = (hd_part) { img->top, top, width, top_height, density };
        }
    }
    free(full);
    return added;
}

static void build_dir_name(char *dir, const char *sg2_filename)
{
    snprintf(dir, FILE_NAME_MAX, "%s/%s", HD_BASE_DIR, file_remove_path(sg2_filename));
    file_remove_extension(dir);
    for (char *c = dir; *c; c++) {
        *c = (char) tolower((unsigned char) *c);
    }
}

void image_hd_load(image *images, int num_images, const char *sg2_filename)
{
    graphics_renderer()->free_image_atlas(ATLAS_HD);

    char dir[FILE_NAME_MAX];
    build_dir_name(dir, sg2_filename);
    const dir_listing *files = dir_find_files_with_extension(dir, "png");
    if (!files->num_files) {
        return;
    }
    // Copy the ids now: the listing is reused by other directory calls
    int *ids = malloc(sizeof(int) * files->num_files);
    hd_part *parts = malloc(sizeof(hd_part) * files->num_files * 2);
    if (!ids || !parts) {
        free(ids);
        free(parts);
        return;
    }
    int num_ids = 0;
    for (int i = 0; i < files->num_files; i++) {
        char *end;
        long id = strtol(files->files[i].name, &end, 10);
        if (end != files->files[i].name && *end == '.' &&
            id > 0 && id < num_images && images[id].original.width && !image_is_external(&images[id])) {
            ids[num_ids++] = (int) id;
        }
    }
    int num_parts = 0;
    for (int i = 0; i < num_ids; i++) {
        num_parts += load_image_parts(&images[ids[i]], ids[i], dir, &parts[num_parts]);
    }
    free(ids);
    if (!num_parts) {
        free(parts);
        return;
    }

    image_packer packer;
    int max_width, max_height;
    graphics_renderer()->get_max_image_size(&max_width, &max_height);
    if (image_packer_init(&packer, num_parts, max_width, max_height) != IMAGE_PACKER_OK) {
        log_error("Failed to init the HD image packer", 0, 0);
        for (int i = 0; i < num_parts; i++) {
            free(parts[i].pixels);
        }
        free(parts);
        return;
    }
    packer.options.fail_policy = IMAGE_PACKER_NEW_IMAGE;
    packer.options.reduce_image_size = 1;
    packer.options.sort_by = IMAGE_PACKER_SORT_BY_AREA;
    for (int i = 0; i < num_parts; i++) {
        packer.rects[i].input.width = parts[i].width + 2 * ATLAS_PADDING;
        packer.rects[i].input.height = parts[i].height + 2 * ATLAS_PADDING;
    }
    image_packer_pack(&packer);

    const image_atlas_data *atlas_data = graphics_renderer()->prepare_image_atlas(ATLAS_HD,
        packer.result.images_needed, packer.result.last_image_width, packer.result.last_image_height);
    for (int i = 0; i < num_parts; i++) {
        if (atlas_data && packer.rects[i].output.packed) {
            int index = packer.rects[i].output.image_index;
            int dst_width = atlas_data->image_widths[index];
            int x = packer.rects[i].output.x + ATLAS_PADDING;
            int y = packer.rects[i].output.y + ATLAS_PADDING;
            image_copy_info copy = {
                .src = { 0, 0, parts[i].width, parts[i].height, parts[i].pixels },
                .dst = { x, y, dst_width, atlas_data->image_heights[index], atlas_data->buffers[index] },
                .rect = { 0, 0, parts[i].width, parts[i].height }
            };
            image_copy(&copy);
            extend_edges(atlas_data->buffers[index], dst_width, x, y, parts[i].width, parts[i].height);
            image *target = parts[i].target;
            target->hd.density = parts[i].density;
            target->hd.atlas_id = index; // index only: ATLAS_HD << 28 does not fit in a signed int
            target->hd.x_offset = x;
            target->hd.y_offset = y;
        }
        free(parts[i].pixels);
    }
    free(parts);
    image_packer_free(&packer);
    if (atlas_data) {
        graphics_renderer()->create_image_atlas(atlas_data, 1);
        log_info("Loaded HD images from", dir, num_parts);
    }
}
