/* Headless scenario dumper: loads .mapx files and prints scenario data. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>

#include <SDL.h>

#include "building/properties.h"
#include "building/type.h"
#include "empire/city.h"
#include "empire/trade_route.h"
#include "game/file_editor.h"
#include "game/game.h"
#include "game/resource.h"
#include "map/elevation.h"
#include "map/grid.h"
#include "map/terrain.h"
#include "platform/file_manager.h"
#include "platform/screen.h"
#include "scenario/allowed_building.h"
#include "scenario/custom_messages_export_xml.h"
#include "scenario/custom_variable.h"
#include "scenario/data.h"
#include "scenario/demand_change.h"
#include "scenario/event/export_xml.h"
#include "scenario/invasion.h"
#include "scenario/event/controller.h"
#include "scenario/price_change.h"
#include "scenario/request.h"
#include "game/file.h"
#include "empire/trade_prices.h"

uint64_t system_get_ticks(void) { return 0; }
void system_resize(int width, int height) { (void) width; (void) height; }
void system_set_fullscreen(int fullscreen) { (void) fullscreen; }
int system_supports_select_folder_dialog(void) { return 0; }
const char *system_show_select_folder_dialog(const char *t, const char *d) { (void) t; (void) d; return 0; }
void system_exit(void) { exit(0); }
void system_center(void) { }
void system_reload_textures(void) { }

static const char *res_name(int r)
{
    if (r < 0 || r >= RESOURCE_ALL) return "?";
    const resource_data *d = resource_get_data(r);
    return d && d->xml_attr_name ? d->xml_attr_name : "?";
}

#define BLOCKED (TERRAIN_TREE | TERRAIN_ROCK | TERRAIN_WATER | TERRAIN_SHRUB | TERRAIN_ELEVATION | \
    TERRAIN_ACCESS_RAMP | TERRAIN_BUILDING)

static int comp_id[GRID_SIZE * GRID_SIZE];
static int stack_buf[GRID_SIZE * GRID_SIZE];

static void terrain_stats(const char *ppm_path)
{
    int w = scenario.map.width, h = scenario.map.height;
    long n_tree = 0, n_rock = 0, n_water = 0, n_shallow = 0, n_meadow = 0, n_shrub = 0, n_elev = 0,
         n_ramp = 0, n_build = 0, n_road = 0, n_free = 0, max_h = 0, n_high = 0;
    FILE *ppm = fopen(ppm_path, "wb");
    fprintf(ppm, "P6 %d %d 255\n", w, h);
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            int g = map_grid_offset(x, y);
            int t = map_terrain_get(g);
            int e = map_elevation_at(g);
            if (e > max_h) max_h = e;
            if (e > 0) n_high++;
            unsigned char c[3] = { 200, 190, 140 };
            if (t & TERRAIN_TREE) { n_tree++; c[0] = 30; c[1] = 110; c[2] = 30; }
            if (t & TERRAIN_ROCK) { n_rock++; c[0] = 120; c[1] = 120; c[2] = 120; }
            if (t & TERRAIN_WATER) { n_water++; c[0] = 40; c[1] = 80; c[2] = 200; }
            if (t & TERRAIN_SHALLOW_WATER) { n_shallow++; c[0] = 90; c[1] = 150; c[2] = 230; }
            if (t & TERRAIN_SHRUB) { n_shrub++; c[0] = 90; c[1] = 140; c[2] = 60; }
            if (t & TERRAIN_ELEVATION) { n_elev++; c[0] = 90; c[1] = 60; c[2] = 40; }
            if (t & TERRAIN_ACCESS_RAMP) { n_ramp++; c[0] = 160; c[1] = 100; c[2] = 60; }
            if (t & TERRAIN_BUILDING) { n_build++; c[0] = 220; c[1] = 30; c[2] = 30; }
            if (t & TERRAIN_ROAD) { n_road++; c[0] = 60; c[1] = 40; c[2] = 20; }
            if (t & TERRAIN_MEADOW) { n_meadow++; if (!(t & BLOCKED)) { c[0] = 170; c[1] = 210; c[2] = 90; } }
            if (!(t & BLOCKED)) {
                n_free++;
                if (e > 0 && !(t & (TERRAIN_ROAD | TERRAIN_MEADOW))) {
                    int k = e * 12 > 80 ? 80 : e * 12;
                    c[0] -= k / 2; c[1] -= k / 2; c[2] -= k / 3;
                }
            }
            fwrite(c, 1, 3, ppm);
        }
    }
    fclose(ppm);
    long total = (long) w * h;
    printf("MAP %dx%d = %ld tiles\n", w, h, total);
    printf("TERRAIN free=%ld (%.1f%%) tree=%ld (%.1f%%) rock=%ld (%.1f%%) water=%ld (%.1f%%) shallow=%ld "
        "meadow=%ld shrub=%ld cliff=%ld ramp=%ld native/building=%ld road=%ld\n",
        n_free, 100.0 * n_free / total, n_tree, 100.0 * n_tree / total, n_rock, 100.0 * n_rock / total,
        n_water, 100.0 * n_water / total, n_shallow, n_meadow, n_shrub, n_elev, n_ramp, n_build, n_road);
    printf("ELEVATION max=%ld tiles_above_0=%ld (%.1f%%)\n", max_h, n_high, 100.0 * n_high / total);

    /* Connected regions of free land (4-neighbour, same elevation not required: ramps are separate). */
    memset(comp_id, 0, sizeof(comp_id));
    int ncomp = 0;
    long sizes[4096];
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            int g = map_grid_offset(x, y);
            if (comp_id[g] || (map_terrain_get(g) & BLOCKED)) continue;
            ncomp++;
            long size = 0;
            int sp = 0;
            stack_buf[sp++] = g;
            comp_id[g] = ncomp;
            while (sp) {
                int cur = stack_buf[--sp];
                size++;
                int cx = map_grid_offset_to_x(cur), cy = map_grid_offset_to_y(cur);
                int nx[4] = { cx + 1, cx - 1, cx, cx }, ny[4] = { cy, cy, cy + 1, cy - 1 };
                for (int i = 0; i < 4; i++) {
                    if (nx[i] < 0 || ny[i] < 0 || nx[i] >= w || ny[i] >= h) continue;
                    int ng = map_grid_offset(nx[i], ny[i]);
                    if (comp_id[ng] || (map_terrain_get(ng) & BLOCKED)) continue;
                    if (map_elevation_at(ng) != map_elevation_at(cur)) continue;
                    comp_id[ng] = ncomp;
                    stack_buf[sp++] = ng;
                }
            }
            if (ncomp < 4096) sizes[ncomp] = size;
        }
    }
    /* top regions */
    long top[8] = { 0 };
    int big = 0;
    for (int i = 1; i <= ncomp && i < 4096; i++) {
        if (sizes[i] >= 400) big++;
        for (int k = 0; k < 8; k++) {
            if (sizes[i] > top[k]) {
                memmove(&top[k + 1], &top[k], (7 - k) * sizeof(long));
                top[k] = sizes[i];
                break;
            }
        }
    }
    printf("REGIONS (free land, same elevation) count=%d regions>=400tiles=%d largest:", ncomp, big);
    for (int k = 0; k < 8 && top[k]; k++) printf(" %ld", top[k]);
    printf("  (largest share of free=%.1f%%)\n", n_free ? 100.0 * top[0] / n_free : 0);
}

