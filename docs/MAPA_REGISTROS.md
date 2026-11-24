# Mapa de registros Modbus — Actividad 2

> **Generado** con `python3 tools/mapa_registros.py doc` desde los dos JSON de `config/`.
> No se edita a mano: se cambia el JSON y se regenera. `A2_MAPA` elige cuál usa Node-RED.

## 1. Sustituto (planta simulada de C2)

`config/mapa_registros_a2.json`. Estado: provisional: los nombres de las etiquetas de la escena se confirman despues.

Driver: Factory I/O, Modbus TCP/IP Server. Factor de escala 100: un valor flotante viaja multiplicado por 100.
Las direcciones son las del protocolo, contadas desde 0, igual que en Factory I/O.

| Tabla | Límite del driver |
|---|---|
| Entradas discretas (FC 02) | 256 (0 a 255) |
| Registros de entrada (FC 04) | 64 (0 a 63) |
| Bobinas (FC 01 / 05 / 15) | 256 (0 a 255) |
| Registros de retencion (FC 03 / 06 / 16) | 64 (0 a 63) |

### Entradas discretas (FC 02)

| Dirección | Etiqueta | Sentido | Tipo | Rango físico | Rango en el registro | Descripción |
|---|---|---|---|---|---|---|
| 0 | `sens_entrada` | lectura | bool |  | 0 / 1 | Caja a la entrada del tramo vigilado |
| 1 | `sens_bascula` | lectura | bool |  | 0 / 1 | Caja sobre la bascula |
| 2 | `sens_salida` | lectura | bool |  | 0 / 1 | Caja a la salida del tramo vigilado |
| 3 | `emp_lim_frontal` | lectura | bool |  | 0 / 1 | Empujador extendido |
| 4 | `emp_lim_trasero` | lectura | bool |  | 0 / 1 | Empujador retraido |

### Registros de entrada (FC 04)

| Dirección | Etiqueta | Sentido | Tipo | Rango físico | Rango en el registro | Descripción |
|---|---|---|---|---|---|---|
| 0 | `peso_V` | lectura | uint16 | 0 a 10 V | 0 a 1000 (× 100) | Peso en la bascula, 0 a 10 V |

### Bobinas (FC 01 / 05 / 15)

| Dirección | Etiqueta | Sentido | Tipo | Rango físico | Rango en el registro | Descripción |
|---|---|---|---|---|---|---|
| 0 | `emisor_on` | escritura | bool |  | 0 / 1 | Emisor de cajas habilitado |
| 1 | `alimentacion_on` | escritura | bool |  | 0 / 1 | Banda de alimentacion y bascula en marcha |
| 2 | `emp_extender` | escritura | bool |  | 0 / 1 | Extension del empujador de rechazo |
| 3 | `luz_alerta` | escritura | bool |  | 0 / 1 | Indicador de alerta |

### Registros de retencion (FC 03 / 06 / 16)

| Dirección | Etiqueta | Sentido | Tipo | Rango físico | Rango en el registro | Descripción |
|---|---|---|---|---|---|---|
| 0 | `vel_banda_V` | escritura | int16 | -10 a 10 V | -1000 a 1000 (× 100), negativos en complemento a dos | Velocidad del tramo vigilado, -10 a 10 V, en complemento a dos |

## 2. Factory I/O, escena Sorting by Weight

`config/mapa_registros_fio.json`. Estado: confirmado con la captura del driver (docs/capturas/driver_fio_parallels.png) y con vigila el 24 oct 2026, Factory I/O 2.5.10 en Parallels (10.211.55.3:502, Slave ID 1), escena Sorting by Weight. NC = normalmente cerrado: vale 1 sin caja o sin presionar, observado con vigila; Stop y Emergency stop confirmados al presionarlos el 11 nov 2026 (prueba_fio.py tablero, 9/9: bajan a 0 al presionar y vuelven a 1 al soltar). Bobinas 11 Reset y 12 Run agregadas por Ari el 24 oct (probadas por Modbus).

Driver: Factory I/O 2.5.10, Modbus TCP/IP Server (puerto 502, Slave ID 1, offsets 0). Factor de escala 100: un valor flotante viaja multiplicado por 100.
Las direcciones son las del protocolo, contadas desde 0, igual que en Factory I/O.

| Tabla | Límite del driver |
|---|---|
| Entradas discretas (FC 02) | 256 (0 a 255) |
| Registros de entrada (FC 04) | 64 (0 a 63) |
| Bobinas (FC 01 / 05 / 15) | 256 (0 a 255) |
| Registros de retencion (FC 03 / 06 / 16) | 64 (0 a 63) |

### Entradas discretas (FC 02)

