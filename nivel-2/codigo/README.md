# Nivel 2: código de ruteo

Python 3.10 o superior, sólo biblioteca estándar (sin paquetes para instalar).

| Archivo | Qué hace |
|---|---|
| `red.py` | Lee los datos, arma el grafo dirigido desde `siracusa.osm` y calcula caminos mínimos |
| `planificar.py` | Busca el plan de rutas y escribe `rutas.json` |
| `validar.py` | Recalcula cada tramo sobre el mapa y controla todas las condiciones del plan |

## Uso

`DIR_NIVEL2` es la carpeta con `pedidos.json`, `siracusa.osm`, `flota.json` y `operacion.json`. `DIR_NIVEL1` es la carpeta con `catalogo.json` y `padron.csv`.

```bash
python3 planificar.py --datos DIR_NIVEL2 --nivel1 DIR_NIVEL1 --salida ../rutas.json --segundos 240 --semilla 2
python3 validar.py --datos DIR_NIVEL2 --nivel1 DIR_NIVEL1 --rutas ../rutas.json
```

## Reglas aplicadas (de `operacion.json`)

- **Grafo:** cada `way` es una arista con `distancia_m`. `oneway=yes` se recorre del primer nodo al segundo, `oneway=-1` al revés y `no` en ambos sentidos. Las aristas con `access=no` se descartan.
- **Tiempo por arista:** `ceil(distancia_m * 3.6 / velocidad_kmh)` según `highway` (residential 24, tertiary 32, service 15), sumando segundos enteros.
- **Camino entre dos puntos:** Dijkstra con clave `(distancia, tiempo)`: menor distancia dirigida y, si empata, menor tiempo.
- **Carga:** kg y m³ de cada pedido según el catálogo (incluyen envases). Se controlan las dos capacidades del vehículo.
- **Horarios:** cada camioneta sale a la hora de inicio de su turno. Se puede esperar antes de descargar. La descarga entera (`inicio + descarga_segundos`) queda dentro de la franja del cliente, sin superponerse con otra, y el regreso al depósito (nodo 1026) es antes del fin del turno.
- **Viajes:** una salida por vehículo, sin recarga ni pedidos divididos. Se entregan los 80 pedidos.

## Método

1. Matrices de distancia y tiempo entre el depósito y los 80 domicilios.
2. Solución inicial por inserción, ordenando los pedidos por fin de franja.
3. Búsqueda de vecindad grande (LNS): en cada iteración se quitan de 4 a 20 pedidos (al azar, cercanos entre sí o un tramo de una ruta) y se reinsertan con inserción por arrepentimiento (regret-2). Se aceptan cambios con recocido simulado sobre la distancia total. Cada ruta candidata se valida completa antes de aceptarla.
4. Se guarda la mejor solución que entrega todos los pedidos.

Con 6 semillas de 240 s, cuatro convergieron al mismo valor, **62.694 m**, que es el plan entregado.
