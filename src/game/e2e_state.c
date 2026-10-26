#include "e2e_state.h"

#include "building/building.h"
#include "building/construction.h"
#include "building/count.h"
#include "building/granary.h"
#include "building/house.h"
#include "building/warehouse.h"
#include "city/finance.h"
#include "city/population.h"
#include "city/ratings.h"
#include "city/resource.h"
#include "core/config.h"
#include "core/encoding.h"
#include "core/xml_parser.h"
#include "editor/tool.h"
#include "game/cheats.h"
#include "game/e2e.h"
#include "game/resource.h"
#include "game/time.h"
#include "map/building.h"
#include "map/grid.h"
#include "map/point.h"
#include "map/routing_terrain.h"
#include "map/terrain.h"
#include "scenario/custom_variable.h"
#include "scenario/event/controller.h"
#include "scenario/event/data.h"
#include "scenario/event/parameter_data.h"
#include "scenario/property.h"

#include <stdlib.h>
#include <string.h>

#define MAX_TEXT 256

typedef struct {
    const char *name;
    int (*get)(void);
} simple_query;

static const simple_query SIMPLE_QUERIES[] = {
    { "money", city_finance_treasury },
    { "population", city_population },
    { "favor", city_rating_favor },
    { "tick", game_time_tick },
    { "day", game_time_day },
    { "month", game_time_month },
    { "year", game_time_year },
};

#define NUM_SIMPLE_QUERIES (sizeof(SIMPLE_QUERIES) / sizeof(simple_query))

typedef struct {
    const char *name;
    tool_type tool;
    int terrain;
} terrain_type;

// "grass" is land with none of the other terrain types
static const terrain_type TERRAIN_TYPES[] = {
    { "grass", TOOL_GRASS, 0 },
    { "meadow", TOOL_MEADOW, TERRAIN_MEADOW },
    { "trees", TOOL_TREES, TERRAIN_TREE },
    { "rocks", TOOL_ROCKS, TERRAIN_ROCK },
    { "water", TOOL_WATER, TERRAIN_WATER },
    { "shrub", TOOL_SHRUB, TERRAIN_SHRUB },
};

#define NUM_TERRAIN_TYPES (sizeof(TERRAIN_TYPES) / sizeof(terrain_type))

#define GRASS_EXCLUDED_TERRAIN (TERRAIN_TREE | TERRAIN_ROCK | TERRAIN_WATER | TERRAIN_SHRUB | TERRAIN_MEADOW | \
    TERRAIN_BUILDING | TERRAIN_ROAD | TERRAIN_GARDEN)

static int parse_int(const char *text, int *value)
{
    char *end;
    long result = strtol(text, &end, 10);
    if (!*text || *end) {
        return 0;
    }
    *value = (int) result;
    return 1;
}

static int parse_ints(char **argv, int count, int *values)
{
    for (int i = 0; i < count; i++) {
        if (!parse_int(argv[i], &values[i])) {
            return 0;
        }
    }
    return 1;
}

static int lookup_mapping(parameter_type type, const char *name, int *value)
{
    special_attribute_mapping_t *mapping = scenario_events_parameter_data_get_attribute_mapping_by_text(type, name);
    if (!mapping) {
        return 0;
    }
    *value = mapping->value;
    return 1;
}

static int lookup_building_type(const char *name, int *type)
{
    return lookup_mapping(PARAMETER_TYPE_BUILDING, name, type) && *type > 0;
}

// Uses the resource names of the event XML files, for example "wheat" or "timber|wood"
static int lookup_resource(const char *name, int *resource)
{
    for (resource_type r = RESOURCE_MIN; r < RESOURCE_MAX; r++) {
        if (xml_parser_compare_multiple(resource_get_data(r)->xml_attr_name, name)) {
            *resource = r;
            return 1;
        }
    }
    return 0;
}

static const terrain_type *lookup_terrain(const char *name)
{
    for (unsigned int i = 0; i < NUM_TERRAIN_TYPES; i++) {
        if (strcmp(TERRAIN_TYPES[i].name, name) == 0) {
            return &TERRAIN_TYPES[i];
        }
    }
    return 0;
}

int e2e_lookup_value_name(const char *name, int *value)
{
    return lookup_building_type(name, value) || lookup_mapping(PARAMETER_TYPE_HOUSING_TYPE, name, value);
}

static building *get_building(const char *id_text)
{
    int id;
    if (!parse_int(id_text, &id) || id <= 0 || id >= building_count()) {
        return 0;
    }
    building *b = building_get(id);
    return b->state == BUILDING_STATE_UNUSED ? 0 : b;
}

