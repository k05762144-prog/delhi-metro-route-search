import heapq
import random
import time

import pandas as pd

from .graph import line_graph
from .multistop import exact_tour, hill_climbing, leg_matrix, simulated_annealing
from .search import ALGORITHMS, a_star, reference

NAMES = list(ALGORITHMS)


def benchmark(graph, net):
    size = len(net.names)
    rows = []
    for s in range(size):
        for t in range(s + 1, size):
            h = net.straight[t]
            ref = reference(graph, h, s, t)
            row = {"src": s, "dst": t, "straight_km": net.straight[s][t],
                   "optimal_km": ref.cost, "ref_expanded": ref.expanded}
            for name, fn in ALGORITHMS.items():
                start = time.perf_counter()
                res = fn(graph, h, s, t)
                elapsed = (time.perf_counter() - start) * 1000
                row[f"{name}|cost"] = res.cost
                row[f"{name}|hops"] = len(res.stations) - 1
                row[f"{name}|expanded"] = res.expanded
                row[f"{name}|peak"] = res.peak_frontier
                row[f"{name}|ms"] = elapsed
                row[f"{name}|optimal"] = res.cost <= ref.cost + 1e-9
            rows.append(row)
    return pd.DataFrame(rows)


def summarise(df):
    positive = df[df["optimal_km"] > 0]
    out = []
    for name in NAMES:
        out.append({
            "Algorithm": name,
            "Avg route length (km)": df[f"{name}|cost"].mean(),
            "Avg stations in route": df[f"{name}|hops"].mean() + 1,
            "Avg nodes expanded": df[f"{name}|expanded"].mean(),
            "Avg peak frontier": df[f"{name}|peak"].mean(),
            "Avg runtime (ms)": df[f"{name}|ms"].mean(),
            "Shortest route found (%)": 100 * df[f"{name}|optimal"].mean(),
            "Avg detour vs shortest (%)": 100 * (positive[f"{name}|cost"] / positive["optimal_km"] - 1).mean(),
        })
    return pd.DataFrame(out).set_index("Algorithm")


def by_distance(df):
    bins = [0, 5, 10, 20, 30, 1000]
    labels = ["0-5 km", "5-10 km", "10-20 km", "20-30 km", "30+ km"]
    banded = df.assign(band=pd.cut(df["straight_km"], bins=bins, labels=labels, right=False))
    grouped = banded.groupby("band", observed=True)
    table = grouped[[f"{n}|expanded" for n in NAMES]].mean()
    table.columns = NAMES
    table["pairs"] = grouped.size()
    return table


def worked_example(graph, net, src_name, dst_name):
    s, t = net.find(src_name), net.find(dst_name)
    h = net.straight[t]
    best, parent = {s: 0.0}, {s: None}
    heap, serial, rows = [(h[s], 0, 0.0, s)], 1, []
    while heap:
        f, _, g, u = heapq.heappop(heap)
        if g > best[u]:
            continue
        rows.append({"step": len(rows) + 1, "station": net.names[u], "g": g, "h": h[u], "f": f})
        if u == t:
            break
        for v, c in graph.adj[u]:
            if g + c < best.get(v, float("inf")):
                best[v], parent[v] = g + c, u
                heapq.heappush(heap, (g + c + h[v], serial, g + c, v))
                serial += 1
    summary = {}
    for name, fn in ALGORITHMS.items():
        res = fn(graph, h, s, t)
        summary[name] = {"expanded": res.expanded, "hops": len(res.stations) - 1, "km": res.km,
                         "route": [net.names[i] for i in res.stations]}
    return pd.DataFrame(rows), summary


def transfer_study(net, penalties=(0.0, 0.5, 1.0, 2.0, 4.0), pairs=1500, seed=11):
    rng = random.Random(seed)
    size = len(net.names)
    sample = []
    while len(sample) < pairs:
        s, t = rng.randrange(size), rng.randrange(size)
        if s != t:
            sample.append((s, t))
    baseline_routes = None
    rows = []
    for penalty in penalties:
        graph = line_graph(net, penalty)
        results = [a_star(graph, net.straight[t], s, t) for s, t in sample]
        routes = [tuple(r.stations) for r in results]
        if baseline_routes is None:
            baseline_routes = routes
        changed = sum(a != b for a, b in zip(routes, baseline_routes))
        rows.append({
            "penalty_km": penalty,
            "avg_transfers": sum(r.transfers for r in results) / pairs,
            "avg_distance_km": sum(r.km for r in results) / pairs,
            "avg_total_cost": sum(r.cost for r in results) / pairs,
            "avg_nodes_expanded": sum(r.expanded for r in results) / pairs,
            "routes_changed_pct": 100 * changed / pairs,
        })
    return pd.DataFrame(rows)


HC_RESTARTS = (1, 2, 5, 10, 20)
SA_STEPS = (250, 500, 1000, 2000, 4000)


def multistop_study(net, stops=10, instances=100, seed=5, round_trip=False, penalty=1.0):
    rng = random.Random(seed)
    graph = line_graph(net, penalty)
    size = len(net.names)
    rows = []
    for inst in range(instances):
        chosen = rng.sample(range(size), stops)
        matrix = leg_matrix(graph, net, chosen)
        _, optimum = exact_tour(matrix, round_trip)
        for reversals in (False, True):
            hood = "swap + reverse" if reversals else "swap only"
            runs = [("Hill climbing", r, lambda r=r: hill_climbing(
                        matrix, round_trip, r, random.Random(rng.random()), reversals)) for r in HC_RESTARTS]
            runs += [("Simulated annealing", n, lambda n=n: simulated_annealing(
                        matrix, round_trip, n, rng=random.Random(rng.random()), reversals=reversals))
                     for n in SA_STEPS]
            for method, setting, run in runs:
                start = time.perf_counter()
                _, cost, evaluations = run()
                rows.append({
                    "instance": inst, "method": method, "neighbourhood": hood, "setting": setting,
                    "cost": cost, "optimum": optimum, "gap_pct": max(0.0, 100 * (cost / optimum - 1)),
                    "found_optimum": cost <= optimum + 1e-9, "evaluations": evaluations,
                    "ms": (time.perf_counter() - start) * 1000,
                })
    return pd.DataFrame(rows)


def summarise_multistop(df):
    grouped = df.groupby(["method", "neighbourhood", "setting"], sort=False)
    return grouped.agg(
        avg_gap_pct=("gap_pct", "mean"),
        optimum_found_pct=("found_optimum", lambda s: 100 * s.mean()),
        avg_evaluations=("evaluations", "mean"),
        avg_ms=("ms", "mean"),
    ).reset_index()
