# Orden para Claude Code. Actividad 2, fase 2: cierre de C5 a C9, escena real y demostración

Fecha: 24 de octubre de 2026. Entrega de la actividad: enlace a un video de evidencia, 25 de octubre de 2026 a las 23:59.

## Contexto

Sigues en `~/dev aws/dev/IoT`, con `docs/ORDEN_A2_FASE_1.md` y `docs/CICLO_DESARROLLO_A2.md`. En `main` ya están C0 a C4 (C4 es `5d5be96`). C5 está en el árbol de trabajo, probado en local (emulador 28 de 28, `prueba_nube.py` 14 de 14 y regresión completa), con la verificación contra la base real pendiente.

Esta fase cierra todo lo que falta para grabar el video: C5, la escena real de Factory I/O, C6, C7, C8, C9 y la demostración. Lee primero la fase 1. Sus cinco reglas y sus datos fijos siguen vigentes salvo donde esta orden los cambia.

## Forma de trabajo: de corrido, con puertas automáticas

1. No pidas visto bueno entre pasos. Al cerrar cada paso corres sus verificaciones con el código de salida visible (sin tuberías que lo oculten, o con `set -o pipefail`). Actualizas el documento de ciclo con lo hecho, las pruebas con su salida, las decisiones y lo pendiente. Haces el commit `Cn: ...` y sigues.
2. Te detienes solo en tres casos: una verificación que no logras pasar después de dos intentos de corrección dentro del mismo paso, una PUERTA ARI que todavía no se abre, o algo que te obligue a romper una regla. En los tres casos dejas el árbol limpio, escribes en el documento de ciclo qué falta y por qué, y sigues con el siguiente paso que no dependa de lo bloqueado.
3. Si el tiempo no alcanza, lo marcado ESENCIAL va primero, en el orden de esta orden. Lo marcado DESEABLE se recorta antes que cualquier paso esencial.
4. Nunca corras dos pruebas largas a la vez, ni una prueba mientras otra sesión usa los mismos puertos. El 24 de octubre una corrida de Claude en esta Mac mini se cortó por eso.
5. Declara en `.assurance/config.toml`, sección `[audit]`, los comandos de prueba del proyecto (`pruebas/bateria.sh`, los `pruebas/prueba_*.py` y `pruebas/prueba.sh`) para que el gancho de cierre los reconozca.
6. La base real y Gemini solo se tocan en los pasos que lo dicen. Gemini conserva su tope propio de 15 consultas diarias y `maxOutputTokens` en 2048.
7. Todo lo que se ve en el video va en inglés: textos de la HMI, de la gráfica, del diagnóstico y de la lista técnica de la demostración. El código y los documentos internos siguen en español.

## Datos nuevos de la planta real

Salen de las capturas de Ari y de mediciones de Claude del 24 de octubre. Úsalos como punto de partida y vuelve a medir.

- Hay dos destinos posibles para la planta. Opción A: la VM de Azure `factoryio-vm` (Windows Server 2022, East Asia), en Tailscale `100.116.150.89`. Opción B, en preparación: Windows dentro de Parallels en esta misma Mac mini, con una IP de la red interna de Parallels. Se elige solo con `A2_MODBUS_HOST`, `A2_MODBUS_PUERTO` y `A2_MODBUS_UNIDAD`. Nada en el código puede depender de cuál se usa.
- Escena: **Sorting by Weight**, Factory I/O 2.5.10. Driver Modbus TCP/IP Server, puerto 502, Slave ID 1, Scale 100, Auto connect activo. Los sensores digitales salen como entradas discretas, los analógicos (Weight) como registros de entrada, y el driver lee las salidas analógicas de holding registers y las digitales de coils. Offsets en 0. Conteos configurados: 14 entradas digitales, 11 salidas digitales, 1 registro de entrada y 4 de salida.
- Etiquetas vistas en la escena: Load scale, Weight, At scale entry, At scale exit, Send left, Send right, Send forward, At left entry y At right entry. La lista completa y sus direcciones llegan con la PUERTA ARI R0.
- La escena no tiene empujador. Clasifica con un desviador de ruedas de tres salidas.
- Medición con `sonda_modbus.py mide` contra la VM por Tailscale, a través del relevo de Hong Kong: conexión en 3.3 s, 38 de 40 lecturas contestadas, ida y vuelta mínima de 205 ms, mediana de 753, p95 de 1890 y máxima de 4420 ms. Factory I/O corre a 1 FPS en esa VM, que no tiene tarjeta gráfica, y todo indica que el driver contesta una vez por cuadro. Con esos tiempos los límites de C4 no valen, y por eso existe la opción B.

## Pasos