static building *get_house(const char *id_text)
{
    building *b = get_building(id_text);
    return b && building_is_house(b->type) ? b : 0;
}

static int get_stock(building *b, int resource)
{
    if (b->type == BUILDING_WAREHOUSE) {
        return building_warehouse_get_amount(b, resource);
    }
    return building_granary_get_amount(b, resource);
}

static int query_building(int argc, char **argv, int *value)
{
    building *b = get_building(argv[1]);
    if (argc != 3 || !b) {
        return 0;
    }
    if (strcmp(argv[2], "state") == 0) {
        *value = b->state;
    } else if (strcmp(argv[2], "type") == 0) {
        *value = b->type;
    } else {
        return 0;
    }
    return 1;
}

static int query_house(int argc, char **argv, int *value)
{
    building *b = get_house(argv[1]);
    int resource;
    if (argc != 3 || !b) {
        return 0;
    }
    if (strcmp(argv[2], "level") == 0) {
        *value = b->type;
    } else if (strcmp(argv[2], "population") == 0) {
        *value = b->house_population;
    } else if (lookup_resource(argv[2], &resource)) {
        *value = b->resources[resource];
    } else {
        return 0;
    }
    return 1;
}

static int query_terrain(int argc, char **argv, int *value)
{
    int xy[2];
    const terrain_type *type = argc == 4 ? lookup_terrain(argv[3]) : 0;
    if (!type || !parse_ints(argv + 1, 2, xy) || !map_grid_is_inside(xy[0], xy[1], 1)) {
        return 0;
    }
    int terrain = map_terrain_get(map_grid_offset(xy[0], xy[1]));
    if (type->terrain) {
        *value = (terrain & type->terrain) ? 1 : 0;
    } else {
        *value = (terrain & GRASS_EXCLUDED_TERRAIN) ? 0 : 1;
    }
    return 1;
}

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
    int number;
    if (strcmp(argv[0], "stock") == 0 && argc == 3) {
        building *b = get_building(argv[1]);
        if (!b || !lookup_resource(argv[2], &number)) {
            return 0;
        }
        *value = get_stock(b, number);
        return 1;
    }
    if (strcmp(argv[0], "city_stock") == 0 && argc == 2) {
        if (!lookup_resource(argv[1], &number)) {
            return 0;
        }
        *value = resource_is_food(number) ?
            city_resource_count_food_on_granaries(number) : city_resource_count_warehouses_amount(number);
        return 1;
    }
    if (strcmp(argv[0], "building_count") == 0 && argc == 2) {
        if (!lookup_building_type(argv[1], &number)) {
            return 0;
        }
        *value = building_count_total(number);
        return 1;
    }
    if (strcmp(argv[0], "building") == 0) {
        return query_building(argc, argv, value);
    }
    if (strcmp(argv[0], "house") == 0) {
        return query_house(argc, argv, value);
    }
    if (strcmp(argv[0], "event") == 0 && argc == 3 && strcmp(argv[2], "executions") == 0) {
        if (!parse_int(argv[1], &number) || number < 0 || number >= scenario_events_get_count()) {
            return 0;
        }
        *value = scenario_event_get(number)->execution_count;
        return 1;
    }
    if (strcmp(argv[0], "variable") == 0 && argc == 2) {
        uint8_t name[MAX_TEXT];
        encoding_from_utf8(argv[1], name, MAX_TEXT);
        unsigned int id = scenario_custom_variable_get_id_by_name(name);
        if (!id) {
            return 0;
        }
        *value = scenario_custom_variable_get_value(id);
        return 1;
    }
    if (strcmp(argv[0], "terrain") == 0) {
        return query_terrain(argc, argv, value);
    }
    return 0;
}

void e2e_state_write_queries(FILE *fp)
{
    for (unsigned int i = 0; i < NUM_SIMPLE_QUERIES; i++) {
        fprintf(fp, "  \"%s\": %d,\n", SIMPLE_QUERIES[i].name, SIMPLE_QUERIES[i].get());
    }
}

// Places a building in the same way as the player, so that the engine checks the place and takes the cost
static int construct(building_type type, int x1, int y1, int x2, int y2)
{
    building_construction_set_type(type, 0);
    building_construction_start(x1, y1, map_grid_offset(x1, y1));
    building_construction_update(x2, y2, map_grid_offset(x2, y2));
    building_construction_place();
    building_construction_clear_type();
    return 1;
}

