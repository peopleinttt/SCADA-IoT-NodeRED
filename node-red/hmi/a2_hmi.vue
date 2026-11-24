<template>
  <div class="a2">
    <div v-if="!s || !s.ready" class="banner warn">Waiting for the plant client (A2-Planta)...</div>
    <template v-else>
      <div class="row">
        <div class="card status" :class="s.comm === 'ok' ? 'good' : 'bad'">
          <div class="label">Plant communication</div>
          <div class="big">{{ s.commLabel }}</div>
          <div class="small">poll {{ s.pollMs }} ms · expected RTT {{ s.rttMs }} ms · worst gap {{ s.tEfMs }} ms</div>
        </div>
        <div class="card status" :class="s.running ? 'good' : 'idle'">
          <div class="label">Line</div>
          <div class="big">{{ s.line }}</div>
          <div class="small">{{ s.actuator === 'desviador' ? '3-way wheel diverter' : 'Reject pusher' }} · emitter {{ s.emitter ? 'ON' : 'OFF' }}</div>
        </div>
        <div class="card status" :class="s.feasible ? 'good' : 'bad'">
          <div class="label">Timing limits</div>
          <div class="big">{{ s.feasible ? 'Feasible' : 'NOT feasible' }}</div>
          <div class="small" v-if="s.variableBelt">belt speed {{ s.velMinV }} – {{ s.velMaxV }} V</div>
          <div class="small" v-else>fixed-speed belts</div>
          <div class="small problem" v-for="p in (s.problems || []).slice(0, 2)" :key="p">{{ p }}</div>
        </div>
      </div>

      <div class="row">
        <div class="card controls">
          <div class="label">Operation</div>
          <div class="buttons">
            <button class="go" @click="cmd('marcha')">Start</button>
            <button class="stop" @click="cmd('paro')">Stop</button>
            <button @click="cmd('emisor', { valor: !s.emitter })">{{ s.emitter ? 'Emitter OFF' : 'Emitter ON' }}</button>
          </div>
          <div v-if="s.variableBelt" class="setpoint">
            <label>Belt setpoint (V)</label>
            <input type="number" step="0.01" :min="0" :max="s.velMaxV" v-model.number="setpoint" />
            <button @click="cmd('velocidad', { vel_V: setpoint })">Apply</button>
            <span class="small">applied {{ s.appliedV }} V · allowed 0 or {{ s.velMinV }}–{{ s.velMaxV }} V</span>
          </div>
          <div v-if="resp" class="resp" :class="resp.codigo === 200 ? 'ok' : 'err'">
            {{ resp.codigo }} · {{ resp.accion || resp.motivo }}<span v-if="resp.codigo !== 200"> — {{ explain(resp) }}</span>
          </div>
        </div>
        <div class="card">
          <div class="label">Boxes</div>
          <div class="kpis">
            <div><span class="num">{{ s.boxesOut }}</span><span class="cap">sorted</span></div>
            <div><span class="num">{{ s.perMinute }}</span><span class="cap">per minute</span></div>
            <div><span class="num">{{ s.boxesIn }}</span><span class="cap">entered</span></div>
            <div><span class="num" :class="s.lost ? 'badtxt' : ''">{{ s.lost }}</span><span class="cap">lost</span></div>
          </div>
          <div class="dest">
            <span v-for="(n, d) in s.byDestination" :key="d" class="pill">{{ label(d) }}: <b>{{ n }}</b></span>
            <span v-if="s.misrouted" class="pill badtxt">misrouted: <b>{{ s.misrouted }}</b></span>
          </div>
          <div class="small" v-if="s.lastBox">Last box #{{ s.lastBox.id }}: <b>{{ s.lastBox.massKg }} kg</b> → {{ label(s.lastBox.destination) }}</div>
          <div class="small" v-else>No box sorted yet</div>
        </div>
      </div>

      <div class="row">
        <div class="card">
          <div class="label">Firebase (process branch)</div>
          <div v-if="!s.firebaseOn" class="small">Cloud writes are off (A2_NUBE is not 1)</div>
          <div v-else-if="s.firebase" class="small">Last accepted: {{ s.firebase.kind }} at {{ s.firebase.ts }}<br><code>{{ s.firebase.id }}</code></div>
          <div v-else class="small">No record accepted yet</div>
          <div class="small" v-if="s.firebaseLast && s.firebaseLast.code !== 201">Last attempt: code {{ s.firebaseLast.code }}</div>
        </div>
        <div class="card">
          <div class="label">Diagnosis (advice only, never moves the plant)</div>
          <div v-if="s.diagnosis" class="small">
            <b :class="'lvl-' + s.diagnosis.nivel_estimado">{{ (s.diagnosis.nivel_estimado || '').toUpperCase() }}</b>
            · {{ s.diagnosis.accion_codigo }}<span v-if="s.diagnosis.valor_pct"> ({{ s.diagnosis.valor_pct }} %)</span><br>
            {{ s.diagnosis.texto_diagnostico }}<br><span class="muted">{{ s.diagnosis.ts }}</span>
          </div>
          <div v-else class="small">No diagnosis yet</div>
          <button class="small-btn" @click="cmd('diagnostico')">Request diagnosis</button>
        </div>
        <div class="card" v-if="s.esp32">
          <div class="label">ESP32 telemetry (Activity 1)</div>
          <div class="small">{{ s.esp32.temperature_C }} °C · {{ s.esp32.vibration_mm_s }} mm/s · {{ s.esp32.cycles }} cycles<br><span class="muted">{{ s.esp32.ts }}</span></div>
        </div>
      </div>
      <div class="row" v-if="mat">
        <div class="card materials">
          <div class="label">Materials layer (virtual rods, nominal model; advice only)</div>
          <div v-if="mat.error" class="resp err">{{ mat.error }}</div>
          <div class="rods">
            <div v-for="r in mat.rods" :key="r.rod" class="rod" :class="'lvlbox-' + r.level">
              <div class="small"><b>{{ r.rod }}</b> · laminate {{ r.laminate }}</div>
              <div class="big">{{ r.lifePct.toFixed(1) }} %<span class="cap"> life used</span></div>
              <div class="small">level <b :class="'lvl-' + r.level">{{ r.levelLabel.toUpperCase() }}</b>
                <span v-if="r.lastLevelChange" class="chg"> · changed to {{ r.lastLevelChange.level }} at step {{ r.lastLevelChange.step }}</span></div>
              <div class="small">steps inside {{ r.inside }} · below {{ r.below }} · above {{ r.above }} the tested range</div>
              <div class="small">last strain range: {{ r.lastStrainRangeUe === null ? '–' : r.lastStrainRangeUe + ' µε' }}</div>
              <div class="small" v-if="r.estimate">remaining: ~{{ r.estimate.steps }} steps<span v-if="r.estimate.seconds !== null"> · ~{{ duration(r.estimate.seconds) }}</span></div>
              <div class="small muted" v-else>no estimate yet</div>
              <div class="small problem" v-if="r.alert">ALERT: {{ r.alert.text }} ({{ r.alert.count }} steps, last at step {{ r.alert.lastStep }})</div>
            </div>
          </div>
          <div class="muted">{{ mat.steps }} steps · {{ mat.noWeight }} without weight</div>
        </div>
      </div>
      <div class="muted foot">Updated {{ s.ts }}</div>
    </template>
  </div>
