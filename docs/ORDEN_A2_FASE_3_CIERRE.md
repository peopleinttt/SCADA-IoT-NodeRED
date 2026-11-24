# Orden para Claude Code. Actividad 2, cierre de la fase 3: tablero, redimensionamiento de la capa de materiales y M3

Fecha: 11 de noviembre de 2026. Esta orden complementa `docs/ORDEN_A2_FASE_3.md` y no la sustituye. Lo que aquí no se menciona sigue como dice esa orden.

## Contexto

Sigues en `~/dev aws/dev/IoT`, en la Mac mini. El último commit es `a946ecf`, con los pasos S2, E1, E2, M1, M2, U y L cerrados. Faltan el paso T y el paso M3. Lee antes de empezar `docs/EVIDENCIA_U0.md`, `docs/corrida_L.md` y la sección L de `docs/CICLO_DESARROLLO_A2.md`.

Las corridas L1 y L2 mostraron que el dimensionamiento con que se abrió la puerta M0 no sirve para lo que se quería medir. La pieza más pesada de la escena pesa 15 kg y marca 7.5 V, por lo que con 10 V como referencia una pieza sola llega a 720.75 MPa y queda por debajo del intervalo ensayado de los dos laminados. Todo el daño salió de lecturas por encima de lo que pesa una pieza sola, que con 8 V o más fueron 16 de 601 en L1 y 9 de 601 en L2, y el resultado de la varilla 0:0 cambió de D = 0.7236 a D = 0.1804 entre dos corridas iguales. Además, en las 18 cajas de 9.0 V o más el registro llegó a 1000 y nunca lo rebasó, lo que indica una señal recortada en plena escala.

## Decisión de dimensionamiento

Ari revisó la puerta M0 el 11 de noviembre de 2026 con `docs/corrida_L.md` a la vista y la deja abierta con estos cambios. Lo que no aparece en la lista queda como estaba.

1. **Referencia de carga.** La pieza más pesada de la escena, de 15 kg y 7.5 V, produce el esfuerzo de referencia de 930 MPa. La clave `senal_plena_escala_V` deja de existir y su lugar lo toma `senal_ref_V`, con valor 7.5, ya que 7.5 V no es la plena escala de la báscula.
2. **Ajuste al nivel.** Una lectura que cae a 0.03 V o menos de un nivel del catálogo de la escena (1.5, 2.5, 3.5, 4.0, 5.0 y 7.5 V) entra al modelo con el valor del nivel. Una lectura que no cae cerca de ningún nivel entra cruda. El motivo es que el tramo común a los intervalos ensayados de los dos laminados mide 1.85 MPa, que equivale a 0.016 V, y la resolución del registro es de 0.01 V.
3. **Ciclos por paso.** `ciclos_por_paso` pasa de 2500 a 350, de modo que una corrida de 600 cajas recorra los tres umbrales en la varilla 0:0. Con los pasos de L1 y L2 el daño llega a 1.0 en los pasos 526 y 499.
4. **Lo que no cambia.** El modelo nunca extrapola, la vida se acota en 10^6 ciclos, los umbrales siguen en 0.5, 0.8 y 1.0, la galga se calcula igual y la separación entre lo medido y la verdad se conserva. La pestaña de diagnóstico no se toca.
5. **Consecuencia aceptada.** Las pesadas con más de una pieza quedan por encima del intervalo ensayado del laminado 0:0. Esos pasos se cuentan, levantan la alerta que ya existe y no cambian D. Con 10 V el esfuerzo es de 1209 MPa, que supera la resistencia a tensión del laminado 0:0 (1128 MPa). El modelo no gana una regla de falla estática en esta orden. El reporte del paso M3 cuenta esos pasos a partir del archivo de verdad.

El ajuste al nivel vive solo dentro de la capa de materiales. La masa que calcula A2-Planta, la clasificación y `caja_masa_kg` no cambian.

## Forma de trabajo

Siguen vigentes las trece reglas de `docs/ORDEN_A2_FASE_3.md`. Las que más pesan aquí son estas.

