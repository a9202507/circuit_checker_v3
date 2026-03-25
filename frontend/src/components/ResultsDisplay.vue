<script setup>
import { ref } from 'vue'
import { useAppStore } from '../stores/appStore'
import { useT } from '../i18n'
import { exportReport } from '../api'

const store = useAppStore()
const t = useT()
const collapsed = ref({})

function toggleCollapse(refDes) {
  collapsed.value[refDes] = !collapsed.value[refDes]
}
function isCollapsed(refDes) {
  return collapsed.value[refDes] ?? false
}

function overallStatus(results) {
  if (results.some(r => r.status === 'ERROR'))   return 'ERROR'
  if (results.some(r => r.status === 'WARNING')) return 'WARNING'
  return 'PASS'
}

function statusCount(results) {
  const p = results.filter(r => r.status === 'PASS').length
  const w = results.filter(r => r.status === 'WARNING').length
  const e = results.filter(r => r.status === 'ERROR').length
  const parts = []
  if (p) parts.push(`${p} PASS`)
  if (w) parts.push(`${w} WARNING`)
  if (e) parts.push(`${e} ERROR`)
  return parts.join(' · ')
}

function exportCSV() {
  const rows = [['RefDes', 'YAML', 'Type', 'Description', 'Status', 'Detail']]
  for (const ic of store.checkResults) {
    for (const r of ic.results) {
      rows.push([ic.ref_des, ic.yaml_file, r.rule_type, r.description, r.status, r.detail])
    }
  }
  const csv = rows.map(r => r.map(v => `"${String(v).replace(/"/g, '""')}"`).join(',')).join('\n')
  const blob = new Blob(['\ufeff' + csv], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = 'circuit_check_results.csv'
  a.click()
  URL.revokeObjectURL(url)
}

async function exportZip() {
  try {
    const yamlFilesUsed = [...new Set(store.checkResults.map(ic => ic.yaml_file).filter(Boolean))]
    const res = await exportReport(store.checkResults, yamlFilesUsed)
    const url = URL.createObjectURL(res.data)
    const a = document.createElement('a')
    a.href = url
    const cd = res.headers['content-disposition'] || ''
    const match = cd.match(/filename="?([^"]+)"?/)
    a.download = match ? match[1] : 'circuit_report.zip'
    a.click()
    URL.revokeObjectURL(url)
  } catch (err) {
    alert(t.value.results.exportFail + (err.response?.data?.detail || err.message))
  }
}
</script>

<template>
  <div class="results-page">
    <div class="top-bar">
      <h2>{{ t.results.title }}</h2>
      <div v-if="store.checkResults.length" class="export-group">
        <button class="btn btn-ghost" @click="exportCSV">{{ t.results.exportCsv }}</button>
        <button class="btn btn-outline" @click="exportZip">{{ t.results.exportZip }}</button>
      </div>
    </div>

    <div v-if="!store.checkResults.length" class="empty">
      {{ t.results.empty }}
    </div>

    <div v-for="ic in store.checkResults" :key="ic.ref_des" class="ic-section">
      <div
        class="ic-header"
        :class="'hdr-' + overallStatus(ic.results).toLowerCase()"
        @click="toggleCollapse(ic.ref_des)"
      >
        <span class="badge" :class="'badge-' + overallStatus(ic.results).toLowerCase()">
          {{ overallStatus(ic.results) }}
        </span>
        <span class="ic-refdes">{{ ic.ref_des }}</span>
        <span class="ic-type">({{ ic.component_type }})</span>
        <span class="ic-yaml">{{ ic.yaml_file }}</span>
        <span class="ic-summary">{{ statusCount(ic.results) }}</span>
        <span class="toggle">{{ isCollapsed(ic.ref_des) ? '▶' : '▼' }}</span>
      </div>

      <table v-if="!isCollapsed(ic.ref_des)" class="a-table">
        <thead>
          <tr>
            <th style="width:40px">{{ t.results.th.num }}</th>
            <th>{{ t.results.th.desc }}</th>
            <th style="width:96px">{{ t.results.th.status }}</th>
            <th>{{ t.results.th.detail }}</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="(r, idx) in ic.results"
            :key="idx"
            :class="'row-' + r.status.toLowerCase()"
          >
            <td class="td-num">{{ idx + 1 }}</td>
            <td>{{ r.description || r.rule_type }}</td>
            <td>
              <span class="badge" :class="'badge-' + r.status.toLowerCase()">{{ r.status }}</span>
            </td>
            <td class="td-detail">{{ r.detail }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<style scoped>
.results-page { max-width: 1000px; }

.top-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
}
h2 { font-size: 18px; font-weight: 700; color: var(--text); }

.export-group { display: flex; gap: 8px; }

.empty {
  color: var(--text-sub);
  font-size: 14px;
  padding: 60px 0;
  text-align: center;
}

/* IC section */
.ic-section {
  border: 1px solid var(--border);
  border-radius: 8px;
  margin-bottom: 12px;
  overflow: hidden;
}

.ic-header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 16px;
  cursor: pointer;
  user-select: none;
  background: var(--tbl-head-bg);
  border-bottom: 1px solid var(--border);
  transition: background 0.15s;
}
.ic-header:hover { background: #EDF2FB; }
.hdr-error   { background: #FFF8F8; border-left: 4px solid #E84040; }
.hdr-warning { background: #FFFDF5; border-left: 4px solid #F0A500; }
.hdr-pass    { background: #F5FFF9; border-left: 4px solid var(--primary); }

.ic-refdes { font-family: ui-monospace, monospace; font-weight: 700; font-size: 14px; }
.ic-type   { font-size: 13px; color: var(--text-sub); }
.ic-yaml   { font-size: 11px; color: #AAA; }
.ic-summary { font-size: 12px; color: var(--text-sub); margin-left: auto; }
.toggle    { font-size: 11px; color: #AAA; }

/* Table */
.a-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.a-table thead th {
  background: var(--tbl-head-bg);
  padding: 8px 14px;
  text-align: left;
  font-weight: 600;
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: var(--text-sub);
  border-bottom: 1px solid var(--border);
}
.a-table tbody td {
  padding: 9px 14px;
  border-bottom: 1px solid #F5F7FA;
  vertical-align: top;
}
.a-table tbody tr:last-child td { border-bottom: none; }
.td-num    { color: #C8CDD6; text-align: center; }
.td-detail { color: var(--text-sub); font-size: 12px; }

.row-pass    td { background: #F9FFFC; }
.row-warning td { background: #FFFEF5; }
.row-error   td { background: #FFF9F9; }

/* Reuse global badge but add pill shape for status tags inside table */
.badge { border-radius: 3px; }
.badge-pass  { background: #E6F7F2; color: #007A52; }
.badge-warn, .badge-warning { background: #FFF8E6; color: #B07700; }
.badge-error { background: #FFF0EE; color: #C0392B; }
</style>
