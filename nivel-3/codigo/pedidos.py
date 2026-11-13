"""Arma nivel-3/pedidos.json a partir de los mensajes del lote 3.

Uso:
    python3 pedidos.py --datos DIR_NIVEL3 --nivel1 DIR_NIVEL1 --salida ../pedidos.json

Los audios se transcribieron en local con Whisper (mlx-whisper, modelos large-v3 y
large-v3-turbo, idioma es; ver README). Las fotos se leyeron a mano. La tabla PEDIDOS
deja, para cada pedido, el estado final después de aplicar las correcciones posteriores
(M103 a M138) y la fuente de cada dato. El script controla que:
- haya exactamente un pedido por cliente de clientes.json, con su identificador;
- cada producto exista en el catálogo y sólo los fraccionables lleven fracciones;
- calle, altura y nodo sean una misma fila del padrón y del barrio del cliente;
- la franja quede dentro del horario de recepción (límites no dichos = 10:00 / 15:00).
"""
import argparse
import csv
import json
import os

REC_DESDE, REC_HASTA = "10:00:00", "15:00:00"

# pedido: (items, calle, altura, desde, hasta, fuente)
# desde/hasta None = límite no expresado por el cliente -> extremo del horario de recepción.
PEDIDOS = {
    "P3-001": ({"PAP-B5": 1, "HUE-M30": 2}, "Wendarpa", 3310, "10:00:00", "11:05:00", "nota-01"),
    "P3-002": ({"BAN-KG": 3, "RUC-AT": 4}, "Xiloria", 2110, "10:10:00", "11:30:00", "nota-02"),
    "P3-003": ({"BAT-B5": 2, "HUE-M30": 1}, "Yerralma", 2610, "10:05:00", "11:10:00", "nota-03; M103 batata 3 -> 2"),
    "P3-004": ({"ACEL-AT": 6, "HUE-D12": 0.5}, "Orvencia", 2810, "10:00:00", "11:40:00", "nota-04"),
    "P3-005": ({"PAP-B5": 1, "HUE-M30": 3}, "Yerralma", 2510, "10:04:00", "11:45:00", "nota-05 ('diez y cuatro')"),
    "P3-006": ({"BAN-KG": 3, "RUC-AT": 4}, "Quiranda", 3210, "10:00:00", "11:15:00", "nota-06"),
    "P3-007": ({"BAT-B5": 2, "HUE-M30": 1}, "Wendarpa", 2810, "10:10:00", "11:50:00", "nota-07"),
    "P3-008": ({"ACEL-AT": 6, "HUE-D12": 0.5}, "Valdoria", 3410, "10:05:00", "11:25:00", "nota-08; M108 domicilio 3510 -> 3410"),
    "P3-009": ({"PAP-B5": 1, "HUE-M30": 1}, "Wendarpa", 2310, "10:00:00", "11:55:00", "nota-09"),
    "P3-010": ({"BAN-KG": 3, "RUC-AT": 4}, "Rieluma", 2810, "10:15:00", "11:38:00", "nota-10"),
    "P3-011": ({"BAT-B5": 2, "HUE-M30": 1}, "Almunela", 2010, "10:00:00", "11:10:00", "nota-11"),
    "P3-012": ({"ACEL-AT": 6, "HUE-D12": 0.5}, "Rieluma", 3010, "10:10:00", "11:45:00", "nota-12; M112 franja 12-14 -> 10:10-11:45"),
    "P3-013": ({"PAP-B5": 1, "HUE-M30": 2}, "Zafralia", 1810, "10:05:00", "11:30:00", "nota-13"),
    "P3-014": ({"BAN-KG": 3, "RUC-AT": 4}, "Zafralia", 3010, "10:00:00", "11:50:00", "nota-14"),
    "P3-015": ({"BAT-B5": 2, "HUE-M30": 1}, "Serralvia", 2710, "10:15:00", "11:55:00", "nota-15"),
    "P3-016": ({"ACEL-AT": 6, "HUE-D12": 0.5}, "Rieluma", 3110, "10:00:00", "11:40:00", "nota-16"),
    "P3-017": ({"TOM-CJ": 2}, "Galdoria", 2610, "10:15:00", "14:00:00", "nota-17; M117 tomate 3 -> 2"),
    "P3-018": ({"TOM-CJ": 1, "PAP-B5": 4}, "Wendarpa", 2710, "10:30:00", "14:15:00", "nota-18"),
    "P3-019": ({"TOM-CJ": 1, "BAT-B5": 3, "PAP-B5": 1}, "Yerralma", 1910, "10:00:00", "14:40:00", "nota-19"),
    "P3-020": ({"PAP-B5": 8}, "Wendarpa", 3110, "10:20:00", "14:10:00", "nota-20"),
    "P3-021": ({"MAN-CJ": 1, "HUE-M30": 5, "PAP-B5": 2, "BAN-KG": 3}, "Quiranda", 1910, None, "12:00:00", "lista-01 ('antes del mediodía'); M021 banana 3 kg"),
    "P3-022": ({"TOM-CJ": 1, "PAP-B5": 3, "BAT-B5": 1}, "Xiloria", 2710, "10:15:00", "14:45:00", "lista-02; M022 papa 3 bolsas"),
    "P3-023": ({"TOM-CJ": 2}, "Zafralia", 2110, "12:00:00", None, "lista-03 ('después de las 12'); M123 zanahoria -> 2 cajones de tomate"),
    "P3-024": ({"PAP-B5": 6, "BAT-B5": 2}, "Umbralia", 3110, "10:10:00", "13:55:00", "lista-04"),
    "P3-025": ({"LEC-CJ": 2, "TOM-CJ": 1, "BAN-KG": 4}, "Orvencia", 2010, "10:30:00", "14:10:00", "lista-05; M025 banana 4 kg"),
    "P3-026": ({"TOM-CJ": 1, "PAP-B5": 2, "BAT-B5": 2}, "Serralvia", 2610, "10:00:00", "14:25:00", "lista-06; M026 batata 2 bolsas"),
    "P3-027": ({"TOM-CJ": 2}, "Valdoria", 2810, "10:20:00", "14:05:00", "M027; M127 tomate 3 -> 2"),
    "P3-028": ({"PAP-B5": 8}, "Wendarpa", 2010, "10:45:00", "14:50:00", "M028 (corrige 'diez menos cuarto' por 10:45)"),
    "P3-029": ({"PAP-B5": 8}, "Valdoria", 2610, "10:15:00", "14:00:00", "M029"),
    "P3-030": ({"PAP-B5": 8}, "Serralvia", 3110, "10:35:00", "14:35:00", "M030"),
    "P3-031": ({"PAP-B5": 7, "BAT-B5": 1}, "Wendarpa", 2710, "10:30:00", "14:15:00", "M031"),
    "P3-032": ({"PAP-B5": 8}, "Umbralia", 2010, "10:05:00", "14:55:00", "M032"),
    "P3-033": ({"TOM-CJ": 2}, "Wendarpa", 2210, "10:25:00", "14:20:00", "M033; M133 domicilio 2310 -> 2210"),
    "P3-034": ({"PAP-B5": 6, "BAT-B5": 2}, "Yerralma", 1910, "10:00:00", "14:40:00", "M034"),
    "P3-035": ({"TOM-CJ": 2}, "Rieluma", 2210, "10:15:00", "14:50:00", "M035"),
    "P3-036": ({"PAP-B5": 8}, "Wendarpa", 2510, "10:40:00", "14:10:00", "M036 ('Wenarpa')"),
    "P3-037": ({"PAP-B5": 5, "BAT-B5": 3}, "Xiloria", 2710, "10:15:00", "14:45:00", "M037"),
    "P3-038": ({"PAP-B5": 8}, "Wendarpa", 1810, "10:05:00", "14:35:00", "M038; M138 franja 12-14 -> 10:05-14:35"),
    "P3-039": ({"PAP-B5": 4, "BAT-B5": 4}, "Umbralia", 3110, "10:10:00", "13:55:00", "M039"),
    "P3-040": ({"PAP-B5": 3, "BAT-B5": 5}, "Serralvia", 2610, "10:00:00", "14:25:00", "M040 ('Serralbia')"),
}


