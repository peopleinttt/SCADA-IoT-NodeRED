# Orden para Claude Code. Actividad 2, fase 3: correcciones de la revisión y capa de materiales mínima

Fecha: 10 de noviembre de 2026. Esta fase no tiene fecha de entrega fija. Su límite práctico es la licencia de prueba de Factory I/O, cuya fecha de término no está comprobada y se lee en la aplicación cuando la escena vuelva a abrir.

## Contexto

Sigues en `~/dev aws/dev/IoT`, en la Mac mini. Lee primero `docs/ORDEN_A2_FASE_1.md`, `docs/ORDEN_A2_FASE_2.md`, `docs/CICLO_DESARROLLO_A2.md` y `docs/PARAMETROS_MATERIALES.md`. La Actividad 2 quedó cerrada el 24 de octubre de 2026 en el commit `621ad6d`.

La documentación técnica se envió a revisión. El revisor señaló cinco puntos que no se resuelven redactando: el editor de Node-RED sin autenticación, los botones Stop y Emergency stop que nunca se presionaron en la escena real, la distribución de masas que cambia entre corridas, la posible saturación de la báscula y la ausencia de la capa de materiales. Al preparar esa documentación apareció un sexto punto en el código, que es el estado `emergencia` que A2-Nube no acepta. Esta fase atiende los seis.

Estado medido el 10 de noviembre de 2026 desde Cowork, solo con lecturas:

- Node-RED está apagado. Estuvo encendido del 24 de octubre al 8 de noviembre con `A2_NUBE=1` y `PLANTA_ID=planta_01`. En ese periodo A2-Nube escribió en la base real 21688 latidos y 429 registros de caja, según `datos/a2_nube_*.csv`. Desde el 6 de noviembre los latidos repiten el mismo `ts_origen`, lo que indica que ya no había lecturas Modbus.
- `prlsrvctl info` reporta `License: state='not valid'` y la máquina virtual `Windows 11` está suspendida desde el 6 de noviembre a las 10:22, que es el instante en que dejaron de llegar lecturas Modbus. Mientras Ari no resuelva esa licencia no hay escena.
- El árbol de trabajo tiene sin versionar seis archivos en `docs/`, que son los `.docx` y `.pdf` de la documentación técnica y de la respuesta al revisor. No los modifiques. Agrégalos al repositorio solo si Ari lo pide.
- El último commit es `621ad6d`. Al momento de la revisión no había procesos de Node-RED ni de pruebas en marcha.

## Forma de trabajo

Siguen vigentes las reglas de las fases 1 y 2. Las que más pesan aquí, junto con las nuevas, son estas.

1. Trabajas de corrido, un paso a la vez. Un paso se cierra solo con la salida de su verificación a la vista y con su código de salida visible. Te detienes en tres casos: una verificación que no pasa después de dos correcciones dentro del mismo paso, una PUERTA ARI que no se ha abierto, o algo que te obligue a romper una regla. En los tres casos dejas el árbol limpio, escribes en el documento de ciclo qué falta y por qué, y sigues con el siguiente paso que no dependa de lo bloqueado.
2. `docs/CICLO_DESARROLLO_A2.md` gana una sección "Fase 3" con su tabla de estado. Cada paso deja ahí lo hecho, las pruebas con su salida, las decisiones y lo pendiente. Haces un commit por paso, con el prefijo `F3`.
3. El primer commit de la fase agrega esta orden y `docs/PARAMETROS_MATERIALES.md`, sin más cambios.
4. Nunca corres dos pruebas a la vez, ni una prueba mientras otra sesión usa los mismos puertos.
5. Ninguna credencial entra al repositorio. Tú nunca conoces la contraseña del editor que elija Ari, y ninguna prueba ni script puede necesitarla.
6. Nada escribe en `planta_01` durante esta fase. Al empezar, pon `A2_NUBE=0` en `.env` y déjalo así. Con ese valor `demo_a2.sh` avisa que la nube está apagada, que es lo esperado. La base real solo se toca en el paso E, en `planta_99`, con las pruebas de reglas.
7. Ninguna consulta real a Gemini en esta fase.
8. Las pestañas de la Actividad 1 no cambian, y `pruebas/prueba.sh` sigue en 26 de 26 después de cada paso. La batería completa pasa al cerrar cada paso.
9. Todo lo que se ve en pantalla va en inglés. El código y los documentos internos siguen en español.
10. Los pasos marcados ESCENA esperan la PUERTA ARI V0. No intentes reanudar la máquina virtual ni tocar Parallels.
11. Lo que se mide se define por escrito antes de medir, en `docs/INSTRUMENTACION_A2.md`.
12. Esta orden se escribió leyendo el código con búsquedas, sin ejecutarlo. Si un dato de la orden no coincide con el código, vale el código. Detente en ese punto, anótalo en el documento de ciclo y dilo en tu reporte.
13. Ningún valor de la capa de materiales se inventa ni se ajusta para que una prueba pase. Los valores salen del Anexo A, y los resultados esperados, del Anexo B.

