# Ciclo de desarrollo — Actividad 2, fase 1

Estado de cada paso de `docs/ORDEN_A2_FASE_1.md`, las pruebas que lo
respaldan, las decisiones tomadas al implementarlo y lo pendiente. Un paso
solo se marca cerrado con la salida de su verificación a la vista.

| Paso | Estado | Respaldo |
|---|---|---|
| C0. Entorno de la Mac mini | **cerrado** (22 oct 2026) | `prueba.sh` 26/26, `prueba_reglas.py` 50/50, `mide_errores.py` 2 respuestas para 9 casos, `arranca.sh` con 2 pestañas |
| C1. Contrato de registros | **cerrado** (22 oct 2026) | `prueba_mapa.py` 22/22 en Python 3.9.6, mutación de las 3 reglas, `prueba.sh` 26/26 |
| C2. Planta simulada | **cerrado** (22 oct 2026) | `prueba_sustituto.py funcional` 20/20, dos corridas de 10 min con la misma huella, `prueba.sh` 26/26 con la pestaña cargada |
| C3. Sonda Modbus | **cerrado** (22 oct 2026) | `prueba_sonda.py` 44/44, `mide` con proxy de 200 ms: mediana 206.6 ms; `prueba.sh` 26/26 |
| C4. A2-Planta | **cerrado** (24 oct 2026) | 200 cajas a 250 ms y 200 cajas a 500 ms + 200 ms de latencia: 0 perdidas, 0 duplicados, 11/11 cada una; estado seguro 25/25; control con balance 5/5 |
| C5. A2-Nube y reglas | **cerrado en local**, falta la base real (24 oct 2026) | reglas `proceso` 28/28 y Actividad 1 50/50 en el emulador; `prueba_nube.py` 14/14 contra el simulador (25 registros, todos 201); falta publicar y correr contra `planta_99` |
| C6. A2-HMI | pendiente | |
| C7. A2-Diagnóstico | pendiente | |
| C8. Gráfica | deseable | **cerrado con datos reales** (24 oct): visor real, `planta_01`, durante C9 | `corrida_c9_real.py`: 0 navegaciones, 1 → 127 cajas, la página termina con las 127 de Firebase; captura `docs/img/grafica_a2_real.png` |
| C9. Corrida instrumentada | esencial (mínima) | **cerrado**: 10 min contra Factory I/O escribiendo en `planta_01` (ventana 01:22:42 a 01:32:44 UTC del 25 oct) | `corrida_c9_real.py` 11/11: periodo p50 52 / p95 54 ms, latencia p50 52 / p95 55 ms, completitud 127/127 = 100 %; `docs/corrida_a2.md` |

### Fase 2 (`docs/ORDEN_A2_FASE_2.md`, 24 oct 2026)

| Paso | Prioridad | Estado | Respaldo |
|---|---|---|---|
| C5b. Cierre de C5 | esencial | **cerrado** (24 oct): reglas publicadas por Ari, `A2_NUBE=1` | `prueba_reglas_proceso.py --planta planta_99` 30/30 y `prueba_reglas_real.py --planta planta_99` 46/46 contra la base real |
| S. Seguridad del 1881 | esencial | commit `f784a4a` | `prueba_seguridad.py` 10/10 (y 10/10 sin capa 3), `prueba.sh` 26/26 |
| R1. Sonda `vigila` | esencial | **cerrado** con Factory I/O en Parallels (R0, opción B): rtt p95 9 ms (Node-RED), refresco p95 36.6 ms, salidas NC confirmadas con vigila | `prueba_vigila.py` 12/12, `prueba_sonda.py` 43/43 (el caso de host por omisión se omite con `A2_MODBUS_HOST` en `.env`) |
| R2. Mapa real | esencial | **cerrado**: `mapa_registros_fio.json` (33 etiquetas, con Reset y Run); Stop y E-stop NC **por su reposo**, falta presionarlos en la escena | `prueba_mapa.py` 26/26; `prueba_fio.py cliente` 200 cajas |
| R3. Desviador | esencial | **cerrado**: umbrales 4.5 / 7.0 V, pesaje detenido, motriz, una petición a la vez, ruedas quietas hasta que la caja deja el desviador; T_ef medido 55 ms (decisión de Ari) | `prueba_fio.py cliente --cajas 200` 16/17: 200/200 por su salida, 0 desvíos, 0 pérdidas, 0 caídas, pulsos de rama ≥ 6 lecturas (la falla: 2 rebotes de 20-30 ms que el antirrebote descartó) |
| C6. HMI | esencial | commit `164ca21`; probada contra la escena real en el ensayo; **otro equipo de la tailnet: falta (Ari)** | `prueba_hmi.py` 25/25; `ensayo_demo.py --real` pasos 3-8 |
| C7. Diagnóstico | deseable | commit `19400b9` | `prueba_diagnostico_a2.py` 18/18 simulado; 1 consulta real válida (gemini-3.1-flash-lite, 13.1 s, 408 tokens) |
| C8. Gráfica | deseable | **cerrado con datos reales** (24 oct): visor real, `planta_01`, durante C9 | `corrida_c9_real.py`: 0 navegaciones, 1 → 127 cajas, la página termina con las 127 de Firebase; captura `docs/img/grafica_a2_real.png` |
| C9. Corrida instrumentada | esencial (mínima) | **cerrado**: 10 min contra Factory I/O escribiendo en `planta_01` (ventana 01:22:42 a 01:32:44 UTC del 25 oct) | `corrida_c9_real.py` 11/11: periodo p50 52 / p95 54 ms, latencia p50 52 / p95 55 ms, completitud 127/127 = 100 %; `docs/corrida_a2.md` |
| D. Demostración | esencial | **cerrado**: ensayo completo de `docs/DEMO_A2.md` contra la escena real, HMI, Firebase real y gráfica | `ensayo_demo.py --real` **21/21, 0 bloqueados**; `ensayo_demo.py` (sustituto) 19/19; batería: todo pasa (mapa 26/26 tras regenerar la doc) |

---

## C0. Entorno de la Mac mini

### Qué se hizo

- `npm install -g node-red@5.0.9 firebase-tools@15.34.1`. Con el prefijo de
  npm en `/opt/homebrew`, los comandos quedan en `/opt/homebrew/bin`.
- `tunel.sh`: si no existe `bin/cloudflared`, usa el `cloudflared` del PATH.
  `bin/cloudflared` sigue teniendo prioridad, así que en la MacBook el
  comportamiento no cambia. Es el único cambio a un script de la Actividad 1.
- `prepara_a2.sh` (nuevo): instala `node-red-contrib-modbus@5.62.0` y
  `@flowfuse/node-red-dashboard@1.34.0`, con versión exacta, en
  `node-red/runtime` y en `${TMPDIR:-/tmp}/actividad1-pruebas/userdir`, la misma
  expresión que usa `pruebas/prueba.sh`. Con `--revisa` solo compara las
  versiones instaladas contra las esperadas y termina con código 1 si alguna
  falta.
- `.env` (fuera de git): `DATOS_DIR` apuntaba a `/Users/arinunez/dev/IoT/datos`,
  la ruta de la MacBook. En esta máquina ese `mkdir -p` falla y `arranca.sh`
  aborta por `set -e`. Ahora vale `"/Users/ariarinunezm/dev aws/dev/IoT/datos"`,
  entre comillas por el espacio. Se comprobó que `. ./.env` en bash y el lector
  de `tools/exporta_corrida.py` (que quita comillas) leen el mismo valor.
- `.env.example`: comentario sobre entrecomillar rutas con espacio.

### Verificación

```
pruebas/prueba.sh contra pruebas/simulador.py     26 correctas, 0 fallidas
pruebas/emulador/mide_errores.py                  9 escrituras, 2 respuestas distintas (igual que el 25 ago)
pruebas/prueba_reglas.py (emulador RTDB 4.11.2)   50 casos, 0 discrepancias
./arranca.sh                                      Node-RED v5.0.9 en el 1881, 2 pestañas
                                                  ('A1 · Ingesta', 'A1 · Diagnostico (Gemini)'), 42 nodos,
                                                  módulos node-red-contrib-modbus y @flowfuse/node-red-dashboard cargados
./estado.sh                                       pasos 1, 2, 4 y 8 marcados (ver abajo)
./prepara_a2.sh                                   segunda corrida idéntica: "up to date", mismas versiones
```

`prueba.sh` corrió con las paletas nuevas ya instaladas en su userDir, sin
avisos de carga en `nodered.log`.

### Decisiones

- **Node-RED 5.0.9.** La Actividad 1 no dejó versión anotada. Se instaló la
  vigente, que pide Node ≥ 22.9 (aquí hay v22.23.3), y los 26 casos pasan sin
  cambios en los flujos.
- **`arranca.sh` se verificó sin gastar cuota.** `inj_diag` dispara una
  consulta a Gemini 20 s después de arrancar los flujos (`once`). Node-RED se
  levantó con el `.env` real, se revisaron pestañas, módulos y `estado.sh`, y
  se apagó por puerto un segundo después de `Started flows`. El log no tiene
  ninguna línea de Gemini. No hubo escritura en la base.
- **Python.** La orden dice que `python3` es el del sistema (3.9.6), pero el
  `.zshrc` antepone el de Homebrew y `python3` resuelve a 3.11.17. El del
  sistema sigue en `/usr/bin/python3` (3.9.6). Los arneses de la Actividad 1
  corrieron con el 3.11, como los invocan sus scripts. Los scripts nuevos se
  prueban con `/usr/bin/python3` para garantizar la compatibilidad con 3.9.

### Pendiente o a la vista

- `estado.sh` marca el paso 3 sin hacer porque `firebase/database.rules.generado.json`
  está en `.gitignore` y no vino en la migración. Se regenera con
  `firebase/prepara.sh` en C5, que es donde se extienden las reglas. Los pasos
  5 y 10 salen sin marcar por la misma razón: `datos/` no se migró.
- Tailscale sin comando en el PATH: hace falta hasta C6 (abrir la HMI desde otro
  dispositivo de la tailnet).
- El userDir de `prueba.sh` vive en el directorio temporal. Si el sistema lo
  limpia, hay que volver a correr `./prepara_a2.sh`; `./prepara_a2.sh --revisa` lo
  detecta.

---

## C1. Contrato de registros

### Qué se hizo

- `config/mapa_registros_a2.json`: fuente única. Trae el driver (factor de
  escala 100 y límite por tabla) y las 11 etiquetas de la orden. Cada etiqueta
  lleva `nombre`, `tabla`, `direccion`, `tipo`, `escala`, `unidad`,
  `rango_fisico`, `sentido` y `descripcion`. Host, puerto y unidad Modbus no
  van aquí, sino en `.env` (C2/C3).
- `tools/mapa_registros.py` (Python 3.9, sin dependencias):
  - `valida`: código 0 si el mapa es válido. Si no, imprime todos los errores,
    cada uno con un código estable al inicio.
  - `doc`: genera `docs/MAPA_REGISTROS.md`. Con `doc --revisa` termina con
    código 1 si la doc quedó desfasada del JSON.
  - `carga()`, `a_registro()` y `de_registro()` para que C3 (sonda) y el
    resto lean el mapa ya validado y conviertan igual (int16 en complemento a dos).
- `docs/MAPA_REGISTROS.md`: generado. No se edita a mano.
- `pruebas/prueba_mapa.py`: 22 casos con `unittest`.

### Verificación

```
/usr/bin/python3 tools/mapa_registros.py valida     mapa valido: 11 etiquetas
/usr/bin/python3 tools/mapa_registros.py doc --revisa  docs/MAPA_REGISTROS.md al dia
/usr/bin/python3 pruebas/prueba_mapa.py -v          Ran 22 tests ... OK   (Python 3.9.6)
pruebas/prueba.sh                                   26 correctas, 0 fallidas
```

Los tres rechazos que pide la orden, cada uno con su control:

| Rechazo | Casos que rechazan | Control que debe pasar |
|---|---|---|
| dirección repetida en la misma tabla | `sens_bascula` en la entrada discreta 0 | dirección 0 usada en las 4 tablas a la vez |
| dirección fuera de los límites del driver | entrada discreta 256, registro de retención 64, dirección -1 | 255 y 63 |
| escala que desborda el tipo | uint16 [0, 700]×100 = 70000; int16 [-400, 10]×100 = -40000; uint16 con negativo; escala 10000 | [0, 655.35] = 65535 y [-327.68, 327.67] = int16 completo |

Cada caso de rechazo compara la lista completa de códigos, no solo que haya
error. Así, un defecto que dispare un error equivocado también se detecta.
Prueba de mutación: con cada una de las tres reglas apagada, su caso de rechazo
pasa sin error, así que cada prueba depende de la regla que dice probar.

### Decisiones

- **Las etiquetas booleanas llevan `escala`, `unidad` y `rango_fisico` en `null`.**
  Todas las etiquetas tienen los mismos nueve campos y un booleano no tiene
  rango que escalar.
- **`escala` debe ser igual a `driver.factor_escala`.** Factory I/O aplica un
  solo factor a todos los valores flotantes. Una etiqueta con otro factor
  leería mal sin aviso, así que se rechaza (`escala_distinta_del_driver`).
- **Las tablas de entrada (entradas discretas y registros de entrada) solo
  admiten `sentido: lectura`.** Modbus no tiene función para que un cliente las
  escriba.
- **Direcciones del protocolo, contadas desde 0**, como las muestra Factory I/O.
  No se usa la notación 1xxxx/3xxxx/4xxxx.
- `direccion: true` se rechaza: en Python `True == 1` y pasaría como dirección 1.
- Se eligió Python para el validador porque los arneses ya están en Python. El
  lado de Node-RED (C2/C4) leerá el mismo JSON. Si cambia el mapa, se valida
  aquí antes de que lo vea Node-RED.

### Pendiente

- Los nombres de las etiquetas siguen siendo provisionales hasta ver la escena
  real de Factory I/O. Cambiarlos solo toca el JSON y regenerar la doc.

---

## C2. Planta simulada

### Qué se hizo

- Pestaña **`A2 · Sustituto (planta simulada)`**, generada por
  `node-red/construye_flows.py` (los 42 nodos de la Actividad 1 quedan
  idénticos byte a byte, comprobado contra `HEAD`):
  - `inject` al arrancar → `20_sust_rutas.js` → `file in` (`A2_MAPA`) →
    `21_carga_mapa.js` (deja el mapa en `global.a2_mapa`, porque `flow` es por
    pestaña y A2-Planta lo va a leer) → `file in` (`A2_SUST_CONFIG`) →
    `22_sust_config.js` (valida e inicia `flow.sust`).
  - `inject` cada 0.1 s → `23_sust_pide_memoria.js` → **Modbus-Server** →
    `24_sust_emulador.js` → escrituras de vuelta al servidor y eventos a
    `$DATOS_DIR/a2_sustituto_eventos.jsonl`.
- `config/sustituto_a2.json`: semilla, geometría, constante de calibración
  (`k_banda_m_s_por_V` = 0.1 m/s por V), distribución de masas (normal
  truncada de 10 ± 2 kg en [2, 18], o uniforme), intervalo de emisión, báscula
  (plena escala, constante de tiempo, ruido) y empujador (carrera, alcance).
- `tools/modbus_tcp.py`: cliente Modbus TCP mínimo en Python 3.9 sin
  dependencias (FC 01–06), porque `pymodbus` no está instalado. Lo usa la
  prueba y es la base de la sonda de C3.
- `pruebas/prueba_sustituto.py`, en dos modos: `funcional` y `determinismo`.
- `arranca.sh`: exporta `A2_MAPA` y `A2_SUST_CONFIG` con las rutas del repo
  si `.env` no las fija. Son dos líneas que no cambian nada de la Actividad 1.
- `.env.example`: `A2_SUSTITUTO`, `A2_SUST_PUERTO`, `A2_SUST_HOST`,
  `A2_SUST_SEMILLA`, `A2_MAPA`, `A2_SUST_CONFIG`, sin valores.

### Verificación

```
prueba_sustituto.py funcional          20 correctas, 0 fallidas
prueba_sustituto.py determinismo       corrida1 semilla 20261022: 1063 eventos hasta t=600 s, 133 cajas, 130 salen, 606 s de pared
                                       corrida2 semilla 20261022: 1063 eventos hasta t=600 s, 133 cajas, 130 salen, 606 s de pared
                                       huellas 5be0bca003806c38 / 5be0bca003806c38, iguales evento por evento
                                       control semilla 20261023: la secuencia del primer minuto cambia (masas distintas)
                                       pedidos sin respuesta: 0 en las tres corridas
pruebas/prueba.sh                      26 correctas, 0 fallidas, con las tres pestañas cargadas
```

Qué cubre `funcional`: estado inicial (sensores en 0, empujador retraído,
peso 0); −2 V escrito como 65336, leído igual y decodificado por el emulador
como −2.0; 20 V avisado como fuera de rango; cada caja que sale activa entrada,
báscula y salida en ese orden (en los eventos y por el cable); el peso asentado
vale masa/20 kg × 10 V ± 3 cuentas en 3 cajas, y el primer valor sobre la báscula
queda por debajo del 50 %; el empujador suelta el límite trasero en menos de
0.3 s y llega al frontal en 0.5 ± 0.25 s; una caja que pasa con el empujador
extendido sale rechazada y nunca llega a `sens_salida`; con
`A2_SUST_PUERTO=5021` contesta en 5021 y no en 5020; con `A2_SUSTITUTO=0` nadie
contesta en 5020.

Una falla durante el desarrollo, que conviene guardar: la primera versión de la
prueba comparaba el peso con la masa a media báscula y dio −2, −3 y −4 cuentas,
siempre por debajo. No era ruido, era el retraso de primer orden (τ = 0.3 s): a
la mitad del paso todavía falta ~0.7 %. Ahora la prueba mide en el último cuarto
del paso y además comprueba que el retraso exista, porque C4 lo necesita para
probar su "valor estable".

### Decisiones

- **El tiempo de la simulación es `tick × 0.1 s`, no el reloj de pared.** Todo lo
  aleatorio sale de tres generadores mulberry32 con semilla, uno por fuente
  (masas, intervalos, ruido). Así, cambiar una fuente no altera las otras.
- **`t = 0` es el primer encendido de `emisor_on`.** Así el instante de arranque
  de Node-RED queda fuera de la comparación. La prueba escribe velocidad y
  alimentación antes que el emisor, y compara lo que produce la planta (los
  eventos de entrada los pone la propia prueba).
- **El Modbus-Server no avisa cuando un cliente escribe.** Solo entrega sus
  buffers como respuesta a un mensaje, así que en cada tick se le manda un
  pedido numerado que no es una escritura válida. El emulador espera las dos
  respuestas de ese pedido (holding y coils) para avanzar. El nodo mide la
  memoria en múltiplos de 8 bytes (`address × 8`), así que el emulador escribe
  la imagen completa de las entradas discretas y de los registros de entrada
  desde la dirección 0.
- **Los buffers del servidor se toman de los límites del driver en el mapa**
  (256 bits y 64 registros), así que el sustituto recorta igual que Factory I/O.
- **Valores por omisión con variables de pestaña en JSONata**
  (`SUST_PUERTO`, `SUST_HOST`, `SUST_ACTIVO`): no hace falta cambiar los scripts de
  la Actividad 1 para que el puerto sea 5020 y el host 127.0.0.1.
- **Apagado (`A2_SUSTITUTO=0`):** el emulador no avanza y el servidor se va al
  puerto 0, que es efímero. Un nodo no se puede desactivar en tiempo de
  ejecución, y un servidor que siguiera en 5020 contestando ceros engañaría a
  un cliente mal configurado; así, el cliente recibe conexión rechazada.
- **Host por omisión 127.0.0.1**, no 0.0.0.0: el sustituto no se expone a la
  red local ni a la tailnet salvo que se pida con `A2_SUST_HOST`.
- **Sin `A2_MAPA` la pestaña se queda quieta sin lanzar error.** `prueba.sh`
  corre sin esa variable, y un error caería en sus nodos Catch y en
  `errores.log`, que el caso 7 de la Actividad 1 usa como evidencia.
- **Modelo de la línea (provisional):** alimentación y báscula avanzan a
  0.5 m/s con `alimentacion_on`; a partir de `inicio_banda_variable` el tramo
  va a `k × vel_banda_V`, que puede ser negativo (la caja retrocede sin volver a
  la báscula). Las cajas no se enciman, y el empujador saca la caja que tiene
  enfrente al pasar el 50 % de su carrera.

### Pendiente

- La geometría, la constante de calibración y la báscula son inventadas. Se
  reemplazan cuando se mida la escena real. Basta cambiar
  `config/sustituto_a2.json`, sin tocar código.
- A 10 V la caja (0.4 m) tapa un sensor 0.4 s. Con el sondeo de 250 ms de C4 se
  alcanza a ver, pero con poco margen; hay que revisarlo en C4.

---

## C3. Sonda Modbus

### Qué se hizo

- `tools/sonda_modbus.py` (Python 3.9, sin dependencias, sobre `tools/modbus_tcp.py`
  y el mapa de C1):
  - `lista`: las 11 etiquetas con tabla, dirección, tipo y rango.
  - `lee <etiqueta|todas>`: valor físico, tabla, dirección y palabra cruda.
  - `escribe <etiqueta> <valor>`: en unidades físicas, con la conversión del mapa
    (−2.5 V → palabra 65286). Después lee de vuelta: que el servidor acepte una
    escritura no prueba que la guardó donde se cree.
  - `mide <etiqueta> -n N [--pausa-ms]`: N lecturas por la misma conexión.
    Reporta el saludo TCP aparte y el tiempo de ida y vuelta por petición
    (mínimo, mediana, p95, máximo). Se agregó a pedido de Ari: Factory I/O
    queda en Azure East Asia (Hong Kong) y cada lectura es un viaje completo.
  - Destino: `--host/--puerto/--unidad`, o `A2_MODBUS_HOST/PUERTO/UNIDAD` del
    entorno o de `.env`. Por omisión, 127.0.0.1:5020, unidad 1 (el sustituto).
  - Códigos de salida: 0 bien, 1 uso o valor inválido (incluye escribir una
    etiqueta de solo lectura o fuera de rango, sin abrir la red), 2 sin
    conexión, 3 excepción Modbus.
- `pruebas/proxy_retardo.py`: proxy TCP que agrega un retardo de ida y vuelta
  fijo (mitad en cada sentido) sin tocar el sustituto. Es el oráculo de `mide`.
- `pruebas/prueba_sonda.py`: invoca la sonda por su línea de comandos.
- `.env.example`: `A2_MODBUS_HOST`, `A2_MODBUS_PUERTO`, `A2_MODBUS_UNIDAD`, sin valores.
- `.gitignore` (commit aparte, `4465350`): `datos/*.json`, `datos/*.jsonl`, `__pycache__`.

### Verificación

```
/usr/bin/python3 pruebas/prueba_sonda.py   44 correctas, 0 fallidas
pruebas/prueba_mapa.py                     22 tests OK
pruebas/prueba.sh                          26 correctas, 0 fallidas
```

Cada etiqueta, contra un oráculo que no es la sonda:

| Qué | Oráculo |
|---|---|
| 6 de lectura en reposo (sensores 0, trasero 1, peso 0) | estado inicial del emulador |
| `sens_entrada`, `sens_bascula`, `sens_salida` en 1 | la planta se congela con una caja tapando el sensor |
| `peso_V` = 5.125 V ± 0.05 | masa de esa caja (10.250 kg) según el registro de eventos del emulador |
| `emp_lim_frontal` 1 / `emp_lim_trasero` 0 | empujador extendido por la sonda |
| 4 bobinas × 1/0 y `vel_banda_V` en 5, −2, −10, 10, −0.01, 0 | lectura de vuelta, palabra cruda por el cliente directo (−2 → 65336, −10 → 64536, −0.01 → 65535) y el registro de eventos: la planta leyó las 14 escrituras en orden y con su valor |

`mide`, directo y con retardo conocido:

```
directo        ida y vuelta  min 0.1   mediana 0.1   p95 0.1   max 0.2   ms
proxy 200 ms   ida y vuelta  min 203.0 mediana 206.6 p95 210.6 max 210.8 ms
```

### Decisiones

- **Una sola conexión para las N lecturas de `mide`**, y el saludo TCP medido
  aparte. Así queda separado el costo de abrir la conexión del costo de cada
  petición, que es lo que paga el sondeo de A2-Planta.
- **A través del proxy, el saludo TCP no incluye el retardo**, porque el proxy
  acepta en local. Contra Azure sí lo incluye: ahí "conexion" ≈ un RTT.
- **Las escrituras rechazadas no abren la red.** Una etiqueta de solo lectura o
  un valor fuera del rango del mapa se rechazan antes de conectar.

### Pendiente

- Correr `mide` contra Factory I/O en Azure en cuanto la máquina responda:
  `python3 tools/sonda_modbus.py --host <IP de Tailscale> --puerto 502 mide peso_V -n 50`.
- Puntos que Ari mandó el 22 de octubre para C4 (**confirmados e incorporados en C4**): latencia simulada configurable en las pruebas (el proxy ya existe);
  velocidad máxima de banda para que cada sensor quede activo al menos tres
  periodos de sondeo con la latencia incluida, guardada en la configuración y en
  este documento; detección de cajas que no dependa de un solo pulso;
  verificación de consistencia entre cajas que entran y que salen; y una segunda
  corrida de 200 cajas con sondeo de 500 ms y 200 ms de latencia simulada, sin
  pérdida ni duplicado.

---

## C4. A2-Planta

Incluye los cuatro puntos que Ari agregó el 22 de octubre: medir la ida y
vuelta (hecho en C3), latencia simulada configurable en las pruebas,
velocidad máxima de banda con al menos tres lecturas por sensor, detección sin
depender de una sola lectura más verificación de consistencia, y una segunda
corrida de 200 cajas con sondeo de 500 ms y 200 ms de ida y vuelta.

### Qué se hizo

- Pestaña **`A2 · Planta (cliente Modbus)`**, generada por `construye_flows.py`.
  Los 59 nodos de la Actividad 1 y de C2 quedan idénticos.
  - Cliente `modbus-client` dentro de la pestaña. El destino viene de
    `A2_MODBUS_HOST/PUERTO/UNIDAD`, con valores por omisión en JSONata
    (127.0.0.1:5020, unidad 1) y **sin `bufferCommands`**: una orden guardada
    durante un corte llegaría después de reconectar, en medio de la secuencia
    segura.
  - `27_planta_ciclo.js`: un reloj de 25 ms con rejilla fija por periodo
    (`A2_SONDEO_MS` o `sondeo_ms` = 250). Cada ciclo es **un bloque** de
    entradas discretas. Mientras hay caja en la báscula se lee antes un bloque
    de registros de entrada. Si un ciclo no termina a tiempo, se salta el
    siguiente y se cuenta. También aquí está el perro guardián de comunicación
    (`comunicacion_timeout_ms` = 2 s).
  - `28_planta_lectura.js`: antirrebote, FIFO, pesaje, clasificación,
    empujador, consistencia y arranque de la secuencia segura.
  - `29_planta_escritura.js`: encadena la secuencia segura y registra lo que la
    planta aceptó.
  - `30_planta_comando.js` (`POST /a2/planta/comando`: marcha, paro, emisor,
    velocidad) y `31_planta_estado.js` (`GET /a2/planta/estado`). Solo aceptan
    peticiones locales o de la tailnet y rechazan lo que llega por el túnel de
    Cloudflare de la Actividad 1, que publica el 1881 en Internet.
  - `link out` `a2_paso_caja` para C5. Eventos en `$DATOS_DIR/a2_planta_eventos.jsonl`.
- `config/planta_a2.json`: lo que el cliente supone de la línea (geometría,
  constante de calibración, báscula, tolerancia), los dos escenarios y los
  límites calculados.
- `tools/limites_planta.py`: el cálculo de la velocidad de banda permitida.
  `26_planta_config.js` hace la misma cuenta en Node-RED y la prueba compara
  las dos.
- `pruebas/proxy_retardo.py`: latencia configurable sin tocar el sustituto,
  corte de la conexión a voluntad y registro de las tramas del cliente (el
  orden real de las escrituras en el cable).
- `pruebas/prueba_planta.py`: modos `seguro`, `corrida --escenario local|azure`
  y `control`.
- `config/sustituto_a2.json`: geometría y constantes ajustadas (ver Decisiones).
- `arranca.sh`: exporta `A2_PLANTA_CONFIG`. `.env.example`: `A2_SONDEO_MS`,
  `A2_RTT_PREVISTO_MS`, `A2_PLANTA_CONFIG`.

### Velocidad máxima de banda (definiciones fijadas antes de medir)

```
T_ef  = max(sondeo, (lecturas + escrituras por ciclo) x rtt) + holgura      peor espacio entre lecturas
t_min = 3 x T_ef                                                             periodos_minimos = 3
encendido   L / v       >= t_min   ->  v <= L / t_min                       la caja se ve 3 lecturas
apagado     dt - L / v  >= t_min   ->  v >= L / (dt - t_min)                dos cajas no se funden
```

Con L = 0.4 m (largo de caja), dt = 5 s (emisión mínima), 2 lecturas + 1
escritura por ciclo, holgura de 50 ms y k = 0.1 m/s por V. Los sensores de la
banda de alimentación (0.18 m/s, fija) solo se comprueban:

| Escenario | sondeo | rtt | T_ef | t_min | `vel_banda_V` permitida | entrada y báscula (encendido / apagado) |
|---|---|---|---|---|---|---|
| local | 250 ms | 5 ms | 300 ms | 0.90 s | **0.98 a 4.44 V** | 2.22 s / 2.78 s, cumple |
| azure | 500 ms | 200 ms | 650 ms | 1.95 s | **1.32 a 2.05 V** | 2.22 s / 2.78 s, cumple |

Queda en `config/planta_a2.json` → `limites_calculados`
(`python3 tools/limites_planta.py --escribe`). La consigna admite **0 (paro)
o un valor dentro de [vel_min_V, vel_max_V]**. Cualquier otro valor se
rechaza con 422, también los que quedan entre 0 y el mínimo, porque ahí dos
cajas se funden en una sola lectura. "marcha" se rechaza con 422 si la
consigna no está dentro del intervalo, y con 409 (`limites_no_factibles`) si
con el sondeo y el rtt actuales no hay intervalo posible.

### Verificación

```
prueba_planta.py corrida --escenario local --cajas 200    11 correctas, 0 fallidas
  1187 s a 4.44 V; entran 200, salen 164, rechazo 36; perdidas 0, fantasmas 0, rechazos fallidos 0
  periodo efectivo ms: p50 242, p95 268, max 340, media 250, sd 12.9
  lecturas minimas por pulso: sens_entrada 8, sens_bascula 8, sens_salida 3
  masa: peor 0.083 kg
prueba_planta.py corrida --escenario azure --cajas 200    11 correctas, 0 fallidas
  1195 s a 2.05 V; entran 200, salen 165, rechazo 35; perdidas 0, fantasmas 0, rechazos fallidos 0
  periodo efectivo ms: p50 504, p95 511, max 552, media 500, sd 11.1
  ida y vuelta medida ms: p50 215, p95 222, max 304
  lecturas minimas por pulso: sens_entrada 4, sens_bascula 3, sens_salida 3
  masa: peor 0.123 kg
prueba_planta.py seguro                                   25 correctas, 0 fallidas   (24 oct, tras las correcciones)
prueba_planta.py control                                   5 correctas, 0 fallidas   (24 oct, con balance completo)
regresión: prueba_sustituto funcional 20/20, determinismo 1 min (huellas iguales),
           prueba_sonda 44/44, prueba_mapa 22/22, prueba.sh 26/26
```

Oráculo de las corridas: el registro de eventos del **sustituto** (qué caja se
emitió, con qué masa, si salió o la empujaron), caja por caja contra el
`paso_caja` del cliente. En cada corrida se comprueba:

- 200 de 200, sin duplicados.
- Balance: entradas = salidas + rechazos.
- Masa ± 0.15 kg.
- Destino igual al real.
- Destinos iguales a la tolerancia (10 ± 2.5 kg). Se excluyen las 8 cajas que
  están a menos de 0.15 kg del límite.
- Límites del cliente iguales a los de `limites_planta.py`, y una consigna
  0.01 V arriba del límite rechazada.
- Cada pulso de sensor visto en al menos 3 lecturas.

Estado seguro: se corta la conexión en el proxy con la línea en marcha. El
cliente pasa a `sin_comunicacion` en 2.0 s y rechaza comandos con 409. Al
volver la red, **en el cable** las tres primeras escrituras son FC6
`vel_banda_V=0`, FC5 `emisor_on=0` y FC5 `alimentacion_on=0`, en ese orden. La línea queda detenida sin
reanudar sola, y las 2 cajas que estaban en el tramo se marcan como perdidas
por la desconexión. Después, marcha funciona y la consigna llega.

Control (que la consistencia detecta pérdidas): con la banda a 8 V por fuera
del cliente, se apaga el emisor tras 6 cajas, se espera a que todas salgan de
la línea y además el tránsito máximo del cliente (34 s). El sustituto emitió
6 cajas, el cliente vio entrar 6, salir 0 y marcó 6 perdidas, sin ninguna en
el tramo. **El balance cierra**: salidas + rechazos + perdidas = 0 + 0 + 6 =
6 cajas fuera de la línea.

Correcciones del 24 de octubre, antes del commit (`prueba_planta.py seguro`,
25 correctas, 0 fallidas):

- Secuencia segura de tres pasos, en el cable y en ese orden, al arrancar y
  al reconectar.
- "marcha" con consigna 0 → 422; consigna 0.97 V (0.01 debajo del mínimo) →
  422; 0.01 arriba del máximo → 422; 0 y el mínimo exacto se aceptan; los
  rechazos no escriben nada en el cable.
- Con sondeo de 3000 ms los límites salen no factibles, "marcha" → 409
  `limites_no_factibles`, y la comunicación no oscila (timeout de 9150 ms, 0
  desconexiones en 10 s).

### Decisiones

- **Detección con antirrebote de 2 lecturas** (`lecturas_para_cambio`). Un
  cambio de sensor se acepta solo si lo muestran dos lecturas seguidas, y su
  instante es el de la primera. Con 3 lecturas garantizadas por pulso queda
  una de margen. Un pulso de una sola lectura no cuenta.
- **Consistencia.** Salida sin caja en la cola cuenta como fantasma; báscula
  sin caja por pesar, fantasma de báscula; caja que excede 1.5 veces su
  tránsito esperado (+3 T_ef), perdida, con `luz_alerta`. En el estado van
  contadores y balance.
- **Pesaje entre dos lecturas de sensores.** El peso se pide antes que los
  sensores, y vale solo si la lectura de sensores anterior y la siguiente ven
  la caja en la báscula. Se retiene la última de 3 lecturas seguidas dentro de
  0.03 V; si la caja sale antes, la última lectura válida, marcada no estable.
- **Rechazo por posición calculada.** La salida de la báscula se toma a mitad
  del intervalo entre lecturas. El empujador se manda cuando la caja va a
  estar enfrente (`bascula_a_empujador_m / (k × vel)`, menos rtt/2 y lo que
  tarda en extenderse) y se confirma con el límite frontal. Su tiempo límite
  sale del sondeo: carrera + 3 × T_ef + rtt + margen.
- **Tras reconectar, la línea no se reanuda sola.** La secuencia segura es
  `vel_banda_V=0` → `emisor_on=0` → `alimentacion_on=0`, cada una después de
  confirmada la anterior, y luego hace falta un "marcha". Las cajas que estaban en el
  tramo ya no se pueden seguir y se descartan, contadas.
- **Consigna 0 o dentro de [vel_min_V, vel_max_V].** Nada negativo desde el
  cliente, porque la FIFO supone que la banda avanza.
- **El tiempo límite de comunicación crece con el sondeo:** es el mayor entre
  `comunicacion_timeout_ms` y 3 T_ef. Con un periodo mayor que el valor fijo,
  el perro guardián declaraba la línea sin comunicación entre dos lecturas
  sanas (lo destapó el caso de 3000 ms).
- **Geometría del sustituto ajustada** (sigue siendo provisional). Con la de
  C2 ningún escenario es factible: `sens_entrada` a 0.5 m/s fija se ve 0.8 s, y
  en Azure la velocidad mínima por el apagado (3.81 V) queda arriba de la
  máxima por el encendido (2.05 V). Ahora: alimentación 0.18 m/s, báscula de
  0.4 m, emisión cada 5 a 6.5 s. El determinismo completo de C2 se repitió con
  la geometría nueva el 24 de octubre: dos corridas de 10 min con la semilla
  20261022, 836 eventos, 105 cajas, huellas `b4b22f7cf32b5d45` iguales evento
  por evento; con la semilla 20261023 el primer minuto cambia.

