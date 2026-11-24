# Corrida instrumentada de la Actividad 2 — ENSAYO

**Ensayo, no la corrida final.** 10 minutos con la escena del desviador contra el
SUSTITUTO, con A2-Nube escribiendo en `pruebas/simulador.py` en lugar de
Firebase (24 oct 2026). La corrida de C9 en `planta_01` espera la PUERTA ARI P1
(reglas publicadas) y la elección de planta (R1). Definiciones:
`docs/INSTRUMENTACION_A2.md`. Generado con `pruebas/prueba_instrumentacion_a2.py
--minutos 10` → `tools/exporta_corrida.py --rama proceso` →
`tools/analiza_corrida.py --a2`.

| Cifra | Definicion | n | Mediana | p95 | Max | Media ± sd |
|---|---|---|---|---|---|---|
| Periodo efectivo del sondeo | inicio_i − inicio_(i−1), com ok | 2458 | 242.0 ms | 268.0 ms | 282 ms | 250.0 ± 12.7 ms |
| Latencia lectura → Firebase | ts_escritura − ts_origen, cajas | 103 | 243.0 ms | 272.7 ms | 311.0 ms | 251.4 ± 16.3 ms |
| Completitud | cajas en Firebase / paso_caja | 103 / 103 | 100.00 % | | | |

Las tres cifras se reprodujeron por un segundo camino: el periodo efectivo con la
estadística en vivo de A2-Planta (250.0 ms), la latencia con el CSV de A2-Nube
(mediana 243.0 ms) y la completitud contra el registro del sustituto (103 cajas
salieron de la línea).
