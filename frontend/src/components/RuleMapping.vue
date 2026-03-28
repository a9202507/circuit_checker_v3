<script setup>
import { ref, computed } from 'vue'
import { useAppStore } from '../stores/appStore'
import { useT } from '../i18n'
import { runCheck } from '../api'

const emit = defineEmits(['go-results'])
const store = useAppStore()
const t = useT()

const search   = ref('')
const bulkYaml = ref('')

const filtered = computed(() => {
  const q = search.value.trim().toUpperCase()
  return store.mappings.filter(m =>
    !q ||
    m.refDes.toUpperCase().includes(q) ||
    m.componentType.toUpperCase().includes(q)
  )
})

const selectedMappings = computed(() => store.mappings.filter(m => m.selected))

const readyToRun = computed(() =>
  selectedMappings.value.length > 0 &&
  selectedMappings.value.every(m => m.yamlFile)
)

const allFilteredSelected = computed(() =>
  filtered.value.length > 0 && filtered.value.every(m => m.selected)
)

const someFilteredSelected = computed(() =>
  !allFilteredSelected.value && filtered.value.some(m => m.selected)
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
    regpair_file: m.regpairFile || '',
  }))
  try {
    const res = await runCheck(mappings)
    store.setCheckResults(res.data.results)
    emit('go-results')
  } catch (err) {
    store.isChecking = false
    alert('Error: ' + (err.response?.data?.detail || err.message))
  }
}

// Format spec badge: show key=value pairs
function specBadges(m) {
  const specs = m.specifications || {}
  return Object.entries(specs).map(([k, v]) => ({ k, v }))
}
</script>

<template>
  <div class="mapping-page">
    <div class="page-header">
      <h2>{{ t.mapping.title }}</h2>
      <p class="hint">{{ t.mapping.hint }}</p>
    </div>

    <div class="toolbar">
      <input v-model="search" class="search-input" :placeholder="t.mapping.search" />
      <select v-model="bulkYaml" class="a-select">
        <option value="">{{ t.mapping.bulkSelect }}</option>
        <option v-for="f in store.yamlFiles" :key="f" :value="f">{{ f }}</option>
      </select>
      <button class="btn btn-outline" :disabled="!bulkYaml" @click="applyBulk">
        {{ t.mapping.applyBtn }}
      </button>
    </div>

    <div class="table-wrap">
      <table class="a-table">
        <thead>
          <tr>
            <th class="th-check">
              <input
                type="checkbox"
                :checked="allFilteredSelected"
                :indeterminate="someFilteredSelected"
                @change="e => toggleAll(e.target.checked)"
              />
            </th>
            <th>{{ t.mapping.th.refdes }}</th>
            <th>{{ t.mapping.th.component }}</th>
            <th>{{ t.mapping.th.yaml }}</th>
            <th>{{ t.mapping.th.config }}</th>
            <th>{{ t.mapping.th.spec }}</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="m in filtered"
            :key="m.refDes"
            :class="{ selected: m.selected }"
            @click.self="m.selected = !m.selected"
          >
            <td class="td-check"><input type="checkbox" v-model="m.selected" /></td>
            <td class="td-refdes">{{ m.refDes }}</td>
            <td class="td-comp">{{ m.componentType }}</td>
            <td>
              <select
                v-model="m.yamlFile"
                class="a-select yaml-sel"
                :class="{ matched: m.yamlFile }"
              >
                <option value="">{{ t.mapping.unassigned }}</option>
                <option v-for="f in store.yamlFiles" :key="f" :value="f">{{ f }}</option>
              </select>
            </td>
            <td>
              <select
                v-model="m.regpairFile"
                class="a-select regpair-sel"
                :class="{ matched: m.regpairFile }"
              >
                <option value="">—</option>
                <option v-for="f in store.regpairFiles" :key="f" :value="f">{{ f }}</option>
              </select>
            </td>
            <td class="td-spec">
              <template v-if="m.specFile">
                <div class="spec-source">{{ m.specFile }}</div>
                <div class="spec-badges">
                  <span
                    v-for="badge in specBadges(m)"
                    :key="badge.k"
                    class="spec-badge"
                  >{{ badge.k }}={{ badge.v }}</span>
                </div>
              </template>
              <span v-else class="no-spec">—</span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <div class="footer">
      <span class="summary">
        {{
          t.mapping.summary
            .replace('{sel}', selectedMappings.length)
            .replace('{assigned}', selectedMappings.filter(m => m.yamlFile).length)
        }}
      </span>
      <button
        class="btn btn-primary"
        :disabled="!readyToRun || store.isChecking"
        @click="runChecks"
      >
        {{ store.isChecking ? t.mapping.running : t.mapping.runBtn }}
      </button>
    </div>
  </div>
