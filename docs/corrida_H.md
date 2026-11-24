# Tramos de recorrido con eventos del cliente (paso H)

Generado con `tools/mide_tramos.py`. Definiciones: `docs/INSTRUMENTACION_A2.md`, sección 7. Sin interpretación.

## Tramo de confirmación: `caja_pesada` → `ts_salida` del `paso_caja`

| Corrida | n | Mediana (s) | p95 (s) | Máximo (s) |
|---|---|---|---|---|
| L1 | 601 | 1.292 | 1.559 | 1.619 |
| L2 | 601 | 1.294 | 1.566 | 1.629 |
| M1 | 601 | 1.290 | 1.555 | 1.757 |
| G | 151 | 1.296 | 1.567 | 1.745 |
| I | 132 | 1.294 | 1.584 | 1.711 |
| **conjunto** | 2086 | 1.292 | 1.562 | 1.757 |

## Tramo previo al pesaje: `ts_entrada` de `caja_entra` → escritura que apaga `entry_conveyor` por pesaje

| Corrida | n | Mediana (s) | p95 (s) | Máximo (s) |
|---|---|---|---|---|
| L1 | 601 | 0.055 | 0.061 | 0.074 |
| L2 | 601 | 0.055 | 0.060 | 0.069 |
| M1 | 601 | 0.054 | 0.058 | 0.063 |
| G | 151 | 0.055 | 0.061 | 0.261 |
| I | 132 | 0.055 | 0.059 | 0.061 |
| **conjunto** | 2086 | 0.055 | 0.060 | 0.261 |

## Tiempos medidos y límites

| Tramo | Tiempo medido (máximo, s) | Dónde | Límite nuevo (s) | Margen sobre el máximo (s) | Cajas por encima del límite |
|---|---|---|---|---|---|
| confirmación | 1.757 | M1 caja 293 | 4.806 | 3.049 | 0 |
| previo al pesaje | 0.261 | G caja 93 | 2.556 | 2.296 | 0 |

T_ef 55 ms (medido), rtt 0.005 s, comunicacion_timeout 2.000 s.
