<script setup>
import { ref, computed } from 'vue'
import { useAppStore } from '../stores/appStore'
import { runCheck, exportReport } from '../api'

const store = useAppStore()

const collapsed = ref({})

function toggleCollapse(refDes) {
  collapsed.value[refDes] = !collapsed.value[refDes]
}

function isCollapsed(refDes) {
  return collapsed.value[refDes] ?? false
}

function overallStatus(results) {
  if (results.some(r => r.status === 'ERROR')) return 'ERROR'
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
  return parts.join('，')
}

async function exportZip() {
  try {
    const yamlFilesUsed = [...new Set(store.checkResults.map(ic => ic.yaml_file).filter(Boolean))]
    const res = await exportReport(store.checkResults, yamlFilesUsed)
    const url = URL.createObjectURL(res.data)
    const a = document.createElement('a')
    a.href = url
    // filename comes from Content-Disposition, but set a fallback
    const cd = res.headers['content-disposition'] || ''
    const match = cd.match(/filename="?([^"]+)"?/)
    a.download = match ? match[1] : 'circuit_report.zip'
    a.click()
    URL.revokeObjectURL(url)
  } catch (err) {
    alert('匯出報告失敗：' + (err.response?.data?.detail || err.message))
  }
}

function exportCSV() {
  const rows = [['RefDes', 'YAML', '類型', '描述', '狀態', '詳細']]
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
</script>

<template>
  <div class="results-page">
    <div class="top-bar">
      <h2>檢查結果</h2>
      <div v-if="store.checkResults.length" class="export-group">
        <button class="export-btn" @click="exportCSV">↓ 匯出 CSV</button>
        <button class="export-btn zip-btn" @click="exportZip">↓ 匯出完整報告 (.zip)</button>
      </div>
    </div>

    <div v-if="!store.checkResults.length" class="empty">
      尚無檢查結果，請至「IC 對應設定」頁面執行檢查。
    </div>

    <div v-for="ic in store.checkResults" :key="ic.ref_des" class="ic-section">
      <div
        class="ic-header"
        :class="'status-' + overallStatus(ic.results).toLowerCase()"
        @click="toggleCollapse(ic.ref_des)"
      >
        <span class="ic-title">
          <span class="status-badge" :class="'badge-' + overallStatus(ic.results).toLowerCase()">
            {{ overallStatus(ic.results) }}
          </span>
          {{ ic.ref_des }}
          <span class="ic-type">({{ ic.component_type }})</span>
          <span class="ic-yaml">{{ ic.yaml_file }}</span>
        </span>
        <span class="ic-summary">{{ statusCount(ic.results) }}</span>
        <span class="toggle">{{ isCollapsed(ic.ref_des) ? '▶' : '▼' }}</span>
      </div>

      <table v-if="!isCollapsed(ic.ref_des)">
        <thead>
          <tr>
            <th style="width:40px">#</th>
            <th>描述</th>
            <th style="width:90px">狀態</th>
            <th>詳細</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="(r, idx) in ic.results"
            :key="idx"
            :class="'row-' + r.status.toLowerCase()"
          >
            <td class="idx">{{ idx + 1 }}</td>
            <td>{{ r.description || r.rule_type }}</td>
            <td>
              <span class="status-tag" :class="'tag-' + r.status.toLowerCase()">
                {{ r.status }}
              </span>
            </td>
            <td class="detail">{{ r.detail }}</td>
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
  margin-bottom: 16px;
}
h2 { font-size: 18px; color: #1a73e8; }

.export-group { display: flex; gap: 8px; }
.export-btn {
  background: #fff;
  border: 1px solid #1a73e8;
  color: #1a73e8;
  border-radius: 6px;
  padding: 6px 16px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
}
.export-btn:hover { background: #e8f0fe; }
.zip-btn { border-color: #34a853; color: #34a853; }
.zip-btn:hover { background: #f0fdf4; }

.empty {
  color: #888;
  font-size: 14px;
  padding: 40px 0;
  text-align: center;
}

.ic-section {
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  margin-bottom: 12px;
  overflow: hidden;
}

.ic-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 16px;
  cursor: pointer;
  background: #f8f9fa;
  user-select: none;
}
.ic-header:hover { background: #f0f4ff; }

.ic-title { display: flex; align-items: center; gap: 8px; flex: 1; font-weight: 600; font-size: 14px; }
.ic-type { font-weight: 400; color: #666; }
.ic-yaml { font-size: 12px; color: #999; font-weight: 400; }
.ic-summary { font-size: 12px; color: #555; }
.toggle { color: #888; font-size: 11px; }

.status-badge {
  font-size: 11px;
  font-weight: 700;
  padding: 2px 7px;
  border-radius: 10px;
  text-transform: uppercase;
}
.badge-pass { background: #d4edda; color: #155724; }
.badge-warning { background: #fff3cd; color: #856404; }
.badge-error { background: #f8d7da; color: #721c24; }

table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}
thead th {
  background: #f5f5f5;
  padding: 7px 12px;
  text-align: left;
  font-weight: 600;
  border-bottom: 1px solid #ddd;
  border-top: 1px solid #e0e0e0;
}
tbody td {
  padding: 7px 12px;
  border-bottom: 1px solid #f0f0f0;
  vertical-align: top;
}
.idx { color: #bbb; text-align: center; }
.detail { color: #555; font-size: 12px; }

.row-pass td { background: #f9fff9; }
.row-warning td { background: #fffef0; }
.row-error td { background: #fff8f8; }

.status-tag {
  font-size: 11px;
  font-weight: 700;
  padding: 2px 7px;
  border-radius: 4px;
}
.tag-pass { background: #d4edda; color: #155724; }
.tag-warning { background: #fff3cd; color: #856404; }
.tag-error { background: #f8d7da; color: #721c24; }
</style>