</template>

<style scoped>
.mapping-page { max-width: 1000px; margin: 0 auto; }

.page-header { margin-bottom: 20px; }
h2 { font-size: 18px; font-weight: 700; color: var(--text); margin-bottom: 6px; }
.hint { font-size: 13px; color: var(--text-sub); }

/* Toolbar */
.toolbar {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 14px;
  flex-wrap: wrap;
}
.search-input {
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 7px 12px;
  font-size: 13px;
  width: 220px;
  outline: none;
  transition: border-color 0.15s;
}
.search-input:focus { border-color: var(--primary); }
.a-select {
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 7px 10px;
  font-size: 13px;
  background: #fff;
  outline: none;
}
.a-select:focus { border-color: var(--primary); }

/* Table */
.table-wrap {
  max-height: 480px;
  overflow-y: auto;
  border: 1px solid var(--border);
  border-radius: 8px;
}
.a-table { width: 100%; border-collapse: collapse; font-size: 13px; }

.a-table thead th {
  background: var(--tbl-head-bg);
  padding: 9px 14px;
  text-align: left;
  font-weight: 600;
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: var(--text-sub);
  border-bottom: 1px solid var(--border);
  position: sticky;
  top: 0;
  z-index: 1;
}
.th-check { width: 40px; text-align: center !important; }

.a-table tbody tr { transition: background 0.1s; }
.a-table tbody tr:hover { background: #F8FBFF; }
.a-table tbody tr.selected { background: var(--primary-light); }
.a-table tbody td {
  padding: 9px 14px;
  border-bottom: 1px solid #F5F7FA;
  color: var(--text);
  vertical-align: top;
}
.a-table tbody tr:last-child td { border-bottom: none; }
.td-check { width: 40px; text-align: center; vertical-align: middle !important; }
.td-refdes { font-family: ui-monospace, monospace; font-weight: 600; font-size: 13px; vertical-align: middle !important; }
.td-comp   { font-size: 12px; color: var(--text-sub); vertical-align: middle !important; }

.yaml-sel { width: 100%; font-size: 12px; }
.yaml-sel.matched { border-color: var(--primary); color: var(--primary); background: var(--primary-light); }

.regpair-sel { width: 100%; font-size: 12px; }
.regpair-sel.matched { border-color: #8B5CF6; color: #7C3AED; background: #F5F3FF; }

/* Spec column */
.td-spec { min-width: 160px; }
.spec-source {
  font-size: 11px;
  color: var(--text-muted);
  margin-bottom: 4px;
}
.spec-badges { display: flex; flex-wrap: wrap; gap: 4px; }
.spec-badge {
  font-size: 11px;
  font-family: ui-monospace, monospace;
  background: #EEF6FF;
  color: #1A6BB0;
  border: 1px solid #C3DCFF;
  border-radius: 4px;
  padding: 2px 6px;
  white-space: nowrap;
}
.no-spec { color: #ccc; font-size: 13px; }

/* Footer */
.footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 16px;
}
.summary { font-size: 13px; color: var(--text-sub); }

input[type="checkbox"] { accent-color: var(--primary); cursor: pointer; }
</style>
