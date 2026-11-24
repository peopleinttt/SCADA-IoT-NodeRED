# Actividad 1 — Cadena Wokwi → Node-RED → Firebase → Gemini → Google Charts

Telemetría de una máquina simulada, ingesta validada, diagnóstico con IA y
visualización en vivo. El esquema de datos en Firebase es el que ya estaba
definido y **no se cambió**.

```
ESP32 (Wokwi)          Node-RED                  Firebase RTDB        Página web
─────────────          ─────────────────         ──────────────       ──────────
DHT22      ─┐          [http in POST]            /plantas/{id}/       Google Charts
transmisor ─┼─ JSON ─▶ [valida + ts_escritura] ─▶   telemetria/{rid}  ◀─ onValue
prox. switch┘  cada    [HTTP Request POST]          diagnosticos/{did}   LineChart
               5 s                                        ▲
                       [inject 5 min]                     │
                       [GET limitToLast] ─▶ [Gemini] ─────┘
```

> **¿Retomando el proyecto o estudiándolo? Empieza por
> [docs/BITACORA.md](BITACORA.md)** — qué se construyó, por qué se
> decidió así, y qué está medido contra qué.
>
> **¿Primera vez? Sigue [docs/PASO_A_PASO.md](PASO_A_PASO.md).** Va de cero
> a la cadena corriendo, con una comprobación al final de cada paso.

## Estado

| Pieza | Estado | Verificación |
|---|---|---|
| Emisor ESP32 (`firmware/wokwi/`) | escrito, **sin correr en Wokwi todavía** | requiere pegar los archivos en wokwi.com |
| Flujos Node-RED (`node-red/flows.json`) | **probado de extremo a extremo** | `pruebas/prueba.sh` → 22/22 |
| Reglas de Firebase (`firebase/`) | escritas, **sin desplegar** | requiere proyecto real |
| Capa Gemini | **probada contra simulador**, incluidos 4 modos de falla | `pruebas/prueba.sh` |
| Página (`web/index.html`) | **probada en navegador** (modo demo y modo error) | captura en el reporte |
| Instrumentación (`tools/`) | **probada con datos reales del flujo** | ver `docs/INSTRUMENTACION.md` |
| Rama `materiales/` | **pospuesta** a propósito | esperando la respuesta del profesor a la pregunta 5 |

Lo que falta para que corra de verdad son las credenciales: proyecto de
Firebase, llave de Gemini y una URL pública para Node-RED. Todo lo demás está
armado y probado.

---

## 1. Emisor en Wokwi