### C5b. Cierre de C5. ESENCIAL

- Haz ya el commit de C5, con la verificación real como pendiente. Acepto las decisiones que reportaste: el 201 lo anota el flujo, el latido va sin `caja_masa_kg` y la escritura depende de `A2_NUBE=1`.
- Corre tú `./firebase/prepara.sh`.
- PUERTA ARI P1: Ari publica `firebase/database.rules.generado.json` en la consola de Firebase. Cuando lo confirme, corres `python3 pruebas/prueba_reglas_proceso.py --planta planta_99` y `python3 pruebas/prueba_reglas_real.py --planta planta_99`, registras su salida y pones `A2_NUBE=1` en `.env`. Mientras tanto sigues con lo demás.

### S. Seguridad del puerto 1881 antes de la HMI. ESENCIAL

`tunel.sh` publica todo el puerto 1881 en un túnel rápido de Cloudflare, y `node-red/runtime/settings.js` no tiene `adminAuth`. Mientras el túnel corre, el editor de Node-RED queda en internet sin contraseña. La HMI de C6 lo agravaría, porque sus botones llaman a `30_planta_comando.js` sin `msg.req` y ese caso se acepta como llamada interna.

- Lleva al repositorio un `settings.js` propio, sin credenciales, y haz que `arranca.sh` y `pruebas/prueba.sh` lo usen.
- Toda petición que llegue con cabeceras de Cloudflare (`cf-connecting-ip` o `cf-ray`) se rechaza con 403, salvo la ruta de ingesta de la Actividad 1 que usa Wokwi. Esto aplica al editor, a las rutas HTTP de los nodos, al Dashboard 2.0 y a su socket.io. Usa los ganchos de middleware de Node-RED para el editor y las rutas, y los que ofrezca `@flowfuse/node-red-dashboard` 1.34.0 para su servidor y su socket.io. Si esa versión no los tiene, documenta la alternativa y aplícala.
- Verificación: peticiones con y sin esas cabeceras contra el editor, `/a2/planta/comando`, `/dashboard` y el socket.io del dashboard. Con las cabeceras todo da 403 salvo la ingesta, sin ellas todo funciona, y `pruebas/prueba.sh` sigue en 26 de 26.

### R1. Sonda en modo vigilancia. ESENCIAL

- Nuevo modo `vigila` en `tools/sonda_modbus.py`, solo de lectura. Durante N segundos lee en bloque, tan rápido como conteste el destino, las entradas discretas y los registros de entrada del mapa, o un rango que se le indique.
- Reporta los cambios por dirección con su hora, la duración de cada pulso en lecturas y en segundos, la distribución de la ida y vuelta, y el periodo de refresco de la escena, entendido como el menor intervalo observado entre dos valores distintos de una misma entrada.
- Verificación: contra el sustituto con `proxy_retardo.py`, el modo cuenta los mismos pulsos que el registro del sustituto.
- En cuanto pase, córrelo 3 minutos contra la VM de Azure con la escena en marcha y anota los números. Cuando la opción B exista, haz lo mismo contra ella. Esos números deciden qué planta se usa en el video, y los registras en el documento de ciclo.

### R2. Mapa real. ESENCIAL, con PUERTA ARI R0

- R0: Ari te pega la captura de la ventana del driver con todas las etiquetas asignadas. Con ella escribes `config/mapa_registros_fio.json`, con los mismos campos y el mismo validador de C1, y documentas las dos versiones en `docs/MAPA_REGISTROS.md`. `config/mapa_registros_a2.json` se queda para el sustituto de C2 y `A2_MAPA` elige cuál se usa.
- Si la captura no ha llegado, deja el archivo con las etiquetas conocidas y sus direcciones marcadas como pendientes, y que el validador lo rechace con un mensaje claro. Nunca inventes una dirección.
- Verificación: el validador acepta el mapa real. Con la escena en marcha, `vigila` ve cambiar cada sensor del mapa en su dirección cuando pasa una caja. Con `escribe`, cada coil y cada holding register mueve lo que su nombre dice. Esas escrituras están permitidas porque la escena es un simulador.

### R3. Cliente y sustituto para el desviador. ESENCIAL

