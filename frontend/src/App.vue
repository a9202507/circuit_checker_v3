<script setup>
import { ref } from 'vue'
import { useAppStore } from './stores/appStore'
import { useT, lang, toggleLang } from './i18n'
import FileUpload from './components/FileUpload.vue'
import YamlGenerator from './components/YamlGenerator.vue'
import RuleMapping from './components/RuleMapping.vue'
import ResultsDisplay from './components/ResultsDisplay.vue'
import SpecEditor from './components/SpecEditor.vue'

const store = useAppStore()
const t = useT()
const activeTab = ref(0)

const TAB_KEYS = ['upload', 'yaml', 'spec', 'mapping', 'results']

const tabDisabled = (idx) => {
  if (idx === 3) return !store.canViewMapping
  if (idx === 4) return !store.canCheck
  return false
}

function selectTab(idx) {
  if (!tabDisabled(idx)) activeTab.value = idx
}
</script>

<template>
  <div id="app-root">
    <!-- Top bar -->
    <header class="topbar">
      <div class="topbar-left">
        <div class="logo-container">
          <span class="logo-text">
            <span class="logo-circuit">Circuit</span><span class="logo-checker">Checker</span>
          </span>
          <span class="logo-version">Rev0.5.1</span>
        </div>
      </div>

      <nav class="nav-tabs">
        <button
          v-for="(key, idx) in TAB_KEYS"
          :key="key"
          :class="['nav-tab', { active: activeTab === idx, disabled: tabDisabled(idx) }]"
          @click="selectTab(idx)"
        >
          {{ t.tabs[key] }}
        </button>
      </nav>

      <div class="topbar-right">
        <button class="lang-btn" @click="toggleLang">{{ t.langBtn }}</button>
      </div>
    </header>

    <!-- Page content -->
    <main class="tab-content">
      <FileUpload    v-if="activeTab === 0" @go-next="activeTab = 1" />
      <YamlGenerator v-else-if="activeTab === 1" @go-next="activeTab = 2" />
      <SpecEditor    v-else-if="activeTab === 2" />
      <RuleMapping   v-else-if="activeTab === 3" @go-results="activeTab = 4" />
      <ResultsDisplay v-else-if="activeTab === 4" />
    </main>
  </div>
</template>

<style scoped>
#app-root {}

/* ── Top bar ──────────────────────────────────────────────────────────── */
.topbar {
  display: flex;
  align-items: center;
  background: #fff;
  border-bottom: 3px solid var(--primary);
  padding: 0 8px;
  height: 56px;
  box-shadow: 0 1px 4px rgba(0,0,0,.06);
  gap: 24px;
}

.topbar-left {
  display: flex;
  align-items: center;
  min-width: 180px;
}

.logo-container {
  display: flex;
  flex-direction: row;
  align-items: baseline;
  gap: 6px;
}

.logo-text {
  font-size: 17px;
  font-weight: 700;
  letter-spacing: -0.3px;
  white-space: nowrap;
  line-height: 1;
}
.logo-circuit { color: var(--primary); }
.logo-checker { color: var(--text); }

.logo-version {
  font-size: 10px;
  font-weight: 500;
  color: var(--text-muted);
  letter-spacing: 0.2px;
  line-height: 1;
}

/* ── Nav tabs ─────────────────────────────────────────────────────────── */
.nav-tabs {
  display: flex;
  gap: 0;
  flex: 1;
  height: 56px;
}
.nav-tab {
  height: 56px;
  padding: 0 20px;
  border: none;
  background: transparent;
  font-size: 13px;
  font-weight: 500;
  color: var(--text-sub);
  border-bottom: 3px solid transparent;
  margin-bottom: -3px;
  cursor: pointer;
  transition: color 0.15s, border-color 0.15s;
  white-space: nowrap;
}
.nav-tab:hover:not(.disabled) { color: var(--primary); }
.nav-tab.active {
  color: var(--primary);
  border-bottom-color: var(--primary);
  font-weight: 600;
}
.nav-tab.disabled { color: #bbb; cursor: not-allowed; }

/* ── Language button ──────────────────────────────────────────────────── */
.topbar-right { min-width: 60px; display: flex; justify-content: flex-end; }
.lang-btn {
  background: #fff;
  border: 1.5px solid var(--border);
  color: var(--text);
  border-radius: var(--radius);
  padding: 5px 14px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: border-color 0.15s, color 0.15s;
  letter-spacing: 0.3px;
}
.lang-btn:hover {
  border-color: var(--primary);
  color: var(--primary);
}

/* ── Content area ─────────────────────────────────────────────────────── */
.tab-content {
  background: var(--card);
  border: 1px solid var(--border);
  border-top: none;
  border-radius: 0 0 8px 8px;
  padding: 28px 28px;
}
</style>
