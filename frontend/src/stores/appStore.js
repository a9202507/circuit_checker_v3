import { defineStore } from 'pinia'

export const useAppStore = defineStore('app', {
  state: () => ({
    ascLoaded: false,
    bomLoaded: false,
    ascFilename: '',
    yamlFiles: [],        // list of loaded yaml filenames
    railSpecs: [],        // [{filename, railName, refDes, component, specifications, variables}]
    icSpecNames: [],      // list of IC component names that have a loaded .spec (e.g. ["TDA38806"])
    regpairFiles: [],     // list of loaded regpair filenames
    icRefs: [],           // detected IC ref designators
    allRefs: [],          // all ref designators
    componentTypes: {},   // {refDes: componentType}  e.g. {U93: "TDM24544"}
    mappings: [],         // [{refDes, componentType, yamlFile, selected, specFile, specifications}]
    checkResults: [],     // array of ICCheckResult
    isChecking: false,
  }),
  getters: {
    canCheck: (state) =>
      state.ascLoaded && state.bomLoaded && state.yamlFiles.length > 0,
    // Build a refDes → railSpec lookup for RuleMapping UI
    refToRailSpec: (state) => {
      const map = {}
      for (const s of state.railSpecs) map[s.refDes] = s
      return map
    },
  },
  actions: {
    setAscLoaded(data) {
      this.ascLoaded = true
      this.ascFilename = data.asc_filename || ''
      this.icRefs = data.ic_refs || []
      this.allRefs = data.all_refs || []
      this.componentTypes = data.ic_component_types || {}

      const existing = new Set(this.mappings.map(m => m.refDes))
      for (const ref of this.icRefs) {
        if (!existing.has(ref)) {
          this.mappings.push({
            refDes: ref,
            componentType: this.componentTypes[ref] || '',
            yamlFile: '',
            regpairFile: '',
            selected: false,
            specFile: '',
            specifications: {},
          })
        } else {
          const m = this.mappings.find(m => m.refDes === ref)
          if (m) m.componentType = this.componentTypes[ref] || ''
        }
      }
      this._autoMatchYaml()
      this._applyRailSpecs()
    },
    setBomLoaded() {
      this.bomLoaded = true
    },
    addYamlFiles(loadedItems) {
      // loadedItems: array of {filename} objects (or plain strings for backward compat)
      for (const item of loadedItems) {
        const fname = typeof item === 'string' ? item : item.filename
        if (!this.yamlFiles.includes(fname)) {
          this.yamlFiles.push(fname)
        }
      }
      this._autoMatchYaml()
    },
    removeYamlFile(filename) {
      this.yamlFiles = this.yamlFiles.filter(f => f !== filename)
      for (const m of this.mappings) {
        if (m.yamlFile === filename) {
          m.yamlFile = ''
          m.specFile = ''
          m.specifications = {}
        }
      }
    },
    addRegpairFiles(loadedItems) {
      for (const item of loadedItems) {
        const fname = typeof item === 'string' ? item : item.filename
        if (!this.regpairFiles.includes(fname)) {
          this.regpairFiles.push(fname)
        }
      }
    },
    addSpecs({ rail_specs = [], ic_specs = [] }) {
      // Rail specs: auto-fill IC mapping
      for (const item of rail_specs) {
        this.railSpecs = this.railSpecs.filter(s => s.refDes !== item.ref_des)
        this.railSpecs.push({
          filename: item.filename,
          railName: item.rail_name,
          refDes: item.ref_des,
          component: item.component,
          specifications: item.specifications || {},
          variables: item.variables || {},
        })
      }
      // IC specs: just track component names that have a spec loaded
      for (const item of ic_specs) {
        if (!this.icSpecNames.includes(item.component)) {
          this.icSpecNames.push(item.component)
        }
      }
      this._applyRailSpecs()
    },
    _applyRailSpecs() {
      for (const spec of this.railSpecs) {
        const m = this.mappings.find(m => m.refDes === spec.refDes)
        if (!m) continue
        // Auto-assign YAML by component name if available
        const yamlCandidate = this.yamlFiles.find(f =>
          f.replace(/\.ya?ml$/i, '').toLowerCase() === spec.component.toLowerCase()
        )
        if (yamlCandidate) m.yamlFile = yamlCandidate
        m.specFile = spec.filename
        m.specifications = spec.specifications || {}
        m.selected = true
      }
    },
    setCheckResults(results) {
      this.checkResults = results
      this.isChecking = false
    },
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
            score = 3
          } else if (base.includes(comp) || comp.includes(base)) {
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
