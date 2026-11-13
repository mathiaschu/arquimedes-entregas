"""Planifica las rutas del nivel 2 (VRP con ventanas horarias y capacidad).

Uso:
    python3 planificar.py --datos DIR_NIVEL2 --nivel1 DIR_NIVEL1 --salida rutas.json [--segundos 240] [--semilla 2]

Método:
1. Matrices de distancia y tiempo entre depósito y pedidos con red.py (caminos mínimos
   dirigidos, desempate por tiempo).
2. Solución inicial por inserción más barata (con orden por fin de franja).
3. Búsqueda de vecindad grande (LNS): se quitan entre 4 y 20 pedidos (al azar, por cercanía
   o de una misma ruta) y se reinsertan con inserción por arrepentimiento (regret-2). Se acepta
   con recocido simulado sobre la distancia total. Cada ruta candidata se valida completa:
   capacidad en kg y m3, salida desde la hora de inicio del vehículo, espera permitida antes
   de descargar, descarga entera dentro de la franja y regreso antes del fin del turno.
4. Se queda con la mejor solución que entrega los 80 pedidos.

Horarios del resultado: cada camioneta sale a su hora de inicio y cada descarga empieza lo
antes posible (llegada o apertura de la franja, lo que ocurra después).
"""
import argparse
import json
import math
import random
import time

import red

PEN = 10 ** 7  # penalidad por pedido sin asignar


class Problema:
    def __init__(self, datos):
        self.ped = datos["pedidos"]
        self.flota = datos["flota"]
        op = datos["operacion"]
        nodos = [op["deposito"]] + [p["direccion"]["nodo"] for p in self.ped]
        self.D, self.T = red.matrices(datos["grafo"], nodos)
        self.n = len(self.ped)
        # índice 0 = depósito; pedido i -> índice i+1
        self.a = [0] + [red.hms(p["franja"]["desde"]) for p in self.ped]
        self.b = [0] + [red.hms(p["franja"]["hasta"]) for p in self.ped]
        self.s = [0] + [p["descarga_segundos"] for p in self.ped]
        cargas = [red.carga(p, datos["catalogo"]) for p in self.ped]
        self.kg = [0] + [round(c[0], 4) for c in cargas]
        self.m3 = [0] + [round(c[1], 6) for c in cargas]
        self.v_ini = [red.hms(v["desde"]) for v in self.flota]
        self.v_fin = [red.hms(v["hasta"]) for v in self.flota]
        self.v_kg = [v["capacidad_kg"] for v in self.flota]
        self.v_m3 = [v["capacidad_m3"] for v in self.flota]

    def horario(self, v, ruta):
        """Devuelve (inicios, regreso) o None si la ruta es infactible para el vehículo v."""
        if sum(self.kg[i] for i in ruta) > self.v_kg[v] + 1e-9:
            return None
        if sum(self.m3[i] for i in ruta) > self.v_m3[v] + 1e-9:
            return None
        t, prev, ini = self.v_ini[v], 0, []
        for i in ruta:
            t = max(t + self.T[prev][i], self.a[i])
            if t + self.s[i] > self.b[i]:
                return None
            ini.append(t)
            t += self.s[i]
            prev = i
        t += self.T[prev][0]
        if t > self.v_fin[v]:
            return None
        return ini, t

    def dist(self, ruta):
        prev, d = 0, 0
        for i in ruta:
            d += self.D[prev][i]
            prev = i
        return d + self.D[prev][0]

    def costo(self, rutas, sueltos):
        return sum(self.dist(r) for r in rutas) + PEN * len(sueltos)


def mejores_inserciones(P, rutas, i):
    """Lista de (delta, v, pos) factibles para insertar el pedido i."""
    out = []
    for v, r in enumerate(rutas):
        base = P.dist(r)
        for pos in range(len(r) + 1):
            prev = r[pos - 1] if pos else 0
            nxt = r[pos] if pos < len(r) else 0
            delta = P.D[prev][i] + P.D[i][nxt] - P.D[prev][nxt]
            out.append((delta, v, pos))
    out.sort()
    res = []
    for delta, v, pos in out:
        nueva = rutas[v][:pos] + [i] + rutas[v][pos:]
        if P.horario(v, nueva) is not None:
            res.append((delta, v, pos))
            if len({x[1] for x in res}) >= 2 or len(res) >= 6:
                break
    return res


