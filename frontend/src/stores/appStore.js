import { defineStore } from 'pinia'

export const useAppStore = defineStore('app', {
  state: () => ({
    ascLoaded: false,
    bomLoaded: false,
    ascFilename: '',
    yamlFiles: [],        // list of loaded yaml filenames
    icRefs: [],           // detected IC ref designators
    allRefs: [],          // all ref designators
    componentTypes: {},   // {refDes: componentType}  e.g. {U93: "TDM24544"}
    mappings: [],         // [{refDes, componentType, yamlFile, selected}]
    checkResults: [],     // array of ICCheckResult
    isChecking: false,
  }),
  getters: {
    canCheck: (state) =>
      state.ascLoaded && state.bomLoaded && state.yamlFiles.length > 0,
  },
  actions: {
    setAscLoaded(data) {
      this.ascLoaded = true
      this.ascFilename = data.asc_filename || ''
      this.icRefs = data.ic_refs || []
      this.allRefs = data.all_refs || []
      this.componentTypes = data.ic_component_types || {}

      // Initialize mappings for new IC refs
      const existing = new Set(this.mappings.map(m => m.refDes))
      for (const ref of this.icRefs) {
        if (!existing.has(ref)) {
          this.mappings.push({
            refDes: ref,
            componentType: this.componentTypes[ref] || '',
            yamlFile: '',
            selected: false,
          })
        } else {
          // update componentType in case ASC was re-uploaded
          const m = this.mappings.find(m => m.refDes === ref)
          if (m) m.componentType = this.componentTypes[ref] || ''
        }
      }
      // Auto-match any already-loaded YAML files
      this._autoMatchYaml()
    },
    setBomLoaded() {
      this.bomLoaded = true
    },
    addYamlFiles(filenames) {
      for (const f of filenames) {
        if (!this.yamlFiles.includes(f)) {
          this.yamlFiles.push(f)
        }
      }
      this._autoMatchYaml()
    },
    removeYamlFile(filename) {
      this.yamlFiles = this.yamlFiles.filter(f => f !== filename)
      for (const m of this.mappings) {
        if (m.yamlFile === filename) m.yamlFile = ''
      }
    },
    setCheckResults(results) {
      this.checkResults = results
      this.isChecking = false
    },
    /** Fuzzy-match component types to YAML filenames.
     *  Only fills in mappings that have no yamlFile assigned yet.
     *  Matching priority:
     *   1. Exact (case-insensitive)
     *   2. YAML base contains component type, or vice versa
     */
    _autoMatchYaml() {
      for (const m of this.mappings) {
        if (m.yamlFile) continue
        const comp = (m.componentType || '').toLowerCase().trim()
        if (!comp) continue
        let best = ''
        let bestScore = 0
        for (const f of this.yamlFiles) {
          const base = f.replace(/\.ya?ml$/i, '').toLowerCase().trim()
          let score = 0
          if (base === comp) {
            score = 3        // exact match
          } else if (base.includes(comp) || comp.includes(base)) {
            // prefer longer overlap
            const overlap = Math.min(base.length, comp.length)
            score = 1 + overlap / Math.max(base.length, comp.length)
          }
          if (score > bestScore) {
            bestScore = score
            best = f
          }
        }
        if (best) m.yamlFile = best
      }
    },
  },
})
