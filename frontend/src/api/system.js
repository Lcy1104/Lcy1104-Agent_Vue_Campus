import api from './index'

export const systemApi = {
  listConfigs: () => api.get('/admin/system/configs'),
  updateConfig: (key, value) => api.put(`/admin/system/configs/${key}`, { value }),
  updateConfigs: (values) => api.put('/admin/system/configs', { values })
}

export default systemApi
