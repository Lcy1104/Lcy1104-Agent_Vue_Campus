import api from './index'

export const sessionsApi = {
  listSessions: (params = {}) => api.get('/sessions', { params }),
  createSession: (data = {}) => api.post('/sessions', data),
  updateSession: (id, data) => api.put(`/sessions/${id}`, data),
  preflightMessage: (id, data) => api.post(`/sessions/${id}/preflight`, data),
  deleteSession: (id) => api.delete(`/sessions/${id}`),
  listMessages: (id) => api.get(`/sessions/${id}/messages`)
}

export default sessionsApi