#define BLOCKED2 (TERRAIN_ROCK | TERRAIN_WATER | TERRAIN_ELEVATION | TERRAIN_ACCESS_RAMP | TERRAIN_BUILDING)
static void regions_clearable(void)
{
    int w = scenario.map.width, h = scenario.map.height;
    memset(comp_id, 0, sizeof(comp_id));
    long total = 0, best = 0; int ncomp = 0, big = 0;
    for (int y = 0; y < h; y++) for (int x = 0; x < w; x++) {
        int g = map_grid_offset(x, y);
        if (comp_id[g] || (map_terrain_get(g) & BLOCKED2)) continue;
        ncomp++; long size = 0; int sp = 0; stack_buf[sp++] = g; comp_id[g] = ncomp;
        while (sp) {
            int cur = stack_buf[--sp]; size++;
            int cx = map_grid_offset_to_x(cur), cy = map_grid_offset_to_y(cur);
            int nx[4] = { cx + 1, cx - 1, cx, cx }, ny[4] = { cy, cy, cy + 1, cy - 1 };
            for (int i = 0; i < 4; i++) {
                if (nx[i] < 0 || ny[i] < 0 || nx[i] >= w || ny[i] >= h) continue;
                int ng = map_grid_offset(nx[i], ny[i]);
                if (comp_id[ng] || (map_terrain_get(ng) & BLOCKED2)) continue;
                if (map_elevation_at(ng) != map_elevation_at(cur)) continue;
                comp_id[ng] = ncomp; stack_buf[sp++] = ng;
            }
        }
        total += size; if (size > best) best = size; if (size >= 400) big++;
    }
    printf("REGIONS2 (trees/shrub clearable) usable=%ld (%.1f%%) count=%d >=400=%d largest=%ld (share %.1f%%)\n",
        total, 100.0 * total / (w * h), ncomp, big, best, total ? 100.0 * best / total : 0);
}