## Puertas de Ari

| Puerta | Qué hace Ari | Qué desbloquea |
|---|---|---|
| V0 | Deja la máquina virtual disponible, con Factory I/O abierto, la escena Sorting by Weight en Play y el driver conectado | Los pasos T, U, L y M3 |
| A1 | Corre `./prepara_admin.sh` y escribe su usuario y su contraseña | El cierre del paso S2 |
| P2 | Publica `firebase/database.rules.generado.json` en la consola de Firebase | La verificación del paso E contra la base real |
| M0 | Confirma el dimensionamiento de la sección 8 de `docs/PARAMETROS_MATERIALES.md` | Los pasos M1, M2 y M3 |
| U0 | Envía dos capturas de la escena en modo de edición: la configuración de la báscula y la lista de artículos del emisor | El paso U |
| T0 | Presiona los botones del tablero cuando la prueba lo pida | El paso T |

El mensaje con que Ari inicie la sesión dice qué puertas están abiertas. Una puerta que ese mensaje no mencione está cerrada.

## Pasos

### S2. Autenticación del editor. ESENCIAL

El paso S de la fase 2 cerró el puerto 1881 frente al túnel de Cloudflare, no obstante el editor y la API de administración siguen abiertos sin contraseña para cualquier equipo de la red local o de la tailnet. El filtro del túnel reconoce cabeceras y no identidades.

- `node-red/settings.js` gana `adminAuth` con un solo usuario de permisos completos. El usuario sale de `NODE_RED_ADMIN_USER` y el hash bcrypt de `NODE_RED_ADMIN_HASH`, ambos del entorno. No existe contraseña por omisión. Confirma los nombres y el formato de `adminAuth` en la documentación de Node-RED para la versión instalada, en la página Securing Node-RED, antes de escribir.
- Si falta cualquiera de las dos variables, el editor y la API de administración quedan deshabilitados, y Node-RED lo dice en su registro. Los flujos, la HMI, las rutas `/a2/planta/*` y la ingesta de la Actividad 1 siguen funcionando. Sin credenciales se cierra el editor, nunca se abre.
- `prepara_admin.sh`, nuevo e interactivo: pide el usuario y la contraseña dos veces sin mostrarla, calcula el hash con la misma biblioteca bcrypt que usa el Node-RED instalado y escribe o reemplaza las dos variables en `.env`. No imprime la contraseña ni el hash. Con `--revisa` solo dice si las dos variables existen y si el hash tiene formato bcrypt, y lo refleja en su código de salida. `.env.example` gana los dos nombres sin valores.
- Varias esperas de arranque consultan `GET /settings`, que deja de contestar 200. Las que encontré son `demo_a2.sh` línea 139, `enciende.sh` línea 24, `pruebas/prueba.sh` línea 47 y `pruebas/prueba_sustituto.py` línea 81. La última usa `urllib`, que trata un 401 o un 404 como error, por lo que todas las pruebas que arrancan con `ps.arranca` dejarían de arrancar. Cambia esas esperas por una que no dependa de la API de administración y búscalas todas de nuevo, no confíes en mi lista.
- `pruebas/ensayo_demo.py` línea 75 lee `/flows` para contar pestañas. Con el `.env` real esa lectura exigiría la contraseña de Ari, por lo que debe obtener las pestañas por otro camino, como el archivo de flujos en disco.
- Las pruebas que necesiten la API de administración generan credenciales desechables en cada corrida, con una contraseña aleatoria cuyo hash solo vive en el entorno del proceso de prueba.
- `arranca.sh` y `estado.sh` dicen si el editor está protegido o deshabilitado.
- Alcance que se declara y no se cambia: `/dashboard/a2` y `/a2/planta/*` no usan `adminAuth` y siguen como están, abiertos a la red local y a la tailnet y cerrados al túnel. No agregues `httpNodeAuth`, ya que cerraría la ruta de ingesta que usa el ESP32.

Verificación, en `pruebas/prueba_seguridad.py` ampliada. Las líneas 63 y 64 de esa prueba hoy esperan 200 en `/flows` y `/settings` y deben cambiar.