def reinsertar(P, rutas, sueltos, rng):
    """Inserción por arrepentimiento (regret-2) con algo de ruido."""
    sueltos = list(sueltos)
    while sueltos:
        mejor = None
        for i in sueltos:
            ops = mejores_inserciones(P, rutas, i)
            if not ops:
                continue
            d1 = ops[0][0]
            otra = next((o[0] for o in ops if o[1] != ops[0][1]), d1 + 5000)
            prioridad = (otra - d1) * (1 + 0.2 * rng.random()) - d1 * 0.01
            if mejor is None or prioridad > mejor[0]:
                mejor = (prioridad, i, ops[0])
        if mejor is None:
            break
        _, i, (_, v, pos) = mejor
        rutas[v].insert(pos, i)
        sueltos.remove(i)
    return sueltos


def quitar(P, rutas, rng):
    todos = [i for r in rutas for i in r]
    if not todos:
        return []
    k = rng.randint(4, min(20, len(todos)))
    modo = rng.random()
    if modo < 0.35:
        elegidos = rng.sample(todos, k)
    elif modo < 0.75:
        semilla = rng.choice(todos)
        elegidos = sorted(todos, key=lambda j: P.D[semilla][j] + P.D[j][semilla] + 0.3 * abs(P.a[j] - P.a[semilla]))[:k]
    else:
        r = rng.choice([r for r in rutas if r])
        ini = rng.randrange(len(r))
        elegidos = r[ini:ini + k]
    for r in rutas:
        r[:] = [j for j in r if j not in elegidos]
    return elegidos


def resolver(P, segundos, semilla):
    rng = random.Random(semilla)
    rutas = [[] for _ in P.flota]
    orden = sorted(range(1, P.n + 1), key=lambda i: P.b[i])
    sueltos = reinsertar(P, rutas, orden, rng)
    actual = (P.costo(rutas, sueltos), [r[:] for r in rutas], list(sueltos))
    mejor = actual
    temp0 = 300.0
    t0 = time.time()
    it = 0
    while time.time() - t0 < segundos:
        it += 1
        rutas = [r[:] for r in actual[1]]
        quitados = quitar(P, rutas, rng) + actual[2]
        rng.shuffle(quitados)
        sueltos = reinsertar(P, rutas, quitados, rng)
        c = P.costo(rutas, sueltos)
        frac = (time.time() - t0) / segundos
        temp = temp0 * (1 - frac) + 1
        if c < actual[0] or rng.random() < math.exp(-(c - actual[0]) / temp):
            actual = (c, rutas, sueltos)
            if c < mejor[0]:
                mejor = (c, [r[:] for r in rutas], list(sueltos))
    return mejor, it


def a_json(P, rutas):
    filas = []
    for v, r in enumerate(rutas):
        ini, reg = P.horario(v, r)
        filas.append({
            "vehiculo": P.flota[v]["vehiculo"],
            "salida": red.fmt(P.v_ini[v]),
            "paradas": [{"pedido": P.ped[i - 1]["pedido"], "inicio": red.fmt(t)} for i, t in zip(r, ini)],
            "regreso": red.fmt(reg),
        })
    return {"rutas": filas}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--datos", required=True)
    ap.add_argument("--nivel1", required=True)
    ap.add_argument("--salida", required=True)
    ap.add_argument("--segundos", type=float, default=240)
    ap.add_argument("--semilla", type=int, default=2)
    a = ap.parse_args()
    P = Problema(red.cargar(a.datos, a.nivel1))
    (costo, rutas, sueltos), it = resolver(P, a.segundos, a.semilla)
    if sueltos:
        raise SystemExit(f"quedaron {len(sueltos)} pedidos sin asignar")
    with open(a.salida, "w", encoding="utf-8") as fh:
        json.dump(a_json(P, rutas), fh, ensure_ascii=False, indent=2)
    print(f"distancia total {costo} m, {it} iteraciones, rutas: {[len(r) for r in rutas]}")


if __name__ == "__main__":
    main()