#include "patterns.inc"

static model_building def_b[BUILDING_TYPE_MAX];
static model_house def_h[HOUSE_MAX + 1];
static void snapshot_defaults(void)
{
    model_reset();
    for (int t = 0; t < BUILDING_TYPE_MAX; t++) { model_building *m = model_get_building(t); if (m) def_b[t] = *m; }
    for (int l = 0; l <= HOUSE_MAX; l++) { model_house *m = model_get_house(l); if (m) def_h[l] = *m; }
}
static void model_diff(void)
{
    printf("MODEL_DIFF:");
    for (int t = 1; t < BUILDING_TYPE_MAX; t++) {
        model_building *m = model_get_building(t);
        const building_properties *p = building_properties_for_type(t);
        if (!m || !p || !p->event_data.attr) continue;
        if (m->laborers != def_b[t].laborers) printf(" %s.workers %d->%d", p->event_data.attr, def_b[t].laborers, m->laborers);
        if (m->cost != def_b[t].cost) printf(" %s.cost %d->%d", p->event_data.attr, def_b[t].cost, m->cost);
        if (m->desirability_value != def_b[t].desirability_value) printf(" %s.desir %d->%d", p->event_data.attr, def_b[t].desirability_value, m->desirability_value);
    }
    for (int l = 0; l <= HOUSE_MAX; l++) {
        model_house *m = model_get_house(l);
        if (!m) continue;
        if (memcmp(m, &def_h[l], sizeof(model_house))) {
            printf(" house%d[food %d->%d ent %d->%d rel %d->%d wine %d->%d evolve %d->%d people %d->%d]", l,
                def_h[l].food_types, m->food_types, def_h[l].entertainment, m->entertainment, def_h[l].religion, m->religion,
                def_h[l].wine, m->wine, def_h[l].evolve_desirability, m->evolve_desirability, def_h[l].max_people, m->max_people);
        }
    }
    printf("\n");
}

static void point(const char *name, map_point p)
{
    if (p.x >= 0 && p.y >= 0) printf(" %s=(%d,%d)", name, p.x, p.y);
}