1. Nada escribe en `planta_01`, `A2_NUBE` sigue en 0 y no hay consultas reales a Gemini.
2. No intentes reanudar la máquina virtual ni tocar Parallels.
3. Ningún valor de referencia se ajusta para que una prueba pase. Los valores salen del Anexo A y los resultados esperados, del Anexo B. Si un resultado no coincide con el Anexo B, detente en ese paso, deja la salida completa en el documento de ciclo y dilo en tu reporte.
4. Un commit por paso, con el prefijo `F3`. La batería completa pasa al cerrar cada paso.
5. El orden es T, R y M3. El paso T va primero porque necesita a Ari presente. Si la puerta T0 no se abre en ese momento, sigue con R y M3 y deja T al final.
6. Esta orden se escribió leyendo el código, sin ejecutarlo. Si un dato de la orden no coincide con el código, vale el código. Anótalo en el documento de ciclo y dilo en tu reporte.

## Puertas de Ari

| Puerta | Estado | Qué desbloquea |
|---|---|---|
| V0 | Abierta desde el 11 de noviembre | Los pasos T y M3 |
| M0 revisada | Abierta con esta orden | Los pasos R y M3 |
| T0 | Cerrada hasta que Ari presione los botones cuando la prueba lo pida | El paso T |

## Pasos

### T. Tablero en la escena real

Queda como en `docs/ORDEN_A2_FASE_3.md`. Con la escena en Play, corre `/usr/bin/python3 pruebas/prueba_fio.py tablero -s 180` y avisa a Ari cuando la prueba diga que está vigilando. Ari presiona, en este orden, Start, Stop, Start, Emergency stop sostenido unos segundos, suelta Emergency stop, Start y Stop. Tu nota del documento de ciclo indica que ese modo vigila al menos 600 s, por lo que Ari tiene ese margen.

- Verificación: todas las comprobaciones de ese modo pasan. Con eso, `config/mapa_registros_fio.json` y `docs/MAPA_REGISTROS.md` dejan de decir que Stop y Emergency stop solo se conocen por su reposo.
- Si una comprobación falla, no corrijas el cliente para que pase. Registra la salida completa y detente en este paso.

### R. Redimensionamiento de la capa de materiales

Este paso no usa la escena.

- `config/materiales.json` queda como el Anexo A, con `version` 2.
- `node-red/funciones/39_mat_modelo.js` y `tools/materiales.py` hacen la misma cuenta, con estos cambios y ninguno más:
  1. `carga` tiene las claves `sigma_ref_MPa`, `R_ref` y `senal_ref_V`. Una configuración con `senal_plena_escala_V`, o con `version` distinta de 2, se rechaza en `valida` con un error que lo diga.
  2. `ajuste_nivel` tiene `niveles_V`, que es una lista de números positivos en orden creciente y puede estar vacía, y `tolerancia_V`, que es un número mayor o igual a cero y menor que la mitad de la separación mínima entre niveles. `valida` rechaza lo que no cumpla.
  3. El peso que entra al modelo es `peso_modelo_V`. La comparación se hace en centésimas de volt enteras, ya que esa es la resolución del registro. Con `c(x) = floor(x × 100 + 0.5)`, si el valor absoluto de `c(peso_V) − c(nivel)` es menor o igual a `c(tolerancia_V)`, `peso_modelo_V` es el nivel. En otro caso `peso_modelo_V` es `peso_V`. Se usa `floor(x + 0.5)` y no el redondeo de cada lenguaje para que JS y Python den lo mismo.
  4. `f = peso_modelo_V / senal_ref_V`. Lo demás de la cuenta no cambia. `f` puede ser mayor que 1.
  5. El resultado de cada paso gana `peso_V`, `peso_modelo_V` y `ajustado`, que es verdadero cuando el ajuste cambió el valor.
  6. El estado gana `cfg_version`. Un archivo de estado con otra versión de configuración no se continúa: la pestaña no acumula y lo reporta, igual que con un archivo de estado dañado.
