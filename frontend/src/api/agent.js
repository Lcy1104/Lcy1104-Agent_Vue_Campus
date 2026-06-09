import api from './index'

export const agentApi = {
  listPublicStrategies: () => api.get('/agent/strategies'),
  listStrategies: () => api.get('/admin/agent/strategies'),
  listConfigs: () => api.get('/admin/agent/configs'),
  updateConfig: (strategyName, data) => api.put(`/admin/agent/configs/${strategyName}`, data)
}

export default agentApi
