import api from './index'

export const audioApi = {
  transcribe: (formData, language = 'zh-CN') => {
    if (language && !formData.has('language')) formData.append('language', language)
    return api.post('/audio/transcribe', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 0
    })
  },
  transcribeMicrophone: (options = {}) => api.post('/audio/transcribe/microphone', options, { timeout: 0 }),
  tts: (text, options = {}) => api.post('/audio/tts', { text, ...options }, { responseType: 'blob', timeout: 0 })
}

export default audioApi
