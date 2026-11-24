# Sesión con Ari (paso S del cierre de la fase 4: Stop con una lectura)

Generado con `tools/analiza_sesion_a.py datos/corridas/S_2026-11-17`. Definiciones: `docs/INSTRUMENTACION_A2.md`, sección 5. Sin interpretación, salvo la conclusión de A3 que pide la orden.

| Parte | Estado | Inicio | Fin |
|---|---|---|---|
| A3 | hecha | 2026-11-17T23:13:45.266Z | 2026-11-17T23:16:40.482Z |

## Eventos de cajas por parte

Cuenta, dentro de cada parte, los eventos `caja_perdida`, `desvio_erroneo`, `caja_fantasma` y `caja_purgada` del cliente y los `paso_caja` con `rechazo_fallido` (cajas que un Stop alcanzó en el desviador). Solo se registran.

| Parte | Eventos |
|---|---|
| A3 | caja_fantasma: 5, caja_perdida (sin_confirmacion): 2, caja_purgada: 8, desvio_erroneo: 2, paso_caja con rechazo_fallido: 2 |

## A3. Start repetido

### Resultado 1. Pulsaciones vistas por el vigilante

| # | Presiona (UTC) | Botón | Duración (ms) | Inicios de ciclo de sondeo durante la pulsación | Evento `boton` en 0.5 s |
|---|---|---|---|---|---|
| 1 | 2026-11-17T23:14:25.549Z | start | 171 | 3 | sí |
| 2 | 2026-11-17T23:14:28.468Z | stop | 200 | 3 | sí |
| 3 | 2026-11-17T23:14:31.198Z | start | 198 | 4 | sí |
| 4 | 2026-11-17T23:14:34.884Z | stop | 171 | 3 | sí |
| 5 | 2026-11-17T23:14:38.814Z | start | 158 | 3 | sí |
| 6 | 2026-11-17T23:14:41.331Z | stop | 137 | 2 | sí |
| 7 | 2026-11-17T23:14:43.753Z | start | 157 | 3 | sí |
| 8 | 2026-11-17T23:14:46.237Z | stop | 139 | 3 | sí |
| 9 | 2026-11-17T23:14:49.278Z | start | 172 | 4 | sí |
| 10 | 2026-11-17T23:14:52.681Z | stop | 201 | 4 | sí |
| 11 | 2026-11-17T23:14:55.298Z | start | 132 | 3 | sí |
| 12 | 2026-11-17T23:14:59.377Z | stop | 242 | 4 | sí |
| 13 | 2026-11-17T23:15:01.244Z | start | 136 | 3 | sí |
| 14 | 2026-11-17T23:15:03.530Z | stop | 101 | 2 | sí |
| 15 | 2026-11-17T23:15:05.851Z | start | 122 | 3 | sí |
| 16 | 2026-11-17T23:15:08.242Z | stop | 137 | 2 | sí |
| 17 | 2026-11-17T23:15:11.033Z | start | 58 | 1 | sí |
| 18 | 2026-11-17T23:15:14.012Z | stop | 135 | 3 | sí |
| 19 | 2026-11-17T23:15:16.413Z | start | 115 | 3 | sí |
| 20 | 2026-11-17T23:15:20.402Z | stop | 174 | 4 | sí |
| 21 | 2026-11-17T23:15:27.414Z | start | 155 | 3 | sí |
| 22 | 2026-11-17T23:15:30.106Z | stop | 159 | 3 | sí |
| 23 | 2026-11-17T23:15:35.108Z | stop | 233 | 5 | sí |
| 24 | 2026-11-17T23:15:39.135Z | start | 133 | 2 | sí |
| 25 | 2026-11-17T23:15:42.108Z | stop | 259 | 5 | sí |
| 26 | 2026-11-17T23:15:48.084Z | stop | 156 | 3 | sí |
| 27 | 2026-11-17T23:15:54.469Z | start | 100 | 2 | sí |
| 28 | 2026-11-17T23:15:58.773Z | stop | 201 | 3 | sí |
| 29 | 2026-11-17T23:16:04.368Z | start | 154 | 3 | sí |
| 30 | 2026-11-17T23:16:07.653Z | stop | 170 | 3 | sí |
| 31 | 2026-11-17T23:16:12.085Z | start | 100 | 2 | **no** |
| 32 | 2026-11-17T23:16:13.409Z | start | 140 | 3 | sí |
| 33 | 2026-11-17T23:16:16.575Z | stop | 177 | 3 | sí |
| 34 | 2026-11-17T23:16:19.150Z | start | 161 | 3 | sí |
| 35 | 2026-11-17T23:16:22.993Z | stop | 193 | 4 | sí |
| 36 | 2026-11-17T23:16:26.593Z | start | 173 | 3 | sí |
| 37 | 2026-11-17T23:16:29.971Z | stop | 175 | 4 | sí |
| 38 | 2026-11-17T23:16:32.922Z | start | 122 | 3 | sí |
| 39 | 2026-11-17T23:16:37.910Z | stop | 181 | 4 | sí |
| 40 | 2026-11-17T23:16:40.150Z | start | 100 | 2 | sí |

