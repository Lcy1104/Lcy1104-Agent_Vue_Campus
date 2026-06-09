<template>
  <div class="login-page">
    <!-- 背景装饰 -->
    <div class="login-page__background">
      <div class="login-page__shape shape-1"></div>
      <div class="login-page__shape shape-2"></div>
      <div class="login-page__shape shape-3"></div>
    </div>

    <!-- 主卡片 -->
    <div class="login-card">
      <!-- Logo 区域 -->
      <div class="login-card__header">
        <div class="login-card__logo">
          <span class="material-icons">smart_toy</span>
        </div>
        <h1 class="login-card__title">{{ pageTitle }}</h1>
        <p class="login-card__subtitle">{{ pageSubtitle }}</p>
      </div>

      <!-- 登录表单 -->
      <form v-if="currentView === 'login'" class="login-card__form" @submit.prevent="handleLogin">
        <div class="material-input">
          <input
            v-model="loginForm.username"
            type="text"
            class="material-input__field"
            placeholder="用户名"
            required
            minlength="3"
            @input="handleLoginUsernameInput"
          />
          <span class="material-icons material-input__icon">person</span>
        </div>

        <div class="material-input password-input">
          <input
            v-model="loginForm.password"
            :type="showLoginPassword ? 'text' : 'password'"
            class="material-input__field"
            placeholder="密码"
            required
            minlength="6"
          />
          <span class="material-icons material-input__icon">lock</span>
          <span 
            class="material-icons password-toggle" 
            @click="showLoginPassword = !showLoginPassword"
          >
            {{ showLoginPassword ? 'visibility' : 'visibility_off' }}
          </span>
        </div>

        <div class="captcha-container">
          <div class="material-input captcha-input">
            <input
              v-model="loginForm.captcha_code"
              type="text"
              class="material-input__field"
              placeholder="验证码"
              required
            />
            <span class="material-icons material-input__icon">security</span>
          </div>
          <div class="captcha-image" @click="refreshCaptcha">
            <img v-if="captchaImage" :src="captchaImage" alt="验证码" />
            <div v-else class="captcha-placeholder">
              <span class="material-icons">refresh</span>
            </div>
          </div>
        </div>

        <div class="form-options">
          <label class="remember-me">
            <input type="checkbox" v-model="loginForm.remember" @change="handleRememberChange" />
            <span>记住我</span>
          </label>
          <a href="#" class="forgot-link" @click.prevent="switchView('forgot')">忘记密码？</a>
        </div>

        <div v-if="errorMessage" class="error-message">
          <span class="material-icons">error</span>
          {{ errorMessage }}
        </div>

        <button type="submit" class="material-button filled submit-button" :disabled="loading">
          <span v-if="loading" class="material-spinner"></span>
          <span v-else>
            <span class="material-icons">login</span>
            登录
          </span>
        </button>

        <div class="form-footer">
          <span>还没有账户？</span>
          <a href="#" class="link-button" @click.prevent="switchView('register')">立即注册</a>
        </div>
      </form>

      <!-- 注册表单 -->
      <form v-if="currentView === 'register'" class="login-card__form" @submit.prevent="handleRegister">
        <div class="material-input">
          <input
            v-model="registerForm.username"
            type="text"
            class="material-input__field"
            placeholder="用户名"
            required
            minlength="3"
          />
          <span class="material-icons material-input__icon">person</span>
        </div>

        <div class="material-input password-input">
          <input
            v-model="registerForm.password"
            :type="showRegisterPassword ? 'text' : 'password'"
            class="material-input__field"
            placeholder="密码"
            required
            minlength="8"
          />
          <span class="material-icons material-input__icon">lock</span>
          <span 
            class="material-icons password-toggle" 
            @click="showRegisterPassword = !showRegisterPassword"
          >
            {{ showRegisterPassword ? 'visibility' : 'visibility_off' }}
          </span>
        </div>

        <div class="material-input password-input">
          <input
            v-model="registerForm.confirmPassword"
            :type="showRegisterConfirmPassword ? 'text' : 'password'"
            class="material-input__field"
            placeholder="确认密码"
            required
          />
          <span class="material-icons material-input__icon">lock_outline</span>
          <span 
            class="material-icons password-toggle" 
            @click="showRegisterConfirmPassword = !showRegisterConfirmPassword"
          >
            {{ showRegisterConfirmPassword ? 'visibility' : 'visibility_off' }}
          </span>
        </div>

        <div class="captcha-container">
          <div class="material-input captcha-input">
            <input
              v-model="registerForm.captcha_code"
              type="text"
              class="material-input__field"
              placeholder="验证码"
              required
            />
            <span class="material-icons material-input__icon">security</span>
          </div>
          <div class="captcha-image" @click="refreshCaptcha">
            <img v-if="captchaImage" :src="captchaImage" alt="验证码" />
            <div v-else class="captcha-placeholder">
              <span class="material-icons">refresh</span>
            </div>
          </div>
        </div>

        <div v-if="errorMessage" class="error-message">
          <span class="material-icons">error</span>
          {{ errorMessage }}
        </div>

        <div v-if="successMessage" class="success-message">
          <span class="material-icons">check_circle</span>
          {{ successMessage }}
        </div>

        <button type="submit" class="material-button filled submit-button" :disabled="loading">
          <span v-if="loading" class="material-spinner"></span>
          <span v-else>
            <span class="material-icons">person_add</span>
            注册
          </span>
        </button>

        <div class="form-footer">
          <span>已有账户？</span>
          <a href="#" class="link-button" @click.prevent="switchView('login')">立即登录</a>
        </div>
      </form>

      <!-- 忘记密码表单 -->
      <form v-if="currentView === 'forgot'" class="login-card__form" @submit.prevent="handleForgotStep1">
        <div class="info-text">
          <span class="material-icons">info</span>
          <p>请输入用户名和验证码。若已通过管理员审核，将进入设置新密码；否则会提交重置申请。</p>
        </div>

        <div class="material-input">
          <input
            v-model="forgotStep1.username"
            type="text"
            class="material-input__field"
            placeholder="用户名"
            required
          />
          <span class="material-icons material-input__icon">person</span>
        </div>

        <div class="captcha-container">
          <div class="material-input captcha-input">
            <input
              v-model="forgotStep1.captcha_code"
              type="text"
              class="material-input__field"
              placeholder="验证码"
              required
            />
            <span class="material-icons material-input__icon">security</span>
          </div>
          <div class="captcha-image" @click="refreshCaptcha">
            <img v-if="captchaImage" :src="captchaImage" alt="验证码" />
            <div v-else class="captcha-placeholder">
              <span class="material-icons">refresh</span>
            </div>
          </div>
        </div>

        <div v-if="errorMessage" class="error-message">
          <span class="material-icons">error</span>
          {{ errorMessage }}
        </div>

        <div v-if="successMessage" class="success-message">
          <span class="material-icons">check_circle</span>
          {{ successMessage }}
        </div>

        <button type="submit" class="material-button filled submit-button" :disabled="loading">
          <span v-if="loading" class="material-spinner"></span>
          <span v-else>
            <span class="material-icons">arrow_forward</span>
            下一步
          </span>
        </button>

        <div class="form-footer">
          <a href="#" class="link-button" @click.prevent="switchView('login')">返回登录</a>
        </div>
      </form>

      <!-- 忘记密码 - 设置新密码 -->
      <form v-if="currentView === 'forgot-reset'" class="login-card__form" @submit.prevent="handleForgotReset">
        <div class="info-text">
          <span class="material-icons">lock_reset</span>
          <p>您的密码重置申请已通过审核，请设置新密码。</p>
        </div>

        <div class="material-input">
          <input
            v-model="forgotReset.username"
            type="text"
            class="material-input__field"
            placeholder="用户名"
            readonly
          />
          <span class="material-icons material-input__icon">person</span>
        </div>

        <div class="material-input password-input">
          <input
            v-model="forgotReset.newPassword"
            :type="showForgotNewPassword ? 'text' : 'password'"
            class="material-input__field"
            placeholder="新密码（至少8位）"
            required
            minlength="8"
          />
          <span class="material-icons material-input__icon">lock</span>
          <span 
            class="material-icons password-toggle" 
            @click="showForgotNewPassword = !showForgotNewPassword"
          >
            {{ showForgotNewPassword ? 'visibility' : 'visibility_off' }}
          </span>
        </div>

        <div class="material-input password-input">
          <input
            v-model="forgotReset.confirmPassword"
            :type="showForgotConfirmPassword ? 'text' : 'password'"
            class="material-input__field"
            placeholder="确认新密码"
            required
          />
          <span class="material-icons material-input__icon">lock_outline</span>
          <span 
            class="material-icons password-toggle" 
            @click="showForgotConfirmPassword = !showForgotConfirmPassword"
          >
            {{ showForgotConfirmPassword ? 'visibility' : 'visibility_off' }}
          </span>
        </div>

        <div class="captcha-container">
          <div class="material-input captcha-input">
            <input
              v-model="forgotReset.captcha_code"
              type="text"
              class="material-input__field"
              placeholder="验证码"
              required
            />
            <span class="material-icons material-input__icon">security</span>
          </div>
          <div class="captcha-image" @click="refreshCaptcha">
            <img v-if="captchaImage" :src="captchaImage" alt="验证码" />
            <div v-else class="captcha-placeholder">
              <span class="material-icons">refresh</span>
            </div>
          </div>
        </div>

        <div v-if="errorMessage" class="error-message">
          <span class="material-icons">error</span>
          {{ errorMessage }}
        </div>

        <div v-if="successMessage" class="success-message">
          <span class="material-icons">check_circle</span>
          {{ successMessage }}
        </div>

        <button type="submit" class="material-button filled submit-button" :disabled="loading">
          <span v-if="loading" class="material-spinner"></span>
          <span v-else>
            <span class="material-icons">lock_reset</span>
            设置新密码
          </span>
        </button>

        <div class="form-footer">
          <a href="#" class="link-button" @click.prevent="switchView('login')">返回登录</a>
        </div>
      </form>

      <!-- 修改密码弹窗 (首次登录) -->
      <div v-if="showChangePassword" class="change-password-modal">
        <div class="modal-content">
          <h3>首次登录 - 修改密码</h3>
          <p>您需要使用默认密码登录，请修改为新密码</p>
          <div class="material-input">
            <input v-model="changePasswordForm.newPassword" type="password" placeholder="新密码（至少8位）" required minlength="8" />
            <span class="material-icons material-input__icon">lock</span>
          </div>
          <div class="material-input">
            <input v-model="changePasswordForm.confirmPassword" type="password" placeholder="确认新密码" required />
            <span class="material-icons material-input__icon">lock_outline</span>
          </div>
          <button @click="submitChangePassword" class="material-button filled" :disabled="changingPassword">
            {{ changingPassword ? '修改中...' : '确认修改' }}
          </button>
        </div>
      </div>

      <!-- 版本信息 -->
      <div class="login-card__version">v1.0.0</div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { authApi } from '@/api/auth'

