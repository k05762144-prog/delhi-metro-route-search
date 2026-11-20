import argparse
from pathlib import Path

import pandas as pd

from metrosearch import experiments as ex
from metrosearch import plots
from metrosearch.data import load_network
from metrosearch.graph import line_graph, station_graph

pd.set_option("display.float_format", lambda v: f"{v:,.3f}")
pd.set_option("display.width", 160)


def save(fig, path):
    fig.savefig(path, dpi=200)
    print(f"saved {path}")


def baseline(net, out):
    graph = station_graph(net)
    print(f"{len(net.names)} stations, {sum(len(a) for a in graph.adj) // 2} links")
    df = ex.benchmark(graph, net)
    print(f"{len(df):,} station pairs evaluated\n")
    summary = ex.summarise(df)
    print(summary.T, "\n")
    print(f"Dijkstra reference, avg nodes expanded: {df['ref_expanded'].mean():.1f}\n")
    bands = ex.by_distance(df)
    print(bands, "\n")
    raw = out / "raw"
    raw.mkdir(exist_ok=True)
    df.to_csv(raw / "all_pairs.csv", index=False)
    summary.to_csv(out / "baseline_summary.csv")
    bands.to_csv(out / "effort_by_distance.csv")
    save(plots.bar_chart(summary["Avg nodes expanded"], "Average nodes expanded", "Nodes expanded"),
         out / "chart_nodes_expanded.png")
    save(plots.bar_chart(summary["Avg route length (km)"], "Average route length", "km"),
         out / "chart_route_length.png")
    save(plots.bar_chart(summary["Shortest route found (%)"], "Routes that are the shortest (%)", "% of pairs"),
         out / "chart_shortest_share.png")
    save(plots.bar_chart(summary["Avg runtime (ms)"], "Average runtime per query", "ms", fmt="{:.3f}"),
         out / "chart_runtime.png")
    save(plots.effort_by_distance(bands), out / "chart_effort_by_distance.png")
    src, dst = "Rithala", "Noida Electronic City"
    s, t = net.find(src), net.find(dst)
    routes = {n: ex.ALGORITHMS[n](graph, net.straight[t], s, t).stations for n in ex.NAMES}
    save(plots.route_figure(net, routes, f"{net.names[s]} to {net.names[t]}"), out / "chart_route_map.png")
    trace, summ = ex.worked_example(graph, net, "Kanhaiya Nagar", "Shivaji Park")
    print("\nWorked example: Kanhaiya Nagar to Shivaji Park (A* trace)")
    print(trace.to_string(index=False))
    for name, info in summ.items():
        print(f"{name}: {info['expanded']} expansions, {info['hops']} hops, {info['km']:.2f} km")
    trace.to_csv(out / "worked_example_astar.csv", index=False)


def transfers(net, out, seed):
    df = ex.transfer_study(net, seed=seed)
    print(df.to_string(index=False), "\n")
    df.to_csv(out / "transfer_study.csv", index=False)
    save(plots.transfer_chart(df), out / "chart_transfers.png")


def multistop(net, out, seed):
    df = ex.multistop_study(net, seed=seed)
    summary = ex.summarise_multistop(df)
    print(summary.to_string(index=False), "\n")
    summary.to_csv(out / "multistop_study.csv", index=False)
    save(plots.multistop_chart(summary), out / "chart_multistop.png")


def main():
    parser = argparse.ArgumentParser(description="Run the benchmark studies")
    parser.add_argument("study", nargs="?", default="all",
                        choices=["baseline", "transfers", "multistop", "all"])
    parser.add_argument("--out", default="results")
    parser.add_argument("--seed", type=int, default=5)
    args = parser.parse_args()
    out = Path(args.out)
    out.mkdir(exist_ok=True)
    net = load_network()
    if args.study in ("baseline", "all"):
        baseline(net, out)
    if args.study in ("transfers", "all"):
        transfers(net, out, args.seed)
    if args.study in ("multistop", "all"):
        multistop(net, out, args.seed)


if __name__ == "__main__":
    main()