def armar(dir_n3, dir_n1):
    with open(os.path.join(dir_n3, "clientes.json"), encoding="utf-8") as fh:
        clientes = json.load(fh)
    with open(os.path.join(dir_n1, "catalogo.json"), encoding="utf-8") as fh:
        catalogo = {c["producto"]: c for c in json.load(fh)}
    padron = {}
    with open(os.path.join(dir_n1, "padron.csv"), encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            padron.setdefault((r["calle"], int(r["altura"])), []).append((int(r["nodo"]), r["barrio"]))

    assert {c["pedido"] for c in clientes} == set(PEDIDOS), "pedidos distintos de clientes.json"
    filas = []
    for c in clientes:
        items, calle, altura, desde, hasta, _ = PEDIDOS[c["pedido"]]
        for prod, cant in items.items():
            assert prod in catalogo, prod
            assert cant > 0 and (catalogo[prod]["fraccionable"] or float(cant).is_integer()), (c["pedido"], prod)
        nodos = [n for n, b in padron.get((calle, altura), []) if b == c["barrio"]]
        assert len(nodos) == 1, (c["pedido"], calle, altura, padron.get((calle, altura)))
        desde, hasta = desde or REC_DESDE, hasta or REC_HASTA
        assert REC_DESDE <= desde < hasta <= REC_HASTA, c["pedido"]
        filas.append({
            "pedido": c["pedido"],
            "cliente": c["cliente"],
            "estado": "confirmado",
            "items": [{"producto": p, "cantidad": q} for p, q in items.items()],
            "direccion": {"calle": calle, "altura": altura, "nodo": nodos[0]},
            "franja": {"desde": desde, "hasta": hasta},
            "motivos": [],
        })
    return filas


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--datos", required=True)
    ap.add_argument("--nivel1", required=True)
    ap.add_argument("--salida", required=True)
    a = ap.parse_args()
    filas = armar(a.datos, a.nivel1)
    with open(a.salida, "w", encoding="utf-8") as fh:
        json.dump(filas, fh, ensure_ascii=False, indent=2)
    print(f"{len(filas)} pedidos")


if __name__ == "__main__":
    main()
