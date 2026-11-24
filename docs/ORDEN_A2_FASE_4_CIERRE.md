# Orden para Claude Code. Actividad 2, cierre de la fase 4: Stop con una lectura, límites con tiempos medidos y segundo ensayo con Gemini

Fecha: 17 de noviembre de 2026. Esta orden complementa `docs/ORDEN_A2_FASE_4.md` y no la sustituye. Lo que aquí no se menciona sigue como dice esa orden.

## Contexto

Sigues en `~/dev aws/dev/IoT`, en la Mac mini. El último commit es `390021a`, con los pasos B, I y C cerrados, el paso A detenido en A3, el paso G con cuatro valores de `linea` todavía estimados y el paso D con 23 de 24 en el ensayo. Cowork auditó la fase contra el código y los datos, y Ari tomó tres decisiones el 17 de noviembre de 2026.

1. **Botones del tablero.** Stop actúa con una sola lectura, ya que detener la línea es la dirección segura. Start conserva las dos lecturas, y su límite queda documentado. En la sesión A el cliente registró 16 de 20 pulsaciones de Stop y 21 de 23 de Start, y las seis que no registró duraron de 63 a 98 ms, sin ningún hueco de sondeo.
2. **Geometría.** Los dos límites de tiempo de recorrido del cliente dejan de calcularse con metros y velocidad estimados y pasan a calcularse con tiempos de recorrido medidos. El manual de Factory I/O da longitudes de banda (2, 4 y 6 m) y una velocidad máxima de 0.6 m/s, pero no la unidad de las posiciones de la escena ni el tamaño de las piezas, por lo que distancia y velocidad no se pueden separar.
3. **Gemini.** Ari autoriza una segunda consulta real, para repetir el ensayo completo con la corrección de la espera a Chrome ya hecha.

## Forma de trabajo

Siguen vigentes las reglas de `docs/ORDEN_A2_FASE_4.md`, con estos cambios.

1. La regla 6 de esa orden se levanta para los dos cambios al cliente que piden los pasos S y H, y solo para ellos. Ningún otro cambio a la lógica del cliente entra en esta orden.
2. La regla 3 de esa orden cambia. Hay una consulta real más a Gemini, en el paso D2, con lo que la fase suma dos. Si esa consulta falla por una causa externa, o si el ensayo falla en otra comprobación, no se repite.
3. Los commits llevan el prefijo `F4 cierre`, uno por paso. El primer commit agrega esta orden, sin más cambios.
4. El orden es S, H y D2. El paso S va primero porque necesita a Ari presente. El paso D2 va al final para que el ensayo completo corra con el cliente ya cambiado.
5. La nube va apagada en S y en H. Solo D2 la enciende, en su propio archivo de variables.

## Puertas de Ari

| Puerta | Estado | Qué desbloquea |
|---|---|---|
| V0 | Ari la abre al dejar la escena de Factory I/O en Play | Los pasos S, H y D2 |
| S0 | Cerrada hasta que Ari esté frente a la Mac | La sesión del paso S |
| N0 | Abierta para el paso D2 | El paso D2 |
| G1 | Abierta el 17 de noviembre de 2026. Ari autorizó una segunda consulta real a Gemini | El paso D2 |

## Antes de los pasos: tres notas en el registro

Estas notas van en la sección de la fase 4 de `docs/CICLO_DESARROLLO_A2.md`, en el primer commit de trabajo, sin cambiar código del cliente.

- **Duración de las pulsaciones del paso T.** El modo `tablero` de `pruebas/prueba_fio.py`, tal como corrió en el commit `28a1b75`, esperaba 0.6 s después de ver cada cambio antes de anotar su hora. Por eso todas las pulsaciones de `datos/corridas/T_2026-11-11/prueba_fio.log` aparecen con 0.6 a 0.7 s entre presionar y soltar. Ese valor es la espera del vigilante y no la duración de la pulsación, que no quedó registrada.
- **Latidos escritos.** Los CSV de la nube guardados muestran 42 latidos aceptados en el paso A y 14 en el paso I contando el intento abortado, no 31 y 13. Vuelve a contar los registros `caja` y `latido` de cada paso desde sus CSV y corrige la tabla.
- **Cajas durante A3.** `datos/corridas/A_2026-11-17/a2_planta_eventos.jsonl` tiene, dentro de A3, 4 eventos `caja_perdida` con motivo `sin_confirmacion`, 4 `desvio_erroneo`, 4 `caja_fantasma` y 7 `caja_purgada`, además de 4 `paso_caja` con `rechazo_fallido` en verdadero. Son cajas a las que un Stop las alcanzó en el desviador. `docs/sesion_A.md` no los reporta. `tools/analiza_sesion_a.py` gana un resultado que cuente esos eventos por parte, y `docs/sesion_A.md` se regenera con él. No se corrige ese comportamiento en esta orden.