const router = useRouter()
const authStore = useAuthStore()

// 密码强度检查
const checkPasswordStrength = (password) => {
  const errors = []
  if (password.length < 8) {
    errors.push('密码长度至少8位')
  }
  if (!/[A-Z]/.test(password)) {
    errors.push('需包含大写字母')
  }
  if (!/[a-z]/.test(password)) {
    errors.push('需包含小写字母')
  }
  if (!/[0-9]/.test(password)) {
    errors.push('需包含数字')
  }
  if (!/[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]/.test(password)) {
    errors.push('需包含特殊字符')
  }
  return errors
}

// 当前视图: login / register / forgot
const currentView = ref('login')
const loading = ref(false)
const errorMessage = ref('')
const successMessage = ref('')
const captchaImage = ref('')
const captchaId = ref('')
const rememberedUsername = ref('')
const rememberedPassword = ref('')

// 密码显示/隐藏状态
const showLoginPassword = ref(false)
const showRegisterPassword = ref(false)
const showRegisterConfirmPassword = ref(false)

// 登录表单
const loginForm = reactive({
  username: '',
  password: '',
  captcha_code: '',
  remember: false
})

const REMEMBER_LOGIN_KEY = 'remembered_login'

const loadRememberedLogin = () => {
  const raw = localStorage.getItem(REMEMBER_LOGIN_KEY)
  if (!raw) return
  try {
    const data = JSON.parse(raw)
    rememberedUsername.value = data.username || ''
    rememberedPassword.value = data.password || ''
    loginForm.username = rememberedUsername.value
    loginForm.password = rememberedPassword.value
    loginForm.remember = Boolean(rememberedUsername.value)
  } catch (error) {
    localStorage.removeItem(REMEMBER_LOGIN_KEY)
  }
}

