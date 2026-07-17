import math
import networkx as nx


def population_deviation(plan, G):
    district_pop = {}
    for node, district in plan.items():
        pop = int(G.nodes[node].get('TOTPOP', 0) or 0)
        district_pop[district] = district_pop.get(district, 0) + pop
    total = sum(district_pop.values())
    ideal = total / len(district_pop)
    deviations = [abs(pop - ideal) / ideal * 100 for pop in district_pop.values()]
    return {
        'max_deviation_pct': round(max(deviations), 2),
        'mean_deviation_pct': round(sum(deviations) / len(deviations), 2),
        'ideal_population': round(ideal),
        'district_populations': district_pop,
    }


def polsby_popper(plan, gdf):
    gdf = gdf.copy()
    gdf['district'] = [plan.get(i, -1) for i in range(len(gdf))]
    scores = []
    for district_id, group in gdf.groupby('district'):
        if district_id == -1:
            continue
        dissolved = group.geometry.union_all()
        area = dissolved.area
        perimeter = dissolved.length
        if perimeter == 0:
            continue
        pp = (4 * math.pi * area) / (perimeter ** 2)
        scores.append((district_id, round(pp, 4)))
    scores_only = [s for _, s in scores]
    return {
        'mean_polsby_popper': round(sum(scores_only) / len(scores_only), 4),
        'min_polsby_popper': round(min(scores_only), 4),
        'max_polsby_popper': round(max(scores_only), 4),
        'per_district': {d: s for d, s in scores},
    }


def cut_edges(plan, G):
    cuts = sum(1 for u, v in G.edges() if plan.get(u) != plan.get(v))
    return {
        'cut_edges': cuts,
        'total_edges': G.number_of_edges(),
        'cut_pct': round(cuts / G.number_of_edges() * 100, 1),
    }


def efficiency_gap(plan, G):
    district_votes = {}
    for node, district in plan.items():
        d = int(G.nodes[node].get('PRES16D', 0) or 0)
        r = int(G.nodes[node].get('PRES16R', 0) or 0)
        if district not in district_votes:
            district_votes[district] = {'D': 0, 'R': 0}
        district_votes[district]['D'] += d
        district_votes[district]['R'] += r
    total_wasted_D = 0
    total_wasted_R = 0
    total_votes = 0
    for dist, votes in district_votes.items():
        d, r = votes['D'], votes['R']
        total = d + r
        total_votes += total
        threshold = total / 2
        if d > r:
            total_wasted_D += d - threshold
            total_wasted_R += r
        else:
            total_wasted_R += r - threshold
            total_wasted_D += d
    if total_votes == 0:
        return {'efficiency_gap': None, 'efficiency_gap_pct': None}
    gap = (total_wasted_R - total_wasted_D) / total_votes
    return {
        'efficiency_gap': round(gap, 4),
        'efficiency_gap_pct': round(gap * 100, 2),
        'interpretation': 'favors R' if gap > 0 else 'favors D',
    }


def vra_proxy(plan, G, bvap_threshold=0.35):
    district_vap = {}
    district_bvap = {}
    for node, district in plan.items():
        vap = int(G.nodes[node].get('VAP', 0) or 0)
        bvap = int(G.nodes[node].get('BVAP', 0) or 0)
        district_vap[district] = district_vap.get(district, 0) + vap
        district_bvap[district] = district_bvap.get(district, 0) + bvap
    opportunity_districts = []
    for district in district_vap:
        vap = district_vap[district]
        bvap = district_bvap[district]
        if vap > 0 and (bvap / vap) >= bvap_threshold:
            opportunity_districts.append({
                'district': district,
                'bvap_pct': round(bvap / vap * 100, 1),
            })
    return {
        'opportunity_districts': len(opportunity_districts),
        'threshold_used': bvap_threshold,
        'districts': sorted(opportunity_districts, key=lambda x: -x['bvap_pct']),
    }


def score_plan(plan, G, gdf):
    return {
        'population':  population_deviation(plan, G),
        'compactness': polsby_popper(plan, gdf),
        'cut_edges':   cut_edges(plan, G),
        'partisan':    efficiency_gap(plan, G),
        'vra':         vra_proxy(plan, G),
    }