1. Con credenciales desechables y sin token: leer y escribir flujos, leer el contexto, listar nodos y cualquier otra ruta de la API de administración que entregue contenido se rechaza. El websocket del editor no entrega eventos sin autenticarse.
2. Con una contraseña equivocada no se obtiene token. Con la correcta se obtiene, y con ese token `/flows` contesta 200.
3. Sin las dos variables, la API de administración no se sirve, `/dashboard/a2` contesta 200, `POST /telemetria` llega a la ingesta y los flujos corren.
4. Con las cabeceras del túnel todo sigue en 403 salvo la ingesta, igual que en el paso S.
5. La batería completa pasa con las esperas nuevas, y `pruebas/prueba.sh` sigue en 26 de 26.
6. Una búsqueda en el repositorio y en su historial de esta fase no encuentra hashes bcrypt ni contraseñas.

PUERTA ARI A1: Ari corre `./prepara_admin.sh`. Después tú corres `./prepara_admin.sh --revisa` y registras su salida. La comprobación final, que es abrir el editor y ver que pide usuario y contraseña, la hace Ari.

### E. Estado de emergencia y latido en reposo en A2-Nube. ESENCIAL

`32_nube_registro.js` toma `estado_linea` de `R.linea` cuando hay comunicación, y el paro de emergencia pone esa línea en `emergencia`. Ese valor no está en la expresión regular de `33_nube_valida.js` ni en la de las reglas de Firebase, por lo que la validación local descarta todos los latidos mientras el paro está activo.

E1, esencial:

- Agrega `emergencia` a los valores cerrados de `estado_linea` en `firebase/database.rules.json`, en `33_nube_valida.js` y en la lista de `pruebas/prueba_nube.py` línea 53. Las reglas del emulador en `pruebas/emulador/database.rules.json` deben quedar iguales a las del repositorio, por el camino con que hoy se generan. Mi búsqueda encontró esos estados también en `node-red/hmi/a2_hmi.vue`, en `35_hmi_estado.js`, en `pruebas/prueba_hmi.py`, en `pruebas/ensayo_demo.py`, en `pruebas/prueba_planta.py` y en `pruebas/prueba_desviador.py`. Revisa cuáles enumeran valores permitidos y cuáles solo los usan, y busca de nuevo por tu cuenta.
- `web/proceso.html` muestra ese estado como `EMERGENCY STOP`.
- `pruebas/prueba_reglas_proceso.py` gana un caso que permite un latido con `emergencia` y conserva el caso que niega un estado inventado.
- Verificación: primero muestra la prueba fallando sin el cambio. Con el paro presionado y la nube simulada encendida, el latido con `estado_linea` igual a `emergencia` se acepta y el CSV de A2-Nube no registra rechazos. Las reglas pasan en el emulador, con un caso más en `proceso` y los 50 de la Actividad 1 sin cambio.
- Corre `./firebase/prepara.sh` y deja listo `firebase/database.rules.generado.json`.
- PUERTA ARI P2: Ari publica ese archivo. Después corres `python3 pruebas/prueba_reglas_proceso.py --planta planta_99` y `python3 pruebas/prueba_reglas_real.py --planta planta_99` y registras su salida. Esas escrituras en `planta_99` están autorizadas.

E2, deseable:

- Con la línea fuera de marcha y el mismo `estado_linea` que en el latido anterior, el latido sale cada `A2_LATIDO_REPOSO_S`, con 900 s por omisión. Un cambio de estado produce un latido inmediato. Con la línea en marcha el periodo sigue siendo `A2_LATIDO_S`. El motivo son los 21688 latidos que quedaron en la base real en quince días con la línea detenida.
- Verificación en `pruebas/prueba_nube.py` con periodos cortos: en marcha salen al ritmo de `A2_LATIDO_S`, detenida salen al ritmo de reposo, y cada cambio de estado deja un latido en menos de dos segundos. La corrida instrumentada de C9 no cambia sus cifras, ya que mide con la línea en marcha.
- Actualiza `docs/DEMO_A2.md` y `docs/INSTRUMENTACION_A2.md` en donde describen el latido.

### M1. Modelo de la capa de materiales. ESENCIAL, con PUERTA ARI M0

Este paso construye el modelo sin planta y sin Node-RED en marcha. `docs/PARAMETROS_MATERIALES.md` explica de dónde sale cada número y por qué el diseño es así. Léelo completo antes de empezar.

