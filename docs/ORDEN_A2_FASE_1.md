# Orden para Claude Code. Actividad 2, fase 1: orquestación contra planta simulada

Fecha: 22 de octubre de 2026. Entrega de la actividad: enlace a un video, 25 de octubre de 2026 a las 23:59.

## Contexto

Trabajas en `~/dev aws/dev/IoT` en la Mac mini, que es el repositorio de la Actividad 1 de la estancia Digital Twins for Manufacturing with IoT and AI, migrado desde la MacBook el 4 de octubre de 2026 con un solo commit. La ruta lleva un espacio en `dev aws`, por lo que todo script debe citar las rutas entre comillas.

Antes de tocar nada, lee `README.md`, `docs/BITACORA.md`, `docs/PASO_A_PASO.md`, `docs/INSTRUMENTACION.md`, `docs/ERRORES.md`, `pruebas/README.md`, `node-red/construye_flows.py`, `node-red/funciones/`, `firebase/`, `arranca.sh`, `enciende.sh` y `tunel.sh`. La meta es reutilizar el generador de flujos, la autenticación, las reglas, los arneses de prueba y los scripts de medición.

La Actividad 2 integra una planta virtual de Factory I/O con Node-RED por Modbus TCP, junto con la cadena IoT de la Actividad 1. Factory I/O va a correr en una máquina con Windows en Azure, con el driver Modbus TCP/IP Server, alcanzable por Tailscale. Esa máquina todavía no está lista, por lo que esta fase construye todo contra una planta simulada en esta Mac, con el mismo mapa de registros.

## Reglas

1. Un paso a la vez. No arranques un paso hasta que el anterior pase su verificación, y muéstrame la salida de las pruebas al cerrar cada uno.
2. Mantén `docs/CICLO_DESARROLLO_A2.md` con el estado de cada paso, las pruebas que lo respaldan, las decisiones tomadas durante la implementación y lo pendiente.
3. No edites `node-red/flows.json` a mano. Las pestañas nuevas se generan con `node-red/construye_flows.py`, a partir de funciones en archivos separados.
4. Ninguna credencial entra al repositorio. Host, puerto y unidad Modbus van por variables de entorno en `.env`, y `.env.example` se actualiza con los nombres nuevos sin valores.
5. No modifiques el comportamiento de las pestañas de la Actividad 1. Las de la Actividad 2 llevan el prefijo A2, y los arneses de la Actividad 1 deben seguir pasando después de cada paso.
6. Haz un commit al cerrar cada paso, después de mostrar sus pruebas.
7. En este paso no gastes cuota de Gemini ni escribas en la base real, salvo en las verificaciones que lo pidan de forma explícita.

## Entorno detectado en la Mac mini el 23 de octubre de 2026

- Node.js v22.23.3 y npm en `/opt/homebrew/opt/node@22/bin`.
- `node-red` no está instalado. `firebase-tools` no está instalado.
- Java 21 disponible, por lo que el emulador de Firebase puede correr.
- `python3` es el del sistema, versión 3.9.6. Todo script de Python nuevo debe ser compatible con 3.9. `pymodbus` no está instalado.
- `cloudflared` está en `/opt/homebrew/bin`, pero `tunel.sh` espera `bin/cloudflared`, que no existe.
- No existen `bin/`, `datos/` ni `node-red/runtime/`, lo cual es normal porque están en `.gitignore`.
- Tailscale.app está instalada, pero su comando no está en el PATH.

## Datos fijos

- Driver de Factory I/O: Modbus TCP/IP Server, puerto 502, factor de escala 100. Los valores flotantes viajan multiplicados por 100. Límites del driver: 256 puntos digitales y 64 registros por tipo.
- La consigna de velocidad es un entero con signo de 16 bits en complemento a dos. El intervalo de menos 1000 a 1000 equivale a menos 10 a 10 V.
- Node-RED sigue en el puerto 1881 con el `userDir` de `node-red/runtime`, como en la Actividad 1.
- El mapa es provisional. Los nombres reales de las etiquetas de la escena se confirman después, por lo que el mapa vive en un solo archivo de configuración y cambiarlo no debe tocar código.

