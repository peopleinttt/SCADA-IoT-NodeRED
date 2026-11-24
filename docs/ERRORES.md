# Manejo de errores

Cada modo de falla del punto 6 de la actividad tiene tres cosas: dónde se
detecta, qué hace el sistema, y cómo reproducirlo a propósito para grabarlo.

Todos los casos de esta tabla están probados de forma automática en
`pruebas/prueba.sh` (22 comprobaciones, todas en verde).

---

## 1. Permiso denegado por las reglas de Firebase

**Dónde.** `node-red/funciones/03_respuesta_firebase.js:43` para la escritura;
`web/index.html:271` para la lectura desde la página.

**Qué hace.**

**El dato medido que gobierna este diseño.** Realtime Database devuelve el
**mismo** `401 {"error":"Permission denied"}` para ocho causas distintas.
Comprobado contra el emulador con estas reglas (`pruebas/emulador/mide_errores.py`):
UID equivocado, cuenta sin permiso, valor fuera de rango, marca de tiempo mal
formada, campo extra, campo faltante, `plantaId` mal formado y tipo equivocado
producen respuestas idénticas byte por byte. Nueve escrituras, dos respuestas
distintas: la del dato bueno y la de todo lo demás.

La consecuencia es que **la causa de un 401 no se puede leer de la respuesta**.
De ahí el diseño:

- `01_valida_telemetria.js` replica las mismas condiciones que las reglas y
  rechaza en el borde, donde el mensaje sí puede nombrar el campo y el motivo.
  Incluye una post-condición sobre el `ts_escritura` que él mismo genera, porque
  un formato malo ahí se vería como un problema de credenciales.
- `03_respuesta_firebase.js:43` ya no adivina: declara que el dato pasó la
  validación local y que, por lo tanto, la causa está en la credencial o en las
  reglas publicadas. Renueva el token **como mucho una vez por minuto**, para no
  provocar una tormenta de logins cuando la causa no era el token; y a partir
  del tercer rechazo seguido dice explícitamente que deje de buscar por ahí.
- El 400 sigue tratándose aparte, pero significa otra cosa de la que yo creía:
  JSON mal formado o ruta inválida. Las reglas `.validate` **no** producen 400.
- La página distingue `PERMISSION_DENIED` de un fallo de red y dice cuál de las
  dos cuentas es la que no tiene permiso.

**Cómo reproducirlo.** En la consola de Firebase, cambia `.read` o `.write` de
`plantas` a `false` y publica. O más limpio, sin tocar producción:

```bash
python3 pruebas/simulador.py 8099          # en otra terminal
curl -X POST http://127.0.0.1:8099/__modo -H 'Content-Type: application/json' -d '{"modo":"permiso"}'
```

---

## 2. Saturación de la base por lecturas demasiado frecuentes

**Dónde.** `node-red/funciones/10_lee_telemetria.js:26` y `web/index.html:346`.

**Qué hace.** Nunca se descarga la rama completa. Las dos rutas de lectura usan
`orderBy="$key"` con `limitToLast=N`:

| Ruta | Límite | Frecuencia |
|---|---|---|
| Node-RED → diagnóstico | `DIAG_MUESTRAS` (12 por omisión) | `inject` cada 5 min, con nodo `delay` en modo *rate limit* a 1/min como techo duro |
| Página → gráfica | `CONFIG.muestras` (60) | `onValue`: la base empuja solo los cambios |

La página usa `onValue` (listener) por omisión: después de la carga inicial, la
base manda únicamente los registros nuevos. En modo `sondeo` cada vuelta baja
otra vez las N muestras completas; por eso el periodo tiene un piso de 5 s
forzado en el código, aunque se configure menos.

`$key` no necesita índice declarado en las reglas, así que la consulta no
dispara el aviso de *"Consider adding .indexOn"* ni un escaneo completo.

**Cómo reproducirlo.** Pon `CONFIG.modoLectura = "sondeo"` y
`periodoSondeoMs = 100`: verás en la pestaña de red del navegador que el piso de
5 s se aplica de todas formas. Para ver la saturación de verdad, sube
`CONFIG.muestras` a varios miles y compara el tamaño de la descarga inicial.

---

## 3. Error de parsing de la respuesta de Gemini

**Dónde.** `node-red/funciones/12_parsea_gemini.js`, que está a propósito
detrás de un nodo HTTP Request configurado en modo **texto**: el `JSON.parse` es
explícito para poder distinguir *"la API contestó otra cosa"* de *"contestó bien
pero el contenido no sirve"*.