const saveRememberedLogin = () => {
  if (loginForm.remember) {
    localStorage.setItem(REMEMBER_LOGIN_KEY, JSON.stringify({
      username: loginForm.username,
      password: loginForm.password,
    }))
    rememberedUsername.value = loginForm.username
    rememberedPassword.value = loginForm.password
  } else {
    localStorage.removeItem(REMEMBER_LOGIN_KEY)
    rememberedUsername.value = ''
    rememberedPassword.value = ''
  }
}

const clearRememberedLogin = () => {
  localStorage.removeItem(REMEMBER_LOGIN_KEY)
  rememberedUsername.value = ''
  rememberedPassword.value = ''
}

const handleLoginUsernameInput = () => {
  if (!rememberedUsername.value) return
  if (loginForm.username === rememberedUsername.value) return
  const wasUsingRememberedPassword = loginForm.password === rememberedPassword.value
  clearRememberedLogin()
  loginForm.remember = false
  if (wasUsingRememberedPassword) loginForm.password = ''
}

const handleRememberChange = () => {
  if (!loginForm.remember) clearRememberedLogin()
}

// 注册表单
const registerForm = reactive({
  username: '',
  password: '',
  confirmPassword: '',
  captcha_code: ''
})

// 忘记密码 - 第一步（输入用户名和验证码）
const forgotStep1 = reactive({
  username: '',
  captcha_code: ''
})