- El archivo de verdad guarda por paso `peso_V`, `peso_modelo_V` y `ajustado`. El archivo de lo medido no gana campos.
- La tarjeta de la HMI no cambia.
- Las pruebas del modelo y del flujo pasan a la configuración versión 2. Los valores esperados del Anexo B de `docs/ORDEN_A2_FASE_3.md` dejan de aplicar y los sustituye el Anexo B de esta orden. Conserva las pruebas de mutación.
- `docs/PARAMETROS_MATERIALES.md` no se reescribe. Agrega una nota fechada al inicio de sus secciones 8 y 9 que diga que el dimensionamiento y la lectura de los pesos altos cambiaron el 11 de noviembre de 2026 y que remita a `docs/EVIDENCIA_U0.md` y a esta orden.
- Verificación:
  1. `valida` acepta el Anexo A y rechaza la configuración del commit `a946ecf`, una con `tolerancia_V` de 0.3 y una con niveles en desorden.
  2. La implementación en JS y la de Python reproducen la tabla del Anexo B, con N con diferencia relativa menor a 10^−9 y ΔD con ocho decimales.
  3. Las dos reproducen las secuencias del Anexo B, con D con ocho decimales y conteos exactos.
  4. Las dos reproducen la galga sin ruido del Anexo B con diferencia menor a 0.001 µε.
  5. Un estado con `cfg_version` 1 bloquea la acumulación y la tarjeta lo dice.
  6. El archivo de lo medido sigue sin traer ningún campo de la verdad, incluidos `peso_modelo_V` y `ajustado`.
  7. Batería completa con 0 fallidas y `pruebas/prueba.sh` en 26 de 26.

### M3. Capa de materiales contra la escena, con la configuración versión 2

- **Recálculo de L1 y L2.** Con `tools/materiales.py` y la configuración versión 2, recalcula las dos corridas a partir de los `paso_caja` de `datos/corridas/L1_2026-11-11` y `datos/corridas/L2_2026-11-11`. No vuelvas a correr L1 ni L2.
- **Corrida en vivo.** Una corrida de `prueba_fio.py cliente --cajas 600 --materiales`, lanzada con `caffeinate -d`, sin Firebase, con reinicio de escena al empezar y con D igual a cero. Copia sus archivos a `datos/corridas/M1_<fecha>/`, igual que en el paso L.
- **Captura.** `docs/img/hmi_materiales.png`, con la tarjeta `Materials layer` durante la corrida en vivo, tomada después de que la varilla 0:0 cruce D = 0.5.
- **Reporte.** `docs/corrida_materiales.md`, con tablas y sin interpretación, que da por corrida (L1 y L2 recalculadas, M1 en vivo) y por laminado:
  1. D final, pasos dentro, por debajo y por encima del intervalo, y número de lecturas que el ajuste cambió.
  2. La línea de tiempo de D cada 50 pasos.
  3. El paso, la caja y el instante en que se cruzó cada umbral.
  4. La relación entre el D final de los dos laminados.
  5. El aporte a D de los pasos con `peso_modelo_V` de 7.5 V y el aporte de los demás pasos.
  6. El número de pasos con esfuerzo máximo mayor o igual a la resistencia a tensión del laminado, tomado de `sigma_max_MPa` y de `sigma_uts_MPa`.
  7. Para L1 y L2, el D que dio la configuración versión 1 sobre los mismos pasos, tomado de `docs/corrida_L.md`.
- Verificación:
  1. El recálculo de L1 y L2 reproduce la tercera parte del Anexo B, con D con ocho decimales y con conteos y pasos de cruce exactos.
  2. En M1, la verdad coincide con el recálculo con diferencia relativa menor a 10^−9, D no decrece y los pasos por encima del intervalo no cambian D.
  3. En M1, la HMI mostró cada nivel en el paso que predice el recálculo.
  4. En M1, el oráculo de `prueba_fio.py` conserva sus criterios, con cada caja por la salida de su peso y sin desvíos, pérdidas ni fantasmas.
  5. Batería completa con 0 fallidas.

## Fuera de esta orden

