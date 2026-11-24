# Orden para Claude Code. Actividad 2, fase 4: cierre de las observaciones a la versión 3 del documento

Fecha: 13 de noviembre de 2026. Esta orden sigue a `docs/ORDEN_A2_FASE_3.md` y a `docs/ORDEN_A2_FASE_3_CIERRE.md`. Lo que aquí no se menciona sigue como dicen esas órdenes.

## Contexto

Sigues en `~/dev aws/dev/IoT`, en la Mac mini. El último commit es `f750a43`, con la fase 3 cerrada. El profesor revisó la versión 3 del documento técnico y señaló que varios puntos de su tabla de pendientes siguen abiertos. Ari decidió el 13 de noviembre de 2026 cerrarlos con trabajo real y no con redacción. La tabla siguiente lista cada punto, su estado al cierre de la fase 3 y el paso de esta orden que lo cierra.

| Punto abierto | Estado al 11 de noviembre de 2026 | Paso |
|---|---|---|
| HMI abierta desde otro dispositivo de la tailnet | Solo se comprobó con la dirección de Tailscale de la propia Mac mini | A |
| Paro de emergencia con la nube encendida | El paso T corrió con `A2_NUBE=0`, por lo que ningún latido con `estado_linea` en `emergencia` salió del tablero real hacia Firebase | A |
| Primera pulsación de Start del paso T | Cambió el registro durante 0.6 s sin evento del cliente, con causa sin determinar | A |
| Descripción de `at_scale_entry` | `config/mapa_registros_fio.json` dice "caja a la entrada de la bascula", y el archivo de escena indica un sensor retrorreflectivo | B |
| Geometría de la línea y velocidad de banda | El bloque `linea` de `config/planta_fio.json` conserva valores estimados | G |
| Perfil temporal de Chrome de la corrida instrumentada | El commit `3d8a37e` solo se revisó en su sintaxis, ya que la corrida no se repitió | I |
| Diagnóstico de Gemini en el ensayo | `pruebas/ensayo_demo.py --real` corre sin llave para no gastar cuota | D |
| Carrera de la prueba de gráfica | `pruebas/prueba_grafica.py` toma la última muestra de la página antes de la última escritura de A2-Nube | C |

Sobre la pulsación de Start, esto es lo que hay. `datos/corridas/T_2026-11-11/prueba_fio.log` muestra que a los 41.9 s `start_button` pasó de 0 a 1 y a los 42.5 s volvió a 0, con la línea detenida antes y después, y la lista de eventos del cliente no tiene un `boton` de Start para esa pulsación. Las pulsaciones de los 53.6 s y de los 65.5 s sí pusieron la línea en marcha. En `node-red/funciones/28_planta_lectura.js` el evento `boton` sale con el flanco de presionar que entrega el antirrebote, sin otra condición, por lo que el cliente no vio ese flanco. La carpeta del paso T no guardó el CSV de sondeo, de modo que no hay datos para decidir la causa. La única pista es que la corrida instrumentada del 25 de octubre tuvo un periodo de sondeo máximo de 668 ms entre 11,983 ciclos, mayor que los 0.6 s de la pulsación, y esa pista es una hipótesis que este paso tiene que probar o descartar.

El documento técnico no es parte de esta orden. Lo actualiza Cowork con tus resultados, por lo que cada paso tiene que dejar sus cifras en archivos que se puedan volver a leer.

## Forma de trabajo

Siguen vigentes las trece reglas de `docs/ORDEN_A2_FASE_3.md`, con estos cambios y adiciones.

