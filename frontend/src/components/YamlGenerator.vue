<script setup>
import { ref, reactive, computed } from 'vue'
import jsYaml from 'js-yaml'
import { useAppStore } from '../stores/appStore'
import { useT } from '../i18n'
import { generateYaml, uploadYAML, getYamlContent } from '../api'

const emit = defineEmits(['go-next'])
const store = useAppStore()
const t = useT()

const componentName  = ref('')
const gndNetsInput   = ref('GND, PGND')
const rules          = reactive([])
const loadFromSession = ref('')

function addRule() {
  rules.push({
    type: 'pin_to_pin_connection',
    severity: 'error',
    description: '',
    count: '52, 53',
    pin1: '', pin2: '', pin: '', capacitance: '',
    net: '', min_value: '', max_value: '',
  })
}

function removeRule(idx) { rules.splice(idx, 1) }

function buildRuleObj(r) {
  const base = { type: r.type, severity: r.severity }
  if (r.description.trim()) base.description = r.description.trim()
  if (r.type === 'pin_count') {
    base.count = r.count.split(',').map(s => parseInt(s.trim())).filter(n => !isNaN(n))
  } else if (r.type === 'pin_to_pin_connection') {
    base.pin1 = r.pin1.trim(); base.pin2 = r.pin2.trim()
  } else if (r.type === 'pin_to_gnd_cap') {
    base.pin = r.pin.trim(); base.capacitance = r.capacitance.trim()
  } else if (r.type === 'pin_to_pin_cap') {
    base.pin1 = r.pin1.trim(); base.pin2 = r.pin2.trim(); base.capacitance = r.capacitance.trim()
  } else if (r.type === 'pin_floating') {
    base.pin = r.pin.trim()
  } else if (r.type === 'pin_to_net_resistor' || r.type === 'pin_to_net_capacitor' || r.type === 'pin_to_net_inductor') {
    base.pin = r.pin.trim()
    base.net = r.net.trim()
    if (r.min_value.trim()) base.min_value = r.min_value.trim()
    if (r.max_value.trim()) base.max_value = r.max_value.trim()
  }
  return base
}

function buildRuleSet() {
  return {
    component: componentName.value.trim(),
    gnd_nets: gndNetsInput.value.split(',').map(s => s.trim()).filter(Boolean),
    rules: rules.map(buildRuleObj),
  }
}

const previewYaml = computed(() => {
  try { return jsYaml.dump(buildRuleSet(), { lineWidth: -1 }) } catch { return '' }
})

