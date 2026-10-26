#ifndef PLATFORM_RENDERER_H
#define PLATFORM_RENDERER_H

#include "graphics/color.h"

int platform_renderer_init(void *window);

#ifdef E2E_TESTS
int platform_renderer_is_software(void);
void platform_renderer_e2e_reset_counts(void);
// The number of draws of a main image since the reset, with (is_hd 1) or without (is_hd 0) an HD texture
int platform_renderer_e2e_count(int image_id, int is_hd);
#endif

int platform_renderer_create_render_texture(int width, int height);

int platform_renderer_lost_render_texture(void);

void platform_renderer_invalidate_target_textures(void);

void platform_renderer_generate_mouse_cursor_texture(int cursor_id, int size, const color_t *pixels,
    int hotspot_x, int hotspot_y);

void platform_renderer_clear(void);

void platform_renderer_render(void);

void platform_renderer_pause(void);

void platform_renderer_resume(void);

void platform_renderer_destroy(void);

#endif // PLATFORM_RENDERER_H