### Fallas encontradas y corregidas durante C4

| Síntoma | Causa | Corrección |
|---|---|---|
| masas −0.08 y −0.15 kg | "estable" con 2 lecturas a 0.05 V mientras la báscula subía, y promedio | banda 0.03 V, 3 lecturas, se retiene la última |
| Azure: 4 fallas de empujador y la FIFO desalineada (6.7 kg de error) | tiempo límite fijo de 1.5 s; confirmar tarda ~2 s con 650 ms entre lecturas | límite calculado con el sondeo; confirmación tardía aceptada |
| Azure: −2 a −3.8 kg en cajas con 4 muestras | el peso se leía 200 ms después de los sensores, con la caja ya fuera | peso antes que sensores, válido solo entre dos lecturas con caja |
| local: peor 0.177 kg en 200 cajas | 2 lecturas "estables" a 250 ms todavía en la subida | 3 lecturas seguidas |
| prueba de estado seguro: no veía el 0 | el sustituto mira cada 100 ms; el oráculo correcto es el cable | el proxy registra las tramas y la prueba lee FC5/FC6 en orden |

### Pendiente

- **La escena real de Factory I/O usa un desviador de ruedas, no un empujador.**
  Sus etiquetas son Send left/right/forward, At left/right entry, At scale
  entry/exit, Load scale y Weight. Cuando llegue la lista de etiquetas, el
  rechazo y su confirmación cambian en código (hoy: `emp_extender` confirmado
  con `emp_lim_frontal`/`emp_lim_trasero` en `28_planta_lectura.js` y
  `27_planta_ciclo.js`), además del mapa y la geometría.
- **Factory I/O corre a ~1 FPS en la VM.** La sonda debe medir, además del rtt,
  cada cuánto cambian de verdad los valores de la escena. Si la escena refresca
  más lento que T_ef, los límites de velocidad no valen: el periodo efectivo de
  muestreo sería el del refresco, no el del sondeo.
- **Prueba de control:** antes dejaba cajas sin contar (el sustituto sacó 5 y
  el cliente marcó 2 perdidas). Ya corregido: ahora espera el tránsito máximo
  del cliente y verifica el balance completo (ver Verificación).
- El periodo efectivo y su variación, la latencia de la lectura a Firebase y la
  completitud se definen y se miden en C9. Aquí solo se reportan los periodos
  vistos.
- Contra Factory I/O, `rtt_previsto_ms` debe salir de
  `sonda_modbus.py mide`. Si la mediana pasa de 200 ms, `limites_planta.py`
  da otra velocidad máxima.
- La geometría (`config/planta_a2.json` → `linea`) se mide en la escena real.
  Si Factory I/O mueve la báscula con la banda variable, hay que cambiar
  `banda` de `sens_bascula`.
- Los sensores del empujador se ven solo 2 lecturas en el frontal: no es
  problema, porque el frontal se confirma y se retrae de inmediato, pero queda
  anotado.

---

## C5. A2-Nube y reglas

### Qué se hizo

- `firebase/database.rules.json`: rama nueva
  `/plantas/{plantaId}/proceso/{registroId}`, con las mismas cuatro propiedades
  de la Actividad 1:
  1. escritura anónima imposible;
  2. solo el UID del ingestor y solo en `planta_NN`;
  3. append-only (`!data.exists()`);
  4. esquema validado en el servidor: tipos, rangos, marcas por expresión
     regular y `$otro: false`.

  Lectura solo para el visor y el ingestor. Las ramas `telemetria`,
  `diagnosticos`, `materiales` y la raíz quedan idénticas (comprobado contra
  `HEAD`).

  | Campo | Regla |
  |---|---|
  | `ts_origen` | instante de la lectura Modbus en Node-RED, ISO UTC con `Z` |
  | `ts_escritura` | ISO con desplazamiento local, como en la Actividad 1 |
  | `vel_banda_V` | número en [−10, 10] |
  | `peso_V` | número en [0, 10] |
  | `caja_masa_kg` | número en [0, 20]; **solo en registros de caja**, los latidos no lo llevan |
  | `cajas_acumuladas` | entero ≥ 0 |
  | `estado_linea` | `en_marcha`, `detenida`, `sin_comunicacion`, `reconectando` o `iniciando` |

- Pestaña **`A2 · Nube (rama proceso)`**:
  - `link in` desde A2-Planta, más un reloj de 1 s para el latido.
  - `32_nube_registro.js` arma el registro.
  - `33_nube_valida.js` valida con las mismas condiciones que las reglas y
    arma el POST con el idToken del ingestor.
  - Un limitador de 2 por segundo, un `http request` POST y
    `34_nube_respuesta.js`, que escribe el CSV
    `$DATOS_DIR/a2_nube_AAAA-MM-DD.csv` y renueva la sesión tras un 401, una
    vez por minuto. La sesión propia reutiliza `05_login_firebase.js` y
    `06_guarda_token.js`; el token se comparte en `global`.
- A2-Planta publica `global.a2_planta_resumen` (en `27_planta_ciclo.js`), y el
  `paso_caja` lleva `cajas_acumuladas` y `vel_banda_V` (`28_planta_lectura.js`).
- `pruebas/simulador.py` acepta la rama `proceso`. Son tres líneas, y
  `prueba.sh` sigue en 26/26.
- `pruebas/prueba_reglas_proceso.py` (emulador o base real) y `pruebas/prueba_nube.py`.
- `.env.example`: `A2_NUBE` y `A2_LATIDO_S`.

### Verificación

```
prueba_reglas_proceso.py --emulador 127.0.0.1:9000   28 casos, 0 discrepancias
prueba_reglas.py (Actividad 1, reglas extendidas)    50 casos, 0 discrepancias
mide_errores.py                                      2 respuestas distintas, igual que antes
prueba_nube.py                                       14 correctas, 0 fallidas
  75 s: 10 paso_caja; el simulador recibio 25 registros (10 de caja, 15 latidos de 5 s)
  CSV: 25 filas, todas codigo 201 aceptado
  latencia lectura -> escritura de las cajas: mediana 259 ms, max 261 ms
regresion: prueba.sh 26/26, prueba_planta seguro 25/25, corrida azure 15 cajas 11/11, prueba_mapa OK
```

`prueba_nube.py` comprueba:

- Un registro de caja por cada `paso_caja`, con su masa y en orden.
- `cajas_acumuladas` de 1 a 10 sin saltos.
- Latidos al ritmo configurado.
- Esquema de las reglas en los 25 registros.
- El último latido dice `detenida`.
- Con permiso negado se anota `http 401` / código 502 y no 201; al volver,
  la sesión se renueva y el siguiente entra con 201.
- Sin `A2_NUBE=1`, 0 registros en 12 s.

### Decisiones

- **"Aceptado con 201".** Firebase contesta **200** con `{"name": ...}` a un
  POST aceptado. Igual que la Actividad 1, el flujo anota el registro aceptado
  con código **201** (creado) y guarda en la columna `http` lo que contestó
  Firebase.
- **Sin campos nuevos.** El registro lleva exactamente los siete de la orden, y
  el latido se distingue por no traer `caja_masa_kg`. El destino de la caja
  (salida o rechazo) no va a Firebase. Si C8 lo necesita, hay que agregarlo a
  la orden y a las reglas.
- **Ritmo:** una escritura por caja (~1 cada 5.75 s con el emisor encendido)
  más un latido cada `A2_LATIDO_S` = 60 s, con un limitador de 2/s detrás. En
  una hora son unas 630 escrituras, contra las 720 por hora de la telemetría de
  la Actividad 1 a 5 s.
- **`A2_NUBE=1` para escribir, apagado por omisión.** Hasta que estén
  publicadas las reglas con `proceso`, cada escritura sería un 401 contra la
  base real, y la regla 7 de esta fase pide no escribir en ella.
- **`cajas_acumuladas` se reinicia al reiniciar Node-RED.** Es el contador de
  la sesión de A2-Planta, no uno persistente como `ciclos_acumulados` del
  ESP32.
- **La latencia incluye el antirrebote.** `ts_origen` es la primera lectura
  que vio la salida, y la caja se confirma un periodo después. De ahí la
  mediana de 259 ms con sondeo de 250 ms. Se define y se mide en C9.
- **Sin reintento:** un registro que Firebase rechaza queda en el CSV con su
  código y no se reintenta (en la Actividad 1 reintentaba el emisor).

### Lo que le toca a Ari (en este orden)

1. `./firebase/prepara.sh`. Resuelve los dos UID con las credenciales del
   `.env` (Identity Toolkit, no escribe en la base) y genera
   **`firebase/database.rules.generado.json`**. El archivo generado no vino en
   la migración desde la MacBook.
2. Consola de Firebase → Realtime Database → **Reglas** → reemplazar todo por el
   contenido de **`firebase/database.rules.generado.json`** → **Publicar**.
   (`cat firebase/database.rules.generado.json | pbcopy`)
3. Verificación contra la base real, en `planta_99`:
   `python3 pruebas/prueba_reglas_proceso.py --planta planta_99` (26 casos) y
   `python3 pruebas/prueba_reglas_real.py --planta planta_99` (46 casos de la
   Actividad 1, para confirmar que las reglas publicadas no rompieron nada).
   Deja unos 40 registros imborrables en `planta_99`, como en la Actividad 1.
4. `A2_NUBE=1` en `.env`, y `A2_LATIDO_S` si se quiere otro periodo.

### Pendiente

- Los pasos 1 a 4 de arriba y su salida.
- C8 mostrará la masa por caja y las cajas por minuto. Si además debe
  distinguir rechazos, hace falta un campo de destino (cambio de orden y de
  reglas).


---

# Fase 2

## C5b. Cierre de C5

- Commit de C5: `4bb46a7`.
- `./firebase/prepara.sh` (corrido por Claude el 24 oct, exit 0). Resolvió el
  UID del ingestor `NCGRYv24iXc1BFSxD3RViIDeYRY2` y el del visor
  `FSn5au5bUuQmUD0sNUZ7kbyWn1w2`, y escribió
  `firebase/database.rules.generado.json` (sin marcadores `__UID_`, con las
  ramas `telemetria`, `diagnosticos`, `proceso` y `materiales`). El archivo
  está en `.gitignore`.
- **PUERTA ARI P1, abierta:** publicar `firebase/database.rules.generado.json`
  en Consola → Realtime Database → Reglas. Al confirmarlo: correr
  `prueba_reglas_proceso.py --planta planta_99` y
  `prueba_reglas_real.py --planta planta_99`, y poner `A2_NUBE=1` en `.env`.
  Hasta entonces C9 (que escribe en `planta_01`) queda bloqueado en su corrida
  real.

## S. Seguridad del puerto 1881

### Qué se hizo

- `node-red/settings.js` en el repositorio, sin credenciales. Lo usan
  `arranca.sh`, `pruebas/prueba.sh` y las pruebas de la Actividad 2
  (`--settings`); el userDir de cada uno no cambia.
- Toda petición con `cf-connecting-ip` o `cf-ray` (las pone cloudflared) se
  rechaza con 403 `origen_no_permitido`, salvo `POST /telemetria`, la ingesta
  de Wokwi. Tres capas:
  1. `httpAdminMiddleware` y `httpNodeMiddleware`: editor, API de admin y
     rutas `http in`.
  2. `dashboard.middleware` y `dashboard.ioMiddleware` de Dashboard 2.0 1.34.0.
     `ioMiddleware` reemplaza al de la librería, así que repite lo que el
     original hacía: rechazar websocket directo y peticiones de otro origen.
  3. Un filtro en el servidor HTTP del proceso (`request` y `upgrade`). Es la
     alternativa documentada que pide la orden: socket.io (engine.io) atiende
     su ruta antes que express, y con `ioMiddleware` solo puede cortar la
     conexión después del saludo, no contestar 403. Además, ninguna de las
     capas 1 y 2 ve el websocket del editor (`/comms`).
- `pruebas/prueba_seguridad.py`: con y sin las cabeceras. Con
  `--sin-capa3` (`A2_FILTRO_SERVIDOR=0`) comprueba que las capas 1 y 2 cubren
  lo suyo por sí solas y deja medido lo que solo la capa 3 cubre.
- `pruebas/bateria.sh` (lo pide D; se adelantó para usarlo desde aquí) y
  `.assurance/config.toml` con los comandos de prueba bajo `[audit]`. Nota: el
  gancho de cierre no usa las declaraciones del proyecto en la sesión que creó
  el archivo, así que esta sesión no se beneficia; las siguientes sí.

### Verificación

```
prueba_seguridad.py               10 correctas, 0 fallidas
prueba_seguridad.py --sin-capa3   10 correctas, 0 fallidas
prueba.sh                         26 correctas, 0 fallidas (log: Settings file node-red/settings.js)
prueba_nube.py                    14 correctas, 0 fallidas
```

| Ruta | Sin túnel | Por el túnel |
|---|---|---|
| `GET /` (editor), `/flows`, `/settings` | 200 | 403 |
| `GET /a2/planta/estado`, `POST /a2/planta/comando` | 200 | 403 |
| `GET /telemetria` | 404 | 403 |
| `POST /telemetria` (y con `?x=1`) | 401 `clave_invalida` de la ingesta | 401 `clave_invalida`: llega a la ingesta |
| websocket del editor `/comms` | 101 | 403; **sin la capa 3, 101** |
| `/dashboard` y su socket.io | se prueban en C6 | (no existe `ui-base` hasta C6) |

### Pendiente

- Los casos de `/dashboard`, socket.io polling y websocket se activan solos en
  `prueba_seguridad.py` cuando C6 crea el `ui-base`.
- No hay `adminAuth`. La orden no lo pide, y el editor queda abierto en la red
  local y en la tailnet; el túnel ya no lo alcanza.

## R1. Sonda en modo vigilancia

### Qué se hizo

- `tools/sonda_modbus.py vigila -s N [--discretas a:b] [--entrada a:b] [--json f] [--detalle]`,
  solo de lectura. Cada vuelta lee un bloque de entradas discretas y uno de
  registros de entrada, sin pausa. Sin rangos usa los del mapa; con rangos
  funciona aunque el mapa no pase el validador (para descubrir las
  direcciones de una escena cuyo mapa aún no existe).
- Reporta, por dirección:
  - número de cambios;
  - pulsos en 1 con su duración en lecturas y en segundos (mín., mediana, máx.);
  - intervalo mínimo y mediano entre cambios.

  En total: vueltas por segundo, lecturas fallidas, la ida y vuelta de cada
  petición (mín., mediana, p95, máx.) y el **periodo de refresco**. Con
  `--json` guarda cada cambio con su hora.
- `pruebas/prueba_vigila.py`: `vigila` a través de `proxy_retardo.py`
  (20 ms) mientras la prueba mueve el sustituto en el 5020: 4 cajas y un
  ciclo del empujador.

### Verificación

```
prueba_vigila.py   12 correctas, 0 fallidas
  983 vueltas en 48 s (20.5/s), ida y vuelta min 20.5 / mediana 24.3 ms
  sens_entrada, sens_bascula, sens_salida: 4 subidas / 4 bajadas = sustituto 4 / 4
  emp_lim_frontal 1/1 = 1/1, emp_lim_trasero 1/1 = 1/1
  pulso de sens_entrada 2.19-2.22 s = largo / alimentacion = 2.22 s
  peso_V: intervalo mediano 0.097 s = tick del sustituto; refresco (minimo) 0.049 s
prueba_sonda.py    44 correctas, 0 fallidas
```

Dos fallas del oráculo durante el paso, corregidas:
1. `emp_lim_trasero`: el sustituto registra `sensor_on` en el tick 0, su estado
   inicial, antes de la primera lectura de `vigila`. Se excluye el tick 0.
2. El refresco medido (0.049 s) salió por debajo del tick (0.1 s). Los ticks
   del sustituto salen de un `inject` y varían: uno tarde seguido de uno a
   tiempo quedan a ~50 ms. El refresco es un mínimo por definición y recoge esa
   variación; la prueba compara la **mediana** del intervalo con el tick. Por
   eso `vigila` reporta las dos. **Contra Factory I/O conviene mirar las dos:**
   el mínimo puede ser menor que el cuadro real si el driver contesta a
   destiempo.

### Bloqueado

- **Medición de 3 minutos contra la VM de Azure: BLOQUEADA.** El 24 oct a las
  ~05:10, `tailscale status` muestra `factoryio-vm` (100.116.150.89)
  *offline, last seen 21m ago*, y el TCP al 502 no conecta en 8 s. Necesita la
  VM encendida con la escena en marcha. Comando:
  `python3 tools/sonda_modbus.py --host 100.116.150.89 --puerto 502 vigila -s 180 --discretas 0:14 --entrada 0:1 --json datos/vigila_azure.json`
- Opción B (Parallels en esta Mac): todavía no existe.
- Mientras tanto, los números de partida son los de la orden: ida y vuelta
  mín. 205 / mediana 753 / p95 1890 / máx. 4420 ms y ~1 FPS.

## R2. Mapa real (PUERTA ARI R0 abierta)

### Qué se hizo

- `config/mapa_registros_fio.json`: las 9 etiquetas conocidas de Sorting by
  Weight (`at_scale_entry`, `at_scale_exit`, `at_left_entry`, `at_right_entry`,
  `weight`, `load_scale`, `send_left`, `send_right`, `send_forward`), con
  tabla, tipo y sentido según la orden (sensores digitales → entradas
  discretas, Weight → registro de entrada, salidas digitales → bobinas) y
  **`direccion: null`**. No se inventa ninguna dirección.
- Validador (`tools/mapa_registros.py`): código nuevo `direccion_pendiente`,
  con un mensaje que nombra la PUERTA ARI R0. El mapa real se rechaza con 9
  errores, uno por etiqueta.
- `docs/MAPA_REGISTROS.md` documenta las dos versiones (sustituto y Factory
  I/O) y marca la segunda como rechazada por el validador, con las direcciones
  "pendiente". `A2_MAPA` elige cuál usa Node-RED.