async function downloadYaml() {
  if (!componentName.value.trim()) return alert(t.value.yaml.alerts.noName)
  try {
    const res = await generateYaml(buildRuleSet())
    const blob = new Blob([res.data], { type: 'text/plain;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url; a.download = `${componentName.value.trim()}.yaml`; a.click()
    URL.revokeObjectURL(url)
  } catch (err) {
    alert(t.value.yaml.alerts.genFail + (err.response?.data?.detail || err.message))
  }
}

async function uploadToSession() {
  if (!componentName.value.trim()) return alert(t.value.yaml.alerts.noName)
  try {
    const res = await generateYaml(buildRuleSet())
    const filename = `${componentName.value.trim()}.yaml`
    const file = new File([res.data], filename, { type: 'text/plain' })
    const uploadRes = await uploadYAML([file])
    const { loaded, errors } = uploadRes.data
    store.addYamlFiles(loaded)
    if (errors.length) alert(t.value.yaml.alerts.uploadFail + errors.map(e => e.error).join('\n'))
    else alert(filename + t.value.yaml.alerts.uploadOk)
  } catch (err) {
    alert(t.value.yaml.alerts.uploadFail + (err.response?.data?.detail || err.message))
  }
}

async function loadFromSessionFile() {
  if (!loadFromSession.value) return
  try {
    const res = await getYamlContent(loadFromSession.value)
    applyYamlData(jsYaml.load(res.data))
  } catch (err) { alert(t.value.yaml.alerts.parseFail + err.message) }
}

function loadFromFile(e) {
  const file = e.target.files[0]
  if (!file) return
  const reader = new FileReader()
  reader.onload = (ev) => {
    try { applyYamlData(jsYaml.load(ev.target.result)) }
    catch (err) { alert(t.value.yaml.alerts.parseFail + err.message) }
  }
  reader.readAsText(file)
  e.target.value = ''
}

function applyYamlData(data) {
  componentName.value = data.component || ''
  gndNetsInput.value  = (data.gnd_nets || ['GND']).join(', ')
  rules.splice(0)
  for (const r of data.rules || []) {
    rules.push({
      type: r.type, severity: r.severity || 'error', description: r.description || '',
      count: (r.count || []).join(', '), pin1: r.pin1 || '', pin2: r.pin2 || '',
      pin: r.pin || '', capacitance: r.capacitance || '',
      net: r.net || '', min_value: r.min_value || '', max_value: r.max_value || '',
    })
  }
}
</script>

<template>
  <div class="yaml-page">
    <div class="page-header">
      <h2>{{ t.yaml.title }}</h2>
      <p class="hint">{{ t.yaml.hint }}</p>
    </div>

    <!-- Load bar -->
    <div class="load-bar">
      <span class="load-label">{{ t.yaml.loadLabel }}</span>
      <select v-model="loadFromSession" @change="loadFromSessionFile" class="a-select">
        <option value="">{{ t.yaml.loadSession }}</option>
        <option v-for="f in store.yamlFiles" :key="f" :value="f">{{ f }}</option>
      </select>
      <span class="sep">or</span>
      <input type="file" id="yaml-load" accept=".yaml,.yml" hidden @change="loadFromFile" />
      <button class="btn btn-ghost sm" @click="() => document.getElementById('yaml-load').click()">
        {{ t.yaml.loadLocal }}
      </button>
    </div>

    <!-- Component info -->
    <div class="form-row-group">
      <div class="form-field">
        <label>{{ t.yaml.compName }}</label>
        <input v-model="componentName" class="a-input" :placeholder="t.yaml.compNamePh" />
      </div>
      <div class="form-field grow">
        <label>{{ t.yaml.gndNets }}</label>
        <input v-model="gndNetsInput" class="a-input" :placeholder="t.yaml.gndNetsPh" />
      </div>
    </div>

    <!-- Rules header -->
    <div class="rules-bar">
      <span class="rules-title">{{ t.yaml.rulesTitle }} ({{ rules.length }})</span>
      <button class="btn btn-primary sm" @click="addRule">{{ t.yaml.addRule }}</button>
    </div>

    <div v-if="!rules.length" class="no-rules">{{ t.yaml.noRules }}</div>

    <!-- Rule cards -->
    <div v-for="(r, idx) in rules" :key="idx" class="rule-card">
      <div class="rule-head">
        <span class="rule-num">#{{ idx + 1 }}</span>
        <select v-model="r.type" class="a-select type-sel">
          <option v-for="tp in t.yaml.ruleTypes" :key="tp.value" :value="tp.value">
            {{ tp.label }}
          </option>
        </select>
        <select v-model="r.severity" class="a-select sev-sel" :class="'sev-' + r.severity">
          <option value="error">ERROR</option>
          <option value="warning">WARNING</option>
        </select>
        <button class="del-btn" @click="removeRule(idx)">✕</button>
      </div>

      <div class="rule-fields">
        <template v-if="r.type === 'pin_count'">
          <div class="rf">
            <label>{{ t.yaml.fields.validPins }}</label>
            <input v-model="r.count" class="a-input" :placeholder="t.yaml.fields.pinsPh" />
          </div>
        </template>

        <template v-else-if="r.type === 'pin_to_pin_connection'">
          <div class="rf short">
            <label>{{ t.yaml.fields.pin1 }}</label>
            <input v-model="r.pin1" class="a-input" placeholder="e.g. 16" />
          </div>
          <div class="rf short">
            <label>{{ t.yaml.fields.pin2 }}</label>
            <input v-model="r.pin2" class="a-input" placeholder="e.g. 22" />
          </div>
        </template>

        <template v-else-if="r.type === 'pin_to_gnd_cap'">
          <div class="rf short">
            <label>{{ t.yaml.fields.pin }}</label>
            <input v-model="r.pin" class="a-input" placeholder="e.g. 16" />
          </div>
          <div class="rf short">
            <label>{{ t.yaml.fields.cap }}</label>
            <input v-model="r.capacitance" class="a-input" :placeholder="t.yaml.fields.capPh" />
          </div>
        </template>

        <template v-else-if="r.type === 'pin_to_pin_cap'">
          <div class="rf short">
            <label>{{ t.yaml.fields.pin1 }}</label>
            <input v-model="r.pin1" class="a-input" placeholder="e.g. 27" />
          </div>
          <div class="rf short">
            <label>{{ t.yaml.fields.pin2 }}</label>
            <input v-model="r.pin2" class="a-input" placeholder="e.g. 28" />
          </div>
          <div class="rf short">
            <label>{{ t.yaml.fields.cap }}</label>
            <input v-model="r.capacitance" class="a-input" :placeholder="t.yaml.fields.capPh" />
          </div>
        </template>

        <template v-else-if="r.type === 'pin_floating'">
          <div class="rf short">
            <label>{{ t.yaml.fields.pin }}</label>
            <input v-model="r.pin" class="a-input" placeholder="e.g. 5" />
          </div>
        </template>

        <template v-else-if="r.type === 'pin_to_net_resistor' || r.type === 'pin_to_net_capacitor' || r.type === 'pin_to_net_inductor'">
          <div class="rf short">
            <label>{{ t.yaml.fields.pin }}</label>
            <input v-model="r.pin" class="a-input" placeholder="e.g. 5" />
          </div>
          <div class="rf short">
            <label>{{ t.yaml.fields.net }}</label>
            <input v-model="r.net" class="a-input" :placeholder="t.yaml.fields.netPh" />
          </div>
          <div class="rf short">
            <label>{{ t.yaml.fields.minValue }}</label>
            <input v-model="r.min_value" class="a-input"
              :placeholder="r.type === 'pin_to_net_inductor' ? t.yaml.fields.indPh : r.type === 'pin_to_net_resistor' ? t.yaml.fields.resPh : t.yaml.fields.capPh" />
          </div>
          <div class="rf short">
            <label>{{ t.yaml.fields.maxValue }}</label>
            <input v-model="r.max_value" class="a-input"
              :placeholder="r.type === 'pin_to_net_inductor' ? t.yaml.fields.indPh : r.type === 'pin_to_net_resistor' ? t.yaml.fields.resPh : t.yaml.fields.capPh" />
          </div>
        </template>

        <div class="rf grow">
          <label>{{ t.yaml.fields.desc }}</label>
          <input v-model="r.description" class="a-input" :placeholder="t.yaml.fields.descPh" />
        </div>
      </div>
    </div>

    <!-- Preview -->
    <div v-if="rules.length || componentName" class="preview-wrap">
      <div class="preview-label">{{ t.yaml.preview }}</div>
      <pre class="preview">{{ previewYaml }}</pre>
    </div>

    <!-- Actions -->
    <div class="actions">
      <button class="btn btn-outline" @click="downloadYaml">{{ t.yaml.download }}</button>
      <button class="btn btn-primary" @click="uploadToSession">{{ t.yaml.uploadSession }}</button>
      <button v-if="store.canCheck" class="btn btn-ghost" @click="emit('go-next')">
        {{ t.yaml.next }}
      </button>
    </div>
  </div>
</template>

<style scoped>
.yaml-page { max-width: 860px; }

.page-header { margin-bottom: 20px; }
h2 { font-size: 18px; font-weight: 700; color: var(--text); margin-bottom: 6px; }
.hint { font-size: 13px; color: var(--text-sub); }

/* Load bar */
.load-bar {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 20px;
  padding: 10px 14px;
  background: var(--tbl-head-bg);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  flex-wrap: wrap;
}
.load-label { font-size: 13px; font-weight: 600; color: var(--text); white-space: nowrap; }
.sep { font-size: 12px; color: var(--text-sub); }

/* Shared input */
.a-select, .a-input {
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 7px 10px;
  font-size: 13px;
  background: #fff;
  outline: none;
  font-family: inherit;
  transition: border-color 0.15s;
}
.a-select:focus, .a-input:focus { border-color: var(--primary); }

/* Form fields */
.form-row-group {
  display: flex;
  gap: 16px;
  margin-bottom: 20px;
  flex-wrap: wrap;
}
.form-field { display: flex; flex-direction: column; gap: 5px; min-width: 200px; }
.form-field.grow { flex: 1; }
.form-field label { font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; color: var(--text-sub); }

/* Rules */
.rules-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}
.rules-title { font-size: 13px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; color: var(--text-sub); }
.no-rules { color: #C8CDD6; font-size: 13px; padding: 16px 0; }

.rule-card {
  border: 1px solid var(--border);
  border-radius: var(--radius);
  margin-bottom: 10px;
  overflow: hidden;
}
.rule-head {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: var(--tbl-head-bg);
  border-bottom: 1px solid var(--border);
}
.rule-num { font-size: 11px; font-weight: 700; color: #C8CDD6; width: 26px; }
.type-sel { flex: 1; font-size: 12px; }
.sev-sel  { font-size: 12px; font-weight: 700; width: 100px; }
.sev-error   { color: #C0392B; border-color: #F5C6C6; background: #FFF5F5; }
.sev-warning { color: #B07700; border-color: #FFE5A0; background: #FFFDE7; }
.del-btn { background: none; border: none; color: #C8CDD6; font-size: 13px; padding: 4px 6px; }
.del-btn:hover { color: #E84040; }

.rule-fields {
  display: flex;
  gap: 14px;
  padding: 12px 14px;
  flex-wrap: wrap;
  align-items: flex-end;
}
.rf { display: flex; flex-direction: column; gap: 4px; }
.rf.grow  { flex: 1; min-width: 180px; }
.rf.short { }
.rf label { font-size: 11px; font-weight: 600; color: var(--text-sub); text-transform: uppercase; letter-spacing: 0.4px; }
.rf .a-input { min-width: 80px; }

/* Preview */
.preview-wrap { margin: 16px 0; }
.preview-label { font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; color: var(--text-sub); margin-bottom: 6px; }
.preview {
  background: #1B1F2E;
  color: #CBD6F0;
  border-radius: 6px;
  padding: 14px 16px;
  font-size: 12px;
  font-family: ui-monospace, Consolas, monospace;
  line-height: 1.65;
  white-space: pre-wrap;
  max-height: 280px;
  overflow-y: auto;
}

/* Actions */
.actions { display: flex; gap: 10px; margin-top: 8px; flex-wrap: wrap; }
.sm { padding: 6px 14px; font-size: 12px; }
</style>