static void dump(const char *path, const char *outdir, const char *tag)
{
    int is_save = strstr(path, ".svx") != 0;
    if (is_save ? game_file_load_saved_game(path) != 1 : !game_file_editor_load_scenario(path)) {
        printf("LOAD FAILED %s\n", path);
        return;
    }
    printf("##### %s\n", tag);
    printf("NAME %s\n", scenario.scenario_name);
    printf("BRIEF %s\n", scenario.brief_description);
    printf("START year=%d climate=%d rank=%d salary=%d funds=%d rescue_loan=%d rome_wheat=%d enemy_id=%d "
        "open_play=%d start_favor=%d savings=%d reset_favor_monthly=%d\n",
        scenario.start_year, scenario.climate, scenario.player_rank, scenario.caesar_salary, scenario.initial_funds,
        scenario.rescue_loan, scenario.rome_supplies_wheat, scenario.enemy_id, scenario.is_open_play,
        scenario.settings.starting_favor, scenario.settings.starting_personal_savings, scenario.reset_favour_monthly);
    const scenario_win_criteria *wc = &scenario.win_criteria;
    printf("WIN pop=%d:%d culture=%d:%d prosperity=%d:%d peace=%d:%d favor=%d:%d time_limit=%d:%d survival=%d:%d "
        "milestones=%d/%d/%d\n",
        wc->population.enabled, wc->population.goal, wc->culture.enabled, wc->culture.goal,
        wc->prosperity.enabled, wc->prosperity.goal, wc->peace.enabled, wc->peace.goal,
        wc->favor.enabled, wc->favor.goal, wc->time_limit.enabled, wc->time_limit.years,
        wc->survival_time.enabled, wc->survival_time.years,
        wc->milestone25_year, wc->milestone50_year, wc->milestone75_year);
    printf("EMPIRE id=%d custom=%s expanded=%d expansion_year=%d battle_travel roman=%d enemy=%d\n",
        scenario.empire.id, scenario.empire.custom_name, scenario.empire.is_expanded, scenario.empire.expansion_year,
        scenario.empire.distant_battle_roman_travel_months, scenario.empire.distant_battle_enemy_travel_months);
    printf("DISASTERS earthquake sev=%d year=%d | emperor_change=%d:%d | gladiator_revolt=%d:%d\n",
        scenario.earthquake.severity, scenario.earthquake.year, scenario.emperor_change.enabled,
        scenario.emperor_change.year, scenario.gladiator_revolt.enabled, scenario.gladiator_revolt.year);
    printf("RANDOM sea_trade=%d land_trade=%d raise_wages=%d lower_wages=%d bad_water=%d iron_collapse=%d clay_flood=%d"
        " flotsam=%d\n",
        scenario.random_events.sea_trade_problem, scenario.random_events.land_trade_problem,
        scenario.random_events.raise_wages, scenario.random_events.lower_wages,
        scenario.random_events.contaminated_water, scenario.random_events.iron_mine_collapse,
        scenario.random_events.clay_pit_flooded, scenario.flotsam_enabled);
    printf("POINTS");
    point("entry", scenario.entry_point);
    point("exit", scenario.exit_point);
    point("river_in", scenario.river_entry_point);
    point("river_out", scenario.river_exit_point);
    point("quake", scenario.earthquake_point);
    int n_inv = 0, n_herd = 0, n_fish = 0;
    for (int i = 0; i < MAX_INVASION_POINTS; i++) {
        if (scenario.invasion_points[i].x >= 0) { n_inv++; point("inv", scenario.invasion_points[i]); }
    }
    for (int i = 0; i < MAX_HERD_POINTS; i++) if (scenario.herd_points[i].x >= 0) n_herd++;
    for (int i = 0; i < MAX_FISH_POINTS; i++) if (scenario.fishing_points[i].x >= 0) n_fish++;
    printf(" | invasion_pts=%d herd_pts=%d fish_pts=%d\n", n_inv, n_herd, n_fish);

    regions_clearable();
    model_diff();
    terrain_stats(strcat(strcpy((char[512]){0}, outdir), "/map.ppm"));
    terrain_patterns();
    site_counts();
    if (is_save) {
        printf("SAVE executed_events:");
        for (int i = 0; i < scenario_events_get_count(); i++) {
            scenario_event_t *e = scenario_event_get(i);
            if (e && e->execution_count) printf(" E%d(x%d,state%d)", i, e->execution_count, e->state);
        }
        printf("\n");
    }
    if (is_save) {
        printf("SAVE stock:");
        for (int r = 1; r < RESOURCE_MAX; r++) {
            int total = 0;
            for (int i = 1; i < building_count(); i++) {
                building *b = building_get(i);
                if (!b || b->state != BUILDING_STATE_IN_USE) continue;
                if (b->type == BUILDING_WAREHOUSE_SPACE || b->type == BUILDING_GRANARY) total += b->resources[r];
            }
            if (total) printf(" %s=%d", res_name(r), total);
        }
        printf("\n");
    }
    if (is_save) printf("SAVE treasury=%d population=%d\n", city_finance_treasury(), city_population());

    printf("FORBIDDEN BUILDINGS:");
    for (int t = 1; t < BUILDING_TYPE_MAX; t++) {
        const building_properties *p = building_properties_for_type(t);
        if (!p || !p->event_data.attr) continue;
        if (!scenario_allowed_building(t)) printf(" %s", p->event_data.attr);
    }
    printf("\n");

    printf("INVASIONS total=%d\n", scenario_invasion_count_total());
    for (int i = 0; i < scenario_invasion_count_total(); i++) {
        const invasion_t *v = scenario_invasion_get(i);
        if (!v || !v->type) continue;
        printf("  inv year+%d month=%d type=%d amount=%u-%u from=%d attack=%d repeat=%d every %u-%u y\n",
            v->year, v->month, v->type, v->amount.min, v->amount.max, v->from, v->attack_type,
            v->repeat.times, v->repeat.interval.min, v->repeat.interval.max);
    }
    printf("REQUESTS total=%u\n", scenario_request_count_total());
    for (unsigned int i = 0; i < scenario_request_count_total(); i++) {
        const scenario_request *r = scenario_request_get(i);
        if (!r || !r->resource) continue;
        printf("  req year+%d month=%d %s %u-%u deadline=%dm favor=%d repeat=%d every %u-%u y vis=%d\n",
            r->year, r->month, res_name(r->resource), r->amount.min, r->amount.max, r->months_to_comply, r->favor,
            r->repeat.times, r->repeat.interval.min, r->repeat.interval.max, r->visible);
    }
    printf("DEMAND_CHANGES total=%u\n", scenario_demand_change_count_total());
    for (unsigned int i = 0; i < scenario_demand_change_count_total(); i++) {
        const demand_change_t *d = scenario_demand_change_get(i);
        if (!d || !d->year) continue;
        printf("  dem year+%d month=%d %s route=%d amount=%d buys=%d\n", d->year, d->month, res_name(d->resource),
            d->route_id, d->amount, d->buys);
    }
    printf("PRICE_CHANGES total=%u\n", scenario_price_change_count_total());
    for (unsigned int i = 0; i < scenario_price_change_count_total(); i++) {
        const price_change_t *p = scenario_price_change_get(i);
        if (!p || !p->year) continue;
        printf("  price year+%d month=%d %s %s%d\n", p->year, p->month, res_name(p->resource),
            p->is_rise ? "+" : "-", p->amount);
    }
    printf("TRADE ROUTES count=%d\n", trade_route_count());
    for (int route = 1; route < trade_route_count(); route++) {
        int cid = empire_city_get_for_trade_route(route);
        if (cid < 0) continue;
        empire_city *c = empire_city_get(cid);
        if (!c || !c->in_use) continue;
        printf("  route %d %s type=%d %s open=%d cost=%u | sells:", route, empire_city_get_name(c), c->type,
            c->is_sea_trade ? "SEA" : "LAND", c->is_open, c->cost_to_open);
        for (int r = 1; r < RESOURCE_MAX; r++) {
            if (c->sells_resource[r]) printf(" %s(%d)", res_name(r), trade_route_limit(route, r, 0));
        }
        printf(" | buys:");
        for (int r = 1; r < RESOURCE_MAX; r++) {
            if (c->buys_resource[r]) printf(" %s(%d)", res_name(r), trade_route_limit(route, r, 1));
        }
        printf("\n");
    }
    if (!is_save) trade_prices_reset();
    printf("PRICES%s buy/sell:", is_save ? "(save)" : "(default)");
    for (int r = 1; r < RESOURCE_MAX; r++) {
        printf(" %s=%d/%d", res_name(r), trade_price_base_buy(r), trade_price_base_sell(r));
    }
    printf("\n");
    for (int l = 0; l <= HOUSE_MAX; l++) {
        model_house *m = model_get_house(l);
        printf("HOUSE %d devolve=%d evolve=%d ent=%d water=%d religion=%d edu=%d barber=%d bath=%d health=%d food=%d "
            "pottery=%d oil=%d furniture=%d wine=%d prosperity=%d people=%d tax=%d\n", l, m->devolve_desirability,
            m->evolve_desirability, m->entertainment, m->water, m->religion, m->education, m->barber, m->bathhouse,
            m->health, m->food_types, m->pottery, m->oil, m->furniture, m->wine, m->prosperity, m->max_people,
            m->tax_multiplier);
    }
    printf("BMODEL");
    for (int t = 1; t < BUILDING_TYPE_MAX; t++) {
        model_building *m = model_get_building(t);
        const building_properties *p = building_properties_for_type(t);
        if (!m || !p || !p->event_data.attr) continue;
        printf(" %s=%d:%d:%d", p->event_data.attr, m->cost, m->laborers, p->size);
    }
    printf("\n");
    printf("PRODUCTION res:industry:per_month:workers:");
    for (int r = 1; r < RESOURCE_MAX; r++) {
        const resource_data *rd = resource_get_data(r);
        model_building *mb = rd->industry ? model_get_building(rd->industry) : 0;
        printf(" %s=%d:%d:%d", res_name(r), rd->industry, rd->production_per_month, mb ? mb->laborers : 0);
    }
    printf("\n");
    printf("LOCAL can_produce:");
    for (int r = 1; r < RESOURCE_MAX; r++) {
        if (empire_can_produce_resource_locally(r)) printf(" %s", res_name(r));
    }
    printf("\n");
    printf("CUSTOM_VARIABLES count=%u:", scenario_custom_variable_count());
    for (unsigned int i = 0; i < scenario_custom_variable_count(); i++) {
        if (scenario_custom_variable_exists(i)) {
            printf(" [%s=%d%s]", scenario_custom_variable_get_name(i), scenario_custom_variable_get_value(i),
                scenario_custom_variable_is_visible(i) ? ",visible" : "");
        }
    }
    printf("\n");

    for (unsigned int i = 1; i < 400; i++) {
        scenario_formula_t *f = scenario_formula_get(i);
        if (!f) break;
        if (f->is_error) printf("FORMULA_ERROR id=%u '%s'\n", i, f->formatted_calculation);
        else if (strchr((const char *) f->formatted_calculation, ',') || strchr((const char *) f->formatted_calculation, '(')) {
            int r1 = scenario_formula_evaluate_formula(i), r2 = scenario_formula_evaluate_formula(i), r3 = scenario_formula_evaluate_formula(i);
            printf("FORMULA id=%u '%s' static=%d eval=%d,%d,%d range=[%d,%d]\n", i, f->formatted_calculation, f->is_static,
                r1, r2, r3, f->min_evaluation, f->max_evaluation);
        }
    }
    char buf[512];
    snprintf(buf, sizeof(buf), "%s/events.xml", outdir);
    printf("EVENTS_XML %d\n", scenario_events_export_to_xml(buf));
    snprintf(buf, sizeof(buf), "%s/messages.xml", outdir);
    printf("MESSAGES_XML %d\n", custom_messages_export_to_xml(buf));
    fflush(stdout);
}

int main(int argc, char **argv)
{
    if (argc < 4 || (argc - 2) % 2) {
        fprintf(stderr, "usage: %s <data_dir> <mapx> <outdir> [<mapx> <outdir>...]\n", argv[0]);
        return 2;
    }
    setenv("SDL_AUDIODRIVER", "dummy", 1);
    if (SDL_Init(SDL_INIT_VIDEO | SDL_INIT_AUDIO) != 0) return 3;
    if (!platform_file_manager_set_base_path(argv[1])) return 4;
    if (!game_pre_init()) return 5;
    if (!platform_screen_create("dump", 100, 0)) return 6;
    if (!game_init()) return 7;
    snapshot_defaults();
    for (int i = 2; i + 1 < argc; i += 2) {
        dump(argv[i], argv[i + 1], argv[i]);
    }
    return 0;
}
