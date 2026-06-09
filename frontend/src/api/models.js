import api from './index'

export const modelsApi = {
  listVisibleModels: () => api.get('/models/visible'),
  listBackends: () => api.get('/admin/model-backends'),
  listBackendStatuses: () => api.get('/admin/model-backends/status'),
  createBackend: (data) => api.post('/admin/model-backends', data),
  updateBackend: (id, data) => api.put(`/admin/model-backends/${id}`, data),
  deleteBackend: (id) => api.delete(`/admin/model-backends/${id}`),
  testBackend: (id) => api.get(`/admin/model-backends/${id}/status`),
  scanBackend: (id) => api.get(`/admin/model-backends/${id}/scan`),
  importBackendModels: (id, modelNames) => api.post(`/admin/model-backends/${id}/import`, { model_names: modelNames }),
  listModels: () => api.get('/admin/models'),
  createModel: (data) => api.post('/admin/models', data),
  updateModel: (id, data) => api.put(`/admin/models/${id}`, data),
  deleteModel: (id) => api.delete(`/admin/models/${id}`)
}

export default modelsApi
