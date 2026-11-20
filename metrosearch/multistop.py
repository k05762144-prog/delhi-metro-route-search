import math
import random

from .search import a_star


def leg_matrix(graph, net, stops):
    k = len(stops)
    matrix = [[0.0] * k for _ in range(k)]
    for i in range(k):
        for j in range(i + 1, k):
            res = a_star(graph, net.straight[stops[j]], stops[i], stops[j])
            matrix[i][j] = matrix[j][i] = res.cost
    return matrix


def tour_cost(order, matrix, round_trip=False):
    total = sum(matrix[a][b] for a, b in zip(order, order[1:]))
    if round_trip:
        total += matrix[order[-1]][order[0]]
    return total


def exact_tour(matrix, round_trip=False):
    k = len(matrix)
    inf = math.inf
    states = 1 << (k - 1)
    dp = [[inf] * (k - 1) for _ in range(states)]
    prev = [[-1] * (k - 1) for _ in range(states)]
    for j in range(k - 1):
        dp[1 << j][j] = matrix[0][j + 1]
    for mask in range(1, states):
        for j in range(k - 1):
            if not mask >> j & 1 or dp[mask][j] == inf:
                continue
            for t in range(k - 1):
                if mask >> t & 1:
                    continue
                nxt = mask | 1 << t
                cost = dp[mask][j] + matrix[j + 1][t + 1]
                if cost < dp[nxt][t]:
                    dp[nxt][t], prev[nxt][t] = cost, j
    full = states - 1
    last = min(
        range(k - 1),
        key=lambda j: dp[full][j] + (matrix[j + 1][0] if round_trip else 0.0),
    )
    best = dp[full][last] + (matrix[last + 1][0] if round_trip else 0.0)
    order, mask, j = [], full, last
    while j != -1:
        order.append(j + 1)
        mask, j = mask ^ (1 << j), prev[mask][j]
    order.append(0)
    order.reverse()
    return order, best


def _move(order, i, j, reverse):
    candidate = order[:]
    if reverse:
        candidate[i:j + 1] = reversed(candidate[i:j + 1])
    else:
        candidate[i], candidate[j] = candidate[j], candidate[i]
    return candidate


def hill_climbing(matrix, round_trip=False, restarts=10, rng=None, reversals=True):
    rng = rng or random.Random()
    k = len(matrix)
    best_order, best_cost, evaluations = None, math.inf, 0
    for _ in range(restarts):
        order = [0] + rng.sample(range(1, k), k - 1)
        cost = tour_cost(order, matrix, round_trip)
        evaluations += 1
        while True:
            best_move = None
            for i in range(1, k - 1):
                for j in range(i + 1, k):
                    for reverse in ((False, True) if reversals and j > i + 1 else (False,)):
                        candidate = _move(order, i, j, reverse)
                        value = tour_cost(candidate, matrix, round_trip)
                        evaluations += 1
                        if value < cost - 1e-12 and (best_move is None or value < best_move[0]):
                            best_move = (value, candidate)
            if best_move is None:
                break
            cost, order = best_move
        if cost < best_cost:
            best_order, best_cost = order[:], cost
    return best_order, best_cost, evaluations


def simulated_annealing(matrix, round_trip=False, steps=2000, t_start=None, t_end=None,
                        rng=None, reversals=True):
    rng = rng or random.Random()
    k = len(matrix)
    legs = [matrix[i][j] for i in range(k) for j in range(k) if i != j]
    scale = sum(legs) / len(legs)
    t_start = t_start if t_start is not None else 0.5 * scale
    t_end = t_end if t_end is not None else 0.005 * scale
    cooling = (t_end / t_start) ** (1.0 / steps)
    order = [0] + rng.sample(range(1, k), k - 1)
    cost = tour_cost(order, matrix, round_trip)
    best_order, best_cost = order[:], cost
    temperature = t_start
    for _ in range(steps):
        i, j = sorted(rng.sample(range(1, k), 2))
        reverse = reversals and j > i + 1 and rng.random() < 0.5
        candidate = _move(order, i, j, reverse)
        value = tour_cost(candidate, matrix, round_trip)
        delta = value - cost
        if delta <= 0 or rng.random() < math.exp(-delta / temperature):
            order, cost = candidate, value
            if cost < best_cost:
                best_order, best_cost = order[:], cost
        temperature *= cooling
    return best_order, best_cost, steps + 1
