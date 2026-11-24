# Bitácora del proyecto — Actividad 1

Documento de traspaso y de estudio. Explica **qué se construyó, por qué se
decidió así, y qué está medido contra qué**. Escrito el 2026-08-25, al cerrar
la cadena de extremo a extremo.

Si eres otro agente retomando este proyecto: lee esto antes de tocar nada, y
corre `./estado.sh` para saber en qué punto está.

---

## 1. Qué es

Una cadena de mantenimiento predictivo con cinco eslabones:

```
ESP32 (Wokwi)  →  Node-RED  →  Firebase RTDB  →  Gemini  →  página web
   emite            valida        almacena       diagnostica    visualiza
   cada 5 s         y sella       inmutable      y prescribe    sin recargar
```

Vive en `~/dev/IoT`. Es una actividad escolar con siete requisitos explícitos;
el mapa de requisito → archivo está en `docs/entrega.html`.

**El esquema de datos estaba congelado por el enunciado y no se cambió:**

```
/plantas/{plantaId}
    telemetria/{registroId}: ts_origen, ts_escritura, temperatura_C,
                             vibracion_mm_s, ciclos_acumulados
    diagnosticos/{diagnosticoId}: ts, resumen_entrada, texto_diagnostico,
                                  accion_prescrita, modelo, latencia_ms
    materiales/{piezaId}: POSPUESTA — cerrada a lectura y escritura
```

---

## 2. Las piezas

### Emisor · `firmware/wokwi/`

`sketch.ino` (492 líneas), `diagram.json`, `libraries.txt`.

Sensores y por qué cada uno:

| Sensor | Pin | Papel |
|---|---|---|
| DHT22 | GPIO15 | `temperatura_C` |
| Potenciómetro | GPIO34 | transmisor de vibración, 0–3.3 V ≙ 0–50 mm/s RMS |
| MPU6050 | GPIO21/22 | ruta alterna: deriva vibración de la aceleración |
| Botón | GPIO27 | interruptor de proximidad → `ciclos_acumulados` |

**GPIO34 no es arbitrario.** Es ADC1. Los pines de ADC2 dejan de funcionar en
cuanto el WiFi está activo en el ESP32, y falla sin dar ningún error.

**Por qué el potenciómetro y no solo el acelerómetro.** El MPU6050 de Wokwi
devuelve el valor configurado en `diagram.json`, no una señal que varíe sola.
Un acelerómetro estático da vibración cero después de quitar la componente de
CD. El potenciómetro modela un transmisor industrial de salida analógica
—tipo IFM VSA— cuyo acondicionador ya entrega un nivel de CD proporcional al
RMS de velocidad. Es físicamente fiel y se mueve en vivo para la demostración.
La ruta del acelerómetro está implementada igual (`VIB_FUENTE 1`), con la
integración `v_rms = a_rms / (2πf₀)`, el filtro anti-alias del sensor puesto en
44 Hz para quedar bajo Nyquist, y la limitación documentada.

Tres decisiones del firmware que vale la pena entender:

- **No publica si el reloj no está sincronizado.** Una marca de tiempo falsa
  contamina el cálculo de latencia de toda la corrida. Prefiere perder la
  muestra y decirlo.
- **`ciclos_acumulados` sobrevive al reinicio**, guardado en NVS cada diez
  cuentas para no castigar la flash.
- **Los bytes del MPU6050 se leen en sentencias separadas.** En C++ el orden de
  evaluación de los operandos de `|` no está especificado, así que el clásico
  `(Wire.read() << 8) | Wire.read()` puede tomarlos al revés según el
  compilador.

### Ingesta · `node-red/`

`flows.json` se **genera**: el código de cada nodo de función vive en
`node-red/funciones/*.js` y se ensambla con `python3 node-red/construye_flows.py`.
Editar `flows.json` a mano es un error; se pierde en la siguiente generación.

Dos pestañas: `A1 · Ingesta` y `A1 · Diagnóstico (Gemini)`.

El flujo de ingesta es `http in` → validación → `HTTP Request POST` → respuesta.
Es POST y no PATCH para que Firebase genere una clave push por evento.

`ts_escritura` se arma con `Intl.DateTimeFormat` + `formatToParts`,
reensamblado a ISO-8601 con desplazamiento. Se hace por partes porque ningún
*locale* entrega ISO-8601 con milisegundos y offset de un solo golpe, y el
resultado tiene que ser parseable para restar tiempos. **No se usa
`toISOString()`**: siempre emite `Z`, y la regla de Firebase exige
desplazamiento numérico.