## Pasos

### S. Stop con una lectura

Marcas: ESCENA, ARI. La sesión con Ari dura cerca de 3 minutos.

- El antirrebote de `node-red/funciones/28_planta_lectura.js` acepta un cambio de `stop_button` con una sola lectura. Los demás sensores y botones conservan `lecturas_para_cambio`, que sigue en 2. La forma recomendada es un valor propio del botón en el bloque `tablero` de la configuración, que por omisión toma el valor general.
- Emergency stop no cambia. Actúa por nivel y el botón de la escena queda enclavado hasta el segundo clic, como mostró el paso A2.
- `pruebas/prueba_tablero.py` gana tres casos contra el servidor Modbus emulado: un Stop que dura una sola lectura detiene la línea, un Start que dura una sola lectura no la arranca, y una sola lectura falsa en un sensor de la línea no produce flanco. Comprueba por mutación que el primer caso falla si se quita el cambio.
- Sesión con Ari, con `pruebas/sesion_ari.py` en la parte de Start repetido y la nube apagada. Ari presiona Start y Stop veinte veces cada uno, alternados, con clics rápidos como los de A3. Los datos quedan en `datos/corridas/S_<fecha>/` y el reporte en `docs/sesion_S.md`, con la misma herramienta.
- Verificación 1: toda pulsación de Stop que contenga al menos un ciclo de sondeo completo tiene su evento `boton` del cliente. Reporta aparte las que no contengan ninguno.
- Verificación 2: el reporte da, para Start, las vistas y las registradas por número de ciclos dentro de la pulsación, igual que en A3, sin exigir un mínimo.
- Verificación 3: el reporte cuenta por parte los eventos `caja_perdida`, `desvio_erroneo`, `caja_fantasma` y `caja_purgada` de la sesión.
- Verificación 4: batería completa con 0 fallidas y `pruebas/prueba.sh` en 26 de 26.

### H. Límites del cliente con tiempos de recorrido medidos

Marca: ESCENA. No necesita a Ari.

El cliente calcula hoy dos límites con valores estimados. `timeout_confirmacion_s` sale de `1.5 × fin_bascula_a_confirmacion_m / velocidad_fija_m_s` más el antirrebote y la ida y vuelta, en `node-red/funciones/26_planta_config.js`. El límite de las cajas que no llegan a la salida de la báscula sale de `1.5 × entrada_a_fin_bascula_m / velocidad_fija_m_s` más tres periodos, en `node-red/funciones/28_planta_lectura.js`. `largo_caja_m` se exige al validar y no se usa en ninguna cuenta del desviador.

