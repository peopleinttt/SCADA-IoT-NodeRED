# Instrumentación de la Actividad 2

Definiciones fijadas el 24 de octubre de 2026, **antes de medir**. Las tres
cifras de C9 se calculan solo desde archivos (CSV y JSONL), con
`tools/analiza_corrida.py --a2`, y cualquiera puede reproducirlas desde ellos.

## Fuentes

| Archivo | Lo escribe | Una fila por |
|---|---|---|
| `$DATOS_DIR/a2_sondeo_AAAA-MM-DD.csv` | A2-Planta (`28_planta_lectura.js`) | ciclo de sondeo terminado: `ciclo;t_inicio_ms;ts_inicio;duracion_ms;peticiones;com;saltados_acumulados` |
| `$DATOS_DIR/a2_planta_eventos.jsonl` | A2-Planta | evento; los que cuentan aquí son `paso_caja` (una caja que salió de la línea) |
| `proceso_*.csv` | `tools/exporta_corrida.py --rama proceso` | registro de la rama `/plantas/{plantaId}/proceso` en Firebase |
| `$DATOS_DIR/a2_nube_AAAA-MM-DD.csv` | A2-Nube (`34_nube_respuesta.js`) | intento de escritura, con su código (control cruzado del CSV exportado) |
| `$DATOS_DIR/a2_sustituto_eventos.jsonl` | el sustituto | evento de la planta simulada; solo existe contra el sustituto |

## 1. Periodo efectivo del sondeo y su variación

```
periodo_i = t_inicio_i − t_inicio_(i−1)      (ms, ciclos consecutivos, ambos con com = ok)
periodo efectivo = media(periodo_i)
variación        = desviación estándar de periodo_i, y además p95 − p50
```

- `t_inicio` es el instante en que A2-Planta manda la primera petición del
  ciclo (reloj de la Mac, `Date.now()`).
- Solo cuentan ciclos con número consecutivo: si un ciclo se salta (el anterior
  no terminó a tiempo), ese hueco aparece en `saltados_acumulados` y no se
  promedia como un periodo largo. Se reporta aparte.
- **Lo que no mide:** cada cuánto cambia de verdad la escena. Eso es el
  refresco (`sonda_modbus.py vigila`). Si la escena refresca más lento que el
  sondeo, el periodo efectivo de información es el refresco y no este número.

## 2. Latencia de la lectura a la escritura en Firebase

```
latencia_i = ts_escritura_i − ts_origen_i      (ms, solo registros de caja)
reporte: mediana, p95, máximo, media ± sd
```

- `ts_origen` es el instante de la lectura Modbus en Node-RED: la primera
  lectura que vio el flanco de salida de la caja (con el desviador, el sensor de
  confirmación; con el empujador, `sens_salida` o el límite frontal).
- `ts_escritura` lo pone A2-Nube justo antes del POST.
- Las dos marcas salen del **mismo reloj** (la Mac), así que no hay sesgo entre
  relojes como en la Actividad 1. Lo que la latencia incluye:
  1. el antirrebote: el cambio se confirma `lecturas_para_cambio − 1`
     periodos después de la primera lectura (con 2 lecturas, un periodo);
  2. el paso por los nodos de A2-Planta y A2-Nube;
  3. la cola del limitador de 2 escrituras por segundo.
- **No incluye** el viaje a Firebase (`rtt_firebase_ms` del CSV de A2-Nube lo
  mide aparte) ni el tiempo de la planta a la lectura (a lo más un periodo de
  sondeo más el refresco de la escena).
- Los latidos no cuentan: su `ts_origen` es la última lectura buena, no un
  evento.
- Ritmo de los latidos (E2, fase 3): con la línea en marcha, uno cada
  `A2_LATIDO_S` (60 s por omisión); con la línea fuera de marcha y el mismo
  `estado_linea` que el latido anterior, uno cada `A2_LATIDO_REPOSO_S` (900 s
  por omisión); un cambio de `estado_linea` produce un latido en el siguiente
  tic de 1 s. Las cifras de C9 no cambian: se midieron con la línea en marcha y
  solo sobre registros de caja.

## 3. Completitud de cajas

```
completitud = registros de caja en Firebase en la ventana / paso_caja de A2-Planta en la ventana
```

- La ventana se fija con `--desde` y `--hasta` sobre `ts_origen` (Firebase) y
  `ts_salida` (`paso_caja`), que son el mismo instante.
