<script setup>
import { ref, reactive, computed } from 'vue'
import jsYaml from 'js-yaml'
import { useAppStore } from '../stores/appStore'
import { generateYaml, uploadYAML, getYamlContent } from '../api'

const emit = defineEmits(['go-next'])
const store = useAppStore()

const componentName = ref('')
const gndNetsInput = ref('GND, PGND')
const rules = reactive([])
const loadFromSession = ref('')

const RULE_TYPES = [
  { value: 'pin_count',           label: 'pin_count - 總 PIN 數驗證' },
  { value: 'pin_to_pin_connection', label: 'pin_to_pin_connection - 兩 PIN 相連' },
  { value: 'pin_to_gnd_cap',      label: 'pin_to_gnd_cap - PIN 接電容到 GND' },
  { value: 'pin_to_pin_cap',      label: 'pin_to_pin_cap - 兩 PIN 間接電容' },
]

function addRule() {
  rules.push({
    type: 'pin_to_pin_connection',
    severity: 'error',
    description: '',
    // pin_count
    count: '52, 53',
    // pin_to_pin_connection / pin_to_pin_cap
    pin1: '',
    pin2: '',
    // pin_to_gnd_cap
    pin: '',
    // pin_to_gnd_cap / pin_to_pin_cap
    capacitance: '',
  })
}

function removeRule(idx) {
  rules.splice(idx, 1)
}

function buildRuleObj(r) {
  const base = { type: r.type, severity: r.severity }
  if (r.description.trim()) base.description = r.description.trim()
  if (r.type === 'pin_count') {
    base.count = r.count.split(',').map(s => parseInt(s.trim())).filter(n => !isNaN(n))
  } else if (r.type === 'pin_to_pin_connection') {
    base.pin1 = r.pin1.trim()
    base.pin2 = r.pin2.trim()
  } else if (r.type === 'pin_to_gnd_cap') {
    base.pin = r.pin.trim()
    base.capacitance = r.capacitance.trim()
  } else if (r.type === 'pin_to_pin_cap') {
    base.pin1 = r.pin1.trim()
    base.pin2 = r.pin2.trim()
    base.capacitance = r.capacitance.trim()
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
  try {
    return jsYaml.dump(buildRuleSet(), { lineWidth: -1 })
  } catch {
    return ''
  }
})

