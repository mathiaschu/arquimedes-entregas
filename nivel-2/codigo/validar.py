"""Chequea un rutas.json contra los datos, recalculando cada tramo sobre el mapa.

Uso:
    python3 validar.py --datos DIR_NIVEL2 --nivel1 DIR_NIVEL1 --rutas rutas.json

Controla: formato exacto, una fila por vehículo, cada pedido una sola vez, capacidad en kg
y m3, salida y regreso dentro del turno, que cada inicio sea alcanzable desde la parada
anterior (llegada <= inicio), descarga completa dentro de la franja, sin superposición y
regreso coherente. Imprime la distancia total con salidas y regresos.
"""
import argparse
import json

import red


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--datos", required=True)
    ap.add_argument("--nivel1", required=True)
    ap.add_argument("--rutas", required=True)
    a = ap.parse_args()
    d = red.cargar(a.datos, a.nivel1)
    with open(a.rutas, encoding="utf-8") as fh:
        plan = json.load(fh)
    errores = []
    assert list(plan) == ["rutas"], "el objeto debe tener sólo la clave rutas"
    ped = {p["pedido"]: p for p in d["pedidos"]}
    flota = {v["vehiculo"]: v for v in d["flota"]}
    dep = d["operacion"]["deposito"]
    cache = {}

    def tramo(o, x):
        if o not in cache:
            cache[o] = red.dijkstra(d["grafo"], o)
        return cache[o][x]

    vistos, total = [], 0
    assert sorted(r["vehiculo"] for r in plan["rutas"]) == sorted(flota), "una fila por vehículo"
    for r in plan["rutas"]:
        assert set(r) == {"vehiculo", "salida", "paradas", "regreso"}, r.keys()
        v = flota[r["vehiculo"]]
        t = red.hms(r["salida"])
        if t < red.hms(v["desde"]):
            errores.append(f"{r['vehiculo']} sale antes del turno")
        nodo, kg, m3 = dep, 0, 0
        for st in r["paradas"]:
            assert set(st) == {"pedido", "inicio"}
            p = ped[st["pedido"]]
            vistos.append(st["pedido"])
            dd, tt = tramo(nodo, p["direccion"]["nodo"])
            total += dd
            ini = red.hms(st["inicio"])
            if ini < t + tt:
                errores.append(f"{st['pedido']}: inicio {st['inicio']} antes de la llegada {red.fmt(t + tt)}")
            if ini < red.hms(p["franja"]["desde"]) or ini + p["descarga_segundos"] > red.hms(p["franja"]["hasta"]):
                errores.append(f"{st['pedido']}: descarga fuera de franja")
            t = ini + p["descarga_segundos"]
            nodo = p["direccion"]["nodo"]
            k, m = red.carga(p, d["catalogo"])
            kg += k
            m3 += m
        dd, tt = tramo(nodo, dep)
        total += dd
        if red.hms(r["regreso"]) != t + tt:
            errores.append(f"{r['vehiculo']}: regreso {r['regreso']} != {red.fmt(t + tt)}")
        if t + tt > red.hms(v["hasta"]):
            errores.append(f"{r['vehiculo']}: vuelve después del turno")
        if kg > v["capacidad_kg"] + 1e-9 or m3 > v["capacidad_m3"] + 1e-9:
            errores.append(f"{r['vehiculo']}: excede capacidad ({kg:.2f} kg, {m3:.4f} m3)")
        print(f"{r['vehiculo']}: {len(r['paradas'])} paradas, {kg:.2f}/{v['capacidad_kg']} kg, "
              f"{m3:.3f}/{v['capacidad_m3']} m3, {r['salida']} a {r['regreso']}")
    if sorted(vistos) != sorted(ped):
        errores.append("faltan o se repiten pedidos")
    print(f"distancia total: {total} m ({total / 1000:.3f} km)")
    print("OK" if not errores else "\n".join(errores))


if __name__ == "__main__":
    main()
