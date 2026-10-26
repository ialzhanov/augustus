#ifndef GAME_E2E_STATE_H
#define GAME_E2E_STATE_H

#ifdef E2E_TESTS

#include <stdio.h>

/**
 * Gets the value of a state query, for example "money" or "tick".
 * @param argc The number of words in the query
 * @param argv The words of the query
 * @param value The value of the query
 * @return 1 when the query is known and its arguments are valid, 0 otherwise
 */
int e2e_query(int argc, char **argv, int *value);

/**
 * Writes the value of each query that has no arguments as JSON members.
 * @param fp The file to write to
 */
void e2e_state_write_queries(FILE *fp);

/**
 * Gets the value of a name in a check, for example "small_shack" or "warehouse".
 * @param name The building or house level name of the scenario events
 * @param value The building type
 * @return 1 when the name is known, 0 otherwise
 */
int e2e_lookup_value_name(const char *name, int *value);

// State-change commands. Each returns E2E_OK or E2E_ERROR.
int e2e_command_place(int argc, char **argv);
int e2e_command_clear(int argc, char **argv);
int e2e_command_terrain(int argc, char **argv);
int e2e_command_set(int argc, char **argv);
int e2e_command_date(int argc, char **argv);
int e2e_command_variable(int argc, char **argv);
int e2e_command_config(int argc, char **argv);
int e2e_command_cheat(int argc, char **argv);

#endif // E2E_TESTS

#endif // GAME_E2E_STATE_H
