<script setup>
import { ref, computed } from 'vue'
import { useAppStore } from './stores/appStore'
import FileUpload from './components/FileUpload.vue'
import YamlGenerator from './components/YamlGenerator.vue'
import RuleMapping from './components/RuleMapping.vue'
import ResultsDisplay from './components/ResultsDisplay.vue'

const store = useAppStore()
const activeTab = ref(0)

const tabs = [
  { label: '① 上傳檔案', key: 'upload' },
  { label: '② YAML 規則產生器', key: 'yaml' },
  { label: '③ IC 對應設定', key: 'mapping' },
  { label: '④ 檢查結果', key: 'results' },
]

const tabDisabled = (idx) => {
  if (idx <= 1) return false
  return !store.canCheck
}

function selectTab(idx) {
  if (!tabDisabled(idx)) activeTab.value = idx
}
</script>

<template>
  <div id="app-root">
    <header>
      <h1>線路檢查器 Circuit Checker</h1>
    </header>

    <nav class="tabs">
      <button
        v-for="(tab, idx) in tabs"
        :key="tab.key"
        :class="['tab-btn', { active: activeTab === idx, disabled: tabDisabled(idx) }]"
        @click="selectTab(idx)"
      >
        {{ tab.label }}
      </button>
    </nav>

    <main class="tab-content">
      <FileUpload v-if="activeTab === 0" @go-next="activeTab = 1" />
      <YamlGenerator v-else-if="activeTab === 1" @go-next="activeTab = 2" />
      <RuleMapping v-else-if="activeTab === 2" @go-results="activeTab = 3" />
      <ResultsDisplay v-else-if="activeTab === 3" />
    </main>
  </div>
</template>

<style scoped>
#app-root {
  min-height: 100vh;
}

header {
  padding: 20px 0 12px;
  border-bottom: 2px solid #1a73e8;
  margin-bottom: 0;
}

header h1 {
  font-size: 22px;
  font-weight: 700;
  color: #1a73e8;
  letter-spacing: 0.3px;
}

.tabs {
  display: flex;
  gap: 0;
  border-bottom: 1px solid #ddd;
  background: #fff;
  padding: 0 4px;
}

.tab-btn {
  padding: 12px 20px;
  border: none;
  background: transparent;
  font-size: 14px;
  font-weight: 500;
  color: #555;
  border-bottom: 3px solid transparent;
  margin-bottom: -1px;
  transition: color 0.15s, border-color 0.15s;
}

.tab-btn:hover:not(.disabled) {
  color: #1a73e8;
}

.tab-btn.active {
  color: #1a73e8;
  border-bottom-color: #1a73e8;
}

.tab-btn.disabled {
  color: #bbb;
  cursor: not-allowed;
}

.tab-content {
  background: #fff;
  border: 1px solid #e0e0e0;
  border-top: none;
  border-radius: 0 0 8px 8px;
  padding: 24px;
  min-height: 500px;
}
</style>
