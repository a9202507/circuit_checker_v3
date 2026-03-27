<script setup>
import { ref, computed, watch } from 'vue'
import jsyaml from 'js-yaml'
import { useAppStore } from '../stores/appStore'
import { useT } from '../i18n'
import { uploadSpec, getIcSpecContent } from '../api'

const store = useAppStore()
const t = useT()

// ── State ──────────────────────────────────────────────────────────────────
const component = ref('')
const pinParams = ref([])   // [{key, name, type, specification, variables, options}]
// options entry: [{key, vars: [{varName, varValue}]}]

const yamlPreview = ref('')
const alertMsg = ref('')
const alertType = ref('info')  // 'info' | 'ok' | 'error'
const isUploading = ref(false)

// ── Load from session ──────────────────────────────────────────────────────
const sessionIcSpecs = computed(() => store.icSpecNames)
const selectedSession = ref('')

async function loadFromSession() {
  if (!selectedSession.value) return
  try {
    const res = await getIcSpecContent(selectedSession.value)
    importFromYaml(res.data)
  } catch (e) {
    showAlert(t.value.spec.ic.alerts.loadFail + e.message, 'error')
  }
}

function importFromYaml(yamlText) {
  try {
    const data = jsyaml.load(yamlText)
    component.value = data.component || ''
    pinParams.value = []
    for (const [key, pp] of Object.entries(data.pin_parameters || {})) {
      const entry = {
        key,
        name: pp.name || '',
        type: pp.type || 'resistor_to_gnd',
        specification: pp.specification || '',
        variables: Object.entries(pp.variables || {}).map(([k, v]) => ({ varName: k, varValue: v || '' })),
        options: Object.entries(pp.options || {}).map(([optKey, optVars]) => ({
          key: optKey,
          vars: Object.entries(optVars || {}).map(([k, v]) => ({ varName: k, varValue: v || '' })),
        })),
      }
      pinParams.value.push(entry)
    }
    refreshPreview()
  } catch (e) {
    showAlert(t.value.spec.ic.alerts.parseFail + e.message, 'error')
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

// ── Pin parameter management ───────────────────────────────────────────────
function addPinParam() {
  const idx = pinParams.value.length + 1
  pinParams.value.push({
    key: `pin${idx}`,
    name: '',
    type: 'resistor_to_gnd',
    specification: '',
    variables: [],
    options: [],
  })
  refreshPreview()
}

function removePinParam(idx) {
  pinParams.value.splice(idx, 1)
  refreshPreview()
}

function addOption(ppIdx) {
  pinParams.value[ppIdx].options.push({ key: '', vars: [{ varName: '', varValue: '' }] })
  refreshPreview()
}

function removeOption(ppIdx, optIdx) {
  pinParams.value[ppIdx].options.splice(optIdx, 1)
  refreshPreview()
}

function addOptionVar(ppIdx, optIdx) {
  pinParams.value[ppIdx].options[optIdx].vars.push({ varName: '', varValue: '' })
  refreshPreview()
}

function removeOptionVar(ppIdx, optIdx, varIdx) {
  pinParams.value[ppIdx].options[optIdx].vars.splice(varIdx, 1)
  refreshPreview()
}

function addFixedVar(ppIdx) {
  pinParams.value[ppIdx].variables.push({ varName: '', varValue: '' })
  refreshPreview()
}

function removeFixedVar(ppIdx, varIdx) {
  pinParams.value[ppIdx].variables.splice(varIdx, 1)
  refreshPreview()
}

// ── YAML generation ────────────────────────────────────────────────────────
function buildData() {
  const pin_parameters = {}
  for (const pp of pinParams.value) {
    const key = pp.key.trim()
    if (!key) continue
    const entry = { name: pp.name, type: pp.type }
    if (pp.type === 'resistor_to_gnd') {
      entry.specification = pp.specification
      const options = {}
      for (const opt of pp.options) {
        const vars = {}
        for (const v of opt.vars) {
          if (v.varName.trim()) vars[v.varName.trim()] = v.varValue.trim() || null
        }
        if (opt.key.trim()) options[opt.key.trim()] = vars
      }
      entry.options = options
    } else {
      const variables = {}
      for (const v of pp.variables) {
        if (v.varName.trim()) variables[v.varName.trim()] = v.varValue.trim() || null
      }
      entry.variables = variables
    }
    pin_parameters[key] = entry
  }
  return { component: component.value.trim(), pin_parameters }
}

function refreshPreview() {
  try {
    const data = buildData()
    yamlPreview.value = jsyaml.dump(data, { lineWidth: 120, quotingType: '"', noRefs: true })
  } catch (e) {
    yamlPreview.value = '# Error: ' + e.message
  }
}

watch([component, pinParams], refreshPreview, { deep: true })

// ── Download ───────────────────────────────────────────────────────────────
function download() {
  if (!component.value.trim()) { showAlert(t.value.spec.ic.alerts.noName, 'error'); return }
  const blob = new Blob([yamlPreview.value], { type: 'text/plain' })
  const a = document.createElement('a')
  a.href = URL.createObjectURL(blob)
  a.download = `${component.value.trim()}.spec`
  a.click()
}

// ── Upload to session ──────────────────────────────────────────────────────
async function uploadToSession() {
  if (!component.value.trim()) { showAlert(t.value.spec.ic.alerts.noName, 'error'); return }
  isUploading.value = true
  try {
    const blob = new Blob([yamlPreview.value], { type: 'text/plain' })
    const f = new File([blob], `${component.value.trim()}.spec`)
    const res = await uploadSpec([f])
    const { ic_specs = [], errors = [] } = res.data
    if (errors.length) throw new Error(errors[0].error)
    store.addSpecs({ ic_specs })
    showAlert(`${component.value.trim()}.spec` + t.value.spec.ic.alerts.uploadOk, 'ok')
  } catch (e) {
    showAlert(t.value.spec.ic.alerts.uploadFail + e.message, 'error')
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
  <div class="ice-editor">
    <!-- Load bar -->
    <div class="load-bar">
      <span class="load-label">{{ t.spec.ic.loadLabel }}</span>
      <select v-model="selectedSession" class="sel-session">
        <option value="">{{ t.spec.ic.loadSession }}</option>
        <option v-for="comp in sessionIcSpecs" :key="comp" :value="comp">{{ comp }}</option>
      </select>
      <button class="btn-sm" :disabled="!selectedSession" @click="loadFromSession">{{ t.spec.ic.loadBtn }}</button>
      <span class="sep">|</span>
      <button class="btn-sm" @click="loadFromFile">{{ t.spec.ic.loadLocal }}</button>
      <input ref="fileInput" type="file" accept=".spec,.yaml,.yml" style="display:none" @change="onFileChange" />
    </div>

    <!-- Alert -->
    <div v-if="alertMsg" :class="['alert', `alert-${alertType}`]">{{ alertMsg }}</div>

    <div class="editor-body">
      <!-- Left: form -->
      <div class="form-col">
        <!-- Component name -->
        <div class="field-group">
          <label class="field-label">{{ t.spec.ic.compName }}</label>
          <input v-model="component" class="input-field" :placeholder="t.spec.ic.compNamePh" @input="refreshPreview" />
        </div>

        <!-- Pin parameters -->
        <div class="section-title">{{ t.spec.ic.pinParams }}</div>

        <div v-for="(pp, ppIdx) in pinParams" :key="ppIdx" class="pin-param-card">
          <div class="pp-header">
            <div class="pp-header-fields">
              <input v-model="pp.key" class="input-sm" :placeholder="t.spec.ic.pinKey" @input="refreshPreview" />
              <input v-model="pp.name" class="input-sm flex1" :placeholder="t.spec.ic.pinName" @input="refreshPreview" />
              <select v-model="pp.type" class="sel-sm" @change="refreshPreview">
                <option value="resistor_to_gnd">resistor_to_gnd</option>
                <option value="fixed">fixed</option>
              </select>
            </div>
            <button class="btn-remove" @click="removePinParam(ppIdx)">✕</button>
          </div>

          <!-- resistor_to_gnd: specification + options -->
          <template v-if="pp.type === 'resistor_to_gnd'">
            <div class="sub-field">
              <label class="sub-label">{{ t.spec.ic.specification }}</label>
              <input v-model="pp.specification" class="input-sm" :placeholder="t.spec.ic.specPh" @input="refreshPreview" />
            </div>
            <div class="options-section">
              <div class="options-title">{{ t.spec.ic.options }}</div>
              <div v-for="(opt, optIdx) in pp.options" :key="optIdx" class="opt-row-group">
                <div class="opt-key-row">
                  <input v-model="opt.key" class="input-sm flex1" :placeholder="t.spec.ic.optKeyPh" @input="refreshPreview" />
                  <button class="btn-remove-sm" @click="removeOption(ppIdx, optIdx)">✕</button>
                </div>
                <div v-for="(v, vi) in opt.vars" :key="vi" class="var-row">
                  <input v-model="v.varName" class="input-sm" :placeholder="t.spec.ic.varName" @input="refreshPreview" />
                  <span class="arrow">→</span>
                  <input v-model="v.varValue" class="input-sm flex1" :placeholder="t.spec.ic.varValue" @input="refreshPreview" />
                  <button class="btn-remove-sm" @click="removeOptionVar(ppIdx, optIdx, vi)">✕</button>
                </div>
                <button class="btn-add-var" @click="addOptionVar(ppIdx, optIdx)">+ {{ t.spec.ic.addVar }}</button>
              </div>
              <button class="btn-add-opt" @click="addOption(ppIdx)">+ {{ t.spec.ic.addOption }}</button>
            </div>
          </template>

          <!-- fixed: variables -->
          <template v-else>
            <div class="options-section">
              <div class="options-title">{{ t.spec.ic.variables }}</div>
              <div v-for="(v, vi) in pp.variables" :key="vi" class="var-row">
                <input v-model="v.varName" class="input-sm" :placeholder="t.spec.ic.varName" @input="refreshPreview" />
                <span class="arrow">→</span>
                <input v-model="v.varValue" class="input-sm flex1" :placeholder="t.spec.ic.varValue" @input="refreshPreview" />
                <button class="btn-remove-sm" @click="removeFixedVar(ppIdx, vi)">✕</button>
              </div>
              <button class="btn-add-var" @click="addFixedVar(ppIdx)">+ {{ t.spec.ic.addVar }}</button>
            </div>
          </template>
        </div>

        <button class="btn-add-pp" @click="addPinParam">+ {{ t.spec.ic.addPinParam }}</button>
      </div>

      <!-- Right: YAML preview -->
      <div class="preview-col">
        <div class="preview-title">{{ t.spec.ic.preview }}</div>
        <pre class="yaml-pre">{{ yamlPreview }}</pre>
        <div class="action-row">
          <button class="btn-primary" @click="download">{{ t.spec.ic.download }}</button>
          <button class="btn-secondary" :disabled="isUploading" @click="uploadToSession">
            {{ isUploading ? t.spec.ic.uploading : t.spec.ic.uploadSession }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.ice-editor { display: flex; flex-direction: column; gap: 16px; }

.load-bar {
  display: flex; align-items: center; gap: 8px;
  padding: 10px 14px; background: var(--card); border: 1px solid var(--border);
  border-radius: var(--radius); flex-wrap: wrap;
}
.load-label { font-size: 12px; font-weight: 600; color: var(--text-sub); white-space: nowrap; }
.sep { color: var(--border); }
.sel-session { font-size: 12px; border: 1px solid var(--border); border-radius: 4px; padding: 4px 8px; min-width: 160px; }
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

.form-col { flex: 1; display: flex; flex-direction: column; gap: 12px; min-width: 0; }
.preview-col { flex: 1; display: flex; flex-direction: column; gap: 10px; min-width: 0; }

.field-group { display: flex; flex-direction: column; gap: 4px; }
.field-label { font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: .4px; color: var(--text-sub); }
.input-field {
  border: 1.5px solid var(--border); border-radius: var(--radius); padding: 7px 10px;
  font-size: 13px; color: var(--text); width: 100%; box-sizing: border-box;
}
.input-field:focus { outline: none; border-color: var(--primary); }

.section-title { font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: .5px; color: var(--text-sub); border-bottom: 1px solid var(--border); padding-bottom: 6px; }

.pin-param-card {
  border: 1.5px solid var(--border); border-radius: var(--radius); padding: 10px 12px;
  display: flex; flex-direction: column; gap: 8px; background: #fafbfc;
}
.pp-header { display: flex; align-items: center; gap: 8px; }
.pp-header-fields { display: flex; gap: 6px; flex: 1; align-items: center; }
.input-sm {
  border: 1.5px solid var(--border); border-radius: 4px; padding: 4px 8px;
  font-size: 12px; color: var(--text); min-width: 60px;
}
.input-sm:focus { outline: none; border-color: var(--primary); }
.input-sm.flex1 { flex: 1; }
.sel-sm {
  border: 1.5px solid var(--border); border-radius: 4px; padding: 4px 6px;
  font-size: 12px; color: var(--text);
}
.btn-remove {
  background: none; border: 1px solid #fca5a5; border-radius: 4px; color: #dc2626;
  font-size: 12px; padding: 3px 7px; cursor: pointer; flex-shrink: 0;
}
.btn-remove:hover { background: #fff0ee; }

.sub-field { display: flex; align-items: center; gap: 8px; }
.sub-label { font-size: 11px; color: var(--text-sub); white-space: nowrap; }

.options-section { display: flex; flex-direction: column; gap: 6px; padding-left: 8px; border-left: 2px solid var(--border); }
.options-title { font-size: 11px; font-weight: 600; color: var(--text-sub); }

.opt-row-group { display: flex; flex-direction: column; gap: 4px; padding: 6px 8px; background: #fff; border: 1px solid var(--border); border-radius: 4px; }
.opt-key-row { display: flex; gap: 6px; align-items: center; }
.var-row { display: flex; align-items: center; gap: 6px; padding-left: 8px; }
.arrow { color: var(--text-muted); font-size: 12px; flex-shrink: 0; }
.btn-remove-sm {
  background: none; border: none; color: #dc2626; cursor: pointer; font-size: 12px; padding: 2px 4px;
}
.btn-remove-sm:hover { color: #991b1b; }
.btn-add-var { font-size: 11px; color: var(--primary); background: none; border: none; cursor: pointer; text-align: left; padding: 2px 0; }
.btn-add-opt { font-size: 11px; color: var(--primary); background: none; border: none; cursor: pointer; text-align: left; padding: 2px 0; }
.btn-add-pp {
  font-size: 13px; padding: 7px 14px; border: 1.5px dashed var(--primary); border-radius: var(--radius);
  color: var(--primary); background: none; cursor: pointer; align-self: flex-start;
}
.btn-add-pp:hover { background: #f0f9ff; }

.preview-title { font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: .5px; color: var(--text-sub); }
.yaml-pre {
  font-family: 'JetBrains Mono', 'Fira Code', monospace; font-size: 11px; line-height: 1.6;
  background: #F8F9FC; border: 1px solid var(--border); border-radius: var(--radius);
  padding: 12px; overflow: auto; min-height: 300px; max-height: 500px; white-space: pre; color: #2d3748;
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
