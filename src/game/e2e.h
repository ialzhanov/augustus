#ifndef GAME_E2E_H
#define GAME_E2E_H

#ifdef E2E_TESTS

/**
 * @file
 * End-to-end test mode. It runs the commands of one test file and exits.
 */

typedef enum {
    E2E_OK = 0,
    E2E_CHECK_FAILED = 1,
    E2E_ERROR = 2
} e2e_result;

/**
 * Sets the test mode on. Call this before the window is created.
 */
void e2e_set_active(void);

/**
 * @return 1 when the program runs a test file, 0 otherwise
 */
int e2e_is_active(void);

/**
 * Runs the test file and writes the results to <out_dir>/<test name>/.
 * @param test_file The test file
 * @param out_dir The results folder, or 0 for "e2e-results"
 * @param update_images 1 to write each capture as the new approved image
 * @return The exit code: E2E_OK, E2E_CHECK_FAILED or E2E_ERROR
 */
int e2e_run(const char *test_file, const char *out_dir, int update_images);

/**
 * Writes a line to stdout and to log.txt.
 */
void e2e_log(const char *format, ...);

/**
 * Writes an error line with the current line number of the test file.
 */
void e2e_error(const char *format, ...);

#endif // E2E_TESTS

#endif // GAME_E2E_H
