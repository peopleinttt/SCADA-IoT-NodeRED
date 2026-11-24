# Evidencia de la puerta U0: báscula y emisor de la escena

Fecha: 11 de noviembre de 2026. Esta nota registra la configuración de la báscula y del emisor de la escena Sorting by Weight, leída del archivo de escena que Factory I/O 2.5.10 guardó ese día a las 11:41:54. El archivo es texto XML y una copia idéntica quedó en `docs/capturas/escena_sorting_by_weight_A2.factoryio` (SHA-256 `b9738f9318b8b1b1878e053de35e0066ecddb73ee5d01e128a1524d02fffeb87`). Se usa el archivo en lugar de dos capturas de pantalla, ya que contiene la configuración guardada y no una vista de ella.

## 1. Configuración de la báscula

Las líneas 57 y 58 del archivo pertenecen al objeto `ConveyorScale`.

```
<ComponentIO Index="1" CurrentOperatingMode="0" />
<OperatingMode Description="$C_ConveyorScale_OM_Default20_NAME">
```

El manual de Factory I/O indica para la báscula de banda capacidades de 20 y 100 Kg, con las configuraciones "20 Kg Max." y "100 Kg Max.", y una señal `Weight (V)` de 0 a 10 V. El modo guardado es el de 20 kg, por lo que 10 V equivalen a 20 kg y la báscula mide 2 kg por volt.

## 2. Piezas que emite la escena

Las líneas 104 a 106 pertenecen al objeto `Emitter`, cuya salida está forzada a encendido en la línea 101.

```
<Emitter MinTimeToEmit="1" MaxTimeToEmit="2" UpTo="0" RandomPartPosition="False" RandomPartOrientation="False">
  <Bases />
  <Parts BoxS="True" BoxM="True" BoxL="True" PalletizingBox="True" ProductBaseGreen="True" ProductLidBlue="True" />
```

El emisor entrega seis tipos de pieza y ninguna base. La tabla relaciona cada pieza con el peso que declara el manual y con las 434 pesadas (`caja_pesada`) registradas el 25 de octubre de 2026 entre la 01:00 y las 03:00 UTC en `datos/a2_planta_eventos.jsonl`, contadas a menos de 0.03 V de cada nivel. La correspondencia entre el nombre del archivo y el nombre del manual se hizo por nombre.

| Pieza en el archivo | Nombre en el manual | Peso (kg) | Nivel a 2 kg/V (V) | Pesadas en el nivel |
|---|---|---|---|---|
| `PalletizingBox` | Palletizing Box | 3 | 1.5 | 70 |
| `ProductLidBlue` | Blue Product Lid | 5 | 2.5 | 63 |
| `ProductBaseGreen` | Green Product Base | 7 | 3.5 | 67 |
| `BoxS` | Small | 8 | 4.0 | 63 |
| `BoxM` | Medium | 10 | 5.0 | 74 |
| `BoxL` | Large | 15 | 7.5 | 46 |

Las 51 pesadas restantes se reparten en 5 de 10.00 V y 46 fuera de nivel, entre 1.60 y 9.77 V. Por ende, los seis tipos de pieza explican seis de los siete niveles observados, y la pieza más pesada de la escena pesa 15 kg, que equivale a 7.5 V.

## 3. Lo que cambia respecto a la sección 9 de PARAMETROS_MATERIALES.md

1. **Unidad de la báscula.** Queda confirmada. La báscula está en su configuración de 20 kg y 1 V equivale a 2 kg.
2. **Saturación.** El punto 2 de la sección 9 pierde su sustento. Los artículos de 20 kg del manual son las dos tarimas, que son bases, y el emisor no entrega bases. Por lo que las cinco lecturas de 10.00 V no corresponden a ninguna pieza de la escena.
3. **Lecturas altas.** Las 13 lecturas de 8 V o más superan a la pieza más pesada, por lo que no pueden venir de una sola pieza pesada antes de asentarse, como suponía el punto 3. Son consistentes con más de una pieza sobre la báscula durante la pesada. El manual no describe el comportamiento por encima de la capacidad, por lo que leer los 10.00 V como señal recortada es una inferencia y no un dato documentado. De esas 13 lecturas, 3 ocurrieron en la corrida de 127 pesadas y 10 en la de 307.
4. **Dimensionamiento de la sección 8.** Una sola pieza produce como máximo 7.5 V, que equivale a un esfuerzo máximo de 720.75 MPa. Ese valor queda por debajo del intervalo ensayado de los dos laminados, que empieza en 846.00 MPa para el 0:0 y en 928.75 MPa para el 9:1. Por lo que el daño de las varillas no proviene de los artículos más pesados, como decía la sección 8, sino de las pesadas con más de una pieza sobre la báscula, y una corrida con las piezas bien separadas no acumularía daño.

Los pasos T, U y L no dependen del punto 4. El paso M3 sí depende, y la decisión sobre el dimensionamiento corresponde a Ari con `docs/corrida_L.md` a la vista. En síntesis, la unidad de 2 kg por volt queda confirmada y la interpretación de las lecturas altas cambia de artículos pesados a pesadas con más de una pieza.

## 4. Driver guardado en la escena

El bloque `ModbusTCPServer` del archivo, en las líneas 1193 a 1231, declara 16 entradas discretas, 16 bobinas, 1 registro de entrada y 4 registros de retención, con offsets en 0 y `ScaleFactor="100"`. Las 33 direcciones de `config/mapa_registros_fio.json` coinciden con las etiquetas guardadas en la escena. La escena tiene un punto adicional que el mapa no usa, el registro de retención 3 con el indicador Weight. La lectura por Modbus de las 11:46:55 respondió en las 33 etiquetas con el driver conectado, por lo que la configuración del driver quedó guardada y coincide con el repositorio.

## Fuentes

- Manual de Factory I/O, Items, consultado el 11 de noviembre de 2026: https://docs.factoryio.com/manual/parts/items/
- Manual de Factory I/O, Light Load Parts, consultado el 11 de noviembre de 2026: https://docs.factoryio.com/manual/parts/light-load/
- `datos/a2_planta_eventos.jsonl`, eventos `caja_pesada` del 25 de octubre de 2026.