Se separan cinco fallas distintas, cada una con su motivo:

| Motivo | Línea | Cuándo pasa |
|---|---|---|
| `peticion_invalida` | `12_parsea_gemini.js:51` | HTTP 400. Ocurre de verdad: `gemini-3.5-flash-lite` responde `INVALID_ARGUMENT` si se le manda `thinkingConfig.thinkingBudget`, que `gemini-3.1-flash-lite` sí acepta. El mensaje del nodo nombra esa causa entre las posibles |
| `respuesta_no_json` | `12_parsea_gemini.js:64` | el cuerpo no es JSON (una página de error de un proxy, por ejemplo) |
| `prompt_bloqueado` | `:70` | `promptFeedback.blockReason` |
| `sin_candidatos` | `:74` | JSON válido pero sin `candidates` |
| `generacion_incompleta` | `:79` | `finishReason` distinto de `STOP`, típicamente `MAX_TOKENS` |
| `sin_texto` | `:87` | hay candidato pero `parts` viene vacío |

Si el sobre está bien y el texto **no** es JSON válido, no se tira el
diagnóstico: se guarda en **modo degradado** (`:99`), con el texto tal cual y
la acción extraída por expresión regular, y se marca la columna `formato` como
`degradado` en el CSV. Un diagnóstico con contenido vale más que un descarte.

**Cómo reproducirlo.**

```bash
curl -X POST http://127.0.0.1:8099/__modo -H 'Content-Type: application/json' -d '{"modo":"basura"}'        # respuesta_no_json
curl -X POST http://127.0.0.1:8099/__modo -H 'Content-Type: application/json' -d '{"modo":"truncado"}'      # generacion_incompleta
curl -X POST http://127.0.0.1:8099/__modo -H 'Content-Type: application/json' -d '{"modo":"texto_suelto"}'  # modo degradado
```

Contra la API real: baja `GEMINI_MAX_TOKENS` a `10` y verás `MAX_TOKENS`.

---

## 4. Sobrecarga de peticiones a Gemini

**Dónde.** `12_parsea_gemini.js:38` (429) y `:43` (500/503), más el freno de
entrada en `10_lee_telemetria.js:16`.

**Qué hace.** Retroceso exponencial acotado: 60 s, 120 s, 240 s… hasta un tope
de 15 min. La pausa se guarda en `flow.gemini_pausa_hasta` y el **primer** nodo
del flujo la respeta, así que durante la pausa ni siquiera se lee la base. Si la
API manda `RetryInfo` con su propio `retryDelay`, se registra en la bitácora.
Una respuesta buena reinicia el contador (`:113`).

Un `503` (modelo sobrecargado del lado de Google) espera 120 s fijos: no es
culpa del consumo propio y no tiene caso escalar la penalización.

**Cómo reproducirlo.** `{"modo":"cuota"}` en el simulador, o baja
`DIAG_MAX_DIA` a `1` y dispara el `inject` dos veces.

---

## 5. Límite de tokens de la cuenta gratuita agotado

**Dónde.** Tres frenos en cascada, todos en `11_arma_prompt.js`:

1. **Tope diario** (`:74`): `DIAG_MAX_DIA` consultas por día natural, contadas
   en la zona horaria del reporte. Al llegar al tope no se consulta más y lo
   dice en la bitácora.

   El número no es inventado. Está **medido** contra la API real el
   2026-08-25, agotando la cuota a propósito:

   ```
   429 RESOURCE_EXHAUSTED
     cuota agotada: GenerateRequestsPerDayPerProjectPerModel-FreeTier
        metrica   : generativelanguage.googleapis.com/generate_content_free_tier_requests
        valor     : 20
   ```

   Veinte peticiones por día, **por modelo**. Dos consecuencias de diseño:

   - El `inject` del diagnóstico pasó de 5 a **30 minutos**. A 5 minutos serían
     288 peticiones diarias: la cuota se agota en menos de dos horas. Para la
     grabación se dispara a mano con el botón del nodo.
   - `DIAG_MAX_DIA=15` deja margen para esos disparos manuales.
   - Como el límite es por modelo, cambiar `GEMINI_MODEL` da una cuota nueva
     de inmediato. Es la salida de emergencia si se agota a media grabación.
2. **Omisión por estado sin cambio** (`:90`): se compara una *huella* del estado
   redondeada (temperatura al entero, vibración a media unidad, si cruzó umbral,
   ciclos). Si es la misma que la anterior y no han pasado
   `DIAG_MIN_REPETIR_MIN`, no se gasta una consulta en repetir el mismo
   diagnóstico. El ruido de centésimas no dispara consultas; un cambio real sí.
