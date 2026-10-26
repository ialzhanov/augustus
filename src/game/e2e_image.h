#ifndef GAME_E2E_IMAGE_H
#define GAME_E2E_IMAGE_H

#ifdef E2E_TESTS

#include "graphics/color.h"

/**
 * Draws the city with the camera on tile x y, reads the pixels and keeps them under the name.
 * Also writes <out>/<test>/<name>.png.
 * @param name The capture name
 * @param x The tile x of the camera
 * @param y The tile y of the camera
 * @param zoom The zoom in percent, from 50 to city_view_get_max_scale()
 * @param dx The camera offset in pixels
 * @param dy The camera offset in pixels
 * @param width The capture width, or 0 for the width of the city viewport
 * @param height The capture height, or 0 for the height of the city viewport
 * @return E2E_OK or E2E_ERROR
 */
int e2e_capture(const char *name, int x, int y, int zoom, int dx, int dy, int width, int height);

/**
 * @return The pixels of a capture, or 0 when no capture has the name
 */
const color_t *e2e_capture_pixels(const char *name, int *width, int *height);

/**
 * Compares a capture with tests/e2e/images/<test>/<name>.png.
 * With --update-images, writes the capture as the new approved image.
 * @param name The capture name
 * @param max_channel_diff A pixel differs when one colour channel differs by more than this value
 * @param max_pixels The check fails when more than this number of pixels differ
 * @return E2E_OK, E2E_CHECK_FAILED or E2E_ERROR
 */
int e2e_check_image(const char *name, int max_channel_diff, int max_pixels);

#endif // E2E_TESTS

#endif // GAME_E2E_IMAGE_H
