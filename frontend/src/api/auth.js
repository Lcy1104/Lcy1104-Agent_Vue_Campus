import api from './index'

// 认证相关 API
export const authApi = {
  // 获取验证码
  getCaptcha: () => api.get('/auth/captcha'),
  
  // 登录
  login: (data) => api.post('/auth/login', data),

  // 当前用户资料
  getProfile: () => api.get('/auth/me'),
  
  // 注册
  register: (data) => api.post('/auth/register', data),
  
  // 忘记密码
  forgotPassword: (data) => api.post('/auth/forgot-password', data),
  
  // 检查是否可以重置密码
  checkResetStatus: (data) => api.post('/auth/check-reset-status', data),
  
  // 重置密码
  resetPassword: (data) => api.post('/auth/reset-password', data),
  
  // 修改密码
  changePassword: (data) => api.post('/auth/change-password', data)
}

export default authApi