- Contra el sustituto se reporta además la **completitud contra la planta**:
  registros de caja / cajas que salieron de la línea según el sustituto. La
  primera mide la cadena A2-Planta → A2-Nube → Firebase; la segunda suma lo que
  A2-Planta no vio.
- Una caja rechazada por Firebase queda en `a2_nube_*.csv` con su código y no
  se reintenta, así que cuenta como faltante.

## 4. Corridas largas y distribución de masas (paso L, fase 3)

Definiciones escritas antes de las corridas L1 y L2 (11 nov 2026). Las
calcula `tools/analiza_masas.py`; el resultado va a `docs/corrida_L.md`, con
tablas y sin interpretación.

**Fuentes por corrida.** Los eventos de A2-Planta (`a2_planta_eventos.jsonl`),
el archivo del oráculo de `prueba_fio.py cliente` (`oraculo.json`) y los de la
capa de materiales (`a2_materiales_medido.jsonl`, `a2_materiales_verdad.jsonl`,
`a2_materiales_estado.json`). Para los datos del 25 oct solo hay eventos.

- **Caja**: un evento `paso_caja` de A2-Planta. Su **peso** es `peso_V`, el
  valor en volts que el cliente usó para clasificar (lectura cruda del
  registro `weight` / 100).
- **Niveles**: 1.5, 2.5, 3.5, 4.0, 5.0, 7.5 y 10.0 V. Una caja **cae en un
  nivel** si |peso − nivel| ≤ 0.03 V (comparación redondeada a 6 decimales
  para no depender del error de coma flotante). Si no cae en ninguno, es una
  **lectura fuera de nivel**.
- **Histograma**: cajas por intervalo de 0.5 V, [0, 0.5), [0.5, 1.0), …,
  [10.0, 10.5).
- **Emparejamiento cliente–oráculo**: la caja i del cliente (i-ésimo
  `paso_caja`) con la suelta i del oráculo (i-ésimo elemento de `esperado`),
  el mismo orden FIFO que ya usa `prueba_fio.py`. Del oráculo se toman el
  **peso al soltar** (última lectura del registro antes de que `load_scale`
  vuelva a 1), la **variación en los últimos 0.3 s** (máximo − mínimo de sus
  lecturas en los 0.3 s previos a la última) y el **máximo crudo**: el mayor
  valor entero del registro `weight` leído mientras `load_scale` estuvo
  apagada con la caja en `at_scale`, sin dividir entre 100. Ampliar el
  oráculo con el máximo crudo no cambia sus criterios ni sus comprobaciones.
- **Lecturas altas**: cajas con peso ≥ 8.0 V; se reporta cuántas quedan por
  debajo de 9.95 V y su fracción.
- **Saturación**: para cada caja con peso ≥ 9.0 V, el máximo crudo; se
  reporta cuántas llegan a 1000 (10.00 V) y cuántas lo rebasan.
- **Ventanas de 10 minutos**: desde el `ts_salida` de la primera caja de la
  corrida, intervalos semiabiertos de 600 s. Una ventana final con menos de
  600 s se incluye y se marca.
- **Homogeneidad**: prueba ji cuadrada de homogeneidad sobre la tabla de
  contingencia filas × categorías, con las siete categorías de nivel más
  "fuera de nivel". Dentro de una corrida, las filas son sus ventanas de 10
  min; entre corridas, las filas son las corridas completas. Se quitan las
  columnas con total cero (y las filas con total cero). Estadístico
  X² = Σ (O − E)² / E con E = total de fila × total de columna / gran total;
  grados de libertad (filas − 1)(columnas − 1); valor p = P(χ² ≥ X²), la
  función de supervivencia de la ji cuadrada calculada en la herramienta con
  la gamma incompleta regularizada (serie y fracción continua), sin
  bibliotecas, comprobada contra 11.24 con 2 grados → 0.0036, 3.841 con 1 →
  0.050 y 9.488 con 4 → 0.050. Se reporta también cuántas celdas tienen E < 5.
- **Cadencia**: cajas / minutos entre el primer y el último `ts_salida` de la
  corrida; y cajas por ventana de 10 min.
- **Materiales**: con `tools/materiales.py` (funciones `carga_config` y
  `recalcula`, configuración `config/materiales.json` sin cambios), D final
  por laminado (a) con los pesos crudos y (b) llevando cada lectura fuera de
  nivel al **nivel inmediato superior** (el menor nivel mayor que el peso; una
  lectura por encima de 10.0 V se deja igual). El **tiempo esperado para
  llegar a D = 0.5, 0.8 y 1.0** es una extrapolación lineal al ritmo medio de
  la corrida: t = D_objetivo / (D_final / duración), con la duración entre el
  primer y el último `ts_salida`; si D_final es 0 no hay estimación. (b) es
  solo un reporte de sensibilidad y no cambia el modelo.