1. Los commits llevan el prefijo `F4`, uno por paso. El primer commit de la fase agrega esta orden, sin más cambios. `docs/CICLO_DESARROLLO_A2.md` gana una sección "Fase 4" con su tabla de estado.
2. La regla 6 de esa orden cambia. `.env` sigue con `A2_NUBE=0` durante toda la fase y no lo editas. Los pasos marcados NUBE encienden la nube solo en su propio archivo de variables (`ENV_ARCHIVO`), con `PLANTA_ID=planta_01`, y solo mientras corren. Al terminar cada uno de esos pasos Node-RED queda detenido, para que no sigan saliendo latidos. Ningún otro paso escribe en la base real.
3. La regla 7 de esa orden cambia. Hay una sola consulta real a Gemini en toda la fase, en el paso D. Si esa consulta falla por una causa externa, no se repite.
4. El orden es A, B, G, I, D y C. El paso A va primero porque necesita a Ari presente. Si la puerta A0 no se abre en ese momento, sigue con los demás y deja A al final. Usa `caffeinate -d` mientras corran pasos con escena.
5. Los pasos A y G miden. Lo que miden se define por escrito en `docs/INSTRUMENTACION_A2.md` antes de medir, como pide la regla 11 de esa orden.
6. Ningún paso cambia la lógica del cliente para que una verificación pase. Si una verificación de esta orden muestra un defecto del cliente, el paso se detiene con la evidencia en el documento de ciclo y la decisión es de Ari.
7. Toda corrida que se guarde en `datos/corridas/` incluye el CSV de sondeo de A2-Planta, además de los eventos y de la bitácora de la prueba.
8. Si `pruebas/prueba_seguridad.py` vuelve a fallar con el rechazo de un token válido en `/comms`, antes de repetirla anota en el documento de ciclo cuántas sesiones tenía el almacén de sesiones del editor y cuándo vencía cada una, sin imprimir ningún token.
9. Esta orden se escribió leyendo el código, sin ejecutarlo. Si un dato de la orden no coincide con el código, vale el código. Anótalo en el documento de ciclo y dilo en tu reporte.

## Puertas de Ari

| Puerta | Estado | Qué desbloquea |
|---|---|---|
| V0 | Ari la abre al dejar la máquina virtual encendida y la escena de Factory I/O en Play | Los pasos A, B, G, I y D |
| N0 | Abierta el 13 de noviembre de 2026. Ari autorizó escribir en `planta_01` con la nube encendida, solo en los pasos A, I y D | Los pasos A, I y D |
| G0 | Abierta el 13 de noviembre de 2026. Ari autorizó una consulta real a Gemini | El paso D |
| A0 | Cerrada hasta que Ari esté frente a la Mac con su teléfono conectado a la tailnet | El paso A |

## Pasos

### A. Sesión con Ari: teléfono, paro de emergencia con la nube y Start repetido

Marcas: ESCENA, NUBE, ARI. Dura entre 15 y 20 minutos con Ari presente.

Antes de abrir la puerta A0, y sin Ari, busca si todavía existe el directorio temporal de datos del paso T, que `datos/corridas/T_2026-11-11/prueba_fio.log` nombra en su primera línea. Si existe y conserva el CSV de sondeo, cópialo a `datos/corridas/T_2026-11-11/` y reporta los ciclos de sondeo entre las 21:10:12Z y las 21:10:15Z del 11 de noviembre de 2026, que es la ventana de la pulsación sin evento. Si no existe, anótalo y sigue.

La sesión se apoya en lo que ya hace `pruebas/prueba_fio.py tablero`: reinicio de la escena por Modbus, A2-Planta con el cliente de Factory I/O y su propio `DATOS_DIR`, y un proceso separado del cliente que vigila los registros del tablero y anota cada cambio con su hora. Puede ser un modo nuevo de ese script o un script aparte, lo que resulte más limpio. Lo que cambia frente al modo `tablero` es que la nube va encendida en el archivo de variables de la sesión, que no hay llave de Gemini, que cada parte le dice a Ari en pantalla qué hacer y espera a verlo, y que al terminar todo el `DATOS_DIR` se copia a `datos/corridas/A_<fecha>/`. Si una parte no se puede hacer en el momento, se reporta como bloqueada y la sesión sigue con las otras, ya que el tiempo de Ari es lo escaso.

**A1. HMI desde el teléfono.** El script imprime la dirección de la HMI con la IP de Tailscale de la Mac mini, la misma que imprime `demo_a2.sh`. Ari la abre en su teléfono con Tailscale activo, presiona Start en la página, espera a que salgan al menos tres cajas y presiona Stop. Durante esta parte el script no abre ninguna sesión propia de la HMI, de modo que un comando con origen `hmi` solo pueda venir del teléfono.

