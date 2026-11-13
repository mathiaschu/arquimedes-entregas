"""Carga de datos, grafo dirigido del plano y caminos mínimos.

Reglas de operacion.json:
- Recorrido: menor distancia dirigida; empate por menor tiempo.
- access=no no es transitable.
- tiempo_arista = ceil(distancia_m * 3.6 / velocidad_kmh), en segundos enteros por arista.
- oneway=yes: sólo del primer nodo al segundo; oneway=-1: sólo del segundo al primero.
"""
import csv
import heapq
import json
import math
import os
import xml.etree.ElementTree as ET


def hms(s):
    h, m, x = (int(p) for p in s.split(":"))
    return h * 3600 + m * 60 + x


def fmt(t):
    return f"{t // 3600:02d}:{t % 3600 // 60:02d}:{t % 60:02d}"


def cargar(dir_n2, dir_n1):
    """Lee los archivos del nivel 2 y el catálogo/padrón del nivel 1."""
    def j(d, f):
        with open(os.path.join(d, f), encoding="utf-8") as fh:
            return json.load(fh)

    datos = {
        "pedidos": j(dir_n2, "pedidos.json"),
        "flota": j(dir_n2, "flota.json"),
        "operacion": j(dir_n2, "operacion.json"),
        "catalogo": {c["producto"]: c for c in j(dir_n1, "catalogo.json")},
    }
    with open(os.path.join(dir_n1, "padron.csv"), encoding="utf-8") as fh:
        datos["padron"] = {(r["calle"], int(r["altura"]), int(r["nodo"])) for r in csv.DictReader(fh)}
    datos["grafo"] = leer_grafo(os.path.join(dir_n2, "siracusa.osm"), datos["operacion"]["velocidades_kmh"])
    return datos


def leer_grafo(ruta_osm, velocidades):
    """Devuelve {nodo: [(vecino, distancia_m, segundos)]} con las aristas transitables."""
    g = {}
    for way in ET.parse(ruta_osm).getroot().iter("way"):
        nds = [int(n.get("ref")) for n in way.iter("nd")]
        tags = {t.get("k"): t.get("v") for t in way.iter("tag")}
        if tags.get("access") == "no":
            continue
        d = int(tags["distancia_m"])
        seg = math.ceil(d * 3.6 / velocidades[tags["highway"]])
        oneway = tags.get("oneway", "no")
        for a, b in zip(nds, nds[1:]):
            if oneway in ("no", "yes"):
                g.setdefault(a, []).append((b, d, seg))
            if oneway in ("no", "-1"):
                g.setdefault(b, []).append((a, d, seg))
    return g


def dijkstra(g, origen):
    """Caminos mínimos desde origen con clave lexicográfica (distancia, tiempo)."""
    mejor = {origen: (0, 0)}
    cola = [(0, 0, origen)]
    while cola:
        d, t, u = heapq.heappop(cola)
        if (d, t) != mejor[u]:
            continue
        for v, dd, tt in g.get(u, ()):
            cand = (d + dd, t + tt)
            if v not in mejor or cand < mejor[v]:
                mejor[v] = cand
                heapq.heappush(cola, (cand[0], cand[1], v))
    return mejor


def matrices(g, nodos):
    """Distancia (m) y tiempo (s) entre cada par de nodos de la lista, sobre el camino mínimo."""
    n = len(nodos)
    D = [[0] * n for _ in range(n)]
    T = [[0] * n for _ in range(n)]
    for i, o in enumerate(nodos):
        m = dijkstra(g, o)
        for k, dst in enumerate(nodos):
            if dst not in m:
                raise ValueError(f"nodo {dst} inalcanzable desde {o}")
            D[i][k], T[i][k] = m[dst]
    return D, T


def carga(pedido, catalogo):
    kg = sum(catalogo[i["producto"]]["kg"] * i["cantidad"] for i in pedido["items"])
    m3 = sum(catalogo[i["producto"]]["m3"] * i["cantidad"] for i in pedido["items"])
    return kg, m3
