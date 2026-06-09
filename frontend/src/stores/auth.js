import { defineStore } from 'pinia'
import { ref } from 'vue'
import { authApi } from '@/api/auth'

export const useAuthStore = defineStore('auth', () => {
  // State
  const token = ref(localStorage.getItem('token') || '')
  const user = ref(JSON.parse(localStorage.getItem('user') || 'null'))
  const loading = ref(false)
  const error = ref('')

  // Actions
  const setToken = (newToken) => {
    token.value = newToken
    localStorage.setItem('token', newToken)
  }

  const setUser = (userData) => {
    user.value = userData
    localStorage.setItem('user', JSON.stringify(userData))
  }

  const clearAuth = () => {
    token.value = ''
    user.value = null
    localStorage.removeItem('token')
    localStorage.removeItem('user')
  }

  const login = async (loginData) => {
    loading.value = true
    error.value = ''
    
    try {
      const response = await authApi.login(loginData)
      const { access_token, user: userData } = response.data
      
      setToken(access_token)
      setUser(userData)
      
      return { success: true }
    } catch (err) {
      error.value = err.response?.data?.detail || '登录失败，请重试'
      return { success: false, error: error.value }
    } finally {
      loading.value = false
    }
  }

  const register = async (registerData) => {
    loading.value = true
    error.value = ''
    
    try {
      const response = await authApi.register(registerData)
      return { success: true, message: response.data.message }
    } catch (err) {
      error.value = err.response?.data?.detail || '注册失败，请重试'
      return { success: false, error: error.value }
    } finally {
      loading.value = false
    }
  }

  const logout = () => {
    clearAuth()
  }

  return {
    token,
    user,
    loading,
    error,
    login,
    register,
    logout,
    isAuthenticated: () => !!token.value
  }
})
