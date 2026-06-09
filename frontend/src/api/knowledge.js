import api from './index'

export const knowledgeApi = {
  getUploadPolicy: () => api.get('/knowledge/upload-policy'),
  listCollections: () => api.get('/knowledge/collections'),
  createCollection: (data) => api.post('/knowledge/collections', data),
  updateCollectionName: (id, data) => api.put(`/knowledge/collections/${id}`, data),
  deleteCollection: (id, params = {}) => api.delete(`/knowledge/collections/${id}`, { params }),
  listDocuments: (params) => api.get('/knowledge/documents', { params }),
  uploadDocument: (formData, config = {}) => api.post('/knowledge/documents/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    ...config
  }),
  uploadDocuments: (formData) => api.post('/knowledge/documents/uploads', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  }),
  addUrls: (data) => api.post('/knowledge/documents/urls', data, { timeout: 0 }),
  updateVisibility: (id, isPublic) => api.put(`/knowledge/documents/${id}/visibility`, { is_public: isPublic }),
  updateCollection: (id, data) => api.put(`/knowledge/documents/${id}/collection`, data),
  updateTitle: (id, filename) => api.put(`/knowledge/documents/${id}/title`, { filename }),
  listChunks: (id) => api.get(`/knowledge/documents/${id}/chunks`),
  updateChunk: (id, chunkText) => api.put(`/knowledge/chunks/${id}`, { chunk_text: chunkText }),
  deleteChunk: (id) => api.delete(`/knowledge/chunks/${id}`),
  retryDocument: (id) => api.post(`/knowledge/documents/${id}/retry`),
  reindexAllDocuments: () => api.post('/knowledge/documents/reindex'),
  deleteDocument: (id) => api.delete(`/knowledge/documents/${id}`)
}

export default knowledgeApi
