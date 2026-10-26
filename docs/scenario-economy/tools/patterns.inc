/* Terrain pattern metrics. Included by dumper3.c after terrain_stats(). */
#include "building/building.h"
#include "city/finance.h"
#include "city/population.h"

#define U_BLOCK (TERRAIN_ROCK | TERRAIN_WATER | TERRAIN_ELEVATION | TERRAIN_ACCESS_RAMP | TERRAIN_BUILDING | \
    TERRAIN_MARSHLAND)
#define WALK_BLOCK (TERRAIN_ROCK | TERRAIN_WATER | TERRAIN_ELEVATION | TERRAIN_BUILDING | TERRAIN_MARSHLAND)
#define N GRID_SIZE * GRID_SIZE

static int g_dist[N], g_tmp[N], g_clear[N], g_q[N];
static int g_w, g_h;

/* Routing treats ramps and beach as walkable even when other flags are set. */
static int blocked(int g, int mask)
{
    int t = map_terrain_get(g);
    if (!(mask & TERRAIN_ACCESS_RAMP) && (t & (TERRAIN_ACCESS_RAMP | TERRAIN_BEACH | TERRAIN_ROAD))) return 0;
    return (t & mask) != 0;
}

/* Multi-source chebyshev distance from every tile that matches mask (map edge counts if edge_blocks). */
static void clearance(int mask, int edge_blocks, int *out)
{
    int qh = 0, qt = 0;
    for (int y = 0; y < g_h; y++) for (int x = 0; x < g_w; x++) {
        int g = map_grid_offset(x, y);
        out[g] = -1;
        if (blocked(g, mask)) { out[g] = 0; g_q[qt++] = g; }
        else if (edge_blocks && (x == 0 || y == 0 || x == g_w - 1 || y == g_h - 1)) { out[g] = 1; g_q[qt++] = g; }
    }
    while (qh < qt) {
        int c = g_q[qh++], cx = map_grid_offset_to_x(c), cy = map_grid_offset_to_y(c);
        for (int dy = -1; dy <= 1; dy++) for (int dx = -1; dx <= 1; dx++) {
            int nx = cx + dx, ny = cy + dy;
            if (nx < 0 || ny < 0 || nx >= g_w || ny >= g_h) continue;
            int ng = map_grid_offset(nx, ny);
            if (out[ng] != -1) continue;
            out[ng] = out[c] + 1;
            g_q[qt++] = ng;
        }
    }
    for (int y = 0; y < g_h; y++) for (int x = 0; x < g_w; x++) {
        int g = map_grid_offset(x, y);
        if (out[g] == -1) out[g] = 999;
    }
}

/* 4-neighbour BFS from src over tiles not matching mask and with clear[] >= min_clear. */
static void bfs(int src, int mask, const int *clear, int min_clear, int *out)
{
    for (int y = 0; y < g_h; y++) for (int x = 0; x < g_w; x++) out[map_grid_offset(x, y)] = -1;
    if (blocked(src, mask)) {
        int sx = map_grid_offset_to_x(src), sy = map_grid_offset_to_y(src), found = -1;
        for (int r = 1; r <= 3 && found < 0; r++) for (int dy = -r; dy <= r && found < 0; dy++) for (int dx = -r; dx <= r; dx++) {
            int nx = sx + dx, ny = sy + dy;
            if (nx < 0 || ny < 0 || nx >= g_w || ny >= g_h) continue;
            int ng = map_grid_offset(nx, ny);
            if (!blocked(ng, mask)) { found = ng; break; }
        }
        if (found < 0) return;
        src = found;
    }
    if (clear && clear[src] < min_clear) return;
    int qh = 0, qt = 0;
    out[src] = 0; g_q[qt++] = src;
    while (qh < qt) {
        int c = g_q[qh++], cx = map_grid_offset_to_x(c), cy = map_grid_offset_to_y(c);
        int nx[4] = { cx + 1, cx - 1, cx, cx }, ny[4] = { cy, cy, cy + 1, cy - 1 };
        for (int i = 0; i < 4; i++) {
            if (nx[i] < 0 || ny[i] < 0 || nx[i] >= g_w || ny[i] >= g_h) continue;
            int ng = map_grid_offset(nx[i], ny[i]);
            if (out[ng] != -1 || blocked(ng, mask) || (clear && clear[ng] < min_clear)) continue;
            out[ng] = out[c] + 1;
            g_q[qt++] = ng;
        }
    }
}