// 忘记密码 - 重置密码（已有通过的申请）
const forgotReset = reactive({
  username: '',
  newPassword: '',
  confirmPassword: '',
  captcha_code: ''
})

const showForgotNewPassword = ref(false)
const showForgotConfirmPassword = ref(false)

// 修改密码
const showChangePassword = ref(false)
const changingPassword = ref(false)
const changePasswordUserId = ref('')
const changePasswordForm = reactive({
  newPassword: '',
  confirmPassword: ''
})

// 计算标题
const pageTitle = computed(() => {
  switch (currentView.value) {
    case 'login': return 'Agent Campus'
    case 'register': return '创建账户'
    case 'forgot': return '忘记密码'
    default: return 'Agent Campus'
  }
})

const pageSubtitle = computed(() => {
  switch (currentView.value) {
    case 'login': return '登录以访问您的 AI 助手'
    case 'register': return '注册新账户以开始使用'
    case 'forgot': return '申请密码重置'
    default: return ''
  }
})

// 切换视图
const switchView = (view) => {
  currentView.value = view
  errorMessage.value = ''
  successMessage.value = ''
  
  // 切换登录相关页面时只重置验证码；是否保留账号密码由“记住我”和用户输入账号决定。
  loginForm.captcha_code = ''
  
  registerForm.username = ''
  registerForm.password = ''
  registerForm.confirmPassword = ''
  registerForm.captcha_code = ''
  
  forgotStep1.username = ''
  forgotStep1.captcha_code = ''
  
  forgotReset.username = ''
  forgotReset.newPassword = ''
  forgotReset.confirmPassword = ''
  forgotReset.captcha_code = ''
  
  // 重置密码显示状态
  showLoginPassword.value = false
  showRegisterPassword.value = false
  showRegisterConfirmPassword.value = false
  showForgotNewPassword.value = false
  showForgotConfirmPassword.value = false
  
  refreshCaptcha()
}

