<script setup>
import { ref, computed, watch } from 'vue'
import jsyaml from 'js-yaml'
import { useAppStore } from '../stores/appStore'
import { useT } from '../i18n'
import { uploadSpec, getRailSpecContent } from '../api'

const store = useAppStore()
const t = useT()

// ── State ──────────────────────────────────────────────────────────────────
const railName   = ref('')
const refDes     = ref('')
const component  = ref('')
const specs      = ref([])  // [{key, value}]
const extraVars  = ref([])  // [{key, value}]

const yamlPreview = ref('')
const alertMsg  = ref('')
const alertType = ref('info')
const isUploading = ref(false)

// ── Load from session ──────────────────────────────────────────────────────
const sessionRailSpecs = computed(() => store.railSpecs)
const selectedSession  = ref('')

async function loadFromSession() {
  if (!selectedSession.value) return
  try {
    const res = await getRailSpecContent(selectedSession.value)
    importFromYaml(res.data)
  } catch (e) {
    showAlert(t.value.spec.rail.alerts.loadFail + e.message, 'error')
  }
}

function importFromYaml(yamlText) {
  try {
    const data = jsyaml.load(yamlText)
    railName.value  = data.rail_name  || ''
    refDes.value    = data.ref_des    || ''
    component.value = data.component  || ''
    specs.value = Object.entries(data.specifications || {}).map(([k, v]) => ({ key: k, value: v || '' }))
    extraVars.value = Object.entries(data.variables || {}).map(([k, v]) => ({ key: k, value: v || '' }))
    refreshPreview()
  } catch (e) {
    showAlert(t.value.spec.rail.alerts.parseFail + e.message, 'error')
  }
}

// ── Load from local file ───────────────────────────────────────────────────
const fileInput = ref(null)
function loadFromFile() { fileInput.value?.click() }
function onFileChange(e) {
  const f = e.target.files[0]
  if (!f) return
  const reader = new FileReader()
  reader.onload = ev => importFromYaml(ev.target.result)
  reader.readAsText(f)
  e.target.value = ''
}

// ── Spec row management ────────────────────────────────────────────────────
function addSpec() {
  specs.value.push({ key: '', value: '' })
  refreshPreview()
}
function removeSpec(idx) {
  specs.value.splice(idx, 1)
  refreshPreview()
}

function addVar() {
  extraVars.value.push({ key: '', value: '' })
  refreshPreview()
}
function removeVar(idx) {
  extraVars.value.splice(idx, 1)
  refreshPreview()
}

// Common spec suggestions
const specSuggestions = ['vout', 'vin', 'fsw', 'ocp', 'ocp_threshold', 'i2c_address', 'phases']

// ── YAML generation ────────────────────────────────────────────────────────
function buildData() {
  const specifications = {}
  for (const s of specs.value) {
    if (s.key.trim()) specifications[s.key.trim()] = s.value.trim()
  }
  const variables = {}
  for (const v of extraVars.value) {
    if (v.key.trim()) variables[v.key.trim()] = v.value.trim()
  }
  const data = {
    rail_name: railName.value.trim(),
    ref_des: refDes.value.trim(),
    component: component.value.trim(),
    specifications,
  }
  if (Object.keys(variables).length > 0) data.variables = variables
  return data
}

function refreshPreview() {
  try {
    const data = buildData()
    yamlPreview.value = jsyaml.dump(data, { lineWidth: 120, quotingType: '"', noRefs: true })
  } catch (e) {
    yamlPreview.value = '# Error: ' + e.message
  }
}

watch([railName, refDes, component, specs, extraVars], refreshPreview, { deep: true })

// ── Download ───────────────────────────────────────────────────────────────
function download() {
  const name = railName.value.trim() || refDes.value.trim()
  if (!name) { showAlert(t.value.spec.rail.alerts.noName, 'error'); return }
  const blob = new Blob([yamlPreview.value], { type: 'text/plain' })
  const a = document.createElement('a')
  a.href = URL.createObjectURL(blob)
  a.download = `${name}.spec`
  a.click()
}

