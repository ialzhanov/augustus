#ifndef GAME_E2E_STATE_H
#define GAME_E2E_STATE_H

#ifdef E2E_TESTS

/**
 * Gets the value of a state query, for example "money" or "tick".
 * @param argc The number of words in the query
 * @param argv The words of the query
 * @param value The value of the query
 * @return 1 when the query is known and its arguments are valid, 0 otherwise
 */
int e2e_query(int argc, char **argv, int *value);

#endif // E2E_TESTS

#endif // GAME_E2E_STATE_H
