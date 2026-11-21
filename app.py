import random
import time

import pandas as pd
import streamlit as st

from metrosearch.data import load_network
from metrosearch.graph import line_graph
from metrosearch.itinerary import describe
from metrosearch.multistop import (exact_tour, hill_climbing, leg_matrix,
                                   simulated_annealing, tour_cost)
from metrosearch.plots import route_figure, tour_figure
from metrosearch.search import ALGORITHMS, a_star, solve

st.set_page_config(page_title="Delhi Metro Route Search", layout="wide")


@st.cache_resource
def get_network():
    return load_network()


@st.cache_resource
def get_graph(penalty):
    return line_graph(get_network(), penalty)


net = get_network()
names = net.names


def default_index(label, fallback):
    try:
        return net.find(label)
    except KeyError:
        return fallback


st.title("Delhi Metro Route Search")
st.caption("Depth-first search, greedy best-first search and A* on the Delhi Metro network.")

with st.sidebar:
    st.header("Trip")
    source = st.selectbox("From", names, index=default_index("Rithala", 0))
    destination = st.selectbox("To", names, index=default_index("Noida Electronic City", 1))
    penalty = st.slider("Transfer penalty (km-equivalent)", 0.0, 5.0, 1.0, 0.5)
    st.caption("Each line change adds this many kilometres to the cost the search tries to minimise.")

graph = get_graph(penalty)
src, dst = net.find(source), net.find(destination)

tab_route, tab_compare, tab_trip = st.tabs(["Route", "Compare algorithms", "Multi-stop trip"])

with tab_route:
    algorithm = st.radio("Algorithm", list(ALGORITHMS), index=2, horizontal=True)
    if src == dst:
        st.info("Pick two different stations.")
    else:
        start = time.perf_counter()
        res = solve(algorithm, graph, net, src, dst)
        elapsed = (time.perf_counter() - start) * 1000
        cols = st.columns(5)
        cols[0].metric("Distance", f"{res.km:.2f} km")
        cols[1].metric("Stations", len(res.stations))
        cols[2].metric("Transfers", res.transfers)
        cols[3].metric("Nodes expanded", res.expanded)
        cols[4].metric("Runtime", f"{elapsed:.2f} ms")
        left, right = st.columns([1, 1])
        with left:
            st.subheader("Itinerary")
            for line in describe(res, graph, net):
                st.write(line)
        with right:
            st.pyplot(route_figure(net, {algorithm: res.stations}, f"{source} to {destination}"))

with tab_compare:
    if src == dst:
        st.info("Pick two different stations.")
    else:
        rows, routes = [], {}
        optimum = a_star(graph, net.straight[dst], src, dst).cost
        for name in ALGORITHMS:
            start = time.perf_counter()
            res = solve(name, graph, net, src, dst)
            elapsed = (time.perf_counter() - start) * 1000
            routes[name] = res.stations
            rows.append({
                "Algorithm": name,
                "Distance (km)": round(res.km, 2),
                "Transfers": res.transfers,
                "Stations": len(res.stations),
                "Nodes expanded": res.expanded,
                "Peak frontier": res.peak_frontier,
                "Runtime (ms)": round(elapsed, 3),
                "Shortest": "yes" if res.cost <= optimum + 1e-9 else "no",
            })
        table = pd.DataFrame(rows).set_index("Algorithm")
        left, right = st.columns([1, 1])
        with left:
            st.dataframe(table)
            st.bar_chart(table["Nodes expanded"])
        with right:
            st.pyplot(route_figure(net, routes, f"{source} to {destination}"))

with tab_trip:
    st.write("The starting point is the station chosen as From. Pick the stations to visit.")
    extras = st.multiselect("Stations to visit", [n for n in names if n != source],
                            default=[n for n in ("Kashmere Gate", "Hauz Khas", "Dwarka Sector - 21") if n in names and n != source],
                            max_selections=11)
    c1, c2, c3 = st.columns(3)
    method = c1.radio("Method", ["Simulated annealing", "Hill climbing", "Exact (dynamic programming)"])
    round_trip = c2.checkbox("Return to the start")
    seed = c3.number_input("Random seed", 0, 9999, 0)
    if len(extras) < 2:
        st.info("Choose at least two stations to visit.")
    else:
        stops = [src] + [net.find(n) for n in extras]
        matrix = leg_matrix(graph, net, stops)
        rng = random.Random(int(seed))
        if method == "Simulated annealing":
            steps = st.slider("Steps", 250, 8000, 2000, 250)
            order, cost, evaluations = simulated_annealing(matrix, round_trip, steps, rng=rng)
        elif method == "Hill climbing":
            restarts = st.slider("Restarts", 1, 30, 10)
            order, cost, evaluations = hill_climbing(matrix, round_trip, restarts, rng)
        else:
            order, cost = exact_tour(matrix, round_trip)
            evaluations = None
        sequence = order + [0] if round_trip else order
        legs, table = [], []
        for a, b in zip(sequence, sequence[1:]):
            res = a_star(graph, net.straight[stops[b]], stops[a], stops[b])
            legs.append(res.stations)
            table.append({"From": names[stops[a]], "To": names[stops[b]],
                          "Distance (km)": round(res.km, 2), "Transfers": res.transfers})
        left, right = st.columns([1, 1])
        with left:
            st.metric("Total distance", f"{sum(t['Distance (km)'] for t in table):.2f} km")
            if evaluations:
                st.caption(f"{evaluations} tours evaluated")
            st.dataframe(pd.DataFrame(table))
        with right:
            labels = [(str(i + 1), stops[o]) for i, o in enumerate(order)]
            st.pyplot(tour_figure(net, legs, labels, "Visiting order"))