// A road is terrain, not a building, so the check of a road is the terrain at both ends
static int is_placed(building_type type, int count_before, int x1, int y1, int x2, int y2)
{
    if (type == BUILDING_ROAD) {
        return map_terrain_is(map_grid_offset(x1, y1), TERRAIN_ROAD) &&
            map_terrain_is(map_grid_offset(x2, y2), TERRAIN_ROAD);
    }
    return building_count_total(type) > count_before;
}

int e2e_command_place(int argc, char **argv)
{
    int type;
    int xy[4];
    int has_end = argc == 8 && strcmp(argv[5], "to") == 0;
    if ((argc != 5 && !has_end) || strcmp(argv[2], "at") != 0 || !parse_ints(argv + 3, 2, xy) ||
        (has_end && !parse_ints(argv + 6, 2, xy + 2))) {
        e2e_error("place needs: place <building> at x y [to x2 y2]");
        return E2E_ERROR;
    }
    if (!has_end) {
        xy[2] = xy[0];
        xy[3] = xy[1];
    }
    if (!lookup_building_type(argv[1], &type)) {
        e2e_error("unknown building '%s' (see the names in src/scenario/event/parameter_data.c)", argv[1]);
        return E2E_ERROR;
    }
    if (!map_grid_is_inside(xy[0], xy[1], 1) || !map_grid_is_inside(xy[2], xy[3], 1)) {
        e2e_error("the tiles %d %d to %d %d are not inside the map", xy[0], xy[1], xy[2], xy[3]);
        return E2E_ERROR;
    }
    int count_before = building_count_total(type);
    construct(type, xy[0], xy[1], xy[2], xy[3]);
    if (!is_placed(type, count_before, xy[0], xy[1], xy[2], xy[3])) {
        e2e_error("the engine did not place %s at %d %d", argv[1], xy[0], xy[1]);
        return E2E_ERROR;
    }
    e2e_log("placed %s at %d %d: building %d", argv[1], xy[0], xy[1],
        (int) map_building_at(map_grid_offset(xy[0], xy[1])));
    return E2E_OK;
}

static int parse_region(char **argv, int *region)
{
    return parse_ints(argv, 4, region) &&
        map_grid_is_inside(region[0], region[1], 1) && map_grid_is_inside(region[2], region[3], 1);
}

int e2e_command_clear(int argc, char **argv)
{
    int region[4];
    if (argc != 5 || !parse_region(argv + 1, region)) {
        e2e_error("clear needs: clear x1 y1 x2 y2, inside the map");
        return E2E_ERROR;
    }
    construct(BUILDING_CLEAR_LAND, region[0], region[1], region[2], region[3]);
    return E2E_OK;
}

// Changes the terrain with the brush of the map editor, one tile at a time
int e2e_command_terrain(int argc, char **argv)
{
    int region[4];
    const terrain_type *type = argc == 6 ? lookup_terrain(argv[1]) : 0;
    if (!type || !parse_region(argv + 2, region)) {
        e2e_error("terrain needs: terrain grass|meadow|trees|rocks|water|shrub x1 y1 x2 y2, inside the map");
        return E2E_ERROR;
    }
    editor_tool_set_type(type->tool);
    editor_tool_set_brush_size(1);
    for (int y = region[1]; y <= region[3]; y++) {
        for (int x = region[0]; x <= region[2]; x++) {
            map_tile tile = { x, y, map_grid_offset(x, y) };
            editor_tool_start_use(&tile);
            editor_tool_update_use(&tile);
            editor_tool_end_use(&tile);
        }
    }
    editor_tool_deactivate();
    map_routing_update_all();
    return E2E_OK;
}

static int set_stock(building *b, int resource, int amount)
{
    if (b->type == BUILDING_WAREHOUSE) {
        int current = building_warehouse_get_amount(b, resource);
        if (amount > current) {
            building_warehouse_try_add_resource(b, resource, amount - current, 0);
        } else if (amount < current) {
            building_warehouse_try_remove_resource(b, resource, current - amount);
        }
    } else if (b->type == BUILDING_GRANARY) {
        int current = building_granary_get_amount(b, resource);
        b->resources[RESOURCE_NONE] += current - amount; // the free space of the granary
        b->resources[resource] = amount;
    } else {
        return 0;
    }
    return get_stock(b, resource) == amount;
}

