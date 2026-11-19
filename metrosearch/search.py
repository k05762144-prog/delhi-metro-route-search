import heapq
import itertools
from dataclasses import dataclass


@dataclass
class Result:
    nodes: list
    stations: list
    cost: float
    km: float
    transfers: int
    expanded: int
    peak_frontier: int


def _result(graph, parent, goal, expanded, peak):
    nodes = []
    u = goal
    while u != -1:
        nodes.append(u)
        u = parent[u]
    nodes.reverse()
    km = transfer_cost = 0.0
    transfers = 0
    stations = [graph.station[nodes[0]]]
    for a, b in zip(nodes, nodes[1:]):
        w = graph.weight[a][b]
        if graph.station[a] == graph.station[b]:
            transfers += 1
            transfer_cost += w
        else:
            km += w
            stations.append(graph.station[b])
    return Result(nodes, stations, km + transfer_cost, km, transfers, expanded, peak)


def dfs(graph, h, src, dst):
    size = len(graph.adj)
    parent, explored = [-1] * size, [False] * size
    stack = [(s, -1) for s in reversed(graph.nodes_at[src])]
    expanded, peak = 0, len(stack)
    while stack:
        u, p = stack.pop()
        if explored[u]:
            continue
        explored[u], parent[u] = True, p
        expanded += 1
        if graph.station[u] == dst:
            return _result(graph, parent, u, expanded, peak)
        for v, _ in reversed(graph.adj[u]):
            if not explored[v]:
                stack.append((v, u))
        peak = max(peak, len(stack))
    return None


def best_first(graph, h, src, dst):
    size = len(graph.adj)
    parent, seen, closed = [-1] * size, [False] * size, [False] * size
    tie = itertools.count()
    heap = []
    for s in graph.nodes_at[src]:
        seen[s] = True
        heapq.heappush(heap, (h[src], next(tie), s))
    expanded, peak = 0, len(heap)
    while heap:
        _, _, u = heapq.heappop(heap)
        if closed[u]:
            continue
        closed[u] = True
        expanded += 1
        if graph.station[u] == dst:
            return _result(graph, parent, u, expanded, peak)
        for v, _ in graph.adj[u]:
            if not seen[v]:
                seen[v], parent[v] = True, u
                heapq.heappush(heap, (h[graph.station[v]], next(tie), v))
        peak = max(peak, len(heap))
    return None


def a_star(graph, h, src, dst, use_h=True):
    size = len(graph.adj)
    inf = float("inf")
    best, parent = [inf] * size, [-1] * size
    tie = itertools.count()
    heap = []
    for s in graph.nodes_at[src]:
        best[s] = 0.0
        heapq.heappush(heap, (h[src] if use_h else 0.0, next(tie), 0.0, s))
    expanded, peak = 0, len(heap)
    while heap:
        _, _, g, u = heapq.heappop(heap)
        if g > best[u]:
            continue
        expanded += 1
        # goal test at expansion, not at generation: keeps the first goal found optimal
        if graph.station[u] == dst:
            return _result(graph, parent, u, expanded, peak)
        for v, c in graph.adj[u]:
            ng = g + c
            if ng < best[v]:
                best[v], parent[v] = ng, u
                f = ng + (h[graph.station[v]] if use_h else 0.0)
                heapq.heappush(heap, (f, next(tie), ng, v))
        peak = max(peak, len(heap))
    return None


def reference(graph, h, src, dst):
    return a_star(graph, h, src, dst, use_h=False)


ALGORITHMS = {"DFS": dfs, "Best-First": best_first, "A*": a_star}


def solve(name, graph, net, src, dst):
    return ALGORITHMS[name](graph, net.straight[dst], src, dst)
