# Corrida G: geometría de la línea y tiempos de recorrido

Generado con `tools/mide_linea.py datos/corridas/G_2026-11-17`. Definiciones: `docs/INSTRUMENTACION_A2.md`, sección 6. Sin interpretación.

Cajas (`paso_caja`) en la corrida: 151.

## 1. Tramos de los límites del cliente

| Tiempo (s) | n | Mediana | p5 | p95 | Máximo |
|---|---|---|---|---|---|
| `caja_pesada` → confirmación de rama (límite `timeout_confirmacion_s`) | 151 | 1.296 | 1.162 | 1.567 | 1.745 |
| `at_scale` sube → `entry_conveyor` se apaga (límite `no_llego_a_fin_bascula`) | 150 | 0.076 | 0.045 | 0.101 | 0.426 |

| Límite | Valor con `linea` (s) | Máximo observado (s) | Margen (s) | Mayor que el máximo |
|---|---|---|---|---|
| `timeout_confirmacion_s` | 4.670 | 1.745 | 2.925 | sí |
| `no_llego_a_fin_bascula` | 6.165 | 0.426 | 5.739 | sí |

T_ef usado: 55 ms (medido).

## 2. Recorridos sin detenerse

| Tiempo (s) | n | Mediana | p5 | p95 | Máximo |
|---|---|---|---|---|---|
| `at_scale_exit` sube → `at_left_entry` sube | 86 | 0.671 | 0.581 | 0.810 | 0.838 |
| `at_scale_exit` sube → `at_forward_entry` sube | 36 | 0.956 | 0.913 | 1.095 | 1.211 |
| `at_scale_exit` sube → `at_right_entry` sube | 29 | 0.703 | 0.631 | 0.848 | 0.917 |
| `at_left_entry` sube → `at_exit_left` baja (banda de la rama) | 85 | 4.371 | 4.249 | 4.507 | 4.680 |
| `at_forward_entry` sube → `at_exit_front` baja (banda de la rama) | 36 | 4.144 | 4.096 | 4.341 | 4.387 |
| `at_right_entry` sube → `at_exit_right` baja (banda de la rama) | 29 | 4.412 | 4.316 | 4.533 | 4.610 |

## 3. Pulso del sensor de rama por tipo de pieza (nivel de peso del `paso_caja`)

| Tiempo (s) | n | Mediana | p5 | p95 | Máximo |
|---|---|---|---|---|---|
| nivel 1.5 V | 21 | 0.500 | 0.487 | 0.529 | 0.531 |
| nivel 10.0 V | 2 | 0.489 | 0.489 | 0.538 | 0.538 |
| nivel 2.5 V | 17 | 0.632 | 0.584 | 0.666 | 0.666 |
| nivel 3.5 V | 21 | 0.631 | 0.598 | 0.656 | 0.669 |
| nivel 4.0 V | 25 | 0.672 | 0.648 | 0.705 | 0.708 |
| nivel 5.0 V | 30 | 0.579 | 0.535 | 0.629 | 0.630 |
| nivel 7.5 V | 22 | 0.536 | 0.499 | 0.574 | 0.603 |
| fuera de nivel | 13 | 0.501 | 0.353 | 0.694 | 0.694 |

## 4. Intervalo entre `caja_entra` consecutivos

| Tiempo (s) | n | Mínimo | Mediana | p5 | p95 | Máximo |
|---|---|---|---|---|---|---|
| corrida G | 150 | 2.188 | 4.558 | 2.504 | 5.801 | 5.940 |
| corrida L1 | 600 | 1.999 | 4.891 | 2.552 | 5.712 | 5.998 |
| corrida L2 | 600 | 2.068 | 4.653 | 3.157 | 5.691 | 6.051 |
| corrida M1 | 600 | 1.908 | 5.194 | 4.358 | 5.895 | 6.252 |

Emisor en el archivo de escena: `MinTimeToEmit` = 1.0 s, `MaxTimeToEmit` = 2.0 s.

## 5. Posiciones de los sensores en el archivo de escena (unidades de la escena)

| Sensor | Pieza | X | Y | Z |
|---|---|---|---|---|
| `at_scale_entry` | RetroreflectivePhotoelectricSensor | 292 | 8 | 144 |
| `at_exit_left` | RetroreflectivePhotoelectricSensor | 273 | 8 | 114 |
| `at_exit_right` | RetroreflectivePhotoelectricSensor | 273 | 8 | 166 |
| `at_exit_front` | RetroreflectivePhotoelectricSensor | 251 | 8 | 136 |
| `at_scale` | DiffusePhotoelectricSensor | 284 | 8 | 144 |
| `at_scale_exit` | DiffusePhotoelectricSensor | 281 | 8 | 144 |
| `at_left_entry` | DiffusePhotoelectricSensor | 281 | 8 | 136 |
| `at_right_entry` | DiffusePhotoelectricSensor | 273 | 8 | 144 |
| `at_forward_entry` | DiffusePhotoelectricSensor | 273 | 8 | 136 |

| Par de sensores | Distancia en el plano X-Z (unidades de la escena) |
|---|---|
| at_scale_entry -> at_scale_exit | 11.0 |
| at_scale_exit -> at_left_entry | 8.0 |
| at_scale_exit -> at_forward_entry | 11.3 |
| at_scale_exit -> at_right_entry | 8.0 |
| at_left_entry -> at_exit_left | 23.4 |
| at_forward_entry -> at_exit_front | 22.0 |
| at_right_entry -> at_exit_right | 22.0 |

## 6. Valores de `linea` en `config/planta_fio.json` al generar este reporte

| Clave | Valor |
|---|---|
| `velocidad_fija_m_s` | 0.3 |
| `intervalo_emision_min_s` | 1.908 |
| `largo_caja_m` | 0.4 |
| `entrada_a_fin_bascula_m` | 1.2 |
| `fin_bascula_a_confirmacion_m` | 0.9 |