async function downloadYaml() {
  if (!componentName.value.trim()) return alert('請輸入元件名稱')
  try {
    const res = await generateYaml(buildRuleSet())
    const blob = new Blob([res.data], { type: 'text/plain;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${componentName.value.trim()}.yaml`
    a.click()
    URL.revokeObjectURL(url)
  } catch (err) {
    alert('產生 YAML 失敗：' + (err.response?.data?.detail || err.message))
  }
}

async function uploadToSession() {
  if (!componentName.value.trim()) return alert('請輸入元件名稱')
  try {
    const res = await generateYaml(buildRuleSet())
    const yamlText = res.data
    const filename = `${componentName.value.trim()}.yaml`
    const blob = new Blob([yamlText], { type: 'text/plain' })
    const file = new File([blob], filename, { type: 'text/plain' })
    const uploadRes = await uploadYAML([file])
    const { loaded, errors } = uploadRes.data
    store.addYamlFiles(loaded)
    if (errors.length) {
      alert('上傳失敗：' + errors.map(e => e.error).join('\n'))
    } else {
      alert(`已將 ${filename} 上傳至工作階段`)
    }
  } catch (err) {
    alert('上傳失敗：' + (err.response?.data?.detail || err.message))
  }
}

async function loadFromSessionFile() {
  if (!loadFromSession.value) return
  try {
    const res = await getYamlContent(loadFromSession.value)
    const data = jsYaml.load(res.data)
    componentName.value = data.component || ''
    gndNetsInput.value = (data.gnd_nets || ['GND']).join(', ')
    rules.splice(0)
    for (const r of data.rules || []) {
      const row = {
        type: r.type,
        severity: r.severity || 'error',
        description: r.description || '',
        count: (r.count || []).join(', '),
        pin1: r.pin1 || '',
        pin2: r.pin2 || '',
        pin: r.pin || '',
        capacitance: r.capacitance || '',
      }
      rules.push(row)
    }
  } catch (err) {
    alert('載入失敗：' + err.message)
  }
}

function loadFromFile(e) {
  const file = e.target.files[0]
  if (!file) return
  const reader = new FileReader()
  reader.onload = (ev) => {
    try {
      const data = jsYaml.load(ev.target.result)
      componentName.value = data.component || ''
      gndNetsInput.value = (data.gnd_nets || ['GND']).join(', ')
      rules.splice(0)
      for (const r of data.rules || []) {
        rules.push({
          type: r.type,
          severity: r.severity || 'error',
          description: r.description || '',
          count: (r.count || []).join(', '),
          pin1: r.pin1 || '',
          pin2: r.pin2 || '',
          pin: r.pin || '',
          capacitance: r.capacitance || '',
        })
      }
    } catch (err) {
      alert('解析 YAML 失敗：' + err.message)
    }
  }
  reader.readAsText(file)
  e.target.value = ''
}
</script>

<template>
  <div class="yaml-gen-page">
    <h2>YAML 規則產生器</h2>
    <p class="hint">設計元件規則並下載或上傳至工作階段。也可載入已有的 YAML 進行編輯。</p>

    <div class="load-bar">
      <span class="load-label">載入現有 YAML：</span>
      <select v-model="loadFromSession" @change="loadFromSessionFile" class="sel">
        <option value="">從工作階段選擇…</option>
        <option v-for="f in store.yamlFiles" :key="f" :value="f">{{ f }}</option>
      </select>
      <span style="color:#999;font-size:12px">或</span>
      <input type="file" id="yaml-load" accept=".yaml,.yml" hidden @change="loadFromFile" />
      <button class="sm-btn" @click="() => document.getElementById('yaml-load').click()">從本機載入</button>
    </div>

    <div class="form-section">
      <div class="form-row">
        <label>元件名稱</label>
        <input v-model="componentName" class="text-input" placeholder="例：TDM24544" />
      </div>
      <div class="form-row">
        <label>GND 網路名稱</label>
        <input v-model="gndNetsInput" class="text-input" placeholder="以逗號分隔，例：GND, PGND" />
      </div>
    </div>

    <div class="rules-header">
      <span class="rules-title">規則列表 ({{ rules.length }} 條)</span>
      <button class="add-btn" @click="addRule">+ 新增規則</button>
    </div>

    <div v-if="!rules.length" class="no-rules">尚未新增規則，點擊「新增規則」開始。</div>

    <div v-for="(r, idx) in rules" :key="idx" class="rule-card">
      <div class="rule-card-head">
        <span class="rule-num">#{{ idx + 1 }}</span>
        <select v-model="r.type" class="type-sel">
          <option v-for="t in RULE_TYPES" :key="t.value" :value="t.value">{{ t.label }}</option>
        </select>
        <select v-model="r.severity" class="sev-sel" :class="'sev-' + r.severity">
          <option value="error">ERROR</option>
          <option value="warning">WARNING</option>
        </select>
        <button class="del-btn" @click="removeRule(idx)">✕</button>
      </div>

      <div class="rule-fields">
        <!-- pin_count -->
        <template v-if="r.type === 'pin_count'">
          <div class="field">
            <label>有效 PIN 數（逗號分隔）</label>
            <input v-model="r.count" class="field-input" placeholder="例：52, 53" />
          </div>
        </template>

        <!-- pin_to_pin_connection -->
        <template v-else-if="r.type === 'pin_to_pin_connection'">
          <div class="field">
            <label>PIN 1</label>
            <input v-model="r.pin1" class="field-input short" placeholder="例：16" />
          </div>
          <div class="field">
            <label>PIN 2</label>
            <input v-model="r.pin2" class="field-input short" placeholder="例：22" />
          </div>
        </template>

        <!-- pin_to_gnd_cap -->
        <template v-else-if="r.type === 'pin_to_gnd_cap'">
          <div class="field">
            <label>PIN</label>
            <input v-model="r.pin" class="field-input short" placeholder="例：16" />
          </div>
          <div class="field">
            <label>電容值</label>
            <input v-model="r.capacitance" class="field-input short" placeholder="例：2.2uF" />
          </div>
        </template>

        <!-- pin_to_pin_cap -->
        <template v-else-if="r.type === 'pin_to_pin_cap'">
          <div class="field">
            <label>PIN 1</label>
            <input v-model="r.pin1" class="field-input short" placeholder="例：27" />
          </div>
          <div class="field">
            <label>PIN 2</label>
            <input v-model="r.pin2" class="field-input short" placeholder="例：28" />
          </div>
          <div class="field">
            <label>電容值</label>
            <input v-model="r.capacitance" class="field-input short" placeholder="例：220pF" />
          </div>
        </template>

        <div class="field full">
          <label>描述（選填）</label>
          <input v-model="r.description" class="field-input" placeholder="規則說明" />
        </div>
      </div>
    </div>

    <div v-if="rules.length || componentName" class="preview-section">
      <div class="preview-label">YAML 預覽</div>
      <pre class="preview">{{ previewYaml }}</pre>
    </div>

    <div class="actions">
      <button class="action-btn download" @click="downloadYaml">↓ 下載 YAML</button>
      <button class="action-btn upload" @click="uploadToSession">↑ 上傳至工作階段</button>
      <button v-if="store.canCheck" class="action-btn next" @click="emit('go-next')">
        下一步：IC 對應設定 →
      </button>
    </div>
  </div>
</template>

<style scoped>
.yaml-gen-page { max-width: 860px; }
h2 { font-size: 18px; margin-bottom: 6px; color: #1a73e8; }
.hint { color: #666; font-size: 14px; margin-bottom: 16px; }

.load-bar {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 20px;
  padding: 10px 14px;
  background: #f8f9fa;
  border-radius: 8px;
  border: 1px solid #e0e0e0;
  flex-wrap: wrap;
}
.load-label { font-size: 13px; font-weight: 500; color: #444; }
.sel {
  border: 1px solid #ccc;
  border-radius: 6px;
  padding: 5px 8px;
  font-size: 13px;
}
.sm-btn {
  background: #fff;
  border: 1px solid #1a73e8;
  color: #1a73e8;
  border-radius: 6px;
  padding: 5px 12px;
  font-size: 12px;
}

.form-section {
  display: flex;
  gap: 20px;
  margin-bottom: 20px;
  flex-wrap: wrap;
}
.form-row { display: flex; flex-direction: column; gap: 4px; flex: 1; min-width: 220px; }
.form-row label { font-size: 12px; font-weight: 600; color: #555; }
.text-input {
  border: 1px solid #ccc;
  border-radius: 6px;
  padding: 7px 10px;
  font-size: 13px;
}

.rules-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
}
.rules-title { font-weight: 600; font-size: 14px; }
.add-btn {
  background: #1a73e8;
  color: #fff;
  border: none;
  border-radius: 6px;
  padding: 6px 14px;
  font-size: 13px;
}
.add-btn:hover { background: #1558b0; }

.no-rules { color: #aaa; font-size: 13px; padding: 20px 0; }

.rule-card {
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  margin-bottom: 10px;
  overflow: hidden;
}
.rule-card-head {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: #f5f5f5;
  border-bottom: 1px solid #e0e0e0;
}
.rule-num { font-size: 12px; color: #999; font-weight: 600; width: 24px; }
.type-sel {
  flex: 1;
  border: 1px solid #ccc;
  border-radius: 5px;
  padding: 4px 8px;
  font-size: 13px;
}
.sev-sel {
  border: 1px solid #ccc;
  border-radius: 5px;
  padding: 4px 8px;
  font-size: 12px;
  font-weight: 600;
}
.sev-error { color: #c62828; border-color: #ef9a9a; background: #fff8f8; }
.sev-warning { color: #f57f17; border-color: #ffe082; background: #fffde7; }
.del-btn {
  background: none;
  border: none;
  color: #bbb;
  font-size: 14px;
  padding: 4px 6px;
}
.del-btn:hover { color: #e53935; }

.rule-fields {
  display: flex;
  gap: 16px;
  padding: 12px 14px;
  flex-wrap: wrap;
  align-items: flex-end;
}
.field { display: flex; flex-direction: column; gap: 4px; }
.field.full { flex: 1; min-width: 200px; }
.field label { font-size: 11px; font-weight: 600; color: #666; }
.field-input {
  border: 1px solid #ccc;
  border-radius: 5px;
  padding: 5px 8px;
  font-size: 13px;
  width: 100%;
}
.field-input.short { width: 90px; }

.preview-section { margin: 16px 0; }
.preview-label { font-size: 12px; font-weight: 600; color: #555; margin-bottom: 6px; }
.preview {
  background: #1e1e2e;
  color: #cdd6f4;
  border-radius: 8px;
  padding: 14px 16px;
  font-size: 12px;
  font-family: ui-monospace, Consolas, monospace;
  line-height: 1.6;
  white-space: pre-wrap;
  max-height: 300px;
  overflow-y: auto;
}

.actions { display: flex; gap: 10px; margin-top: 8px; flex-wrap: wrap; }
.action-btn {
  border: none;
  border-radius: 6px;
  padding: 9px 20px;
  font-size: 13px;
  font-weight: 600;
}
.download { background: #e8f0fe; color: #1a73e8; border: 1px solid #1a73e8; }
.download:hover { background: #d2e3fc; }
.upload { background: #e6f4ea; color: #34a853; border: 1px solid #34a853; }
.upload:hover { background: #ceead6; }
.next { background: #34a853; color: #fff; }
.next:hover { background: #2d8f47; }
</style>
