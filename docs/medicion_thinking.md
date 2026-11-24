# ¿Apagar el razonamiento de Gemini degrada el diagnóstico?

## Criterio, fijado ANTES de medir

La primera medición (2026-08-25) comparó `thinkingBudget: 0` contra el
razonamiento encendido sobre **un solo caso, y el más fácil que existe**:
temperatura y vibración muy por encima del umbral, tendencia clara y monótona.
Ahí el razonamiento no tiene nada que aportar, así que apagarlo no podía costar
nada. Medir eso y concluir "apagarlo no degrada" es medir donde no importa.

Esta segunda medición usa tres casos donde sí puede doler. El criterio queda
escrito antes de hacer la primera llamada.

### Casos

| # | Situación | Lo correcto |
|---|---|---|
| A | Vibración subiendo, temperatura plana y normal | atribuir a causa mecánica, **no** inventar problema térmico |
| B | Ambas rozando el umbral sin cruzarlo, con tendencia al alza | decir que **no** ha cruzado, proyectar el cruce, prescribir vigilar |
| C | Datos con ruido y sin tendencia real | decir que la evidencia no alcanza y prescribir seguir midiendo |

### Reglas de decisión

Cada respuesta se juzga contra tres condiciones:

1. **No afirma un cruce de umbral que no ocurrió.**
2. **La acción prescrita corresponde a la severidad real** (nada de "detener la
   máquina" ante una tendencia que aún no cruza).
3. **Cita los números de la entrada**, no genéricos.

**Decisión pre-registrada:** si con el razonamiento apagado falla alguna de las
tres condiciones en algún caso, y con el razonamiento encendido no falla, se
revierte `GEMINI_THINKING_BUDGET` a vacío y se documenta que el ahorro de tokens
costaba calidad. Si las dos configuraciones se comportan igual, se conserva el 0.

Los tres casos usan valores que el pipeline **sí puede producir**: temperatura
dentro de −40..80 °C y vibración dentro de 0..100 mm/s, que son los topes de las
reglas de Firebase y del DHT22.

## Resultado

Medido el 2026-08-25 con `gemini-2.5-flash` y la llave real, vía
`pruebas/mide_thinking.py`.

### Lo primero que apareció no era una diferencia de calidad

Con el razonamiento **encendido** y `maxOutputTokens: 512`, los tres casos
devolvieron JSON truncado y `finishReason: MAX_TOKENS`:

```
razonamiento ENCENDIDO, tope 512   [805 tokens, 488 de pensamiento, MAX_TOKENS]
  diagnostico: {"texto_diagnostico": "La
```

El pensamiento se comió el presupuesto y no quedó nada para la respuesta. Es
exactamente el modo de falla `generacion_incompleta` que maneja
`12_parsea_gemini.js`. Comparar eso contra "apagado" no habría sido una
comparación de calidad, así que se repitió dándole al razonamiento
`maxOutputTokens: 2048`, suficiente para que termine.

### La comparación justa

| Caso | Configuración | Tokens | Veredicto |
|---|---|---:|---|
| A | encendido, tope 512 | 805 | **truncado, inservible** |
| A | encendido, tope 2048 | 1084 | correcto, pero no menciona que la temperatura está normal |
| A | **apagado**, tope 512 | **434** | correcto, y sí señala la temperatura estable |
| B | encendido, tope 512 | 805 | **truncado, inservible** |
| B | encendido, tope 2048 | 1242 | correcto |
| B | **apagado**, tope 512 | **450** | correcto, misma acción prescrita, redacción casi idéntica |
| C | encendido, tope 512 | 805 | **truncado, inservible** |
| C | **apagado**, tope 512 | 408 | correcto: dice que no hay evidencia y prescribe seguir midiendo |

**Hueco declarado:** falta el caso C con el razonamiento encendido y tope 2048.
Las dos llamadas siguientes devolvieron `HTTP 429` — se agotó el límite por
minuto de la cuenta gratuita. Se decidió no seguir gastando cuota, que hace
falta para la grabación. La conclusión se sostiene sobre A y B; C queda medido
solo del lado apagado, donde pasó.

### Contra el criterio pre-registrado

Con el razonamiento apagado, las tres condiciones se cumplen en los tres casos:

1. **Ningún cruce de umbral inventado.** En B dice "acercándose al umbral" y
   "cerca del umbral", que es exactamente lo que ocurre. En C dice "por debajo
   del umbral" para las dos variables.
2. **Acción proporcional.** En A, que sí cruzó, prescribe inspeccionar de
   inmediato. En B, que no cruzó, prescribe monitorear y preparar inspección —
   la misma acción que dio el modelo razonando. En C, seguir midiendo.
3. **Cita los números.** Los tres casos citan valores y umbrales concretos.

En el caso A el diagnóstico sin razonamiento es **mejor** en la tercera
condición: menciona que la temperatura está estable en 58.20 °C por debajo de 75,
observación que la versión razonada omite.

### Decisión

Se conserva `GEMINI_THINKING_BUDGET=0`. No es solo un ahorro del 60 %: con el
tope de 512 tokens, encender el razonamiento **rompe** el diagnóstico en los tres
casos ambiguos. Si alguien quiere razonamiento, tiene que subir
`GEMINI_MAX_TOKENS` a 2048 como mínimo, y eso triplica el consumo sin ganancia
medible de calidad.

Por eso `11_arma_prompt.js` avisa cuando esa combinación está mal puesta.
