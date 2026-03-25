<script setup>
import { ref } from 'vue'
import { useAppStore } from '../stores/appStore'
import { useT } from '../i18n'
import { uploadASC, uploadBOM, uploadYAML } from '../api'

const emit = defineEmits(['go-next'])
const store = useAppStore()
const t = useT()

const ascStatus    = ref(null)   // null | 'loading' | 'ok' | 'error'
const bomStatus    = ref(null)
const yamlStatus   = ref(null)
const ascError     = ref('')
const bomError     = ref('')
const yamlError    = ref('')
const ascFileName  = ref('')
const bomFileName  = ref('')
const yamlFileNames = ref([])

async function handleAsc(e) {
  const file = e.target.files[0]
  if (!file) return
  ascFileName.value = file.name
  ascStatus.value = 'loading'
  ascError.value = ''
  try {
    const res = await uploadASC(file)
    store.setAscLoaded({ ...res.data, asc_filename: file.name })
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
    <div class="page-header">
      <h2>{{ t.upload.title }}</h2>
      <p class="hint">{{ t.upload.hint }}</p>
    </div>

    <div class="upload-grid">
      <!-- ASC -->
      <div class="zone" :class="{ 'zone-ok': ascStatus === 'ok', 'zone-err': ascStatus === 'error' }">
        <div class="zone-icon">📄</div>
        <div class="zone-title">{{ t.upload.asc.title }}</div>
        <div class="zone-sub">{{ t.upload.asc.sub }}</div>
        <input id="asc-input" type="file" accept=".asc,*/*" hidden @change="handleAsc" />
        <button class="btn btn-primary zone-btn" @click="triggerInput('asc-input')">
          {{ ascStatus === 'loading' ? t.upload.uploading : t.upload.asc.btn }}
        </button>
        <div v-if="ascFileName" class="file-name">{{ ascFileName }}</div>
        <div v-if="ascStatus === 'ok'" class="status-ok">
          ✓ {{ t.upload.asc.loaded.replace('{n}', store.allRefs.length).replace('{ic}', store.icRefs.length) }}
        </div>
        <div v-if="ascStatus === 'error'" class="status-err">✗ {{ ascError }}</div>
      </div>

      <!-- BOM -->
      <div class="zone" :class="{ 'zone-ok': bomStatus === 'ok', 'zone-err': bomStatus === 'error' }">
        <div class="zone-icon">📋</div>
        <div class="zone-title">{{ t.upload.bom.title }}</div>
        <div class="zone-sub">{{ t.upload.bom.sub }}</div>
        <input id="bom-input" type="file" accept=".BOM,.bom,.txt,*/*" hidden @change="handleBom" />
        <button class="btn btn-primary zone-btn" @click="triggerInput('bom-input')">
          {{ bomStatus === 'loading' ? t.upload.uploading : t.upload.bom.btn }}
        </button>
        <div v-if="bomFileName" class="file-name">{{ bomFileName }}</div>
        <div v-if="bomStatus === 'ok'" class="status-ok">✓ {{ t.upload.bom.loaded }}</div>
        <div v-if="bomStatus === 'error'" class="status-err">✗ {{ bomError }}</div>
      </div>

      <!-- YAML -->
      <div class="zone" :class="{ 'zone-ok': yamlStatus === 'ok', 'zone-err': yamlStatus === 'error' }">
        <div class="zone-icon">⚙️</div>
        <div class="zone-title">{{ t.upload.yaml.title }}</div>
        <div class="zone-sub">{{ t.upload.yaml.sub }}</div>
        <input id="yaml-input" type="file" accept=".yaml,.yml" multiple hidden @change="handleYaml" />
        <button class="btn btn-primary zone-btn" @click="triggerInput('yaml-input')">
          {{ yamlStatus === 'loading' ? t.upload.uploading : t.upload.yaml.btn }}
        </button>
        <div v-if="yamlFileNames.length" class="file-name">{{ yamlFileNames.join(', ') }}</div>
        <div v-if="yamlStatus === 'ok'" class="status-ok">
          ✓ {{ t.upload.yaml.loaded.replace('{n}', store.yamlFiles.length) }}
        </div>
        <div v-if="yamlStatus === 'error'" class="status-err" style="white-space:pre-line">✗ {{ yamlError }}</div>
      </div>
    </div>

    <div class="actions">
      <button v-if="store.canCheck" class="btn btn-primary" @click="emit('go-next')">
        {{ t.upload.nextBtn }}
      </button>
    </div>
  </div>
</template>

<style scoped>
.upload-page { max-width: 900px; }

.page-header { margin-bottom: 24px; }
h2 { font-size: 18px; font-weight: 700; color: var(--text); margin-bottom: 6px; }
.hint { font-size: 13px; color: var(--text-sub); }

.upload-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
  margin-bottom: 24px;
}

.zone {
  border: 2px dashed var(--border);
  border-radius: 8px;
  padding: 26px 18px;
  text-align: center;
  background: #FAFBFD;
  transition: border-color 0.2s, background 0.2s;
}
.zone-ok  { border-color: var(--primary); background: var(--primary-light); }
.zone-err { border-color: #E84040; background: #FFF5F5; }

.zone-icon  { font-size: 30px; margin-bottom: 10px; }
.zone-title { font-size: 13px; font-weight: 600; color: var(--text); margin-bottom: 4px; }
.zone-sub   { font-size: 12px; color: var(--text-sub); margin-bottom: 16px; line-height: 1.5; }
.zone-btn   { margin: 0 auto; }

.file-name  { font-size: 12px; color: #555; margin-top: 10px; word-break: break-all; }
.status-ok  { font-size: 12px; color: var(--primary); margin-top: 6px; font-weight: 500; }
.status-err { font-size: 12px; color: #E84040; margin-top: 6px; }

.actions { margin-top: 4px; }
</style>