### Reglas · `firebase/database.rules.json`

Cuatro propiedades, todas verificadas contra la base real:

1. Escritura anónima imposible en toda la base.
2. Solo el UID del ingestor escribe, y solo en `planta_NN`.
3. **Append-only**: `!data.exists()` impide modificar o borrar lo ya escrito.
4. Esquema validado del lado del servidor: tipo, rango, formato ISO de las
   marcas por expresión regular, y rechazo de cualquier campo extra.

`firebase/prepara.sh` crea las dos cuentas de servicio y sustituye los UID.

### Diagnóstico · `node-red/funciones/10–14`

`inject` cada 30 min → limitador 1/min → `GET` con `limitToLast` → resumen y
prompt → `POST` a Gemini → `JSON.parse` explícito → `POST` a `diagnosticos.json`.

El nodo HTTP está en modo **texto** a propósito: el `JSON.parse` explícito
permite distinguir "la API contestó otra cosa" de "contestó bien pero el
contenido no sirve".

### Página · `web/index.html`

Google Charts LineChart con dos ejes, listener `onValue` de Firebase. El modo
de sondeo con `setInterval` está implementado y a un cambio de constante.

La credencial del visor queda a la vista en el HTML, **y eso es el argumento,
no un descuido**: el diseño asimétrico existe para que esa credencial no valga
más que para leer dos ramas. Lo que faltaría en producción es Firebase App
Check.

### Instrumentación · `tools/`

`exporta_corrida.py` baja la corrida de Firebase a un CSV delimitado.
`analiza_corrida.py` calcula latencia, periodo efectivo, jitter y completitud,
con las definiciones fijadas antes de medir.

---

## 3. Los cinco hallazgos

Todos salieron de medir, no de suponer, y cada uno cambió una decisión.

### 3.1 Firebase devuelve el mismo error para ocho causas distintas

Medido con el emulador (`pruebas/emulador/mide_errores.py`): UID equivocado,
cuenta sin permiso, valor fuera de rango, marca mal formada, campo extra,
campo faltante, `plantaId` mal formado y tipo equivocado dan **el mismo**
`401 {"error":"Permission denied"}`, byte por byte. Nueve escrituras, dos
respuestas distintas.

**Consecuencia:** la validación se hace en Node-RED, antes de escribir, donde
el mensaje sí puede nombrar el campo y el motivo. Y el manejo del 401 ya no
adivina la causa: renueva el token como mucho una vez por minuto, y al tercer
rechazo seguido dice explícitamente que deje de buscar por ahí.

Corrección de razonamiento que vale la pena guardar: catorce discrepancias en
sentido "esperaba PERMITE, obtuvo NIEGA" es *consistente* con reglas sin
publicar, pero también con reglas publicadas y UID equivocado. Lo que descarta
la segunda es que **las lecturas del visor también fallen**.

### 3.2 El razonamiento de Gemini rompía el diagnóstico

Los tokens de pensamiento salen del mismo presupuesto de `maxOutputTokens`.
Con el tope de 512 el modelo gastaba ~490 pensando y devolvía JSON truncado
con `finishReason: MAX_TOKENS` en los tres casos ambiguos probados.

Con presupuesto suficiente (2048) sí termina, y ahí la calidad es
indistinguible: en el caso ambiguo la acción prescrita fue **la misma**, con
un tercio de los tokens. Criterio de juicio escrito antes de medir en
`docs/medicion_thinking.md`.

### 3.3 La cuota gratuita de Gemini son 20 peticiones diarias por modelo

Medido agotándola: `GenerateRequestsPerDayPerProjectPerModel-FreeTier = 20`.
Por eso el `inject` pasó de 5 a 30 minutos y `DIAG_MAX_DIA` de 200 a 15. Como
el límite es **por modelo**, cambiar `GEMINI_MODEL` da cuota nueva de
inmediato: es la salida de emergencia.

### 3.4 En Wokwi el monitor serie hay que cablearlo

`diagram.json` necesita estas dos conexiones o el panel queda mudo por
completo, ni siquiera aparece el arranque del ROM:

```json
["esp:TX0", "$serialMonitor:RX", "", []],
["esp:RX0", "$serialMonitor:TX", "", []]
```

Sin error, sin aviso. Parece un cuelgue del programa y no lo es. Reproducido
con el sketch `Hello, ESP32!` de fábrica. (El botón "Serial plotter" también
esconde el texto y muestra una cuadrícula negra.)