/* Largest k such that a path src->dst exists through tiles with clearance >= k. */
static int bottleneck(int src, int dst, int mask, const int *clear)
{
    int hi = clear[src] < clear[dst] ? clear[src] : clear[dst];
    if (hi > 60) hi = 60;
    for (int k = hi; k >= 1; k--) {
        bfs(src, mask, clear, k, g_tmp);
        if (g_tmp[dst] >= 0) return k;
    }
    return 0;
}

static int *g_lab, g_big;
static int dist_to_region(const int *d)
{
    int best = -1;
    for (int y = 0; y < g_h; y++) for (int x = 0; x < g_w; x++) {
        int g = map_grid_offset(x, y);
        if (g_lab[g] == g_big && d[g] >= 0 && (best < 0 || d[g] < best)) best = d[g];
    }
    return best;
}
static int bottleneck_region(int src, int mask, const int *clear)
{
    for (int k = 30; k >= 1; k--) {
        bfs(src, mask, clear, k, g_tmp);
        if (dist_to_region(g_tmp) >= 0) return k;
    }
    return 0;
}

static int cmp_int(const void *a, const void *b) { return *(const int *) a - *(const int *) b; }

static void terrain_patterns(void)
{
    g_w = scenario.map.width; g_h = scenario.map.height;
    /* city centre: usable tile with the largest clearance from non-usable terrain (trees count as usable). */
    static int lab[N];
    int nl = 0, big_lab = 0; long big_size = 0;
    for (int y = 0; y < g_h; y++) for (int x = 0; x < g_w; x++) lab[map_grid_offset(x, y)] = 0;
    for (int y = 0; y < g_h; y++) for (int x = 0; x < g_w; x++) {
        int g0 = map_grid_offset(x, y);
        if (lab[g0] || blocked(g0, U_BLOCK)) continue;
        nl++; long size = 0; int qh = 0, qt = 0; g_q[qt++] = g0; lab[g0] = nl;
        while (qh < qt) {
            int c = g_q[qh++], cx = map_grid_offset_to_x(c), cy = map_grid_offset_to_y(c); size++;
            int nx[4] = { cx + 1, cx - 1, cx, cx }, ny[4] = { cy, cy, cy + 1, cy - 1 };
            for (int i = 0; i < 4; i++) {
                if (nx[i] < 0 || ny[i] < 0 || nx[i] >= g_w || ny[i] >= g_h) continue;
                int ng = map_grid_offset(nx[i], ny[i]);
                if (lab[ng] || blocked(ng, U_BLOCK) || map_elevation_at(ng) != map_elevation_at(c)) continue;
                lab[ng] = nl; g_q[qt++] = ng;
            }
        }
        if (size > big_size) { big_size = size; big_lab = nl; }
    }
    g_lab = lab; g_big = big_lab;
    clearance(U_BLOCK, 1, g_clear);
    int center = -1, best = -1;
    for (int y = 0; y < g_h; y++) for (int x = 0; x < g_w; x++) {
        int g = map_grid_offset(x, y);
        if (lab[g] == big_lab && g_clear[g] > best) { best = g_clear[g]; center = g; }
    }
    if (center < 0) { printf("PATTERN no usable land\n"); return; }
    int open_square_clearable = 2 * best - 1;
    clearance(U_BLOCK | TERRAIN_TREE | TERRAIN_SHRUB, 1, g_tmp);
    int best_now = 0;
    for (int y = 0; y < g_h; y++) for (int x = 0; x < g_w; x++) {
        int g = map_grid_offset(x, y);
        if (g_tmp[g] < 999 && g_tmp[g] > best_now) best_now = g_tmp[g];
    }
    printf("PATTERN center=(%d,%d) open_square_side clearable=%d now=%d\n", map_grid_offset_to_x(center),
        map_grid_offset_to_y(center), open_square_clearable, 2 * best_now - 1);

    /* land reachable from centre by walking (trees clearable, ramps walkable) */
    bfs(center, WALK_BLOCK, 0, 0, g_dist);
    long reach = 0, usable = 0;
    for (int y = 0; y < g_h; y++) for (int x = 0; x < g_w; x++) {
        int g = map_grid_offset(x, y);
        if (blocked(g, U_BLOCK)) continue;
        usable++;
        if (g_dist[g] >= 0) reach++;
    }
    printf("PATTERN usable_land_walk_connected_to_center=%.1f%%\n", usable ? 100.0 * reach / usable : 0);

    /* elevation levels and ramps */
    int levels[64] = { 0 }, nlev = 0, ramps = 0;
    for (int y = 0; y < g_h; y++) for (int x = 0; x < g_w; x++) {
        int g = map_grid_offset(x, y);
        if (map_terrain_get(g) & TERRAIN_ACCESS_RAMP) ramps++;
        int e = map_elevation_at(g);
        if (e >= 0 && e < 64 && !blocked(g, U_BLOCK)) levels[e]++;
    }
    printf("PATTERN elevation_levels(usable tiles):");
    for (int e = 0; e < 64; e++) if (levels[e]) { nlev++; printf(" h%d=%d", e, levels[e]); }
    printf(" | levels=%d ramp_tiles=%d\n", nlev, ramps);

    /* water distance for usable land walk-connected to the centre */
    clearance(TERRAIN_WATER, 0, g_tmp);
    int *wd = malloc(sizeof(int) * N);
    int nwd = 0, coast = 0, near3 = 0, near10 = 0;
    for (int y = 0; y < g_h; y++) for (int x = 0; x < g_w; x++) {
        int g = map_grid_offset(x, y);
        if (blocked(g, U_BLOCK) || g_dist[g] < 0) continue;
        int d = g_tmp[g];
        wd[nwd++] = d;
        if (d == 1) coast++;
        if (d <= 3) near3++;
        if (d <= 10) near10++;
    }
    if (nwd) {
        qsort(wd, nwd, sizeof(int), cmp_int);
        printf("PATTERN water_dist(connected land) median=%d p90=%d max=%d coast=%d within3=%.1f%% within10=%.1f%%\n",
            wd[nwd / 2], wd[nwd * 9 / 10], wd[nwd - 1], coast, 100.0 * near3 / nwd, 100.0 * near10 / nwd);
    }
    free(wd);

    /* meadow and raw material sites in connected land */
    int meadow = 0, rock_sites = 0, tree_tiles = 0, rock_tiles = 0;
    for (int y = 0; y < g_h; y++) for (int x = 0; x < g_w; x++) {
        int g = map_grid_offset(x, y);
        int t = map_terrain_get(g);
        if (t & TERRAIN_TREE) tree_tiles++;
        if (t & TERRAIN_ROCK) rock_tiles++;
        if (blocked(g, U_BLOCK) || g_dist[g] < 0) continue;
        if (t & TERRAIN_MEADOW) meadow++;
        int adj_rock = 0;
        for (int dy = -1; dy <= 1 && !adj_rock; dy++) for (int dx = -1; dx <= 1; dx++) {
            int nx = x + dx, ny = y + dy;
            if (nx < 0 || ny < 0 || nx >= g_w || ny >= g_h) continue;
            if (map_terrain_get(map_grid_offset(nx, ny)) & TERRAIN_ROCK) { adj_rock = 1; break; }
        }
        rock_sites += adj_rock;
    }
    printf("PATTERN connected: meadow=%d (%.1f%% of usable) rock_edge_sites=%d | map tree=%d rock=%d\n",
        meadow, usable ? 100.0 * meadow / usable : 0, rock_sites, tree_tiles, rock_tiles);

    /* entry / exit */
    map_point en = scenario.entry_point, ex = scenario.exit_point;
    if (en.x >= 0) {
        int ge = map_grid_offset(en.x, en.y), gx = ex.x >= 0 ? map_grid_offset(ex.x, ex.y) : -1;
        bfs(ge, WALK_BLOCK, 0, 0, g_tmp);
        printf("PATTERN entry->region walk=%d entry->center walk=%d", dist_to_region(g_tmp), g_dist[ge]);
        if (gx >= 0) {
            bfs(ge, WALK_BLOCK, 0, 0, g_tmp);
            printf(" entry->exit walk=%d", g_tmp[gx]);
        }
        printf("\n");
    }

    /* invasion approaches: enemy terrain, trees block enemies */
    static int eclear[N];
    clearance(TERRAIN_IMPASSABLE_ENEMY, 0, eclear);
    clearance(TERRAIN_IMPASSABLE_ENEMY & ~(TERRAIN_TREE | TERRAIN_SHRUB), 0, g_clear);
    int ninv = 0, nreach = 0;
    for (int i = 0; i < MAX_INVASION_POINTS; i++) {
        map_point p = scenario.invasion_points[i];
        if (p.x < 0) continue;
        ninv++;
        int gi = map_grid_offset(p.x, p.y);
        bfs(gi, TERRAIN_IMPASSABLE_ENEMY, 0, 0, g_tmp);
        int d = g_tmp[center];
        int k = d >= 0 ? bottleneck(gi, center, TERRAIN_IMPASSABLE_ENEMY, eclear) : 0;
        bfs(gi, TERRAIN_IMPASSABLE_ENEMY & ~(TERRAIN_TREE | TERRAIN_SHRUB), 0, 0, g_tmp);
        int d2 = g_tmp[center];
        int k2 = d2 >= 0 ? bottleneck(gi, center, TERRAIN_IMPASSABLE_ENEMY & ~(TERRAIN_TREE | TERRAIN_SHRUB), g_clear) : 0;
        if (d >= 0) nreach++;
        bfs(gi, TERRAIN_IMPASSABLE_ENEMY, 0, 0, g_tmp);
        int rd = dist_to_region(g_tmp);
        int rk = rd >= 0 ? bottleneck_region(gi, TERRAIN_IMPASSABLE_ENEMY, eclear) : 0;
        bfs(gi, TERRAIN_IMPASSABLE_ENEMY & ~(TERRAIN_TREE | TERRAIN_SHRUB), 0, 0, g_tmp);
        int rd2 = dist_to_region(g_tmp);
        int rk2 = rd2 >= 0 ? bottleneck_region(gi, TERRAIN_IMPASSABLE_ENEMY & ~(TERRAIN_TREE | TERRAIN_SHRUB), g_clear) : 0;
        printf("PATTERN inv%d to_region dist=%d choke=%d | cut dist=%d choke=%d\n", i, rd, rk ? 2 * rk - 1 : 0,
            rd2, rk2 ? 2 * rk2 - 1 : 0);
        printf("PATTERN inv%d (%d,%d) to_center dist=%d choke_width=%d | trees_cleared dist=%d choke_width=%d\n", i,
            p.x, p.y, d, k ? 2 * k - 1 : 0, d2, k2 ? 2 * k2 - 1 : 0);
    }
    int marsh = 0, beach = 0;
    for (int y = 0; y < g_h; y++) for (int x = 0; x < g_w; x++) {
        int t = map_terrain_get(map_grid_offset(x, y));
        if (t & TERRAIN_MARSHLAND) marsh++;
        if (t & TERRAIN_BEACH) beach++;
    }
    for (int i = 0; i < MAX_INVASION_POINTS; i++) {
        map_point p = scenario.invasion_points[i];
        if (p.x < 0) continue;
        printf("PATTERN invpt%d terrain=0x%x\n", i, map_terrain_get(map_grid_offset(p.x, p.y)));
    }
    printf("PATTERN marsh=%d beach=%d\n", marsh, beach);
    printf("PATTERN invasion_points=%d reach_center_with_trees=%d\n", ninv, nreach);

    /* natives and other pre-placed buildings */
    int counts[BUILDING_TYPE_MAX] = { 0 }, total = 0, native_min = -1;
    bfs(center, WALK_BLOCK & ~TERRAIN_BUILDING, 0, 0, g_tmp);
    for (int i = 1; i < building_count(); i++) {
        building *b = building_get(i);
        if (!b || b->state != BUILDING_STATE_IN_USE || b->type <= 0 || b->type >= BUILDING_TYPE_MAX) continue;
        counts[b->type]++; total++;
        if (b->type == BUILDING_NATIVE_HUT || b->type == BUILDING_NATIVE_HUT_ALT || b->type == BUILDING_NATIVE_HUT_ALT_2 ||
            b->type == BUILDING_NATIVE_MEETING || b->type == BUILDING_NATIVE_LARGE_HUT_ALT) {
            int d = g_tmp[b->grid_offset];
            if (d >= 0 && (native_min < 0 || d < native_min)) native_min = d;
        }
    }
    printf("PATTERN buildings total=%d native_min_walk_to_center=%d:", total, native_min);
    for (int t = 1; t < BUILDING_TYPE_MAX; t++) {
        if (!counts[t]) continue;
        const building_properties *p = building_properties_for_type(t);
        if (p && p->event_data.attr) printf(" %s=%d", p->event_data.attr, counts[t]);
        else printf(" type%d=%d", t, counts[t]);
    }
    printf("\n");
    for (int i = 0; i < MAX_HERD_POINTS; i++) {
        map_point p = scenario.herd_points[i];
        if (p.x < 0) continue;
        int d = g_dist[map_grid_offset(p.x, p.y)];
        printf("PATTERN herd%d walk_to_center=%d\n", i, d);
    }
}