- Una regla de falla estática en el modelo. Los pasos por encima de la resistencia solo se cuentan en el reporte.
- La rama `materiales` de Firebase, A2-Comandos y cualquier cambio a la pestaña o al prompt de diagnóstico.
- Cambios al pesaje detenido, a la masa de A2-Planta o a `caja_masa_kg`.
- La carrera de `pruebas/prueba_grafica.py` que anotaste en el paso U.

## Al terminar

Actualiza la tabla de estado de la fase 3 en `docs/CICLO_DESARROLLO_A2.md` y la lista de puntos en que una orden no coincidió con el código. Tu reporte dice, por paso, qué commit lo cierra, la salida de su verificación y lo que quedó pendiente. No abras ninguna puerta por tu cuenta.

## Anexo A. `config/materiales.json`, versión 2

```json
{
  "version": 2,
  "fuente": "Jen y Huang (2021), Nanomaterials 11(12), 3459, Tablas 1 y 2 y Fig. 9. Ver docs/PARAMETROS_MATERIALES.md. Dimensionamiento del 11 nov 2026: docs/EVIDENCIA_U0.md, docs/corrida_L.md y docs/ORDEN_A2_FASE_3_CIERRE.md",
  "carga": {
    "sigma_ref_MPa": 930.0,
    "R_ref": 0.1,
    "senal_ref_V": 7.5
  },
  "ajuste_nivel": {
    "niveles_V": [1.5, 2.5, 3.5, 4.0, 5.0, 7.5],
    "tolerancia_V": 0.03
  },
  "n_tope_ciclos": 1000000,
  "ciclos_por_paso": 350,
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

Los parámetros de los laminados y las tablas de rigidez son los mismos de la versión 1. Cambian `version`, `fuente`, `carga`, `ciclos_por_paso` y la clave nueva `ajuste_nivel`.

## Anexo B. Valores de referencia

Los calculé por tres caminos independientes, que son Python con coma flotante, mpmath con 50 dígitos y Node, y los tres coinciden en todas las cifras que aparecen aquí.

### Primera parte. Un paso

El esfuerzo mínimo es 93.0000 MPa en todos los casos.

| peso_V | peso_modelo_V | ajustado | sigma_max (MPa) | 0:0 región | 0:0 N del ajuste | 0:0 N usado | 0:0 ΔD | 9:1 región | 9:1 N del ajuste | 9:1 N usado | 9:1 ΔD |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 7.50 | 7.50 | no | 930.0000 | dentro | 26737.4818 | 26737.4818 | 0.01309024 | dentro | 6739167.3880 | 1000000.0000 | 0.00035000 |
| 7.49 | 7.50 | sí | 930.0000 | dentro | 26737.4818 | 26737.4818 | 0.01309024 | dentro | 6739167.3880 | 1000000.0000 | 0.00035000 |
| 7.47 | 7.50 | sí | 930.0000 | dentro | 26737.4818 | 26737.4818 | 0.01309024 | dentro | 6739167.3880 | 1000000.0000 | 0.00035000 |
| 7.53 | 7.50 | sí | 930.0000 | dentro | 26737.4818 | 26737.4818 | 0.01309024 | dentro | 6739167.3880 | 1000000.0000 | 0.00035000 |
| 7.46 | 7.46 | no | 925.5360 | dentro | 33622.2535 | 33622.2535 | 0.01040977 | bajo |  |  | 0 |
| 7.54 | 7.54 | no | 934.4640 | sobre |  |  | 0 | dentro | 4786978.7674 | 1000000.0000 | 0.00035000 |
| 6.75 | 6.75 | no | 846.3000 | dentro | 2385230.7033 | 1000000.0000 | 0.00035000 | bajo |  |  | 0 |
| 6.74 | 6.74 | no | 845.1840 | bajo |  |  | 0 | bajo |  |  | 0 |
| 5.00 | 5.00 | no | 651.0000 | bajo |  |  | 0 | bajo |  |  | 0 |
| 4.97 | 5.00 | sí | 651.0000 | bajo |  |  | 0 | bajo |  |  | 0 |
| 5.04 | 5.04 | no | 655.4640 | bajo |  |  | 0 | bajo |  |  | 0 |
| 8.36 | 8.36 | no | 1025.9760 | sobre |  |  | 0 | dentro | 6051.6510 | 6051.6510 | 0.05783546 |
| 8.48 | 8.48 | no | 1039.3680 | sobre |  |  | 0 | dentro | 2396.5040 | 2396.5040 | 0.14604607 |
| 8.49 | 8.49 | no | 1040.4840 | sobre |  |  | 0 | sobre |  |  | 0 |
| 9.27 | 9.27 | no | 1127.5320 | sobre |  |  | 0 | sobre |  |  | 0 |
| 9.28 | 9.28 | no | 1128.6480 | sobre |  |  | 0 | sobre |  |  | 0 |
| 10.00 | 10.00 | no | 1209.0000 | sobre |  |  | 0 | sobre |  |  | 0 |

- Fronteras en volts de `peso_modelo_V`. El laminado 0:0 está dentro de su intervalo entre 6.7473 y 7.5054 V, y el 9:1 entre 7.4888 y 8.4875 V. El esfuerzo iguala la resistencia a tensión del laminado 0:0 en 9.2742 V y la del 9:1 en 12.4821 V, valor que la señal no alcanza.
- Con 10.00 V el esfuerzo máximo es 1209.0000 MPa.
- Galga sin ruido, laminado 0:0, con `peso_modelo_V` de 7.50 V: 10338.439 µε con D = 0, 11293.055 µε con D = 0.5, 11518.204 µε con D = 0.8 y 11953.334 µε con D = 1.0. Con 5.00 V y D = 0: 6892.292 µε. Con 10.00 V y D = 0: 13784.585 µε.
- Galga sin ruido, laminado 9:1, con `peso_modelo_V` de 7.50 V: 8999.032 µε con D = 0, 9255.352 µε con D = 0.5, 9344.392 µε con D = 0.8 y 9412.229 µε con D = 1.0. Con 10.00 V y D = 0: 11998.710 µε.

### Segunda parte. Secuencias

- Carga constante: 77 pasos de 7.50 V dan D = 1.00794833 en el laminado 0:0 y D = 0.02695000 en el 9:1. El laminado 0:0 cruza 0.5 en el paso 39, 0.8 en el paso 62 y 1.0 en el paso 77.
- Secuencia mixta de 15 pasos, en volts: 7.50, 7.49, 7.47, 7.46, 7.53, 7.54, 5.00, 6.75, 6.74, 8.36, 8.48, 8.49, 9.29, 10.00, 7.50. En el laminado 0:0: D = 0.07621096, con 7 pasos dentro del intervalo, 2 por debajo y 6 por encima. En el 9:1: D = 0.20598153, con 8 dentro, 4 por debajo y 3 por encima. El ajuste cambia 3 de las 15 lecturas.

### Tercera parte. Recálculo de L1 y L2 con la versión 2

Calculado sobre los `paso_caja` de cada corrida, con Python y con Node por separado.

| Corrida | Laminado | D final | Dentro | Por debajo | Por encima | Cruza 0.5 | Cruza 0.8 | Cruza 1.0 | Pasos con esfuerzo ≥ resistencia |
|---|---|---|---|---|---|---|---|---|---|
| L1 | 0:0 | 1.14730757 | 91 | 490 | 20 | paso 250 | paso 413 | paso 526 | 9 |
| L1 | 9:1 | 0.09261109 | 92 | 494 | 15 | no cruza | no cruza | no cruza | 0 |
| L2 | 0:0 | 1.18322756 | 93 | 496 | 12 | paso 248 | paso 405 | paso 499 | 4 |
| L2 | 9:1 | 0.03262895 | 93 | 499 | 9 | no cruza | no cruza | no cruza | 0 |

El ajuste cambia 269 lecturas de 601 en L1 y 265 de 601 en L2. En las dos corridas el número de paso coincide con el número de caja.
