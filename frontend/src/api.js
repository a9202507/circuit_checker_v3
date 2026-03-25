import axios from 'axios'

function formData(file) {
  const fd = new FormData()
  fd.append('file', file)
  return fd
}

export const uploadASC = (file) =>
  axios.post('/api/upload/asc', formData(file), {
    headers: { 'Content-Type': 'multipart/form-data' },
  })

export const uploadBOM = (file) =>
  axios.post('/api/upload/bom', formData(file), {
    headers: { 'Content-Type': 'multipart/form-data' },
  })

export const uploadYAML = (files) => {
  const fd = new FormData()
  for (const f of files) fd.append('files', f)
  return axios.post('/api/upload/yaml', fd, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

export const getStatus = () => axios.get('/api/status')

export const runCheck = (mappings) =>
  axios.post('/api/check', { mappings })

export const getYamlContent = (filename) =>
  axios.get(`/api/yaml/${encodeURIComponent(filename)}`)

export const deleteYaml = (filename) =>
  axios.delete(`/api/yaml/${encodeURIComponent(filename)}`)

export const generateYaml = (ruleset) =>
  axios.post('/api/yaml/generate', ruleset)

export const exportReport = (results, yamlFilesUsed) =>
  axios.post('/api/export', { results, yaml_files_used: yamlFilesUsed }, { responseType: 'blob' })
