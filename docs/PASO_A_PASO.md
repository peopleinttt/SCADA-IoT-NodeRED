# Paso a paso, de cero a la cadena funcionando

Cada paso termina con una **comprobación**. Si la comprobación falla, no sigas
al siguiente: el error se vuelve invisible tres pasos más adelante.

Necesitas cuatro terminales al final. Ábrelas conforme vayan haciendo falta.

---

## Paso 0 · Detén lo que esté corriendo

En la terminal donde arrancaste Node-RED, **Ctrl+C**. Con el `.env` en valores
de ejemplo no sirve de nada tenerlo arriba.

---

## Paso 1 · Firebase (unos 10 minutos, todo en el navegador)

1. Entra a <https://console.firebase.google.com> y abre tu proyecto (o crea uno).
2. **Realtime Database** → *Crear base de datos*:
   - Ubicación: la que quieras.
   - Reglas de seguridad: **empezar en modo bloqueado**. No elijas modo de
     prueba; la actividad lo prohíbe explícitamente y de todos modos vamos a
     publicar nuestras propias reglas.
   - Copia la URL que queda arriba de la tabla. Se ve así:
     `https://TUPROYECTO-default-rtdb.firebaseio.com`
     — o así, si elegiste una región fuera de us-central1:
     `https://TUPROYECTO-default-rtdb.europe-west1.firebasedatabase.app`
     Las dos sirven; usa **tal cual** la que te muestre.
3. **Authentication** → *Sign-in method* → habilita **Correo electrónico/contraseña**.
   (Solo el primero; no hace falta el enlace por correo.)
4. **⚙ Configuración del proyecto** → *Tus apps* → botón **`</>`** (Web) →
   registra la app con cualquier apodo → copia el bloque `firebaseConfig`.
   De ahí necesitas `apiKey`, `authDomain`, `databaseURL` y `projectId`.

> La `apiKey` de Firebase **no es un secreto**: es el identificador público del
> proyecto y va en el HTML a propósito. Quien decide qué se puede leer o
> escribir son las reglas, no la llave.

---

## Paso 2 · Llena el `.env`

```bash
cd ~/dev/IoT
openssl rand -hex 24          # copia el resultado, es tu INGEST_KEY
open -e .env                  # lo abre en TextEdit
```

Llena estos siete valores y deja los demás como están:

| Variable | De dónde sale |
|---|---|
| `FIREBASE_DB_URL` | la URL del paso 1.2, **sin barra al final** |
| `FIREBASE_API_KEY` | `apiKey` del paso 1.4 |
| `FB_INGESTOR_EMAIL` | **te lo inventas**, ej. `ingestor@actividad1.mx` |
| `FB_INGESTOR_PASS` | te la inventas, **mínimo 6 caracteres** |
| `FB_VISOR_EMAIL` | te lo inventas, ej. `visor@actividad1.mx` |
| `FB_VISOR_PASS` | otra, distinta a la anterior |
| `INGEST_KEY` | lo que imprimió `openssl` |
| `GEMINI_API_KEY` | tu llave de <https://aistudio.google.com/apikey> |

Los correos **no tienen que existir de verdad**: son cuentas dentro de tu
proyecto de Firebase, no buzones. Nadie les va a mandar nada.

**Comprobación**

```bash
grep -cE "PROYECTO|AIza\.\.\.|cambia-|ejemplo\.mx" .env
```

Tiene que imprimir **0**. Si imprime otro número, quedó algún valor de ejemplo.

---

## Paso 3 · Crea las cuentas y publica las reglas

```bash
./firebase/prepara.sh
```

Debe imprimir dos UID y crear `firebase/database.rules.generado.json`.

Si dice `OPERATION_NOT_ALLOWED`, te faltó habilitar Correo/contraseña (paso 1.3).
Si dice `WEAK_PASSWORD`, tu contraseña tiene menos de 6 caracteres.

Luego, en el navegador: **Realtime Database → Reglas** → borra lo que haya,
pega el contenido de `database.rules.generado.json` y dale **Publicar**.

```bash
cat firebase/database.rules.generado.json | pbcopy   # te lo deja en el portapapeles
```

**Comprobación.** No sirve mirar si la pestaña *Reglas* muestra la advertencia de
"base de datos pública": esa advertencia nunca apareció, porque la creaste en
modo bloqueado. La evidencia de verdad es que esto **falle**:

```bash
source .env
curl -s "$FIREBASE_DB_URL/plantas/planta_01/telemetria.json"
```

Debe responder `{"error":"Permission denied"}`. **Que falle es el éxito**: quiere
decir que un anónimo ya no puede leer ni escribir. Guarda esta captura, sirve
para el video.

---

## Paso 4 · Arranca Node-RED

```bash
./arranca.sh
```

Abre <http://localhost:1881>. En el panel derecho, pestaña **Depurar** (el
icono de bichito), debe aparecer a los pocos segundos un mensaje del nodo
*sesión lista* con el UID del ingestor.