// 忘记密码第一步 - 输入用户名和验证码
const handleForgotStep1 = async () => {
  errorMessage.value = ''
  successMessage.value = ''
  
  if (!forgotStep1.username || !forgotStep1.captcha_code) {
    errorMessage.value = '请填写所有必填项'
    return
  }
  
  loading.value = true
  
  try {
    const result = await authApi.forgotPassword({
      username: forgotStep1.username,
      captcha_id: captchaId.value,
      captcha_code: forgotStep1.captcha_code
    })
    
    if (result.data.can_reset) {
      forgotReset.username = forgotStep1.username
      forgotStep1.captcha_code = ''
      currentView.value = 'forgot-reset'
      errorMessage.value = ''
      refreshCaptcha()
    } else {
      successMessage.value = result.data.message || '密码重置申请已提交，请等待管理员审核'
      forgotStep1.username = ''
      forgotStep1.captcha_code = ''
      refreshCaptcha()
    }
  } catch (err) {
    console.error('提交申请错误:', err)
    const detail = err.response?.data?.detail
    errorMessage.value = detail || '提交失败，请重试'
    forgotStep1.captcha_code = ''
    refreshCaptcha()
  } finally {
    loading.value = false
  }
}

// 忘记密码 - 设置新密码
const handleForgotReset = async () => {
  errorMessage.value = ''
  successMessage.value = ''
  
  if (!forgotReset.username || !forgotReset.newPassword || 
      !forgotReset.confirmPassword || !forgotReset.captcha_code) {
    errorMessage.value = '请填写所有必填项'
    return
  }
  
  if (forgotReset.newPassword !== forgotReset.confirmPassword) {
    errorMessage.value = '两次输入的密码不一致'
    return
  }
  
  const passwordErrors = checkPasswordStrength(forgotReset.newPassword)
  if (passwordErrors.length > 0) {
    errorMessage.value = passwordErrors.join('；')
    return
  }
  
  loading.value = true
  
  try {
    const result = await authApi.resetPassword({
      username: forgotReset.username,
      new_password: forgotReset.newPassword,
      confirm_password: forgotReset.confirmPassword,
      captcha_id: captchaId.value,
      captcha_code: forgotReset.captcha_code
    })
    
    successMessage.value = result.data.message || '密码重置成功'
    // 清空表单
    forgotReset.username = ''
    forgotReset.newPassword = ''
    forgotReset.confirmPassword = ''
    forgotReset.captcha_code = ''
    // 返回登录页面
    setTimeout(() => {
      switchView('login')
    }, 2000)
  } catch (err) {
    console.error('重置密码错误:', err)
    const detail = err.response?.data?.detail
    errorMessage.value = detail || '重置失败，请重试'
    forgotReset.captcha_code = ''
    refreshCaptcha()
  } finally {
    loading.value = false
  }
}

// 获取验证码
const refreshCaptcha = async () => {
  try {
    const response = await authApi.getCaptcha()
    captchaImage.value = response.data.image_data
    captchaId.value = response.data.captcha_id
    errorMessage.value = ''  // 清除错误信息
  } catch (error) {
    console.error('获取验证码失败:', error)
    console.error('错误详情:', error.response?.status, error.response?.data)
    errorMessage.value = '获取验证码失败，请刷新页面重试'
  }
}