| Dirección | Etiqueta | Sentido | Tipo | Rango físico | Rango en el registro | Descripción |
|---|---|---|---|---|---|---|
| 0 | `at_scale_entry` | lectura | bool |  | 0 / 1 | At scale entry: NC, baja a 0 cuando pasa una caja a la entrada de la bascula |
| 1 | `at_scale` | lectura | bool |  | 0 / 1 | At scale: caja sobre la bascula |
| 2 | `at_scale_exit` | lectura | bool |  | 0 / 1 | At scale exit: caja a la salida de la bascula |
| 3 | `at_left_entry` | lectura | bool |  | 0 / 1 | At left entry: caja entrando a la salida izquierda |
| 4 | `at_exit_left` | lectura | bool |  | 0 / 1 | At exit left: NC, baja a 0 cuando sale una caja por la izquierda |
| 5 | `at_forward_entry` | lectura | bool |  | 0 / 1 | At forward entry: caja entrando a la salida de frente |
| 6 | `at_exit_front` | lectura | bool |  | 0 / 1 | At exit front: NC, baja a 0 cuando sale una caja de frente |
| 7 | `at_right_entry` | lectura | bool |  | 0 / 1 | At right entry: caja entrando a la salida derecha |
| 8 | `at_exit_right` | lectura | bool |  | 0 / 1 | At exit right: NC, baja a 0 cuando sale una caja por la derecha |
| 9 | `start_button` | lectura | bool |  | 0 / 1 | Start: boton del tablero, 1 al presionar |
| 10 | `reset_button` | lectura | bool |  | 0 / 1 | Reset: boton del tablero |
| 11 | `stop_button` | lectura | bool |  | 0 / 1 | Stop: boton del tablero, NC (1 sin presionar, 0 presionado; confirmado al presionarlo el 11 nov 2026) |
| 12 | `auto_mode` | lectura | bool |  | 0 / 1 | Auto: selector del tablero |
| 13 | `fio_running` | lectura | bool |  | 0 / 1 | FACTORY I/O (Running): la simulacion esta en Play |
| 14 | `emergency_stop` | lectura | bool |  | 0 / 1 | Emergency stop: NC (1 sin presionar, 0 presionado; confirmado al presionarlo y sostenerlo el 11 nov 2026) |
| 15 | `manual_mode` | lectura | bool |  | 0 / 1 | Manual: selector del tablero |

### Registros de entrada (FC 04)

| Dirección | Etiqueta | Sentido | Tipo | Rango físico | Rango en el registro | Descripción |
|---|---|---|---|---|---|---|
| 0 | `weight` | lectura | uint16 | 0 a 10 V | 0 a 1000 (× 100) | Weight: peso de la bascula (float x 100), 0-10 V = 0-20 kg (configuracion 20 Kg Max., docs/EVIDENCIA_U0.md); se asienta ~0.8 s despues de detener la banda |

### Bobinas (FC 01 / 05 / 15)

| Dirección | Etiqueta | Sentido | Tipo | Rango físico | Rango en el registro | Descripción |
|---|---|---|---|---|---|---|
| 0 | `entry_conveyor` | escritura | bool |  | 0 / 1 | Entry conveyor: banda de entrada |
| 1 | `load_scale` | escritura | bool |  | 0 / 1 | Load scale: banda de la bascula |
| 2 | `send_left` | escritura | bool |  | 0 / 1 | Send left: ruedas del desviador a la izquierda |
| 3 | `left_conveyor` | escritura | bool |  | 0 / 1 | Left conveyor: banda de la salida izquierda |
| 4 | `send_right` | escritura | bool |  | 0 / 1 | Send right: ruedas del desviador a la derecha |
| 5 | `right_conveyor` | escritura | bool |  | 0 / 1 | Right conveyor: banda de la salida derecha |
| 6 | `send_forward` | escritura | bool |  | 0 / 1 | Send forward: ruedas del desviador de frente |
| 7 | `front_conveyor` | escritura | bool |  | 0 / 1 | Front conveyor: banda de la salida de frente |
| 8 | `start_light` | escritura | bool |  | 0 / 1 | Start light: luz del tablero |
| 9 | `reset_light` | escritura | bool |  | 0 / 1 | Reset light: luz del tablero |
| 10 | `stop_light` | escritura | bool |  | 0 / 1 | Stop light: luz del tablero |
| 11 | `fio_reset` | escritura | bool |  | 0 / 1 | FACTORY I/O (Reset): en 1 detiene y reinicia la escena (Running baja a 0); en 0 vuelve a correr |
| 12 | `fio_run` | escritura | bool |  | 0 / 1 | FACTORY I/O (Run): por nivel, 1 = la escena corre, 0 = se detiene (probado por Modbus el 24 oct) |

### Registros de retencion (FC 03 / 06 / 16)

| Dirección | Etiqueta | Sentido | Tipo | Rango físico | Rango en el registro | Descripción |
|---|---|---|---|---|---|---|
| 0 | `left_count` | escritura | uint16 | 0 a 65535 cajas | 0 a 65535 (× 1) | Left count: contador del tablero (entero, sin escala) |
| 1 | `forward_count` | escritura | uint16 | 0 a 65535 cajas | 0 a 65535 (× 1) | Forward count: contador del tablero (entero, sin escala) |
| 2 | `right_count` | escritura | uint16 | 0 a 65535 cajas | 0 a 65535 (× 1) | Right count: contador del tablero (entero, sin escala) |