</template>

<script>
export default {
  data () { return { s: null, resp: null, setpoint: 0, mat: null } },
  watch: {
    msg: function (m) {
      // Dashboard 2.0 reescribe msg.topic: se distingue por la forma del payload.
      if (!m || !m.payload) return
      if (m.payload.materials === true) {
        this.mat = m.payload                 // solo llega con A2_MATERIALES=1 (pestana A2 · Materiales)
      } else if (m.payload.ready !== undefined) {
        this.s = m.payload
        if (this.s && this.s.setpointV !== undefined && this.setpoint === 0) this.setpoint = this.s.setpointV
      } else if (m.payload.codigo !== undefined) {
        this.resp = m.payload
      }
    }
  },
  methods: {
    cmd (accion, extra) { this.send({ payload: Object.assign({ accion: accion }, extra || {}) }) },
    duration (sec) {
      if (sec < 90) return sec + ' s'
      if (sec < 5400) return Math.round(sec / 60) + ' min'
      return (sec / 3600).toFixed(1) + ' h'
    },
    label (d) { return ({ left: 'Left', right: 'Right', forward: 'Forward', salida: 'Exit', rechazo: 'Rejected' })[d] || d },
    explain (r) {
      const m = {
        limites_no_factibles: 'timing limits are not feasible with the measured polling and RTT',
        consigna_fuera_de_intervalo: 'set a belt speed inside the allowed range first',
        velocidad_fuera_de_limite: 'speed must be 0 or inside the allowed range',
        velocidad_no_aplica: 'belts in this scene run at fixed speed',
        sin_comunicacion: 'no communication with the plant',
        linea_detenida: 'start the line before the emitter'
      }
      return m[r.motivo] || r.motivo
    }
  }
}
</script>