/* Production sites: greedy packing of each building type with the engine footprint and terrain rule
   (building/construction.c:1400-1433). Trees, shrub and meadow count as clearable; roads count as blocked. */
#define SITE_BLOCK (TERRAIN_ROCK | TERRAIN_WATER | TERRAIN_ELEVATION | TERRAIN_ACCESS_RAMP | TERRAIN_BUILDING | \
    TERRAIN_MARSHLAND | TERRAIN_BEACH | TERRAIN_ROAD)
static unsigned char site_used[N];

static int area_has(int x, int y, int size, int radius, int mask)
{
    for (int yy = y - radius; yy < y + size + radius; yy++) for (int xx = x - radius; xx < x + size + radius; xx++) {
        if (xx < 0 || yy < 0 || xx >= g_w || yy >= g_h) continue;
        if (map_terrain_get(map_grid_offset(xx, yy)) & mask) return 1;
    }
    return 0;
}

static int footprint_free(int x, int y, int size)
{
    if (x + size > g_w || y + size > g_h) return 0;
    for (int yy = y; yy < y + size; yy++) for (int xx = x; xx < x + size; xx++) {
        int g = map_grid_offset(xx, yy);
        if (site_used[g] || (map_terrain_get(g) & SITE_BLOCK)) return 0;
    }
    return 1;
}