- `config/planta_a2.json` gana el campo `actuador`, con dos valores: `empujador` (el de C4, que se queda para la regresión) y `desviador`. Con `desviador`, la clasificación usa N clases por peso con umbrales configurables, cada clase sale por una salida (Send left, Send right o Send forward) y se confirma con el sensor de entrada de esa salida. Los umbrales salen de los pesos que observes con `vigila`, no de suposiciones.
- Si las bandas de la escena son de velocidad fija, `vel_banda_V` y el comando `velocidad` no aplican. En ese caso `tools/limites_planta.py` solo comprueba si la velocidad fija es factible con el sondeo y el refresco medidos. Si no lo es, el cliente sigue corriendo, marca `factible: false` y lo dice en el estado.
- `lecturas_para_cambio` se vuelve configurable por escenario. Los sensores de Factory I/O no tienen rebote, así que con la escena real se permite 1 si el refresco no da para 2. Documenta el riesgo.
- El sustituto aprende la misma escena: tres salidas, báscula, sensor de entrada por salida y bandas de velocidad fija o variable según su configuración, con el mapa real. Así las pruebas siguen corriendo sin Factory I/O.
- Si entre los coils o los holding registers de la escena hay contadores o luces del tablero, el cliente escribe ahí los conteos por destino y el estado de la línea.
- El evento `paso_caja` gana el destino, y si Firebase lo necesita para C8, extiendes las reglas de `proceso` con un campo `destino` de valores cerrados y sus pruebas en el emulador.
- Verificación: las pruebas de C4 adaptadas al desviador (corrida, seguro y control) pasan contra el sustituto en el escenario medido en R1, y las de C4 con `empujador` siguen pasando.

### C6. HMI con Dashboard 2.0. ESENCIAL

- Lo de la fase 1, en inglés y para los dos actuadores: marcha y paro, consigna solo si aplica, emisor, conteos por destino, peso de la última caja, cajas por minuto, estado de comunicación y de la línea, factibilidad de los límites, último registro aceptado por Firebase y último diagnóstico. Si la cadena del ESP32 de la Actividad 1 corre, un panel con su última telemetría.
- Los botones pasan por la misma lógica y los mismos códigos que `/a2/planta/comando`, y un 409 o un 422 se ve en pantalla.
- Verificación: la página abre desde otro equipo de la tailnet y sus controles mueven el sustituto. Por el túnel da 403 (paso S). Una desconexión forzada se ve en la HMI en menos de `timeout_com_ms` más un segundo.

### C7. Diagnóstico con Gemini. DESEABLE

- Lo de la fase 1, con el texto del diagnóstico en inglés. Con banda de velocidad fija no se ofrece al modelo el código `reducir_velocidad`. El diagnóstico es solo un consejo y no mueve la planta.
- El disparo periódico, como mucho cada 60 minutos y solo con la línea en marcha.
- Verificación: respuestas simuladas válidas e inválidas, ninguna inválida llega a la HMI y el tope diario se respeta. Una sola llamada real para cerrar el paso.

### C8. Gráfica. DESEABLE

- Lo de la fase 1, en inglés: masa por caja, por destino si R3 lo dejó en Firebase, y cajas por minuto, con el listener de Firebase de la Actividad 1.
- Verificación: la gráfica se actualiza sin recargar durante una corrida contra el sustituto.

### C9. Corrida instrumentada. ESENCIAL en versión mínima

- Antes de medir, escribe en `docs/INSTRUMENTACION_A2.md` las definiciones del periodo efectivo del sondeo y su variación, la latencia de la lectura a la escritura en Firebase y la completitud de cajas.
- Corrida de 10 minutos contra la planta elegida en R1, escribiendo en `planta_01`. Esa escritura en la base real está autorizada. Exporta y analiza con `tools/exporta_corrida.py` y `tools/analiza_corrida.py` extendidos a la rama `proceso`.
- Verificación: las tres cifras se reproducen desde el CSV.

### D. Demostración. ESENCIAL

- `demo_a2.sh` arranca todo con un comando. Antes revisa que el Modbus conteste, que Firebase dé sesión, que los límites sean factibles y cuánta cuota de Gemini queda, e imprime las URL de la HMI y de la gráfica.
- `docs/DEMO_A2.md`, en inglés, con la lista técnica en orden de lo que se muestra: arquitectura, Factory I/O corriendo, HMI con marcha y paro, cajas clasificadas, registros llegando a Firebase, gráfica en vivo, diagnóstico, y estado seguro con una desconexión y su recuperación. Cada punto lleva el comando o la acción que lo provoca.
- `pruebas/bateria.sh` corre todas las pruebas rápidas y deja un resumen con el código de salida de cada una.
- Verificación: un ensayo completo de la lista sin intervenir fuera de lo que dice el documento.

## Fuera de esta fase

A2-Materiales, A2-Comandos con aprobación y cualquier actuación automática a partir del diagnóstico.

## Al terminar

Entrega una tabla con cada paso, su commit, su verificación con el resultado y lo que quedó bloqueado, con la puerta que lo bloquea. No afirmes que algo funciona sin la prueba que lo demuestre.