| Dirección | Etiqueta | Sentido | Tipo | Rango en el registro | Significado |
|---|---|---|---|---|---|
| Entrada discreta 0 | sens_entrada | lectura | bool | | Caja a la entrada del tramo vigilado |
| Entrada discreta 1 | sens_bascula | lectura | bool | | Caja sobre la báscula |
| Entrada discreta 2 | sens_salida | lectura | bool | | Caja a la salida del tramo vigilado |
| Entrada discreta 3 | emp_lim_frontal | lectura | bool | | Empujador extendido |
| Entrada discreta 4 | emp_lim_trasero | lectura | bool | | Empujador retraído |
| Registro de entrada 0 | peso_V | lectura | uint16 | 0 a 1000 | 0 a 10 V, peso en la báscula |
| Bobina 0 | emisor_on | escritura | bool | | Emisor de cajas habilitado |
| Bobina 1 | alimentacion_on | escritura | bool | | Banda de alimentación y báscula en marcha |
| Bobina 2 | emp_extender | escritura | bool | | Extensión del empujador de rechazo |
| Bobina 3 | luz_alerta | escritura | bool | | Indicador de alerta |
| Registro de retención 0 | vel_banda_V | escritura | int16 | menos 1000 a 1000 | menos 10 a 10 V, velocidad del tramo vigilado |

## Pasos

### C0. Entorno de la Mac mini

- Herramientas: npm, Homebrew, los arneses de `pruebas/`.
- Trabajo: instalar `node-red` y `firebase-tools` de forma global, como los usó la Actividad 1. Hacer que `tunel.sh` use el `cloudflared` del PATH cuando falte `bin/cloudflared`, con el cambio mínimo y documentado. Crear `prepara_a2.sh`, que instala de forma reproducible las paletas `node-red-contrib-modbus` y `@flowfuse/node-red-dashboard` en `node-red/runtime` y en el `userDir` temporal que usa `pruebas/prueba.sh`, ya que ambos directorios quedan fuera de git.
- Objetivo: que la Actividad 1 corra en esta máquina igual que en la MacBook antes de agregar nada.
- Verificación: `pruebas/prueba.sh` contra `pruebas/simulador.py` pasa todos sus casos, las pruebas del emulador de reglas corren, `./arranca.sh` levanta Node-RED en el 1881 con las dos pestañas de la Actividad 1, y `./estado.sh` muestra su salida. Muéstrame el conteo de casos de cada arnés.

### C1. Contrato de registros

- Herramientas: Node.js o Python 3.9.
- Trabajo: `config/mapa_registros_a2.json` como fuente única, con nombre, tabla Modbus, dirección, tipo, escala, unidad, rango físico, sentido y descripción por etiqueta. Un validador y un generador de `docs/MAPA_REGISTROS.md`.
- Objetivo: que el cliente, el simulador y la documentación salgan del mismo archivo.
- Verificación: el validador rechaza una dirección repetida en la misma tabla, una dirección fuera de los límites del driver y una escala que desborda el tipo, con un caso de prueba para cada rechazo.

### C2. Planta simulada

- Herramientas: Node-RED, node-red-contrib-modbus con su nodo Modbus-Server.
- Trabajo: pestaña A2-Sustituto con el servidor Modbus cargado desde el mapa y un emulador de la estación. El emulador genera cajas con masa de una distribución configurable y semilla fija, las mueve según `vel_banda_V` con una constante de calibración provisional, activa los sensores en el orden entrada, báscula y salida, publica el peso en el registro de entrada mientras la caja está en la báscula y responde a `emp_extender` con los límites del empujador. Puerto configurable, 5020 por omisión. Una bandera de configuración lo apaga cuando el cliente apunta a Factory I/O.
- Objetivo: desarrollar y probar sin Windows.
- Verificación: dos corridas de 10 minutos con la misma semilla producen la misma secuencia de eventos, y `pruebas/prueba.sh` sigue pasando con la pestaña nueva cargada.

### C3. Sonda Modbus

- Herramientas: Node.js o Python 3.9.
- Trabajo: script de línea de comandos que lee o escribe una etiqueta del mapa por su nombre, contra el host y el puerto que se le indiquen.
- Objetivo: comprobar la conexión con Factory I/O en Azure en cuanto exista, sin Node-RED de por medio.
- Verificación: contra el simulador lee y escribe cada etiqueta con el valor esperado, incluido un valor negativo en `vel_banda_V`.

### C4. A2-Planta