static int is_water(int x, int y)
{
    if (x < 0 || y < 0 || x >= g_w || y >= g_h) return 0;
    return (map_terrain_get(map_grid_offset(x, y)) & TERRAIN_WATER) != 0;
}

/* kind: 0 meadow(3x3 r1) 1 rock(2x2 r1) 2 tree(2x2 r1) 3 clay(2x2 r3 water) 4 sand(2x2 r9 water) 5 wharf(2x2 shore) */
static int count_sites(int kind)
{
    memset(site_used, 0, sizeof(site_used));
    int count = 0;
    for (int y = 0; y < g_h; y++) for (int x = 0; x < g_w; x++) {
        int size = kind == 0 ? 3 : 2, ok = 0;
        if (kind == 5) {
            /* one full edge of the 2x2 square is water, the other edge is free land */
            int pairs[4][4] = { {0,0,1,0}, {0,1,1,1}, {0,0,0,1}, {1,0,1,1} };
            int land[4][4] = { {0,1,1,1}, {0,0,1,0}, {1,0,1,1}, {0,0,0,1} };
            for (int d = 0; d < 4 && !ok; d++) {
                int ax = x + pairs[d][0], ay = y + pairs[d][1], bx = x + pairs[d][2], by = y + pairs[d][3];
                int lx = x + land[d][0], ly = y + land[d][1], mx = x + land[d][2], my = y + land[d][3];
                if (!is_water(ax, ay) || !is_water(bx, by)) continue;
                if (lx >= g_w || mx >= g_w || ly >= g_h || my >= g_h) continue;
                int g1 = map_grid_offset(lx, ly), g2 = map_grid_offset(mx, my);
                if (site_used[g1] || site_used[g2] || (map_terrain_get(g1) & SITE_BLOCK) || (map_terrain_get(g2) & SITE_BLOCK)) continue;
                ok = 1;
            }
            if (ok) {
                for (int yy = y; yy < y + 2 && yy < g_h; yy++) for (int xx = x; xx < x + 2 && xx < g_w; xx++)
                    site_used[map_grid_offset(xx, yy)] = 1;
                count++;
            }
            continue;
        }
        if (!footprint_free(x, y, size)) continue;
        switch (kind) {
            case 0: ok = area_has(x, y, 3, 1, TERRAIN_MEADOW); break;
            case 1: ok = area_has(x, y, 2, 1, TERRAIN_ROCK); break;
            case 2: ok = area_has(x, y, 2, 1, TERRAIN_TREE | TERRAIN_SHRUB); break;
            case 3: ok = area_has(x, y, 2, 3, TERRAIN_WATER | TERRAIN_BEACH); break;
            case 4: ok = area_has(x, y, 2, 9, TERRAIN_WATER | TERRAIN_BEACH); break;
        }
        if (!ok) continue;
        for (int yy = y; yy < y + size; yy++) for (int xx = x; xx < x + size; xx++) site_used[map_grid_offset(xx, yy)] = 1;
        count++;
    }
    return count;
}

static void site_counts(void)
{
    g_w = scenario.map.width; g_h = scenario.map.height;
    printf("SITES farm=%d rock=%d timber=%d clay=%d sand=%d wharf=%d\n", count_sites(0), count_sites(1), count_sites(2),
        count_sites(3), count_sites(4), count_sites(5));
}
