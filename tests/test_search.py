import itertools
import random

import pytest

from metrosearch.data import load_network
from metrosearch.graph import line_graph, station_graph
from metrosearch.multistop import (exact_tour, hill_climbing, leg_matrix,
                                   simulated_annealing, tour_cost)
from metrosearch.search import a_star, best_first, dfs, reference


@pytest.fixture(scope="module")
def net():
    return load_network()


@pytest.fixture(scope="module")
def graph(net):
    return station_graph(net)


def sample_pairs(net, count=150, seed=3):
    rng = random.Random(seed)
    size = len(net.names)
    pairs = []
    while len(pairs) < count:
        s, t = rng.randrange(size), rng.randrange(size)
        if s != t:
            pairs.append((s, t))
    return pairs


def test_network_size(net):
    assert len(net.names) == 241
    assert len(net.links) == 512


def test_every_link_is_symmetric(net):
    pairs = {(u, v) for u, v, _, _ in net.links}
    assert all((v, u) in pairs for u, v in pairs)


def test_heuristic_is_consistent(net, graph):
    goal = net.find("Rajiv Chowk")
    h = net.straight[goal]
    for u, nbrs in enumerate(graph.adj):
        for v, cost in nbrs:
            assert h[u] <= cost + h[v] + 1e-9


def test_a_star_matches_reference(net, graph):
    for s, t in sample_pairs(net):
        h = net.straight[t]
        assert a_star(graph, h, s, t).cost == pytest.approx(reference(graph, h, s, t).cost)


def test_baselines_never_beat_a_star(net, graph):
    for s, t in sample_pairs(net, 80):
        h = net.straight[t]
        best = a_star(graph, h, s, t).cost
        assert dfs(graph, h, s, t).cost >= best - 1e-9
        assert best_first(graph, h, s, t).cost >= best - 1e-9


def test_all_algorithms_reach_the_goal(net, graph):
    s, t = net.find("Rithala"), net.find("Noida Electronic City")
    for fn in (dfs, best_first, a_star):
        res = fn(graph, net.straight[t], s, t)
        assert res.stations[0] == s and res.stations[-1] == t


def test_line_graph_without_penalty_matches_station_graph(net, graph):
    lg = line_graph(net, 0.0)
    for s, t in sample_pairs(net, 60):
        h = net.straight[t]
        assert a_star(lg, h, s, t).cost == pytest.approx(a_star(graph, h, s, t).cost)


def test_penalty_never_lowers_cost_and_reduces_transfers(net):
    pairs = sample_pairs(net, 60)
    free, costly = line_graph(net, 0.0), line_graph(net, 5.0)
    transfers_free = transfers_costly = 0
    for s, t in pairs:
        h = net.straight[t]
        a, b = a_star(free, h, s, t), a_star(costly, h, s, t)
        assert b.cost >= a.cost - 1e-9
        transfers_free += a.transfers
        transfers_costly += b.transfers
    assert transfers_costly <= transfers_free


def test_transfers_are_counted(net):
    lg = line_graph(net, 1.0)
    s, t = net.find("Rithala"), net.find("Noida Electronic City")
    assert a_star(lg, net.straight[t], s, t).transfers >= 2


def small_matrix(net, size=7, seed=1):
    rng = random.Random(seed)
    stops = rng.sample(range(len(net.names)), size)
    return leg_matrix(line_graph(net, 1.0), net, stops)


@pytest.mark.parametrize("round_trip", [False, True])
def test_exact_tour_matches_brute_force(net, round_trip):
    matrix = small_matrix(net)
    brute = min(tour_cost([0, *p], matrix, round_trip)
                for p in itertools.permutations(range(1, len(matrix))))
    assert exact_tour(matrix, round_trip)[1] == pytest.approx(brute)


def test_heuristic_searches_do_not_beat_exact(net):
    matrix = small_matrix(net, 8, 2)
    optimum = exact_tour(matrix)[1]
    _, hc, _ = hill_climbing(matrix, restarts=5, rng=random.Random(0))
    _, sa, _ = simulated_annealing(matrix, steps=1500, rng=random.Random(0))
    assert hc >= optimum - 1e-9 and sa >= optimum - 1e-9


def test_tour_keeps_the_start_first(net):
    matrix = small_matrix(net)
    order, _, _ = simulated_annealing(matrix, rng=random.Random(4))
    assert order[0] == 0 and sorted(order) == list(range(len(matrix)))
