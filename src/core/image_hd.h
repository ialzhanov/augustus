#ifndef CORE_IMAGE_HD_H
#define CORE_IMAGE_HD_H

#include "core/image.h"

/**
 * Loads high-resolution replacements for images of a .sg2 file.
 *
 * Files are read from hd/<sg2 name without extension>/<image id>.png, for example hd/c3/2797.png.
 * The PNG must be the full original image scaled by an integer factor (2 to 8).
 * Isometric images with a top part may also have <image id>_top.png with only the top part
 * (no ground), which keeps walkers behind the building visible.
 * The images keep their original size on screen: the renderer draws the larger texture in the same area.
 *
 * @param images The image array of the .sg2 file
 * @param num_images Number of images in the array
 * @param sg2_filename The .sg2 file name
 */
void image_hd_load(image *images, int num_images, const char *sg2_filename);

#endif // CORE_IMAGE_HD_H
