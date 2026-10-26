#include "e2e_state.h"

#include "city/finance.h"
#include "game/time.h"

#include <string.h>

typedef struct {
    const char *name;
    int (*get)(void);
} simple_query;

static const simple_query SIMPLE_QUERIES[] = {
    { "money", city_finance_treasury },
    { "tick", game_time_tick },
    { "day", game_time_day },
    { "month", game_time_month },
    { "year", game_time_year },
};

#define NUM_SIMPLE_QUERIES (sizeof(SIMPLE_QUERIES) / sizeof(simple_query))

int e2e_query(int argc, char **argv, int *value)
{
    for (unsigned int i = 0; i < NUM_SIMPLE_QUERIES; i++) {
        if (strcmp(argv[0], SIMPLE_QUERIES[i].name) == 0) {
            if (argc != 1) {
                return 0;
            }
            *value = SIMPLE_QUERIES[i].get();
            return 1;
        }
    }
    return 0;
}