static int set_house(int argc, char **argv)
{
    building *b = get_house(argv[2]);
    int value;
    if (argc != 5 || !b) {
        e2e_error("set house needs: set house <house id> level|population|<resource> <value>");
        return E2E_ERROR;
    }
    if (strcmp(argv[3], "level") == 0) {
        if (!lookup_mapping(PARAMETER_TYPE_HOUSING_TYPE, argv[4], &value)) {
            e2e_error("unknown house level '%s'", argv[4]);
            return E2E_ERROR;
        }
        building_house_change_to(b, value);
        b->data.house.devolve_delay = 0;
        return E2E_OK;
    }
    if (!parse_int(argv[4], &value)) {
        e2e_error("the value '%s' is not a number", argv[4]);
        return E2E_ERROR;
    }
    int resource;
    if (strcmp(argv[3], "population") == 0) {
        b->house_population = value;
    } else if (lookup_resource(argv[3], &resource)) {
        b->resources[resource] = value;
    } else {
        e2e_error("unknown house value '%s'", argv[3]);
        return E2E_ERROR;
    }
    return E2E_OK;
}

int e2e_command_set(int argc, char **argv)
{
    int value;
    if (argc >= 2 && strcmp(argv[1], "house") == 0) {
        return set_house(argc, argv);
    }
    if (argc == 5 && strcmp(argv[1], "stock") == 0) {
        building *b = get_building(argv[2]);
        int resource;
        if (!b || !lookup_resource(argv[3], &resource) || !parse_int(argv[4], &value)) {
            e2e_error("set stock needs: set stock <granary or warehouse id> <resource> <amount>");
            return E2E_ERROR;
        }
        if (!set_stock(b, resource, value)) {
            e2e_error("cannot store %d %s in building %s", value, argv[3], argv[2]);
            return E2E_ERROR;
        }
        return E2E_OK;
    }
    if (argc == 3 && parse_int(argv[2], &value)) {
        if (strcmp(argv[1], "money") == 0) {
            city_finance_treasury_add(value - city_finance_treasury());
            return E2E_OK;
        }
        if (strcmp(argv[1], "favor") == 0) {
            city_ratings_change_favor(value - city_rating_favor());
            return E2E_OK;
        }
    }
    e2e_error("set needs: set money|favor <n>, set stock ..., or set house ...");
    return E2E_ERROR;
}

int e2e_command_date(int argc, char **argv)
{
    int date[3];
    if (argc != 4 || !parse_ints(argv + 1, 3, date) ||
        date[1] < 0 || date[1] >= GAME_TIME_MONTHS_PER_YEAR || date[2] < 0 || date[2] >= GAME_TIME_DAYS_PER_MONTH) {
        e2e_error("date needs: date <year offset> <month 0-%d> <day 0-%d>",
            GAME_TIME_MONTHS_PER_YEAR - 1, GAME_TIME_DAYS_PER_MONTH - 1);
        return E2E_ERROR;
    }
    game_time_set_date(scenario_property_start_year() + date[0], date[1], date[2]);
    return E2E_OK;
}

int e2e_command_variable(int argc, char **argv)
{
    int value;
    if (argc != 3 || !parse_int(argv[2], &value)) {
        e2e_error("variable needs: variable <name> <value>");
        return E2E_ERROR;
    }
    uint8_t name[MAX_TEXT];
    encoding_from_utf8(argv[1], name, MAX_TEXT);
    unsigned int id = scenario_custom_variable_get_id_by_name(name);
    if (!id) {
        e2e_error("unknown custom variable '%s'", argv[1]);
        return E2E_ERROR;
    }
    scenario_custom_variable_set_value(id, value);
    return E2E_OK;
}

int e2e_command_config(int argc, char **argv)
{
    int value;
    int key = argc == 3 ? config_key_from_name(argv[1]) : -1;
    if (key < 0 || !parse_int(argv[2], &value)) {
        e2e_error("config needs: config <key in augustus.ini> <value>");
        return E2E_ERROR;
    }
    if (key == CONFIG_GP_CH_YEARLY_AUTOSAVE) {
        // The yearly autosave writes augustus.ini, which would put the test values in the user options
        e2e_error("the test mode does not allow the yearly autosave");
        return E2E_ERROR;
    }
    config_set(key, value);
    return E2E_OK;
}

int e2e_command_cheat(int argc, char **argv)
{
    if (argc < 2) {
        e2e_error("cheat needs: cheat <cheat command>");
        return E2E_ERROR;
    }
    char text[MAX_TEXT] = { 0 };
    for (int i = 1; i < argc; i++) {
        if (i > 1) {
            strncat(text, " ", MAX_TEXT - strlen(text) - 1);
        }
        strncat(text, argv[i], MAX_TEXT - strlen(text) - 1);
    }
    uint8_t command[MAX_TEXT];
    encoding_from_utf8(text, command, MAX_TEXT);
    game_cheat_parse_command(command);
    return E2E_OK;
}