- Verificación 1: mientras Ari usa la página hay al menos una conexión establecida al puerto de Node-RED cuya dirección remota pertenece al rango de la tailnet (100.64.0.0/10) y es distinta de la dirección de Tailscale de la propia Mac. La evidencia sale de observar las conexiones del puerto, sin cambiar el flujo.
- Verificación 2: `a2_planta_eventos.jsonl` tiene dentro de esta parte un `comando` de marcha y uno de paro con `origen` igual a `hmi`, y al menos tres `paso_caja` entre ambos.
- Ari toma una captura de pantalla en el teléfono con la página en línea y la línea en marcha. Esa captura es para el documento y no forma parte de la verificación.

**A2. Paro de emergencia con la nube.** Ari presiona Start en el tablero de la escena, espera dos cajas, presiona Emergency stop, lo sostiene unos 5 s, lo suelta, y presiona Start y Stop.

- Verificación 1: el vigilante ve `emergency_stop` bajar a 0 y volver a 1, y el cliente registra `paro_de_emergencia` y `emergencia_liberada`.
- Verificación 2: `a2_nube_<día>.csv` tiene un latido aceptado con HTTP 200 escrito dentro de los 2 s siguientes al `paro_de_emergencia`, y otro dentro de los 2 s siguientes a `emergencia_liberada`. Reporta el retraso medido de cada uno.
- Verificación 3: esos dos registros, leídos de la base real por su `registro_id` con la cuenta del visor, tienen `tipo` igual a `latido` y `estado_linea` igual a `emergencia` el primero y a `detenida` el segundo. Ninguna credencial se imprime.
- Verificación 4: las cajas que el paro descartó no aparecen como registros `caja`, es decir, el número de registros `caja` aceptados en la sesión es igual al número de eventos `paso_caja`.

**A3. Start repetido.** La escena se reinicia por Modbus, igual que al inicio del paso T. Ari presiona Start y después Stop, veinte veces, a su ritmo normal y dejando al menos 2 s entre una pulsación y la siguiente. Esta parte mide y no cambia el cliente.

- Resultado 1: una tabla con cada pulsación que vio el vigilante, con su hora, su botón, su duración y si el cliente registró su evento `boton` en los 0.5 s siguientes.
- Resultado 2: cuántas pulsaciones de Start vio el vigilante y cuántas registró el cliente, en esta sesión y sumadas a las tres del paso T.
- Resultado 3: para cada pulsación sin evento, los ciclos del CSV de sondeo entre 1 s antes de presionar y 1 s después de soltar, con su inicio, su duración y su estado de comunicación, y si entre dos inicios consecutivos hay un hueco mayor o igual a la duración de la pulsación que la cubra.
- Resultado 4: la distribución del periodo de sondeo de toda la sesión, con mediana, p95, máximo y número de periodos de 300 ms o más.
- Conclusión: si una pulsación sin evento coincide con un hueco de sondeo, la causa queda registrada como hueco de sondeo, con su tamaño. Si hay una pulsación sin evento y sin hueco, el paso se detiene con la evidencia, ya que sería un defecto del cliente y aplica la regla 6 de esta orden. Si las veinte se registran, se reporta como no reproducida.
- Verificación: la herramienta que arma estos cuatro resultados se vuelve a correr sobre `datos/corridas/A_<fecha>/` y da lo mismo.

Al cerrar el paso, Node-RED queda detenido y la batería completa pasa con 0 fallidas.

### B. Descripción de `at_scale_entry`

Marca: ESCENA. No necesita a Ari.

- Con la escena recién reiniciada, la línea detenida y sin cajas, lee `at_scale_entry` veinte veces con `tools/sonda_modbus.py` en modo de lectura.
- Si lee 1 en todas, corrige solo el texto de su descripción en `config/mapa_registros_fio.json`, con la misma forma que ya tienen `at_exit_left`, `at_exit_front` y `at_exit_right`, y regenera la documentación con `python3 tools/mapa_registros.py doc`.
- Reporta dónde usa el cliente el rol `entrada`, que `config/planta_fio.json` asigna a ese sensor, y si alguna cuenta depende de su polaridad. Incluye en ese reporte los mínimos de `linea.sensores.at_scale_entry`, que se midieron el 24 de octubre leyendo el 1 como caja presente. Si alguna cuenta depende de la polaridad, no la cambies en este paso. Detente y dilo.
- Anota en el documento de ciclo que la frase de la fase 2 sobre cajas que se forman sin hueco venía de leer ese sensor al revés.
- Verificación: `pruebas/prueba_mapa.py` pasa, la documentación generada coincide con el mapa y la batería completa pasa con 0 fallidas.

