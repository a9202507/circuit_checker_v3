<script setup>
import { ref } from 'vue'
import { useAppStore } from '../stores/appStore'
import { uploadASC, uploadBOM, uploadYAML } from '../api'

const emit = defineEmits(['go-next'])
const store = useAppStore()

const ascStatus = ref(null)   // null | 'loading' | 'ok' | 'error'
const bomStatus = ref(null)
const yamlStatus = ref(null)
const ascError = ref('')
const bomError = ref('')
const yamlError = ref('')
const ascFileName = ref('')
const bomFileName = ref('')
const yamlFileNames = ref([])

async function handleAsc(e) {
  const file = e.target.files[0]
  if (!file) return
  ascFileName.value = file.name
  ascStatus.value = 'loading'
  ascError.value = ''
  try {
    const res = await uploadASC(file)
    store.setAscLoaded(res.data)
    ascStatus.value = 'ok'
  } catch (err) {
    ascStatus.value = 'error'
    ascError.value = err.response?.data?.detail || err.message
  }
}

async function handleBom(e) {
  const file = e.target.files[0]
  if (!file) return
  bomFileName.value = file.name
  bomStatus.value = 'loading'
  bomError.value = ''
  try {
    await uploadBOM(file)
    store.setBomLoaded()
    bomStatus.value = 'ok'
  } catch (err) {
    bomStatus.value = 'error'
    bomError.value = err.response?.data?.detail || err.message
  }
}

async function handleYaml(e) {
  const files = Array.from(e.target.files)
  if (!files.length) return
  yamlStatus.value = 'loading'
  yamlError.value = ''
  try {
    const res = await uploadYAML(files)
    const { loaded, errors } = res.data
    store.addYamlFiles(loaded)
    yamlFileNames.value = [...new Set([...yamlFileNames.value, ...loaded])]
    if (errors.length) {
      yamlStatus.value = 'error'
      yamlError.value = errors.map(e => `${e.file}: ${e.error}`).join('\n')
    } else {
      yamlStatus.value = 'ok'
    }
  } catch (err) {
    yamlStatus.value = 'error'
    yamlError.value = err.response?.data?.detail || err.message
  }
}

function triggerInput(id) {
  document.getElementById(id).click()
}
</script>

<template>
  <div class="upload-page">
    <h2>上傳檔案</h2>
    <p class="hint">請依序上傳 Netlist (.asc)、BOM (.BOM) 及規則 YAML 檔案。</p>

    <div class="upload-grid">
      <!-- ASC -->
      <div class="upload-zone" :class="{ ok: ascStatus === 'ok', error: ascStatus === 'error' }">
        <div class="zone-icon">📄</div>
        <div class="zone-title">Netlist 檔案 (.asc)</div>
        <div class="zone-sub">PADS2000 格式，由 Allegro OrCAD 匯出</div>
        <input id="asc-input" type="file" accept=".asc,*/*" hidden @change="handleAsc" />
        <button class="upload-btn" @click="triggerInput('asc-input')">
          {{ ascStatus === 'loading' ? '上傳中…' : '選擇檔案' }}
        </button>
        <div v-if="ascFileName" class="file-name">{{ ascFileName }}</div>
        <div v-if="ascStatus === 'ok'" class="status-ok">✓ 已載入 {{ store.allRefs.length }} 個元件，{{ store.icRefs.length }} 個 IC</div>
        <div v-if="ascStatus === 'error'" class="status-err">✗ {{ ascError }}</div>
      </div>

      <!-- BOM -->
      <div class="upload-zone" :class="{ ok: bomStatus === 'ok', error: bomStatus === 'error' }">
        <div class="zone-icon">📋</div>
        <div class="zone-title">BOM 檔案 (.BOM)</div>
        <div class="zone-sub">Allegro OrCAD 匯出的 Bill of Materials</div>
        <input id="bom-input" type="file" accept=".BOM,.bom,.txt,*/*" hidden @change="handleBom" />
        <button class="upload-btn" @click="triggerInput('bom-input')">
          {{ bomStatus === 'loading' ? '上傳中…' : '選擇檔案' }}
        </button>
        <div v-if="bomFileName" class="file-name">{{ bomFileName }}</div>
        <div v-if="bomStatus === 'ok'" class="status-ok">✓ BOM 載入成功</div>
        <div v-if="bomStatus === 'error'" class="status-err">✗ {{ bomError }}</div>
      </div>

      <!-- YAML -->
      <div class="upload-zone" :class="{ ok: yamlStatus === 'ok', error: yamlStatus === 'error' }">
        <div class="zone-icon">⚙️</div>
        <div class="zone-title">規則 YAML 檔案</div>
        <div class="zone-sub">可一次選取多個 .yaml 規則檔</div>
        <input id="yaml-input" type="file" accept=".yaml,.yml" multiple hidden @change="handleYaml" />
        <button class="upload-btn" @click="triggerInput('yaml-input')">
          {{ yamlStatus === 'loading' ? '上傳中…' : '選擇檔案' }}
        </button>
        <div v-if="yamlFileNames.length" class="file-name">
          {{ yamlFileNames.join(', ') }}
        </div>
        <div v-if="yamlStatus === 'ok'" class="status-ok">✓ 已載入 {{ store.yamlFiles.length }} 個規則檔</div>
        <div v-if="yamlStatus === 'error'" class="status-err" style="white-space:pre-line">✗ {{ yamlError }}</div>
      </div>
    </div>

    <div class="actions">
      <button
        v-if="store.canCheck"
        class="next-btn"
        @click="emit('go-next')"
      >
        下一步：設定 IC 對應 →
      </button>
    </div>
  </div>
</template>

<style scoped>
.upload-page { max-width: 900px; }
h2 { font-size: 18px; margin-bottom: 6px; color: #1a73e8; }
.hint { color: #666; font-size: 14px; margin-bottom: 24px; }

.upload-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
  margin-bottom: 24px;
}

.upload-zone {
  border: 2px dashed #ccc;
  border-radius: 10px;
  padding: 24px 16px;
  text-align: center;
  transition: border-color 0.2s, background 0.2s;
  background: #fafafa;
}
.upload-zone.ok { border-color: #34a853; background: #f0fdf4; }
.upload-zone.error { border-color: #ea4335; background: #fff5f5; }

.zone-icon { font-size: 32px; margin-bottom: 8px; }
.zone-title { font-weight: 600; font-size: 14px; margin-bottom: 4px; }
.zone-sub { font-size: 12px; color: #888; margin-bottom: 16px; }

.upload-btn {
  background: #1a73e8;
  color: #fff;
  border: none;
  border-radius: 6px;
  padding: 8px 20px;
  font-size: 13px;
  font-weight: 500;
  transition: background 0.15s;
}
.upload-btn:hover { background: #1558b0; }

.file-name { font-size: 12px; color: #555; margin-top: 8px; word-break: break-all; }
.status-ok { font-size: 12px; color: #34a853; margin-top: 6px; font-weight: 500; }
.status-err { font-size: 12px; color: #ea4335; margin-top: 6px; }

.actions { margin-top: 8px; }
.next-btn {
  background: #34a853;
  color: #fff;
  border: none;
  border-radius: 6px;
  padding: 10px 28px;
  font-size: 14px;
  font-weight: 600;
  transition: background 0.15s;
}
.next-btn:hover { background: #2d8f47; }
</style>