// 登录处理
const handleLogin = async () => {
  errorMessage.value = ''
  
  if (!loginForm.username || !loginForm.password || !loginForm.captcha_code) {
    errorMessage.value = '请填写所有必填项'
    return
  }
  
  loading.value = true
  
  try {
    const response = await authApi.login({
      username: loginForm.username,
      password: loginForm.password,
      captcha_id: captchaId.value,
      captcha_code: loginForm.captcha_code
    })
    
    // 登录成功
    const { access_token, user: userData } = response.data
    localStorage.setItem('token', access_token)
    localStorage.setItem('user', JSON.stringify(userData))
    saveRememberedLogin()
    // 跳转到测试页面（dashboard）
    window.location.href = '/dashboard'
    
  } catch (err) {
    console.log('Error response:', err.response?.status, err.response?.data)
    // 处理 403 - 需要修改密码，直接跳转
    const responseData = err.response?.data
    // FastAPI 包装格式: {detail: {require_password_change: true, ...}}
    const detail = responseData?.detail || responseData
    
    if (err.response?.status === 403 && detail?.require_password_change) {
      // 存储必要信息，跳转到修改密码页面
      localStorage.setItem('temp_user_id', detail.user_id)
      localStorage.setItem('temp_username', loginForm.username)
      // 强制跳转
      window.location.href = '/change-password'
      return
    }
    // 显示错误信息
    if (typeof detail === 'string') {
      errorMessage.value = detail
    } else if (detail?.message) {
      errorMessage.value = detail.message
    } else {
      errorMessage.value = '登录失败，请重试'
    }
    // 清空验证码输入框，让用户重新输入
    loginForm.captcha_code = ''
    refreshCaptcha()
  } finally {
    loading.value = false
  }
}

// 注册处理
const handleRegister = async () => {
  errorMessage.value = ''
  successMessage.value = ''
  
  if (!registerForm.username || !registerForm.password || !registerForm.captcha_code) {
    errorMessage.value = '请填写所有必填项'
    return
  }
  
  if (registerForm.password !== registerForm.confirmPassword) {
    errorMessage.value = '两次输入的密码不一致'
    return
  }
  
  // 密码强度检查
  const passwordErrors = checkPasswordStrength(registerForm.password)
  if (passwordErrors.length > 0) {
    errorMessage.value = passwordErrors.join('；')
    return
  }
  
  loading.value = true
  
  try {
    const result = await authStore.register({
      username: registerForm.username,
      password: registerForm.password,
      captcha_id: captchaId.value,
      captcha_code: registerForm.captcha_code
    })
    
    if (result.success) {
      successMessage.value = result.message
      // 清空表单
      registerForm.username = ''
      registerForm.password = ''
      registerForm.confirmPassword = ''
      registerForm.captcha_code = ''
    } else {
      errorMessage.value = result.error
      registerForm.captcha_code = ''
      refreshCaptcha()
    }
  } catch (error) {
    errorMessage.value = '注册失败，请重试'
  } finally {
    loading.value = false
  }
}

// 提交修改密码
const submitChangePassword = async () => {
  errorMessage.value = ''
  
  if (changePasswordForm.newPassword.length < 8) {
    errorMessage.value = '密码长度不能少于8位'
    return
  }
  
  if (changePasswordForm.newPassword !== changePasswordForm.confirmPassword) {
    errorMessage.value = '两次输入的密码不一致'
    return
  }
  
  changingPassword.value = true
  
  try {
    await authApi.changePassword({
      user_id: changePasswordUserId.value,
      old_password: loginForm.password, // 原密码
      new_password: changePasswordForm.newPassword
    })
    
    // 修改成功，隐藏弹窗并重新登录
    showChangePassword.value = false
    successMessage.value = '密码修改成功，请重新登录'
    changePasswordForm.newPassword = ''
    changePasswordForm.confirmPassword = ''
  } catch (err) {
    errorMessage.value = err.response?.data?.detail || '修改密码失败'
  } finally {
    changingPassword.value = false
  }
}

