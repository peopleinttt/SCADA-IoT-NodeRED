# Corrida instrumentada con la nube (paso I de la fase 4)

`pruebas/corrida_c9_real.py` del 17 nov 2026, ventana 2026-11-17T20:59:44.467Z a
2026-11-17T21:09:46.699Z, contra Factory I/O, escribiendo en `planta_01` de la base
real. Las tres cifras de `docs/INSTRUMENTACION_A2.md` con `tools/analiza_corrida.py --a2`,
las mismas definiciones que el 25 oct. Datos en `datos/corridas/I_2026-11-17/`. Sin
interpretación.

Registros escritos en la ventana: 132 `caja` y 11 `latido`.

## 17 de noviembre de 2026

| Cifra | Definicion | n | Mediana | p95 | Max | Media ± sd |
|---|---|---|---|---|---|---|
| Periodo efectivo del sondeo | inicio_i − inicio_(i−1), com ok | 12036 | 52.0 ms | 54.0 ms | 159 ms | 50.0 ± 7.8 ms |
| Latencia lectura → Firebase | ts_escritura − ts_origen, cajas | 132 | 53.0 ms | 57.0 ms | 60.0 ms | 50.8 ± 7.7 ms |
| Completitud | cajas en Firebase / paso_caja | 132 / 132 | 100.00 % | | | |

## 25 de octubre de 2026 (`docs/corrida_a2.md`, sin cambios)

| Cifra | Definicion | n | Mediana | p95 | Max | Media ± sd |
|---|---|---|---|---|---|---|
| Periodo efectivo del sondeo | inicio_i − inicio_(i−1), com ok | 11983 | 52.0 ms | 54.0 ms | 668 ms | 50.1 ± 9.6 ms |
| Latencia lectura → Firebase | ts_escritura − ts_origen, cajas | 127 | 52.0 ms | 55.0 ms | 57.0 ms | 49.7 ± 8.2 ms |
| Completitud | cajas en Firebase / paso_caja | 127 / 127 | 100.00 % | | | |