- **Verificación de la herramienta**: sobre `datos/a2_planta_eventos.jsonl`
  entre 2026-10-25T01:00:00Z y 2026-10-25T03:00:00Z debe dar 429 cajas; por
  nivel 68, 63, 66, 63, 74, 44 y 5, con 46 fuera de nivel; y las lecturas ≥
  8.0 V 8.36, 8.37, 8.72, 9.4, 9.4, 9.53, 9.67, 9.77 y cinco de 10.0
  (`tools/analiza_masas.py --verifica`).

## 5. Sesión con Ari (paso A, fase 4)

Definiciones escritas antes de la sesión del 17 nov 2026. Fuentes: el
`DATOS_DIR` de la sesión (copiado a `datos/corridas/A_2026-11-17/`), con
`a2_planta_eventos.jsonl`, `a2_sondeo_<día>.csv` y `a2_nube_<día>.csv` del
cliente, y los archivos del vigilante (`vigilante.jsonl`, `conexiones.jsonl`,
`partes.jsonl`). Las calcula `tools/analiza_sesion_a.py`.

- **Vigilante**: el proceso de la prueba, separado de Node-RED, lee las
  entradas discretas del tablero (`start_button`, `stop_button`,
  `emergency_stop`) por su propia conexión Modbus cada ~15 ms y anota cada
  cambio con la hora UTC del reloj de la Mac (milisegundos).
- **Pulsación**: para Start (NA), del cambio 0→1 al cambio 1→0; para Stop y
  Emergency stop (NC), del cambio 1→0 al cambio 0→1. **Duración** = soltar −
  presionar.
- **Registrada**: hay un evento `boton` del cliente con ese botón cuyo `ts`
  cae entre el instante de presionar y 0.5 s después de presionar.
- **Ciclo de sondeo**: una fila del CSV de sondeo de A2-Planta (inicio,
  duración, estado de comunicación). **Periodo** = diferencia entre inicios
  consecutivos. Para una pulsación sin evento se listan los ciclos con inicio
  entre 1 s antes de presionar y 1 s después de soltar; hay **hueco que la
  cubre** si dos inicios consecutivos están separados por un tiempo mayor o
  igual a la duración de la pulsación y el intervalo entre ellos contiene la
  pulsación entera.
- **Distribución del periodo de sondeo** de toda la sesión: mediana, p95
  (percentil por rango más cercano), máximo y número de periodos ≥ 300 ms.
- **Conexión de la tailnet** (A1): una conexión TCP establecida al puerto de
  Node-RED cuya dirección remota está en 100.64.0.0/10 y es distinta de la IP
  de Tailscale de la Mac; se observa con `lsof -nP -iTCP:<puerto>
  -sTCP:ESTABLISHED` cada 2 s.
- **Retraso de un latido** (A2): `ts_escritura` del latido aceptado (HTTP 200)
  en `a2_nube_<día>.csv` menos el `ts` del evento `paro_de_emergencia` o
  `emergencia_liberada`; cuenta el primer latido con retraso entre 0 y 2 s.

## 6. Geometría de la línea y velocidad de banda (paso G, fase 4)

Definiciones escritas antes de la corrida G (17 nov 2026). Fuentes: la
carpeta `datos/corridas/G_<fecha>/` con los eventos y el CSV de sondeo del
cliente, el oráculo de `prueba_fio.py` y `flancos.jsonl` del registrador
(`pruebas/registra_flancos.py`: proceso separado del cliente, conexión Modbus
propia, lee cada ~10 ms las entradas discretas 0 a 8 y las bobinas
`entry_conveyor` y `load_scale`, y anota cada cambio con la hora UTC de la
Mac). Las calcula `tools/mide_linea.py`; resultado en `docs/corrida_G.md`.
Para cada tiempo: n, mediana, p5, p95 y máximo (percentiles por rango más
cercano).

**Tramos de los límites del cliente** (los mismos instantes que usa el
cliente al aplicar cada límite):

- **Confirmación** (`timeout_confirmacion_s`, `26_planta_config.js`; se aplica
  en `27_planta_ciclo.js`): de `caja_pesada` (el cliente decide la clase y
  suelta la caja; ahí fija `t_desvio`) al flanco de subida del sensor de
  confirmación de su rama (`at_left_entry`, `at_forward_entry` o
  `at_right_entry`), que es el `ts_salida` de su `paso_caja`. Límite =
  1.5 × `fin_bascula_a_confirmacion_m` / `velocidad_fija_m_s` + (N + 1) ×
  T_ef + rtt, con N = `lecturas_para_cambio`.