// 初始化
onMounted(() => {
  loadRememberedLogin()
  refreshCaptcha()
})
</script>

<style scoped lang="scss">
@use "@/styles/variables.scss" as *;

.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  overflow: hidden;
  background: linear-gradient(135deg, #f5f5f5 0%, #e8e0ec 100%);

  &__background {
    position: absolute;
    width: 100%;
    height: 100%;
    overflow: hidden;
    z-index: 0;
  }

  &__shape {
    position: absolute;
    border-radius: 50%;
    filter: blur(60px);
    opacity: 0.6;
    animation: float 20s ease-in-out infinite;

    &.shape-1 {
      width: 300px;
      height: 300px;
      background: $primary-container;
      top: -100px;
      left: -100px;
      animation-delay: 0s;
    }

    &.shape-2 {
      width: 400px;
      height: 400px;
      background: $tertiary-container;
      bottom: -150px;
      right: -150px;
      animation-delay: -5s;
    }

    &.shape-3 {
      width: 250px;
      height: 250px;
      background: $secondary-container;
      top: 50%;
      left: 10%;
      animation-delay: -10s;
    }
  }
}

@keyframes float {
  0%, 100% { transform: translate(0, 0) scale(1); }
  33% { transform: translate(30px, -30px) scale(1.1); }
  66% { transform: translate(-20px, 20px) scale(0.9); }
}

.login-card {
  width: 100%;
  max-width: 420px;
  background: $surface;
  border-radius: 28px;
  box-shadow: 
    0 8px 32px rgba($primary-color, 0.1),
    0 2px 8px rgba(0, 0, 0, 0.08);
  padding: 48px 40px;
  position: relative;
  z-index: 1;
  animation: slideUp 0.6s cubic-bezier(0.4, 0, 0.2, 1);

  &:hover {
    box-shadow: 
      0 12px 48px rgba($primary-color, 0.15),
      0 4px 12px rgba(0, 0, 0, 0.1);
  }
}

@keyframes slideUp {
  from { opacity: 0; transform: translateY(30px); }
  to { opacity: 1; transform: translateY(0); }
}

.login-card__header {
  text-align: center;
  margin-bottom: 32px;
}

.login-card__logo {
  width: 80px;
  height: 80px;
  background: linear-gradient(135deg, $primary-color 0%, $tertiary-color 100%);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 24px;
  box-shadow: $shadow-3;

  .material-icons {
    font-size: 40px;
    color: $on-primary;
  }
}

.login-card__title {
  font-size: 28px;
  font-weight: 500;
  color: $on-surface;
  margin-bottom: 8px;
  letter-spacing: -0.5px;
}

.login-card__subtitle {
  font-size: 14px;
  color: $on-surface-variant;
  line-height: 1.5;
}

.login-card__form {
  margin-bottom: 24px;
}

.material-input {
  position: relative;
  margin-bottom: 16px;

  &__field {
    width: 100%;
    padding: 16px 16px 16px 48px;
    border: 1px solid $outline-variant;
    border-radius: $radius-small;
    background: rgba($surface-variant, 0.5);
    font-family: $font-family;
    font-size: 16px;
    color: $on-surface;
    transition: border-color 0.2s, box-shadow 0.2s;

    &:focus {
      outline: none;
      border-color: $primary-color;
      border-width: 2px;
      background: $surface;
    }

    &::placeholder {
      color: $on-surface-variant;
    }
  }

  &__icon {
    position: absolute;
    left: 16px;
    top: 50%;
    transform: translateY(-50%);
    color: $on-surface-variant;
    font-size: 20px;
    transition: color 0.2s;
  }

  &__field:focus + &__icon {
    color: $primary-color;
  }
}