Si en su lugar ves `login de Firebase fallido`, la contraseña del `.env` no
coincide con la cuenta que se creó en el paso 3.

---

## Paso 5 · Prueba la ingesta SIN Wokwi

Este paso es el que más tiempo te ahorra: comprueba Node-RED → Firebase antes de
meter el simulador de por medio. En **otra terminal**:

```bash
cd ~/dev/IoT && source .env
curl -i -X POST http://localhost:1881/telemetria \
  -H 'Content-Type: application/json' \
  -H "X-Ingest-Key: $INGEST_KEY" \
  -d "{\"ts_origen\":\"$(python3 -c 'import datetime as d;n=d.datetime.now(d.timezone.utc);print(n.strftime("%Y-%m-%dT%H:%M:%S.")+f"{n.microsecond//1000:03d}Z")')\",\"temperatura_C\":71.2,\"vibracion_mm_s\":4.8,\"ciclos_acumulados\":1}"
```

**Comprobación:** responde `HTTP/1.1 201` con un `registroId` (`-N…`), y en la
consola de Firebase aparece el registro bajo `plantas/planta_01/telemetria`.

| Si responde | Significa |
|---|---|
| `400` o `422` con un motivo legible | el dato no pasó la validación de Node-RED. El motivo te dice cuál campo y por qué; **no** es un problema de Firebase |
| `401 clave_invalida` | el `INGEST_KEY` del `.env` no es el que mandaste |
| `502 firebase_permiso_denegado` | ver abajo |
| `503` con `"codigo":404` | `FIREBASE_DB_URL` no corresponde a una base real (típico: quedó el `PROYECTO` de ejemplo) |
| `503` con `ECONNREFUSED` o `ENOTFOUND` | `FIREBASE_DB_URL` mal escrita, o sobró la barra final |

### Sobre el `502 firebase_permiso_denegado`

Realtime Database devuelve **exactamente el mismo** `401 {"error":"Permission
denied"}` para ocho causas distintas. Está medido contra el emulador con estas
mismas reglas (`pruebas/emulador/`): UID equivocado, cuenta sin permiso, valor
fuera de rango, marca de tiempo mal formada, campo extra, campo faltante,
`plantaId` mal formado y tipo equivocado dan la misma respuesta, byte por byte.

Por eso Node-RED valida antes de escribir, replicando las mismas condiciones que
las reglas: así, cuando un dato **sí** llega a Firebase y aun así lo rechazan, la
causa ya no puede ser el dato. Queda en dos:

1. **el token venció** — el flujo lo renueva solo, como mucho una vez por minuto;
2. **el UID del ingestor en las reglas publicadas no es el correcto** — repite
   el paso 3.

Si el mensaje de error dice *"N rechazos seguidos con datos que SÍ pasaron la
validación local"*, descarta el token: es el UID o el `PLANTA_ID`.

---

## Paso 6 · La URL pública

**No puede ser cualquier URL.** Tiene que ser una dirección que, al recibir un
POST, se lo entregue **a tu Node-RED del puerto 1881**. Un dominio cualquiera no
sirve; una URL de otro servicio tampoco.

En **otra terminal**:

```bash
ngrok http 1881
```

Toma la línea `Forwarding https://algo-algo.ngrok-free.app -> http://localhost:1881`.
Esa dirección `https://…` es tu URL pública.

Dos cosas de ngrok gratuito:

- **La URL cambia cada vez que reinicias ngrok.** Si lo cierras, la de antes
  deja de existir y hay que actualizar el sketch de Wokwi. Déjalo abierto toda
  la sesión de trabajo y toda la grabación del video.
- No cierres esa terminal. Si la cierras, el túnel muere.

**Comprobación:** desde otra terminal, repite el `curl` del paso 5 pero contra la
URL de ngrok:

```bash
curl -i -X POST https://TU-URL.ngrok-free.app/telemetria \
  -H 'Content-Type: application/json' -H "X-Ingest-Key: $INGEST_KEY" \
  -d '{"ts_origen":"2026-08-24T22:00:00.000Z","temperatura_C":70,"vibracion_mm_s":4,"ciclos_acumulados":2}'
```

Si contesta `201`, el camino desde Internet ya funciona y Wokwi va a poder.

---

## Paso 7 · Wokwi

1. Entra a <https://wokwi.com>, *New Project* → **ESP32**.
2. Pestaña `diagram.json`: borra todo y pega `firmware/wokwi/diagram.json`.
3. Pestaña `sketch.ino`: borra todo y pega `firmware/wokwi/sketch.ino`.
4. Botón de librerías (**+** en la pestaña *Library Manager*): agrega
   `DHT sensor library for ESPx` y `ArduinoJson`. O pega directo el archivo
   `libraries.txt`.
5. **En el sketch, cambia dos líneas** (están hasta arriba, en la sección
   CONFIGURACIÓN):