- `config/materiales.json` con el contenido exacto del Anexo A. Es la fuente única, como lo es el mapa de registros.
- El modelo, con estas definiciones:
  - Fracción de carga: `f = peso_V / senal_plena_escala_V`. No usa la masa en kilogramos.
  - Ciclo de esfuerzo: `sigma_max = sigma_ref · (R_ref + (1 − R_ref) · f)`, `sigma_min = sigma_ref · R_ref` y `delta_sigma = sigma_max − sigma_min`.
  - Intervalo ensayado de cada laminado: de `nivel_min_pct` a `nivel_max_pct` por ciento de su `sigma_uts_MPa`, con los extremos incluidos.
  - Región de cada paso para cada laminado: `bajo` si `sigma_max` queda por debajo del intervalo, `dentro` si cae en él y `sobre` si lo supera.
  - Vida: `N_ajuste = (sigma_max / a)^(1/b)` y `N_usado` es el menor entre `N_ajuste` y `n_tope_ciclos`.
  - Daño: un paso `dentro` suma `ciclos_por_paso / N_usado`. Un paso `bajo` no suma daño y se cuenta. Un paso `sobre` tampoco suma daño, se cuenta y levanta la alerta `carga_fuera_del_intervalo`. Nunca se extrapola.
  - D se acumula por laminado y nunca decrece.
  - Nivel: `normal` con D menor que 0.5, `preventiva` desde 0.5, `critica` desde 0.8 y `falla` desde 1.0.
  - Rigidez perdida d(D): interpolación lineal en la tabla `rigidez` del laminado. Con D mayor que 1 se usa el último valor.
  - Galga: `deformacion_ue = delta_sigma / (E0 · (1 − d(D))) · 10^6 + ruido`, con E0 en MPa y con D tomado antes de sumar el daño de ese paso. El ruido es gaussiano con desviación `ruido_sd_ue`, de un generador con semilla, uno por laminado, como en el sustituto.
  - Un paso sin peso no se evalúa y se cuenta como `sin_peso`.
- Un validador de la configuración que rechaza, con un código estable por error: `b` mayor o igual que cero, `a` menor o igual que cero, intervalo invertido, umbrales desordenados, tabla de rigidez que no empieza en `[0, 0]`, con D que no crece de forma estricta, con d que decrece o con D fuera de 0 a 1, y cualquier campo desconocido.
- `tools/materiales.py`, en Python 3.9 sin dependencias, con la misma cuenta por un segundo camino: `valida`, `referencia` (imprime la tabla del Anexo B) y `recalcula --eventos <jsonl> --desde <ts> --hasta <ts>` (D y conteos por región de cada laminado a partir de eventos `paso_caja`).
- El archivo de JavaScript que usa el flujo es el mismo que ejecutan las pruebas del modelo, sin copias del código. Elige tú la forma, sea un módulo cargado desde `settings.js` o el archivo de función ejecutado por un arnés, y documenta la decisión.

Verificación, en `pruebas/prueba_materiales.py modelo`, dentro de la batería:

1. JavaScript y Python reproducen la tabla del Anexo B: `sigma_max` con diferencia relativa menor a 10^−9, `N_ajuste`, `N_usado` y ΔD con diferencia relativa menor a 10^−6, y la región exacta.
2. Carga constante y secuencia mixta del Anexo B, con el mismo criterio, y D nunca decrece.
3. Las fronteras del Anexo B: 8.99 V queda `bajo` y 9.00 V queda `dentro` con el tope en el laminado 0:0, y 9.98 V queda `bajo` y 9.99 V queda `dentro` en el 9:1.
4. La rigidez interpolada y la galga sin ruido del Anexo B, con diferencia menor a 0.01 µε en la galga.
5. Con ruido, la misma semilla da la misma secuencia, y en 10000 muestras la media queda dentro de 1 µε de cero y la desviación dentro de 1 µε de 25.
6. JavaScript y Python coinciden en D con diferencia relativa menor a 10^−9 sobre una secuencia de 10000 pesos generada con semilla.
7. Cada rechazo del validador con su control, y una prueba de mutación como la de C1: con cada regla apagada, su caso de rechazo deja de rechazar.
8. `python3 tools/materiales.py recalcula` sobre `datos/a2_planta_eventos.jsonl`, entre `2026-10-25T01:00:00Z` y `2026-10-25T03:00:00Z`, da 429 cajas, D = 0.54952814 con 10 pasos `dentro` y 419 `bajo` en el laminado 0:0, y D = 0.01250000 con 5 `dentro` y 424 `bajo` en el 9:1. Esas cifras las calculé yo por separado el 10 de noviembre. Si el archivo ya no está o cambió, dilo y omite este punto.

