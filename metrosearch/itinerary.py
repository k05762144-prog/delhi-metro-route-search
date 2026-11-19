def segments(result, graph):
    out, current = [], None
    for a, b in zip(result.nodes, result.nodes[1:]):
        sa, sb = graph.station[a], graph.station[b]
        if sa == sb:
            continue
        line = graph.label[b]
        if current and current["line"] == line:
            current["to"] = sb
            current["stops"] += 1
            current["km"] += graph.weight[a][b]
        else:
            current = {"line": line, "from": sa, "to": sb, "stops": 1, "km": graph.weight[a][b]}
            out.append(current)
    return out


def describe(result, graph, net):
    lines = []
    for i, seg in enumerate(segments(result, graph)):
        if i:
            lines.append(f"  change at {net.names[seg['from']]}")
        name = seg["line"] or "Metro"
        lines.append(
            f"{name}: {net.names[seg['from']]} to {net.names[seg['to']]} "
            f"({seg['stops']} stops, {seg['km']:.2f} km)"
        )
    return lines
