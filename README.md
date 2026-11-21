# Delhi Metro Route Search

Route planning on the Delhi Metro network, treated as a state-space search problem. The project compares three search algorithms, adds a transfer penalty to the cost model, and plans multi-stop trips with hill climbing and simulated annealing.

## What is in here

- **Route search.** Depth-first search (DFS), greedy best-first search and A* on a graph of 241 stations and 255 links across 10 lines. Edge cost is the straight-line distance between consecutive stations; the heuristic is the great-circle (Haversine) distance to the goal.
- **Transfer penalty.** A line-aware graph whose nodes are (station, line) pairs. Changing line adds a configurable penalty, so the search can trade distance against transfers.
- **Multi-stop trips.** Choose the order in which to visit several stations. Hill climbing (with random restarts) and simulated annealing are compared against an exact dynamic-programming solution.
- **Benchmarks, tests and a Streamlit demo.**

## Results

All numbers come from `python run_benchmark.py all` and are saved in `results/`.

### Algorithm comparison (every station pair, 28,920 queries)

| | DFS | Best-First | A* |
|---|---|---|---|
| Average route length (km) | 73.7 | 25.9 | 23.4 |
| Average nodes expanded | 132.7 | 24.5 | 42.7 |
| Shortest route found | 10.1% | 60.7% | 100% |
| Average detour vs shortest | +320.9% | +9.2% | 0% |

Dijkstra's algorithm is used only as a reference to check whether a route is the shortest; it expands 129.3 nodes on average, so A* expands about 67% fewer. Best-first search expands fewer nodes than A* but returns a longer route in about 39% of pairs. Runtimes are well under a millisecond per query on a graph this small, so nodes expanded is the more useful efficiency measure.

### Effect of the transfer penalty (1,500 random trips, A*)

| Penalty (km) | Avg transfers | Avg distance (km) | Routes changed vs no penalty |
|---|---|---|---|
| 0 | 1.58 | 23.44 | 0% |
| 0.5 | 1.52 | 23.45 | 4.4% |
| 1 | 1.48 | 23.49 | 7.4% |
| 2 | 1.41 | 23.58 | 11.1% |
| 4 | 1.29 | 23.90 | 20.7% |

### Multi-stop planning (100 random trips of 10 stations)

Both methods were run with two move sets: swap two stops only, and swap or reverse a segment. The optimum comes from an exact solver.

| Method | Moves | Tours evaluated | Optimal tour found | Average gap |
|---|---|---|---|---|
| Hill climbing, 5 restarts | swap + reverse | ~1,950 | 98% | 0.03% |
| Simulated annealing, 2000 steps | swap + reverse | ~2,000 | 94% | 0.19% |
| Hill climbing, 5 restarts | swap only | ~1,000 | 55% | 1.93% |
| Simulated annealing, 2000 steps | swap only | ~2,000 | 57% | 2.16% |

The move set mattered more than the choice of method. At these instance sizes hill climbing with restarts matched or beat simulated annealing at the same budget.

## Setup

```
pip install -r requirements.txt
```

The dataset is downloaded on first run and cached in `data/`.

## Usage

```
python cli.py route "Rithala" "Noida Electronic City" --compare --penalty 1.5
python cli.py trip "Rithala" "Kashmere Gate" "Hauz Khas" "Noida Electronic City" --method sa --round-trip
python run_benchmark.py all
streamlit run app.py
python -m pytest
```

`python run_benchmark.py` also accepts `baseline`, `transfers` or `multistop` to run one study. Station names are matched case-insensitively and partial names are accepted when unambiguous (for example `"Dwarka Sector - 21"`).

## Layout

```
metrosearch/
  data.py         dataset download, network construction, Haversine distance
  graph.py        station graph and line-aware graph
  search.py       DFS, best-first, A* and the Dijkstra reference
  itinerary.py    turns a route into line-by-line directions
  multistop.py    tour cost, exact solver, hill climbing, simulated annealing
  experiments.py  benchmark, transfer study and multi-stop study
  plots.py        charts
cli.py            command-line route and trip planner
run_benchmark.py  runs the studies and writes results/
app.py            Streamlit demo
tests/            pytest suite
results/          tables and charts from the last run
```

## How the searches work

All three share one loop: take a node off the frontier, stop if it is the goal, otherwise generate its neighbours and add them to the frontier. They differ in how the frontier is ordered.

- **DFS** uses a stack, so it keeps following the most recently discovered station and only backtracks at dead ends. It ignores cost.
- **Best-first** uses a priority queue ordered by h(n), the straight-line distance to the goal. It chases whatever looks closest and never revisits a station once reached.
- **A\*** orders the queue by f(n) = g(n) + h(n), where g is the cheapest known cost from the start. A cheaper way to a station replaces the old one. The goal test happens when a node is expanded, not when it is generated. Because h never overestimates and is consistent, the first goal expanded is on a shortest route.

The multi-stop planner builds a matrix of shortest costs between the chosen stations with A*, then searches over visiting orders.

## Data and limitations

- Station coordinates and links come from `station_network.json` in [bhoot1234567890/TERMINAL_DMRC](https://github.com/bhoot1234567890/TERMINAL_DMRC), which is derived from the Delhi Metro GTFS feed. It is downloaded at run time and not redistributed here; check the original repository for its terms.
- The Aqua Line is disconnected from the rest of the network in this dataset, so only the largest connected component (241 stations, 10 lines) is used.
- Distances are straight-line lengths between consecutive stations, not surveyed track lengths. Routes are therefore close to, but slightly shorter than, real track distance.
- The dataset has no travel times or timetables. The transfer penalty is a modelling parameter in kilometres, not a measured walking time.
- DFS results depend on the order in which neighbours are tried; the file order is used.
- The multi-stop study uses random 10-station trips; conclusions may not carry over to much larger ones.
