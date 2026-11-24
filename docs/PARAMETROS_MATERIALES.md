# Parámetros de la capa de materiales y su origen

Fecha: 10 de noviembre de 2026. Elaborado en Cowork para la fase 3 de la Actividad 2. Este documento es la fuente única de los valores que usa `config/materiales.json`. Ningún valor de la capa de materiales se toma de otro lugar ni se estima de memoria.

## 1. Fuente y forma de extracción

La referencia es Jen, Y.-M., y Huang, Y.-C. (2021). Improvement in tensile quasi-static and fatigue properties of carbon fiber-reinforced epoxy laminates with matrices modified by carbon nanotubes and graphene nanoplatelets hybrid nanofillers. *Nanomaterials*, 11(12), 3459. https://doi.org/10.3390/nano11123459. El artículo es de acceso abierto.

Las Tablas 1, 2 y 3 se leyeron el 10 de noviembre de 2026 del texto de la página del editor (https://www.mdpi.com/2079-4991/11/12/3459), celda por celda, ya que en esa página las tablas son texto y no imagen. La Fig. 9 solo existe como imagen, por lo que sus curvas se digitalizaron por color sobre la imagen original de 1812 por 1398 pixeles, con los ejes calibrados contra el marco de la gráfica. La calibración se comprobó con un dato independiente, ya que la curva del laminado 9:1 termina en el pixel que corresponde a 117786 ciclos y su leyenda indica una vida de 113511 ciclos, una diferencia de 4 pixeles que equivale al grosor de la línea. Por ende, los valores de las tablas son exactos respecto a la fuente y los de la Fig. 9 son lecturas con una incertidumbre de alrededor de 0.001 en la degradación.

## 2. Materiales y condiciones de ensayo

El laminado es de fibra de carbono unidireccional 12 k (Formosa Taffeta, 216 g/m² y 0.28 mm por capa) con matriz epóxica EPO-622, apilado (0)4 para las probetas estáticas y de fatiga, con fracción volumétrica de fibra de 45 %. Los nanorrellenos son nanotubos de carbono de pared múltiple NC7000 (Nanocyl) y nanoplaquetas de grafeno KNG-150 (Knano), con un contenido total de 0.25 % en peso respecto a la resina epóxica, en seis relaciones MWCNT:GNP, que son 0:0, 10:0, 0:10, 5:5, 9:1 y 1:9.

Los ensayos estáticos siguieron ASTM D3039 con control de desplazamiento a 2 mm/min. Los ensayos de fatiga siguieron ASTM D3479 con control de carga, onda senoidal de 10 Hz y relación de esfuerzos R = 0.1, en donde R es el esfuerzo mínimo entre el esfuerzo máximo del ciclo. El nivel de carga r se define como el esfuerzo máximo entre la resistencia última estática. El ensayo se interrumpió al superar 10^6 ciclos y esa probeta se consideró de vida infinita. Con base en estas condiciones, los parámetros de fatiga de la referencia solo son válidos para ciclos de tensión con R cercano a 0.1.

## 3. Propiedades estáticas (Tabla 1 de la referencia)

| MWCNT:GNP | Módulo E (GPa) | Resistencia σ_uts (MPa) | Deformación a la falla (%) |
|---|---|---|---|
| 0:0 (epóxico sin modificar) | 80.96 ± 0.43 | 1128 ± 58 | 1.31 ± 0.02 |
| 10:0 | 75.05 ± 0.97 | 1157 ± 104 | 1.39 ± 0.04 |
| 0:10 | 86.67 ± 0.77 | 1250 ± 108 | 1.28 ± 0.23 |
| 5:5 | 81.09 ± 3.22 | 1296 ± 136 | 1.44 ± 0.10 |
| 9:1 | 93.01 ± 1.43 | 1486 ± 25 | 1.46 ± 0.02 |
| 1:9 | 88.86 ± 1.55 | 1319 ± 56 | 1.41 ± 0.16 |

El laminado 9:1 supera al laminado sin modificar en 14.9 % de módulo y en 31.7 % de resistencia, cifras que coinciden con las que el texto del artículo declara, por lo que la transcripción de la tabla queda comprobada contra el propio artículo.

## 4. Fatiga (Tabla 2 de la referencia)

La referencia ajusta la ley de potencia σ_max = a · N_f^b a los datos de cada laminado, con σ_max en MPa.

| MWCNT:GNP | Niveles r (%) | Vidas N_f (ciclos), tres por nivel | a | b | R² |
|---|---|---|---|---|---|
| 0:0 | 75, 77.5, 80, 82.5 | 890023, 1000000, 1000000. 585644, 656983, 579416. 145788, 207800, 353534. 26145, 11980, 20593 | 1152 | 0.021 impreso, se usa −0.021 | 0.86 |
| 10:0 | 72.5, 75, 77.5, 80 | 1000000 tres veces. 547691, 367158, 431649. 398070, 181435, 225663. 74476, 47396, 75509 | 1358 | −0.034 | 0.92 |
| 0:10 | 62.5, 65, 67.5, 70 | 1000000 tres veces. 649877, 716640, 642066. 136197, 127407, 177407. 9939, 10689, 7606 | 1073 | −0.021 | 0.88 |
| 5:5 | 72.5, 75, 77.5, 80 | 1000000, 1000000, 819407. 160943, 189778, 241175. 13605, 11602, 25091. 1106, 6440, 3487 | 1174 | −0.016 | 0.96 |
| 9:1 | 62.5, 65, 67.5, 70 | 1000000, 1000000, 849793. 609748, 714277, 686646. 168684, 113511, 167219. 829, 1718, 1415 | 1159 | −0.014 | 0.80 |
| 1:9 | 70, 72.5, 75, 77.5 | 1000000 tres veces. 119721, 133696, 140635. 31506, 19159, 47737. 2561, 3188, 4670 | 1185 | −0.018 | 0.98 |

Cuatro observaciones acompañan a esta tabla.

1. **Signo del exponente del laminado sin modificar.** La tabla imprime b = 0.021 sin signo para el laminado 0:0, mientras que los otros cinco exponentes son negativos. Un exponente positivo implicaría que la resistencia crece con la vida. El reajuste de los doce datos de esa misma fila da b = −0.0213, por lo que el signo faltante es una errata y se usa b = −0.021.
2. **Comprobación de las seis filas.** El ajuste por mínimos cuadrados de log σ_max contra log N_f, con las probetas interrumpidas contadas en 10^6 ciclos, reproduce las constantes impresas de los seis laminados. Los valores recalculados son a = 1153.3 y b = −0.0213 (0:0), 1359.6 y −0.0344 (10:0), 1073.8 y −0.0216 (0:10), 1173.9 y −0.0159 (5:5), 1160.0 y −0.0143 (9:1), y 1184.9 y −0.0180 (1:9), con R² de 0.855, 0.920, 0.884, 0.958, 0.801 y 0.982. Esto confirma la transcripción y revela cómo se trataron las probetas interrumpidas.
3. **Errata de separador.** En la fila 0:10 la tabla imprime "64,2066", que se toma como 642066.
4. **Diferencia entre el texto y la tabla.** El texto del artículo habla de cinco niveles de carga entre 60 y 85 % y de dos repeticiones, mientras que la tabla lista cuatro niveles y tres vidas por nivel. Se usan los datos de la tabla.

La capa de materiales usa las constantes impresas, con el signo corregido, ya que son las que un lector puede rastrear hasta la fuente. Por ende, la ley de vida de cada laminado queda definida por dos constantes publicadas y comprobadas contra sus propios datos.

## 5. Intervalo ensayado y calidad del ajuste

La ley de potencia solo está respaldada dentro del intervalo de esfuerzo que se ensayó, que resulta de multiplicar los niveles extremos por la resistencia de cada laminado.

| Laminado | Intervalo ensayado de σ_max (MPa) | Esfuerzo en que el ajuste da 10^6 ciclos (MPa) | Resistencia a fatiga del ajuste a 10^4, 10^5 y 10^6 ciclos (MPa) |
|---|---|---|---|
| 0:0 | 846.00 a 930.60 | 861.89 | 949.4, 904.6, 861.9 |
| 9:1 | 928.75 a 1040.20 | 955.18 | 1018.8, 986.5, 955.2 |

Los dos intervalos solo coinciden entre 928.75 y 930.60 MPa. Esto se debe a que la referencia fijó los niveles de carga como fracción de la resistencia de cada laminado, y la resistencia del 9:1 es 31.7 % mayor. Es importante destacar que, en términos absolutos, la resistencia a fatiga del 9:1 supera a la del 0:0 entre 7.3 y 10.8 %, mientras que en términos relativos a su propia resistencia estática el 9:1 falla a niveles menores, que es lo que el artículo describe como una reducción cercana al 20 % en el nivel de carga.

La siguiente tabla compara la vida que da el ajuste con las vidas medidas en cada nivel.

| Laminado | Nivel (%) | σ_max (MPa) | Vida del ajuste (ciclos) | Ajuste entre media geométrica de las vidas medidas |
|---|---|---|---|---|
| 0:0 | 75.0 | 846.00 | 2425843 | 2.52 |
| 0:0 | 77.5 | 874.20 | 509034 | 0.84 |
| 0:0 | 80.0 | 902.40 | 112244 | 0.51 |
| 0:0 | 82.5 | 930.60 | 25929 | 1.39 |
| 9:1 | 62.5 | 928.75 | 7418724 | 7.83 |
| 9:1 | 65.0 | 965.90 | 450466 | 0.67 |
| 9:1 | 67.5 | 1003.05 | 30403 | 0.21 |
| 9:1 | 70.0 | 1040.20 | 2263 | 1.79 |

Debido a que los exponentes son pequeños, la vida es muy sensible al esfuerzo. Un cambio de 1 % en el esfuerzo multiplica la vida por 1.61 en el laminado 0:0 y por 2.04 en el 9:1, y un cambio de 5 % la multiplica por 10.2 y por 32.6. De mismo modo, el ajuste reproduce el esfuerzo dentro de alrededor de 2 %, lo que en vida equivale a un factor cercano a 5 en el nivel de 67.5 % del laminado 9:1. En el nivel más bajo de cada laminado la comparación no es concluyente, ya que la mayoría de esas probetas se interrumpieron en 10^6 ciclos y su vida real es mayor. Con base en lo anterior, la ley de vida se usa solo dentro del intervalo ensayado, sus vidas se acotan en 10^6 ciclos, y la incertidumbre en vida se declara como un factor y no como un porcentaje.

## 6. Degradación de rigidez (Fig. 9 de la referencia)

La referencia define la degradación como 1 − T/T0, en donde T es la rigidez del ciclo, calculada como el rango de esfuerzo entre el rango de deformación, y T0 es la del primer ciclo. La Fig. 9 muestra una probeta por laminado, elegidas con vidas cercanas a 200000 ciclos. Las vidas de la leyenda coinciden con valores de la Tabla 2, por lo que la curva del laminado 0:0 corresponde al nivel de 80 % (N_f = 145788) y la del 9:1 al nivel de 67.5 % (N_f = 113511).

Los puntos digitalizados se expresan contra la fracción de vida D = N/N_f, y la capa de materiales interpola de forma lineal entre ellos. La serie del 9:1 tenía un descenso de 0.0007 entre 5000 y 20000 ciclos, que se sustituyó por su máximo acumulado para que la degradación no decrezca.

| D (0:0) | d (0:0) | D (9:1) | d (9:1) |
|---|---|---|---|
| 0.00000 | 0.0000 | 0.00000 | 0.0000 |
| 0.00003 | 0.0163 | 0.00002 | 0.0025 |
| 0.00014 | 0.0221 | 0.00004 | 0.0055 |
| 0.00069 | 0.0237 | 0.00009 | 0.0075 |
| 0.00686 | 0.0298 | 0.00088 | 0.0095 |
| 0.06859 | 0.0420 | 0.00881 | 0.0124 |
| 0.13719 | 0.0454 | 0.04405 | 0.0169 |
| 0.17148 | 0.0560 | 0.08810 | 0.0169 |
| 0.20578 | 0.0647 | 0.17619 | 0.0169 |
| 0.27437 | 0.0711 | 0.26429 | 0.0191 |
| 0.34296 | 0.0751 | 0.35239 | 0.0238 |
| 0.41156 | 0.0807 | 0.44049 | 0.0256 |
| 0.48015 | 0.0832 | 0.52858 | 0.0287 |
| 0.54874 | 0.0878 | 0.61668 | 0.0309 |
| 0.61733 | 0.0927 | 0.70478 | 0.0335 |
| 0.68593 | 0.0991 | 0.79287 | 0.0367 |
| 0.75452 | 0.1011 | 0.88097 | 0.0399 |
| 0.82311 | 0.1031 | 0.96907 | 0.0413 |
| 0.89171 | 0.1067 | 1.00000 | 0.0439 |
| 0.96030 | 0.1132 | | |
| 1.00000 | 0.1351 | | |

Al final de su vida, la probeta 0:0 perdió 13.5 % de rigidez y la 9:1 perdió 4.4 %, lo que coincide con la afirmación del artículo de que los nanorrellenos híbridos reducen la degradación. Por lo que la relación entre daño y rigidez queda definida por una tabla leída de la referencia, con la limitación de que proviene de una sola probeta por laminado y de un solo nivel de carga.

## 7. Tenacidad a la fractura en modo I (Tabla 3 de la referencia)

Los valores de G_IC, medidos según ASTM D5528, son 795 ± 92 (0:0), 1000 ± 120 (10:0), 968 ± 141 (0:10), 917 ± 94 (5:5), 1034 ± 102 (9:1) y 1093 ± 62 J/m² (1:9). El texto del artículo declara una mejora de 12.8 % para el laminado 0:10, mientras que los valores de la tabla dan 21.8 %. Esta tabla no interviene en el modelo y se registra solo para completar la extracción.

## 8. Dimensionamiento propuesto de la capa mínima (PUERTA ARI M0)

> **Nota del 11 de noviembre de 2026.** El dimensionamiento de esta sección
> cambió ese día: la referencia de carga pasó a la pieza más pesada de la
> escena (15 kg, 7.5 V, `senal_ref_V`), las lecturas cercanas a un nivel del
> catálogo entran al modelo con el valor del nivel y `ciclos_por_paso` pasó a
> 350 (`config/materiales.json` versión 2). Ver `docs/EVIDENCIA_U0.md` y
> `docs/ORDEN_A2_FASE_3_CIERRE.md`. El texto siguiente se conserva como estaba.

Esta sección es una propuesta de diseño y requiere la confirmación de Ari antes de implementarse.

### 8.1 Mapeo de la carga al esfuerzo

La señal de peso de la báscula se convierte en una fracción de carga f = peso_V / 10, que no depende de la unidad de masa. El elemento vigilado es una varilla virtual cuyo ciclo de esfuerzo por cada paso de caja es

    σ_max = σ_ref · (R_ref + (1 − R_ref) · f)
    σ_min = σ_ref · R_ref
    Δσ    = σ_max − σ_min

con σ_ref = 930.0 MPa y R_ref = 0.1. Esta forma equivale a la Ecuación 4 del documento técnico, con una masa muerta igual a un noveno de la masa de plena escala.

Los dos valores se eligen por las siguientes razones. El esfuerzo de 930.0 MPa cae dentro de los dos intervalos ensayados (846.00 a 930.60 MPa para el 0:0 y 928.75 a 1040.20 MPa para el 9:1), cuyo traslape va de 928.75 a 930.60 MPa, por lo que la carga máxima de la escena puede evaluarse en ambos laminados sin extrapolar. La relación de 0.1 es la de los ensayos de la referencia, y con este mapeo los ciclos que caen dentro del intervalo del laminado 0:0 tienen R entre 0.100 y 0.110. Una masa muerta mayor permitiría que más cajas cayeran dentro del intervalo, no obstante llevaría R a valores cercanos a 0.65, en donde los parámetros de la referencia dejan de aplicar.

La sección equivalente de la varilla resulta de 0.234 mm² si la plena escala de la báscula es de 20 kg. Esa sección no corresponde a un diseño físico. La varilla es un recurso numérico que coloca el espectro de carga de la escena dentro del intervalo ensayado por la referencia, y así debe declararse en el reporte.

### 8.2 Reglas de daño

1. Se evalúan dos varillas en paralelo con la misma historia de carga, una del laminado 0:0 y otra del 9:1.
2. Un ciclo cuyo σ_max cae dentro del intervalo ensayado del laminado consume ΔD = k_t / N, en donde N es el menor entre la vida del ajuste y 10^6 ciclos. El tope en 10^6 es conservador, ya que la referencia no observó fallas más allá de ese número.
3. Un ciclo por debajo del intervalo no recibe daño y se cuenta aparte. Un ciclo por encima del intervalo tampoco se extrapola, se cuenta aparte y levanta una alerta.
4. El factor k_t = 2500 ciclos por paso es un artificio de demostración, de modo que una corrida de una hora recorra los umbrales de alerta. Su valor definitivo se fija con la distribución de masas que mida el paso L.
5. Los umbrales son preventiva en D = 0.5, crítica en D = 0.8 y falla en D = 1, según la regla de Miner.
6. La galga virtual reporta el rango de deformación del ciclo, Δε = Δσ / (E0 · (1 − d(D))) más un ruido gaussiano de 25 microdeformaciones, con D tomado antes de sumar el daño de ese paso. Esto ajusta la Ecuación 5 del documento técnico, que usaba el esfuerzo máximo, para coincidir con la definición de rigidez de la referencia.

### 8.3 Consecuencias numéricas

| Peso (V) | f | σ_max (MPa) | R | Laminado 0:0 | Laminado 9:1 |
|---|---|---|---|---|---|
| 10.00 | 1.0000 | 930.000 | 0.1000 | N = 26737.5, ΔD = 0.093502 | N del ajuste 6739167.4, se usa 1000000, ΔD = 0.002500 |
| 9.99 | 0.9990 | 929.163 | 0.1001 | N = 27908.8, ΔD = 0.089577 | se usa 1000000, ΔD = 0.002500 |
| 9.98 | 0.9980 | 928.326 | 0.1002 | N = 29132.6, ΔD = 0.085815 | por debajo del intervalo |
| 9.77 | 0.9770 | 910.749 | 0.1021 | N = 72394.2, ΔD = 0.034533 | por debajo del intervalo |
| 9.50 | 0.9500 | 888.150 | 0.1047 | N = 239519.5, ΔD = 0.010438 | por debajo del intervalo |
| 9.40 | 0.9400 | 879.780 | 0.1057 | N = 375977.3, ΔD = 0.006649 | por debajo del intervalo |
| 9.20 | 0.9200 | 863.040 | 0.1078 | N = 938544.7, ΔD = 0.002664 | por debajo del intervalo |
| 9.00 | 0.9000 | 846.300 | 0.1099 | N del ajuste 2385230.7, se usa 1000000, ΔD = 0.002500 | por debajo del intervalo |
| 8.99 | 0.8990 | 845.463 | 0.1100 | por debajo del intervalo | por debajo del intervalo |
| 7.50 | 0.7500 | 720.750 | 0.1290 | por debajo del intervalo | por debajo del intervalo |

El laminado 0:0 recibe daño a partir de 8.9964 V y el 9:1 a partir de 9.9851 V. A plena escala, el laminado 0:0 consume 9.35 % de su vida por paso y el 9:1 consume 0.25 %, una relación de 37.4 que constituye una cota inferior de la ventaja del nanorrelleno híbrido, debido al tope de 10^6 ciclos. Los valores de esta tabla se calcularon por dos caminos independientes, con potencias en doble precisión y con logaritmos a 40 dígitos, y coincidieron con una diferencia relativa menor a 10^−9.

A plena escala y sin daño, el rango de deformación es de 10338.4 microdeformaciones en el laminado 0:0 y de 8999.0 en el 9:1. En el laminado 0:0 ese rango crece a 10805.6 con D = 0.0935, a 11293.1 con D = 0.5, a 11518.2 con D = 0.8 y a 11953.3 con D = 1.

Con base en este dimensionamiento, el daño de la varilla queda gobernado por los artículos más pesados de la escena, que es un resultado propio de las curvas de fatiga casi planas de un laminado unidireccional y no un defecto del modelo.

## 9. Lo que los datos existentes ya anticipan

> **Nota del 11 de noviembre de 2026.** La lectura de los pesos altos de esta
> sección cambió ese día: la escena no emite piezas de más de 15 kg, así que
> las lecturas de 8 V o más corresponden a pesadas con más de una pieza y no a
> artículos pesados. Ver `docs/EVIDENCIA_U0.md` y
> `docs/ORDEN_A2_FASE_3_CIERRE.md`. El texto siguiente se conserva como estaba.

Los 429 pasos de caja registrados el 25 de octubre de 2026 (UTC) en `datos/a2_planta_eventos.jsonl` permiten tres observaciones previas al paso L.

1. **Unidad de la báscula.** El manual de Factory I/O indica que la báscula de banda tiene dos configuraciones, de 20 kg y de 100 kg, con salida de 0 a 10 V, y su catálogo de artículos lista pesos de 3, 5, 7, 8, 9, 10, 12, 14, 15, 16 y 20 kg. De los 429 pesos, 383 caen a menos de 0.03 V de siete niveles, que son 1.5, 2.5, 3.5, 4.0, 5.0, 7.5 y 10.0 V. Con 2 kg por volt esos niveles equivalen a 3, 5, 7, 8, 10, 15 y 20 kg, todos presentes en el catálogo. Esto indica que la báscula está en su configuración de 20 kg y que 1 V equivale a 2 kg, y no a 1 kg como supone hoy `config/planta_fio.json`. Falta confirmarlo en la escena.
2. **Saturación.** El artículo más pesado del catálogo pesa 20 kg, que coincide con la plena escala de la configuración de 20 kg. Por lo que una lectura de 10.0 V es la esperada para ese artículo y no implica por sí sola una señal recortada.
3. **Pesaje de los artículos pesados.** De las 13 lecturas de 8 V o más, solo 5 marcan 10.00 V. Las otras 8 marcan entre 8.36 y 9.77 V, aunque el catálogo no tiene artículos entre 16 y 20 kg, lo que sugiere que esos artículos se pesaron antes de asentarse. El cliente solo marcó como no estable 1 de los 429 pesos. Con lecturas crudas, esas 429 cajas llevan al laminado 0:0 a D = 0.55. Si las 10 lecturas de 9.0 V o más se tomaran como 10.0 V, el resultado sería D = 0.94.

Es importante destacar que una lectura 2.3 % baja (9.77 en lugar de 10.00 V) reduce el daño asignado 2.7 veces. Por ende, la precisión de pesaje que basta para clasificar no basta para contabilizar fatiga, y esa diferencia es un resultado que la capa de materiales aporta y que el paso L debe medir.

## 10. Limitaciones del modelo

Los parámetros provienen de una sola relación de esfuerzos, de una frecuencia de 10 Hz y de temperatura ambiente. La regla de Miner es lineal y no considera el orden de las cargas. La tabla de rigidez proviene de una probeta por laminado y se aplica a cualquier nivel de carga como función única del daño. La vida se acota en 10^6 ciclos, lo que sobrestima el daño de las cargas bajas del intervalo. El factor k_t y el ruido de la galga son supuestos de demostración. Con base en estas limitaciones, las cifras de la capa mínima deben presentarse como el resultado de un modelo nominal trazable a su fuente y no como una predicción de vida de una pieza real.