Stop con al menos un ciclo de sondeo completo dentro de la pulsación (inicio y fin del ciclo entre presionar y soltar): 20, de ellas 20 con evento `boton`. Stop sin ningún ciclo completo dentro: 0 (0 con evento).

Start por número de inicios de ciclo dentro de la pulsación:

| Inicios de ciclo dentro | Vistas | Registradas |
|---|---|---|
| 1 | 1 | 1 |
| 2 | 4 | 3 |
| 3 | 13 | 13 |
| 4 | 2 | 2 |

Stop por número de inicios de ciclo dentro de la pulsación:

| Inicios de ciclo dentro | Vistas | Registradas |
|---|---|---|
| 2 | 3 | 3 |
| 3 | 9 | 9 |
| 4 | 6 | 6 |
| 5 | 2 | 2 |

Pulsaciones por número de inicios de ciclo dentro de ellas:

| Inicios de ciclo dentro | Registradas | Sin evento |
|---|---|---|
| 1 | 1 | 0 |
| 2 | 6 | 1 |
| 3 | 22 | 0 |
| 4 | 8 | 0 |
| 5 | 2 | 0 |

### Resultado 2. Conteo

| | Vistas | Registradas |
|---|---|---|
| Start, esta sesión | 20 | 19 |
| Stop, esta sesión | 20 | 20 |
| Start, paso T (11 nov) | 3 | 2 |
| Start, total | 23 | 21 |

Fuente del paso T: datos/corridas/T_2026-11-11/prueba_fio.log: Start a los 41.9, 53.6 y 65.5 s; eventos del cliente con dos boton start.

### Resultado 3. Pulsaciones sin evento y ciclos de sondeo

start presionado 2026-11-17T23:16:12.085Z, 100 ms. Hueco que la cubre: ninguno.

| Inicio del ciclo | Duración (ms) | Comunicación |
|---|---|---|
| 2026-11-17T23:16:11.134Z | 3 | ok |
| 2026-11-17T23:16:11.185Z | 5 | ok |
| 2026-11-17T23:16:11.237Z | 3 | ok |
| 2026-11-17T23:16:11.263Z | 3 | ok |
| 2026-11-17T23:16:11.316Z | 2 | ok |
| 2026-11-17T23:16:11.366Z | 2 | ok |
| 2026-11-17T23:16:11.418Z | 5 | ok |
| 2026-11-17T23:16:11.470Z | 3 | ok |
| 2026-11-17T23:16:11.522Z | 3 | ok |
| 2026-11-17T23:16:11.574Z | 3 | ok |
| 2026-11-17T23:16:11.626Z | 6 | ok |
| 2026-11-17T23:16:11.678Z | 2 | ok |
| 2026-11-17T23:16:11.730Z | 3 | ok |
| 2026-11-17T23:16:11.782Z | 3 | ok |
| 2026-11-17T23:16:11.834Z | 6 | ok |
| 2026-11-17T23:16:11.885Z | 5 | ok |
| 2026-11-17T23:16:11.936Z | 3 | ok |
| 2026-11-17T23:16:11.963Z | 3 | ok |
| 2026-11-17T23:16:12.014Z | 3 | ok |
| 2026-11-17T23:16:12.066Z | 3 | ok |
| 2026-11-17T23:16:12.118Z | 3 | ok |
| 2026-11-17T23:16:12.169Z | 5 | ok |
| 2026-11-17T23:16:12.221Z | 3 | ok |
| 2026-11-17T23:16:12.273Z | 4 | ok |
| 2026-11-17T23:16:12.324Z | 3 | ok |
| 2026-11-17T23:16:12.375Z | 3 | ok |
| 2026-11-17T23:16:12.427Z | 2 | ok |
| 2026-11-17T23:16:12.478Z | 9 | ok |
| 2026-11-17T23:16:12.528Z | 3 | ok |
| 2026-11-17T23:16:12.580Z | 3 | ok |
| 2026-11-17T23:16:12.632Z | 4 | ok |
| 2026-11-17T23:16:12.684Z | 3 | ok |
| 2026-11-17T23:16:12.736Z | 3 | ok |
| 2026-11-17T23:16:12.788Z | 3 | ok |
| 2026-11-17T23:16:12.814Z | 2 | ok |
| 2026-11-17T23:16:12.869Z | 3 | ok |
| 2026-11-17T23:16:12.921Z | 4 | ok |
| 2026-11-17T23:16:12.973Z | 4 | ok |
| 2026-11-17T23:16:13.025Z | 7 | ok |
| 2026-11-17T23:16:13.077Z | 2 | ok |
| 2026-11-17T23:16:13.128Z | 3 | ok |
| 2026-11-17T23:16:13.180Z | 4 | ok |


### Resultado 4. Periodo de sondeo de toda la sesión

| n | Mediana (ms) | p95 (ms) | Máximo (ms) | Periodos ≥ 300 ms |
|---|---|---|---|---|
| 3659 | 52 | 53 | 105 | 0 |

### Conclusión

DEFECTO DEL CLIENTE posible: 1 pulsacion(es) sin evento y sin hueco de sondeo que la cubra.