.password-input {
  .material-input__field {
    padding-right: 48px;
  }
  
  .password-toggle {
    position: absolute;
    right: 16px;
    top: 50%;
    transform: translateY(-50%);
    color: $on-surface-variant;
    font-size: 20px;
    cursor: pointer;
    transition: color 0.2s;
    user-select: none;
    
    &:hover {
      color: $primary-color;
    }
  }
}

.captcha-container {
  display: flex;
  gap: 12px;
  align-items: flex-start;
  margin-bottom: 16px;
}

.captcha-input {
  flex: 1;
}

.captcha-image {
  width: 140px;  // 匹配新的验证码图片宽度
  height: 40px;
  border-radius: $radius-small;
  overflow: hidden;
  cursor: pointer;
  border: 1px solid $outline-variant;
  background: $surface-variant;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;

  &:hover {
    border-color: $primary-color;
    box-shadow: $shadow-1;
  }

  img {
    width: 100%;
    height: 100%;
    object-fit: contain;  // 改为contain确保图片完整显示
  }
}

.captcha-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;

  .material-icons {
    color: $on-surface-variant;
    font-size: 24px;
  }
}

.form-options {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  font-size: 14px;

  .remember-me {
    display: flex;
    align-items: center;
    gap: 8px;
    color: $on-surface-variant;
    cursor: pointer;

    input[type="checkbox"] {
      width: 18px;
      height: 18px;
      accent-color: $primary-color;
    }
  }

  .forgot-link {
    color: $primary-color;
    text-decoration: none;
    font-weight: 500;

    &:hover {
      text-decoration: underline;
    }
  }
}

.error-message {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  background: $error-container;
  border-radius: $radius-small;
  color: $error;
  font-size: 14px;
  margin-bottom: 16px;
  animation: shake 0.5s cubic-bezier(0.4, 0, 0.2, 1);

  .material-icons {
    font-size: 18px;
  }
}

.success-message {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  background: #e8f5e9;
  border-radius: $radius-small;
  color: #2e7d32;
  font-size: 14px;
  margin-bottom: 16px;
  animation: slideUp 0.3s ease;

  .material-icons {
    font-size: 18px;
  }
}

@keyframes shake {
  0%, 100% { transform: translateX(0); }
  25% { transform: translateX(-5px); }
  75% { transform: translateX(5px); }
}

.submit-button {
  width: 100%;
  height: 48px;
  font-size: 16px;
  margin-top: 8px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 10px 24px;
  border: none;
  border-radius: 50px;
  background: $primary-color;
  color: $on-primary;
  font-family: $font-family;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    background: color-mix(in srgb, $primary-color 92%, black);
    box-shadow: $shadow-2;
  }

  &:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }
}

.material-spinner {
  width: 24px;
  height: 24px;
  border: 3px solid rgba($on-primary, 0.3);
  border-top-color: $on-primary;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.form-footer {
  text-align: center;
  margin-top: 24px;
  padding-top: 16px;
  border-top: 1px solid $outline-variant;
  font-size: 14px;
  color: $on-surface-variant;

  .link-button {
    color: $primary-color;
    text-decoration: none;
    font-weight: 500;
    margin-left: 4px;

    &:hover {
      text-decoration: underline;
    }
  }
}

.info-text {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 16px;
  background: $primary-container;
  border-radius: $radius-medium;
  margin-bottom: 24px;

  .material-icons {
    color: $primary-color;
    font-size: 20px;
    margin-top: 2px;
  }

  p {
    color: $on-primary-container;
    font-size: 14px;
    line-height: 1.5;
    margin: 0;
  }
}

.login-card__version {
  position: absolute;
  bottom: 12px;
  right: 16px;
  font-size: 11px;
  color: $on-surface-variant;
  opacity: 0.6;
}

// 响应式
@media (max-width: 480px) {
  .login-card {
    max-width: 100%;
    border-radius: 0;
    box-shadow: none;
    min-height: 100vh;
  }

  .login-page {
    background: $surface;
  }

  .login-page__background {
    display: none;
  }
}
</style>