- **Llegada a fin de báscula** (`no_llego_a_fin_bascula`,
  `28_planta_lectura.js`): el reloj de una caja corre solo con la línea en
  marcha y sin otra caja en pesaje, desde que la caja nace (con pesaje
  detenido, el flanco de subida de `at_scale`) hasta que pasa a "desviando"
  (`caja_pesada`). Con pesaje detenido la caja misma queda "separando" desde
  que nace, así que su reloj no avanza. Se reporta el tiempo del flanco de
  `at_scale` al apagado de `entry_conveyor` (la parada de pesaje), que es lo
  más que ese reloj podría contar. Límite = 1.5 × `entrada_a_fin_bascula_m` /
  `velocidad_fija_m_s` + 3 × T_ef.

**Los cinco valores de `linea`:**

- **Distancias** (`entrada_a_fin_bascula_m` y `fin_bascula_a_confirmacion_m`):
  de las posiciones del archivo de escena, convertidas a metros solo con una
  escala que documente el manual de Factory I/O. Si el manual no la
  documenta, se reportan las posiciones en unidades de la escena y el valor
  sigue estimado.
- **Velocidad** (`velocidad_fija_m_s`): distancia entre dos sensores de una
  banda que la caja recorre sin detenerse (rama: `at_<rama>_entry` →
  `at_exit_<rama>`) entre la mediana del tiempo entre sus flancos (subida del
  de entrada a bajada del NC de salida). Sin escala documentada se reportan
  los tiempos y la velocidad sigue estimada.
- **Largo de caja** (`largo_caja_m`): duración del pulso de
  `at_<rama>_entry` (la caja lo cruza a velocidad constante) × velocidad, por
  tipo de pieza (nivel de peso del `paso_caja`). Sin velocidad medida se
  reportan las duraciones y el largo sigue estimado.
- **Intervalo de emisión** (`intervalo_emision_min_s`), tres fuentes: (a) el
  mínimo entre `caja_entra` consecutivos de esta corrida; (b) el mismo mínimo
  en L1, L2 y M1; (c) el emisor del archivo de escena (`MinTimeToEmit` y
  `MaxTimeToEmit`).

## 7. Tramos de recorrido con eventos del cliente (paso H, cierre de la fase 4)

Definiciones escritas antes de medir (17 nov 2026). Se miden con los eventos
de A2-Planta (`a2_planta_eventos.jsonl`), así que valen para todas las
corridas guardadas; las calcula `tools/mide_tramos.py` → `docs/corrida_H.md`.

- **Tramo de confirmación**: del `ts` del evento `caja_pesada` de una caja al
  `ts_salida` del `paso_caja` de la misma caja (`caja` igual). Es el tramo del
  límite `timeout_confirmacion_s`.
- **Tramo previo al pesaje**: del `ts_entrada` del evento `caja_entra` de una
  caja al `ts` del evento `escritura` que apaga `entry_conveyor`
  (`valor` falso) con `motivo` `pesaje` y la misma `caja`. Es el tramo del
  límite de las cajas que no llegan a la salida de la báscula.
- Corridas sin paros intermedios: L1, L2, M1, G e I (no A ni D, que tienen
  paros y una desconexión). Por corrida y en conjunto: n, mediana, p95
  (percentil por rango más cercano) y máximo.
- **Tiempo medido** de cada tramo: el máximo en esas cinco corridas.
- **Límite nuevo**: confirmación = 1.5 × tiempo medido + (N + 1) × T_ef + rtt
  + `comunicacion_timeout_ms`; previo al pesaje = 1.5 × tiempo medido + 3 ×
  T_ef + `comunicacion_timeout_ms`, con N = `lecturas_para_cambio`, T_ef y rtt
  los de `config/planta_fio.json`. **Margen** = límite − máximo observado.

## Cómo se calculan

```bash
python3 tools/exporta_corrida.py --rama proceso --desde <inicio> --hasta <fin> --salida datos/proceso_c9.csv
python3 tools/analiza_corrida.py --a2 datos/proceso_c9.csv \
    --sondeo datos/a2_sondeo_<dia>.csv --eventos datos/a2_planta_eventos.jsonl \
    --desde <inicio> --hasta <fin> --md docs/corrida_a2.md
```