PUERTA ARI M0: si el mensaje de inicio no dice que M0 está abierta, no empieces M1.

### M2. Pestaña A2 · Materiales contra el sustituto. ESENCIAL

- Pestaña nueva `A2 · Materiales (capa de materiales)`, generada por `node-red/construye_flows.py` con funciones en archivos separados, numeradas a partir de 39. Solo trabaja con `A2_MATERIALES=1`. La configuración sale de `A2_MAT_CONFIG`, con `config/materiales.json` por omisión. Sin la bandera, la pestaña no hace nada, no crea archivos y la batería no cambia.
- Entrada: el enlace `a2_paso_caja` de A2-Planta gana un segundo destino. A2-Planta y A2-Nube no cambian su comportamiento.
- Estado por laminado en el contexto `flow` de la pestaña y en `$DATOS_DIR/a2_materiales_estado.json`, escrito de forma atómica cada vez que cambia. Al arrancar se carga ese archivo, ya que D es vida consumida y no se reinicia con Node-RED. Si el archivo existe y no se puede leer, la pestaña no acumula y lo dice en su estado. No reinicia en silencio.
- Dos archivos por separado. `$DATOS_DIR/a2_materiales_medido.jsonl` lleva lo que un sistema real mediría, una línea por paso y laminado: `ts_salida`, `caja`, `pieza`, `peso_V`, `peso_estable`, `f`, `sigma_max_MPa`, `delta_sigma_MPa`, `deformacion_ue` y el número de paso. `$DATOS_DIR/a2_materiales_verdad.jsonl` lleva la verdad del modelo: `ts_salida`, `caja`, `pieza`, `region`, `N_usado`, `dD`, `D`, `d` y `nivel`.
- Separación entre lo medido y la verdad. La verdad no entra al contexto `global`, no entra al archivo de lo medido y no sale de la pestaña salvo por el enlace hacia la HMI. `global.a2_mat_medido` publica solo lo medido, con los últimos 30 pasos por laminado y los conteos de pasos. La pestaña de diagnóstico no se modifica en esta fase.
- HMI: una tarjeta `Materials layer` en inglés, que solo aparece con `A2_MATERIALES=1`. Por cada varilla muestra la vida consumida en porcentaje con un decimal, el nivel, los pasos dentro, por debajo y por encima del intervalo, el último rango de deformación medido y la estimación de pasos y de tiempo restantes, o `no estimate yet` mientras no haya al menos 100 pasos y uno con daño. Un cambio de nivel se ve en pantalla. Sus datos llegan por un enlace desde la pestaña de materiales y no por el contexto `global`.
- La capa no escribe en la planta, no escribe en Firebase y no consulta a Gemini.

Verificación, en `pruebas/prueba_materiales.py`, dentro de la batería:

1. Sin `A2_MATERIALES`, la pestaña no crea archivos, la HMI no muestra la tarjeta y la batería pasa igual que antes.
2. Corrida contra el sustituto del desviador, con una configuración de sustituto para esta prueba cuyas masas dejen pasos en las regiones `dentro` y `bajo` de ambos laminados. El archivo de verdad coincide con `tools/materiales.py recalcula` sobre los `paso_caja` del cliente: D por laminado con diferencia relativa menor a 10^−9, conteos por región exactos y D sin decrecer.
3. Separación: el archivo de lo medido no trae ningún campo de la verdad. El contexto `global`, leído por la API de administración con el token desechable del paso S2, no trae ninguna clave ni valor de la verdad. En `flows.json` no hay cable ni enlace de la pestaña de materiales hacia la de diagnóstico, y las funciones `37_diag_arma.js` y `38_diag_valida.js` son idénticas a las de `HEAD`.
4. Persistencia: se detiene Node-RED a media corrida y al volver D continúa desde el último valor del archivo de verdad. Con el archivo de estado dañado, la pestaña no acumula y lo reporta.
5. Umbrales: con una configuración de prueba que lleve a D por encima de 1, la HMI pasa por `normal`, `preventive`, `critical` y `failure` en ese orden y en los pasos que predice el recálculo.
6. Región `sobre`: con una configuración de prueba cuyo `sigma_ref_MPa` deje pasos por encima del intervalo, esos pasos se cuentan, levantan la alerta en la HMI y no cambian D.
7. Galga: la deformación del archivo de lo medido coincide, con diferencia menor a 0.1 µε, con la que se recalcula a partir de la secuencia de D de la verdad y del ruido con la misma semilla.
8. Regresión: batería completa, `pruebas/prueba.sh` en 26 de 26 y los nodos de la Actividad 1 idénticos.

