# Activity 2 — Demonstration script

Technical checklist for the evidence video, in the order it is shown. Every
step lists the command or action that triggers it and what must be seen.
Commands run from the repository root (`~/dev aws/dev/IoT`).

## 0. Before recording

| Check | Command | Expected |
|---|---|---|
| Quick test battery | `./pruebas/bateria.sh` | `FIN: 0 fallidas` |
| Plant choice in `.env` | see the header of `demo_a2.sh` | substitute (local) or Factory I/O (`A2_SUSTITUTO=0`, `A2_MAPA=config/mapa_registros_fio.json`, `A2_PLANTA_CONFIG=config/planta_fio.json`) |
| Pre-flight only | `./demo_a2.sh --revisa` | limits feasible (T_ef from the measured block), Modbus answers, Firebase session, Gemini quota left |

With Factory I/O, route the client through the TCP relay: it is the switch
for step 8, and it lets the Python tools reach the Parallels VM (macOS
blocks Python from the local network unless it is granted "Local Network"):

```bash
node pruebas/relevo.mjs 5030 10.211.55.3 502
# and in .env:  A2_MODBUS_HOST=127.0.0.1  A2_MODBUS_PUERTO=5030
```

`./demo_a2.sh` resets the scene over Modbus before starting (Reset, wait
until it is empty, Run; `tools/reinicia_escena.mjs`).

## 1. Architecture

- **Show:** `docs/CICLO_DESARROLLO_A2.md` (status table) and the Node-RED
  editor tabs: `A2 · Planta`, `A2 · Nube`, `A2 · HMI`, `A2 · Diagnostico`,
  `A2 · Sustituto`, next to the Activity 1 tabs.
- **Say:** Factory I/O (Modbus TCP server) → Node-RED client (block polling,
  FIFO, weighing, sorting, safe state) → Firebase `proceso` branch → live
  chart, plus HMI and Gemini advice. The register map lives in one JSON file
  (`docs/MAPA_REGISTROS.md`).
- **Command:** `./demo_a2.sh` → prints the HMI and chart URLs.

## 2. Factory I/O running

- **Action:** Factory I/O → *Sorting by Weight* → Play; driver *Modbus TCP/IP
  Server* connected (green). With the substitute instead, show
  `A2 · Sustituto` status in the editor.
- **Proof on screen:**
  `python3 tools/sonda_modbus.py --mapa config/mapa_registros_fio.json --host 127.0.0.1 --puerto 5030 vigila -s 20`
  → sensors change as boxes pass; RTT and scene refresh period are printed.

## 3. HMI — start and stop

- **Open:** `http://localhost:1881/dashboard/a2` (or the tailnet URL printed
  by `demo_a2.sh` from another device).
- **Action:** **Start** (with the substitute, also **Emitter ON**; the
  Factory I/O scene emits boxes by itself and has no emitter coil).
  *Plant communication* shows *Online*, *Line* shows *Running*.
- **Scene panel:** the **Start**, **Stop** and **Emergency stop** buttons of the
  Factory I/O panel do the same (Stop and Emergency stop are normally closed).
  Emergency stop switches everything off and shows *Emergency stop*; Start is
  refused until it is released. Lights: Start = running, Stop = stopped,
  Reset = emergency. The panel counters show boxes per destination.
- **Show a rejected command:** with variable-speed belts, **Apply** a setpoint
  above the limit → the red banner shows `422 · velocidad_fuera_de_limite`.
  With fixed belts, the setpoint field is hidden and the API answers
  `422 velocidad_no_aplica`.
- **Action:** **Stop** → *Line: Stopped*.

## 4. Boxes sorted

- **Action:** Start (+ Emitter ON with the substitute) for ~1 minute.
- **Show:** *Boxes* card: sorted, per minute, counts per destination (Left /
  Forward / Right with the diverter; Exit / Rejected with the pusher), last box
  mass and destination, *lost: 0*.
- **Units:** with Factory I/O the scale is in its *20 Kg Max.* setting, so
  0-10 V is 0-20 kg (2 kg per volt). Classes: light up to 9.0 kg (4.5 V),
  medium up to 14.0 kg (7.0 V), heavy above. The scene's items weigh 3, 5, 7,
  8, 10 and 15 kg. Box records written before 11 Nov 2026 used 1 kg per volt.

## 5. Records arriving in Firebase

- **Show:** Firebase console → Realtime Database →
  `plantas/planta_01/proceso`: one record per box (with `caja_masa_kg` and
  `destino`) plus heartbeats: every `A2_LATIDO_S` seconds (60 by default)
  while the line runs, every `A2_LATIDO_REPOSO_S` seconds (900 by default)
  while it is stopped with no change, and one right away whenever the line
  state changes (e.g. Start, Stop, emergency stop).
- **HMI:** *Firebase* card shows the last accepted record id.
- **Requires:** rules published (gate P1) and `A2_NUBE=1`.

## 6. Live chart

- **Open:** `http://localhost:8123/proceso.html`.
- **Show:** mass per box (by destination) and boxes per minute updating
  without reloading while the line runs.
- **Note:** the 429 box records of 25 Oct 2026 in `planta_01` were written
  with 1 kg per volt, so their masses are half the real ones; the chart says
  so under the mass plot when such records are shown.

## 7. Diagnosis

- **Action:** HMI → **Request diagnosis**.
- **Show:** *Diagnosis* card: level (normal / preventiva / critica), action
  code and English text. It is advice only: nothing moves the plant. Quota: at
  most 15 per day (own cap), 1 per minute.

## 8. Safe state: disconnection and recovery

- **Action:** with the line running, stop the proxy (Ctrl+C), or in Factory
  I/O stop the driver.
- **Show:** within `timeout_com_ms + 1 s` the HMI shows *NO COMMUNICATION*;
  **Start** answers `409 · sin_comunicacion`.
- **Action:** start the proxy again (same command) or restart the driver.
- **Show:** the HMI goes back to *Online* and *Stopped*: the client wrote
  emitter off (substitute), every belt off and the diverter wheels off
  **before** resuming, and does not restart by itself. **Start** works again.
- **Proof:** `tail datos/a2_planta_eventos.jsonl` → `reconexion_inicia`,
  one `escritura` line with `motivo: seguro` per actuator (8 with Factory I/O:
  five belts and three wheel coils), `reconexion_completa`.

## 9. Closing

- `./demo_a2.sh --apaga`
- Numbers for the report: `docs/INSTRUMENTACION_A2.md` (definitions) and
  `docs/corrida_a2.md` (C9 results).
