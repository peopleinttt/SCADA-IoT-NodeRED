# Pruebas

Arneses, de menor a mayor cercanía con la realidad.

| Archivo | Qué prueba | Necesita |
|---|---|---|
| `prueba_mapa.py` | el contrato de registros de la Actividad 2: validador y conversion de escala | Python 3.9 (22 casos) |
| `prueba.sh` + `simulador.py` | los flujos de Node-RED completos: validación, ingesta, diagnóstico, modos de falla de Gemini, permisos, caídas | nada (26 casos) |
| `prueba_sustituto.py funcional` | la planta sustituta de la Actividad 2 por Modbus: sensores, peso, empujador, `vel_banda_V` negativa, puerto y bandera | `./prepara_a2.sh` (20 casos, ~2 min) |
| `prueba_sustituto.py determinismo` | dos corridas de 10 min con la misma semilla dan la misma secuencia de eventos; otra semilla la cambia | `./prepara_a2.sh` (~22 min) |
| `prueba_sonda.py` | la sonda Modbus por su linea de comandos, cada etiqueta contra el emulador, y `mide` contra un proxy de 200 ms | `./prepara_a2.sh` (44 casos, ~1 min) |
| `prueba_planta.py seguro` | A2-Planta: desconexion forzada, estado sin comunicacion, secuencia segura en el cable al reconectar | `./prepara_a2.sh` (~1.5 min) |
| `prueba_planta.py corrida --escenario local\|azure` | 200 cajas sin perdida ni duplicado, masas y rechazos caja por caja contra el sustituto; `azure` = sondeo 500 ms + 200 ms de ida y vuelta por `proxy_retardo.py` | `./prepara_a2.sh` (~20 min cada una) |
| `prueba_planta.py control` | con la banda mas rapida que el limite calculado, el cliente marca cajas perdidas | `./prepara_a2.sh` (~3 min) |
| `prueba_nube.py` | A2-Nube contra el simulador de Firebase: un registro por caja mas latidos, esquema, codigo 201, 401 y renovacion, `A2_NUBE` | `./prepara_a2.sh` (14 casos, ~2.5 min) |
| `prueba_reglas_proceso.py` | las reglas de la rama `proceso` (emulador con `--emulador 127.0.0.1:9000`, o la base real en `planta_99`) | emulador: Java + firebase-tools (28 casos); real: credenciales del `.env` (26 casos) |
| `prueba_seguridad.py` | el puerto 1881 frente al tunel: 403 con cabeceras de Cloudflare salvo POST /telemetria (`--sin-capa3` prueba solo los middleware) | `./prepara_a2.sh` (~30 s) |
| `prueba_vigila.py` | la sonda en modo `vigila` contra el sustituto: pulsos, duracion y refresco | `./prepara_a2.sh` (~1 min) |
| `prueba_desviador.py [corrida]` | A2-Planta con el desviador: seguro, control y factibilidad (~5 min); `corrida --cajas 200` (~20 min) | `./prepara_a2.sh` |
| `bateria.sh [--con-emulador]` | todas las rapidas, una tras otra, con su codigo de salida en un resumen | todo lo anterior |
| `prueba_hmi.py` | la HMI de Dashboard 2.0 por su socket.io: lo que pinta, sus botones, 409/422 en pantalla, desconexion visible | `./prepara_a2.sh` (~2 min) |
| `prueba_diagnostico_a2.py [--real]` | el diagnostico de A2: valido e invalidos contra el simulador, tope diario, periodico solo en marcha; `--real` = UNA consulta real | ~2 min; `--real` gasta 1 de la cuota |
| `prueba_grafica.py` | la grafica de A2 en Chrome sin cabeza contra los emuladores de RTDB y Auth con las reglas del repo | firebase-tools, Java, Chrome (~3 min) |
| `emulador/` | qué contestan **las reglas** ante cada forma de fallar | Java + firebase-tools |
| `prueba_reglas_real.py` | las reglas **ya publicadas** en tu proyecto | credenciales del `.env` (46 casos) |
| `mide_thinking.py` | si apagar el razonamiento de Gemini degrada el diagnóstico | llave de Gemini y cuota |

## Contra tu base real

```bash
cd ~/dev/IoT
python3 pruebas/prueba_reglas_real.py --planta planta_99
```

No hace falta `source .env`: el script lo lee solo.

Corre sobre `planta_99` a propósito. Da de alta unos 30 registros y las reglas
son *append-only*, así que **no se pueden borrar desde la aplicación**: solo
desde la consola de Firebase, que hace bypass de las reglas. En `planta_99` no
estorban a tu corrida real de `planta_01`. Para limpiar después: consola →
Realtime Database → nodo `plantas/planta_99` → borrar.

El grupo "Holgura restante" **pasa a propósito**: documenta lo que el esquema
congelado no permite cerrar (ver `docs/INSTRUMENTACION.md`).