```cpp
#define INGEST_URL   "https://TU-URL.ngrok-free.app/telemetria"
#define INGEST_KEY   "el mismo valor que pusiste en .env"
```

6. Dale al botón verde de *Play*.

**Comprobación:** en el monitor serie de Wokwi debes ver, en este orden:

```
[wifi] conectando a Wokwi-GUEST ... listo, IP 10.10.0.2
[ntp] sincronizando... listo (epoch 17…)
[tx] {"ts_origen":"2026-…","temperatura_C":24,…}
[http] 201 {"ok":true,"registroId":"-N…"}
```

Y en Node-RED, la pestaña Depurar se llena cada 5 segundos.

Para mover los valores durante la grabación:
- **temperatura:** clic en el DHT22 → arrastra el deslizador.
- **vibración:** clic en la perilla del potenciómetro → flechas ↑↓ del teclado
  (Re Pág / Av Pág para saltos grandes).
- **ciclos:** tecla `c`, o clic en el botón verde.

| Si en el monitor serie ves | Qué pasa |
|---|---|
| se queda en `[ntp] sincronizando....` | reinicia la simulación; el gateway de Wokwi tarda a veces |
| `[http] error de transporte -1` | la URL de ngrok cambió o ngrok se cerró |
| `[http] 401` | el `INGEST_KEY` del sketch no es el del `.env` |
| nada, ni el `[wifi]` | falta el `sketch.ino` completo o el diagrama no coincide |

---

## Paso 8 · La página

Esto es lo que te salía "rechazado": la página necesita un servidor. Abrirla con
doble clic **no funciona** porque usa módulos de JavaScript y el navegador los
bloquea en `file://`.

1. Edita `web/index.html`, bloque `CONFIG` (línea ~110): pega tu `apiKey`,
   `authDomain`, `databaseURL`, `projectId`, y el correo y contraseña del
   **visor** (los del paso 2).
2. En **otra terminal**:

```bash
cd ~/dev/IoT && ./sirve_pagina.sh
```

3. Abre <http://localhost:8123/index.html>

**Comprobación:** la gráfica se llena sola mientras Wokwi publica, sin recargar.
Si quieres ver primero cómo se ve, sin Firebase:
<http://localhost:8123/index.html?demo=1> (lo anuncia en pantalla).

| Si la página dice | Qué pasa |
|---|---|
| `auth/api-key-not-valid` | la `apiKey` está mal copiada |
| `auth/invalid-credential` | el correo o la clave del visor no coinciden |
| `PERMISSION_DENIED` | el UID del visor no quedó en las reglas: repite el paso 3 |

### La credencial del visor en el HTML, para el reporte

Sí, el correo y la contraseña del visor quedan a la vista de quien abra el
código fuente de la página. Eso **no es un descuido, es el argumento**: el
diseño asimétrico existe precisamente para que esa credencial no valga nada más
que para leer dos ramas. Con las reglas publicadas, quien la copie no puede
escribir, ni borrar, ni leer `materiales`, ni listar `/plantas`.

Vale la pena escribirlo así en el reporte, en vez de dejarlo implícito. Y decir
también lo que falta: el mecanismo pensado para restringir el acceso a *una app
concreta* es Firebase App Check, que es lo que se añadiría antes de servir esta
página fuera de `localhost`.

---

## Paso 9 · El diagnóstico de Gemini

Ya está corriendo solo: se dispara a los 20 s de arrancar y luego cada 5 min.
Para forzarlo ahora, en Node-RED dale clic al cuadrito azul a la izquierda del
nodo **cada 5 min**.

**Comprobación:** aparece un diagnóstico bajo `plantas/planta_01/diagnosticos` en
Firebase, y el texto se pinta en la página.

Si en Depurar sale `consulta omitida` con motivo `muestras_insuficientes`, deja
que Wokwi mande unas cuantas muestras más. Si sale `estado_sin_cambio`, es que
no ha cambiado nada desde el diagnóstico anterior: mueve el potenciómetro y
vuelve a intentar.

---

## Paso 10 · Los datos para el reporte

Con la corrida terminada:

```bash
cd ~/dev/IoT
python3 tools/exporta_corrida.py --diagnosticos
python3 tools/analiza_corrida.py datos/corrida_*.csv --md docs/corrida.md
```

Eso te da latencia, frecuencia efectiva, jitter y completitud, con las
definiciones ya escritas. Detalle en [INSTRUMENTACION.md](INSTRUMENTACION.md).

---

## Resumen de terminales al final

| Terminal | Comando | Se queda abierta |
|---|---|---|
| 1 | `./arranca.sh` | sí |
| 2 | `ngrok http 1881` | sí |
| 3 | `./sirve_pagina.sh` | sí |
| 4 | los `curl`, exportar, analizar | no |

Más el navegador con Wokwi, la consola de Firebase, Node-RED (1881) y la página
(8123).