### 3.5 El ESP32 simulado no completa TLS contra ngrok

| Destino | TLS |
|---|---|
| example.com | OK (6747 ms) |
| www.howsmyssl.com | OK (3303 ms) |
| Cloudflare | **OK (6252 ms)** |
| ngrok | **FALLO (6725 ms)** |

El síntoma era `HTTPClient -1 (connection refused)`, que es el mismo código
para DNS caído, TCP rechazado y TLS fallido. Hasta que el sketch no midió las
tres cosas por separado, se depuraba a ciegas.

Además el apretón de manos tarda ~6.4 s en el simulador, que no tiene
acelerador criptográfico. Dos consecuencias: el tiempo de espera subió de 8 a
30 s, y la conexión se **reutiliza** — sin eso, esos 6.4 s entraban en cada
muestra y la latencia mediana daba 14.8 s con un periodo real de 6.8 s contra
los 5 s nominales.

`ngrok tcp`, que habría evitado el TLS, exige tarjeta de crédito.

---

## 4. Errores propios que quedaron corregidos

Vale la pena conservarlos: los tres eran silenciosos.

- **El token de Firebase en contexto `flow`.** El contexto `flow` de Node-RED
  es **por pestaña**. El login está en la pestaña de ingesta y el diagnóstico
  en otra, así que la segunda nunca veía el token y consultaba sin credencial.
  Ahora vive en `global`. **El simulador de pruebas no lo detectó porque
  aceptaba peticiones sin autenticar** — un simulador demasiado permisivo
  esconde justo los errores que importa ver, así que ahora exige `?auth=`.
- **`arranca.sh` no actualizaba los flujos.** Solo copiaba `flows.json` la
  primera vez, así que Node-RED corría código viejo sin avisar. Ahora detecta
  la diferencia y guarda la versión anterior.
- **Rangos que no eran del instrumento.** `temperatura_C` aceptaba hasta
  125 °C, que es el rango del DS18B20; el DHT22 topa en 80.

---

## 5. Cómo verificar todo

```bash
cd ~/dev/IoT
./estado.sh                                        # en qué paso va

python3 pruebas/simulador.py 8099 &                # terminal aparte
./pruebas/prueba.sh                                # 26 casos, sin gastar cuota

python3 pruebas/prueba_reglas_real.py --rapido --planta planta_99
python3 pruebas/prueba_reglas_real.py --planta planta_99   # 46 casos
```

El firmware se compila de verdad con `arduino-cli` y el core `esp32:esp32`:
0 errores y 0 avisos con `--warnings all`, 81 % de flash y 15 % de RAM.

---

## 6. Estado y pendientes

| Pieza | Estado |
|---|---|
| Emisor | corriendo en Wokwi, 13/13 POST con 201 |
| Flujos Node-RED | 26/26 |
| Reglas | publicadas, 46/46 contra la base real |
| Gemini | diagnósticos escritos con `gemini-3.1-flash-lite` |
| Página | leyendo datos reales |
| Instrumentación | probada con la corrida real |
| **Rama `materiales/`** | **cerrada, espera la pregunta 5 al profesor** |

Dos cosas de higiene pendientes: **rotar `INGEST_KEY`** (los proyectos de Wokwi
en el plan gratuito son públicos y la clave va dentro del sketch) y limpiar
`plantas/planta_99` desde la consola, que es la única vía porque los registros
son inmutables por diseño.

---

## 7. Orden de lectura para estudiarlo

1. `README.md` — el mapa completo.
2. `firmware/wokwi/sketch.ino` — de arriba abajo; los comentarios explican el
   porqué de cada decisión, no el qué.
3. `node-red/funciones/01_valida_telemetria.js` — la validación y el sellado.
4. `firebase/database.rules.json` — las cuatro propiedades.
5. `node-red/funciones/11_arma_prompt.js` y `12_parsea_gemini.js` — los frenos
   de consumo y los cinco modos de falla del parseo.
6. `docs/ERRORES.md` — cada caso con su línea exacta y su receta.
7. `docs/INSTRUMENTACION.md` — las definiciones y el supuesto declarado sobre
   las marcas de tiempo.
8. `docs/medicion_thinking.md` — un ejemplo de criterio pre-registrado.

Si solo vas a leer dos cosas: `docs/ERRORES.md` y la sección 3 de este archivo.
