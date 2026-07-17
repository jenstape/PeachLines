import random
import networkx as nx
from collections import defaultdict


def make_seed_plan(G):
    return {node: int(G.nodes[node]['CD']) for node in G.nodes()}


def is_contiguous(nodes, G):
    subgraph = G.subgraph(nodes)
    return nx.is_connected(subgraph)


def population_deviation(plan, G):
    district_pop = defaultdict(int)
    for node, district in plan.items():
        district_pop[district] += int(G.nodes[node].get('TOTPOP', 0) or 0)
    total = sum(district_pop.values())
    ideal = total / len(district_pop)
    return max(abs(pop - ideal) / ideal * 100 for pop in district_pop.values())


def propose_step(plan, G, max_pop_deviation=5.0):
    cut = [(u, v) for u, v in G.edges() if plan[u] != plan[v]]
    if not cut:
        return None
    u, v = random.choice(cut)
    dist_a, dist_b = plan[u], plan[v]
    region_nodes = [n for n, d in plan.items() if d in (dist_a, dist_b)]
    subgraph = G.subgraph(region_nodes)
    spanning_tree = nx.minimum_spanning_tree(subgraph, algorithm='kruskal')
    for e in spanning_tree.edges():
        spanning_tree[e[0]][e[1]]['weight'] = random.random()
    spanning_tree = nx.minimum_spanning_tree(spanning_tree)
    tree_edges = list(spanning_tree.edges())
    random.shuffle(tree_edges)
    for edge in tree_edges:
        test_tree = spanning_tree.copy()
        test_tree.remove_edge(*edge)
        components = list(nx.connected_components(test_tree))
        if len(components) != 2:
            continue
        part_a, part_b = components
        if not is_contiguous(part_a, G) or not is_contiguous(part_b, G):
            continue
        new_plan = dict(plan)
        for node in part_a:
            new_plan[node] = dist_a
        for node in part_b:
            new_plan[node] = dist_b
        if population_deviation(new_plan, G) <= max_pop_deviation:
            return new_plan
    return None


def run_mcmc(G, steps=1000, save_every=100, max_pop_deviation=5.0,
             seed=None, progress_callback=None):
    if seed is not None:
        random.seed(seed)
    current_plan = make_seed_plan(G)
    plans = [current_plan]
    accepted = 0
    attempted = 0
    for step in range(steps):
        attempted += 1
        proposal = propose_step(current_plan, G, max_pop_deviation)
        if proposal is not None:
            current_plan = proposal
            accepted += 1
            if accepted % save_every == 0:
                plans.append(dict(current_plan))
        if progress_callback:
            progress_callback(step + 1, accepted, steps)
    stats = {
        'steps_attempted': attempted,
        'steps_accepted': accepted,
        'acceptance_rate': round(accepted / attempted * 100, 1) if attempted > 0 else 0,
        'plans_saved': len(plans),
    }
    return plans, stats
