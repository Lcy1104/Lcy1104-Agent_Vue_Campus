import api from './index'

export default {
  listTools: () => api.get('/tools'),
  listEnabledTools: () => api.get('/tools/enabled'),
  createTool: (data) => api.post('/tools', data),
  updateTool: (id, data) => api.put(`/tools/${id}`, data),
  testTool: (id) => api.post(`/tools/${id}/test`),
  deleteTool: (id) => api.delete(`/tools/${id}`)
}
