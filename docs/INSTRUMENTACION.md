# Instrumentación de una corrida

Lo que pide la sección 5 del reporte: **latencia** y **frecuencia efectiva de
muestreo**, medidas sobre una corrida real y con la definición escrita antes de
mirar el número.

## Definiciones (fijadas antes de medir)

```
latencia_i        = ts_escritura_i − ts_origen_i
periodo_i         = ts_origen_i − ts_origen_(i−1)
f_efectiva        = 1 / media(periodo_i)
jitter            = desviación estándar de periodo_i
completitud       = muestras_recibidas / (ventana / periodo_nominal + 1)
hueco             = periodo_i > 1.5 × periodo_nominal
perdidas_estimadas= Σ (round(periodo_i / periodo_nominal) − 1) sobre los huecos
```

`periodo_nominal` = 5 s (`PERIODO_PUBLICACION_MS` en el sketch).

La latencia se reporta con **mediana y p95**, no con el promedio: la
distribución tiene cola larga por los reintentos, y el promedio la esconde.

## Lo que la latencia realmente incluye

`ts_origen` lo pone el ESP32 con su reloj sincronizado por SNTP.
`ts_escritura` lo pone Node-RED con el reloj del equipo anfitrión. La resta
contiene tres cosas, no una:

1. el tiempo de transporte ESP32 → gateway de Wokwi → túnel → Node-RED,
2. el tiempo de validación dentro del nodo de función (microsegundos),
3. **el sesgo entre los dos relojes**, que puede ser de decenas de ms y no es
   latencia.

Por eso `analiza_corrida.py` reporta dos columnas: la latencia cruda y la
latencia corregida restando el mínimo observado. El mínimo es una cota superior
del sesgo (si los relojes estuvieran alineados, el mínimo sería el transporte
más rápido posible, que es mayor que cero). Decir "la latencia mediana fue de
X ms" sin esta aclaración es afirmar más de lo que el dato aguanta.

## Supuesto declarado: las marcas de tiempo se creen al escribirse

Las reglas de Firebase impiden **alterar** un registro después de escrito
(`!data.exists()`), pero eso no es lo mismo que garantizar que las marcas eran
ciertas en el momento de escribirlas. No pueden serlo: el esquema guarda las
marcas como texto ISO-8601, y las reglas de RTDB solo saben comparar `now`
contra números. Un registro con `ts_escritura` anterior a `ts_origen` —latencia
negativa— entra sin problema por las reglas.

Entonces el supuesto es explícito: **se confía en el reloj del ESP32 (SNTP) y en
el del equipo con Node-RED en el instante de la escritura.** Lo que sí está
garantizado es que nadie los cambió después.

La garantía que falta en la base se cubre en el análisis, no en la escritura:
`analiza_corrida.py` detecta y denuncia las latencias negativas, y reporta el
sesgo de reloj estimado en vez de esconderlo. Es la capa correcta para hacerlo,
porque es la única que ve la corrida completa.

En el reporte conviene escribirlo así y no como "las marcas son inalterables",
que promete más de lo que la base entrega.

Si aparecen latencias **negativas**, la herramienta lo grita: eso solo puede
venir de relojes desalineados y hay que resincronizar antes de reportar nada.

El tiempo de ida y vuelta contra Firebase se mide aparte (`rtt_firebase_ms`),
así se puede separar "tardó la red hasta Node-RED" de "tardó Firebase".

## Cómo levantar los datos

Hay dos caminos y conviene correr los dos: dan el mismo número por vías
distintas, y si no coinciden, algo está mal.

### a) Archivo que escribe Node-RED en vivo

El nodo `instrumentación CSV` escribe una línea por evento en
`$DATOS_DIR/ingesta_AAAA-MM-DD.csv`, con separador `;`:

```
registro_id;ts_origen;ts_escritura;latencia_ms;rtt_firebase_ms;temperatura_C;vibracion_mm_s;ciclos_acumulados;resultado
```

Incluye los eventos que **fallaron** (columna `resultado`), que es justo lo que
se necesita para la tasa de entrega y lo que se perdería si solo se mirara la
base de datos.

### b) Descarga desde Firebase al terminar

```bash
python3 tools/exporta_corrida.py --diagnosticos
python3 tools/exporta_corrida.py --desde 2026-08-24T18:00:00Z --salida datos/corrida_final.csv
```

Escribe `registro_id;ts_origen;ts_escritura;latencia_ms;temperatura_C;vibracion_mm_s;ciclos_acumulados`
y, con `--diagnosticos`, un segundo archivo `*_diagnosticos.csv`.

## Análisis

```bash
python3 tools/analiza_corrida.py datos/ingesta_2026-08-24.csv --md docs/corrida.md
```

Salida (ejemplo real de una corrida de prueba):

```
Muestras utilizables .... 17
Ventana ................. 78.1 s (1.30 min)

  latencia cruda  (n = 17, unidad = ms)
  min 14.0   p50 10019.0   p90 22049.4   p95 26050.4   max 30052.0
  media 9735.3 ± 8575.9

  periodo entre ts_origen consecutivos  (n = 16, unidad = s)
  min 0.098   p50 5.051   p90 5.083   p95 7.161   max 13.391
  media 4.882 ± 2.618

  frecuencia efectiva ..... 0.2048 Hz (1 / 4.882 s)
  desviacion del nominal .. -2.36 %
  completitud ............. 100.00 %
```

(Esos números vienen del arnés de pruebas, que manda marcas de tiempo
retrasadas a propósito; una corrida real con Wokwi da latencias de cientos de
milisegundos, no de segundos.)

Con `--md` deja además una tabla en Markdown lista para pegar en el reporte.

## Control positivo

Antes de reportar la latencia de la cadena completa, mide una **línea base** en
la misma ventana y con el mismo equipo:

```bash
# 1. Línea base: cuánto tarda un POST local sin Wokwi de por medio
for i in $(seq 1 20); do
  curl -s -o /dev/null -w "%{time_total}\n" -X POST http://localhost:1881/telemetria \
    -H 'Content-Type: application/json' -H "X-Ingest-Key: $INGEST_KEY" \
    -d "{\"ts_origen\":\"$(python3 -c 'import datetime as d;print(d.datetime.now(d.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.")+f"{d.datetime.now().microsecond//1000:03d}Z")')\",\"temperatura_C\":25,\"vibracion_mm_s\":1,\"ciclos_acumulados\":$i}"
done
```

La diferencia entre esa línea base y la corrida con Wokwi es lo que cuesta el
tramo simulado. Sin la línea base, el número de latencia no tiene contra qué
compararse.

## Qué reportar en la sección 5

| Campo | De dónde sale |
|---|---|
| n, ventana | encabezado del análisis |
| latencia mediana y p95 | bloque de latencia cruda |
| sesgo de reloj | línea "sesgo de reloj estimado" |
| f efectiva y desviación del nominal | bloque de frecuencia |
| jitter | sd del periodo |
| completitud y pérdidas | bloque de completitud |
| tasa de entrega del emisor | contadores del monitor serie del ESP32 |
| latencia del diagnóstico | `datos/diagnosticos_*.csv`, columna `latencia_ms` |
| consumo de tokens | mismo archivo, columnas `tokens_*` |