3. **Recorte del prompt** (`:114`): tope duro de `DIAG_MAX_CARACTERES`. Lo que
   se sacrifica es el historial, nunca el resumen ni las instrucciones.

Además, el consumo real queda medido: cada diagnóstico registra
`promptTokenCount`, `candidatesTokenCount`, `thoughtsTokenCount` y
`totalTokenCount` en `datos/diagnosticos_AAAA-MM-DD.csv`
(`14_cierra_diagnostico.js:20`). Con eso se sabe cuánto falta para el límite
antes de chocar con él.

**Costo por diagnóstico, medido contra la API real el 2026-08-25** con
`gemini-2.5-flash` y el prompt de esta actividad:

| Configuración | Tokens del diagnóstico completo | De razonamiento |
|---|---|---|
| razonamiento encendido, tope 2048 | 1084 – 1242 | 665 – 800 |
| razonamiento encendido, tope 512 | 805 | 488 → **truncado, inservible** |
| `thinkingBudget: 0`, tope 512 | **408 – 450** | ninguno |

Los tokens de pensamiento salen del **mismo** presupuesto de `maxOutputTokens`.
Con el tope de 512 el modelo gastó ~490 pensando y devolvió JSON truncado con
`finishReason: MAX_TOKENS` en los tres casos ambiguos probados — que es justo el
caso `generacion_incompleta` de arriba, provocado sin querer por la
configuración.

Apagar el razonamiento cuesta un tercio de los tokens y, medido contra un
criterio escrito antes de ver los resultados, no degrada el diagnóstico: en el
caso ambiguo la acción prescrita fue **la misma** que dio el modelo razonando.
El detalle completo, con los casos y el criterio, está en
[medicion_thinking.md](medicion_thinking.md). `11_arma_prompt.js` avisa si
alguien deja el razonamiento encendido con un tope menor a 1500.

**Cómo reproducirlo.** `DIAG_MAX_DIA=2` en `.env`, reinicia y dispara el
`inject` tres veces: la tercera sale por `tope_diario`.

> **Margen para la grabación.** Entre el umbral de alarma de temperatura (75 °C)
> y el techo que aceptan las reglas (80 °C, que es también el máximo del DHT22)
> hay solo 5 grados. Alcanza para mostrar el cruce de umbral, pero el canal
> cómodo para la demostración es la vibración: alarma en 7.1 mm/s, fondo de
> escala del transmisor en 50 y techo de la regla en 100.

---

## 6. Fallas que no producen código HTTP

Un DNS que no resuelve, un TLS inválido, un socket cortado o un timeout no
generan `statusCode`: nunca llegan al nodo de función. Por eso cada pestaña
tiene un nodo **Catch** de alcance total (`uncaught: true`) conectado a
`15_errores.js`, que clasifica el error (`dns_no_resuelve`,
`conexion_rechazada`, `tiempo_agotado`, `tls_invalido`, `conexion_cortada`,
`parseo`), lleva la cuenta por clase y lo escribe en `datos/errores.log`.

Antes de escribir nada tapa las credenciales: los mensajes de error de Node-RED
traen la URL completa y la URL lleva `?auth=<idToken>`. `15_errores.js:7`
sustituye `auth=`, `key=` y `x-goog-api-key` por `<oculto>`.

**Cómo reproducirlo.** Pon `FIREBASE_DB_URL=http://127.0.0.1:9` y manda una
muestra: aparece la línea en `datos/errores.log` con el token ya tapado.

---

## 7. Del lado del emisor (ESP32)

| Situación | Línea | Qué hace |
|---|---|---|
| Reloj sin sincronizar por NTP | `firmware/wokwi/sketch.ino:345` | **no publica**; una marca de tiempo falsa arruina el cálculo de latencia de toda la corrida |
| Lectura inválida del DHT22 | `:352` | descarta la muestra y la cuenta como descarte |
| MPU6050 ausente con `VIB_FUENTE=1` | `:361` | descarta la muestra; no inventa una vibración |
| WiFi caído | `:340` | reconecta antes de intentar publicar |
| POST fallido | `:393` | un reintento a los 500 ms y luego se cuenta como pérdida |

El emisor lleva sus propios contadores (`intentos`, `ok`, `fallo`, `descartes`)
y los imprime en cada ciclo: son el numerador y el denominador de la tasa de
entrega que pide la instrumentación.