// ── Upload to session ──────────────────────────────────────────────────────
async function uploadToSession() {
  const name = railName.value.trim() || refDes.value.trim()
  if (!name) { showAlert(t.value.spec.rail.alerts.noName, 'error'); return }
  isUploading.value = true
  try {
    const blob = new Blob([yamlPreview.value], { type: 'text/plain' })
    const f = new File([blob], `${name}.spec`)
    const res = await uploadSpec([f])
    const { rail_specs = [], errors = [] } = res.data
    if (errors.length) throw new Error(errors[0].error)
    store.addSpecs({ rail_specs })
    showAlert(`${name}.spec` + t.value.spec.rail.alerts.uploadOk, 'ok')
  } catch (e) {
    showAlert(t.value.spec.rail.alerts.uploadFail + e.message, 'error')
  } finally {
    isUploading.value = false
  }
}

function showAlert(msg, type = 'info') {
  alertMsg.value = msg
  alertType.value = type
  setTimeout(() => { alertMsg.value = '' }, 4000)
}
</script>

<template>
  <div class="rse-editor">
    <!-- Load bar -->
    <div class="load-bar">
      <span class="load-label">{{ t.spec.rail.loadLabel }}</span>
      <select v-model="selectedSession" class="sel-session">
        <option value="">{{ t.spec.rail.loadSession }}</option>
        <option v-for="s in sessionRailSpecs" :key="s.filename" :value="s.filename">
          {{ s.filename }} ({{ s.refDes }})
        </option>
      </select>
      <button class="btn-sm" :disabled="!selectedSession" @click="loadFromSession">{{ t.spec.rail.loadBtn }}</button>
      <span class="sep">|</span>
      <button class="btn-sm" @click="loadFromFile">{{ t.spec.rail.loadLocal }}</button>
      <input ref="fileInput" type="file" accept=".spec,.yaml,.yml" style="display:none" @change="onFileChange" />
    </div>

    <!-- Alert -->
    <div v-if="alertMsg" :class="['alert', `alert-${alertType}`]">{{ alertMsg }}</div>

    <div class="editor-body">
      <!-- Left: form -->
      <div class="form-col">
        <!-- Header fields -->
        <div class="fields-grid">
          <div class="field-group">
            <label class="field-label">{{ t.spec.rail.railName }}</label>
            <input v-model="railName" class="input-field" :placeholder="t.spec.rail.railNamePh" />
          </div>
          <div class="field-group">
            <label class="field-label">{{ t.spec.rail.refDes }}</label>
            <input v-model="refDes" class="input-field" :placeholder="t.spec.rail.refDesPh" />
          </div>
          <div class="field-group span2">
            <label class="field-label">{{ t.spec.rail.component }}</label>
            <input v-model="component" class="input-field" :placeholder="t.spec.rail.compPh" />
          </div>
        </div>

        <!-- Specifications -->
        <div class="section-title">{{ t.spec.rail.specsTitle }}</div>
        <div class="spec-hint">{{ t.spec.rail.specsHint }}</div>

        <div v-for="(s, idx) in specs" :key="idx" class="kv-row">
          <div class="kv-key-wrap">
            <input v-model="s.key" class="input-sm" :placeholder="t.spec.rail.keyPh" list="spec-suggestions" />
            <datalist id="spec-suggestions">
              <option v-for="sg in specSuggestions" :key="sg" :value="sg" />
            </datalist>
          </div>
          <span class="colon">:</span>
          <input v-model="s.value" class="input-sm flex1" :placeholder="t.spec.rail.valuePh" />
          <button class="btn-remove-sm" @click="removeSpec(idx)">✕</button>
        </div>
        <button class="btn-add-row" @click="addSpec">+ {{ t.spec.rail.addSpec }}</button>

        <!-- Extra variables (optional) -->
        <div class="section-title mt">{{ t.spec.rail.varsTitle }}</div>
        <div v-for="(v, idx) in extraVars" :key="idx" class="kv-row">
          <input v-model="v.key" class="input-sm" :placeholder="t.spec.rail.keyPh" />
          <span class="colon">:</span>
          <input v-model="v.value" class="input-sm flex1" :placeholder="t.spec.rail.valuePh" />
          <button class="btn-remove-sm" @click="removeVar(idx)">✕</button>
        </div>
        <button class="btn-add-row" @click="addVar">+ {{ t.spec.rail.addVar }}</button>
      </div>

      <!-- Right: YAML preview -->
      <div class="preview-col">
        <div class="preview-title">{{ t.spec.rail.preview }}</div>
        <pre class="yaml-pre">{{ yamlPreview }}</pre>
        <div class="action-row">
          <button class="btn-primary" @click="download">{{ t.spec.rail.download }}</button>
          <button class="btn-secondary" :disabled="isUploading" @click="uploadToSession">
            {{ isUploading ? t.spec.rail.uploading : t.spec.rail.uploadSession }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.rse-editor { display: flex; flex-direction: column; gap: 16px; }

.load-bar {
  display: flex; align-items: center; gap: 8px;
  padding: 10px 14px; background: var(--card); border: 1px solid var(--border);
  border-radius: var(--radius); flex-wrap: wrap;
}
.load-label { font-size: 12px; font-weight: 600; color: var(--text-sub); white-space: nowrap; }
.sep { color: var(--border); }
.sel-session { font-size: 12px; border: 1px solid var(--border); border-radius: 4px; padding: 4px 8px; min-width: 180px; }
.btn-sm {
  font-size: 12px; padding: 4px 12px; border: 1.5px solid var(--border); border-radius: 4px;
  background: #fff; cursor: pointer; white-space: nowrap; color: var(--text);
}
.btn-sm:hover:not(:disabled) { border-color: var(--primary); color: var(--primary); }
.btn-sm:disabled { color: #bbb; cursor: not-allowed; }

.alert { padding: 8px 14px; border-radius: var(--radius); font-size: 13px; }
.alert-ok { background: #e6f7f2; color: #007a52; border: 1px solid #a3d9c5; }
.alert-error { background: #fff0ee; color: #c0392b; border: 1px solid #f5bdb7; }
.alert-info { background: #e8f0fe; color: #1a73e8; border: 1px solid #aecbfa; }

.editor-body { display: flex; gap: 20px; align-items: flex-start; }
.form-col { flex: 1; display: flex; flex-direction: column; gap: 10px; min-width: 0; }
.preview-col { flex: 1; display: flex; flex-direction: column; gap: 10px; min-width: 0; }

.fields-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
.span2 { grid-column: span 2; }
.field-group { display: flex; flex-direction: column; gap: 4px; }
.field-label { font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: .4px; color: var(--text-sub); }
.input-field {
  border: 1.5px solid var(--border); border-radius: var(--radius); padding: 7px 10px;
  font-size: 13px; color: var(--text); width: 100%; box-sizing: border-box;
}
.input-field:focus { outline: none; border-color: var(--primary); }

.section-title { font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: .5px; color: var(--text-sub); border-bottom: 1px solid var(--border); padding-bottom: 6px; }
.section-title.mt { margin-top: 8px; }
.spec-hint { font-size: 11px; color: var(--text-muted); }

.kv-row { display: flex; align-items: center; gap: 6px; }
.kv-key-wrap { display: flex; flex-direction: column; }
.input-sm {
  border: 1.5px solid var(--border); border-radius: 4px; padding: 5px 8px;
  font-size: 12px; color: var(--text); min-width: 80px;
}
.input-sm:focus { outline: none; border-color: var(--primary); }
.input-sm.flex1 { flex: 1; }
.colon { color: var(--text-muted); font-weight: 600; }
.btn-remove-sm {
  background: none; border: none; color: #dc2626; cursor: pointer; font-size: 13px; padding: 2px 5px;
}
.btn-remove-sm:hover { color: #991b1b; }
.btn-add-row {
  font-size: 12px; color: var(--primary); background: none; border: none; cursor: pointer;
  text-align: left; padding: 2px 0; align-self: flex-start;
}

.preview-title { font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: .5px; color: var(--text-sub); }
.yaml-pre {
  font-family: 'JetBrains Mono', 'Fira Code', monospace; font-size: 12px; line-height: 1.6;
  background: #F8F9FC; border: 1px solid var(--border); border-radius: var(--radius);
  padding: 12px; overflow: auto; min-height: 260px; max-height: 500px; white-space: pre; color: #2d3748;
}

.action-row { display: flex; gap: 10px; flex-wrap: wrap; }
.btn-primary {
  padding: 8px 18px; background: var(--primary); color: #fff; border: none;
  border-radius: var(--radius); font-size: 13px; font-weight: 600; cursor: pointer;
}
.btn-primary:hover { opacity: .9; }
.btn-secondary {
  padding: 8px 18px; background: #fff; color: var(--primary);
  border: 1.5px solid var(--primary); border-radius: var(--radius); font-size: 13px; font-weight: 600; cursor: pointer;
}
.btn-secondary:hover:not(:disabled) { background: #f0f9ff; }
.btn-secondary:disabled { opacity: .5; cursor: not-allowed; }
</style>
