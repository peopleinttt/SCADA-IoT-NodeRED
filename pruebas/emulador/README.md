# Medición contra el emulador real de Realtime Database

Aquí se comprueba lo que el simulador de `pruebas/simulador.py` no puede: cómo
se comportan **las reglas de verdad**.

## Requisitos

Java (el emulador de RTDB corre sobre JVM) y `firebase-tools`. No hace falta
instalarlo global:

```bash
npm install firebase-tools          # en una carpeta cualquiera
```

## Correr

```bash
cd pruebas/emulador
python3 prepara_emulador.py          # sustituye los UID de prueba en las reglas
npx firebase emulators:start --only database --project demo-iot
```

Y en otra terminal:

```bash
python3 mide_errores.py              # códigos HTTP exactos por causa de fallo
python3 ../prueba_reglas.py --uid-ingestor UIDING --uid-visor UIDVIS
```

## El hallazgo que justifica esto

`mide_errores.py` manda ocho escrituras que fallan por ocho causas distintas
—UID equivocado, cuenta sin permiso, rango fuera, marca de tiempo mal formada,
campo extra, campo faltante, plantaId mal formado, tipo equivocado— y mide qué
contesta la base.

Resultado, medido el 2026-08-25 contra estas mismas reglas:

```
RESPUESTAS DISTINTAS OBSERVADAS: 2
  [200 ...]                                  <- 1 caso: el dato correcto
  [401 {"error":"Permission denied"}]        <- 8 casos: TODOS los demás
```

Es decir: **desde Node-RED no se puede saber por qué falló una escritura.**
Un 401 puede ser el token vencido o una temperatura de 85 °C, y la respuesta es
idéntica.

De ahí sale el diseño del flujo: `01_valida_telemetria.js` replica las mismas
condiciones que las reglas y rechaza en el borde, donde el mensaje sí puede
decir la verdad. Y `03_respuesta_firebase.js` ya no adivina la causa de un 401:
declara que el dato pasó la validación local y que, por lo tanto, la causa está
en la credencial o en las reglas publicadas.