### T. Tablero en la escena real. ESENCIAL, ESCENA, con PUERTAS ARI V0 y T0

- Con la escena en Play, corre `/usr/bin/python3 pruebas/prueba_fio.py tablero -s 180`, con el relevo `node pruebas/relevo.mjs 5031 10.211.55.3 502` si Python sigue sin permiso de red local. Avisa a Ari cuando la prueba diga que está vigilando. Ari presiona, en este orden, Start, Stop, Start, Emergency stop sostenido unos segundos, suelta Emergency stop, Start y Stop.
- Verificación: todas las comprobaciones de ese modo pasan. Con eso, Stop y Emergency stop quedan confirmados como normalmente cerrados al presionarlos, y `config/mapa_registros_fio.json` y `docs/MAPA_REGISTROS.md` dejan de decir que solo se conocen por su reposo.
- Si una comprobación falla, no corrijas el cliente para que pase. Registra la salida completa y detente en este paso.

### U. Unidad de masa de la báscula. ESENCIAL si la puerta lo confirma, con PUERTA ARI U0

El manual de Factory I/O indica que la báscula de banda tiene configuraciones de 20 kg y de 100 kg con salida de 0 a 10 V. Los siete niveles de peso que aparecen en los datos del 25 de octubre equivalen, con 2 kg por volt, a siete pesos del catálogo de artículos. `config/planta_fio.json` supone hoy 1 kg por volt, con `plena_escala_kg` en 10.0. La sección 9 de `docs/PARAMETROS_MATERIALES.md` da el detalle.

- U0: Ari envía la captura de la configuración de la báscula y la de los artículos que emite la escena.
- Si la báscula está en 20 Kg Max: `plena_escala_kg` pasa a 20.0 y los umbrales de clase pasan a 9.0 y 14.0 kg, de modo que la clasificación ocurra en los mismos 4.5 y 7.0 V. Actualiza lo que imprima kilogramos, que incluye la HMI, la gráfica, `docs/DEMO_A2.md`, las masas del prompt de diagnóstico y las pruebas con masas esperadas. La regla de Firebase ya admite `caja_masa_kg` hasta 20.
- Verificación: una prueba de clasificación en 4.49, 4.51, 6.99 y 7.01 V da los mismos destinos que antes del cambio, y la batería completa pasa. El documento de ciclo registra la fecha desde la cual `caja_masa_kg` va en kilogramos a 2 kg por volt, y que los 429 registros de caja anteriores quedaron en la unidad antigua.
- Si la báscula está en otra configuración, o si los artículos de la escena no corresponden al catálogo, no cambies nada. Registra lo observado y detente en este paso.
- La capa de materiales no depende de este paso, ya que usa la fracción de la señal.

### L. Corridas largas y distribución de masas. ESENCIAL, ESCENA

Antes de correr, escribe en `docs/INSTRUMENTACION_A2.md` las definiciones de lo que este paso mide.

- Dos corridas de `prueba_fio.py cliente --cajas 600`, de unos 48 minutos cada una, con reinicio de escena entre ellas, sin Firebase y con la capa de materiales encendida si M2 ya está cerrado. Cada corrida parte de D igual a cero, en su propio directorio de datos. Copia los eventos del cliente, el archivo del oráculo y los archivos de materiales a `datos/corridas/L1_<fecha>/` y `datos/corridas/L2_<fecha>/`.
- `tools/analiza_masas.py`, nuevo, en Python 3.9 sin dependencias, que a partir de esos archivos reporta:
  1. El histograma de los pesos del cliente y cuántos caen a 0.03 V o menos de cada uno de los niveles 1.5, 2.5, 3.5, 4.0, 5.0, 7.5 y 10.0 V.
  2. Las lecturas fuera de nivel, cada una con el peso que vio el oráculo al soltar la caja y con su variación en los últimos 0.3 s.
  3. Las lecturas de 8.0 V o más, con el mismo detalle, y la fracción de ellas que queda por debajo de 9.95 V.
  4. El valor crudo máximo del registro de peso durante el pesaje de cada caja de 9.0 V o más, para saber si la señal llega a 1000 y si lo rebasa. El oráculo de `prueba_fio.py` hoy guarda en `oraculo.json` el peso al soltar y su variación, por lo que hay que ampliarlo para que guarde también ese máximo, sin cambiar sus criterios.
  5. El reparto por nivel en ventanas de 10 minutos, con el estadístico de homogeneidad, sus grados de libertad y su valor p, dentro de cada corrida y entre corridas. El valor p sale de una implementación propia, comprobada contra tres valores conocidos: 11.24 con 2 grados da 0.0036, 3.841 con 1 grado da 0.050 y 9.488 con 4 grados da 0.050.
  6. La cadencia en cajas por minuto.
  7. Con `tools/materiales.py`, el D que resulta de las lecturas crudas y el que resultaría si cada lectura fuera de nivel se llevara al nivel inmediato superior, junto con el tiempo esperado para llegar a D de 0.5, 0.8 y 1.0. Este segundo cálculo es solo un reporte de sensibilidad y no cambia el modelo.
