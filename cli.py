import argparse
import random

from metrosearch.data import load_network
from metrosearch.graph import line_graph
from metrosearch.itinerary import describe
from metrosearch.multistop import (exact_tour, hill_climbing, leg_matrix,
                                   simulated_annealing, tour_cost)
from metrosearch.search import ALGORITHMS, a_star, solve


def route(args):
    net = load_network()
    graph = line_graph(net, args.penalty)
    src, dst = net.find(args.source), net.find(args.destination)
    names = list(ALGORITHMS) if args.compare else [args.algorithm]
    for name in names:
        res = solve(name, graph, net, src, dst)
        print(f"\n{name}: {net.names[src]} to {net.names[dst]}")
        for line in describe(res, graph, net):
            print("  " + line)
        print(f"  {res.km:.2f} km, {len(res.stations)} stations, {res.transfers} transfers, "
              f"{res.expanded} nodes expanded")


def trip(args):
    net = load_network()
    graph = line_graph(net, args.penalty)
    stops = [net.find(s) for s in args.stops]
    if len(set(stops)) != len(stops) or len(stops) < 3:
        raise SystemExit("Give at least three different stations; the first one is the starting point.")
    matrix = leg_matrix(graph, net, stops)
    rng = random.Random(args.seed)
    if args.method == "exact":
        order, cost = exact_tour(matrix, args.round_trip)
    elif args.method == "hill":
        order, cost, _ = hill_climbing(matrix, args.round_trip, args.restarts, rng)
    else:
        order, cost, _ = simulated_annealing(matrix, args.round_trip, args.steps, rng=rng)
    sequence = order + [0] if args.round_trip else order
    print(f"Method: {args.method}, total {tour_cost(order, matrix, args.round_trip):.2f} km")
    for a, b in zip(sequence, sequence[1:]):
        res = a_star(graph, net.straight[stops[b]], stops[a], stops[b])
        print(f"  {net.names[stops[a]]} -> {net.names[stops[b]]}: {res.km:.2f} km, {res.transfers} transfers")


def main():
    parser = argparse.ArgumentParser(description="Delhi Metro route search")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("route", help="route between two stations")
    p.add_argument("source")
    p.add_argument("destination")
    p.add_argument("--algorithm", choices=list(ALGORITHMS), default="A*")
    p.add_argument("--compare", action="store_true", help="run all three algorithms")
    p.add_argument("--penalty", type=float, default=1.0, help="transfer penalty in km-equivalent")
    p.set_defaults(func=route)
    q = sub.add_parser("trip", help="multi-stop trip; first station is the start")
    q.add_argument("stops", nargs="+")
    q.add_argument("--method", choices=["sa", "hill", "exact"], default="sa")
    q.add_argument("--round-trip", action="store_true")
    q.add_argument("--penalty", type=float, default=1.0)
    q.add_argument("--steps", type=int, default=2000)
    q.add_argument("--restarts", type=int, default=10)
    q.add_argument("--seed", type=int, default=0)
    q.set_defaults(func=trip)
    args = parser.parse_args()
    try:
        args.func(args)
    except KeyError as exc:
        raise SystemExit(exc.args[0])


if __name__ == "__main__":
    main()
