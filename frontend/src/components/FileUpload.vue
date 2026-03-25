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
        <div class="zone-icon">
          <svg viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg">
            <path d="M 20 12 L 44 12 Q 48 12 48 16 L 48 52 Q 48 56 44 56 L 20 56 Q 16 56 16 52 L 16 16 Q 16 12 20 12" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/>
            <path d="M 22 24 L 46 24" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
            <path d="M 22 32 L 46 32" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
            <path d="M 22 40 L 46 40" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
            <path d="M 22 48 L 46 48" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
          </svg>
        </div>
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
        <div class="zone-icon">
          <svg viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg">
            <g stroke="currentColor" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round">
              <rect x="14" y="14" width="10" height="10" rx="1"/>
              <rect x="28" y="14" width="10" height="10" rx="1"/>
              <rect x="42" y="14" width="10" height="10" rx="1"/>
              <rect x="14" y="28" width="10" height="10" rx="1"/>
              <rect x="28" y="28" width="10" height="10" rx="1"/>
              <rect x="42" y="28" width="10" height="10" rx="1"/>
              <rect x="14" y="42" width="10" height="10" rx="1"/>
              <rect x="28" y="42" width="10" height="10" rx="1"/>
              <rect x="42" y="42" width="10" height="10" rx="1"/>
            </g>
          </svg>
        </div>
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
        <div class="zone-icon">
          <svg viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg">
            <g stroke="currentColor" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round">
              <path d="M 16 16 L 48 16 Q 50 16 50 18 L 50 50 Q 50 52 48 52 L 16 52 Q 14 52 14 50 L 14 18 Q 14 16 16 16"/>
              <circle cx="22" cy="28" r="3" fill="currentColor"/>
              <line x1="28" y1="26" x2="42" y2="26"/>
              <line x1="28" y1="30" x2="42" y2="30"/>
              <circle cx="22" cy="40" r="3" fill="currentColor"/>
              <line x1="28" y1="38" x2="42" y2="38"/>
              <line x1="28" y1="42" x2="42" y2="42"/>
            </g>
          </svg>
        </div>
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
.upload-page {
  max-width: 900px;
  margin: 0 auto;
}

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

.zone-icon {
  width: 56px;
  height: 56px;
  margin: 0 auto 16px;
  color: var(--primary);
  flex-shrink: 0;
}

.zone-icon svg {
  width: 100%;
  height: 100%;
  stroke: currentColor;
}
.zone-title { font-size: 13px; font-weight: 600; color: var(--text); margin-bottom: 4px; }
.zone-sub   { font-size: 12px; color: var(--text-sub); margin-bottom: 16px; line-height: 1.5; }
.zone-btn   { margin: 0 auto; }

.file-name  { font-size: 12px; color: #555; margin-top: 10px; word-break: break-all; }
.status-ok  { font-size: 12px; color: var(--primary); margin-top: 6px; font-weight: 500; }
.status-err { font-size: 12px; color: #E84040; margin-top: 6px; }

.actions { margin-top: 4px; }
</style>