### G. Geometría de la línea y velocidad de banda

Marca: ESCENA. No necesita a Ari y la nube va apagada.

El bloque `linea` de `config/planta_fio.json` tiene cinco valores estimados, que son `velocidad_fija_m_s` (0.3), `intervalo_emision_min_s` (2.1), `largo_caja_m` (0.4), `entrada_a_fin_bascula_m` (1.2) y `fin_bascula_a_confirmacion_m` (0.9), y su nota lo dice. El cliente los usa en la regla de factibilidad y en dos límites de tiempo de recorrido, en `node-red/funciones/26_planta_config.js` y en `node-red/funciones/28_planta_lectura.js`, y `tools/limites_planta.py` usa el intervalo de emisión.

- Define primero en `docs/INSTRUMENTACION_A2.md` cada tramo, con los mismos dos sensores que usa el cliente al aplicar el límite de ese tramo, y cómo se obtiene cada uno de los cinco valores.
- Corre el cliente contra la escena hasta ver salir al menos 150 cajas, con un proceso separado del cliente que guarde cada flanco de los nueve sensores de la línea con su hora. Todo queda en `datos/corridas/G_<fecha>/`.
- Las distancias salen de las posiciones del archivo `docs/capturas/escena_sorting_by_weight_A2.factoryio`, convertidas a metros con la escala que documente el manual de Real Games. La velocidad sale de la distancia entre dos sensores de una misma banda que la caja recorre sin detenerse, dividida entre la mediana del tiempo entre sus flancos, y se contrasta con la velocidad nominal del manual si el manual la da.
- El largo de caja sale, por tipo de pieza, de la duración del pulso de un sensor que la caja cruza a velocidad constante, y se contrasta con las dimensiones del manual si las da.
- El intervalo de emisión se reporta de tres fuentes: el mínimo entre cajas consecutivas en esta corrida, el mismo mínimo en los eventos `caja_entra` de L1, L2 y M1, y la configuración del emisor en el archivo de escena, que tiene `MinTimeToEmit="1"` y `MaxTimeToEmit="2"`. Di cuál de las tres corresponde a la forma en que la regla de factibilidad usa ese valor, y por qué.
- Si el manual no documenta la escala ni la velocidad nominal, no supongas ninguna de las dos. En ese caso reporta los tiempos de recorrido medidos y deja el valor correspondiente marcado como estimado, con el motivo.
- Una herramienta, por ejemplo `tools/mide_linea.py`, lee la carpeta de la corrida y escribe `docs/corrida_G.md` con las tablas, sin interpretación. Para cada tiempo reporta n, mediana, p5, p95 y máximo.
- `linea` queda con los valores medidos y su nota dice qué se midió, cuándo y cómo, y cuáles valores siguen estimados si queda alguno. Ninguna otra configuración cambia, incluidas las del sustituto.
- Verificación 1: la herramienta vuelta a correr reproduce `docs/corrida_G.md`.
- Verificación 2: cada límite de tiempo de recorrido que el cliente deriva de `linea`, calculado con los valores nuevos, es mayor que el tiempo máximo observado en su tramo. Reporta el límite, el máximo y el margen. Si alguno no lo cumple, detente sin ajustar nada.
- Verificación 3: `tools/limites_planta.py` da para el escenario `parallels` el mismo veredicto que antes del cambio. Reporta `T_ef` y el veredicto antes y después. Si el veredicto cambia, detente.
- Verificación 4: `pruebas/prueba_fio.py cliente --cajas 200` con la configuración nueva pasa 17 de 17.
- Verificación 5: batería completa con 0 fallidas y `pruebas/prueba.sh` en 26 de 26.

### I. Corrida instrumentada con la nube

Marcas: ESCENA, NUBE. No necesita a Ari.