<style scoped>
.a2 { font-family: system-ui, sans-serif; color: #1c2024; }
.row { display: flex; flex-wrap: wrap; gap: 12px; margin-bottom: 12px; }
.card { flex: 1 1 260px; background: #fff; border: 1px solid #d9d9e0; border-radius: 6px; padding: 12px; }
.label { font-size: 12px; text-transform: uppercase; letter-spacing: .04em; color: #60646c; margin-bottom: 6px; }
.big { font-size: 24px; font-weight: 700; }
.small { font-size: 13px; color: #3c4049; margin-top: 4px; }
.muted { color: #8b8d98; font-size: 12px; }
.status.good { border-left: 6px solid #2a9d5c; }
.status.bad { border-left: 6px solid #d1372e; }
.status.idle { border-left: 6px solid #8b8d98; }
.problem { color: #b42318; }
.buttons { display: flex; gap: 8px; flex-wrap: wrap; }
button { font-size: 15px; padding: 8px 14px; border-radius: 6px; border: 1px solid #b9bbc6; background: #f0f0f3; cursor: pointer; }
button.go { background: #2a9d5c; color: #fff; border-color: #2a9d5c; }
button.stop { background: #d1372e; color: #fff; border-color: #d1372e; }
.small-btn { font-size: 12px; padding: 4px 8px; margin-top: 8px; }
.setpoint { margin-top: 10px; display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
.setpoint input { width: 90px; padding: 6px; }
.resp { margin-top: 10px; padding: 6px 10px; border-radius: 4px; font-size: 14px; }
.resp.ok { background: #e6f6eb; color: #18794e; }
.resp.err { background: #fdecea; color: #b42318; font-weight: 600; }
.kpis { display: flex; gap: 18px; flex-wrap: wrap; }
.kpis div { display: flex; flex-direction: column; }
.num { font-size: 26px; font-weight: 700; }
.cap { font-size: 12px; color: #60646c; }
.dest { margin: 8px 0; display: flex; gap: 6px; flex-wrap: wrap; }
.pill { background: #f0f0f3; border-radius: 12px; padding: 2px 10px; font-size: 13px; }
.badtxt { color: #b42318; }
.lvl-normal { color: #18794e; } .lvl-preventiva { color: #ad5700; } .lvl-critica { color: #b42318; }
.lvl-falla { color: #fff; background: #b42318; padding: 0 4px; border-radius: 3px; }
.rods { display: flex; gap: 12px; flex-wrap: wrap; }
.rod { flex: 1 1 240px; border: 1px solid #d9d9e0; border-radius: 6px; padding: 8px; border-left-width: 6px; }
.lvlbox-normal { border-left-color: #2a9d5c; } .lvlbox-preventiva { border-left-color: #ad5700; }
.lvlbox-critica { border-left-color: #d1372e; } .lvlbox-falla { border-left-color: #7a0d06; background: #fdecea; }
.chg { color: #ad5700; font-weight: 600; }
.foot { margin-top: 4px; }
.banner.warn { background: #fff4d5; padding: 10px; border-radius: 6px; }
</style>
