import difflib
import json
import math
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

DATA_URL = (
    "https://raw.githubusercontent.com/bhoot1234567890/"
    "TERMINAL_DMRC/main/station_network.json"
)
DEFAULT_PATH = Path(__file__).resolve().parent.parent / "data" / "station_network.json"
EARTH_RADIUS_KM = 6371.0088


def haversine(a, b):
    p1, p2 = math.radians(a[0]), math.radians(b[0])
    dp, dl = p2 - p1, math.radians(b[1] - a[1])
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(h))


@dataclass
class Network:
    names: list
    coords: list
    lines: list
    links: list
    straight: list
    index: dict = field(init=False)

    def __post_init__(self):
        self.index = {name: i for i, name in enumerate(self.names)}

    def find(self, text):
        key = text.strip().lower()
        for name, i in self.index.items():
            if name.lower() == key:
                return i
        hits = [i for i, name in enumerate(self.names) if key in name.lower()]
        if len(hits) == 1:
            return hits[0]
        pool = [self.names[i] for i in hits]
        if not pool:
            pool = difflib.get_close_matches(text, self.names, n=5, cutoff=0.5)
        hint = ", ".join(pool) if pool else "no close matches"
        raise KeyError(f"Station '{text}' not found or ambiguous. Candidates: {hint}")


def fetch_raw(path=DEFAULT_PATH):
    path = Path(path)
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with urllib.request.urlopen(DATA_URL, timeout=60) as resp:
                path.write_bytes(resp.read())
        except OSError as exc:
            raise RuntimeError(
                f"Could not download the dataset from {DATA_URL}. "
                f"Download it manually and save it as {path}."
            ) from exc
    return json.loads(path.read_text(encoding="utf-8"))


def _largest_component(stations, edges):
    comp, groups = {}, []
    for start in stations:
        if start in comp:
            continue
        stack, members = [start], []
        while stack:
            u = stack.pop()
            if u in comp:
                continue
            comp[u] = len(groups)
            members.append(u)
            stack += [e["to"] for e in edges[u]]
        groups.append(members)
    return set(max(groups, key=len))


def load_network(path=DEFAULT_PATH):
    raw = fetch_raw(path)
    stations, edges = raw["stations"], raw["edges"]
    keep = _largest_component(stations, edges)
    names = [n for n in stations if n in keep]
    index = {n: i for i, n in enumerate(names)}
    coords = [(stations[n]["coords"]["lat"], stations[n]["coords"]["lon"]) for n in names]
    lines = [sorted(stations[n]["line_codes"]) for n in names]
    links = []
    for n in names:
        for e in edges[n]:
            if e["to"] in index:
                u, v = index[n], index[e["to"]]
                links.append((u, v, e["line"], haversine(coords[u], coords[v])))
    count = len(names)
    straight = [[haversine(coords[i], coords[j]) for j in range(count)] for i in range(count)]
    return Network(names, coords, lines, links, straight)
