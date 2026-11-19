class Graph:
    def __init__(self, station, label):
        self.station = station
        self.label = label
        size = len(station)
        self.weight = [{} for _ in range(size)]
        self._order = [[] for _ in range(size)]
        self.adj = None
        self.nodes_at = {}
        for node, s in enumerate(station):
            self.nodes_at.setdefault(s, []).append(node)

    def add_edge(self, u, v, cost):
        if v not in self.weight[u]:
            self._order[u].append(v)
            self.weight[u][v] = cost
        elif cost < self.weight[u][v]:
            self.weight[u][v] = cost

    def finalize(self):
        self.adj = [[(v, self.weight[u][v]) for v in order] for u, order in enumerate(self._order)]
        return self


def station_graph(net):
    graph = Graph(list(range(len(net.names))), [None] * len(net.names))
    for u, v, _, km in net.links:
        graph.add_edge(u, v, km)
    return graph.finalize()


def line_graph(net, penalty=0.0):
    nodes = [(s, line) for s, lines in enumerate(net.lines) for line in lines]
    node_id = {key: i for i, key in enumerate(nodes)}
    graph = Graph([s for s, _ in nodes], [line for _, line in nodes])
    for u, v, line, km in net.links:
        graph.add_edge(node_id[(u, line)], node_id[(v, line)], km)
    for s, lines in enumerate(net.lines):
        for a in lines:
            for b in lines:
                if a != b:
                    graph.add_edge(node_id[(s, a)], node_id[(s, b)], penalty)
    return graph.finalize()
