<script setup>
import { ref } from 'vue'
import { useT } from '../i18n'
import IcSpecEditor from './IcSpecEditor.vue'
import RailSpecEditor from './RailSpecEditor.vue'

const t = useT()
const activeSubTab = ref(0)  // 0 = Rail spec, 1 = IC spec
</script>

<template>
  <div class="spec-editor">
    <div class="page-header">
      <h2 class="page-title">{{ t.spec.title }}</h2>
      <p class="page-hint">{{ t.spec.hint }}</p>
    </div>

    <!-- Sub-tabs -->
    <div class="subtab-bar">
      <button
        v-for="(key, idx) in ['rail', 'ic']"
        :key="key"
        :class="['subtab', { active: activeSubTab === idx }]"
        @click="activeSubTab = idx"
      >
        {{ t.spec.subTabs[key] }}
      </button>
    </div>

    <!-- Sub-tab content -->
    <div class="subtab-content">
      <RailSpecEditor v-if="activeSubTab === 0" />
      <IcSpecEditor  v-else />
    </div>
  </div>
</template>

<style scoped>
.spec-editor { display: flex; flex-direction: column; gap: 20px; }

.page-header { display: flex; flex-direction: column; gap: 4px; }
.page-title { font-size: 18px; font-weight: 700; color: var(--text); margin: 0; }
.page-hint { font-size: 13px; color: var(--text-sub); margin: 0; }

.subtab-bar {
  display: flex; gap: 0; border-bottom: 2px solid var(--border);
}
.subtab {
  padding: 8px 20px; font-size: 13px; font-weight: 500;
  border: none; background: none; cursor: pointer; color: var(--text-sub);
  border-bottom: 2px solid transparent; margin-bottom: -2px;
  transition: color .15s, border-color .15s;
}
.subtab:hover { color: var(--primary); }
.subtab.active {
  color: var(--primary); border-bottom-color: var(--primary); font-weight: 600;
}

.subtab-content { padding-top: 4px; }
</style>