- `pruebas/prueba_mapa.py`: 24 casos (+2: dirección pendiente y "el mapa fio
  se rechaza mientras tenga pendientes; cuando llegue R0 debe pasar").

### Verificación

```
prueba_mapa.py                                       Ran 24 tests ... OK
mapa_registros.py doc --revisa                       al dia
mapa_registros.py valida --mapa config/mapa_registros_fio.json   exit 1, 9 x direccion_pendiente
```

### Bloqueado (PUERTA ARI R0)

- La captura de la ventana del driver con todas las etiquetas y sus
  direcciones. El driver tiene 14 entradas digitales, 11 bobinas, 1 registro de
  entrada y 4 de retención, y solo se conocen 9 nombres.
- Con ella: llenar direcciones y las etiquetas que faltan (emisor, bandas,
  tablero), validar, correr `vigila` (cada sensor cambia en su dirección al
  pasar una caja) y `escribe` (cada bobina y cada registro de retención mueve
  lo que su nombre dice).
- La unidad de `weight` está por confirmar con `vigila` (provisional: 0 a 10 V
  × 100).

## R3. Cliente y sustituto para el desviador

### Qué se hizo

- `config/planta_a2.json` gana `actuador: "empujador"` y `roles` (los nombres de
  C4). `config/planta_desviador.json` es el del desviador:
  - `actuador: "desviador"`, con `roles` (entrada `at_scale_entry`,
    fin de báscula `at_scale_exit`, peso `weight`, sin velocidad, emisor y dos
    bandas);
  - tres clases por peso (light ≤ 8.5 kg → `send_left` / `at_left_entry`,
    medium ≤ 11.5 → `send_forward` / `at_forward_entry`, heavy → `send_right` /
    `at_right_entry`);
  - bandas fijas de 0.2 m/s y escenarios `local`, `azure_medido_24oct` y
    `local_1fps`.

  `A2_PLANTA_CONFIG` elige cuál.
- **A2-Planta, por roles.** Ninguna función nombra etiquetas: `26` resuelve los
  roles y comprueba que estén en el mapa. `27`, `28`, `29`, `30` y `31` usan
  `S.roles`.
  - **Desviador:** la caja entra a la FIFO con el flanco de `entrada` y se pesa
    entre la bajada de `entrada` y la subida de `fin_bascula` (se retiene la
    última de 3 lecturas dentro de 0.03 V; si no, la más alta). Al llegar a
    `fin_bascula` se clasifica y se mandan las ruedas: primero se apagan las
    otras salidas y luego se enciende la suya. Se confirma con el sensor de su
    salida. Un sensor que confirma una caja que esperaba otra salida cuenta como
    `desvio_erroneo`. Sin confirmación en `timeout_confirmacion_s`, la caja se
    da por perdida.
  - **Secuencia segura armada desde los roles:** con empujador, `vel_banda_V=0`
    → `emisor_on=0` → `alimentacion_on=0`; con desviador,
    `emitter=0` → `entry_conveyor=0` → `load_scale=0`.
  - `paso_caja` lleva `destino` y conteos por destino (`por_destino`).
- **Bandas de velocidad fija.** `limites_planta.py` y `26` solo comprueban si
  la velocidad fija cumple, y el intervalo de `vel_banda_V` queda en `null`.
  El comando `velocidad` da 422 `velocidad_no_aplica`, y marcha no pide
  consigna. Si no es factible, el cliente sigue sondeando, dice
  `factible: false` con sus problemas en el estado, y marcha da 409.
- **El refresco de la escena entra en T_ef:**
  `max(sondeo, peticiones × rtt, refresco) + holgura`, con `A2_REFRESCO_MS`.
  `lecturas_para_cambio` se configura por escenario (`A2_LECTURAS_PARA_CAMBIO`).
- **Sustituto con la escena del desviador** (`escena: "desviador"` en
  `config/sustituto_desviador.json`, mapa `config/mapa_registros_desviador.json`
  con los nombres de la escena y direcciones de la simulación). Tiene tres ramas,
  báscula, sensor de entrada por salida, bandas fijas y `refresco_s` para
  publicar un cuadro cada tanto, como Factory I/O a 1 FPS.
- `21_carga_mapa.js` ya no exige los nombres de C4; cada pestaña comprueba lo
  suyo.
- **Firebase:** la rama `proceso` acepta `destino` con valores cerrados
  (`salida|rechazo|left|right|forward`), solo en registros de caja.
  Reglas en el emulador: 32/32 (+4 casos de `destino`). `prepara.sh` se corrió
  de nuevo, así que **el archivo a publicar en P1 ya incluye `destino`**.
- `pruebas/prueba_desviador.py`: `corrida`, `seguro`, `control` y
  `factibilidad` (sin argumentos corre las tres rápidas).

### Verificación

```
prueba_desviador.py corrida --cajas 200 (local)     12 correctas, 0 fallidas
  1186 s; sustituto 200 cajas {left 54, forward 104, right 42} = cliente por destino
  entran 200, salen 200; perdidas 0, fantasmas 0, desvios erroneos 0
  masa: peor 0.088 kg; lecturas minimas por pulso: 8 en los cinco sensores
  periodo efectivo: p50 242, p95 268, max 423 ms
prueba_desviador.py (seguro + control + factibilidad)  19 correctas, 0 fallidas
prueba_planta.py corrida --escenario local --cajas 30  11 correctas, 0 fallidas (empujador, regresion)
bateria.sh                                             FIN: 0 fallidas
  sustituto 20/20, sonda 44/44, seguridad 10/10, seguro 25/25, control 5/5,
  nube 16/16, vigila 12/12, desviador 19/19, prueba.sh 26/26
prueba_reglas_proceso.py --emulador                    32 casos, 0 discrepancias
prueba_reglas.py (A1)                                  50 casos, 0 discrepancias
```

- **Control:** con las ruedas forzadas a la izquierda por fuera del cliente,
  las 6 cajas salieron por la izquierda y el cliente marcó exactamente los 5
  desvíos erróneos (las que no eran de esa clase). El balance cierra: 6 entran,
  6 salen y los conteos por destino dicen dónde fueron de verdad.
- **Seguro:** en el cable, al arrancar y al reconectar, `emitter=0`,
  `entry_conveyor=0` y `load_scale=0`, en ese orden.
- **Factibilidad:** con el escenario medido el 24 oct (500 ms, rtt 1890 ms,
  1 FPS), T_ef = 7610 ms, factible false; el cliente sigue sondeando y marcha da
  409.

### Lo que dicen los límites para la escena real

| Escenario | T_ef | 3 lecturas | Sensor tapado 2.0 s (0.4 m a 0.2 m/s) |
|---|---|---|---|
| local, 250 ms, sin refresco | 300 ms | 0.90 s | cumple |
| Azure medido (500 ms, rtt p95 1890 ms, 1 FPS) | 7610 ms | 22.8 s | **no cumple** |
| local a 1 FPS (opción B si Parallels también va a 1 FPS) | 1050 ms | 3.15 s | **no cumple** |

**Con la escena a 1 FPS no hay forma de ver cada caja 3 veces a 0.2 m/s, ni
siquiera sin latencia.** La opción B solo sirve si Parallels da al menos unos
5 FPS (T_ef ≤ 650 ms → 1.95 s). `lecturas_para_cambio = 1` acepta un cambio con
una sola lectura (los sensores de Factory I/O no rebotan), pero no cambia la
cuenta de 3 lecturas, y con 1 FPS una caja puede pasar en solo 2 cuadros:
riesgo de perder cajas sin que el antirrebote lo note. Los números reales salen
de `vigila` (R1).

### Pendiente o bloqueado

- **Umbrales de clase reales:** salen de los pesos que muestre `vigila` contra
  la escena (R1, bloqueado: VM offline). Los de hoy salen de la distribución de
  masas del sustituto.
- **Mapa real y roles reales (R0):** etiquetas del emisor, de las bandas y, si
  existe, del sensor de la salida de frente. Si la salida de frente no tiene
  sensor, `confirma: null`: la caja se da por buena sin confirmación (se cuenta
  en `sin_confirmar`).
- **Contadores o luces del tablero:** no hay ninguno en las 9 etiquetas
  conocidas. Cuando R0 diga cuáles son, se agregan como roles.

## C6. HMI con Dashboard 2.0

### Qué se hizo

- Pestaña **`A2 · HMI (Dashboard 2.0)`**: `ui-base` en `/dashboard`, página
  `/dashboard/a2` (*Weight sorting station*), un `ui-template` con un
  componente Vue (`node-red/hmi/a2_hmi.vue`, todo en inglés) que pinta:
  - comunicación con la planta (Online / NO COMMUNICATION / Reconnecting),
    con sondeo, rtt previsto y peor espacio entre lecturas;
  - línea (Running / Stopped), actuador y emisor;
  - factibilidad de los límites con sus problemas;
  - botones Start, Stop y Emitter ON/OFF, y consigna de velocidad **solo si
    hay banda variable** (acotada a 0 o [vel_min_V, vel_max_V]);
  - cajas clasificadas, por minuto, entradas, perdidas, conteo por destino,
    desvíos erróneos y la masa y el destino de la última caja;
  - el último registro aceptado por Firebase (o que `A2_NUBE` está apagado);
  - el último diagnóstico (C7) con su botón *Request diagnosis*;
  - la última telemetría del ESP32 de la Actividad 1, si su CSV de hoy tiene
    menos de 60 s (se lee el archivo, no se tocan sus pestañas).
- `35_hmi_estado.js`, cada 0.5 s: junta `global.a2_planta_resumen`,
  `global.a2_nube_resumen` y `global.a2_diag_ultimo`.
- `36_hmi_comando.js` y los nodos `link`: el botón llega a
  **`30_planta_comando.js`**, la misma función y los mismos códigos que
  `POST /a2/planta/comando`. Esa función ganó una salida para la respuesta
  interna, y la respuesta (200, 409 o 422 con su motivo) vuelve a la página
  y se ve en un recuadro rojo con su explicación.
- `pruebas/socketio_min.py`: cliente mínimo de socket.io v4 por polling.
  `pruebas/prueba_hmi.py` lo usa para hablar con la página por el mismo camino
  que el navegador (`widget-action` para los botones, `msg-input` para lo que
  pinta).
- `prueba_seguridad.py`: los casos del dashboard ya corren (había `ui-base`).

### Verificación

```
prueba_hmi.py        25 correctas, 0 fallidas
  empujador: /dashboard/a2 200, por la IP de Tailscale de esta Mac (100.81.236.34) 200;
  Start con consigna 0 -> 422 en pantalla; 9 V -> 422; 3 V, Start, Emitter ON -> 200 y el
  sustituto recibe vel 3 V, alimentacion 1, emisor 1; desconexion forzada -> NO COMMUNICATION
  en 2.0 s (< timeout_com_ms + 1 s = 3.0 s); Start sin comunicacion -> 409 en pantalla;
  al volver la red, Online y Stopped.
  desviador: actuador y bandas fijas, conteo left/forward/right, consigna -> 422
  velocidad_no_aplica, Start -> 200, una caja clasificada con su masa (10.24 kg -> forward).
prueba_seguridad.py  14 correctas, 0 fallidas: /dashboard 301 -> por tunel 403; /dashboard/a2 200 -> 403;
                     socket.io polling 200 con sid -> 403; websocket por tunel 403
prueba.sh            26 correctas, 0 fallidas
A1                   42 nodos identicos al primer commit
```

### Fallas encontradas durante el paso

| Síntoma | Causa | Corrección |
|---|---|---|
| Los botones no producían respuesta | Dashboard 2.0 reescribe `msg.topic` con el `topic` del widget (`appendTopic`); sin configurar queda `undefined`, y el filtro por `topic: "comando"` lo descartaba | Ni la página ni las funciones dependen de `topic`: se distingue por la forma del payload (`accion`, `ready`, `codigo`) |
| Con `topic` configurado en el widget, el estado dejó de reconocerse | el mismo `appendTopic` también reescribe lo que entra a la página | el mismo arreglo |
| La desconexión se veía en 3.0 s contra 3.0 s | la HMI refrescaba cada 1 s, encima del perro guardián de 2 s | refresco cada 0.5 s: ahora 2.0 s |
| `GET /dashboard` daba 301 en la prueba de seguridad | redirige a la página; la prueba esperaba 200 | se prueban `/dashboard` (301) y `/dashboard/a2` (200) |

### Bloqueado (PUERTA ARI)

- **Abrir la página desde OTRO equipo de la tailnet** (el iPhone o la MacBook,
  que aparecen en `tailscale status`) y mover el sustituto con sus botones. La
  prueba automática solo puede abrirla por la IP de Tailscale de esta misma Mac
  (200). URL: `http://100.81.236.34:1881/dashboard/a2`.

## C7. Diagnóstico con Gemini (deseable)

### Qué se hizo

- Pestaña **`A2 · Diagnostico (Gemini)`**, aparte de la de la Actividad 1, que
  no se toca. Disparo bajo demanda desde la HMI (*Request diagnosis*) y
  periódico cada 60 min, este último **solo con la línea en marcha**. El
  diagnóstico es un consejo: nada en la pestaña escribe en la planta.
- `37_diag_arma.js`: el prompt, en inglés, lleva el estado de la planta:
  actuador, línea, tiempo en marcha, cajas por minuto, clasificadas, perdidas,
  desviadas, conteo por destino, las últimas 12 masas con su media y su sd, la
  banda y la factibilidad. Si está corriendo, agrega la telemetría del ESP32.
  `responseSchema` con `enum` para `nivel_estimado` y `accion_codigo`. **Con
  banda fija, `reducir_velocidad` no se ofrece** (ni en el texto ni en el
  esquema).
- Frenos de consumo (hallazgos 3.2 y 3.3): tope propio `A2_DIAG_MAX_DIA` = 15;
  limitador de 1 por minuto (`A2_DIAG_POR_MINUTO` solo para pruebas);
  `maxOutputTokens` 2048 y `thinkingBudget` 0.
- `38_diag_valida.js`: **validación estricta, sin modo degradado.** Exige
  HTTP 200, JSON, `finishReason` STOP y exactamente los campos pedidos, con
  `valor_pct` solo con `reducir_velocidad`, entero de 0 a 30. Lo que no cumple
  queda en `$DATOS_DIR/a2_diagnosticos_DIA.csv` como `fallo` con su motivo, y
  `global.a2_diag_ultimo` (lo que pinta la HMI) no cambia.
- `pruebas/simulador.py`: si el esquema trae `nivel_estimado`, contesta en el
  formato de A2, válido o en una de 7 variantes inválidas. La Actividad 1 no
  cambia (`prueba.sh` 26/26).

### Verificación

```
prueba_diagnostico_a2.py          18 correctas, 0 fallidas (Gemini simulado, sin cuota)
  valido -> en la pagina; 8 invalidos (nivel, accion, pct fuera, pct de mas, falta campo,
  campo extra, texto no JSON, cuerpo no JSON) -> fallo con su motivo y la pagina sigue
  con el anterior; banda variable: reducir_velocidad 10 % valido; tope diario de 10:
  la undecima no consulta; periodico: no consulta con la linea detenida, si en marcha;
  banda fija: reducir_velocidad -> accion_invalida
prueba_diagnostico_a2.py --real   1 consulta real: valido, normal / mantener, 13 099 ms, 408 tokens
```

Texto del diagnóstico real (24 oct, desviador, 3 cajas): *"The 3-way wheel
diverter is operating normally with 3 boxes sorted and 0 lost or misrouted. The
mass mean is 10.79 kg with a standard deviation of 1.12 kg. Timing limits are
feasible and communication is stable after 24 seconds of operation."*

Esa corrida real salió marcada como falla (1 de 2) solo porque la prueba
esperaba la fila del CSV 10 s y Gemini tardó 13.1 s. La fila dice `valido`. Se
alargó la espera de la prueba real a 60 s y no se repitió la consulta, para no
gastar cuota.

### Fallas encontradas durante el paso

- Con `A2_DIAG_POR_MINUTO=60`, el limitador descartaba la mitad de las
  peticiones de la prueba (una por segundo). La prueba usa 600.
- El disparo periódico justo después de *marcha* leía el resumen de antes. La
  prueba espera a que el estado diga `en_marcha`.

## C8. Gráfica (deseable)

### Qué se hizo

- `web/proceso.html` (en inglés): dos gráficas de Google Charts con el
  listener `onValue` de Firebase, igual que la página de la Actividad 1. Una es
  la masa por caja con una serie por destino (Left / Forward / Right, o Exit /
  Rejected con el empujador), y la otra las cajas por minuto. Arriba, las cajas
  registradas, las cajas en el último minuto, la última caja (kg → destino) y el
  estado de la línea. Lee `limitToLast(300)` de
  `/plantas/{planta}/proceso` con la cuenta del **visor**.
- La configuración sale de `web/config_a2.js`, que genera
  `tools/genera_config_web.py` desde `.env` y **no se versiona** (`.gitignore`):
  así la página nueva no mete credenciales al repositorio (regla 4). La
  corre `demo_a2.sh`. Se sirve igual que la de la Actividad 1: `http.server`
  sobre `web/`, puerto 8123.
- Modo `?emulador=1` para la prueba (emuladores de RTDB y Auth).
- `pruebas/prueba_grafica.py`:
  - levanta los emuladores de RTDB y Auth con cuentas creadas en el emulador de
    Auth y **las reglas del repo** con sus UID;
  - corre Node-RED con el sustituto (desviador) y A2-Nube escribiendo en el
    emulador;
  - abre la página en Chrome sin cabeza, que `pruebas/cdp_mira.mjs` (Node 22,
    WebSocket nativo, protocolo de DevTools) observa: estado de la página cada
    5 s, navegaciones y una captura.

### Verificación (parcial)

```
prueba_grafica.py   6 correctas, 1 fallida
  OK  con las reglas del repo, un anonimo no lee proceso
  OK  la pagina inicio sesion como visor y lee sin error
  OK  las cajas subieron durante la corrida (1 -> 15), con 20 actualizaciones del listener
  OK  sin recargar: 0 navegaciones despues de conectarse
  FALLA al final la pagina tiene las mismas cajas que el emulador (15 = 16)
```

Muestras: t+0 s 0 cajas, t+20 2, t+40 5, t+60 9, t+80 12. Captura al final:
`docs/img/grafica_a2_emulador.png`. Esa captura, tomada después de la última
muestra, **ya muestra 16 cajas, las mismas del emulador**: la falla es de
sincronía de la prueba. La última muestra se toma antes de apagar el emisor y
todavía entra una caja después. No es un defecto de la página.

**Por qué quedó parcial:** fue la tercera corrida fallida de la verificación,
tras dos correcciones (una limpieza que mataba al propio proceso con
`lsof -ti`, y la lectura final del emulador con `?auth=owner` en vez de la
cabecera `Bearer owner`). La regla 2 de la fase 2 pide detenerse ahí.

### Pendiente

- Corregir la prueba: apagar el emisor, esperar a que el sustituto saque todas
  las cajas y entonces tomar una última muestra de la página y compararla.
- Las etiquetas del eje de tiempo de *Boxes per minute* se repiten (cosmético).
- Contra la base real, después de P1: `./demo_a2.sh` y abrir
  `http://localhost:8123/proceso.html`.

## C9. Corrida instrumentada (versión mínima)

### Qué se hizo

- `docs/INSTRUMENTACION_A2.md`: definiciones escritas **antes de medir** del
  periodo efectivo del sondeo y su variación, de la latencia de la lectura
  Modbus a la escritura en Firebase y de la completitud de cajas, con sus
  fuentes y lo que cada cifra incluye y no incluye.
- A2-Planta escribe `$DATOS_DIR/a2_sondeo_DIA.csv`, una línea por ciclo, en
  tandas de 20.
- `tools/exporta_corrida.py --rama proceso`: exporta la rama `proceso`
  (`tipo` caja o latido). Sin `--rama` hace lo de siempre (telemetría de la A1).
- `tools/analiza_corrida.py --a2 ... --sondeo ... --eventos ... [--sustituto]`:
  las tres cifras y la tabla en Markdown. Sin `--a2`, lo de la A1 (comprobado
  sobre un CSV de ingesta de `prueba.sh`).
- `pruebas/prueba_instrumentacion_a2.py [--minutos N]`: corrida con el
  desviador y A2-Nube escribiendo en el simulador, exportación, análisis y
  **recálculo por un segundo camino** (estadística en vivo de A2-Planta, CSV de
  A2-Nube, registro del sustituto).

### Verificación

```
prueba_instrumentacion_a2.py --minutos 10    6 correctas, 0 fallidas
  periodo efectivo   n 2458, mediana 242 ms, p95 268 ms, max 282 ms, media 250.0 ± 12.7 ms (en vivo: 250.0)
  latencia           n 103, mediana 243 ms, p95 272.7 ms, max 311 ms (CSV de A2-Nube: mediana 243.0)
  completitud        103 / 103 = 100 % (sustituto: 103 cajas fuera de la linea)
```

Tabla: `docs/corrida_a2_ensayo.md`.

**Primera corrida de 10 min: 5/6.** La completitud dio 103 en Firebase y en el
cliente contra 102 en el sustituto: la prueba cortó cuando la cola del cliente
se vació, con la última caja ya confirmada pero todavía en su rama. Ahora
espera a que el sustituto saque todas. Con esa corrección, 6/6.

### Bloqueado

- **La corrida de 10 min en `planta_01`** (escritura autorizada en la base real)
  necesita P1 (reglas publicadas y `A2_NUBE=1`) y la planta elegida (R1). Con
  las dos:
  ```bash
  ./demo_a2.sh                       # planta elegida en .env
  # Start + Emitter ON en la HMI, 10 minutos, Stop
  python3 tools/exporta_corrida.py --rama proceso --desde <inicio> --hasta <fin> --salida datos/proceso_c9.csv
  python3 tools/analiza_corrida.py --a2 datos/proceso_c9.csv --sondeo datos/a2_sondeo_<dia>.csv \
      --eventos datos/a2_planta_eventos.jsonl --desde <inicio> --hasta <fin> --md docs/corrida_a2.md
  ```

## D. Demostración

### Qué se hizo

- **`demo_a2.sh`**, un solo comando. Primero revisa:
  1. límites factibles con el sondeo, el rtt y el refresco configurados;
  2. que el Modbus conteste: con Factory I/O, antes de arrancar; con el
     sustituto, después;
  3. que Firebase dé sesión al ingestor;
  4. cuánta cuota de Gemini queda hoy, con el contador local, sin gastar una
     petición.

  Luego arranca Node-RED (`arranca.sh`) y la página (8123), genera
  `web/config_a2.js` y espera a que A2-Planta quede en `ok`. Imprime las URL de
  la HMI (local y de Tailscale), de la gráfica, del editor y del guion.
  `--revisa` solo revisa y `--apaga` baja todo. La planta se elige en `.env`,
  nunca en el código.
- `arranca.sh` y `demo_a2.sh` aceptan `ENV_ARCHIVO` (por omisión `.env`). El
  ensayo lo usa para no gastar cuota de Gemini ni leer la base real: los flujos
  de la Actividad 1 arrancan con el `.env` real y su `inject` de diagnóstico
  consultaría Gemini a los 20 s.
- **`docs/DEMO_A2.md`**, en inglés: la lista técnica en el orden del video
  (arquitectura, Factory I/O, HMI con marcha y paro, cajas clasificadas,
  registros en Firebase, gráfica en vivo, diagnóstico, estado seguro con
  desconexión y recuperación), cada punto con su comando o acción. La
  desconexión usa `proxy_retardo.py --rtt-ms 0` como interruptor.
- **`pruebas/bateria.sh`** (desde el paso S): todas las rápidas, una tras otra,
  con su código de salida en un resumen. Se niega a correr si un puerto está
  ocupado.
- **`pruebas/ensayo_demo.py`**: recorre `DEMO_A2.md` en orden con la planta
  sustituta (desviador), los mismos comandos del documento y la HMI por su
  socket.io. Los pasos que dependen de una puerta de Ari se reportan
  **BLOQUEADO**, no OK.

### Verificación

```
ensayo_demo.py   19 correctas, 0 fallidas, 3 BLOQUEADOS
  0  demo_a2.sh --revisa: limites factibles, sesion de Firebase, cuota 15 de 15
  1  demo_a2.sh: Node-RED, Modbus del sustituto por el proxy, A2-Planta ok/desviador/factible, URL impresas; 7 pestanas
  2  BLOQ Factory I/O real (R0, R1)
  3  HMI: Online/Stopped, Start 200, Emitter ON 200, consigna con banda fija -> 422 en pantalla
  4  vigila ve los sensores; la HMI cuenta 5 cajas por destino, 0 perdidas
  5  la HMI dice que la nube esta apagada; BLOQ registros en Firebase (P1)
  6  /proceso.html 200; BLOQ grafica con datos reales (P1; probada contra el emulador en C8)
  7  sin llave, el boton no consulta y la HMI no muestra nada invalido
  8  desconexion: NO COMMUNICATION en 2.5 s, Start 409, Online/Stopped sin reanudar sola,
     escrituras seguras emitter, entry_conveyor, load_scale, Start vuelve a funcionar
  9  demo_a2.sh --apaga libera el 1881 y el 8123
```

Batería completa al cerrar la fase (`bateria.sh --con-emulador`): **0 fallidas**.
Mapa, límites, sustituto 20/20, sonda 44/44, seguridad 14/14, seguro 25/25,
control 5/5, nube 16/16, vigila 12/12, desviador 19/19, HMI 25/25,
diagnóstico 18/18, instrumentación 6/6, `prueba.sh` 26/26, reglas de la A1 50/50
y de `proceso` 32/32 en el emulador.

Dos fallas encontradas por el ensayo y corregidas: las rutas con espacio sin
comillas en el archivo de variables del propio ensayo (Node-RED no arrancaba),
y que `demo_a2.sh` consultaba el estado de A2-Planta antes de que cargara su
configuración (falso "A2-Planta no contesta"). Ahora espera hasta 20 s a que
diga `ok`.

### Bloqueado

- Los pasos 2, 5 y 6 del guion con la planta y la base reales: PUERTAS ARI
  R0, R1 y P1.

---

# PUERTA ARI R0 abierta: Factory I/O en Parallels (24 oct 2026)

Ari eligió la opción B: Factory I/O en Parallels, `10.211.55.3:502`, unidad 1,
escena Sorting by Weight en Play (captura del driver en
`docs/capturas/driver_fio_parallels.png`). En `.env`: `A2_MODBUS_HOST=10.211.55.3`,
`A2_MODBUS_PUERTO=502`, `A2_MODBUS_UNIDAD=1`, `A2_SUSTITUTO=0`, y `A2_MAPA` /
`A2_PLANTA_CONFIG` apuntando a los archivos `_fio` (sin eso, Node-RED habría
hablado con la escena real usando el mapa del sustituto: direcciones distintas).

**Red local de macOS.** `/usr/bin/python3` y el Python de Homebrew reciben
`EHOSTUNREACH` hacia `10.211.55.3` (permiso de "Red local" de macOS); `node` y
`nc` sí llegan. Mientras Ari no le dé ese permiso a Python, las herramientas en
Python van por un relevo TCP en Node: `node pruebas/relevo.mjs 5031 10.211.55.3 502`
y `--puerto 5031`. Node-RED se conecta directo. `demo_a2.sh --revisa` usa la sonda
en Python: con la planta real fallará hasta dar el permiso o usar el relevo.

## R1 con la planta real (vigila 3 min, cajas pasando)

```
rtt (mide)         mediana 1.4 ms, p95 4.1 ms, sin fallas
refresco escena    mediana 33 ms (~30 FPS), mínimo 20 ms   (no el ~1 FPS de Azure)
cajas              59 en 3 min con las bandas encendidas con `escribe`
```

- **Normalmente cerrados, confirmados con vigila**: `at_exit_left`, `at_exit_front`,
  `at_exit_right` están en 1 en reposo y bajan a 0 de 0.6 a 1.8 s cuando sale una
  caja. Se marcan `nc: true` en el mapa.
- `stop_button` y `emergency_stop` se quedan en 1 todo el tiempo sin presionarse:
  consistente con NC, y así quedan marcados; la confirmación final necesita que
  alguien los presione en la escena (**Ari**).
- `at_scale_entry` pasa casi todo el tiempo en 1 (las cajas se forman en fila):
  hueco mínimo 0.56 s, intervalo mediano 2.9 s.

## R2 con el mapa real

`config/mapa_registros_fio.json`: 31 etiquetas con las direcciones de Ari (16
entradas discretas, `weight` en el registro de entrada 0 con escala 100, 11
bobinas, 3 contadores). El validador ahora acepta escala 1 para enteros (los
contadores del tablero viajan sin escalar); `prueba_mapa.py` 26/26 (2 casos
nuevos). `docs/MAPA_REGISTROS.md` regenerado.

`pruebas/prueba_fio.py` (contra la escena, ~3 min): **17 correctas, 2 fallidas**.

- Correctas: vigila ve cambiar cada sensor de cajas en su dirección;
  `entry_conveyor 0` detiene la entrada y `1` la reanuda; luces y contadores se
  escriben y se leen de vuelta; `weight` es de solo lectura; `send_forward` y
  `send_right` mueven cajas a su salida.
- **Fallidas**: solo 4 de 9 cajas salen por donde se mandó, y `send_left` nunca
  llevó una caja a la salida izquierda.
- Intentos: (1) ruedas sostenidas: 1 a 3 de 12 cajas toman la rama; (2) orden en
  el flanco de `at_scale_exit`, destino confirmado por la salida NC: 4/9. Se detuvo
  por la regla de dos correcciones. Hipótesis: con las cajas en fila, la siguiente
  empuja a la anterior a través del clasificador antes de que las ruedas cambien;
  el pesaje detenido (abajo) separa las cajas y debería resolverlo. También
  `at_forward_entry` lo pisan cajas que no van de frente, así que el destino real
  se confirma con las salidas NC, no con las entradas de rama.

## R3: umbrales y factibilidad con la escena real

**Pesaje.** Con la banda en marcha el peso nunca se asienta. Deteniendo
`entry_conveyor` y `load_scale` se asienta en 0.5 a 0.8 s. 20 pesos asentados
(V): 1.49, 1.5, 3.11, 3.99, 3.99, 4.0, 4.85, 4.99, 4.99, 5.0, 5.0, 5.17, 5.47,
5.965, 6.5, 7.49, 7.5, 7.83, 9.99, 10.0 (dispersión en la ventana: mediana
0.02 V, máxima 1.29 V). Umbrales en `config/planta_fio.json`: **light ≤ 4.5 V →
left, medium ≤ 7.0 V → forward, heavy → right** (huecos entre grupos: 4.0–4.85
y 6.5–7.49).

**Factibilidad.** Las bandas son de velocidad fija y la escena no dice su
largo, así que los sensores van con banda `"medida"`: los tiempos mínimos de
encendido y apagado observados en R1 (`tools/limites_planta.py` y
`26_planta_config.js`, la misma regla en los dos). Con sondeo 100 ms, rtt 5 ms
y refresco 33 ms: T_ef 150 ms, t_min 0.45 s. **No factible**:

```
at_right_entry   encendido 0.23 s, apagado 0.23 s   (< 0.45)
at_scale         apagado 0.43 s
at_scale_exit    apagado 0.43 s
```

Esos mínimos son de la escena sin control (cajas en fila, empujándose). El
cliente contra la escena real lo confirma: `com ok`, actuador desviador, la
secuencia segura escribe las 5 bandas al conectar, rtt de Node-RED 8 ms, y
**`marcha` → 409 `limites_no_factibles`** con esas tres líneas. Es el
comportamiento correcto: no arranca una línea que no puede seguir.

Regresión después de los cambios: `prueba_planta.py seguro` 25/25,
`prueba_desviador.py factibilidad` 4/4, `prueba_mapa.py` 26/26.

## Lo que falta (lo que quedó al cerrar el commit `1166262`)

Los puntos 1, 2 y 4 se hicieron en la sección siguiente. Quedan el 3 (botones,
luces, contadores) y el 5 (de Ari).

## Pesaje detenido y ruedas con motriz: A2-Planta controla la escena

### Lo que se aprendió de la escena (prototipos en Python, una caja a la vez)

- **Las ruedas necesitan motriz.** `send_forward` hace girar las ruedas;
  `send_left` y `send_right` solo las orientan. Con `send_right` sola la caja se
  queda parada sobre el desviador; con `send_left` o `send_right` puesta antes
  de que llegue, sin `send_forward`, la caja sale de frente. Con
  `send_forward + send_left` (o `+ send_right`) puestas antes de soltar la caja:
  13 de 15 cajas por su salida; las 2 restantes eran cajas que habían quedado
  paradas sobre el desviador al final de la corrida anterior (con las ruedas
  apagadas, ahí se quedan) y tomaron la primera orden. De ahí la purga al
  arrancar.
- **Factory I/O no contesta peticiones que llegan juntas.** Tres peticiones en
  un mismo paquete TCP: ninguna respuesta (ni la primera); dos en paquetes
  separados: las dos. Node-RED mandaba las escrituras de un mismo ciclo juntas:
  la primera pasaba y las demás vencían a 1.5 s. El sustituto (jsmodbus) sí
  las encola, por eso no se vio antes.
- **Las cajas se forman pegadas** en la banda de entrada: `at_scale_entry` no
  baja entre una y otra, así que no sirve para contar cajas.

### Qué se hizo (todo se enciende desde `config/planta_fio.json`)

| Opción | Qué hace |
|---|---|
| `modbus_una_peticion: true` | una sola petición Modbus en vuelo: las escrituras van a una cola (`S.cola_esc`) y salen de una en una al confirmarse la anterior (`29_planta_escritura.js`); no se lee con una escritura en vuelo ni se escribe con una lectura en curso |
| `desviador.motriz: "send_forward"` | la motriz se enciende junto con la salida de la clase; se apaga al liberar |
| `desviador.purga_ms: 2500` | al dar `marcha`, la motriz sola 2.5 s: lo que estaba parado en el desviador sale de frente y se cuenta como `purgadas`, no como fantasma |
| `roles.en_bascula: "at_scale"` y `bascula.pesaje_detenido` | la caja nace al subir `at_scale`; se para `entry_conveyor` y, cuando la caja anterior ya dejó la báscula (baja `at_scale_exit`), `load_scale`; tras 800 ms se lee el peso hasta que 3 lecturas seguidas caben en 0.05 V (o 2.5 s, y se marca no estable), mediana, clase, ruedas, y se suelta `load_scale`; `entry_conveyor` vuelve al bajar `at_scale_exit` |
| adopción | una caja que ya estaba en la báscula al dar `marcha` no da flanco: se adopta y se pesa |
| secuencia segura | con desviador, al final también las ruedas y la motriz apagadas |

Sin estas opciones (sustituto, empujador) el comportamiento es el de antes.

### Verificación: `prueba_fio.py cliente` contra la escena real

Node-RED va directo a `10.211.55.3:502`; la prueba solo lee (por el relevo) y
es el oráculo: vacía el desviador y las bandas de salida antes de arrancar;
toma el peso de cada caja en el instante en que el cliente la suelta (sube
`load_scale` con la caja en `at_scale`) y el destino real de la salida NC que
baja; compara en orden con lo que reporta el cliente.

| Corrida | Resultado | Qué falló | Corrección |
|---|---|---|---|
| 1 | 5/9, 0 cajas | escrituras en ráfaga: 9 vencidas | una petición a la vez |
| 2 | 5/9, 1 caja | cajas pegadas y cajas ya en la línea al arrancar: fantasmas | la caja nace en `at_scale`; adopción; vaciado previo en la prueba |
| 3 | 8/9, 53/53 por su salida | 2 pesos ±0.1 V: el cliente los marcó no estables | seguir leyendo hasta 3 lecturas en banda (tope 2.5 s) |
| 4 | **9/9**, 50/50 | — | se agregan al oráculo los tiempos bajo control |
| 5 | 8/11, 46 | una caja perdida: dos cajas pegadas en la báscula; al parar por la segunda, la primera se atoró entre la báscula y el desviador | (1ª) correr la báscula 300 ms más para separarlas |
| 6 | 8/11 | peor: la caja pasa de `at_scale` y titila en `at_scale_exit` | (2ª) parar la báscula solo cuando la anterior la dejó |
| 7 | **11/11**, 53/53 | — | |
| 8 | 10/11, 50/50 | una caja oscilando (33 muestras): 8.41 vs 8.08 V, misma clase | el oráculo compara el peso solo en cajas que vio quietas sus últimos 0.3 s, y la clase en todas |
| 9 | 10/12, 51/51 | `at_right_entry` encendido 0.25 s una vez (< t_min 0.30 s) | **se detiene aquí** (regla de dos correcciones) |

En las corridas 7 a 9: **154 cajas, cada una por la salida de su peso**, el
cliente reporta el mismo destino que la salida real caja por caja, 0 desvíos
erróneos, 0 pérdidas, 0 fantasmas, y vio cada pulso en 5 o más lecturas
(antirrebote de 2). Pesos del cliente = pesos del oráculo en todas las cajas
quietas.

### Factibilidad con los tiempos bajo control (el peor de las corridas 7 y 9)

```
at_scale_entry    encendido 0.41  apagado 0.55        at_left_entry     0.46 / 1.94
at_scale          encendido 1.39  apagado 0.46        at_forward_entry  0.39 / 7.29
at_scale_exit     encendido 0.51  apagado 1.62        at_right_entry    0.25 / 1.54
```

Con `sondeo 50 ms` (T_ef = max(50, 4×5, 33) + 50 = 100 ms, t_min 0.30 s):
**no factible por `at_right_entry` (0.25 s)**. Con 30 ms (T_ef 83 ms, t_min
0.249 s) sí, por 1 ms: no es margen. Con 100 ms, no. Se dejó la configuración
con lo medido, así que hoy `marcha` contra la escena responde 409. No se cambió
el sondeo ni el criterio para que pase: eso le toca a Ari (ver abajo).

Nota: el criterio que pidió Ari en C3 es "cada sensor activo al menos 3
periodos de sondeo con la latencia": 3 × (50 + 5) ms = 0.165 s, y eso sí se
cumple con 0.25 s. Lo que no se cumple es el criterio más estricto que se fijó
en C4, que suma el refresco de la escena y una holgura de 50 ms.

### Decisión pendiente (Ari)

1. Sondeo de 30 ms (factible por 1 ms), o
2. quitar la holgura del cálculo cuando el refresco ya está medido (T_ef 50 ms,
   t_min 0.15 s con 50 ms de sondeo), o
3. dejarlo como está y que la demostración use la escena con `marcha` rechazada.

### Pendiente

- Rol de los botones (Stop y E-stop NC), luces y contadores por destino.
- Ari: presionar Stop y Emergency stop en la escena para confirmar NC; permiso
  de "Red local" para Python (o seguir con `pruebas/relevo.mjs`).
- La corrida de 200 cajas contra la escena, cuando se decida lo de arriba.

## Decisión de Ari: T_ef con lo medido (24 oct 2026)

Ari eligió la opción 2 con un ajuste: cuando el refresco está medido, el
margen fijo de 50 ms se reemplaza por lo medido. Se mantienen 3 periodos y el
antirrebote de 2.

```
T_ef = max(p95 del periodo efectivo del sondeo,
           (lecturas + escrituras por ciclo) x p95 de la ida y vuelta,
           p95 del refresco de la escena)            t_min = 3 x T_ef
```

La misma regla está en `tools/limites_planta.py` (`t_efectivo`, `medido_vale`)
y en `26_planta_config.js`. Las medidas van en el bloque `medido` de la
configuración y **solo valen con el mismo sondeo con que se tomaron** y sin rtt
ni refresco dados a mano (`A2_RTT_PREVISTO_MS`, `A2_REFRESCO_MS`); si no, vuelve
la fórmula con holgura. `limites.t_ef_origen` dice cuál se usó (`medido` u
`holgura`).

Medidas en `config/planta_fio.json` (sondeo 50 ms):

| Medida | p95 | De dónde |
|---|---|---|
| periodo efectivo del sondeo | 55 ms | CSV de sondeo de `prueba_fio.py cliente`, 4699 ciclos con carga y una petición a la vez (p50 53, p99 83, máx 720) |
| ida y vuelta | 9 ms | el mismo CSV, ciclos de una sola petición (p50 3 ms); × 4 peticiones = 36 ms |
| refresco de la escena | **pendiente** | la escena quedó detenida (Running = 0) antes de medirlo |

Con el refresco pendiente el bloque no vale y `limites_planta.py` sigue
diciendo no factible con holgura (T_ef 100 ms). Con un refresco ≤ 55 ms,
T_ef = 55 ms y t_min = 0.165 s.

## Tablero de la escena (punto 3)

`config/planta_fio.json` → `tablero`: Start (`start_button`), Stop
(`stop_button`, NC) y Emergency stop (`emergency_stop`, NC); luces y
contadores.

- **Start** (flanco al presionar) → `marcha`; **Stop** (NC: presionar = baja a
  0) → `paro`. Van por `30_planta_comando.js` (salida nueva 4 de
  `28_planta_lectura.js`), así valen las mismas reglas que en el POST y la HMI
  (409 sin límites factibles, etc.); el evento `comando` dice `origen: tablero`.
- **Emergency stop** actúa por **nivel** (también si ya estaba presionado al
  arrancar): línea `emergencia`, se vacía la cola de escrituras, se apaga todo
  (emisor, bandas, ruedas y motriz), las cajas en tramo se descartan
  (`descartadas_emergencia`, entra en el balance), `marcha` → 409
  `paro_de_emergencia` y Stop no la saca. Al soltarlo queda **detenida** hasta
  el siguiente Start. La HMI dice "Emergency stop".
- **Luces**: `start_light` = en marcha, `stop_light` = no en marcha,
  `reset_light` = emergencia. **Contadores**: `left_count`, `forward_count`,
  `right_count` = cajas por destino. Se escriben solo al cambiar; al reconectar
  se reescriben; si una escritura falla se reintenta.

Verificación sin la escena, `pruebas/prueba_tablero.py` (en la batería):
**25/25**. Un servidor Modbus mínimo con las direcciones del mapa real hace de
escena: T_ef medido igual en Python y Node-RED (55 ms, t_min 0.165 s) y con
otro sondeo vuelve la holgura (150 ms = 150 ms); luces; Start y Stop; E-stop
(todo apagado, 409, Stop y Start no sacan, al soltar detenida, Start arranca);
4 cajas pesadas → contadores 2/1/1; E-stop presionado al arrancar → emergencia.
Regresión: desviador 19/19, HMI 25/25, seguro 25/25.

Falta con la escena: refresco medido, la corrida de 200 cajas y la
confirmación NC de Stop y E-stop presionándolos (Ari).

## Refresco medido, Reset/Run de la escena y corrida de 200 cajas (24 oct 2026)

### p95 del refresco y T_ef medido

Registro `weight` leído cada 1.8 ms durante 90 s con cajas pasando: 2393
intervalos entre cambios dentro de tramos de cambio continuo; **p95 36.6 ms**
(p50 33.4, p99 132.7). Con eso el bloque `medido` de `planta_fio.json` vale:
T_ef = max(55, 4 × 9, 36.6) = **55 ms**, t_min = **0.165 s**, factible.
`limites_planta.py --sondeo … --medido` aplica la misma regla en modo manual;
`demo_a2.sh` la usa salvo que `A2_RTT_PREVISTO_MS` o `A2_REFRESCO_MS` vengan a mano.

### FACTORY I/O Reset y Run (bobinas 11 y 12)

Agregadas al mapa real (`fio_reset`, `fio_run`). Probadas por Modbus:
**Reset = 1** detiene y limpia la escena (Running baja a 0); **Run actúa por
nivel**: 1 = corre, 0 = se detiene. `tools/reinicia_escena.mjs` (Node: llega
directo a la VM) hace bandas y ruedas en 0 → Reset 1 → Reset 0 → espera a que
báscula, desviador, ramas y salidas estén libres y el peso < 0.2 V → **Run = 1
y se deja en 1**, comprobando Running sostenido 1 s. Lo usan `prueba_fio.py`
(modos mapa, cliente y tablero), `corrida_c9_real.py` y `demo_a2.sh` al
arrancar con Factory I/O.

Falla propia encontrada en el camino: la primera versión mandaba un flanco de
Run (0 → 1 → 0); la escena arrancaba y se volvía a parar al bajar Run, y la
primera corrida de 200 cajas esperó 22 min sin ninguna caja. Ahora Run se queda
en 1 y la prueba corta si `fio_running` está en 0 más de 2 s.

### Cajas que se cayeron fuera de la línea

En los registros de las 7 corridas controladas (`prueba_fio.py cliente`, 9:52
a 10:22) **ninguna caja soltada por el cliente se perdió**: en cada corrida la
diferencia entre cajas soltadas y salidas NC es exactamente el número de cajas
confirmadas en los últimos 5 s antes del `paro`, que apaga las bandas con esas
cajas todavía en su rama (1, 2, 1, 1 y 2). Las caídas tienen que venir de
antes de que el cliente controlara la escena:

- **pruebas de R2 y prototipos** con las ruedas mal usadas: `send_left` o
  `send_right` sostenidas sin la motriz (las ruedas giran de lado sin
  avanzar; una caja se quedó 55 s atorada y la siguiente la empujó), y ruedas
  apagadas con cajas pasando (la caja se queda sobre el desviador y la que
  viene detrás la empuja);
- **corrida 5**: una caja atorada entre la báscula y el desviador cuando la
  báscula se paró con ella a medio camino (corregido: la báscula para solo
  cuando la caja anterior ya la dejó);
- **cambio de ruedas con una caja todavía encima**: en 6 de las 7 corridas, las
  ruedas cambiaron de dirección 0.42 a 0.75 s después de confirmar la caja
  anterior, con su cola aún sobre el desviador (encendido de 0.4 a 0.6 s). En
  esas corridas las cajas igual llegaron a su salida, pero es el mecanismo para
  lanzar una de lado. **Corregido**: ni se suelta la siguiente caja ni se apagan
  las ruedas hasta que el sensor de rama de la anterior baja (si no baja en 3 s,
  se libera con el evento `sensor_de_rama_sin_bajar`).

Para detectarlo de aquí en adelante, el oráculo exige que toda caja soltada más
de 12 s antes del `paro` aparezca en una salida NC, y la escena se reinicia
antes de cada corrida (no quedan cajas en el piso ni paradas en el desviador).

### Corrida de 200 cajas contra la escena (`prueba_fio.py cliente --cajas 200`)

Primera corrida completa (17:47): el cliente cumplió todo (200 cajas, cada una
por la salida que eligió, 0 desvíos, 0 pérdidas, ninguna caída, pulsos de rama
en ≥ 8 lecturas), pero **el oráculo no vio la suelta de la caja 99**: exigía
ver `load_scale` apagada 0.7 s y la ventana fue de 0.92 s; un tropiezo de su
lectura por el relevo la dejó fuera y desde ahí sus pesos quedaron corridos un
lugar (137 de 200 coincidencias). Corrección del oráculo: la suelta se cuenta en
cualquier flanco de `load_scale` tras 0.5 s apagada, con o sin peso leído, y
guarda sus datos (`oraculo.json`).

Segunda corrida (19:01), **16/17**:

```
oraculo: 201 cajas soltadas, 200 salidas NC; cliente: 200 pasos
por destino: left 115, forward 41, right 44
OK  200 de 200 por la salida de su peso (0 sin peso del oraculo)
OK  el cliente reporta el mismo destino que la salida real, caja por caja (200)
OK  pesos iguales (+-0.05 V) en las 183 cajas quietas; misma clase en las 200
OK  ninguna caja se cae ni se atora: 198 soltadas > 12 s antes del paro, 200 salidas
OK  T_ef de lo medido (55 ms)
OK  cada pulso de rama visto en >= 3 lecturas: right 6, left 8, forward 7
OK  0 desvios erroneos, 0 perdidas, 0 fantasmas
FALLA bajo control, todo sensor dura >= t_min: at_right_entry encendido 0.03 s, apagado 0.02 s
```

Los criterios de la verificación (cada pulso de rama en ≥ 3 lecturas, 0
desvíos, 0 pérdidas) **se cumplen**. La única falla es del chequeo extra del
oráculo: vio `at_right_entry` titilar dos veces (46 pulsos para 44 cajas a la
derecha), 20-30 ms, menos que una lectura de 50 ms. El antirrebote de 2
lecturas los descartó (0 fantasmas, 44 cajas contadas a la derecha). No se
cambió el oráculo para que pase; queda como hallazgo: los sensores de rama
rebotan y el antirrebote es necesario.

## C5b cerrado: reglas publicadas en la base real (24 oct 2026)

Ari publicó `firebase/database.rules.generado.json` (generado a las 11:23 UTC,
con `destino`). Después de la corrida de 200 cajas:

```
$ python3 pruebas/prueba_reglas_proceso.py --planta planta_99      -> exit 0
  == Lectura ==
    ok anonimo lee proceso                              esperado=NIEGA   real=NIEGA
    ok visor lee proceso                                esperado=PERMITE real=PERMITE
    ok ingestor lee proceso                             esperado=PERMITE real=PERMITE
  
  == Escritura ==
    ok anonimo da de alta                               esperado=NIEGA   real=NIEGA
    ok visor da de alta                                 esperado=NIEGA   real=NIEGA
    ok ingestor: registro de caja                       esperado=PERMITE real=PERMITE
    ok ingestor: latido sin caja_masa_kg                esperado=PERMITE real=PERMITE
    ok ingestor: POST (clave push), como Node-RED       esperado=PERMITE real=PERMITE
  
  == Append-only ==
    ok sobrescribe un registro                          esperado=NIEGA   real=NIEGA
    ok parcha un campo                                  esperado=NIEGA   real=NIEGA
    ok borra un registro                                esperado=NIEGA   real=NIEGA
    ok borra la rama proceso                            esperado=NIEGA   real=NIEGA
  
  == Esquema ==
    ok campo fuera del esquema                          esperado=NIEGA   real=NIEGA
    ok falta estado_linea                               esperado=NIEGA   real=NIEGA
    ok falta cajas_acumuladas                           esperado=NIEGA   real=NIEGA
    ok vel_banda_V como texto                           esperado=NIEGA   real=NIEGA
    ok vel_banda_V 10.01                                esperado=NIEGA   real=NIEGA
    ok vel_banda_V -10 (limite)                         esperado=PERMITE real=PERMITE
    ok peso_V negativo                                  esperado=NIEGA   real=NIEGA
    ok caja_masa_kg 20.01                               esperado=NIEGA   real=NIEGA
    ok cajas_acumuladas no entero                       esperado=NIEGA   real=NIEGA
    ok estado_linea inventado                           esperado=NIEGA   real=NIEGA
    ok ts_origen con offset local                       esperado=NIEGA   real=NIEGA
    ok ts_escritura con Z                               esperado=NIEGA   real=NIEGA
    ok destino left (desviador)                         esperado=PERMITE real=PERMITE
    ok destino rechazo (empujador)                      esperado=PERMITE real=PERMITE
    ok destino inventado                                esperado=NIEGA   real=NIEGA
    ok destino numerico                                 esperado=NIEGA   real=NIEGA
  
  == plantaId ==
    ok planta fantasma                                  esperado=NIEGA   real=NIEGA
    ok planta_7                                         esperado=NIEGA   real=NIEGA
  
  30 casos, 0 discrepancias (base real, planta_99)

$ python3 pruebas/prueba_reglas_real.py --planta planta_99         -> exit 0
  (sesiones de ingestor y visor por Identity Toolkit; UID omitidos aqui)
  == Lectura ==
    ok anonimo lee telemetria                           esperado=NIEGA   real=NIEGA
    ok visor lee telemetria                             esperado=PERMITE real=PERMITE
    ok visor lee diagnosticos                           esperado=PERMITE real=PERMITE
    ok ingestor lee telemetria                          esperado=PERMITE real=PERMITE
    ok visor lista /plantas                             esperado=NIEGA   real=NIEGA
    ok visor lee materiales                             esperado=NIEGA   real=NIEGA
    ok visor lee la planta completa                     esperado=NIEGA   real=NIEGA
    ok visor lee la raiz                                esperado=NIEGA   real=NIEGA
  == Escritura ==
    ok anonimo da de alta                               esperado=NIEGA   real=NIEGA
    ok visor da de alta                                 esperado=NIEGA   real=NIEGA
    ok ingestor da de alta valida                       esperado=PERMITE real=PERMITE
    ok ingestor hace push de diagnostico                esperado=PERMITE real=PERMITE
  == Append-only ==
    ok sobrescribe registro existente                   esperado=NIEGA   real=NIEGA
    ok parcha un campo existente                        esperado=NIEGA   real=NIEGA
    ok borra un registro                                esperado=NIEGA   real=NIEGA
    ok borra la rama telemetria                         esperado=NIEGA   real=NIEGA
    ok borra la planta entera                           esperado=NIEGA   real=NIEGA
    ok multi-ruta de puras altas nuevas                 esperado=PERMITE real=PERMITE
    ok multi-ruta que toca historia vieja               esperado=NIEGA   real=NIEGA
    ok multi-ruta mezclando alta nueva e historia       esperado=NIEGA   real=NIEGA
  == Esquema ==
    ok campo fuera del esquema                          esperado=NIEGA   real=NIEGA
    ok falta campo obligatorio                          esperado=NIEGA   real=NIEGA
    ok temperatura como texto                           esperado=NIEGA   real=NIEGA
    ok ciclos no entero                                 esperado=NIEGA   real=NIEGA
    ok ciclos negativo                                  esperado=NIEGA   real=NIEGA
    ok diagnostico con texto vacio                      esperado=NIEGA   real=NIEGA
    ok diagnostico con latencia negativa                esperado=NIEGA   real=NIEGA
  == plantaId ==
    ok planta conforme                                  esperado=PERMITE real=PERMITE
    ok fantasma (no conforme)                           esperado=NIEGA   real=NIEGA
    ok planta_7 (un solo digito)                        esperado=NIEGA   real=NIEGA
    ok planta_007 (tres digitos)                        esperado=NIEGA   real=NIEGA
  == Marcas ==
    ok ts_origen en UTC con Z                           esperado=PERMITE real=PERMITE
    ok ts_origen con offset local                       esperado=NIEGA   real=NIEGA
    ok ts_escritura con offset -06:00                   esperado=PERMITE real=PERMITE
    ok ts_escritura con Z (Node-RED en UTC)             esperado=NIEGA   real=NIEGA
    ok ts sin milisegundos                              esperado=NIEGA   real=NIEGA
    ok diagnostico con ts en Z                          esperado=NIEGA   real=NIEGA
  == Rangos ==
    ok temperatura 80.0 (limite)                        esperado=PERMITE real=PERMITE
    ok temperatura 80.1                                 esperado=NIEGA   real=NIEGA
    ok temperatura -40.0 (limite)                       esperado=PERMITE real=PERMITE
    ok temperatura 120                                  esperado=NIEGA   real=NIEGA
    ok vibracion 100.0 (limite)                         esperado=PERMITE real=PERMITE
    ok vibracion 100.1                                  esperado=NIEGA   real=NIEGA
    ok vibracion 900                                    esperado=NIEGA   real=NIEGA
  == Holgura restante ==
    ok ts_escritura anterior a ts_origen                esperado=PERMITE real=PERMITE
    ok registro fechado en 1999                         esperado=PERMITE real=PERMITE
  
  46 casos, 0 discrepancias
```

Las dos pasan: **30/30** en la rama `proceso` y **46/46** en las reglas de la
Actividad 1, contra la base real. `A2_NUBE=1` puesto en `.env`. **C5b
cerrado**; lo que dependía de la base real (C8 con datos reales, C9 en
`planta_01`, el paso 5 del guion) queda desbloqueado.

## C9 y C8 con la base real, ensayo completo contra la escena (24 oct 2026, noche)

### Tablero: confirmación NC sin presionar

Se armaron tres ventanas de vigilancia (`prueba_fio.py tablero`) y ninguna vio
un cambio en Start, Stop o Emergency stop. Después se encontró que la
simulación de Factory I/O estaba **congelada**: contestaba Modbus, Running = 1
y obedecía Reset/Run, pero ninguna caja avanzaba (0 cambios de sensor en 10 s
con las bandas encendidas), así que los botones tampoco podían cambiar sus
entradas. Ari hizo Stop + Play en la escena y volvió a moverse; el reinicio
por Modbus no la congela (probado: 24 cambios en 10 s después de Reset + Run).
Por decisión de Ari no se repitió la prueba de botones: **Stop y Emergency stop
quedan como NC por su estado en reposo** (1 sin presionar, como las tres
salidas, que sí se vieron bajar con cajas), y la lógica del tablero queda
respaldada por `prueba_tablero.py` 25/25 contra la escena Modbus falsa con el
mapa real. Pendiente: presionarlos en la escena con `prueba_fio.py tablero`.

`corrida_c9_real.py` ahora corta si no entra ninguna caja en el primer minuto
(la primera C9 se detuvo a los 3 min por este congelamiento).

### C9: 10 minutos contra Factory I/O escribiendo en `planta_01`

`pruebas/corrida_c9_real.py` (reinicia la escena, Node-RED con el mapa y el
cliente de Factory I/O, `A2_NUBE=1`, `PLANTA_ID=planta_01`, credenciales del
`.env` que no se imprimen; Gemini no se consulta). Ventana
`2026-10-25T01:22:42.619Z` a `01:32:44.851Z`. **11/11**:

| Cifra | n | Mediana | p95 | Máx | Media ± sd |
|---|---|---|---|---|---|
| Periodo efectivo del sondeo | 11983 | 52 ms | 54 ms | 668 ms | 50.1 ± 9.6 ms |
| Latencia lectura → escritura (cajas) | 127 | 52 ms | 55 ms | 57 ms | 49.7 ± 8.2 ms |
| Completitud | 127 / 127 | 100 % | | | |

127 cajas (left 86, forward 31, right 10), 10 latidos, 0 desvíos, 0 pérdidas,
0 fantasmas. La latencia es la de `docs/INSTRUMENTACION_A2.md`: de la lectura
Modbus a la escritura que emite Node-RED (antirrebote y cola de A2-Nube); **no
incluye** el viaje a Firebase. Reporte: `docs/corrida_a2.md`.

### C8: la gráfica con datos reales

Durante la misma corrida, `web/proceso.html` en Chrome sin cabeza con el visor
real: inició sesión y leyó sin error, subió de 1 a 127 cajas con **0
navegaciones** (sin recargar) y terminó con las 127 cajas que hay en Firebase.
Captura: `docs/img/grafica_a2_real.png`. Cierra la verificación parcial 6/7 de
C8 (la comparación final ahora espera a que la cola de A2-Nube se vacíe).

### Ensayo completo de `docs/DEMO_A2.md` contra la escena real

`pruebas/ensayo_demo.py --real`: Factory I/O por el relevo `127.0.0.1:5030`
(interruptor del paso 8), Firebase real con `A2_NUBE=1`, gráfica con el visor
real, Gemini sin llave (no gasta cuota). Primera corrida: se cayó en el paso 7
porque la sesión socket.io con la que la prueba hace de HMI no se sondeó
durante el minuto de la gráfica y el servidor la cerró (400); se abre otra,
como al recargar la página. Segunda corrida: **21/21, 0 bloqueados**:

```
0  demo_a2.sh --revisa: limites factibles (T_ef medido), Modbus contesta, sesion de Firebase
1  demo_a2.sh: reinicia la escena por Modbus, Node-RED, A2-Planta ok, URL impresas
2  A2-Planta: com ok, desviador, factible con T_ef medido 55 ms
3  HMI Online/Stopped; Start 200; Emitter ON 422 sin_emisor (la escena emite sola);
   consigna con bandas fijas 422 velocidad_no_aplica
4  vigila ve los sensores; la HMI cuenta cajas por destino, 0 perdidas
5  la HMI muestra la nube encendida y el ultimo registro aceptado en Firebase
6  /proceso.html 200; la grafica real sube sin recargar (157 -> 168 cajas)
7  sin llave, el boton de diagnostico no consulta
8  relevo cortado: NO COMMUNICATION en 2.5 s, Start 409; al volver Online/Stopped,
   8 escrituras seguras (5 bandas y 3 ruedas) en orden, Start vuelve a funcionar
9  demo_a2.sh --apaga libera el 1881 y el 8123
```

`docs/DEMO_A2.md` se actualizó para la escena real: `planta_fio.json`, el
relevo de Node como interruptor y para la sonda, el reinicio por Modbus, el
tablero de la escena, sin emisor y 8 escrituras seguras.

### Batería al cerrar

`bateria.sh --con-emulador` (19:05): todo pasa salvo `mapa`, que falló porque
`docs/MAPA_REGISTROS.md` no se regeneró tras corregir la descripción de
`fio_run`; regenerada, `prueba_mapa.py` 26/26. Las demás: sustituto 20/20,
sonda 43/43, seguridad 14/14, seguro 25/25, control 5/5, nube 16/16, vigila
12/12, desviador 19/19, HMI 25/25, diagnóstico 18/18, instrumentación 6/6,
tablero 25/25, `prueba.sh` 26/26, reglas A1 50/50 y `proceso` 32/32.

### Lo que queda pendiente

1. **Ari**: presionar Stop y Emergency stop en la escena para confirmar NC
   (`prueba_fio.py tablero`, ~2 min, con la simulación avanzando).
2. **Ari**: abrir la HMI desde otro equipo de la tailnet (C6).
3. **Ari (opcional)**: permiso de "Red local" de macOS para Python; mientras
   tanto, el relevo de Node (`pruebas/relevo.mjs`) lo cubre.
4. El diagnóstico con Gemini no se repitió en el ensayo para no gastar cuota;
   la consulta real se probó en C7.

### Pendiente de prueba: commit `3d8a37e`

`3d8a37e` (en `corrida_c9_real.py`, el perfil de Chrome y la captura van a una
carpeta temporal fuera del repo) solo pasó `ast.parse`. No se corrió a
propósito: cada corrida escribe en `planta_01` de la base real, que es
append-only. **Queda probado en la siguiente corrida de C9.**

# Fase 3 (`docs/ORDEN_A2_FASE_3.md`, 10 nov 2026; sesión del 11 nov 2026)

Puertas al iniciar: **M0 abierta** (Ari confirmó el dimensionamiento de la
sección 8 de `docs/PARAMETROS_MATERIALES.md`). Cerradas: V0, A1, P2, U0 y T0.
`A2_NUBE=0` en `.env` desde el inicio de la fase; nada escribe en `planta_01`.
Después, el 11 nov: A1 y P2 abiertas (secciones S2 y E1); **V0 y U0 abiertas**
(Factory I/O 2.5.10 reinstalado, Sorting by Weight cargada, driver conectado
en 10.211.55.3:502; U0 con el archivo de escena guardado). T0 sigue cerrada.

| Paso | Prioridad | Estado | Respaldo |
|---|---|---|---|
| Inicio | | commit `b23428b`: orden y `PARAMETROS_MATERIALES.md` | |
| S2. Autenticación del editor | esencial | **cerrado** (PUERTA ARI A1 abierta el 11 nov) | `prueba_seguridad.py` 55/55 (51/51 sin capa 3); batería completa 0 fallidas, `prueba.sh` 26/26 |
| E1. Estado `emergencia` en A2-Nube | esencial | **cerrado** (PUERTA ARI P2 abierta el 11 nov: base real 31/31 y A1 46/46 en `planta_99`) | sin el cambio: `prueba_nube.py emergencia` 1/5 y reglas 1 discrepancia; con él 5/5, reglas `proceso` 33/33, A1 50/50; batería 0 fallidas |
| E2. Latido en reposo | deseable | **cerrado** | `prueba_nube.py reposo` 7/7 (cambio de estado < 1 s); `prueba_nube.py` 28/28; batería 0 fallidas |
| M1. Modelo de materiales | esencial (M0 abierta) | **cerrado** | `prueba_materiales.py modelo` 31/31 (Anexo B, fronteras, rigidez, galga, ruido, 10000 pasos JS = Python, validador con mutación, recalcula 429 cajas); batería 0 fallidas |
| M2. Pestaña A2 · Materiales | esencial | **cerrado** | `prueba_materiales.py flujo` 32/32 (recálculo, separación, persistencia, umbrales, `sobre`, galga, A1 idéntica); batería 0 fallidas |
| T. Tablero en la escena | esencial, ESCENA | **cerrado** (PUERTA T0 abierta el 11 nov) | `prueba_fio.py tablero` 9/9: Stop y Emergency stop NC al presionarlos, Start NA, luces y bandas; mapa actualizado; batería 0 fallidas |
| U. Unidad de la báscula | esencial (U0 lo confirma) | **cerrado** (PUERTA ARI U0 abierta el 11 nov: escena guardada, `20 Kg Max.`) | `prueba_tablero.py fronteras` 9/9 (4.49/4.51/6.99/7.01 V, mismos destinos con 1 y 2 kg/V; control con umbrales viejos falla); batería 0 fallidas, `tablero` 34/34, `prueba.sh` 26/26 |
| L. Corridas largas | esencial, ESCENA | **cerrado** (no decide nada; las decisiones quedan para Ari con `docs/corrida_L.md`) | L1 y L2 de 600 cajas: `prueba_fio.py cliente` 17/17 cada una, sin desvíos, pérdidas ni fantasmas; `analiza_masas.py --verifica` coincide con las cifras del 25 oct y los tres valores p; batería 0 fallidas |
| R. Redimensionamiento (orden de cierre) | esencial (M0 revisada) | **cerrado** | `prueba_materiales.py modelo` 42/42 (Anexo B de la orden de cierre en JS y Python, recálculo de L1 y L2) y `flujo` 36/36 (incluye estado con `cfg_version` 1); segunda batería 0 fallidas (la primera, 1 falla intermitente de `/comms` en `seguridad`), `prueba.sh` 26/26 |
| M3. Materiales contra la escena | esencial, ESCENA | **cerrado** (configuración versión 2) | L1 y L2 recalculados = Anexo B; M1 en vivo: verdad = recálculo (peor 0), D no decrece, pasos sobre sin cambio de D, HMI en los pasos 264/420/489 del recálculo, oráculo 17/17; captura en `docs/img/hmi_materiales.png`; batería 0 fallidas |

## S2. Autenticación del editor

### Qué se hizo

- **Documentación revisada antes de escribir**: página "Securing Node-RED" y
  "Admin API: OAuth" de nodered.org (formato `adminAuth` con `type:
  "credentials"`, `users: [{username, password (bcrypt), permissions: "*"}]`;
  token por `POST /auth/token` con `client_id=node-red-admin`,
  `grant_type=password`, `scope=*`; revocación por `POST /auth/revoke`). La
  página no documenta cómo deshabilitar la API; se comprobó en el código de
  Node-RED 5.0.9 instalado: `httpAdminRoot: false` hace que `red.js` no monte
  ni el editor ni la API (`Admin UI disabled` en el registro), y
  `@node-red/editor-api/lib/auth/users.js` compara con `@node-rs/bcrypt` (y si
  no está, `bcryptjs`).
- `node-red/settings.js`: con `NODE_RED_ADMIN_USER` y un `NODE_RED_ADMIN_HASH`
  con formato bcrypt, `adminAuth` con ese único usuario y permisos `*`. Si
  falta alguna o el hash no tiene formato bcrypt, `httpAdminRoot: false`, y el
  registro dice por qué (`[a2-seguridad] editor y API de administracion
  DESHABILITADOS (falta ...)`). No hay contraseña por omisión. `/dashboard/a2`,
  `/a2/planta/*` y la ingesta viven en `httpNodeRoot` y no cambian; no se
  agregó `httpNodeAuth`.
- `tools/hash_admin.js` (nuevo): hash bcrypt con la misma biblioteca que el
  Node-RED instalado (se resuelve desde su `red.js`; hoy `@node-rs/bcrypt`),
  costo 10. La contraseña entra por stdin. `--revisa` comprueba el formato y
  `--compara` una contraseña contra un hash.
- `prepara_admin.sh` (nuevo, interactivo): usuario, contraseña dos veces sin
  eco (mínimo 12 caracteres), hash, y escribe o reemplaza las dos variables en
  `.env` de forma atómica conservando los permisos del archivo. El hash va
  entre comillas simples porque lleva `$` y `arranca.sh` carga `.env` con bash.
  No imprime la contraseña ni el hash. `--revisa` dice si existen las dos y si
  el hash tiene formato bcrypt, con código de salida 0 o 1. `ENV_ARCHIVO`
  elige otro archivo (así se probó, sin tocar `.env`). `.env.example` gana los
  dos nombres sin valores.
- **Esperas de arranque** sin la API de administración. Búsqueda propia de
  `/settings` en scripts y pruebas: las cuatro de la orden
  (`demo_a2.sh`, `enciende.sh`, `pruebas/prueba.sh`,
  `pruebas/prueba_sustituto.py`) y ninguna más. La espera nueva pregunta por
  `GET /a2/planta/estado`, la ruta de un nodo `http in`: da 404 hasta que los
  flujos corren y después cualquier otra cosa (200, o 503 sin configuración de
  planta). Es más estricta que la anterior, que solo esperaba al servidor.
  `ps.arranca` ya no hereda `NODE_RED_ADMIN_*` del entorno.
- **Otros usos de la API de administración que la orden no listaba**:
  `POST /inject/<id>` (el botón de los inject es de la API de administración)
  en `pruebas/prueba.sh` (dos veces) y en `pruebas/prueba_diagnostico_a2.py`
  (dos veces). Las dos pruebas generan ahora credenciales desechables
  (`pruebas/admin_desechable.py`: usuario y contraseña aleatorios, hash solo en
  el entorno del Node-RED de la prueba) y mandan el token.
- `pruebas/ensayo_demo.py`: las pestañas salen de `node-red/runtime/flows.json`
  (el archivo con que arranca Node-RED), no de `GET /flows`; y ya no copia
  `NODE_RED_ADMIN_*` del `.env` real a su archivo temporal.
- `arranca.sh` dice "Editor: PROTEGIDO" o "Editor: DESHABILITADO"; `estado.sh`
  lo dice preguntando a `GET /auth/login` con Node-RED arriba (404 =
  deshabilitado) o leyendo `.env` con Node-RED apagado.
- Falla propia encontrada en el camino: `ps.detiene()` mataba todo PID con una
  conexión al 1881, y la prueba de seguridad, con un websocket abierto, se
  mataba a sí misma (exit 143). `detiene` y `puerto_ocupado` ahora solo miran
  al proceso que escucha (`-sTCP:LISTEN`), como ya hacía `demo_a2.sh --apaga`.

### Verificación: `pruebas/prueba_seguridad.py` ampliada

Las líneas que esperaban 200 en `/flows` y `/settings` cambiaron. Parte 1 con
credenciales desechables, parte 2 sin las dos variables, parte 3 sobre el
repositorio. Con `--sin-capa3` y sin credenciales, una ruta que no existe da
404 también por el túnel (no hay middleware de admin que conteste 403); no se
sirve nada, y con la configuración real (capa 3) es 403.

```
$ /usr/bin/python3 -u pruebas/prueba_seguridad.py                -> exit 0
  OK    GET /auth/login anuncia el esquema credentials (sin revelar usuarios)
  OK    27 rutas de la API de administracion sin token -> 401 (leer y escribir flujos, contexto,
        nodos, settings, diagnostics, plugins, inject...)
  OK    POST /flows/state (runtimeState apagado) no existe: 404
  OK    GET /flows con un token inventado -> 401
  OK    los flujos siguen corriendo: el estado de A2-Planta no cambio por los intentos (com ok)
  OK    sin autenticarse, /comms no entrega eventos en 4 s con cambios de estado provocados
        (2 marcos: ['{"auth":"fail"}', 'CERRADO'])
  OK    con un token inventado: auth fail y ningun evento
  OK    con contrasena equivocada no se obtiene token
  OK    con un usuario que no existe no se obtiene token
  OK    con la contrasena correcta se obtiene token
  OK    con ese token GET /flows -> 200 (7 pestanas)
  OK    control: autenticado, /comms dice auth ok y SI entrega eventos (12)
  OK    POST /auth/revoke invalida el token: /flows vuelve a 401
  (tunel, editor protegido: 16 casos, todo 403 salvo la ingesta)
  OK    el registro de Node-RED dice que el editor y la API quedan deshabilitados y por que
  OK    la API de administracion y el editor no se sirven: 11 rutas -> 404
  OK    GET /dashboard/a2 -> 200
  OK    POST /telemetria llega a la ingesta (401 clave_invalida de su validacion)
  OK    con la clave correcta la ingesta valida el cuerpo (400, no 404)
  OK    los flujos corren: A2-Planta en com ok contra el sustituto
  OK    POST /a2/planta/comando responde (200)
  (tunel, sin credenciales: 16 casos, todo 403 salvo la ingesta)
  OK    arbol de trabajo (136 archivos versionados o por versionar): sin hashes bcrypt
  OK    historial desde b23428b (fase 3): sin hashes bcrypt
  OK    historial: ninguna asignacion con valor de NODE_RED_ADMIN_HASH
  === RESULTADO: 55 correctas, 0 fallidas ===

$ /usr/bin/python3 -u pruebas/prueba_seguridad.py --sin-capa3    -> exit 0
  === RESULTADO: 51 correctas, 0 fallidas ===
```

`prepara_admin.sh` contra un archivo temporal (`ENV_ARCHIVO`, nunca `.env`):
`--revisa` sin variables → exit 1; alta → exit 0 y `--revisa` → exit 0;
segunda alta reemplaza las líneas (no las duplica) y conserva el modo 600; el
hash cargado con `. archivo` de bash corresponde a la contraseña
(`hash_admin.js --compara` → 0); contraseñas distintas o de menos de 12
caracteres → exit 1 sin cambiar nada.

Batería completa al cerrar S2 (`SALIDA=$TMPDIR/bat_s2 ./pruebas/bateria.sh --con-emulador`, exit 0):

```
mapa                       exit=0      0s  OK
limites                    exit=0      0s
sustituto_funcional        exit=0     57s  === RESULTADO: 20 correctas, 0 fallidas ===
sonda                      exit=0     31s  === RESULTADO: 43 correctas, 0 fallidas ===
seguridad                  exit=0     12s  === RESULTADO: 55 correctas, 0 fallidas ===
planta_seguro              exit=0     30s  === RESULTADO: 25 correctas, 0 fallidas ===
planta_control             exit=0     63s  === RESULTADO: 5 correctas, 0 fallidas ===
nube                       exit=0     99s  === RESULTADO: 16 correctas, 0 fallidas ===
vigila                     exit=0     51s  === RESULTADO: 12 correctas, 0 fallidas ===
desviador                  exit=0     67s  === RESULTADO: 19 correctas, 0 fallidas ===
hmi                        exit=0     25s  === RESULTADO: 25 correctas, 0 fallidas ===
diagnostico_a2             exit=0     34s  === RESULTADO: 19 correctas, 0 fallidas ===
instrumentacion_a2         exit=0    138s  === RESULTADO: 6 correctas, 0 fallidas ===
tablero                    exit=0     31s  === RESULTADO: 25 correctas, 0 fallidas ===
prueba_sh                  exit=0     58s  === RESULTADO: 26 correctas, 0 fallidas ===
reglas_a1                  exit=0      0s  50 casos, 0 discrepancias
reglas_proceso             exit=0      0s  32 casos, 0 discrepancias (emulador)
FIN: 0 fallidas
```

`prueba.sh` sigue en 26/26 con sus inject por token desechable; el
diagnóstico pasa de 18 a 19 casos (el token desechable es un caso más).

### PUERTA ARI A1 (abierta el 11 nov 2026)

1. Ari corre `./prepara_admin.sh` en la Mac mini y escribe su usuario y su
   contraseña (12 caracteres o más). Claude nunca la conoce.
2. Claude corre `./prepara_admin.sh --revisa` y registra su salida aquí.
3. Ari reinicia Node-RED (`./demo_a2.sh --apaga` y `./demo_a2.sh`, o
   `./apaga.sh` y `./arranca.sh`), abre `http://<mac>:1881/` y comprueba que el
   editor pide usuario y contraseña.

Mientras A1 no se abra, con el `.env` real el editor y la API de
administración quedan **deshabilitados** (Node-RED no los sirve), que es el
estado cerrado que pide la orden.

#### Registro de la apertura (11 nov 2026)

Ari corrió `./prepara_admin.sh` (usuario `ari`) y reinició Node-RED con
`./apaga.sh` y `./arranca.sh`. `arranca.sh` imprimió `Editor: PROTEGIDO con
usuario y contrasena (adminAuth)` y el registro de `settings.js` imprimió
`[a2-seguridad] editor y API de administracion PROTEGIDOS`.

```
$ ./prepara_admin.sh --revisa                                         -> exit 0
  NODE_RED_ADMIN_USER   existe
  NODE_RED_ADMIN_HASH   existe, formato bcrypt
  editor: protegido con usuario y contrasena
$ curl -s http://127.0.0.1:1881/auth/login
{"type":"credentials","prompts":[{"id":"username","type":"text","label":"user.username"},{"id":"password","type":"password","label":"user.password"}]}
$ curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:1881/flows   (sin token)
401
```

Comprobación de Ari en el navegador: `http://localhost:1881` pidió usuario y
contraseña y con ellos entró al editor. **PUERTA A1 abierta.**

## E1. Estado `emergencia` en A2-Nube

### Qué se hizo

Búsqueda propia de los estados de la línea. Enumeran los **valores
permitidos** de `estado_linea`, y ganan `emergencia`:

- `firebase/database.rules.json` (regla `estado_linea` de `proceso`);
- `node-red/funciones/33_nube_valida.js` (la validación local, que descartaba
  todos los latidos con el paro presionado);
- `pruebas/prueba_nube.py` (`esquema_ok`, línea 53).

Las reglas del emulador se generan igual que antes
(`pruebas/emulador/prepara_emulador.py` copia las del repo cambiando los UID):
`diff` contra el repo con UID de prueba, sin diferencias.

Solo **usan** los estados, sin enumerar valores permitidos, y no cambian:
`node-red/hmi/a2_hmi.vue` (muestra la etiqueta que arma
`35_hmi_estado.js`, que ya traducía `emergencia` a "Emergency stop"),
`37_diag_arma.js` (ya traducía a `emergency_stop`), `pruebas/prueba_hmi.py`,
`pruebas/ensayo_demo.py`, `pruebas/prueba_planta.py`,
`pruebas/prueba_desviador.py` y `pruebas/prueba_tablero.py` (comparan con un
valor concreto). `web/proceso.html` solo traducía tres estados; ahora muestra
`emergencia` como `EMERGENCY STOP`.

`pruebas/prueba_reglas_proceso.py` gana el caso "latido con estado_linea
emergencia (E1)" (PERMITE) y conserva "estado_linea inventado" (NIEGA).
`pruebas/prueba_nube.py` gana la sección 4 (`prueba_nube.py emergencia` la
corre sola): la escena Modbus falsa de `prueba_tablero.py` con el mapa real y
el paro presionado, el simulador de Firebase y `A2_NUBE=1`.

### Verificación

Primero **sin el cambio** (`flows.json` de HEAD y reglas viejas):

```
$ /usr/bin/python3 -u pruebas/prueba_nube.py emergencia            -> exit 4
  OK    A2-Planta en ok y la linea en emergencia
  el simulador recibio 0 latidos: []; CSV: [('422', 'valor_fuera_del_esquema'), ('422', 'valor_fuera_del_esquema')]
  FALLA los latidos con estado_linea = emergencia llegan a la base simulada
  FALLA y cumplen el esquema de las reglas
  FALLA el CSV de A2-Nube no registra rechazos (2 filas, todas 201)
  FALLA Node-RED no avisa de registros rechazados
$ python3 pruebas/prueba_reglas_proceso.py --emulador 127.0.0.1:9000 -> exit 1
  !! latido con estado_linea emergencia (E1)          esperado=PERMITE real=NIEGA
  33 casos, 1 discrepancias (emulador)
```

**Con el cambio** (`flows.json` regenerado solo con `33_nube_valida.js`):

```
$ /usr/bin/python3 -u pruebas/prueba_nube.py emergencia            -> exit 0
  OK    A2-Planta en ok y la linea en emergencia
  el simulador recibio 2 latidos: ['emergencia', 'emergencia']; CSV: [('201', 'aceptado'), ('201', 'aceptado')]
  OK    los latidos con estado_linea = emergencia llegan a la base simulada
  OK    y cumplen el esquema de las reglas
  OK    el CSV de A2-Nube no registra rechazos (2 filas, todas 201)
  OK    Node-RED no avisa de registros rechazados
$ python3 pruebas/prueba_reglas_proceso.py --emulador 127.0.0.1:9000 -> exit 0
  ok estado_linea inventado                           esperado=NIEGA   real=NIEGA
  ok latido con estado_linea emergencia (E1)          esperado=PERMITE real=PERMITE
  33 casos, 0 discrepancias (emulador)
$ python3 pruebas/prueba_reglas.py --uid-ingestor UIDING --uid-visor UIDVIS -> exit 0
  50 casos, 0 discrepancias
```

`./firebase/prepara.sh` → exit 0; `firebase/database.rules.generado.json`
escrito el 11 nov 2026 a las 07:22 (hora de la Mac), con `emergencia` y sin
marcadores `__UID`. Está en `.gitignore`, como siempre.

### PUERTA ARI P2 (abierta el 11 nov 2026)

Ari publica `firebase/database.rules.generado.json` en la consola de Firebase
(Realtime Database → Reglas → Publicar). Después Claude corre
`python3 pruebas/prueba_reglas_proceso.py --planta planta_99` y
`python3 pruebas/prueba_reglas_real.py --planta planta_99` y registra su
salida. Hasta entonces la base real sigue con las reglas del 24 oct, que
rechazan `emergencia`; no importa mientras `A2_NUBE=0`.

#### Registro de la apertura (11 nov 2026)

Ari publicó `firebase/database.rules.generado.json` en la consola.

```
$ python3 pruebas/prueba_reglas_proceso.py --planta planta_99      -> exit 0
  ...
  ok latido con estado_linea emergencia (E1)          esperado=PERMITE real=PERMITE
  ok estado_linea inventado                           esperado=NIEGA   real=NIEGA
  ...
31 casos, 0 discrepancias (base real, planta_99)

$ python3 pruebas/prueba_reglas_real.py --planta planta_99         -> exit 0
46 casos, 0 discrepancias
```

Contra la base real son 31 casos y no 33 porque los dos casos de un "tercero
autenticado" solo existen en el emulador (la base real no tiene esa cuenta).
Respecto a la corrida del 24 oct (30 casos) se suma el caso de `emergencia`.
La A1 sigue en 46 casos sin discrepancias. Se escribió solo en `planta_99`;
`planta_01` no se tocó y `A2_NUBE` sigue en 0. **PUERTA P2 abierta.**

Batería completa al cerrar E1 (`bateria.sh --con-emulador`, exit 0): igual
que en S2 salvo `nube` 21/21 (16 + los 5 de la sección 4) y `reglas_proceso`
33 casos, 0 discrepancias. `prueba.sh` 26/26, reglas A1 50/50.

## E2. Latido en reposo (deseable)

### Qué se hizo

- `32_nube_registro.js`: con la línea en marcha, un latido cada `A2_LATIDO_S`
  (60 s por omisión); fuera de marcha y con el mismo `estado_linea` que el
  latido anterior, cada `A2_LATIDO_REPOSO_S` (900 s por omisión); un
  `estado_linea` distinto del último latido produce un latido en el siguiente
  tic de 1 s. El estado comparado es el que va en el registro (`linea` con
  comunicación, o el de la comunicación sin ella), así que una caída de
  comunicación también deja latido inmediato. Mínimo de 5 s en los dos
  periodos, como antes.
- `pruebas/prueba_nube.py`: la sección 1 ya no cuenta latidos totales (los
  cambios de estado agregan latidos inmediatos); mide el periodo mediano entre
  latidos consecutivos en marcha. Sección 5 nueva (`prueba_nube.py reposo` la
  corre sola) con periodos cortos (5 s en marcha, 12 s en reposo).
- `docs/DEMO_A2.md`, `docs/INSTRUMENTACION_A2.md` y `.env.example`
  (`A2_LATIDO_REPOSO_S`) describen el ritmo nuevo. Las cifras de C9 no
  cambian: se midieron con la línea en marcha y solo sobre registros de caja.

### Verificación

```
$ /usr/bin/python3 -u pruebas/prueba_nube.py reposo                  -> exit 0
=== 5. Latido en reposo (E2): marcha 5 s, reposo 12 s ===
  OK    A2-Planta en ok
  latidos (estado, s desde el primero): [('detenida', 0.0), ('detenida', 12.0), ('detenida', 24.0),
    ('detenida', 36.0), ('en_march', 39.0), ('en_march', 44.1), ('en_march', 49.1), ('en_march', 54.1),
    ('en_march', 59.1), ('en_march', 64.1), ('detenida', 66.1), ('detenida', 78.1), ('detenida', 90.1),
    ('detenida', 102.1)]
  OK    detenida antes de marcha: latidos cada 12 s ([12.0, 12.0, 12.0])
  OK    marcha (200): el primer latido en marcha llega 0.83 s despues del cambio (< 2 s)
  OK    en marcha: latidos cada 5 s ([5.0, 5.0, 5.0, 5.0, 5.0])
  OK    paro: el primer latido detenida llega 0.86 s despues del cambio (< 2 s)
  OK    detenida despues del paro: latidos cada 12 s ([12.0, 12.0, 12.0])
  OK    CSV: todos aceptados con 201 (14)
=== RESULTADO: 7 correctas, 0 fallidas ===
```

Con los valores por omisión, los quince días del 24 oct al 8 nov con la línea
detenida habrían dejado unos 1440 latidos (uno cada 15 min) en lugar de 21688.

Primera batería al cerrar E2: `nube` 24/28. Las secciones 2 (permiso negado) y
4 (paro de emergencia) esperaban latidos con la línea detenida al ritmo de
`A2_LATIDO_S`, y con E2 ese ritmo pasó a 900 s. Corrección (primera del paso):
esas secciones fijan `A2_LATIDO_REPOSO_S=LATIDO_S`, que conserva lo que miden;
el reposo largo lo prueba la sección 5. Después, `prueba_nube.py` 28/28 y la
batería completa de nuevo, exit 0: todo igual que en E1 salvo `nube` 28/28.

## M1. Modelo de la capa de materiales (PUERTA ARI M0 abierta)

### Qué se hizo

- `config/materiales.json`: el Anexo A, extraído del bloque JSON de la orden
  sin tocarlo (la prueba lo compara contra la orden, punto 0).
- `node-red/funciones/39_mat_modelo.js`: **el modelo**, como función pura de un
  nodo de función: no usa contexto, archivos ni red; todo entra y sale por
  `msg` (acciones `valida`, `inicial`, `paso`, `punto` y `rigidez`).
  **Decisión (forma de compartir el código):** el archivo de función ejecutado
  por un arnés. `pruebas/arnes_materiales.js` lee ESE archivo y lo ejecuta con
  el mismo envoltorio que Node-RED (`function(msg, node, context, flow, global,
  env, RED)`); si el modelo intentara usar contexto, el arnés lanza un error.
  `construye_flows.py` lo incrusta en `flows.json` como a todas las funciones,
  así que no hay una segunda copia del código fuente. Se descartó cargar un
  módulo desde `settings.js` (`functionGlobalContext`) porque lo publicaría en
  el contexto global, que en M2 debe quedar solo con lo medido.
- Definiciones: las de la orden, una por una (comentario de cabecera del
  archivo). Precisiones de implementación:
  - región por comparación directa de `sigma_max` con
    `[nivel_min_pct/100·σ_uts, nivel_max_pct/100·σ_uts]`, extremos incluidos;
  - la galga usa `d(D)` con D **antes** del paso; el resultado del paso da D
    después y `d = d(D después)`;
  - un paso sin peso numérico no se evalúa, cuenta en `sin_peso` y no consume
    números del generador;
  - el ruido se sortea en todo paso con peso, en las tres regiones, porque la
    galga mide en cada paso;
  - generador por laminado: mulberry32 + Box-Muller de `24_sust_emulador.js`,
    sembrado con `mezcla(semilla + i·0x9E3779B9)` (la mezcla de
    `22_sust_config.js`), i = índice del laminado.
- Validador (en JS y en Python, mismos códigos): `b_no_negativo`,
  `a_no_positivo`, `intervalo_invertido` (mínimo ≥ máximo),
  `umbrales_desordenados` (no 0 < preventiva < crítica < falla),
  `rigidez_no_empieza_en_cero`, `rigidez_D_no_creciente`,
  `rigidez_d_decreciente`, `rigidez_D_fuera_de_rango`, `campo_desconocido`, y
  además `campo_faltante`, `tipo_invalido` y `valor_invalido` (números que
  deben ser positivos, `R_ref` en [0, 1), semilla entera). `msg.apaga` (JS) y
  `--apaga` (Python) apagan reglas, solo para la prueba de mutación.
- `tools/materiales.py` (Python 3.9, sin dependencias), segundo camino escrito
  aparte: `valida`, `referencia` (tabla del Anexo B) y `recalcula --eventos
  --desde --hasta` (eventos `paso_caja` con `ts_salida` en el intervalo, en
  orden de `ts_salida`).

### Verificación

```
$ /usr/bin/python3 tools/materiales.py referencia                    -> exit 0
| peso_V | sigma_max (MPa) | 0:0 region | 0:0 N del ajuste | 0:0 N usado | 0:0 dD | 9:1 region | 9:1 N del ajuste | 9:1 N usado | 9:1 dD |
| 10.000 | 930.0000 | dentro | 26737.4818 | 26737.4818 | 0.09350170 | dentro | 6739167.3880 | 1000000.0000 | 0.00250000 |
| 9.990 | 929.1630 | dentro | 27908.8218 | 27908.8218 | 0.08957741 | dentro | 7186836.1821 | 1000000.0000 | 0.00250000 |
| 9.985 | 928.7445 | dentro | 28514.0098 | 28514.0098 | 0.08767620 | bajo |  |  | 0 |
| 9.980 | 928.3260 | dentro | 29132.6027 | 29132.6027 | 0.08581451 | bajo |  |  | 0 |
| 9.770 | 910.7490 | dentro | 72394.1745 | 72394.1745 | 0.03453317 | bajo |  |  | 0 |
| 9.500 | 888.1500 | dentro | 239519.5143 | 239519.5143 | 0.01043756 | bajo |  |  | 0 |
| 9.400 | 879.7800 | dentro | 375977.3005 | 375977.3005 | 0.00664934 | bajo |  |  | 0 |
| 9.200 | 863.0400 | dentro | 938544.7125 | 938544.7125 | 0.00266370 | bajo |  |  | 0 |
| 9.000 | 846.3000 | dentro | 2385230.7033 | 1000000.0000 | 0.00250000 | bajo |  |  | 0 |
| 8.990 | 845.4630 | bajo |  |  | 0 | bajo |  |  | 0 |
| 7.500 | 720.7500 | bajo |  |  | 0 | bajo |  |  | 0 |
| 5.000 | 511.5000 | bajo |  |  | 0 | bajo |  |  | 0 |
| 1.500 | 218.5500 | bajo |  |  | 0 | bajo |  |  | 0 |
```

Coincide celda por celda con el Anexo B.

```
$ /usr/bin/python3 -u pruebas/prueba_materiales.py modelo            -> exit 0
--- 0. Configuracion ---
  OK    config/materiales.json es valida en Python y en JavaScript
  OK    config/materiales.json es exactamente el Anexo A
--- 1. Tabla del Anexo B (JavaScript y Python) ---
  OK    13 pesos x 2 laminados: sigma_max (rel < 1e-9), N_ajuste, N_usado y dD (rel < 1e-6) y region exacta
--- 2. Carga constante y secuencia mixta ---
  OK    10 pasos de 10.00 V, laminado 0:0: D = 0.93501700 (js 0.93501700, py 0.93501700), D no decrece
  OK    10 pasos de 10.00 V, laminado 9:1: D = 0.02500000 (js 0.02500000, py 0.02500000), D no decrece
  OK    secuencia mixta, laminado 0:0: D = 0.42420258 (js 0.42420258, py 0.42420258), dentro/bajo/sobre (8, 2, 0), D no decrece
  OK    secuencia mixta, laminado 9:1: D = 0.01000000 (js 0.01000000, py 0.01000000), dentro/bajo/sobre (4, 6, 0), D no decrece
--- 3. Fronteras ---
  OK    8.99 V bajo y 9.00 V dentro (con el tope) en 0:0; 9.98 V bajo y 9.99 V dentro en 9:1; a 10.00 V ningun laminado por encima
  OK    a 9.00 V el laminado 0:0 usa el tope de 10^6 ciclos
--- 4. Rigidez interpolada y galga sin ruido ---
  OK    d(D) del Anexo B en 0:0 (7 valores) y 9:1 (6 valores), a 6 decimales, en JS y Python
  OK    galga sin ruido del Anexo B (7 casos) con diferencia < 0.01 ue en JS y Python
--- 5. Ruido de la galga ---
  OK    laminado 0:0: la misma semilla da la misma secuencia (dos corridas JS identicas; JS vs Python max 0.00e+00 ue)
  OK    laminado 0:0: 10000 muestras, media 0.140 ue (|media| < 1) y desviacion 25.106 ue (|sd - 25| < 1)
  OK    laminado 9:1: la misma semilla da la misma secuencia (dos corridas JS identicas; JS vs Python max 9.09e-13 ue)
  OK    laminado 9:1: 10000 muestras, media 0.109 ue (|media| < 1) y desviacion 25.021 ue (|sd - 25| < 1)
  OK    los dos laminados usan generadores distintos (primer ruido distinto)
--- 6. D de JavaScript y Python sobre 10000 pesos con semilla ---
  OK    config del repo: D final igual (rel < 1e-9; peor paso 0.0e+00), mismos conteos, sin_peso 1/1: 0:0 D=107.669, 9:1 D=0.165
  OK    ciclos_por_paso = 1: D final igual (rel < 1e-9; peor paso 0.0e+00), mismos conteos, sin_peso 1/1: 0:0 D=0.0430674, 9:1 D=6.6e-05
--- 7. Validador: cada rechazo con su control y prueba de mutacion ---
  OK    b_no_negativo               rechaza (py y js) y con la regla apagada deja de rechazar
  OK    a_no_positivo               rechaza (py y js) y con la regla apagada deja de rechazar
  OK    intervalo_invertido         rechaza (py y js) y con la regla apagada deja de rechazar
  OK    umbrales_desordenados       rechaza (py y js) y con la regla apagada deja de rechazar
  OK    rigidez_no_empieza_en_cero  rechaza (py y js) y con la regla apagada deja de rechazar
  OK    rigidez_D_no_creciente      rechaza (py y js) y con la regla apagada deja de rechazar
  OK    rigidez_d_decreciente       rechaza (py y js) y con la regla apagada deja de rechazar
  OK    rigidez_D_fuera_de_rango    rechaza (py y js) y con la regla apagada deja de rechazar
  OK    campo_desconocido           rechaza (py y js) y con la regla apagada deja de rechazar   (x3: laminado, galga, raiz)
  OK    control: tools/materiales.py valida acepta el Anexo A (exit 0)
--- 8. recalcula sobre los datos del 25 de octubre ---
    0:0 D=0.54952814 {'dentro': 10, 'bajo': 419, 'sobre': 0}; 9:1 D=0.01250000 {'dentro': 5, 'bajo': 424, 'sobre': 0}
  OK    429 cajas; 0:0 D = 0.54952814 con 10 dentro y 419 bajo; 9:1 D = 0.01250000 con 5 dentro y 424 bajo
=== RESULTADO: 31 correctas, 0 fallidas ===
```

Nota sobre el punto 6: con la configuración del repo y la mitad de los pesos
entre 8.9 y 10 V, D del laminado 0:0 llega a 107.7 (no hay tope en D; la
regla es que nunca decrece). Por eso el punto se repite con
`ciclos_por_paso = 1`, que deja D en 0.043 y prueba la coincidencia con cifras
pequeñas. En los dos casos JS y Python dan el mismo valor en cada uno de los
10000 pasos (peor diferencia relativa 0).

`recalcula` del punto 8 reproduce exactamente las cifras de la orden; el
archivo `datos/a2_planta_eventos.jsonl` existe y no cambió (429 `paso_caja`
en total, los 429 en la ventana).

`pruebas/bateria.sh` gana `materiales_modelo` (2 s). Batería completa al
cerrar M1, exit 0: todo igual que en E2 más `materiales_modelo` 31/31.

## M2. Pestaña A2 · Materiales contra el sustituto

### Qué se hizo

- Pestaña `A2 · Materiales (capa de materiales)` generada por
  `construye_flows.py`, funciones 39 a 42:
  - `40_mat_entrada.js` (libs `fs`): sin `A2_MATERIALES=1` no hace nada (no
    lee ni crea archivos ni manda mensajes). Con la bandera carga
    `A2_MAT_CONFIG` (`arranca.sh` y `demo_a2.sh` ponen `config/materiales.json`),
    la valida con el modelo y carga `$DATOS_DIR/a2_materiales_estado.json`. Si
    ese archivo existe y no se puede leer o no corresponde a la configuración,
    la pestaña **no acumula** y lo dice (estado del nodo, registro, tarjeta de
    la HMI). Un paso a la vez: los `paso_caja` que llegan mientras otro va por
    el modelo esperan en una cola.
  - `39_mat_modelo.js`: el modelo de M1, sin cambios.
  - `41_mat_salida.js` (libs `fs`): escribe `a2_materiales_medido.jsonl` y
    `a2_materiales_verdad.jsonl` por separado (una línea por paso y laminado,
    los campos de la orden más el número de paso en la verdad, para alinear),
    guarda el estado de forma atómica (temporal + rename) y publica en
    `global.a2_mat_medido` solo lo medido (últimos 30 pasos por varilla y los
    conteos `pasos` y `sin_peso`).
  - `42_mat_hmi.js`: arma la tarjeta y la manda por el enlace `a2_mat_hmi` a
    la plantilla de A2-HMI (con cada paso y cada 2 s, para que aparezca al
    recargar la página). La verdad sale de la pestaña solo por ese enlace.
- Entrada: el `link out` `a2_paso_caja` de A2-Planta gana el destino
  `link_mat_paso`. A2-Planta y A2-Nube no cambian.
- HMI: tarjeta `Materials layer`, solo si llega un mensaje de la pestaña (es
  decir, con `A2_MATERIALES=1`): por varilla, vida consumida con un decimal,
  nivel (`normal`, `preventive`, `critical`, `failure`) con color y "changed to
  X at step N", pasos dentro, por debajo y por encima del intervalo, último
  rango de deformación medido, estimación de pasos y tiempo restantes (o `no
  estimate yet` con menos de 100 pasos o sin un paso con daño), y la alerta
  `load above the tested range` con su conteo.
- La pestaña no tiene nodos Modbus ni `http request`: no escribe en la planta,
  en Firebase ni consulta a Gemini. La pestaña de diagnóstico no se tocó.
- `.env.example` gana `A2_MATERIALES` y `A2_MAT_CONFIG`; `pruebas/bateria.sh`
  gana `materiales_flujo`.

### Fallas encontradas durante el paso

1. `process is not defined`: el sandbox de las funciones de Node-RED no expone
   `process`; el nombre del archivo temporal usaba `process.pid`. Ahora usa
   `Date.now()`.
2. La prueba perdía su sesión socket.io de la tarjeta durante las corridas (el
   servidor la cierra si no se sondea); ahora abre otra, como al recargar.
3. Primera corrida completa de la prueba, 30/32: (a) mis masas de prueba
   (media 15 kg) dejaron solo 2 cajas pesadas en 36 y ninguna dentro del
   intervalo del 9:1; son un valor de prueba, no del Anexo, y pasaron a media
   19 kg; (b) la alerta de `sobre` llegó vacía porque la prueba solo leía 3 s
   después de la corrida; ahora espera la tarjeta. Una corrección cada una;
   la segunda corrida pasó completa.

### Verificación: `pruebas/prueba_materiales.py flujo`

Configuraciones de prueba (en el directorio temporal, no en el repo):
sustituto del desviador con emisión cada 3.5-4.0 s y masas normales de media
19 kg (corrida, `sobre`) o de media 23 kg (umbrales); `sigma_ref_MPa = 1100`
para `sobre`. Todo lo demás es `config/materiales.json`.

```
$ /usr/bin/python3 -u pruebas/prueba_materiales.py flujo             -> exit 0
--- 1. Sin A2_MATERIALES ---
  OK    el cliente con desviador conecta (local) y queda en ok
  OK    sin la bandera, la pestana no crea archivos ([])
  OK    y la HMI no recibe la tarjeta (estado de la planta si: True)
--- 2. Corrida contra el sustituto, con un reinicio de Node-RED a media corrida ---
  OK    el cliente con desviador conecta (local) y queda en ok
    primera parte: 18 pasos; Node-RED detenido
  OK    el cliente con desviador conecta (local) y queda en ok
    corrida completa: 36 paso_caja; 0:0 D=1.16098692 {'dentro': 18, 'bajo': 18, 'sobre': 0}; 9:1 D=0.01750000 {'dentro': 7, 'bajo': 29, 'sobre': 0}
  OK    la verdad coincide con tools/materiales.py recalcula: D por laminado (rel < 1e-9), conteos exactos, D no decrece
  OK    la configuracion de prueba deja pasos dentro y bajo en los dos laminados ([('varilla_00', 'bajo'), ('varilla_00', 'dentro'), ('varilla_91', 'bajo'), ('varilla_91', 'dentro')])
--- 4. Persistencia ---
  OK    al volver, D continua desde el ultimo valor del archivo de verdad (paso 18 -> 19)
  OK    los pasos siguen numerandose sin saltos ni repeticiones (36 pasos)
--- 3. Separacion entre lo medido y la verdad ---
  OK    el archivo de lo medido trae solo sus campos (['caja', 'deformacion_ue', 'delta_sigma_MPa', 'f', 'paso', 'peso_V', 'peso_estable', 'pieza', 'sigma_max_MPa', 'ts_salida']), ninguno de la verdad
  OK    una linea de lo medido y una de la verdad por paso y laminado (72 y 72)
  OK    contexto global leido con el token desechable (200, 200): claves ['a2_mat_medido']; sin claves ni valores de la verdad
  OK    global.a2_mat_medido: ultimos 30 pasos por laminado, solo campos medidos, y conteos de pasos (['laminados', 'pasos', 'sin_peso'])
  OK    en flows.json no hay cable ni enlace de la pestana de materiales hacia la de diagnostico
  OK    el unico enlace que sale de la pestana va a la HMI ([('link_mat_hmi', 'link_hmi_mat', 'a2_hmi')])
  OK    la pestana no tiene nodos Modbus ni http request: no escribe en la planta, en Firebase ni en Gemini (['catch', 'comment', 'debug', 'function', 'inject', 'link in', 'link out'])
  OK    37_diag_arma.js y 38_diag_valida.js identicos a HEAD y al inicio de la fase
--- 7. Galga ---
  OK    la deformacion medida = la recalculada con la secuencia de D de la verdad y la misma semilla (peor diferencia 0.00e+00 ue < 0.1)
--- 4b. Archivo de estado danado ---
  OK    el cliente con desviador conecta (local) y queda en ok
  OK    con el estado danado la pestana no acumula: verdad 72 -> 72 lineas, medido 72 -> 72
  OK    no reinicia en silencio: el archivo danado sigue igual
  OK    y lo reporta: HMI 'NOT accumulating: state file unreadable (see Node-RED log)', registro de Node-RED
--- 5. Umbrales: la HMI pasa por normal, preventive, critical y failure ---
  OK    el cliente con desviador conecta (local) y queda en ok
    umbrales: 15 paso_caja; 0:0 D=1.33709068 {'dentro': 15, 'bajo': 0, 'sobre': 0}; 9:1 D=0.02750000 {'dentro': 11, 'bajo': 4, 'sobre': 0}
    HMI vio (nivel, paso): [('normal', 0), ('preventive', 6), ('critical', 9), ('failure', 12)]; recalcula: {'preventiva': 6, 'critica': 9, 'falla': 12}; cambios en la tarjeta: [{'level': 'preventive', 'step': 6}, {'level': 'critical', 'step': 9}, {'level': 'failure', 'step': 12}]
  OK    la verdad coincide con el recalculo (D sobre 1 en el laminado 0:0: 1.3371)
  OK    la HMI paso por normal, preventive, critical y failure en ese orden
  OK    cada cambio de nivel en el paso que predice el recalculo
--- 6. Region sobre (sigma_ref 1100 MPa) ---
  OK    el cliente con desviador conecta (local) y queda en ok
    sobre: 13 paso_caja; 0:0 D=0.01043197 {'dentro': 1, 'bajo': 3, 'sobre': 9}; 9:1 D=0.01438262 {'dentro': 2, 'bajo': 4, 'sobre': 7}
  OK    la verdad coincide con el recalculo con la configuracion de prueba
  OK    16 pasos sobre el intervalo, contados ([{'dentro': 1, 'bajo': 3, 'sobre': 9}, {'dentro': 2, 'bajo': 4, 'sobre': 7}])
  OK    los pasos sobre no cambian D
  OK    y levantan la alerta en la HMI ([{'code': 'carga_fuera_del_intervalo', 'text': 'load above the tested range', 'count': 9, 'lastStep': 12}, {'code': 'carga_fuera_del_intervalo', 'text': 'load above the tested range', 'count': 7, 'lastStep': 11}]; tarjeta recibida: True)
--- 8. Nodos de la Actividad 1 ---
  OK    los 42 nodos de la Actividad 1 son identicos a los del inicio de la fase
=== RESULTADO: 32 correctas, 0 fallidas ===
```

La estimación de vida restante de la tarjeta (requiere 100 pasos) no tiene
prueba: la orden no la pide en la verificación y las corridas de la prueba
son de menos de 100 pasos. Queda sin verificar.

Batería completa al cerrar M2 (exit 0): `materiales_modelo` 31/31,
`materiales_flujo` 32/32 (369 s), y las demás igual que en M1, con
`prueba.sh` 26/26, reglas A1 50/50 y `proceso` 33/33. Con eso queda el punto
8 (regresión; los 42 nodos de la Actividad 1 idénticos a `b23428b`).

## U. Unidad de masa de la báscula (PUERTA ARI U0 abierta)

### Evidencia de la puerta

Ari abrió U0 con el archivo de escena en lugar de capturas
(`docs/EVIDENCIA_U0.md` y `docs/capturas/escena_sorting_by_weight_A2.factoryio`).
Comprobación propia del archivo, solo lectura:

```
$ shasum -a 256 docs/capturas/escena_sorting_by_weight_A2.factoryio
b9738f9318b8b1b1878e053de35e0066ecddb73ee5d01e128a1524d02fffeb87   (= el de EVIDENCIA_U0.md)
lineas 57-58:  <ComponentIO Index="1" CurrentOperatingMode="0" />
               <OperatingMode Description="$C_ConveyorScale_OM_Default20_NAME">
lineas 104-106: <Emitter MinTimeToEmit="1" MaxTimeToEmit="2" UpTo="0" ...>
                  <Bases />
                  <Parts BoxS="True" BoxM="True" BoxL="True" PalletizingBox="True" ProductBaseGreen="True" ProductLidBlue="True" />
```

La báscula está en `20 Kg Max.` y los seis artículos del emisor (3, 5, 7, 8,
10 y 15 kg) son del catálogo: se cumple la condición de la orden para el
cambio. La puerta V0 se comprobó con lecturas: `sonda_modbus.py --mapa
config/mapa_registros_fio.json --host 10.211.55.3 lee todas` respondió las 33
etiquetas con `fio_running = 1` (exit 0). No se tocó Parallels.

### Qué se hizo

- **Desde el 11 nov 2026, `caja_masa_kg` va en kilogramos a 2 kg por volt.**
  Los 429 registros de caja de `planta_01` (todos del 25 oct 2026,
  01:22:49Z a 02:30:58Z, según `datos/a2_nube_*.csv`) quedaron en la unidad
  antigua, 1 kg por volt; no se reescriben (la rama es append-only).
- `config/planta_fio.json`: `plena_escala_kg` 10.0 → 20.0; umbrales de clase
  `hasta_kg` 4.5 → 9.0 y 7.0 → 14.0 (los mismos 4.5 y 7.0 V); nota y estado
  con la fuente.
- Búsqueda de lo que imprime kilogramos: A2-Planta calcula la masa en un solo
  lugar (`masa = V / 10 × plena_escala_kg`, `28_planta_lectura.js`) y la HMI
  (`Last box … kg`), A2-Nube (`caja_masa_kg`), el prompt de diagnóstico
  (`last_masses_kg`, media y desviación de `37_diag_arma.js`) y la gráfica
  toman ese valor sin constantes propias, así que cambian solos. No hay
  umbrales de clase escritos en código fuera de la configuración. Cambios:
  - `pruebas/prueba_fio.py`: el oráculo comparaba **volts** contra `hasta_kg`
    (válido solo con 1 kg por volt). Ahora convierte con la plena escala de
    la configuración, con el mismo redondeo que A2-Planta; su criterio en
    volts no cambia (4.49 / 4.5 / 4.51 / 6.99 / 7.0 / 7.01 V dan el mismo
    destino con la configuración vieja y con la nueva).
  - `web/proceso.html`: si se muestran registros de caja anteriores al 11 nov
    2026, una nota bajo la gráfica de masas dice que usaron 1 kg por volt.
  - `docs/DEMO_A2.md` (unidades y clases en kg y V; la nota de la gráfica),
    `config/mapa_registros_fio.json` y `docs/MAPA_REGISTROS.md` regenerado
    (`weight`: 0-10 V = 0-20 kg).
- Los sustitutos (`planta_desviador.json`, `planta_a2.json`) ya usaban 20 kg
  de plena escala y no cambian. La capa de materiales usa la fracción de la
  señal y no cambia; el dimensionamiento (punto 4 de la sección 3 de
  `EVIDENCIA_U0.md`) queda para Ari, como pidió.

### Verificación: `pruebas/prueba_tablero.py fronteras` (punto 7, nuevo)

Node-RED con A2-Planta real contra la escena Modbus falsa de la prueba; cajas
de 4.49, 4.51, 6.99 y 7.01 V con la configuración de antes del cambio (tomada
de `git show 266e697:config/planta_fio.json`) y con la del repo. Compara el
destino que el cliente **elige al pesar** (`caja_pesada`), no el sensor que la
escena falsa enciende después.

```
$ /usr/bin/python3 -u pruebas/prueba_tablero.py fronteras                -> exit 0
=== 7. Fronteras de clase en volts: antes y despues del cambio de unidad (paso U) ===
  OK    antes (266e697): plena escala 10 kg, umbrales [4.5, 7.0, None]; A2-Planta conecta
    antes (266e697): [(4.49, 4.49, 'left'), (4.51, 4.51, 'forward'), (6.99, 6.99, 'forward'), (7.01, 7.01, 'right')]
  OK    antes (266e697): destinos elegidos al pesar ['left', 'forward', 'forward', 'right'] = ['left', 'forward', 'forward', 'right']
  OK    antes (266e697): masa_kg = V x 10 / 10 = [4.49, 4.51, 6.99, 7.01]
  OK    antes (266e697): sin desvios erroneos ni perdidas
  OK    repo: plena escala 20 kg, umbrales [9.0, 14.0, None]; A2-Planta conecta
    repo: [(4.49, 8.98, 'left'), (4.51, 9.02, 'forward'), (6.99, 13.98, 'forward'), (7.01, 14.02, 'right')]
  OK    repo: destinos elegidos al pesar ['left', 'forward', 'forward', 'right'] = ['left', 'forward', 'forward', 'right']
  OK    repo: masa_kg = V x 20 / 10 = [8.98, 9.02, 13.98, 14.02]
  OK    repo: sin desvios erroneos ni perdidas
  OK    mismos destinos antes y despues del cambio de unidad

=== RESULTADO: 9 correctas, 0 fallidas ===
```

Control: con plena escala 20 kg y los umbrales viejos (4.5 / 7.0), la prueba
falla (exit 3): destinos `['right', 'right', 'right', 'right']`, 3 desvíos
erróneos. Una primera versión comparaba el `destino` de `paso_caja`, que sale
del sensor de confirmación, y ese control solo lo detectaba por los desvíos;
se cambió a `caja_pesada` antes de cerrar.

`prueba_grafica.py` (no está en la batería: Chrome y emuladores) ganó la
comprobación de la nota: un registro de caja del 25 oct sembrado como dueño →
`la pagina avisa del registro viejo de 1 kg por volt (1)`, OK. La misma
corrida tiene **una falla que ya existía**: `al final la pagina tiene las
mismas cajas que el emulador (16 = 17)`. Con la página y la prueba de
`266e697`, sin ningún cambio de U, falla igual (15 = 16): la última muestra
de la página se toma antes de que A2-Nube escriba la última caja. No se
corrigió en este paso; queda anotada abajo.

Batería completa (`bateria.sh --con-emulador`):

```
mapa                       exit=0      0s  OK
materiales_modelo          exit=0      3s  === RESULTADO: 31 correctas, 0 fallidas ===
materiales_flujo           exit=0    363s  === RESULTADO: 32 correctas, 0 fallidas ===
limites                    exit=0      0s  
sustituto_funcional        exit=0     58s  === RESULTADO: 20 correctas, 0 fallidas ===
sonda                      exit=0     30s  === RESULTADO: 43 correctas, 0 fallidas ===
seguridad                  exit=0     12s  === RESULTADO: 55 correctas, 0 fallidas ===
planta_seguro              exit=0     31s  === RESULTADO: 25 correctas, 0 fallidas ===
planta_control             exit=0     64s  === RESULTADO: 5 correctas, 0 fallidas ===
nube                       exit=0    220s  === RESULTADO: 28 correctas, 0 fallidas ===
vigila                     exit=0     50s  === RESULTADO: 12 correctas, 0 fallidas ===
desviador                  exit=0     69s  === RESULTADO: 19 correctas, 0 fallidas ===
hmi                        exit=0     26s  === RESULTADO: 25 correctas, 0 fallidas ===
diagnostico_a2             exit=0     33s  === RESULTADO: 19 correctas, 0 fallidas ===
instrumentacion_a2         exit=0    139s  === RESULTADO: 6 correctas, 0 fallidas ===
tablero                    exit=0     67s  === RESULTADO: 34 correctas, 0 fallidas ===
prueba_sh                  exit=0     58s  === RESULTADO: 26 correctas, 0 fallidas ===
reglas_a1                  exit=0      0s  50 casos, 0 discrepancias
reglas_proceso             exit=0      0s  33 casos, 0 discrepancias (emulador)
FIN: 0 fallidas
```

## L. Corridas largas y distribución de masas (V0 abierta)

Ari lo pidió el 11 nov 2026 ("ejecuta el paso L completo"), con la consigna de
no detenerse a preguntar, anotar las dudas aquí y no cambiar el
dimensionamiento de la capa de materiales ni escribir en `planta_01`.

### Qué se hizo

- **Definiciones antes de medir**: `docs/INSTRUMENTACION_A2.md`, sección 4
  (caja, niveles a ±0.03 V, emparejamiento con el oráculo, máximo crudo,
  ventanas de 10 min, prueba de homogeneidad, cadencia, D y tiempos a D).
- `pruebas/prueba_fio.py`:
  - el oráculo guarda en `oraculo.json`, como cuarto elemento de cada caja,
    el **máximo crudo** del registro `weight` mientras `load_scale` está
    apagada con la caja en `at_scale`. Para eso lee el registro durante todo
    el pesaje; el peso al soltar y su serie de 0.3 s se siguen tomando solo
    desde 0.5 s, así que sus criterios y comprobaciones no cambian;
  - `--materiales`: arranca Node-RED con `A2_MATERIALES=1` y
    `A2_MAT_CONFIG=config/materiales.json`, con el estado en el directorio de
    datos nuevo de la corrida (D = 0 al empezar).
- `tools/analiza_masas.py` (Python 3.9, sin dependencias): los siete puntos de
  la orden y `--verifica`. Usa `tools/materiales.py` (`carga_config` y
  `recalcula`) para D; la ji cuadrada es propia (gamma incompleta
  regularizada).
- Dos corridas, cada una lanzada con `caffeinate -d`, sin Firebase (las URL
  de Firebase de las pruebas apuntan a 127.0.0.1:9), con la capa de
  materiales encendida, cada una en su directorio de datos y con reinicio de
  escena por Modbus al empezar (Reset, vacía, Run):

  ```
  caffeinate -d /usr/bin/python3 -u pruebas/prueba_fio.py cliente --cajas 600 --materiales --host 10.211.55.3 --puerto 502
  ```

  Python llegó directo a la VM, sin el relevo. Archivos copiados a
  `datos/corridas/L1_2026-11-11/` y `datos/corridas/L2_2026-11-11/`: eventos
  del cliente, `oraculo.json`, los tres archivos de materiales, `errores.log`
  y la salida de la prueba (`prueba_fio.log`). No se copió el CSV de sondeo
  (3 MB por corrida; no lo usa este paso).
- `docs/corrida_L.md`: generado con
  `tools/analiza_masas.py --corrida L1=datos/corridas/L1_2026-11-11 --corrida L2=datos/corridas/L2_2026-11-11 --md docs/corrida_L.md`.

### Verificación

```
$ /usr/bin/python3 tools/analiza_masas.py --verifica                  -> exit 0
--- valor p de la ji cuadrada (implementacion propia) ---
  OK    X2 = 11.24 con 2 grados -> p = 0.0036 (esperado 0.0036)
  OK    X2 = 3.841 con 1 grados -> p = 0.0500 (esperado 0.0500)
  OK    X2 = 9.488 con 4 grados -> p = 0.0500 (esperado 0.0500)
--- datos del 25 oct, 01:00 a 03:00 UTC ---
  OK    429 cajas (429)
  OK    por nivel [68, 63, 66, 63, 74, 44, 5] = [68, 63, 66, 63, 74, 44, 5]
  OK    46 fuera de nivel (46)
  OK    lecturas >= 8.0 V: [8.36, 8.37, 8.72, 9.4, 9.4, 9.53, 9.67, 9.77, 10, 10, 10, 10, 10]
  OK    D crudo del 0:0 = 0.54952814, igual que tools/materiales.py recalcula (0.54952814)
=== RESULTADO: coincide ===
```

Las dos corridas, oráculo con sus criterios (`prueba_fio.py cliente`):

```
L1 (18:29:35Z a 19:16:57Z)                                             -> exit 0
    oraculo: 601 cajas soltadas, 600 salidas NC; cliente: 601 pasos
    por destino (cliente): {'left': 381, 'forward': 110, 'right': 110} | purgadas 0
  OK    cada caja sale por la salida de su peso (oraculo): 600 de 600 (0 sin peso del oraculo)
  OK    el cliente reporta el mismo destino que la salida real, caja por caja (600)
  OK    pesos del cliente = pesos del oraculo (+-0.05 V) en las 546 cajas quietas
  OK    ninguna caja se cae ni se atora: 598 soltadas con mas de 12 s antes del paro, 600 salidas
  OK    600 cajas por la salida de su peso (600)
  OK    sin desvios erroneos, perdidas ni fantasmas (0 / 0 / 0)
=== RESULTADO: 17 correctas, 0 fallidas ===

L2 (19:17:21Z a 20:03:17Z)                                             -> exit 0
    oraculo: 601 cajas soltadas, 600 salidas NC; cliente: 601 pasos
    por destino (cliente): {'left': 353, 'forward': 144, 'right': 104} | purgadas 0
  OK    cada caja sale por la salida de su peso (oraculo): 600 de 600 (0 sin peso del oraculo)
  OK    el cliente reporta el mismo destino que la salida real, caja por caja (600)
  OK    pesos del cliente = pesos del oraculo (+-0.05 V) en las 559 cajas quietas
  OK    ninguna caja se cae ni se atora: 598 soltadas con mas de 12 s antes del paro, 600 salidas
  OK    600 cajas por la salida de su peso (600)
  OK    sin desvios erroneos, perdidas ni fantasmas (0 / 0 / 0)
=== RESULTADO: 17 correctas, 0 fallidas ===
```

(Salida completa en `prueba_fio.log` de cada directorio.) El estado final de
la capa de materiales coincide con `tools/materiales.py` sobre los pesos del
cliente: L1 0:0 D = 0.72358027 y 9:1 D = 0.0175; L2 0:0 D = 0.18040078 y 9:1
D = 0.0025 (`a2_materiales_estado.json` frente a la tabla 7 de
`docs/corrida_L.md`). La comparación completa paso a paso es del paso M3.

Cifras principales de `docs/corrida_L.md` (sin interpretación):

| | L1 | L2 |
|---|---|---|
| Cajas (`paso_caja`) | 601 | 601 |
| Cadencia (cajas/min) | 12.76 | 13.15 |
| Fuera de nivel | 58 | 51 |
| ≥ 8.0 V (de ellas < 9.95 V) | 16 (9) | 9 (8) |
| Cajas ≥ 9.0 V con máximo crudo 1000 / > 1000 | 11 / 0 | 7 / 0 |
| Homogeneidad entre ventanas (X², gl, p) | 24.471, 28, 0.6564 | 22.735, 28, 0.7462 |
| D 0:0 crudo / fuera de nivel al superior | 0.72358027 / 1.87003400 | 0.18040078 / 1.12202040 |

Entre corridas: X² = 9.666, 7 grados de libertad, p = 0.2083.

Batería completa al cerrar L (`bateria.sh --con-emulador`):

```
mapa                       exit=0      0s  OK
materiales_modelo          exit=0      3s  === RESULTADO: 31 correctas, 0 fallidas ===
materiales_flujo           exit=0    369s  === RESULTADO: 32 correctas, 0 fallidas ===
limites                    exit=0      0s  
sustituto_funcional        exit=0     58s  === RESULTADO: 20 correctas, 0 fallidas ===
sonda                      exit=0     31s  === RESULTADO: 43 correctas, 0 fallidas ===
seguridad                  exit=0     12s  === RESULTADO: 55 correctas, 0 fallidas ===
planta_seguro              exit=0     31s  === RESULTADO: 25 correctas, 0 fallidas ===
planta_control             exit=0     64s  === RESULTADO: 5 correctas, 0 fallidas ===
nube                       exit=0    219s  === RESULTADO: 28 correctas, 0 fallidas ===
vigila                     exit=0     51s  === RESULTADO: 12 correctas, 0 fallidas ===
desviador                  exit=0     68s  === RESULTADO: 19 correctas, 0 fallidas ===
hmi                        exit=0     26s  === RESULTADO: 25 correctas, 0 fallidas ===
diagnostico_a2             exit=0     32s  === RESULTADO: 19 correctas, 0 fallidas ===
instrumentacion_a2         exit=0    139s  === RESULTADO: 6 correctas, 0 fallidas ===
tablero                    exit=0     66s  === RESULTADO: 34 correctas, 0 fallidas ===
prueba_sh                  exit=0     59s  === RESULTADO: 26 correctas, 0 fallidas ===
reglas_a1                  exit=0      0s  50 casos, 0 discrepancias
reglas_proceso             exit=0      0s  33 casos, 0 discrepancias (emulador)
FIN: 0 fallidas
```

### Dudas y observaciones anotadas (no se decidió nada)

1. **601 cajas y no 600.** `--cajas 600` corta al ver 600 salidas NC; el
   cliente registró un `paso_caja` más antes del paro (una caja en camino).
   Con la definición escrita (caja = `paso_caja`), el reporte usa las 601.
2. **Máximo crudo y peso al soltar.** En L2, 7 cajas de 9.0 V o más tuvieron
   máximo crudo 1000, pero solo 1 quedó en 10.00 V al soltar. El reporte da
   las cifras; qué significa queda para Ari con `docs/corrida_L.md`.
3. **Lectura continua del oráculo durante el pesaje.** Ampliar el oráculo
   agregó lecturas del registro `weight` en los primeros 0.5 s del pesaje.
   Sus criterios no cambiaron y las dos corridas pasaron, pero el oráculo ya
   no hace exactamente las mismas peticiones Modbus que en las corridas del
   24 y 25 oct.
4. **Tiempos a D.** Son extrapolación lineal al ritmo medio de cada corrida,
   como dice la definición; el ritmo cambia entre corridas (L1 y L2 dan
   tiempos distintos para el mismo laminado).
5. **Dimensionamiento.** No se tocó `config/materiales.json`. El punto 4 de
   la sección 3 de `docs/EVIDENCIA_U0.md`, la corrección del peso por
   catálogo, el pesaje detenido y `ciclos_por_paso` los decide Ari con
   `docs/corrida_L.md` a la vista. M3 depende de esa decisión.

## T. Tablero en la escena real (PUERTAS V0 y T0 abiertas)

Ari abrió T0 el 11 nov 2026 y presionó los botones cuando la prueba dijo que
estaba vigilando. La orden de cierre (`docs/ORDEN_A2_FASE_3_CIERRE.md`, commit
`11c5053`) deja este paso como estaba.

### Qué se hizo

- Corrida, con Python directo a la VM (no hizo falta el relevo):

  ```
  /usr/bin/python3 -u pruebas/prueba_fio.py tablero -s 180 --host 10.211.55.3 --puerto 502
  ```

  El modo vigila al menos 600 s (`max(x.segundos, 600)`); terminó solo al ver
  la secuencia completa, a los 70 s.
- `config/mapa_registros_fio.json` (estado, `stop_button` y `emergency_stop`)
  y `docs/MAPA_REGISTROS.md` regenerado: Stop y Emergency stop quedan
  confirmados como NC **al presionarlos**, ya no solo por su reposo.
- La salida y los eventos del cliente quedaron en
  `datos/corridas/T_2026-11-11/`.

### Verificación

```
$ /usr/bin/python3 -u pruebas/prueba_fio.py tablero -s 180 --host 10.211.55.3 --puerto 502   -> exit 0
=== Tablero de la escena (datos en /var/folders/6y/56sny62s59j98r894dbqq9y00000gn/T/a2_fio_tablero_rpqpnyql) ===
    reinicio de la escena en 10.211.55.3:502 (unidad 1)
        0.0 s  11 bobinas de actuadores en 0
        0.2 s  Reset = 1 -> running 0
        0.5 s  Reset = 0
        0.5 s  vacia: bascula, desviador, ramas y salidas libres, peso < 0.2 V
        2.2 s  Run = 1 (se queda) -> running 1, sostenido 1 s
  OK    escena reiniciada por Modbus: Reset, vacia y Run (codigo 0)
  OK    A2-Planta conecta con la escena (com ok)
    en reposo (sin presionar): {'start_button': 0, 'stop_button': 1, 'emergency_stop': 1}
    >>> VIGILANDO: presiona en la escena Start, Stop, Start, Emergency stop (dejalo unos segundos),
    >>> suelta Emergency stop, Start y Stop. Tengo 600 s.
      41.9 s  start_button    0 -> 1   linea: detenida   luces {'start_light': 0, 'stop_light': 1, 'reset_light': 0}  entry_conveyor 0
      42.5 s  start_button    1 -> 0   linea: detenida   luces {'start_light': 0, 'stop_light': 1, 'reset_light': 0}  entry_conveyor 0
      49.8 s  stop_button     1 -> 0   linea: detenida   luces {'start_light': 0, 'stop_light': 1, 'reset_light': 0}  entry_conveyor 0
      50.5 s  stop_button     0 -> 1   linea: detenida   luces {'start_light': 0, 'stop_light': 1, 'reset_light': 0}  entry_conveyor 0
      53.6 s  start_button    0 -> 1   linea: en_marcha  luces {'start_light': 1, 'stop_light': 0, 'reset_light': 0}  entry_conveyor 1
      54.2 s  start_button    1 -> 0   linea: en_marcha  luces {'start_light': 1, 'stop_light': 0, 'reset_light': 0}  entry_conveyor 1
      57.4 s  emergency_stop  1 -> 0   linea: emergencia luces {'start_light': 0, 'stop_light': 1, 'reset_light': 1}  entry_conveyor 0
      60.9 s  emergency_stop  0 -> 1   linea: detenida   luces {'start_light': 0, 'stop_light': 1, 'reset_light': 0}  entry_conveyor 0
      65.5 s  start_button    0 -> 1   linea: en_marcha  luces {'start_light': 1, 'stop_light': 0, 'reset_light': 0}  entry_conveyor 0
      66.1 s  start_button    1 -> 0   linea: en_marcha  luces {'start_light': 1, 'stop_light': 0, 'reset_light': 0}  entry_conveyor 0
      69.8 s  stop_button     1 -> 0   linea: detenida   luces {'start_light': 0, 'stop_light': 1, 'reset_light': 0}  entry_conveyor 0
      70.4 s  stop_button     0 -> 1   linea: detenida   luces {'start_light': 0, 'stop_light': 1, 'reset_light': 0}  entry_conveyor 0
  OK    Stop es NC: 1 en reposo, baja a 0 al presionar y vuelve a 1
  OK    Emergency stop es NC: 1 en reposo, baja a 0 al presionar y vuelve a 1
  OK    Start es normalmente abierto: 0 en reposo, 1 al presionar
  OK    Start presionado (sin emergencia) -> en marcha, start_light 1, banda de entrada encendida
  OK    Stop presionado -> detenida, stop_light 1, banda de entrada apagada
  OK    Emergency stop presionado -> emergencia, reset_light 1, banda apagada
  OK    Emergency stop soltado -> detenida, sin arrancar sola
    eventos del cliente: [('boton', 'stop'), ('boton', 'start'), ('paro_de_emergencia', None), ('emergencia_liberada', None), ('boton', 'start'), ('boton', 'stop')]

=== RESULTADO: 9 correctas, 0 fallidas ===
```

### Observación (no se corrigió nada)

El **primer** Start (41.9 s) cambió el botón de 0 a 1 y de vuelta a 0 en 0.6 s,
pero el cliente no registró evento `boton` y la línea siguió detenida. El
segundo y el tercer Start sí arrancaron la línea (los eventos del cliente
empiezan con `boton stop`). Ninguna comprobación del modo exige que cada
Start arranque, así que la prueba pasa. No se investigó más ni se cambió el
cliente, como pide la orden; queda como observación. Tras soltar la
emergencia, el tercer Start dejó la línea en marcha con `start_light` 1 pero
`entry_conveyor` en 0 a los 0.6 s; la comprobación de banda encendida la
cumplió el segundo Start.

Batería completa al cerrar T (`bateria.sh --con-emulador`):

```
mapa                       exit=0      0s  OK
materiales_modelo          exit=0      2s  === RESULTADO: 31 correctas, 0 fallidas ===
materiales_flujo           exit=0    364s  === RESULTADO: 32 correctas, 0 fallidas ===
limites                    exit=0      0s  
sustituto_funcional        exit=0     58s  === RESULTADO: 20 correctas, 0 fallidas ===
sonda                      exit=0     31s  === RESULTADO: 43 correctas, 0 fallidas ===
seguridad                  exit=0     12s  === RESULTADO: 55 correctas, 0 fallidas ===
planta_seguro              exit=0     30s  === RESULTADO: 25 correctas, 0 fallidas ===
planta_control             exit=0     63s  === RESULTADO: 5 correctas, 0 fallidas ===
nube                       exit=0    221s  === RESULTADO: 28 correctas, 0 fallidas ===
vigila                     exit=0     50s  === RESULTADO: 12 correctas, 0 fallidas ===
desviador                  exit=0     67s  === RESULTADO: 19 correctas, 0 fallidas ===
hmi                        exit=0     26s  === RESULTADO: 25 correctas, 0 fallidas ===
diagnostico_a2             exit=0     33s  === RESULTADO: 19 correctas, 0 fallidas ===
instrumentacion_a2         exit=0    139s  === RESULTADO: 6 correctas, 0 fallidas ===
tablero                    exit=0     65s  === RESULTADO: 34 correctas, 0 fallidas ===
prueba_sh                  exit=0     59s  === RESULTADO: 26 correctas, 0 fallidas ===
reglas_a1                  exit=0      1s  50 casos, 0 discrepancias
reglas_proceso             exit=0      0s  33 casos, 0 discrepancias (emulador)
FIN: 0 fallidas
```

## R. Redimensionamiento de la capa de materiales (M0 revisada, orden de cierre)

Orden: `docs/ORDEN_A2_FASE_3_CIERRE.md` (commit `11c5053`). Ari revisó M0 el
11 nov 2026 con `docs/corrida_L.md` a la vista: referencia de carga en la
pieza de 15 kg (7.5 V), ajuste al nivel del catálogo y `ciclos_por_paso` 350.

### Qué se hizo

- `config/materiales.json`: el Anexo A de la orden de cierre tal cual
  (`version` 2, `carga.senal_ref_V` 7.5, `ajuste_nivel` con los seis niveles y
  0.03 V, `ciclos_por_paso` 350).
- `39_mat_modelo.js` y `tools/materiales.py`, la misma cuenta en los dos:
  - `valida`: `version` distinta de 2 → `version_no_soportada`;
    `senal_plena_escala_V` presente → `senal_plena_escala_obsoleta`;
    `ajuste_nivel.niveles_V` no positivos o no crecientes →
    `niveles_desordenados`; `tolerancia_V` negativa o no menor que la mitad de
    la separación mínima → `tolerancia_invalida`. Códigos nuevos, cada uno con
    su prueba de mutación.
  - `peso_modelo_V` con `c(x) = floor(x × 100 + 0.5)` y
    `|c(peso_V) − c(nivel)| ≤ c(tolerancia_V)`; `f = peso_modelo_V /
    senal_ref_V`; lo demás igual (sin extrapolar, tope 10^6, umbrales, galga).
  - el resultado de cada paso gana `peso_V`, `peso_modelo_V` y `ajustado`; el
    estado gana `cfg_version`; `recalcula` reporta `ajustados`.
- `40_mat_entrada.js`: un estado con `cfg_version` distinta de la versión de
  la configuración no se continúa (no acumula y lo reporta, como un estado
  dañado). `41_mat_salida.js`: la verdad gana `peso_V`, `peso_modelo_V` y
  `ajustado`; lo medido no cambia. `42_mat_hmi.js`: solo una entrada más en la
  traducción del motivo de bloqueo ("state file from another configuration
  version"); la tarjeta no cambia de forma.
- `node-red/flows.json` regenerado con `node-red/construye_flows.py`.
- `pruebas/prueba_materiales.py` pasa a la versión 2 (Anexo B de la orden de
  cierre). En `flujo`, masas de prueba nuevas (no son del Anexo): mezcla de
  media 15 kg y la de umbrales entre 14.0 y 15.0 kg; la corrida de umbrales
  usa una configuración de prueba con `ciclos_por_paso` 2500 para cruzar los
  tres umbrales en ~20 pasos; la sección de `sobre` usa ya la configuración del
  repo (las masas de más de 15 kg quedan sobre el intervalo del 0:0). Sección
  4c nueva: estado con `cfg_version` 1.
- `tools/analiza_masas.py --verifica`: el punto de D ya no compara contra
  0.54952814 (era la versión 1) sino contra `tools/materiales.py` con la
  configuración vigente; el reporte dice con qué versión calculó.
  `docs/corrida_L.md` no se regeneró: su tabla 7 es de la versión 1.
- `docs/PARAMETROS_MATERIALES.md`: nota fechada al inicio de las secciones 8
  y 9.

### Verificación

```
$ /usr/bin/python3 tools/materiales.py referencia     (17 filas = primera parte del Anexo B, celda por celda)
$ /usr/bin/python3 -u pruebas/prueba_materiales.py modelo                 -> exit 0
=== Modelo de la capa de materiales, configuracion version 2 (paso R) ===
--- 0. Configuracion ---
  OK    config/materiales.json es valida en Python y en JavaScript
  OK    config/materiales.json es exactamente el Anexo A de la orden de cierre (version 2)
  OK    la configuracion del commit a946ecf (version 1) se rechaza y lo dice: ['campo_desconocido', 'campo_faltante', 'senal_plena_escala_obsoleta', 'tipo_invalido', 'valor_invalido', 'version_no_soportada']
  OK    una configuracion con tolerancia_V de 0.3 se rechaza con tolerancia_invalida (py y js)
  OK    una configuracion con niveles en desorden se rechaza con niveles_desordenados (py y js)
--- 1. Tabla del Anexo B (JavaScript y Python) ---
  OK    17 pesos x 2 laminados: peso_modelo_V y ajustado exactos, sigma_max (rel < 1e-9), N a 4 decimales y JS = Python (rel < 1e-9), dD a 8 decimales, region exacta
--- 2. Carga constante y secuencia mixta ---
  OK    77 pasos de 7.50 V, laminado 0:0: D = 1.00794833 (js 1.00794833, py 1.00794833), cruces {'preventiva': 39, 'critica': 62, 'falla': 77}, 0 ajustadas, D no decrece
  OK    77 pasos de 7.50 V, laminado 9:1: D = 0.02695000 (js 0.02695000, py 0.02695000), D no decrece
  OK    secuencia mixta de 15 pasos, laminado 0:0: D = 0.07621096 (js 0.07621096, py 0.07621096), dentro/bajo/sobre (7, 2, 6), 3 ajustadas, D no decrece
  OK    secuencia mixta de 15 pasos, laminado 9:1: D = 0.20598153 (js 0.20598153, py 0.20598153), dentro/bajo/sobre (8, 4, 3), D no decrece
--- 3. Fronteras ---
  OK    0:0: 6.74 V bajo, 6.75 V dentro (con el tope), 7.53 V dentro (ajustado a 7.50), 7.54 V sobre; 9:1: 7.46 V bajo, 7.47 V dentro (ajustado), 8.48 V dentro, 8.49 V sobre
  OK    a 6.75 V el laminado 0:0 usa el tope de 10^6 ciclos
--- 4. Rigidez interpolada y galga sin ruido ---
  OK    d(D) en 0:0 (7 valores) y 9:1 (6 valores), a 6 decimales, en JS y Python (tablas sin cambio)
  OK    galga sin ruido del Anexo B (11 casos) con diferencia < 0.001 ue en JS y Python
--- 5. Ruido de la galga ---
  OK    laminado 0:0: la misma semilla da la misma secuencia (dos corridas JS identicas; JS vs Python max 0.00e+00 ue)
  OK    laminado 0:0: 10000 muestras, media 0.140 ue (|media| < 1) y desviacion 25.106 ue (|sd - 25| < 1)
  OK    laminado 9:1: la misma semilla da la misma secuencia (dos corridas JS identicas; JS vs Python max 9.09e-13 ue)
  OK    laminado 9:1: 10000 muestras, media 0.109 ue (|media| < 1) y desviacion 25.021 ue (|sd - 25| < 1)
  OK    los dos laminados usan generadores distintos (primer ruido distinto)
--- 6. D de JavaScript y Python sobre 10000 pesos con semilla ---
  OK    config del repo: D final igual (rel < 1e-9; peor paso 0.0e+00), mismos conteos, sin_peso 1/1: 0:0 D=8.02149, 9:1 D=55.398
  OK    ciclos_por_paso = 1: D final igual (rel < 1e-9; peor paso 0.0e+00), mismos conteos, sin_peso 1/1: 0:0 D=0.0229185, 9:1 D=0.15828
--- 7. Validador: cada rechazo con su control y prueba de mutacion ---
  OK    b_no_negativo               rechaza (py y js) y con la regla apagada deja de rechazar
  OK    a_no_positivo               rechaza (py y js) y con la regla apagada deja de rechazar
  OK    intervalo_invertido         rechaza (py y js) y con la regla apagada deja de rechazar
  OK    umbrales_desordenados       rechaza (py y js) y con la regla apagada deja de rechazar
  OK    rigidez_no_empieza_en_cero  rechaza (py y js) y con la regla apagada deja de rechazar
  OK    rigidez_D_no_creciente      rechaza (py y js) y con la regla apagada deja de rechazar
  OK    rigidez_d_decreciente       rechaza (py y js) y con la regla apagada deja de rechazar
  OK    rigidez_D_fuera_de_rango    rechaza (py y js) y con la regla apagada deja de rechazar
  OK    campo_desconocido           rechaza (py y js) y con la regla apagada deja de rechazar
  OK    campo_desconocido           rechaza (py y js) y con la regla apagada deja de rechazar
  OK    campo_desconocido           rechaza (py y js) y con la regla apagada deja de rechazar
  OK    version_no_soportada        rechaza (py y js) y con la regla apagada deja de rechazar
  OK    senal_plena_escala_obsoleta rechaza (py y js) y con la regla apagada deja de rechazar (apagando tambien ['campo_desconocido'])
  OK    niveles_desordenados        rechaza (py y js) y con la regla apagada deja de rechazar
  OK    niveles_desordenados        rechaza (py y js) y con la regla apagada deja de rechazar
  OK    tolerancia_invalida         rechaza (py y js) y con la regla apagada deja de rechazar
  OK    tolerancia_invalida         rechaza (py y js) y con la regla apagada deja de rechazar
  OK    control: tools/materiales.py valida acepta el Anexo A (exit 0)
--- 8. recalcula L1 y L2 (tercera parte del Anexo B) ---
  OK    L1: 601 pasos, 269 ajustados; 0:0 D=1.14730757 {'dentro': 91, 'bajo': 490, 'sobre': 20} cruces {'preventiva': 250, 'critica': 413, 'falla': 526} uts 9; 9:1 D=0.09261109 {'dentro': 92, 'bajo': 494, 'sobre': 15} cruces {} uts 0
  OK    L2: 601 pasos, 265 ajustados; 0:0 D=1.18322756 {'dentro': 93, 'bajo': 496, 'sobre': 12} cruces {'preventiva': 248, 'critica': 405, 'falla': 499} uts 4; 9:1 D=0.03262895 {'dentro': 93, 'bajo': 499, 'sobre': 9} cruces {} uts 0
  OK    tools/materiales.py recalcula da lo mismo por linea de comandos en L1 (0:0 D=1.14730757)

=== RESULTADO: 42 correctas, 0 fallidas ===

$ /usr/bin/python3 -u pruebas/prueba_materiales.py flujo                  -> exit 0
=== M2. Pestana A2 · Materiales contra el sustituto del desviador (en /var/folders/6y/56sny62s59j98r894dbqq9y00000gn/T/a2_materiales__j8f3yc5) ===
--- 1. Sin A2_MATERIALES ---
  OK    el cliente con desviador conecta (local) y queda en ok
  OK    sin la bandera, la pestana no crea archivos ([])
  OK    y la HMI no recibe la tarjeta (estado de la planta si: True)
--- 2. Corrida contra el sustituto, con un reinicio de Node-RED a media corrida ---
  OK    el cliente con desviador conecta (local) y queda en ok
    primera parte: 18 pasos; Node-RED detenido
  OK    el cliente con desviador conecta (local) y queda en ok
    corrida completa: 36 paso_caja; 0:0 D=0.02143476 {'dentro': 6, 'bajo': 14, 'sobre': 16}; 9:1 D=0.06970820 {'dentro': 14, 'bajo': 20, 'sobre': 2}
  OK    la verdad coincide con tools/materiales.py recalcula: D por laminado (rel < 1e-9), conteos exactos, D no decrece
  OK    la configuracion de prueba deja pasos dentro y bajo en los dos laminados ([('varilla_00', 'bajo'), ('varilla_00', 'dentro'), ('varilla_00', 'sobre'), ('varilla_91', 'bajo'), ('varilla_91', 'dentro'), ('varilla_91', 'sobre')])
--- 4. Persistencia ---
  OK    al volver, D continua desde el ultimo valor del archivo de verdad (paso 18 -> 19)
  OK    los pasos siguen numerandose sin saltos ni repeticiones (36 pasos)
--- 3. Separacion entre lo medido y la verdad ---
  OK    el archivo de lo medido trae solo sus campos (['caja', 'deformacion_ue', 'delta_sigma_MPa', 'f', 'paso', 'peso_V', 'peso_estable', 'pieza', 'sigma_max_MPa', 'ts_salida']), ninguno de la verdad
  OK    una linea de lo medido y una de la verdad por paso y laminado (72 y 72)
  OK    contexto global leido con el token desechable (200, 200): claves ['a2_mat_medido']; sin claves ni valores de la verdad
  OK    global.a2_mat_medido: ultimos 30 pasos por laminado, solo campos medidos, y conteos de pasos (['laminados', 'pasos', 'sin_peso'])
  OK    en flows.json no hay cable ni enlace de la pestana de materiales hacia la de diagnostico
  OK    el unico enlace que sale de la pestana va a la HMI ([('link_mat_hmi', 'link_hmi_mat', 'a2_hmi')])
  OK    la pestana no tiene nodos Modbus ni http request: no escribe en la planta, en Firebase ni en Gemini (['catch', 'comment', 'debug', 'function', 'inject', 'link in', 'link out'])
  OK    37_diag_arma.js y 38_diag_valida.js identicos a HEAD y al inicio de la fase
--- 7. Galga ---
  OK    la deformacion medida = la recalculada con la secuencia de D de la verdad y la misma semilla (peor diferencia 0.00e+00 ue < 0.1)
--- 4b. Archivo de estado danado ---
  OK    el cliente con desviador conecta (local) y queda en ok
  OK    con el estado danado la pestana no acumula: verdad 72 -> 72 lineas, medido 72 -> 72
  OK    no reinicia en silencio: el archivo danado sigue igual
  OK    y lo reporta: HMI 'NOT accumulating: state file unreadable (see Node-RED log)', registro de Node-RED
--- 4c. Estado de otra version de configuracion (cfg_version 1) ---
  OK    el cliente con desviador conecta (local) y queda en ok
  OK    con un estado de cfg_version 1 la pestana no acumula: verdad 72 -> 72, medido 72 -> 72
  OK    el estado viejo sigue igual (no se reescribe)
  OK    y lo reporta: HMI 'NOT accumulating: state file from another configuration version (see Node-RED log)', registro de Node-RED
--- 5. Umbrales: la HMI pasa por normal, preventive, critical y failure ---
  OK    el cliente con desviador conecta (local) y queda en ok
    umbrales: 24 paso_caja; 0:0 D=1.12185177 {'dentro': 24, 'bajo': 0, 'sobre': 0}; 9:1 D=0.01000000 {'dentro': 4, 'bajo': 20, 'sobre': 0}
    HMI vio (nivel, paso): [('normal', 0), ('preventive', 13), ('critical', 18), ('failure', 21)]; recalcula: {'preventiva': 13, 'critica': 18, 'falla': 21}; cambios en la tarjeta: [{'level': 'preventive', 'step': 13}, {'level': 'critical', 'step': 18}, {'level': 'failure', 'step': 21}]
  OK    la verdad coincide con el recalculo (D sobre 1 en el laminado 0:0: 1.1219)
  OK    la HMI paso por normal, preventive, critical y failure en ese orden
  OK    cada cambio de nivel en el paso que predice el recalculo
--- 6. Region sobre (masas de mas de 15 kg en el 0:0, configuracion del repo) ---
  OK    el cliente con desviador conecta (local) y queda en ok
    sobre: 13 paso_caja; 0:0 D=0.01033542 {'dentro': 2, 'bajo': 5, 'sobre': 6}; 9:1 D=0.00674113 {'dentro': 5, 'bajo': 7, 'sobre': 1}
  OK    la verdad coincide con el recalculo con la configuracion de prueba
  OK    7 pasos sobre el intervalo, contados ([{'dentro': 2, 'bajo': 5, 'sobre': 6}, {'dentro': 5, 'bajo': 7, 'sobre': 1}])
  OK    los pasos sobre no cambian D
  OK    y levantan la alerta en la HMI ([{'code': 'carga_fuera_del_intervalo', 'text': 'load above the tested range', 'count': 6, 'lastStep': 11}, {'code': 'carga_fuera_del_intervalo', 'text': 'load above the tested range', 'count': 1, 'lastStep': 3}]; tarjeta recibida: True)
--- 8. Nodos de la Actividad 1 ---
  OK    los 42 nodos de la Actividad 1 son identicos a los del inicio de la fase

=== RESULTADO: 36 correctas, 0 fallidas ===
```

Primera batería completa al cerrar R (`bateria.sh --con-emulador`), **1 fallida**:

```
mapa                       exit=0      0s  OK
materiales_modelo          exit=0      4s  === RESULTADO: 42 correctas, 0 fallidas ===
materiales_flujo           exit=0    436s  === RESULTADO: 36 correctas, 0 fallidas ===
limites                    exit=0      0s  
sustituto_funcional        exit=0     57s  === RESULTADO: 20 correctas, 0 fallidas ===
sonda                      exit=0     31s  === RESULTADO: 43 correctas, 0 fallidas ===
seguridad                  exit=1      8s  === RESULTADO: 54 correctas, 1 fallidas ===
planta_seguro              exit=0     30s  === RESULTADO: 25 correctas, 0 fallidas ===
planta_control             exit=0     64s  === RESULTADO: 5 correctas, 0 fallidas ===
nube                       exit=0    220s  === RESULTADO: 28 correctas, 0 fallidas ===
vigila                     exit=0     51s  === RESULTADO: 12 correctas, 0 fallidas ===
desviador                  exit=0     67s  === RESULTADO: 19 correctas, 0 fallidas ===
hmi                        exit=0     26s  === RESULTADO: 25 correctas, 0 fallidas ===
diagnostico_a2             exit=0     33s  === RESULTADO: 19 correctas, 0 fallidas ===
instrumentacion_a2         exit=0    138s  === RESULTADO: 6 correctas, 0 fallidas ===
tablero                    exit=0     66s  === RESULTADO: 34 correctas, 0 fallidas ===
prueba_sh                  exit=0     59s  === RESULTADO: 26 correctas, 0 fallidas ===
reglas_a1                  exit=0      0s  50 casos, 0 discrepancias
reglas_proceso             exit=0      1s  33 casos, 0 discrepancias (emulador)
FIN: 1 fallidas
```

La falla fue el control autenticado de `/comms` en `prueba_seguridad.py`
(sección 3): con un token recién emitido, `GET /flows` respondió 200 pero el
websocket `/comms` contestó `{"auth":"fail"}` y cerró.

```
  OK    con la contrasena correcta se obtiene token
  OK    con ese token GET /flows -> 200 (8 pestanas)
  FALLA control: autenticado, /comms dice auth ok y SI entrega eventos (0) ['{"auth":"fail"}', 'CERRADO']
```

- Corrida suelta inmediata de `prueba_seguridad.py`: la misma falla, 54/55.
- Reproducción aislada (Node-RED con credenciales desechables, token, `/flows`
  y `/comms`, con y sin los intentos de contraseña equivocada antes): `auth ok`
  en los 5 intentos.
- Tercera corrida suelta de `prueba_seguridad.py`: 55/55.
- R no toca nada de lo que esa prueba ejercita (`settings.js`, el editor, la
  API de administración, `admin_desechable.py`); en las baterías de U, L y T
  la misma comprobación pasó.

Queda anotada como **falla intermitente sin causa encontrada** del control de
`/comms` (en `@node-red/editor-api` 5.0.9, `comms.js` contesta `fail` cuando
`Tokens.get` no encuentra la sesión o el usuario). No se cambió la prueba ni el
cliente. La batería se volvió a correr completa:

```
mapa                       exit=0      0s  OK
materiales_modelo          exit=0      3s  === RESULTADO: 42 correctas, 0 fallidas ===
materiales_flujo           exit=0    438s  === RESULTADO: 36 correctas, 0 fallidas ===
limites                    exit=0      0s  
sustituto_funcional        exit=0     57s  === RESULTADO: 20 correctas, 0 fallidas ===
sonda                      exit=0     31s  === RESULTADO: 43 correctas, 0 fallidas ===
seguridad                  exit=0     12s  === RESULTADO: 55 correctas, 0 fallidas ===
planta_seguro              exit=0     30s  === RESULTADO: 25 correctas, 0 fallidas ===
planta_control             exit=0     64s  === RESULTADO: 5 correctas, 0 fallidas ===
nube                       exit=0    219s  === RESULTADO: 28 correctas, 0 fallidas ===
vigila                     exit=0     51s  === RESULTADO: 12 correctas, 0 fallidas ===
desviador                  exit=0     67s  === RESULTADO: 19 correctas, 0 fallidas ===
hmi                        exit=0     25s  === RESULTADO: 25 correctas, 0 fallidas ===
diagnostico_a2             exit=0     33s  === RESULTADO: 19 correctas, 0 fallidas ===
instrumentacion_a2         exit=0    139s  === RESULTADO: 6 correctas, 0 fallidas ===
tablero                    exit=0     65s  === RESULTADO: 34 correctas, 0 fallidas ===
prueba_sh                  exit=0     59s  === RESULTADO: 26 correctas, 0 fallidas ===
reglas_a1                  exit=0      0s  50 casos, 0 discrepancias
reglas_proceso             exit=0      0s  33 casos, 0 discrepancias (emulador)
FIN: 0 fallidas
```

## M3. Capa de materiales contra la escena, configuración versión 2

### Qué se hizo

- **Recálculo de L1 y L2** con `tools/materiales.py` y la versión 2 sobre sus
  `paso_caja` (no se volvieron a correr).
- **Corrida en vivo M1** (desde 2026-11-11T22:27:23Z), con `caffeinate -d`, sin
  Firebase, reinicio de escena al empezar, capa encendida y D = 0 (directorio
  de datos nuevo):

  ```
  caffeinate -d /usr/bin/python3 -u pruebas/prueba_fio.py cliente --cajas 600 --materiales --host 10.211.55.3 --puerto 502
  ```

  Archivos en `datos/corridas/M1_2026-11-11/`, como en L, más
  `hmi_materiales.jsonl` (cada tarjeta que recibió la HMI) y
  `observa_hmi.log`.
- `pruebas/observa_hmi_materiales.py` (nuevo, solo lee): se conecta a la HMI
  por socket.io como el navegador, guarda cada tarjeta `Materials layer` y,
  cuando la tarjeta muestra D ≥ 0.5 en la varilla 0:0, toma la captura con
  Chrome sin ventana. Captura: `docs/img/hmi_materiales.png`, en el paso 264
  (D 0:0 = 0.5105, nivel preventive).
- `tools/corrida_materiales.py` (nuevo): el reporte y `--verifica-vivo`.
  `docs/corrida_materiales.md` generado con
  `--corrida L1=… --corrida L2=… --corrida M1=… --verifica-vivo M1 --md docs/corrida_materiales.md`.

### Verificación

1. Recálculo de L1 y L2 = tercera parte del Anexo B (D a 8 decimales, conteos,
   pasos de cruce, lecturas ajustadas y pasos con esfuerzo ≥ resistencia):
   punto 8 de `prueba_materiales.py modelo` (sección R) y la salida de abajo.
2 y 3. Verdad en vivo contra el recálculo y la HMI:

```
$ /usr/bin/python3 tools/corrida_materiales.py --corrida L1=datos/corridas/L1_2026-11-11 --corrida L2=datos/corridas/L2_2026-11-11 --corrida M1=datos/corridas/M1_2026-11-11 --verifica-vivo M1 --md docs/corrida_materiales.md   -> exit 0
--- M1: verdad en vivo contra el recalculo y la HMI ---
  OK    M1: la verdad coincide con el recalculo paso a paso (1202 lineas; peor diferencia relativa de D 0.0e+00 < 1e-9; region, peso_modelo_V, ajustado y caja iguales)
  OK    M1: D no decrece en ningun laminado
  OK    M1: los 16 pasos sobre el intervalo no cambian D
  OK    M1, laminado 0:0: la HMI mostro ['normal', 'preventive', 'critical', 'failure']; cambios de nivel en la tarjeta [('preventive', 264), ('critical', 420), ('failure', 489)] = recalculo [('preventive', 264), ('critical', 420), ('failure', 489)]
  OK    M1, laminado 9:1: la HMI mostro ['normal']; cambios de nivel en la tarjeta [] = recalculo []
escrito docs/corrida_materiales.md
L1: 601 pasos, 269 ajustados; 0:0 D=1.14730757 {'dentro': 91, 'bajo': 490, 'sobre': 20} cruces {'preventiva': 250, 'critica': 413, 'falla': 526} uts 9; 9:1 D=0.09261109 {'dentro': 92, 'bajo': 494, 'sobre': 15} cruces {} uts 0
L2: 601 pasos, 265 ajustados; 0:0 D=1.18322756 {'dentro': 93, 'bajo': 496, 'sobre': 12} cruces {'preventiva': 248, 'critica': 405, 'falla': 499} uts 4; 9:1 D=0.03262895 {'dentro': 93, 'bajo': 499, 'sobre': 9} cruces {} uts 0
M1: 601 pasos, 284 ajustados; 0:0 D=1.26975309 {'dentro': 97, 'bajo': 495, 'sobre': 9} cruces {'preventiva': 264, 'critica': 420, 'falla': 489} uts 3; 9:1 D=0.03713601 {'dentro': 99, 'bajo': 495, 'sobre': 7} cruces {} uts 0
=== RESULTADO: 0 fallas ===
```

4. Oráculo de `prueba_fio.py` en M1, con sus criterios:

```
    oraculo: 601 cajas soltadas, 600 salidas NC; cliente: 601 pasos
    por destino (cliente): {'left': 383, 'forward': 112, 'right': 106} | purgadas 0
  OK    cada caja sale por la salida de su peso (oraculo): 600 de 600 (0 sin peso del oraculo)
  OK    el cliente reporta el mismo destino que la salida real, caja por caja (600)
  OK    pesos del cliente = pesos del oraculo (+-0.05 V) en las 560 cajas quietas
  OK    ninguna caja se cae ni se atora: 598 soltadas con mas de 12 s antes del paro, 600 salidas
  OK    600 cajas por la salida de su peso (600)
  OK    sin desvios erroneos, perdidas ni fantasmas (0 / 0 / 0)
=== RESULTADO: 17 correctas, 0 fallidas ===   (salida completa en datos/corridas/M1_2026-11-11/prueba_fio.log)
```

Batería completa al cerrar M3 (`bateria.sh --con-emulador`):

```
mapa                       exit=0      0s  OK
materiales_modelo          exit=0      4s  === RESULTADO: 42 correctas, 0 fallidas ===
materiales_flujo           exit=0    432s  === RESULTADO: 36 correctas, 0 fallidas ===
limites                    exit=0      0s  
sustituto_funcional        exit=0     58s  === RESULTADO: 20 correctas, 0 fallidas ===
sonda                      exit=0     30s  === RESULTADO: 43 correctas, 0 fallidas ===
seguridad                  exit=0     12s  === RESULTADO: 55 correctas, 0 fallidas ===
planta_seguro              exit=0     31s  === RESULTADO: 25 correctas, 0 fallidas ===
planta_control             exit=0     63s  === RESULTADO: 5 correctas, 0 fallidas ===
nube                       exit=0    220s  === RESULTADO: 28 correctas, 0 fallidas ===
vigila                     exit=0     50s  === RESULTADO: 12 correctas, 0 fallidas ===
desviador                  exit=0     70s  === RESULTADO: 19 correctas, 0 fallidas ===
hmi                        exit=0     25s  === RESULTADO: 25 correctas, 0 fallidas ===
diagnostico_a2             exit=0     33s  === RESULTADO: 19 correctas, 0 fallidas ===
instrumentacion_a2         exit=0    139s  === RESULTADO: 6 correctas, 0 fallidas ===
tablero                    exit=0     66s  === RESULTADO: 34 correctas, 0 fallidas ===
prueba_sh                  exit=0     58s  === RESULTADO: 26 correctas, 0 fallidas ===
reglas_a1                  exit=0      1s  50 casos, 0 discrepancias
reglas_proceso             exit=0      0s  33 casos, 0 discrepancias (emulador)
FIN: 0 fallidas
```

## Puntos en que la orden no coincidió con el código

1. S2: la orden lista cuatro esperas de `GET /settings`; la búsqueda no
   encontró más. Pero hay otros usos de la API de administración que la orden
   no lista: `POST /inject/<id>` en `pruebas/prueba.sh` (dos) y en
   `pruebas/prueba_diagnostico_a2.py` (dos). Se resolvieron con credenciales
   desechables.
2. S2: la página "Securing Node-RED" no documenta cómo deshabilitar el editor
   y la API; se usó `httpAdminRoot: false`, comprobado en el código de
   Node-RED 5.0.9 instalado.
3. S2: `ps.detiene()` mataba a los clientes conectados al 1881, no solo a
   Node-RED (corregido; no lo menciona la orden).
4. E1: de los archivos que la orden cita, solo tres enumeran valores
   permitidos (reglas, `33_nube_valida.js`, `prueba_nube.py`); los demás solo
   usan estados concretos, y `35_hmi_estado.js` y `37_diag_arma.js` ya
   traducían `emergencia`.
5. E2: el cambio de ritmo obligó a ajustar las secciones 1, 2 y 4 de
   `prueba_nube.py`, que suponían latidos de `A2_LATIDO_S` con la línea
   detenida.
6. U: la orden supone que basta actualizar lo que imprime kilogramos; el
   oráculo de `prueba_fio.py` comparaba **volts** contra `hasta_kg`, así que
   con 2 kg por volt habría marcado como mal clasificadas cajas bien
   clasificadas. Se corrigió para convertir con la plena escala.
7. U: `prueba_grafica.py` (fuera de la batería) falla en
   `la pagina tiene las mismas cajas que el emulador` también con el código de
   `266e697` (15 = 16): carrera entre la última muestra de la página y la
   última escritura de A2-Nube. Ya existía; no se corrigió en esta fase.
8. R: la orden pide N con diferencia relativa menor a 10^-9 frente al Anexo B,
   pero el anexo da N con 4 decimales (26737.4818 tiene una incertidumbre
   relativa de ~2·10^-9). Se comparó N a 4 decimales contra el anexo y JS
   contra Python con diferencia relativa < 10^-9; dD a 8 decimales.
9. R: la orden no nombra los códigos de rechazo nuevos; se agregaron
   `version_no_soportada`, `senal_plena_escala_obsoleta`,
   `niveles_desordenados` y `tolerancia_invalida`, con prueba de mutación.
10. R: "la tarjeta de la HMI no cambia", pero el bloqueo por `cfg_version`
    necesita su texto en inglés: se agregó solo esa entrada a la traducción
    de motivos de `42_mat_hmi.js`.
11. R: `tools/analiza_masas.py --verifica` comparaba D contra la cifra de la
    versión 1; ahora compara contra `tools/materiales.py` con la
    configuración vigente. `docs/corrida_L.md` (versión 1) no se regeneró.

# Fase 4 (`docs/ORDEN_A2_FASE_4.md`, 13 nov 2026; sesión del 17 nov 2026)

Puertas: V0, N0 y G0 abiertas como dice la orden; A0 abierta el 17 nov con Ari
frente a la Mac y su teléfono en la tailnet. `.env` sigue con `A2_NUBE=0`; la
nube se enciende solo en el archivo de variables de los pasos A, I y D.

| Paso | Estado | Respaldo |
|---|---|---|
| Inicio | commit `a2d22fa`: la orden | |
| A. Sesión con Ari | **detenido en A3 por la regla 6** (A1 y A2 pasan; decisión de Ari) | `docs/sesion_A.md`; A2 con la base real 4/4; batería: 1 falla intermitente de `/comms`, repetida 55/55 |
| B. `at_scale_entry` | **cerrado** | 20/20 lecturas en 1 con la escena reiniciada; ninguna cuenta del cliente depende de su polaridad; `prueba_mapa` OK; batería 0 fallidas |
| G. Geometría de la línea | **cerrado** (4 de 5 valores siguen estimados: el manual no documenta escala ni velocidad nominal) | `docs/corrida_G.md` reproducible; límites con margen 2.9 y 5.7 s; `limites_planta` igual; `cliente --cajas 200` 17/17; batería 0 fallidas |
| I. Corrida instrumentada con la nube | **cerrado** (aviso de unidad ausente por la ventana de 300 registros de la página) | 11/11 en el segundo intento (el primero, abortado por la espera de Chrome); `docs/corrida_a2_fase4.md`; 139 caja y 13 latido en `planta_01`; batería 0 fallidas |
| D. Ensayo con Gemini | **abierto en la verificación 1** (23/24: paso 6 por la espera de Chrome, corregida y comprobada con `--con-nube` 21/21; la consulta no se repite) | 1 consulta real, válida, mostrada; tope y 0 comandos; ensayo sin `--real` 19/0 tras pasar `--host` a la sonda; batería 0 fallidas |
| C. Carrera de la prueba de gráfica | **cerrado** | 5 corridas seguidas 8/8 (19 = 19); batería 0 fallidas, `prueba.sh` 26/26 |
| Cierre: orden | commit `7441521` | |
| Cierre: tres notas del registro | **hechas** (commit `2634f3d`) | latidos recontados: A 42, I 14; eventos de cajas en A3 |
| S. Stop con una lectura | **cerrado** (commit `49c018c`) | Stop 20/20 y Start 19/20 en la sesión; `prueba_tablero` 38/38 con mutación; batería: 1 falla intermitente de `/comms`, repetida 55/55 |
| H. Límites con tiempos medidos | **cerrado** (commit `3667d30`) | límites 4.81 y 2.56 s, márgenes 3.05 y 2.30 s; `prueba_limites_linea` 8/8; `cliente --cajas 200` 17/17 sin `caja_perdida`; batería 0 fallidas |
| D2. Segundo ensayo con Gemini | **cerrado** | 24/24 sin bloqueados; segunda consulta real válida; tope; 0 comandos |

## A. Sesión con Ari (17 nov 2026, 19:11 a 19:18 UTC)

### Antes de la sesión

- El directorio temporal del paso T
  (`/var/folders/.../a2_fio_tablero_rpqpnyql`, nombrado en la primera línea de
  `datos/corridas/T_2026-11-11/prueba_fio.log`) **existe pero está vacío**:
  el sistema limpió el directorio temporal el 15 nov. No hay CSV de sondeo de
  la ventana 21:10:12Z a 21:10:15Z del 11 nov.
- La misma limpieza dejó incompletas las paletas del userDir de pruebas
  (Node-RED no arrancaba: "Waiting for missing types ... modbus-client,
  ui-base"); se reinstalaron con `./prepara_a2.sh` (versiones fijas).
- La máquina virtual se había cerrado; Ari la encendió y puso la escena en
  Play antes de la sesión. No se tocó Parallels.

### Qué se hizo

- `pruebas/sesion_ari.py` (nuevo): reinicio de la escena por Modbus,
  A2-Planta con el cliente de Factory I/O y su propio `DATOS_DIR`, vigilante
  del tablero en este mismo proceso (conexión Modbus propia, cada ~15 ms) y
  observación de conexiones al puerto 1881 cada 2 s. La nube va encendida
  (`A2_NUBE=1`, `PLANTA_ID=planta_01`) en un archivo de variables fuera del
  repositorio que se borra al terminar; sin llave de Gemini. Cada parte dice
  en pantalla qué hacer, espera a verlo (o queda como bloqueada en su plazo) y
  al final Node-RED se detiene y el `DATOS_DIR` se copia a
  `datos/corridas/A_2026-11-17/` (eventos, CSV de sondeo, CSV de la nube,
  vigilante, conexiones, partes, bitácora de Node-RED).
- `tools/analiza_sesion_a.py` (nuevo) arma A1, A2 y los cuatro resultados de
  A3; `--base` lee los dos latidos de A2 de la base real con la cuenta del
  visor (sin imprimir credenciales). Definiciones: `docs/INSTRUMENTACION_A2.md`,
  sección 5, escritas antes de la sesión.
- Las tres partes se completaron con Ari. En A2 el primer intento quedó a la
  mitad porque el Emergency stop de Factory I/O se queda enclavado: el
  vigilante lo vio bajar y no volver; Ari le dio otro clic para soltarlo.

### Verificación

A1 (teléfono `iphone181`, 100.122.47.49): conexión de la tailnet distinta de
la Mac durante la parte, marcha y paro con origen `hmi` y 3 `paso_caja` entre
ambos. **Pasa** (verificaciones 1 y 2).

A2, con la lectura de la base (`tools/analiza_sesion_a.py
datos/corridas/A_2026-11-17 --base`, exit 0):

Paro de emergencia con la nube

| Comprobación | Resultado |
|---|---|
| Emergency stop visto por el vigilante (baja, sube, duración s) | 2026-11-17T19:14:03.494Z → 2026-11-17T19:15:18.203Z (74.709) |
| `paro_de_emergencia` / `emergencia_liberada` del cliente | 2026-11-17T19:14:03.562Z / 2026-11-17T19:15:18.284Z |
| Latido aceptado (HTTP 200) tras el paro: registro, escritura, retraso | -P6evYoK5VkwRMUAnCCu, 2026-11-17T13:14:04.155-06:00, 0.593 s |
| Latido aceptado tras la liberación: registro, escritura, retraso | -P6evq9cSGNWo-YGBCyG, 2026-11-17T13:15:19.217-06:00, 0.933 s |
| Registros `caja` aceptados en la sesión / `paso_caja` | 21 / 21 (cajas descartadas por la emergencia: ninguna) |
| Verificación 1 / 2 / 4 | pasa / pasa / pasa |
| Base real, registro -P6evYoK5VkwRMUAnCCu | latido (sin `caja_masa_kg`; el registro no tiene campo `tipo`), estado_linea `emergencia`; campos cajas_acumuladas, estado_linea, peso_V, ts_escritura, ts_origen, vel_banda_V |
| Base real, registro -P6evq9cSGNWo-YGBCyG | latido (sin `caja_masa_kg`; el registro no tiene campo `tipo`), estado_linea `detenida`; campos cajas_acumuladas, estado_linea, peso_V, ts_escritura, ts_origen, vel_banda_V |
| Verificación 3 | pasa |

A3 (`docs/sesion_A.md`, resultados completos):

- 43 pulsaciones vistas: Start 23 vistas y 21 registradas; Stop 20 vistas y
  16 registradas. Con las tres del paso T, Start 26 vistas y 23 registradas.
- Periodo de sondeo de toda la sesión: n 8679, mediana 52 ms, p95 53 ms,
  máximo 81 ms, 0 periodos de 300 ms o más.
- Las 6 pulsaciones sin evento duraron de 63 a 98 ms y **ninguna cae en un
  hueco de sondeo**. Inicios de ciclo de sondeo dentro de cada pulsación:
  con 1 inicio, 0 registradas y 2 sin evento; con 2, 16 y 4; con 3 o más, 21
  y 0. El cliente acepta un cambio de entrada solo tras
  `lecturas_para_cambio` = 2 lecturas seguidas (`28_planta_lectura.js`,
  antirrebote); con el sondeo de ~52 ms, una pulsación de menos de ~100 ms
  puede quedar en una sola lectura.
- `tools/analiza_sesion_a.py` vuelto a correr sobre la carpeta da el mismo
  `docs/sesion_A.md` (`cmp` sin diferencias).

### Conclusión y detención

La conclusión que arma la herramienta es "pulsación sin evento y sin hueco de
sondeo". Por la regla 6 de la orden **el paso A se detiene aquí con la
evidencia** y la decisión es de Ari: no se cambió el cliente. La hipótesis de
la orden (un hueco de sondeo como el de 668 ms del 25 oct) queda descartada
para esta sesión; lo que muestran los datos es que las pulsaciones sin evento
son las más cortas que el antirrebote de dos lecturas.

Batería completa después de A (`bateria.sh --con-emulador`):

```
mapa                       exit=0      0s  OK
materiales_modelo          exit=0      3s  === RESULTADO: 42 correctas, 0 fallidas ===
materiales_flujo           exit=0    438s  === RESULTADO: 36 correctas, 0 fallidas ===
limites                    exit=0      0s  
sustituto_funcional        exit=0     57s  === RESULTADO: 20 correctas, 0 fallidas ===
sonda                      exit=0     31s  === RESULTADO: 43 correctas, 0 fallidas ===
seguridad                  exit=1      8s  === RESULTADO: 54 correctas, 1 fallidas ===
planta_seguro              exit=0     30s  === RESULTADO: 25 correctas, 0 fallidas ===
planta_control             exit=0     63s  === RESULTADO: 5 correctas, 0 fallidas ===
nube                       exit=0    220s  === RESULTADO: 28 correctas, 0 fallidas ===
vigila                     exit=0     50s  === RESULTADO: 12 correctas, 0 fallidas ===
desviador                  exit=0     69s  === RESULTADO: 19 correctas, 0 fallidas ===
hmi                        exit=0     26s  === RESULTADO: 25 correctas, 0 fallidas ===
diagnostico_a2             exit=0     33s  === RESULTADO: 19 correctas, 0 fallidas ===
instrumentacion_a2         exit=0    139s  === RESULTADO: 6 correctas, 0 fallidas ===
tablero                    exit=0     66s  === RESULTADO: 34 correctas, 0 fallidas ===
prueba_sh                  exit=0     59s  === RESULTADO: 26 correctas, 0 fallidas ===
reglas_a1                  exit=0      0s  50 casos, 0 discrepancias
reglas_proceso             exit=0      0s  33 casos, 0 discrepancias (emulador)
FIN: 1 fallidas
```

La falla es otra vez el control autenticado de `/comms` en
`prueba_seguridad.py` (`{"auth":"fail"}` con un token recién emitido que
`GET /flows` sí aceptó). Antes de repetirla, como pide la regla 8, el almacén
de sesiones del editor del userDir de pruebas (`.sessions.json`, leído sin
imprimir ningún token) tenía **10 sesiones de 3 usuarios desechables
distintos, ninguna vencida, todas con vencimiento el 24 nov 2026 entre las
19:26 y las 19:44 UTC**. La repetición inmediata de `prueba_seguridad.py`
pasó 55/55. La batería completa del paso B (abajo) vuelve a correr todo.

```
```

## B. Descripción de `at_scale_entry`

### Qué se hizo

- Escena recién reiniciada por Modbus (`node tools/reinicia_escena.mjs
  10.211.55.3 502 --mapa config/mapa_registros_fio.json`, exit 0: Reset, vacía
  y Run), línea detenida (`entry_conveyor` = 0) y sin Node-RED; veinte
  lecturas con `tools/sonda_modbus.py ... lee at_scale_entry`:

  ```
  20 x at_scale_entry = 1   (entrada discreta 0)
  ```

  Las veinte en 1. El reinicio comprueba vacías la báscula, el desviador, las
  ramas y las salidas, no la banda de entrada; con esa banda detenida no llega
  ninguna caja al sensor.
- `config/mapa_registros_fio.json`: la descripción pasa de "caja a la entrada
  de la bascula" a "NC, baja a 0 cuando pasa una caja a la entrada de la
  bascula", con la forma de `at_exit_left`, `at_exit_front` y `at_exit_right`.
  `docs/MAPA_REGISTROS.md` regenerado con `python3 tools/mapa_registros.py
  doc`. Solo cambia el texto; el mapa no tiene campo de polaridad para ese
  sensor.

### Dónde usa el cliente el rol `entrada` y si depende de la polaridad

`config/planta_fio.json` asigna el rol `entrada` a `at_scale_entry` y tiene
`bascula.pesaje_detenido`. En `28_planta_lectura.js`, con pesaje detenido, el
flanco de `entrada` se descarta (`else if (D && f.s === R.entrada) continue;`)
y la caja nace en el flanco de subida de `at_scale` (`en_bascula`). Las ramas
que cuentan cajas con el flanco de `entrada` (`f.valor` 1 = caja nueva, 0 =
caja en báscula) solo corren sin pesaje detenido, que no es el caso de la
escena real. En `26_planta_config.js` el sensor está en la lista de
antirrebote y en la regla de factibilidad como banda "medida": se comparan
contra t_min tanto `encendido_min_s` (0.41 s) como `apagado_min_s` (0.55 s),
medidos el 24 oct leyendo el 1 como caja presente. Con el sensor NC esos dos
números quedan intercambiados (el 0.55 s es el pulso de caja y el 0.41 s el
hueco), y como la regla exige los dos, el veredicto no cambia. **Ninguna cuenta
del cliente depende de la polaridad de este sensor con la configuración de la
escena**, así que no hay nada que detener.

### Nota sobre la fase 2

La frase de la fase 2 "las cajas se forman pegadas en la banda de entrada:
`at_scale_entry` no baja entre una y otra" (sección R2 con el mapa real), y
"pasa casi todo el tiempo en 1 (las cajas se forman en fila)" (vigila del 24
oct), **venían de leer ese sensor al revés**: en 1 está libre. El comentario
equivalente de `28_planta_lectura.js` es lógica del cliente y no se tocó
(regla 6).

### Verificación

`pruebas/prueba_mapa.py` corre en la batería (abajo); la documentación
regenerada coincide con el mapa (`tools/mapa_registros.py doc` dos veces, sin
diferencias en `git diff` entre ellas).

Batería completa al cerrar B (`bateria.sh --con-emulador`):

```
mapa                       exit=0      0s  OK
materiales_modelo          exit=0      3s  === RESULTADO: 42 correctas, 0 fallidas ===
materiales_flujo           exit=0    433s  === RESULTADO: 36 correctas, 0 fallidas ===
limites                    exit=0      0s  
sustituto_funcional        exit=0     58s  === RESULTADO: 20 correctas, 0 fallidas ===
sonda                      exit=0     30s  === RESULTADO: 43 correctas, 0 fallidas ===
seguridad                  exit=0     12s  === RESULTADO: 55 correctas, 0 fallidas ===
planta_seguro              exit=0     30s  === RESULTADO: 25 correctas, 0 fallidas ===
planta_control             exit=0     63s  === RESULTADO: 5 correctas, 0 fallidas ===
nube                       exit=0    222s  === RESULTADO: 28 correctas, 0 fallidas ===
vigila                     exit=0     50s  === RESULTADO: 12 correctas, 0 fallidas ===
desviador                  exit=0     70s  === RESULTADO: 19 correctas, 0 fallidas ===
hmi                        exit=0     26s  === RESULTADO: 25 correctas, 0 fallidas ===
diagnostico_a2             exit=0     34s  === RESULTADO: 19 correctas, 0 fallidas ===
instrumentacion_a2         exit=0    138s  === RESULTADO: 6 correctas, 0 fallidas ===
tablero                    exit=0     66s  === RESULTADO: 34 correctas, 0 fallidas ===
prueba_sh                  exit=0     59s  === RESULTADO: 26 correctas, 0 fallidas ===
reglas_a1                  exit=0      1s  50 casos, 0 discrepancias
reglas_proceso             exit=0      0s  33 casos, 0 discrepancias (emulador)
FIN: 0 fallidas
```

## G. Geometría de la línea y velocidad de banda

### Qué se hizo

- Definiciones antes de medir: `docs/INSTRUMENTACION_A2.md`, sección 6.
- `pruebas/registra_flancos.py` (nuevo, solo lee): proceso separado del
  cliente, conexión Modbus propia, cada ~10 ms las entradas 0 a 8 y las
  bobinas `entry_conveyor` y `load_scale`; 42,212 lecturas en la corrida.
- Corrida G: `prueba_fio.py cliente --cajas 150` (sin nube) con el registrador
  en paralelo, 17/17 (150 cajas por la salida de su peso, sin desvíos,
  pérdidas ni fantasmas). Todo en `datos/corridas/G_2026-11-17/` (eventos, CSV
  de sondeo, oráculo, flancos, bitácora).
- `tools/mide_linea.py` (nuevo) → `docs/corrida_G.md`. La primera versión
  emparejaba la entrada de cada rama con la siguiente bajada de su salida, que
  a veces era de la caja anterior; se cambió a orden FIFO antes de usar las
  cifras.
- Manual de Factory I/O (consultado el 17 nov 2026): la página de partes
  ligeras da longitudes de banda (2, 4 y 6 m) y la velocidad **máxima** (0.6
  m/s en digital); la de artículos da pesos y no dimensiones; ninguna página
  consultada (partes ligeras, artículos, sensores, edición) documenta la
  escala de las posiciones del archivo de escena ni una velocidad nominal.
  Por la orden, no se supuso ninguna: las posiciones se reportan en unidades
  de la escena y los tiempos medidos, y esos valores siguen estimados.

### Los cinco valores de `linea`, antes y después

| Clave | Antes | Después | Fuente |
|---|---|---|---|
| `velocidad_fija_m_s` | 0.3 | 0.3 (estimado) | sin escala ni velocidad nominal documentadas; tiempos de banda de rama medidos: mediana 4.14 a 4.41 s |
| `intervalo_emision_min_s` | 2.1 | **1.908** (medido) | menor intervalo entre `caja_entra` consecutivos con el cliente controlando: G 2.188, L1 1.999, L2 2.068, M1 1.908 s; emisor de la escena 1 a 2 s |
| `largo_caja_m` | 0.4 | 0.4 (estimado) | sin velocidad medida; pulsos del sensor de rama por tipo de pieza: mediana 0.50 a 0.67 s |
| `entrada_a_fin_bascula_m` | 1.2 | 1.2 (estimado) | sin escala documentada; 11.0 unidades de la escena entre `at_scale_entry` y `at_scale_exit` |
| `fin_bascula_a_confirmacion_m` | 0.9 | 0.9 (estimado) | sin escala documentada; 8.0 a 11.3 unidades de la escena; tiempo `at_scale_exit` → rama, mediana 0.67 a 0.96 s |

**Cuál fuente del intervalo usa la regla.** En `26_planta_config.js` y
`tools/limites_planta.py`, `intervalo_emision_min_s` (dt) es la separación
mínima entre dos cajas consecutivas en un sensor: con una banda de tiempos
calculados, el sensor queda apagado `dt − encendido`. Eso corresponde a las
fuentes (a) y (b), medidas en un sensor con el cliente controlando la línea,
y no al emisor de la escena (c), cuyo ritmo se pierde en la fila de la banda
de entrada y en las paradas de pesaje. En la escena real los seis sensores de
`linea.sensores` son de banda "medida", para la que la regla usa los mínimos
medidos de encendido y apagado y no usa dt: el cambio no altera ningún
veredicto.

### Verificación

1. `tools/mide_linea.py datos/corridas/G_2026-11-17` vuelto a correr da el
   mismo `docs/corrida_G.md` (`cmp` sin diferencias).
2. Límites derivados de `linea` con los valores nuevos contra el máximo
   observado en su tramo: `timeout_confirmacion_s` 4.670 s contra 1.745 s
   (margen 2.925 s); `no_llego_a_fin_bascula` 6.165 s contra 0.426 s (margen
   5.739 s). Los dos cumplen.
3. `tools/limites_planta.py --config config/planta_fio.json`, escenario
   `parallels`, antes y después: salida idéntica (`diff` sin diferencias).

```
escenario parallels      sondeo   50 ms, rtt    5 ms, refresco   33 ms -> T_ef 55 ms (medido), 3 lecturas = 0.17 s
    at_forward_entry banda medida       encendido 0.39 s, apagado >= 7.29 s  cumple
    at_left_entry   banda medida       encendido 0.46 s, apagado >= 1.94 s  cumple
    at_right_entry  banda medida       encendido 0.25 s, apagado >= 1.54 s  cumple
    at_scale        banda medida       encendido 1.39 s, apagado >= 0.46 s  cumple
    at_scale_entry  banda medida       encendido 0.41 s, apagado >= 0.55 s  cumple
    at_scale_exit   banda medida       encendido 0.51 s, apagado >= 1.62 s  cumple
    bandas de velocidad fija: factible
```

4. `prueba_fio.py cliente --cajas 200` con la configuración nueva:

```
$ caffeinate -d /usr/bin/python3 -u pruebas/prueba_fio.py cliente --cajas 200 --host 10.211.55.3 --puerto 502   -> exit 0
=== A2-Planta contra Factory I/O (Node-RED -> 10.211.55.3:502; oraculo por 10.211.55.3:502; datos en /var/folders/6y/56sny62s59j98r894dbqq9y00000gn/T/a2_fio_cliente_isa54d6_) ===
  OK    escena reiniciada por Modbus: Reset, vacia y Run (codigo 0)
  OK    A2-Planta conecta con la escena (com ok)
  OK    limites factibles con sondeo 50 ms (T_ef 55 ms)
  OK    marcha -> 200
    oraculo: 201 cajas soltadas, 200 salidas NC; cliente: 201 pasos
  OK    al menos 15 cajas clasificadas en 1720 s (200)
  OK    cada caja sale por la salida de su peso (oraculo): 200 de 200 (0 sin peso del oraculo)
  OK    las tres salidas se usan
  OK    el cliente reporta el mismo destino que la salida real, caja por caja (200)
  OK    pesos del cliente = pesos del oraculo (+-0.05 V) en las 183 cajas quietas
  OK    y la misma clase en todas las que el oraculo peso (200)
  OK    ninguna caja se cae ni se atora: 198 soltadas con mas de 12 s antes del paro, 200 salidas
  OK    200 cajas por la salida de su peso (200)
  OK    T_ef sale de lo medido (55 ms, medido)
  OK    cada pulso de los sensores de rama visto en al menos 3 lecturas {'at_left_entry': 9, 'at_forward_entry': 7, 'at_right_entry': 9}
  OK    sin desvios erroneos, perdidas ni fantasmas (0 / 0 / 0)
  OK    bajo control, todo sensor seguido dura al menos t_min encendido y apagado
  OK    el cliente vio cada pulso en al menos 3 lecturas
=== RESULTADO: 17 correctas, 0 fallidas ===
exit 0
```

5. Batería completa:

```
mapa                       exit=0      0s  OK
materiales_modelo          exit=0      3s  === RESULTADO: 42 correctas, 0 fallidas ===
materiales_flujo           exit=0    439s  === RESULTADO: 36 correctas, 0 fallidas ===
limites                    exit=0      0s  
sustituto_funcional        exit=0     57s  === RESULTADO: 20 correctas, 0 fallidas ===
sonda                      exit=0     31s  === RESULTADO: 43 correctas, 0 fallidas ===
seguridad                  exit=0     12s  === RESULTADO: 55 correctas, 0 fallidas ===
planta_seguro              exit=0     30s  === RESULTADO: 25 correctas, 0 fallidas ===
planta_control             exit=0     64s  === RESULTADO: 5 correctas, 0 fallidas ===
nube                       exit=0    220s  === RESULTADO: 28 correctas, 0 fallidas ===
vigila                     exit=0     50s  === RESULTADO: 12 correctas, 0 fallidas ===
desviador                  exit=0     69s  === RESULTADO: 19 correctas, 0 fallidas ===
hmi                        exit=0     26s  === RESULTADO: 25 correctas, 0 fallidas ===
diagnostico_a2             exit=0     33s  === RESULTADO: 19 correctas, 0 fallidas ===
instrumentacion_a2         exit=0    139s  === RESULTADO: 6 correctas, 0 fallidas ===
tablero                    exit=0     66s  === RESULTADO: 34 correctas, 0 fallidas ===
prueba_sh                  exit=0     58s  === RESULTADO: 26 correctas, 0 fallidas ===
reglas_a1                  exit=0      1s  50 casos, 0 discrepancias
reglas_proceso             exit=0      0s  33 casos, 0 discrepancias (emulador)
FIN: 0 fallidas
```

## I. Corrida instrumentada con la nube

### Qué se hizo

- `pruebas/corrida_c9_real.py` gana cuatro variables de entorno para no
  sobrescribir lo del 25 oct: `C9_REPORTE` (→ `docs/corrida_a2_fase4.md`),
  `C9_IMAGEN` (→ `docs/img/grafica_fase4.png`), `C9_DATOS` (directorio de datos
  propio, fuera del repo) y `C9_COPIA` (→ `datos/corridas/I_2026-11-17/`, que
  recibe eventos, CSV de sondeo, CSV de la nube, `proceso_c9.csv` y la
  bitácora). La nube va encendida solo en el entorno de Node-RED de la
  corrida (`A2_NUBE=1`, `PLANTA_ID=planta_01`, credenciales tomadas de `.env`
  sin imprimirse); `.env` no se tocó.
- **Primer intento, abortado a los 40 s**: el observador de la página
  (`cdp_mira.mjs`) falló con `ECONNREFUSED 127.0.0.1:9334` porque Chrome sin
  ventana tardó más de los 4 s fijos que esperaba el script. Sin ese observador
  la parte de la gráfica no podía pasar, así que se detuvo con Ctrl-C (Node-RED
  quedó detenido por el `finally`). Alcanzó a escribir **7 registros `caja` y 2
  `latido`** en `planta_01`; su carpeta quedó en
  `datos/corridas/I_2026-11-17_intento1/`. Corrección (una): esperar a que
  DevTools liste la página, hasta 30 s, como `prueba_grafica.py`.
- Segundo intento, completo:

```
=== C9 contra Factory I/O (10.211.55.3) escribiendo en planta_01 de la base real; C8 con la grafica ===
  OK    escena reiniciada por Modbus (codigo 0)
  OK    A2-Planta conecta con la escena
  OK    limites factibles, T_ef de lo medido (55 ms)
  OK    marcha -> 200
  OK    0 desvios erroneos, 0 perdidas, 0 fantasmas (0 / 0 / 0)
  OK    exporta_corrida --rama proceso (codigo 0)
      latidos en la ventana: 11
  OK    analiza_corrida --a2 (codigo 0) -> docs/corrida_a2_fase4.md
  OK    completitud: 132 cajas en Firebase = 132 confirmadas por A2-Planta
  OK    la pagina inicio sesion como visor real y lee sin error
  OK    las cajas subieron durante la corrida sin recargar (28 -> 160, 0 navegaciones)
  OK    al final la pagina tiene las cajas de la corrida que estan en Firebase (160 >= 132)
    ventana: 2026-11-17T20:59:44.467Z a 2026-11-17T21:09:46.699Z
    registros escritos en la ventana: 132 caja, 11 latido
=== RESULTADO: 11 correctas, 0 fallidas ===
exit 0
```

### Verificación

1. 11 de 11 comprobaciones del script (igual que el 25 oct).
2. `docs/corrida_a2_fase4.md` trae las tres cifras con las mismas definiciones
   y `tools/analiza_corrida.py --a2`, junto a la tabla del 25 oct (copiada sin
   cambios de `docs/corrida_a2.md`, que no se tocó): periodo de sondeo mediana
   52.0 ms, p95 54.0 ms, máximo 159 ms (el 25 oct, 668 ms); latencia mediana
   53.0 ms, p95 57.0 ms; completitud 132/132.
3. El perfil de Chrome y la captura original quedan en `mkdtemp` fuera del
   repo (cambio del commit `3d8a37e`); `git status` después de la corrida solo
   muestra el reporte, la imagen y las carpetas de la corrida (más la del
   intento abortado y los scripts modificados de esta fase). Con eso se cierra
   el punto de `3d8a37e`.
4. La página leyó con la cuenta real del visor, sin error, 0 navegaciones
   después de la primera carga, y contó las cajas de la corrida (28 → 160; 160
   ≥ 132 en Firebase). La captura muestra las masas a 2 kg por volt (3, 5, 7,
   8, 10 y 15 kg). **El aviso de los registros anteriores al cambio de unidad
   no aparece**: `web/proceso.html` lee solo los últimos 300 registros
   (`limitToLast(C.muestras || 300)`), y desde las 429 cajas del 25 oct hay
   unos 21,700 latidos de noviembre en `planta_01`; los 300 que ve la página
   son todos del 17 nov. Vale el código: la página no se cambió.
5. Node-RED quedó detenido (`lsof` sin nada escuchando en 1881). Escritos en
   la ventana: 132 `caja` y 11 `latido`; con el intento abortado, el paso I
   escribió 139 `caja` y 13 `latido` en `planta_01`.

Batería completa al cerrar I:

```
mapa                       exit=0      0s  OK
materiales_modelo          exit=0      3s  === RESULTADO: 42 correctas, 0 fallidas ===
materiales_flujo           exit=0    437s  === RESULTADO: 36 correctas, 0 fallidas ===
limites                    exit=0      0s  
sustituto_funcional        exit=0     58s  === RESULTADO: 20 correctas, 0 fallidas ===
sonda                      exit=0     31s  === RESULTADO: 43 correctas, 0 fallidas ===
seguridad                  exit=0     12s  === RESULTADO: 55 correctas, 0 fallidas ===
planta_seguro              exit=0     30s  === RESULTADO: 25 correctas, 0 fallidas ===
planta_control             exit=0     64s  === RESULTADO: 5 correctas, 0 fallidas ===
nube                       exit=0    221s  === RESULTADO: 28 correctas, 0 fallidas ===
vigila                     exit=0     50s  === RESULTADO: 12 correctas, 0 fallidas ===
desviador                  exit=0     68s  === RESULTADO: 19 correctas, 0 fallidas ===
hmi                        exit=0     26s  === RESULTADO: 25 correctas, 0 fallidas ===
diagnostico_a2             exit=0     33s  === RESULTADO: 19 correctas, 0 fallidas ===
instrumentacion_a2         exit=0    139s  === RESULTADO: 6 correctas, 0 fallidas ===
tablero                    exit=0     66s  === RESULTADO: 34 correctas, 0 fallidas ===
prueba_sh                  exit=0     59s  === RESULTADO: 26 correctas, 0 fallidas ===
reglas_a1                  exit=0      0s  50 casos, 0 discrepancias
reglas_proceso             exit=0      0s  33 casos, 0 discrepancias (emulador)
FIN: 0 fallidas
```

## D. Ensayo con una consulta real a Gemini

### Qué se hizo

- `pruebas/ensayo_demo.py --real --con-gemini` (opción nueva): el archivo de
  variables del ensayo (fuera del repo, borrado al terminar) conserva la llave
  de `.env`, enciende la nube (`A2_NUBE=1`, `PLANTA_ID=planta_01`) y lleva
  `A2_DIAG_MAX_DIA=1`. **Discrepancia con la orden**: la pestaña de diagnóstico
  de la Actividad 1 comparte la llave y `FIREBASE_DB_URL`, y su inject de 30 min
  tiene `once: true`, así que con la llave haría su propia consulta al
  arrancar. `DIAG_MAX_DIA=0` no la frena (`11_arma_prompt.js` hace
  `Number(...) || 200`); se puso `DIAG_MAX_DIA=-1`, con lo que esa pestaña se
  detiene en su freno de tope diario sin consultar. El paso 7 presiona el
  botón una vez y, pasados 65 s (el limitador "máximo 1 por minuto" de
  A2-Diagnóstico **descarta**, `drop: true`, lo que llega antes), una segunda
  vez.
- Una sola consulta real en toda la fase, la de este ensayo:

```
OK    la HMI vuelve a abrir (Online)
    a2_diagnosticos: ['2026-11-17T21:36:42.348Z;hmi;gemini-3.1-flash-lite;1252;valido;;normal;mantener;;432']
    modelo gemini-3.1-flash-lite, latencia 1252 ms, nivel normal, accion mantener
    texto: The system is operating normally with 9 boxes sorted and 0 lost. The 3-way wheel diverter is functioning correctly across all destinations. The mean mass is 7.88 kg with a standard deviation of 3.69 kg, indicating stable processing within the 46-second runtime.
    justificacion: All performance metrics are within expected operational parameters with zero errors or misrouted items reported.
  OK    una consulta real: una sola fila con respuesta del modelo, valida, y la HMI la muestra
    espera 63 s para que el limitador de 1 por minuto no descarte la segunda pulsacion
  OK    la segunda pulsacion se detiene en el tope diario: sigue habiendo una sola fila (ninguna salida a la red) y la HMI muestra el mismo diagnostico valido
  OK    en los 30 s siguientes al diagnostico no hay ningun comando (0)
  OK    la pestana de diagnostico de la Actividad 1 no consulto (sin diagnosticos_*.csv: [])
```

  Modelo `gemini-3.1-flash-lite`, latencia 1252 ms, 432 tokens. Texto de la
  respuesta (inglés, como la pide el prompt): "The system is operating
  normally with 9 boxes sorted and 0 lost. The 3-way wheel diverter is
  functioning correctly across all destinations. The mean mass is 7.88 kg with
  a standard deviation of 3.69 kg, indicating stable processing within the
  46-second runtime." La llave no se imprimió; la carpeta del ensayo quedó en
  `datos/corridas/D_2026-11-17/` sin el archivo de variables.

### Verificación

1. **No pasa completa**: el ensayo con la consulta dio 23 de 24, sin pasos
   bloqueados. Falló el paso 6 (gráfica en vivo): `cdp_mira.mjs` no tuvo ni
   una muestra. Ese camino nunca había corrido (en octubre la nube estaba
   apagada y el paso salía bloqueado) y tenía la misma espera fija de 4 s a
   Chrome que hizo fallar el primer intento de I. Por la regla 3 la consulta
   no se repite, así que el ensayo con Gemini no se volvió a correr. Corrección
   (una): esperar a que DevTools liste la página, hasta 30 s, e imprimir el
   error de `cdp_mira` si lo hay; comprobada con `--real --con-nube` (opción
   nueva: nube encendida, sin llave ni consulta), 21/21, sin bloqueados, con
   la gráfica de 190 a 202 cajas y 0 navegaciones.

```
=== 0. Antes de grabar (Factory I/O en 10.211.55.3 por el relevo 127.0.0.1:5030) ===
  OK    ./demo_a2.sh --revisa: limites factibles, Modbus contesta, sesion de Firebase
=== 1. Arquitectura: ./demo_a2.sh (reinicia la escena por Modbus) ===
  OK    demo_a2.sh arranca todo sin fallas y reinicia la escena
  OK    imprime las URL de la HMI y de la grafica
=== 2. Factory I/O corriendo ===
  OK    A2-Planta: com ok, desviador, factible con T_ef medido (55 ms)
=== 3. HMI: marcha y paro ===
  OK    la HMI abre y dice Online / Stopped
  OK    Start -> 200
  OK    Emitter ON -> 422 sin_emisor (la escena emite sola)
  OK    comando rechazado visible: consigna con bandas fijas -> 422 velocidad_no_aplica
=== 4. Cajas clasificadas (y vigila del paso 2) ===
  OK    sonda vigila ve cambiar sensores con la linea en marcha
  OK    la HMI cuenta cajas clasificadas por destino y 0 perdidas
=== 5. Registros llegando a Firebase ===
  OK    la HMI dice que la nube esta encendida y muestra el ultimo registro aceptado
=== 6. Grafica en vivo (visor real, sin recargar) ===
  OK    http://localhost:8123/proceso.html se sirve (200)
  FALLA la grafica lee como visor real y sube sin recargar ([] -> [] cajas, [] navegaciones) None
=== 7. Diagnostico ===
  OK    la HMI vuelve a abrir (Online)
  OK    una consulta real: una sola fila con respuesta del modelo, valida, y la HMI la muestra
  OK    la segunda pulsacion se detiene en el tope diario: sigue habiendo una sola fila (ninguna salida a la red) y la HMI muestra el mismo diagnostico valido
  OK    en los 30 s siguientes al diagnostico no hay ningun comando (0)
  OK    la pestana de diagnostico de la Actividad 1 no consulto (sin diagnosticos_*.csv: [])
=== 8. Estado seguro: desconexion y recuperacion ===
  OK    la HMI dice NO COMMUNICATION en 2.0 s (< timeout_com_ms + 1 s)
  OK    Start -> 409 sin_comunicacion en pantalla
  OK    al volver: Online y Stopped, sin reanudar sola
  OK    eventos: reconexion_inicia, 8 escrituras seguras (bandas y ruedas) en orden, reconexion_completa
  OK    Start vuelve a funcionar
=== 9. Cierre ===
  OK    ./demo_a2.sh --apaga deja libres el 1881 y el 8123
Bloqueados: 0
=== RESULTADO: 23 correctas, 1 fallidas ===
```

```
$ /usr/bin/python3 -u pruebas/ensayo_demo.py --real --con-nube      -> exit 0
  OK    ./demo_a2.sh --revisa: limites factibles, Modbus contesta, sesion de Firebase
  OK    demo_a2.sh arranca todo sin fallas y reinicia la escena
  OK    imprime las URL de la HMI y de la grafica
  OK    A2-Planta: com ok, desviador, factible con T_ef medido (55 ms)
  OK    la HMI abre y dice Online / Stopped
  OK    Start -> 200
  OK    Emitter ON -> 422 sin_emisor (la escena emite sola)
  OK    comando rechazado visible: consigna con bandas fijas -> 422 velocidad_no_aplica
  OK    sonda vigila ve cambiar sensores con la linea en marcha
  OK    la HMI cuenta cajas clasificadas por destino y 0 perdidas
  OK    la HMI dice que la nube esta encendida y muestra el ultimo registro aceptado
  OK    http://localhost:8123/proceso.html se sirve (200)
  OK    la grafica lee como visor real y sube sin recargar (190 -> 202 cajas, 0 navegaciones)
  OK    la HMI vuelve a abrir (Online)
  OK    sin llave en el ensayo, el boton no consulta y la HMI no muestra nada invalido
  OK    la HMI dice NO COMMUNICATION en 2.0 s (< timeout_com_ms + 1 s)
  OK    Start -> 409 sin_comunicacion en pantalla
  OK    al volver: Online y Stopped, sin reanudar sola
  OK    eventos: reconexion_inicia, 8 escrituras seguras (bandas y ruedas) en orden, reconexion_completa
  OK    Start vuelve a funcionar
  OK    ./demo_a2.sh --apaga deja libres el 1881 y el 8123
Bloqueados: 0
=== RESULTADO: 21 correctas, 0 fallidas ===
```

2. Exactamente una consulta real: `a2_diagnosticos_2026-11-17.csv` del
   ensayo tiene una sola fila, `valido` (pasó `38_diag_valida.js`), y la HMI la
   mostró. Pasa.
3. La segunda pulsación, a los 65 s, se detuvo en el tope (sigue una sola
   fila: cualquier respuesta o error de red deja fila en ese CSV) y la HMI
   siguió mostrando el mismo diagnóstico válido. Pasa.
4. En los 30 s siguientes al diagnóstico no hubo ningún `comando` en
   `a2_planta_eventos.jsonl`. Pasa. La pestaña de la Actividad 1 tampoco
   consultó (no hay `diagnosticos_*.csv`).
5. El ensayo sin la opción y sin `--real` falló al principio 18/19: la sonda
   del paso 4 se llamaba sin `--host` y tomaba `A2_MODBUS_HOST` de `.env`
   (10.211.55.3, la VM) en lugar del proxy local del sustituto; no viene de
   esta fase (`main()` no cambió). Con `--host 127.0.0.1` en esa llamada:

```
$ /usr/bin/python3 -u pruebas/ensayo_demo.py                         -> exit 0
  BLOQ  Factory I/O real con Sorting by Weight (PUERTA ARI R0 (mapa) y R1 (VM offline))
  BLOQ  registros en la consola de Firebase (PUERTA ARI P1 (publicar reglas) y A2_NUBE=1)
  BLOQ  grafica con datos reales (PUERTA ARI P1; probada contra el emulador en C8 (6/7))
Bloqueados por puertas de Ari: 3
=== RESULTADO: 19 correctas, 0 fallidas ===
```

Registros escritos en `planta_01` en el paso D: 22 `caja` y 6 `latido`
(ensayo con Gemini) más 21 `caja` y 5 `latido` (comprobación `--con-nube`).

Batería completa al cerrar D:

```
mapa                       exit=0      0s  OK
materiales_modelo          exit=0      4s  === RESULTADO: 42 correctas, 0 fallidas ===
materiales_flujo           exit=0    441s  === RESULTADO: 36 correctas, 0 fallidas ===
limites                    exit=0      0s  
sustituto_funcional        exit=0     58s  === RESULTADO: 20 correctas, 0 fallidas ===
sonda                      exit=0     31s  === RESULTADO: 43 correctas, 0 fallidas ===
seguridad                  exit=0     12s  === RESULTADO: 55 correctas, 0 fallidas ===
planta_seguro              exit=0     30s  === RESULTADO: 25 correctas, 0 fallidas ===
planta_control             exit=0     64s  === RESULTADO: 5 correctas, 0 fallidas ===
nube                       exit=0    222s  === RESULTADO: 28 correctas, 0 fallidas ===
vigila                     exit=0     50s  === RESULTADO: 12 correctas, 0 fallidas ===
desviador                  exit=0     68s  === RESULTADO: 19 correctas, 0 fallidas ===
hmi                        exit=0     26s  === RESULTADO: 25 correctas, 0 fallidas ===
diagnostico_a2             exit=0     33s  === RESULTADO: 19 correctas, 0 fallidas ===
instrumentacion_a2         exit=0    139s  === RESULTADO: 6 correctas, 0 fallidas ===
tablero                    exit=0     66s  === RESULTADO: 34 correctas, 0 fallidas ===
prueba_sh                  exit=0     59s  === RESULTADO: 26 correctas, 0 fallidas ===
reglas_a1                  exit=0      0s  50 casos, 0 discrepancias
reglas_proceso             exit=0      0s  33 casos, 0 discrepancias (emulador)
FIN: 0 fallidas
```

## Fase 4: puntos en que la orden no coincidió con el código (o con el entorno)

1. A: el directorio temporal del paso T existe pero está vacío (el sistema
   limpió el directorio temporal el 15 nov); no hay CSV de sondeo de la
   pulsación sin evento del 11 nov. La misma limpieza dejó incompletas las
   paletas del userDir de pruebas; se reinstalaron con `./prepara_a2.sh`.
2. A2, verificación 3: los registros de `proceso` no tienen campo `tipo`; el
   código distingue el latido porque no trae `caja_masa_kg`
   (`33_nube_valida.js`, `tools/exporta_corrida.py`). La verificación se hizo
   con esa regla; los dos registros traen `estado_linea` `emergencia` y
   `detenida`.
3. A2: el Emergency stop de Factory I/O se queda enclavado; soltarlo pide un
   segundo clic.
4. A3: la hipótesis de la orden (un hueco de sondeo como el de 668 ms) no se
   sostiene en esta sesión: periodo máximo 81 ms. Las 6 pulsaciones sin evento
   (63 a 98 ms) tuvieron 1 o 2 inicios de ciclo dentro y el cliente exige 2
   lecturas seguidas (`lecturas_para_cambio`). Por la regla 6 el paso se
   detuvo y la decisión es de Ari.
5. B: con pesaje detenido el cliente no usa los flancos de `at_scale_entry`;
   el comentario de `28_planta_lectura.js` que repite la lectura al revés de la
   fase 2 es lógica del cliente y no se tocó.
6. G: el manual de Factory I/O no documenta la escala de las posiciones de la
   escena ni una velocidad nominal (solo la máxima, 0.6 m/s); cuatro de los
   cinco valores de `linea` siguen estimados. En la escena real los seis
   sensores de `linea` son de banda "medida" y la regla de factibilidad no usa
   `intervalo_emision_min_s`. Con pesaje detenido, el reloj del límite
   `no_llego_a_fin_bascula` no avanza para la caja que se pesa.
7. I: `web/proceso.html` lee solo los últimos 300 registros, y desde las cajas
   del 25 oct hay ~21,700 latidos de noviembre: la página no muestra el aviso
   de registros anteriores al cambio de unidad. `corrida_c9_real.py` esperaba
   4 s fijos a Chrome (primer intento abortado); se cambió a esperar a
   DevTools. La nube se enciende en el entorno de Node-RED que arma el script
   con las credenciales de `.env`, no en un archivo `ENV_ARCHIVO` (el script
   no usa `demo_a2.sh`).
8. D: la pestaña de diagnóstico de la Actividad 1 comparte la llave y consulta
   al arrancar (`once: true`); `DIAG_MAX_DIA=0` no la frena (`Number(...) ||
   200`), se usó `-1`. El limitador de A2-Diagnóstico descarta (`drop: true`)
   lo que llega antes de un minuto, así que la segunda pulsación se dio a los
   65 s. El paso 6 del ensayo `--real` nunca había corrido con la nube y tenía
   la misma espera fija a Chrome. En modo sustituto la sonda del paso 4 tomaba
   el host de `.env`.
9. La prueba de seguridad volvió a rechazar una vez un token válido en
   `/comms` (batería de A); el almacén tenía 10 sesiones de 3 usuarios, ninguna
   vencida, y la repetición pasó 55/55.

## C. Carrera de la prueba de gráfica

### Qué se hizo

`pruebas/prueba_grafica.py`: después de apagar el emisor, espera a que la
línea se vacíe y la detiene; espera (hasta 60 s) a que la cuenta de cajas del
emulador sea igual a los `paso_caja` del cliente más el registro viejo sembrado
(la última escritura de A2-Nube ya está en el emulador); después muestrea la
página (hasta 30 s) hasta que tenga esa misma cuenta, y esa muestra es la
final. La comparación sigue siendo una igualdad; si la página no la alcanza en
el plazo, la prueba falla y muestra los dos números (el mensaje ya los traía).
No usa la escena ni la base real.

### Verificación: cinco corridas seguidas

```
corrida 1: espera final: emulador 19 cajas (paso_caja del cliente 18 + 1 sembrada); pagina 19; === RESULTADO: 8 correctas, 0 fallidas ===
corrida 2: espera final: emulador 19 cajas (paso_caja del cliente 18 + 1 sembrada); pagina 19; === RESULTADO: 8 correctas, 0 fallidas ===
corrida 3: espera final: emulador 19 cajas (paso_caja del cliente 18 + 1 sembrada); pagina 19; === RESULTADO: 8 correctas, 0 fallidas ===
corrida 4: espera final: emulador 19 cajas (paso_caja del cliente 18 + 1 sembrada); pagina 19; === RESULTADO: 8 correctas, 0 fallidas ===
corrida 5: espera final: emulador 19 cajas (paso_caja del cliente 18 + 1 sembrada); pagina 19; === RESULTADO: 8 correctas, 0 fallidas ===
```

La captura que la prueba copia a `docs/img/grafica_a2_emulador.png` se
restauró a la versión del repositorio después de cada corrida (no es parte de
este paso).

Batería completa al cerrar C:

```
mapa                       exit=0      0s  OK
materiales_modelo          exit=0      4s  === RESULTADO: 42 correctas, 0 fallidas ===
materiales_flujo           exit=0    434s  === RESULTADO: 36 correctas, 0 fallidas ===
limites                    exit=0      0s  
sustituto_funcional        exit=0     58s  === RESULTADO: 20 correctas, 0 fallidas ===
sonda                      exit=0     30s  === RESULTADO: 43 correctas, 0 fallidas ===
seguridad                  exit=0     13s  === RESULTADO: 55 correctas, 0 fallidas ===
planta_seguro              exit=0     30s  === RESULTADO: 25 correctas, 0 fallidas ===
planta_control             exit=0     65s  === RESULTADO: 5 correctas, 0 fallidas ===
nube                       exit=0    220s  === RESULTADO: 28 correctas, 0 fallidas ===
vigila                     exit=0     51s  === RESULTADO: 12 correctas, 0 fallidas ===
desviador                  exit=0     67s  === RESULTADO: 19 correctas, 0 fallidas ===
hmi                        exit=0     26s  === RESULTADO: 25 correctas, 0 fallidas ===
diagnostico_a2             exit=0     33s  === RESULTADO: 19 correctas, 0 fallidas ===
instrumentacion_a2         exit=0    139s  === RESULTADO: 6 correctas, 0 fallidas ===
tablero                    exit=0     67s  === RESULTADO: 34 correctas, 0 fallidas ===
prueba_sh                  exit=0     58s  === RESULTADO: 26 correctas, 0 fallidas ===
reglas_a1                  exit=0      1s  50 casos, 0 discrepancias
reglas_proceso             exit=0      0s  33 casos, 0 discrepancias (emulador)
FIN: 0 fallidas
```

## Fase 4: notas del registro (cierre, `docs/ORDEN_A2_FASE_4_CIERRE.md`)

Orden de cierre agregada en el commit `7441521`. Estas tres notas no cambian
código del cliente.

1. **Duración de las pulsaciones del paso T.** El modo `tablero` de
   `pruebas/prueba_fio.py`, tal como corrió en el commit `28a1b75`, espera 0.6
   s (`time.sleep(0.6)`, "que el cliente reaccione") después de ver cada cambio
   antes de anotar su hora. Por eso todas las pulsaciones de
   `datos/corridas/T_2026-11-11/prueba_fio.log` aparecen con 0.6 a 0.7 s entre
   presionar y soltar: es la espera del vigilante, no la duración de la
   pulsación, que no quedó registrada. La pulsación "de 0.6 s" sin evento del
   11 nov no tiene, entonces, duración conocida.
2. **Registros escritos, recontados desde los CSV de la nube guardados**
   (filas aceptadas de `a2_nube_*.csv`). El reporte de la fase 4 dio 31
   latidos para A (venía de contar mal) y 13 para I (sumaba el conteo de la
   ventana exportada, que deja fuera un latido de las 20:59:42.6Z, anterior a
   la ventana que empieza a las 20:59:43.5Z). La tabla correcta:

   | Paso | `caja` | `latido` | Fuente |
   |---|---|---|---|
   | A | 21 | **42** | `datos/corridas/A_2026-11-17/a2_nube_2026-11-17.csv` |
   | I (intento abortado) | 7 | 2 | `datos/corridas/I_2026-11-17_intento1/` |
   | I (corrida) | 132 | **12** | `datos/corridas/I_2026-11-17/` (11 dentro de la ventana exportada) |
   | I, total | 139 | **14** | |
   | D (ensayo con Gemini) | 22 | 6 | `datos/corridas/D_2026-11-17/` |
   | D (comprobación `--con-nube`) | 21 | 5 | `datos/corridas/D_2026-11-17/con_nube/` (copiado ahora del directorio temporal) |
   | D, total | 43 | 11 | |
   | **Fase 4** | **203** | **67** | |

3. **Cajas durante A3.** Dentro de A3, `a2_planta_eventos.jsonl` de la sesión
   A tiene 4 `caja_perdida` (motivo `sin_confirmacion`), 4 `desvio_erroneo`, 4
   `caja_fantasma` y 7 `caja_purgada`, y 4 `paso_caja` con `rechazo_fallido`:
   cajas a las que un Stop alcanzó en el desviador. A1 y A2 no tienen ninguno.
   `tools/analiza_sesion_a.py` gana la sección "Eventos de cajas por parte" y
   `docs/sesion_A.md` se regeneró con ella. No se corrige ese comportamiento.
   Al regenerar también se corrigió la ventana de "registrada": el cliente
   fecha el flanco con la hora de su propia lectura, que puede caer hasta un
   periodo de sondeo antes de que el vigilante vea el cambio, así que la
   ventana ahora empieza 0.1 s antes de presionar. En A no cambia nada (las 6
   pulsaciones sin evento siguen sin evento); en la sesión S sí importaba (ver
   el paso S).

## S. Stop con una lectura (cierre de la fase 4)

### Qué se hizo

- `config/planta_fio.json`: `tablero.stop.lecturas_para_cambio` = 1.
  `26_planta_config.js` acepta esa clave en los botones Start y Stop (entero ≥
  1; Emergency stop la rechaza porque actúa por nivel) y
  `28_planta_lectura.js` usa en el antirrebote las lecturas propias del botón
  si las trae y `lecturas_para_cambio` (2) en todo lo demás. Emergency stop no
  cambia. `node-red/flows.json` regenerado. Es uno de los dos cambios al
  cliente que la orden autoriza.
- `pruebas/prueba_tablero.py`, punto 8 (nuevo, también en `una_lectura`): el
  servidor Modbus emulado cuenta las lecturas FC2 y una entrada se cambia
  durante exactamente una lectura del cliente.

```
=== 8. Una sola lectura: Stop detiene, Start no arranca, un sensor no da flanco ===
  OK    repo: un Stop de una sola lectura detiene la linea
  OK    repo: un Start de una sola lectura no arranca la linea (Start sigue con 2 lecturas)
  OK    repo: una sola lectura falsa en at_scale no produce flanco (caja_entra/caja_fantasma 0 -> 0)
  OK    mutacion: sin lecturas_para_cambio propio, el mismo Stop de una lectura NO detiene (el caso falla sin el cambio)
=== RESULTADO: 4 correctas, 0 fallidas ===
```

- `pruebas/sesion_ari.py` gana `--solo-a3`, `--sin-nube` y `--prefijo`.
  Sesión con Ari el 17 nov 2026 (23:13 a 23:16 UTC), nube apagada, escena
  reiniciada, 20 Start y 20 Stop alternados con clics rápidos. Datos en
  `datos/corridas/S_2026-11-17/`, reporte en `docs/sesion_S.md` (misma
  herramienta; vuelta a correr, el mismo archivo).
- Al primer análisis aparecieron 9 Stop "sin evento" con 2 a 4 ciclos de
  sondeo dentro. Los 20 tenían su evento `boton`, pero con una sola lectura el
  cliente lo fecha con la hora de su lectura, que caía de 0 a 4 ms antes de que
  el vigilante viera el cambio, fuera de la ventana que empezaba en el
  instante del vigilante. La ventana se corrigió (empieza 0.1 s antes; ver la
  nota 3 del registro) y A no cambia con ella.

### Verificación

1. Stop: un ciclo de sondeo completo dentro de la pulsación (inicio y fin del ciclo entre presionar y soltar): 20, de ellas 20 con evento `boton`. Stop sin ningún ciclo completo dentro: 0 (0 con evento).

2. Conteo y Start por ciclos dentro de la pulsación (sin mínimo exigido):

| | Vistas | Registradas |
|---|---|---|
| Start, esta sesión | 20 | 19 |
| Stop, esta sesión | 20 | 20 |
| Start, paso T (11 nov) | 3 | 2 |
| Start, total | 23 | 21 |

Fuente del paso T: datos/corridas/T_2026-11-11/prueba_fio.log: Start a los 41.9, 53.6 y 65.5 s; eventos del cliente con dos boton start.

| Inicios de ciclo dentro | Vistas | Registradas |
|---|---|---|
| 1 | 1 | 1 |
| 2 | 4 | 3 |
| 3 | 13 | 13 |
| 4 | 2 | 2 |

   El Start sin evento (2 inicios de ciclo dentro) es el límite documentado de
   Start con dos lecturas: la conclusión automática de `docs/sesion_S.md`
   ("pulsación sin evento y sin hueco") se refiere a ese Start, que la decisión
   de Ari deja con dos lecturas a propósito.
3. Eventos de cajas por parte:

Cuenta, dentro de cada parte, los eventos `caja_perdida`, `desvio_erroneo`, `caja_fantasma` y `caja_purgada` del cliente y los `paso_caja` con `rechazo_fallido` (cajas que un Stop alcanzó en el desviador). Solo se registran.

| Parte | Eventos |
|---|---|
| A3 | caja_fantasma: 5, caja_perdida (sin_confirmacion): 2, caja_purgada: 8, desvio_erroneo: 2, paso_caja con rechazo_fallido: 2 |

   Periodo de sondeo de la sesión:

. Periodo de sondeo de toda la sesión

| n | Mediana (ms) | p95 (ms) | Máximo (ms) | Periodos ≥ 300 ms |
|---|---|---|---|---|
| 3659 | 52 | 53 | 105 | 0 |

4. Batería completa:

```
mapa                       exit=0      0s  OK
materiales_modelo          exit=0      3s  === RESULTADO: 42 correctas, 0 fallidas ===
materiales_flujo           exit=0    439s  === RESULTADO: 36 correctas, 0 fallidas ===
limites                    exit=0      0s  
sustituto_funcional        exit=0     58s  === RESULTADO: 20 correctas, 0 fallidas ===
sonda                      exit=0     31s  === RESULTADO: 43 correctas, 0 fallidas ===
seguridad                  exit=1      8s  === RESULTADO: 54 correctas, 1 fallidas ===
planta_seguro              exit=0     30s  === RESULTADO: 25 correctas, 0 fallidas ===
planta_control             exit=0     65s  === RESULTADO: 5 correctas, 0 fallidas ===
nube                       exit=0    221s  === RESULTADO: 28 correctas, 0 fallidas ===
vigila                     exit=0     51s  === RESULTADO: 12 correctas, 0 fallidas ===
desviador                  exit=0     70s  === RESULTADO: 19 correctas, 0 fallidas ===
hmi                        exit=0     26s  === RESULTADO: 25 correctas, 0 fallidas ===
diagnostico_a2             exit=0     33s  === RESULTADO: 19 correctas, 0 fallidas ===
instrumentacion_a2         exit=0    139s  === RESULTADO: 6 correctas, 0 fallidas ===
tablero                    exit=0     87s  === RESULTADO: 38 correctas, 0 fallidas ===
prueba_sh                  exit=0     59s  === RESULTADO: 26 correctas, 0 fallidas ===
reglas_a1                  exit=0      0s  50 casos, 0 discrepancias
reglas_proceso             exit=0      0s  33 casos, 0 discrepancias (emulador)
FIN: 1 fallidas
```

Otra vez el control autenticado de `/comms` en `prueba_seguridad.py`. Antes de
repetirla (regla 8): el almacén de sesiones del editor del userDir de pruebas
tenía **70 sesiones de 21 usuarios desechables, ninguna vencida, con
vencimientos del 24 nov 2026 entre las 19:26:09Z y las 23:47:21Z**. La
repetición inmediata pasó 55/55. La batería de H vuelve a correr todo.

```
```

## H. Límites del cliente con tiempos de recorrido medidos (cierre de la fase 4)

### Qué se hizo

- Definiciones antes de medir: `docs/INSTRUMENTACION_A2.md`, sección 7 (los
  dos tramos con eventos del cliente).
- `tools/mide_tramos.py` (nuevo) → `docs/corrida_H.md`, sobre L1, L2, M1, G e
  I (2,086 cajas). Reproduce la referencia de Cowork sin diferencias: máximo
  1.757 s en confirmación (M1, caja 293) y 0.261 s antes del pesaje (G, caja
  93).
- Cliente (segundo cambio autorizado): `26_planta_config.js` calcula los dos
  límites con `linea.t_pesada_a_confirmacion_s` y `linea.t_entrada_a_parada_s`
  si están completos (1.5 × tiempo + antirrebote + ida y vuelta, el de
  confirmación, o + 3 × T_ef, el de llegada, más `comunicacion_timeout_ms` en
  los dos); si no, con distancia y velocidad como antes; sin ninguna forma
  completa rechaza la configuración diciéndolo. Publica `limite_fin_bascula_s`
  (sin redondear, como lo usaba antes `28_planta_lectura.js` en cada ciclo) y
  `limites_de`. `28_planta_lectura.js` usa `S.lim.limite_fin_bascula_s`.
  `largo_caja_m` deja de exigirse al validar el desviador (no entraba en
  ninguna cuenta).
- `config/planta_fio.json`: `linea` gana los dos tiempos y pierde
  `velocidad_fija_m_s` (0.3), `largo_caja_m` (0.4), `entrada_a_fin_bascula_m`
  (1.2) y `fin_bascula_a_confirmacion_m` (0.9); la nota dice qué se midió, en
  cuántas cajas y cuándo. Ninguna otra configuración cambia.
- `pruebas/prueba_limites_linea.py` (nuevo, agregado a `pruebas/bateria.sh`).
- `tools/mide_linea.py` (del paso G) lee la configuración del commit
  `e575375`, porque la de ahora ya no trae las distancias; `docs/corrida_G.md`
  no se regeneró y la herramienta lo sigue reproduciendo igual (`cmp`).

### Tiempos medidos y límites

| Tramo | Tiempo medido (máximo, s) | Dónde | Límite nuevo (s) | Margen sobre el máximo (s) | Cajas por encima del límite |
|---|---|---|---|---|---|
| confirmación | 1.757 | M1 caja 293 | 4.806 | 3.049 | 0 |
| previo al pesaje | 0.261 | G caja 93 | 2.556 | 2.296 | 0 |

T_ef 55 ms (medido), rtt 0.005 s, comunicacion_timeout 2.000 s.

| Límite | Antes (distancias estimadas) | Después (tiempos medidos) |
|---|---|---|
| `timeout_confirmacion_s` | 4.67 s | 4.81 s |
| `no_llego_a_fin_bascula` (`limite_fin_bascula_s`) | 6.165 s | 2.5565 s |

### Verificación

1. `pruebas/prueba_limites_linea.py`:

```
=== 1. Sustituto del desviador (distancia y velocidad): los limites de antes ===
  OK    el cliente con desviador conecta (local) y queda en ok
  OK    timeout_confirmacion_s 7.66 = formula de antes 7.66 (T_ef 300 ms)
  OK    limite_fin_bascula_s 9.900000 = formula de antes 9.900000
=== 2. Factory I/O (tiempos medidos): la formula nueva ===
  OK    timeout_confirmacion_s 4.81 = 1.5 x 1.757 + 3 x 55 ms + rtt + 2.0 s = 4.81
  OK    limite_fin_bascula_s 2.5565 = 1.5 x 0.261 + 3 x 55 ms + 2.0 s = 2.5565
=== 3. Mutacion: sin ninguna forma completa, la configuracion se rechaza ===
  OK    sin_tiempos_ni_distancias: estado 503 y el registro dice 'faltan los tiempos medidos'
  OK    un_solo_tiempo: estado 503 y el registro dice 'faltan los tiempos medidos'
=== 4. Control: con los tiempos completos la misma configuracion carga (no es la prueba la que la rechaza) ===
  OK    con los dos tiempos: estado 200 con limites
=== RESULTADO: 8 correctas, 0 fallidas ===
```

2. Ninguna caja de las cinco corridas supera el límite nuevo de su tramo
   (columna "Cajas por encima del límite", 0 y 0); márgenes de 3.049 s y
   2.296 s.
3. `tools/limites_planta.py --config config/planta_fio.json`: salida idéntica
   a la de antes (`diff` sin diferencias); `parallels` sigue con T_ef 55 ms
   (medido), factible.
4. `prueba_fio.py cliente --cajas 200`:

```
Primer intento: cortado a las 101 cajas por la escena, que cerró la conexión
Modbus del oráculo (`ConnectionResetError: [Errno 54] Connection reset by
peer`; el puerto 502 de la VM dejó de contestar a las 23:59 UTC aunque
Parallels la daba por encendida). Hasta ahí, 0 `caja_perdida`. Carpeta en
`datos/corridas/H200_2026-11-17_intento1/`. Ari volvió a encender la VM y la
escena; segundo intento, completo:

$ caffeinate -d /usr/bin/python3 -u pruebas/prueba_fio.py cliente --cajas 200 --host 10.211.55.3 --puerto 502   -> exit 0
=== A2-Planta contra Factory I/O (Node-RED -> 10.211.55.3:502; oraculo por 10.211.55.3:502; datos en /var/folders/6y/56sny62s59j98r894dbqq9y00000gn/T/a2_fio_cliente_yxm604ke) ===
  OK    escena reiniciada por Modbus: Reset, vacia y Run (codigo 0)
  OK    A2-Planta conecta con la escena (com ok)
  OK    limites factibles con sondeo 50 ms (T_ef 55 ms)
  OK    marcha -> 200
    oraculo: 201 cajas soltadas, 200 salidas NC; cliente: 201 pasos
  OK    al menos 15 cajas clasificadas en 1720 s (200)
  OK    cada caja sale por la salida de su peso (oraculo): 200 de 200 (0 sin peso del oraculo)
  OK    las tres salidas se usan
  OK    el cliente reporta el mismo destino que la salida real, caja por caja (200)
  OK    pesos del cliente = pesos del oraculo (+-0.05 V) en las 183 cajas quietas
  OK    y la misma clase en todas las que el oraculo peso (200)
  OK    ninguna caja se cae ni se atora: 198 soltadas con mas de 12 s antes del paro, 200 salidas
  OK    200 cajas por la salida de su peso (200)
  OK    T_ef sale de lo medido (55 ms, medido)
  OK    cada pulso de los sensores de rama visto en al menos 3 lecturas {'at_left_entry': 9, 'at_right_entry': 8, 'at_forward_entry': 6}
  OK    sin desvios erroneos, perdidas ni fantasmas (0 / 0 / 0)
  OK    bajo control, todo sensor seguido dura al menos t_min encendido y apagado
  OK    el cliente vio cada pulso en al menos 3 lecturas
=== RESULTADO: 17 correctas, 0 fallidas ===
exit 0
(0 eventos `caja_perdida` en `a2_planta_eventos.jsonl`)
```

5. Batería completa:

```
mapa                       exit=0      0s  OK
materiales_modelo          exit=0      4s  === RESULTADO: 42 correctas, 0 fallidas ===
materiales_flujo           exit=0    441s  === RESULTADO: 36 correctas, 0 fallidas ===
limites                    exit=0      0s  
sustituto_funcional        exit=0     57s  === RESULTADO: 20 correctas, 0 fallidas ===
sonda                      exit=0     31s  === RESULTADO: 43 correctas, 0 fallidas ===
seguridad                  exit=0     13s  === RESULTADO: 55 correctas, 0 fallidas ===
planta_seguro              exit=0     30s  === RESULTADO: 25 correctas, 0 fallidas ===
planta_control             exit=0     64s  === RESULTADO: 5 correctas, 0 fallidas ===
nube                       exit=0    221s  === RESULTADO: 28 correctas, 0 fallidas ===
vigila                     exit=0     50s  === RESULTADO: 12 correctas, 0 fallidas ===
desviador                  exit=0     70s  === RESULTADO: 19 correctas, 0 fallidas ===
hmi                        exit=0     26s  === RESULTADO: 25 correctas, 0 fallidas ===
diagnostico_a2             exit=0     33s  === RESULTADO: 19 correctas, 0 fallidas ===
instrumentacion_a2         exit=0    139s  === RESULTADO: 6 correctas, 0 fallidas ===
tablero                    exit=0     85s  === RESULTADO: 38 correctas, 0 fallidas ===
limites_linea              exit=0     13s  === RESULTADO: 8 correctas, 0 fallidas ===
prueba_sh                  exit=0     59s  === RESULTADO: 26 correctas, 0 fallidas ===
reglas_a1                  exit=0      0s  50 casos, 0 discrepancias
reglas_proceso             exit=0      0s  33 casos, 0 discrepancias (emulador)
FIN: 0 fallidas
```

## D2. Segundo ensayo con una consulta real a Gemini (cierre de la fase 4)

Una sola corrida de `pruebas/ensayo_demo.py --real --con-gemini` (18 nov
2026, 00:39 a 00:45 UTC), con el cliente ya cambiado por S y H y la espera a
Chrome corregida en el paso D. Datos en `datos/corridas/D2_2026-11-17/` (sin el
archivo de variables, que se borró; la llave no aparece en ningún archivo del
repositorio).

### Paso 7 (diagnóstico)

```
OK    la HMI vuelve a abrir (Online)
    a2_diagnosticos: ['2026-11-18T00:41:06.876Z;hmi;gemini-3.1-flash-lite;1206;valido;;normal;mantener;;438']
    modelo gemini-3.1-flash-lite, latencia 1206 ms, nivel normal, accion mantener
    texto: The system is operating normally with 23 boxes sorted and zero errors. The mean mass is 9.09 kg with a standard deviation of 2.92 kg. All timing limits are feasible, and communication is stable after 109 seconds of operation.
    justificacion: All performance metrics are within expected operational parameters with zero misrouted or lost boxes recorded.
  OK    una consulta real: una sola fila con respuesta del modelo, valida, y la HMI la muestra
    espera 63 s para que el limitador de 1 por minuto no descarte la segunda pulsacion
  OK    la segunda pulsacion se detiene en el tope diario: sigue habiendo una sola fila (ninguna salida a la red) y la HMI muestra el mismo diagnostico valido
  OK    en los 30 s siguientes al diagnostico no hay ningun comando (0)
  OK    la pestana de diagnostico de la Actividad 1 no consulto (sin diagnosticos_*.csv: [])
```

Modelo `gemini-3.1-flash-lite`, latencia 1206 ms, 438 tokens, nivel normal,
acción mantener. Texto: "The system is operating normally with 23 boxes
sorted and zero errors. The mean mass is 9.09 kg with a standard deviation of
2.92 kg. All timing limits are feasible, and communication is stable after
109 seconds of operation."

### Verificación

1. Todas las comprobaciones, sin pasos bloqueados:

```
  OK    ./demo_a2.sh --revisa: limites factibles, Modbus contesta, sesion de Firebase
  OK    demo_a2.sh arranca todo sin fallas y reinicia la escena
  OK    imprime las URL de la HMI y de la grafica
  OK    A2-Planta: com ok, desviador, factible con T_ef medido (55 ms)
  OK    la HMI abre y dice Online / Stopped
  OK    Start -> 200
  OK    Emitter ON -> 422 sin_emisor (la escena emite sola)
  OK    comando rechazado visible: consigna con bandas fijas -> 422 velocidad_no_aplica
  OK    sonda vigila ve cambiar sensores con la linea en marcha
  OK    la HMI cuenta cajas clasificadas por destino y 0 perdidas
  OK    la HMI dice que la nube esta encendida y muestra el ultimo registro aceptado
  OK    http://localhost:8123/proceso.html se sirve (200)
  OK    la grafica lee como visor real y sube sin recargar (212 -> 225 cajas, 0 navegaciones)
  OK    la HMI vuelve a abrir (Online)
  OK    una consulta real: una sola fila con respuesta del modelo, valida, y la HMI la muestra
  OK    la segunda pulsacion se detiene en el tope diario: sigue habiendo una sola fila (ninguna salida a la red) y la HMI muestra el mismo diagnostico valido
  OK    en los 30 s siguientes al diagnostico no hay ningun comando (0)
  OK    la pestana de diagnostico de la Actividad 1 no consulto (sin diagnosticos_*.csv: [])
  OK    la HMI dice NO COMMUNICATION en 2.0 s (< timeout_com_ms + 1 s)
  OK    Start -> 409 sin_comunicacion en pantalla
  OK    al volver: Online y Stopped, sin reanudar sola
  OK    eventos: reconexion_inicia, 8 escrituras seguras (bandas y ruedas) en orden, reconexion_completa
  OK    Start vuelve a funcionar
  OK    ./demo_a2.sh --apaga deja libres el 1881 y el 8123
Bloqueados: 0
=== RESULTADO: 24 correctas, 0 fallidas ===
```

2. Una sola consulta real en este ensayo (una fila `valido` en
   `a2_diagnosticos_2026-11-17.csv`), mostrada en la HMI; la segunda pulsación,
   a los 65 s, se detuvo en el tope. **La fase suma dos consultas reales** (D y
   D2).
3. En los 30 s siguientes al diagnóstico no hubo ningún `comando`.

Registros escritos en `planta_01` en D2: 39 `caja` y 6 `latido`. D2 no cambió
código: el árbol, fuera de documentos y datos, es el mismo que pasó la batería
de H (0 fallidas), así que no se volvió a correr.

## Cierre de la fase 4: registros escritos y puntos en que la orden no coincidió con el código

Registros escritos en `planta_01`, contados desde las filas aceptadas de los
`a2_nube_*.csv` guardados:

| Paso | `caja` | `latido` |
|---|---|---|
| A | 21 | 42 |
| I (intento abortado + corrida) | 139 | 14 |
| D (ensayo con Gemini + comprobación `--con-nube`) | 43 | 11 |
| S, H (nube apagada) | 0 | 0 |
| D2 | 39 | 6 |
| **Fase 4** | **242** | **73** |

Consultas reales a Gemini en la fase: 2 (D y D2).

Puntos del cierre:

1. S: el reporte marcaba 9 Stop "sin evento". Con una sola lectura el
   cliente fecha el flanco con la hora de su propia lectura, que caía de 0 a 4
   ms antes de que el vigilante viera el cambio. La ventana de
   `tools/analiza_sesion_a.py` empezaba en el instante del vigilante; ahora
   empieza 0.1 s antes. Con la corrección, Stop da 20 de 20, y A no cambia.
2. S: la orden habla de "al menos un ciclo de sondeo completo dentro de la
   pulsación"; el CSV de sondeo da inicio y duración de cada ciclo, y se tomó
   como completo el ciclo que empieza y termina entre presionar y soltar.
3. H: la orden dice que `largo_caja_m` "se exige al validar y no se usa en
   ninguna cuenta del desviador": coincide; dejó de exigirse para el desviador.
   La configuración del empujador (sustituto) lo sigue exigiendo, sin cambio.
4. H: `limite_fin_bascula_s` se publica sin redondear para que el sustituto dé
   exactamente el límite de antes (28 lo calculaba en cada ciclo sin
   redondeo); `timeout_confirmacion_s` sigue redondeado a 0.01 como antes.
5. H: `tools/mide_linea.py` (paso G) leía las cuatro claves que se quitaron;
   ahora lee la configuración del commit `e575375` y `docs/corrida_G.md` se
   sigue reproduciendo igual.
6. H: el primer intento de `cliente --cajas 200` lo cortó la escena (la VM
   dejó de contestar en el puerto 502 a las 23:59 UTC); Ari volvió a encender
   la VM y el segundo intento pasó.
7. La prueba de seguridad rechazó otra vez un token válido en `/comms` en la
   batería de S (70 sesiones de 21 usuarios en el almacén, ninguna vencida);
   la repetición pasó 55/55 y la batería de H pasó completa.