Crear un proyecto nuevo de **ESP32** en [wokwi.com](https://wokwi.com) y pegar
los tres archivos de `firmware/wokwi/`:

| Archivo | Dónde va |
|---|---|
| `sketch.ino` | pestaña *sketch.ino* |
| `diagram.json` | pestaña *diagram.json* |
| `libraries.txt` | pestaña *Library Manager* → o el archivo directamente |

Sensores del diagrama:

> **El monitor serie es una pieza virtual y hay que cablearla.** El diagrama
> lleva estas dos conexiones antes que ninguna otra:
> ```json
> ["esp:TX0", "$serialMonitor:RX", "", []],
> ["esp:RX0", "$serialMonitor:TX", "", []]
> ```
> Sin ellas la simulación corre con normalidad pero el monitor queda **mudo por
> completo** — ni siquiera aparece el arranque del ROM, que el chip escribe pase
> lo que pase. Es un fallo silencioso: no hay error, no hay aviso, solo un panel
> vacío que parece un problema del programa. Comprobado el 2026-08-25
> reproduciéndolo con el sketch `Hello, ESP32!` de fábrica de Wokwi.

| Componente | Pin | Papel |
|---|---|---|
| DHT22 | GPIO15 | `temperatura_C` (arrastrable en vivo con el ratón) |
| Potenciómetro | GPIO34 | transmisor de vibración: salida 0–3.3 V ≙ 0–50 mm/s RMS |
| MPU6050 | GPIO21/22 (I²C) | ruta alterna: acelerómetro → derivación a mm/s |
| Botón (tecla `c`) | GPIO27 | interruptor de proximidad: `ciclos_acumulados` |
| LED | GPIO2 | estado de transmisión |

**GPIO34 no es casualidad.** Es ADC1; los pines de ADC2 dejan de funcionar en
cuanto el WiFi está activo en el ESP32. Es la clase de detalle que tumba la
práctica sin dar un mensaje de error.

### De dónde sale `vibracion_mm_s`

El sketch trae las dos rutas y se elige con `VIB_FUENTE`:

- **`VIB_FUENTE 0` (por omisión) — transmisor analógico.** Emula un transmisor
  industrial de vibración (tipo IFM VSA / SKF CMSS), cuyo acondicionador ya
  entrega un nivel de CD proporcional al RMS de velocidad. El firmware aplica la
  función de transferencia declarada del sensor y publica. No sintetiza nada, y
  el valor se mueve en vivo al girar la perilla: para el video es la buena.
- **`VIB_FUENTE 1` — acelerómetro MPU6050.** Ventana de 1 s a 250 Hz, se resta
  la componente de CD (gravedad y montaje), se calcula `a_rms` del vector
  resultante y se integra a velocidad con `v_rms = a_rms / (2πf₀)`, con `f₀`
  estimada por cruces por cero. El DLPF del sensor se fija en 44 Hz para que el
  ancho de banda quede por debajo de Nyquist y no haya replegado de espectro.
  **Limitación honesta:** el MPU6050 de Wokwi devuelve el valor configurado en
  `diagram.json`, no una señal que varíe sola; la derivación es correcta pero el
  número solo cambia si se editan los atributos de la pieza.

### El problema que nadie menciona: Wokwi no ve tu `localhost`

El gateway público de Wokwi **solo hace conexiones salientes hacia Internet**.
No alcanza `localhost`, ni tu red local, ni una IP privada. Node-RED tiene que
estar en una URL pública. Tres opciones, de menor a mayor esfuerzo:

```bash
cd ~/dev/IoT && ./tunel.sh      # levanta Cloudflare e imprime la URL
```

**Usa Cloudflare, no ngrok.** Está medido, no es preferencia: el ESP32
simulado de Wokwi **no logra completar el apretón de manos TLS contra el borde
de ngrok**, y falla con un `-1 connection refused` que parece un problema de
red y no lo es. Comprobado desde dentro del simulador el 2026-08-25:

| Destino | TLS |
|---|---|
| `example.com` | OK (6747 ms) |
| `www.howsmyssl.com` | OK (3303 ms) |
| Cloudflare (`trycloudflare.com`) | **OK (6252 ms)** |
| ngrok (`ngrok-free.dev`) | **FALLO (6725 ms)** |

Dos consecuencias de diseño que salieron de esos números:

1. El apretón de manos tarda **~6.4 s** en el simulador, que no tiene
   acelerador criptográfico. El tiempo de espera de HTTPClient tuvo que subir
   de 8 s a **30 s**; con 8 s el envío moría antes de terminar.
2. La conexión se **reutiliza** (`http.setReuse(true)` y cliente persistente).
   Abriendo una conexión nueva por muestra, esos 6.4 s entraban en cada
   publicación: la latencia mediana medida fue de **14.8 s** y el periodo real
   se estiró a **6.8 s** contra los 5 s nominales.

`ngrok tcp`, que habría evitado el TLS por completo, exige tarjeta de crédito
aunque el plan sea gratuito.

Como el endpoint queda expuesto en Internet, el sketch manda una cabecera
`X-Ingest-Key` y Node-RED rechaza con `401` cualquier POST que no la traiga.
Genera la clave con `openssl rand -hex 24` y ponla en los dos lados.

---

## 2. Node-RED

```bash
cp .env.example .env      # y llenar los valores
./arranca.sh              # levanta en el 1881 con userDir propio
```

`arranca.sh` usa un `userDir` aparte a propósito: **no toca** la instancia que
ya tienes corriendo en el 1880 ni sus flujos. Si prefieres usar la tuya, importa
`node-red/flows.json` desde el menú → Importar, pero acuérdate de exportar las
variables de entorno antes de arrancarla, porque los nodos las leen con
`env.get()`.

Dos pestañas:

**`A1 · Ingesta`** — `http in POST /telemetria` → función de validación → `HTTP
Request POST` a `.../telemetria.json` → interpretación de la respuesta →
respuesta al ESP32 + línea en el CSV de instrumentación.

Es **POST**, no PATCH: así Firebase genera una clave push nueva por evento y
ninguna muestra sobrescribe a la anterior. La validación exige los cuatro campos
con su tipo y su rango; si falta uno, rechaza con `400` y un motivo legible, en
vez de escribir un registro a medias.

`ts_escritura` se arma con `Intl.DateTimeFormat` + `formatToParts`, reensamblado
a ISO-8601 con desplazamiento (`2026-08-24T16:39:46.534-06:00`). Se hace por
partes en lugar de usar el formato directo porque ningún *locale* entrega
ISO-8601 con milisegundos y offset de un solo golpe, y el resultado tiene que
ser parseable para poder restar tiempos.

**`A1 · Diagnóstico (Gemini)`** — `inject` cada 5 min → limitador a 1/min →
`GET` acotado con `limitToLast` → resumen + prompt → `HTTP Request POST` a
`generateContent` → `JSON.parse` explícito → `POST` a `.../diagnosticos.json`.

El código de cada nodo de función vive en `node-red/funciones/*.js` para poder
leerlo y citarlo; `flows.json` se regenera con:

```bash
python3 node-red/construye_flows.py
```

---

## 3. Firebase

```bash
# 1. Consola → Authentication → habilitar Correo/Contraseña
# 2. Crear las dos cuentas de servicio y generar las reglas con sus UID:
./firebase/prepara.sh
# 3. Publicar firebase/database.rules.generado.json
```

Qué hacen las reglas (`firebase/database.rules.json`):

- **`.write` anónimo bloqueado en todas partes.** La raíz es `false` y solo el
  UID del ingestor puede escribir, en su rama y nada más.
- **Append-only:** `!data.exists()` impide modificar o borrar un registro ya
  escrito. Ni siquiera el ingestor puede alterar la historia.
- **`.read` acotado a dos identidades:** la cuenta del visor (la página) y la
  del ingestor. Cualquier otra sesión, autenticada o no, recibe
  `PERMISSION_DENIED`.
- **El esquema se valida del lado del servidor:** tipos, rangos, formato ISO-8601
  de las marcas de tiempo por expresión regular, y `"$otro": {".validate": false}`
  para rechazar cualquier campo que no esté en el esquema.
- `materiales/` queda cerrada a lectura y escritura hasta que el profesor
  conteste la pregunta 5.

Sobre "permitir `.read` solo a la página": con una página pública no existe una
forma criptográfica de restringir por *página*, solo por *identidad*. Aquí se
restringe a la cuenta del visor, cuya credencial es de **solo lectura**: aunque
alguien la copie del HTML, las reglas le impiden escribir. El mecanismo pensado
para "solo mi app" es **Firebase App Check**, y es lo que habría que añadir para
producción.

**Para el video:** nada de modo de prueba público. Se demuestra que el modo
prueba está apagado enseñando la pestaña de Reglas y provocando un
`PERMISSION_DENIED` a propósito (ver `docs/ERRORES.md`).

---

## 4. Gemini

Llave desde [aistudio.google.com](https://aistudio.google.com/apikey) →
`GEMINI_API_KEY` en `.env`. El cuerpo es el que pide la actividad:

```json
{ "contents": [ { "parts": [ { "text": "…" } ] } ] }
```

más un `generationConfig` con `responseMimeType: "application/json"` y
`responseSchema`, para que el texto de vuelta sea JSON parseable y no haya que
adivinar dónde termina el diagnóstico y empieza la acción. Si aun así no llega
como JSON, el flujo **no descarta el diagnóstico**: lo guarda en modo degradado
y lo marca como tal.

Tres frenos de consumo, detallados en `docs/ERRORES.md`: limitador de 1/min,
tope diario configurable y omisión cuando el estado no cambió.

---

## 5. Página de visualización

```bash
./sirve_pagina.sh          # http://localhost:8123/index.html
# o: firebase deploy --only hosting
```

Antes de tener Firebase configurado se puede ver el diseño con datos sintéticos:
`http://localhost:8123/index.html?demo=1`, que lo anuncia en pantalla para que
nunca se confunda con una medición real.

Llenar el bloque `CONFIG` al inicio del `<script type="module">`. **No hay
ninguna credencial de escritura en el HTML**: la `apiKey` de Firebase es un
identificador público del proyecto (quien manda son las reglas) y la cuenta del
visor solo puede leer.

Se actualiza sin recargar con `onValue`; el modo `sondeo` con `setInterval` está
implementado y a un cambio de constante (`CONFIG.modoLectura`), por si se
prefiere enseñar esa variante.

Se abre con módulos ES, así que necesita servirse por HTTP: abrirlo con
doble clic (`file://`) no funciona.

---

## 6. Errores → `docs/ERRORES.md`

Los cinco casos que pide la actividad, más los de transporte y los del emisor,
con la línea exacta donde se manejan y la receta para provocar cada uno.

## 7. Instrumentación → `docs/INSTRUMENTACION.md`

```bash
python3 tools/exporta_corrida.py --diagnosticos
python3 tools/analiza_corrida.py datos/corrida_*.csv --md docs/corrida.md
```

Latencia (mediana, p95, corregida por sesgo de reloj), periodo efectivo, jitter,
frecuencia efectiva, completitud y pérdidas estimadas. Con las definiciones
escritas antes de mirar los números.

---

## Pruebas

```bash
python3 pruebas/simulador.py 8099    # terminal 1
./pruebas/prueba.sh                  # terminal 2
```

Levanta Node-RED en el 1881 contra un simulador local de Firebase, Identity
Toolkit y Gemini. Aparte, `pruebas/emulador/` mide el comportamiento de
las reglas contra el **emulador real** de Realtime Database — de ahí sale el
hallazgo de que ocho causas de fallo distintas devuelven la misma respuesta. Verifica validación, ingesta, diagnóstico, los cuatro modos de
falla de Gemini, permiso denegado y caída de la base. No gasta cuota, no toca
credenciales y no interfiere con tu Node-RED del 1880.

## Estructura

```
firmware/wokwi/     sketch.ino, diagram.json, libraries.txt
node-red/           flows.json + funciones/*.js + construye_flows.py
firebase/           database.rules.json, prepara.sh, firebase.json
web/                index.html
tools/              exporta_corrida.py, analiza_corrida.py
pruebas/            simulador.py, prueba.sh
docs/               ERRORES.md, INSTRUMENTACION.md
datos/              CSV de las corridas (no se versiona)
```
