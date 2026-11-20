from matplotlib.figure import Figure

COLORS = {"DFS": "#D7282F", "Best-First": "#F5B800", "A*": "#1565C0"}
METHOD_COLORS = {"Hill climbing": "#7B3FA0", "Simulated annealing": "#2E9E4F"}
GREY = "#B0B7C3"


def _clean(ax):
    ax.spines[["top", "right"]].set_visible(False)


def bar_chart(series, title, ylabel, fmt="{:.1f}"):
    fig = Figure(figsize=(6, 4))
    ax = fig.subplots()
    bars = ax.bar(series.index, series.values, color=[COLORS[a] for a in series.index])
    for bar, value in zip(bars, series.values):
        ax.text(bar.get_x() + bar.get_width() / 2, value, fmt.format(value), ha="center", va="bottom")
    ax.set_title(title)
    ax.set_ylabel(ylabel)
    _clean(ax)
    fig.tight_layout()
    return fig


def effort_by_distance(table):
    fig = Figure(figsize=(7, 4))
    ax = fig.subplots()
    names = ["DFS", "Best-First", "A*"]
    width = 0.27
    for k, name in enumerate(names):
        ax.bar([i + (k - 1) * width for i in range(len(table))], table[name], width,
               label=name, color=COLORS[name])
    ax.set_xticks(range(len(table)))
    ax.set_xticklabels(table.index)
    ax.set_xlabel("Straight-line distance between source and destination")
    ax.set_ylabel("Average nodes expanded")
    ax.set_title("Search effort against trip length")
    ax.legend(frameon=False)
    _clean(ax)
    fig.tight_layout()
    return fig


def route_figure(net, routes, title=""):
    fig = Figure(figsize=(6, 6))
    ax = fig.subplots()
    ax.scatter([c[1] for c in net.coords], [c[0] for c in net.coords], s=6, color=GREY)
    for label, path in routes.items():
        colour = COLORS.get(label, "#1F2937")
        ax.plot([net.coords[i][1] for i in path], [net.coords[i][0] for i in path],
                color=colour, lw=2.2 if label == "A*" else 1.6, label=f"{label}: {len(path) - 1} hops")
    ax.set_title(title)
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    ax.legend(frameon=False)
    _clean(ax)
    fig.tight_layout()
    return fig


def tour_figure(net, legs, order_labels, title=""):
    fig = Figure(figsize=(6, 6))
    ax = fig.subplots()
    ax.scatter([c[1] for c in net.coords], [c[0] for c in net.coords], s=6, color=GREY)
    for path in legs:
        ax.plot([net.coords[i][1] for i in path], [net.coords[i][0] for i in path], color="#1565C0", lw=1.8)
    for label, station in order_labels:
        lat, lon = net.coords[station]
        ax.scatter([lon], [lat], s=36, color="#D7282F", zorder=3)
        ax.annotate(label, (lon, lat), textcoords="offset points", xytext=(5, 5), fontsize=9)
    ax.set_title(title)
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    _clean(ax)
    fig.tight_layout()
    return fig


def transfer_chart(df):
    fig = Figure(figsize=(9, 3.8))
    left, right = fig.subplots(1, 2)
    left.plot(df["penalty_km"], df["avg_transfers"], marker="o", color="#1565C0")
    left.set_xlabel("Transfer penalty (km-equivalent)")
    left.set_ylabel("Average transfers per route")
    left.set_title("Fewer transfers as the penalty grows")
    right.plot(df["penalty_km"], df["avg_distance_km"], marker="o", color="#D7282F")
    right.set_xlabel("Transfer penalty (km-equivalent)")
    right.set_ylabel("Average distance travelled (km)")
    right.set_title("Cost of avoiding transfers")
    for ax in (left, right):
        _clean(ax)
    fig.tight_layout()
    return fig


def multistop_chart(summary):
    fig = Figure(figsize=(7.5, 4.4))
    ax = fig.subplots()
    for (method, hood), group in summary.groupby(["method", "neighbourhood"], sort=False):
        ax.plot(group["avg_evaluations"], group["avg_gap_pct"], marker="o",
                color=METHOD_COLORS[method], linestyle="-" if hood == "swap + reverse" else "--",
                label=f"{method}, {hood}")
    ax.set_xscale("log")
    ax.set_xlabel("Tour evaluations per run (log scale)")
    ax.set_ylabel("Average gap to the optimal tour (%)")
    ax.set_title("Multi-stop planning: solution quality against effort")
    ax.legend(frameon=False)
    _clean(ax)
    fig.tight_layout()
    return fig