- El resultado va a `docs/corrida_L.md`, con tablas y sin interpretación.
- Verificación: sobre `datos/a2_planta_eventos.jsonl`, entre `2026-10-25T01:00:00Z` y `2026-10-25T03:00:00Z`, la herramienta reproduce las cifras que calculé por separado el 10 de noviembre. Son 429 cajas. Por nivel, 68 en 1.5 V, 63 en 2.5 V, 66 en 3.5 V, 63 en 4.0 V, 74 en 5.0 V, 44 en 7.5 V y 5 en 10.0 V, con 46 fuera de nivel. Las lecturas de 8.0 V o más son 8.36, 8.37, 8.72, 9.4, 9.4, 9.53, 9.67 y 9.77, más cinco de 10.0. En las dos corridas nuevas, el oráculo de `prueba_fio.py` conserva sus criterios, con cada caja por la salida de su peso y sin desvíos, pérdidas ni fantasmas.
- Este paso no decide nada. La corrección del peso por catálogo, un cambio al pesaje detenido y el valor final de `ciclos_por_paso` los decide Ari con `docs/corrida_L.md` a la vista.

### M3. Capa de materiales contra la escena. ESENCIAL, ESCENA

Este paso no pide tiempo adicional de escena si las corridas de L se hicieron con la capa encendida.

- Para cada corrida de L, compara el archivo de verdad con `tools/materiales.py recalcula` sobre los eventos del cliente.
- `docs/corrida_materiales.md` reporta, por corrida y por laminado: la línea de tiempo de D, los pasos por región, el instante y el número de paso en que se cruzó cada umbral, la relación entre el D de los dos laminados y la sensibilidad del punto 7 del paso L.
- Una captura de la HMI con la tarjeta `Materials layer` durante una corrida, en `docs/img/hmi_materiales.png`.
- Verificación: la verdad coincide con el recálculo con diferencia relativa menor a 10^−9, hay cero pasos `sobre`, D no decrece, y la HMI mostró cada nivel en el paso que predice el recálculo.

## Fuera de esta fase

- La rama `materiales` de Firebase y sus reglas.
- A2-Comandos y cualquier actuación sobre la planta a partir del estado del material o del diagnóstico.
- Cambios al prompt o a la pestaña de diagnóstico, y la evaluación del diagnóstico contra la verdad. Esta fase solo deja lista la separación entre lo medido y la verdad.
- La corrección del peso por catálogo y cualquier cambio al pesaje detenido.
- `httpNodeAuth` y cualquier cambio al túnel.

## Al terminar

Entrega una tabla con cada paso, su commit, su verificación con el resultado y lo que quedó bloqueado, con la puerta que lo bloquea. Di también en qué puntos la orden no coincidió con el código. No afirmes que algo funciona sin la prueba que lo demuestre.

## Anexo A. Contenido de `config/materiales.json`

