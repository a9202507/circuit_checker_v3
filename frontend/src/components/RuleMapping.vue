<script setup>
import { ref, computed } from 'vue'
import { useAppStore } from '../stores/appStore'
import { runCheck } from '../api'

const emit = defineEmits(['go-results'])
const store = useAppStore()

const search = ref('')
const bulkYaml = ref('')

const filtered = computed(() => {
  const q = search.value.trim().toUpperCase()
  return store.mappings.filter(m => !q || m.refDes.toUpperCase().includes(q) || m.componentType.toUpperCase().includes(q))
})

const selectedMappings = computed(() =>
  store.mappings.filter(m => m.selected)
)

const readyToRun = computed(() =>
  selectedMappings.value.length > 0 &&
  selectedMappings.value.every(m => m.yamlFile)
)

const allFilteredSelected = computed(() =>
  filtered.value.length > 0 && filtered.value.every(m => m.selected)
)

function toggleAll(checked) {
  for (const m of filtered.value) m.selected = checked
}

function applyBulk() {
  if (!bulkYaml.value) return
  for (const m of filtered.value) {
    if (m.selected) m.yamlFile = bulkYaml.value
  }
}

async function runChecks() {
  store.isChecking = true
  const mappings = selectedMappings.value.map(m => ({
    ref_des: m.refDes,
    yaml_file: m.yamlFile,
  }))
  try {
    const res = await runCheck(mappings)
    store.setCheckResults(res.data.results)
    emit('go-results')
  } catch (err) {
    store.isChecking = false
    alert('執行檢查時發生錯誤：' + (err.response?.data?.detail || err.message))
  }
}
</script>

<template>
  <div class="mapping-page">
    <h2>IC 對應設定</h2>
    <p class="hint">勾選要檢查的 IC，並為每個 IC 指定規則 YAML 檔案，然後執行檢查。</p>

    <div class="toolbar">
      <input v-model="search" class="search" placeholder="搜尋 RefDes / 元件型號…" />
      <select v-model="bulkYaml" class="bulk-select">
        <option value="">批次指定規則…</option>
        <option v-for="f in store.yamlFiles" :key="f" :value="f">{{ f }}</option>
      </select>
      <button class="apply-btn" :disabled="!bulkYaml" @click="applyBulk">套用至已選</button>
    </div>

    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th style="width:36px;text-align:center">
              <input
                type="checkbox"
                :checked="allFilteredSelected"
                :indeterminate="!allFilteredSelected && filtered.some(m => m.selected)"
                @change="e => toggleAll(e.target.checked)"
                title="全選 / 全消"
              />
            </th>
            <th>Ref Des</th>
            <th>元件型號</th>
            <th>規則 YAML</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="m in filtered" :key="m.refDes" :class="{ selected: m.selected }">
            <td style="text-align:center"><input type="checkbox" v-model="m.selected" /></td>
            <td class="refdes">{{ m.refDes }}</td>
            <td class="comptype">{{ m.componentType }}</td>
            <td>
              <select v-model="m.yamlFile" class="yaml-select" :class="{ matched: m.yamlFile }">
                <option value="">-- 選擇 --</option>
                <option v-for="f in store.yamlFiles" :key="f" :value="f">{{ f }}</option>
              </select>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <div class="footer">
      <span class="summary">
        已選 {{ selectedMappings.length }} 個 IC，
        {{ selectedMappings.filter(m => m.yamlFile).length }} 個已指定規則
      </span>
      <button
        class="run-btn"
        :disabled="!readyToRun || store.isChecking"
        @click="runChecks"
      >
        {{ store.isChecking ? '檢查中…' : '▶ 執行線路檢查' }}
      </button>
    </div>
  </div>
</template>

<style scoped>
.mapping-page { max-width: 900px; }
h2 { font-size: 18px; margin-bottom: 6px; color: #1a73e8; }
.hint { color: #666; font-size: 14px; margin-bottom: 16px; }

.toolbar {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
  flex-wrap: wrap;
}
.search {
  border: 1px solid #ccc;
  border-radius: 6px;
  padding: 6px 10px;
  font-size: 13px;
  width: 200px;
}
.bulk-select {
  border: 1px solid #ccc;
  border-radius: 6px;
  padding: 6px 8px;
  font-size: 13px;
}
.apply-btn {
  background: #1a73e8;
  color: #fff;
  border: none;
  border-radius: 6px;
  padding: 6px 14px;
  font-size: 13px;
}
.apply-btn:disabled { background: #aaa; cursor: not-allowed; }

.table-wrap {
  max-height: 420px;
  overflow-y: auto;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
}
table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}
thead th {
  background: #f5f5f5;
  padding: 8px 12px;
  text-align: left;
  font-weight: 600;
  position: sticky;
  top: 0;
  border-bottom: 1px solid #ddd;
}
tbody tr:hover { background: #f9fbff; }
tbody tr.selected { background: #e8f0fe; }
tbody td {
  padding: 6px 12px;
  border-bottom: 1px solid #f0f0f0;
}
.refdes { font-family: monospace; font-weight: 600; }
.comptype { font-size: 12px; color: #555; }
.yaml-select {
  width: 100%;
  border: 1px solid #ccc;
  border-radius: 4px;
  padding: 4px 6px;
  font-size: 13px;
}
.yaml-select.matched {
  border-color: #34a853;
  background: #f0fdf4;
}

.footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 16px;
}
.summary { font-size: 13px; color: #666; }
.run-btn {
  background: #1a73e8;
  color: #fff;
  border: none;
  border-radius: 6px;
  padding: 10px 28px;
  font-size: 14px;
  font-weight: 600;
}
.run-btn:disabled { background: #aaa; cursor: not-allowed; }
.run-btn:not(:disabled):hover { background: #1558b0; }
</style>