- Define en `docs/INSTRUMENTACION_A2.md` los dos tramos con eventos del cliente, para poder medirlos en todas las corridas guardadas. El tramo de confirmación va del evento `caja_pesada` a `ts_salida` del `paso_caja` de la misma caja. El tramo previo al pesaje va de `ts_entrada` de `caja_entra` a la escritura que apaga `entry_conveyor` por pesaje para esa caja.
- Mide los dos tramos en las corridas sin paros intermedios, que son L1, L2, M1, G e I. No uses A ni D, que tienen paros y una desconexión. Una herramienta escribe `docs/corrida_H.md` con n, mediana, p95 y máximo por corrida y en conjunto. `docs/corrida_G.md` no se regenera.
- `linea` de `config/planta_fio.json` gana los dos tiempos medidos, que son el máximo de cada tramo en esas cinco corridas, y pierde `velocidad_fija_m_s`, `largo_caja_m`, `entrada_a_fin_bascula_m` y `fin_bascula_a_confirmacion_m`. Su nota dice qué se midió, en cuántas cajas y cuándo.
- Cada límite queda como 1.5 veces su tiempo medido, más los mismos términos de antirrebote e ida y vuelta de hoy, más `comunicacion_timeout_ms`. El último término hace explícita la holgura que antes venía de distancias sobrestimadas: un hueco de comunicación menor que ese tiempo no dispara la secuencia segura, por lo que el límite tiene que tolerarlo.
- El cliente acepta las dos formas. Si `linea` trae los tiempos medidos, los usa. Si no, calcula con distancia y velocidad como hoy, de modo que las configuraciones del sustituto no cambian y dan los mismos límites que antes. Una configuración del desviador sin ninguna de las dos formas completas se rechaza con un error que lo diga.
- Referencia de Cowork, calculada con los eventos del cliente: 2,086 cajas en las cinco corridas, máximo de 1.757 s en el tramo de confirmación (M1) y de 0.261 s en el tramo previo al pesaje (G). Con `T_ef` de 55 ms y 5 ms de ida y vuelta, los límites serían 4.81 s y 2.56 s, frente a 4.67 s y 6.17 s de hoy. Si tus máximos difieren de estos, reporta la diferencia y su causa.
- Verificación 1: con `config/planta_desviador.json` los dos límites son los mismos que antes del cambio. Con `config/planta_fio.json` son los de la fórmula nueva. Una configuración sin ninguna forma completa se rechaza, comprobado por mutación.
- Verificación 2: ninguna caja de las cinco corridas supera el límite nuevo de su tramo. Reporta el margen de cada uno.
- Verificación 3: `tools/limites_planta.py` da el mismo veredicto que antes para el escenario `parallels`.
- Verificación 4: `pruebas/prueba_fio.py cliente --cajas 200` pasa 17 de 17, sin ningún evento `caja_perdida`.
- Verificación 5: batería completa con 0 fallidas y `pruebas/prueba.sh` en 26 de 26.

### D2. Segundo ensayo con una consulta real a Gemini

Marcas: ESCENA, NUBE, GEMINI. No necesita a Ari.

- Corre una vez `pruebas/ensayo_demo.py --real --con-gemini`, con el cliente ya cambiado por S y H. Los datos quedan en `datos/corridas/D2_<fecha>/`.
- Verificación 1: el ensayo pasa todas sus comprobaciones, sin ningún paso bloqueado.
- Verificación 2: hay exactamente una consulta real en este ensayo, válida y mostrada en la HMI, y la segunda pulsación se detiene en el tope. La fase suma dos consultas reales.
- Verificación 3: en los 30 s siguientes al diagnóstico no hay ningún `comando` que provenga de él.
- El texto de la respuesta, el modelo y su latencia quedan en el documento de ciclo. La llave no se imprime.
- Si algo falla, no repitas el ensayo. Registra la salida completa y dilo en tu reporte.

## Fuera de esta orden

- El comportamiento de las cajas que un Stop alcanza en el desviador, que solo se registra.
- El tope `DIAG_MAX_DIA` de la pestaña de diagnóstico de la Actividad 1, que convierte el 0 en 200.
- La ventana de 300 registros de `web/proceso.html`.
- Todo lo que `docs/ORDEN_A2_FASE_4.md` dejó fuera.

## Al terminar

Tu reporte trae lo siguiente.

1. Una tabla con cada paso, su commit, su verificación y su código de salida.
2. Para S, las pulsaciones de Stop y de Start vistas y registradas, y el conteo de eventos de cajas de la sesión.
3. Para H, los dos tiempos medidos, los dos límites antes y después, y el margen sobre el máximo observado.
4. Para D2, el resultado del ensayo y el número de consultas reales de la fase.
5. Los registros `caja` y `latido` escritos en `planta_01` en cada paso de la fase, contados desde los CSV.
6. La confirmación de que `.env` sigue con `A2_NUBE=0`, de que no queda ningún Node-RED corriendo y de que el árbol está limpio.
7. Los puntos en que esta orden no coincidió con el código.