```json
{
  "version": 1,
  "fuente": "Jen y Huang (2021), Nanomaterials 11(12), 3459, Tablas 1 y 2 y Fig. 9. Ver docs/PARAMETROS_MATERIALES.md",
  "carga": {
    "sigma_ref_MPa": 930.0,
    "R_ref": 0.1,
    "senal_plena_escala_V": 10.0
  },
  "n_tope_ciclos": 1000000,
  "ciclos_por_paso": 2500,
  "umbrales_D": {
    "preventiva": 0.5,
    "critica": 0.8,
    "falla": 1.0
  },
  "galga": {
    "ruido_sd_ue": 25.0,
    "semilla": 20261110
  },
  "laminados": [
    {
      "id": "0:0",
      "pieza": "varilla_00",
      "a_MPa": 1152.0,
      "b": -0.021,
      "sigma_uts_MPa": 1128.0,
      "E0_GPa": 80.96,
      "nivel_min_pct": 75.0,
      "nivel_max_pct": 82.5,
      "rigidez": [[0.00000, 0.0000], [0.00003, 0.0163], [0.00014, 0.0221], [0.00069, 0.0237], [0.00686, 0.0298], [0.06859, 0.0420], [0.13719, 0.0454], [0.17148, 0.0560], [0.20578, 0.0647], [0.27437, 0.0711], [0.34296, 0.0751], [0.41156, 0.0807], [0.48015, 0.0832], [0.54874, 0.0878], [0.61733, 0.0927], [0.68593, 0.0991], [0.75452, 0.1011], [0.82311, 0.1031], [0.89171, 0.1067], [0.96030, 0.1132], [1.00000, 0.1351]]
    },
    {
      "id": "9:1",
      "pieza": "varilla_91",
      "a_MPa": 1159.0,
      "b": -0.014,
      "sigma_uts_MPa": 1486.0,
      "E0_GPa": 93.01,
      "nivel_min_pct": 62.5,
      "nivel_max_pct": 70.0,
      "rigidez": [[0.00000, 0.0000], [0.00002, 0.0025], [0.00004, 0.0055], [0.00009, 0.0075], [0.00088, 0.0095], [0.00881, 0.0124], [0.04405, 0.0169], [0.08810, 0.0169], [0.17619, 0.0169], [0.26429, 0.0191], [0.35239, 0.0238], [0.44049, 0.0256], [0.52858, 0.0287], [0.61668, 0.0309], [0.70478, 0.0335], [0.79287, 0.0367], [0.88097, 0.0399], [0.96907, 0.0413], [1.00000, 0.0439]]
    }
  ]
}
```

Las constantes `a_MPa`, `b`, `sigma_uts_MPa` y `E0_GPa` vienen de las Tablas 1 y 2 de la referencia. El exponente del laminado 0:0 aparece impreso sin signo y se usa negativo, por la razón que explica la sección 4 de `docs/PARAMETROS_MATERIALES.md`. La tabla `rigidez` lleva pares de daño y rigidez perdida, leídos de la Fig. 9.

## Anexo B. Valores de referencia

Estos valores se calcularon el 10 de noviembre de 2026 fuera de este repositorio, por dos caminos que coincidieron con diferencia relativa menor a 10^−9. Son el oráculo del paso M1. Si tu modelo no los reproduce, el error está en el modelo o en la configuración, y no en la tabla. Si crees lo contrario, detente y dilo.

| peso_V | sigma_max (MPa) | 0:0 región | 0:0 N del ajuste | 0:0 N usado | 0:0 ΔD | 9:1 región | 9:1 N del ajuste | 9:1 N usado | 9:1 ΔD |
|---|---|---|---|---|---|---|---|---|---|
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

- Carga constante: 10 pasos de 10.00 V dan D = 0.93501700 en el laminado 0:0 y D = 0.02500000 en el 9:1.
- Secuencia mixta de 10 pasos, en volts: 10.00, 9.77, 9.50, 7.50, 10.00, 9.99, 9.40, 9.00, 8.99, 10.00. Resultado en el laminado 0:0: D = 0.42420258, con 8 pasos dentro del intervalo, 2 por debajo y 0 por encima. Resultado en el 9:1: D = 0.01000000, con 4 dentro, 6 por debajo y 0 por encima.
- Rigidez interpolada d(D) en el laminado 0:0: d(0.0935) = 0.043235, d(0.25) = 0.068826, d(0.5) = 0.084531, d(0.8) = 0.102426, d(0.95) = 0.112224, d(1.0) = 0.135100, d(1.2) = 0.135100.
- Rigidez interpolada d(D) en el laminado 9:1: d(0.025) = 0.014467, d(0.25) = 0.018743, d(0.5) = 0.027694, d(0.8) = 0.036959, d(1.0) = 0.043900, d(1.2) = 0.043900.
- Galga sin ruido, laminado 0:0, 10.00 V: 10338.439 µε con D = 0, 11293.055 µε con D = 0.5, 11518.204 µε con D = 0.8, 11953.334 µε con D = 1.0. Con 7.50 V y D = 0: 7753.829 µε.
- Galga sin ruido, laminado 9:1, 10.00 V: 8999.032 µε con D = 0, 9131.136 µε con D = 0.025.
- Fronteras: el laminado 0:0 entra a su intervalo en 8.9964 V y el 9:1 en 9.9851 V. Con la señal en 10.00 V ningún laminado queda por encima de su intervalo.