- Corre `pruebas/corrida_c9_real.py` una vez, con sus 10 minutos. La nube se enciende solo en el archivo de variables de la corrida.
- El reporte se escribe en `docs/corrida_a2_fase4.md`, de modo que `docs/corrida_a2.md`, que es el reporte del 25 de octubre, no se sobrescriba. La captura de la gráfica se copia a `docs/img/grafica_fase4.png` y los datos quedan en `datos/corridas/I_<fecha>/`.
- Verificación 1: todas las comprobaciones del script pasan, que el 25 de octubre fueron 11 de 11.
- Verificación 2: las tres cifras de `docs/INSTRUMENTACION_A2.md` se calculan con las mismas definiciones y con `tools/analiza_corrida.py --a2`, y el reporte las pone junto a las del 25 de octubre, sin interpretación.
- Verificación 3: el perfil de Chrome y la captura original se crean fuera del repositorio, y `git status` no muestra más archivos nuevos que el reporte, la imagen y la carpeta de la corrida. Con eso se cierra el punto del commit `3d8a37e`.
- Verificación 4: la página lee con la cuenta real del visor, no navega después de la primera carga y cuenta las cajas de la corrida. La captura muestra las masas con 2 kg por volt y el aviso de los registros anteriores al cambio de unidad.
- Verificación 5: Node-RED queda detenido y el reporte dice cuántos registros `caja` y cuántos `latido` se escribieron.

### D. Ensayo con una consulta real a Gemini

Marcas: ESCENA, NUBE, GEMINI. No necesita a Ari.

- `pruebas/ensayo_demo.py --real` gana una opción que conserva la llave de Gemini en el archivo de variables del ensayo y enciende la nube en ese mismo archivo, ya que hoy toma `A2_NUBE` de `.env`, que sigue en 0. Con esa opción el archivo lleva `A2_DIAG_MAX_DIA=1`, para que el tope diario del propio flujo impida una segunda consulta, incluida la del disparo periódico.
- El paso 7 del ensayo presiona una vez el botón de diagnóstico.
- Verificación 1: el ensayo pasa todas sus comprobaciones sin ningún paso bloqueado. En octubre fueron 21 de 21 con Gemini sin llave.
- Verificación 2: hay exactamente una consulta real. `a2_diagnosticos_<día>.csv` del ensayo tiene una sola fila con respuesta del modelo, la respuesta pasó `38_diag_valida.js` y la HMI la muestra.
- Verificación 3: una segunda pulsación del botón en el mismo ensayo se rechaza por el tope sin salir a la red, y la HMI no muestra nada inválido.
- Verificación 4: en los 30 s siguientes al diagnóstico, `a2_planta_eventos.jsonl` no tiene ningún `comando` que provenga del diagnóstico.
- Verificación 5: el ensayo sin la opción y sin `--real` sigue pasando como antes, sin llave y sin consulta.
- El texto de la respuesta, el modelo y su latencia quedan en el documento de ciclo. La llave no se imprime.
- Si la consulta falla por cuota, por un error HTTP o por la red, no la repitas. Registra el código, deja el paso abierto y dilo en tu reporte.

### C. Carrera de la prueba de gráfica

No usa la escena ni la base real.

- `pruebas/prueba_grafica.py` espera a que la última escritura de A2-Nube esté en el emulador y a que la página la haya recibido antes de tomar la muestra final.
- La comparación entre las cajas de la página y las del emulador sigue siendo una igualdad. No se cambia por una tolerancia.
- Si la página no alcanza la cuenta del emulador dentro del plazo de espera, la prueba falla y muestra los dos números.
- Verificación: la prueba pasa todas sus comprobaciones en cinco corridas seguidas.

## Fuera de esta orden

- La regla de falla estática de la capa de materiales y el estudio de las pesadas con más de una pieza.
- La rama de materiales en Firebase y la evaluación del diagnóstico contra la verdad de la capa.
- El lazo de comandos con aprobación humana.
- Cualquier cambio al texto que recibe Gemini o al conjunto de acciones que puede devolver.
- Cualquier cambio a la lógica del cliente, por la regla 6 de esta orden.
- El documento técnico y la respuesta al profesor.

## Al terminar

Tu reporte trae lo siguiente.

1. Una tabla con cada paso, su commit, su verificación y su código de salida.
2. Para A3, el número de pulsaciones registradas sobre el total y la conclusión en una oración.
3. Para G, los cinco valores de `linea` antes y después, con la fuente de cada uno.
4. El número de registros escritos en `planta_01` en cada paso con nube y el número de consultas reales a Gemini, que es 1, o 0 si la consulta falló.
5. La confirmación de que `.env` sigue con `A2_NUBE=0`, de que no queda ningún Node-RED corriendo y de que el árbol está limpio.
6. Los puntos en que esta orden no coincidió con el código.