- Herramientas: Node-RED, cliente de node-red-contrib-modbus.
- Trabajo: sondeo por bloque de direcciones, no por etiqueta, con periodo configurable y valor inicial de 250 ms. Marcha y paro desde la interfaz, habilitación del emisor, pesado al activarse `sens_bascula` reteniendo el valor una vez estable, clasificación por una tolerancia de peso configurable con rechazo por empujador y confirmación por límites, y cola FIFO de cajas entre `sens_entrada` y `sens_salida`. Cada caja que sale del tramo emite un evento `paso_caja` con masa, instante de entrada e instante de salida.
- Estado seguro: si se pierde la conexión, la línea queda marcada sin comunicación. Al reconectar se escribe primero `vel_banda_V` en cero y `emisor_on` en falso, y solo después se reanuda.
- Verificación: contra el simulador, 200 cajas sin pérdida ni duplicado en la cola, rechazos coincidentes con la tolerancia y estado seguro tras una desconexión forzada.

### C5. A2-Nube y reglas

- Herramientas: Node-RED, Firebase y su emulador.
- Trabajo: rama `/plantas/{plantaId}/proceso/{registroId}` con `ts_origen` (instante de la lectura Modbus en Node-RED), `ts_escritura`, `vel_banda_V`, `peso_V`, `caja_masa_kg`, `cajas_acumuladas` y `estado_linea`. Escritura por POST con las cuatro propiedades de reglas de la Actividad 1: sin escritura anónima, solo la cuenta del ingestor en su planta, solo adición y esquema validado en el servidor. Un registro por caja más un latido periódico configurable, sin saturar la base. Las reglas extendidas se generan con `firebase/prepara.sh` o su equivalente, y publicarlas en la consola es tarea de Ari: dile exactamente qué archivo publicar.
- Verificación: pruebas de reglas en el emulador, y después de que Ari publique, contra la base real sobre `planta_99`, como en la Actividad 1. Registros aceptados con código 201 en una corrida contra el simulador.

### C6. A2-HMI con Dashboard 2.0

- Herramientas: `@flowfuse/node-red-dashboard`.
- Trabajo: página de operación con marcha y paro, consigna manual de velocidad acotada, contador de cajas, peso de la última caja, cajas rechazadas, estado de comunicación con la planta, último diagnóstico, y un panel con la última telemetría del ESP32 de la Actividad 1 cuando esa cadena esté corriendo.
- Verificación: la página abre desde otro dispositivo de la misma tailnet y sus controles mueven el simulador.

### C7. A2-Diagnóstico

- Herramientas: Node-RED, API de Gemini.
- Trabajo: sobre la pestaña de Gemini de la Actividad 1. El prompt recibe el estado de la planta (cadencia, pesos, rechazos, velocidad y tiempo en marcha) y la telemetría del ESP32 si está disponible. La salida es JSON con `texto_diagnostico`, `nivel_estimado` en {normal, preventiva, critica}, `accion_codigo` en {mantener, reducir_velocidad, detener_y_programar_mantenimiento}, `valor_pct` entero de 0 a 30 solo para `reducir_velocidad`, y `justificacion`. Validación estricta, en donde lo que no cumple se registra como fallo y no llega a la interfaz. Se respetan los frenos de cuota que ya existen en `.env` y los hallazgos 3.2 y 3.3 de `docs/BITACORA.md`. Disparo bajo demanda desde la interfaz más uno periódico largo.
- Verificación: contra `pruebas/simulador.py`, respuestas simuladas válidas e inválidas, ninguna inválida llega a la interfaz, y el conteo diario se respeta. Una sola consulta real al final, para confirmar el formato.

### C8. Gráfica

- Herramientas: Google Charts y el listener de Firebase de `web/index.html`.
- Trabajo: página web para la rama `proceso` con la masa por caja y las cajas por minuto, servida igual que la de la Actividad 1.
- Verificación: la gráfica se actualiza sin recargar durante una corrida contra el simulador.

### C9. Corrida instrumentada contra el simulador

- Herramientas: `tools/exporta_corrida.py` y `tools/analiza_corrida.py` extendidos a la rama `proceso`.
- Trabajo: definiciones escritas antes de medir en `docs/INSTRUMENTACION_A2.md` para el periodo efectivo del sondeo y su variación, la latencia de la lectura a la escritura en Firebase y la completitud de cajas.
- Verificación: corrida de 10 minutos con las tres cifras reproducibles desde el CSV.

## Fuera de esta fase

La capa de materiales (A2-Materiales) y la compuerta de comandos con aprobación (A2-Comandos) no entran ahora. La conexión con Factory I/O real se hace cuando Ari confirme que la máquina de Azure responde, y para eso solo debe cambiar la configuración, no el código.

## Al cerrar cada paso

Indica qué archivos cambiaste, qué pruebas corriste con su salida y qué queda pendiente. No afirmes que algo funciona sin la prueba que lo demuestre.
