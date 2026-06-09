<template>
  <div class="login-page">
    <!-- 背景装饰 -->
    <div class="login-page__background">
      <div class="login-page__shape shape-1"></div>
      <div class="login-page__shape shape-2"></div>
      <div class="login-page__shape shape-3"></div>
    </div>

    <!-- 修改密码卡片 -->
    <div class="login-card">
      <!-- Logo 区域 -->
      <div class="login-card__header">
        <div class="login-card__logo">
          <span class="material-icons">lock_reset</span>
        </div>
        <h1 class="login-card__title">修改密码</h1>
        <p class="login-card__subtitle">
          首次登录需要修改默认密码
        </p>
      </div>

      <!-- 修改密码表单 -->
      <form class="login-card__form" @submit.prevent="handleChangePassword">
        <div class="info-text">
          <span class="material-icons">info</span>
          <p>用户: {{ username }}</p>
        </div>

        <div class="material-input">
          <input
            v-model="form.oldPassword"
            type="password"
            class="material-input__field"
            placeholder="原密码"
            required
          />
          <span class="material-icons material-input__icon">lock</span>
        </div>

        <div class="material-input">
          <input
            v-model="form.newPassword"
            type="password"
            class="material-input__field"
            placeholder="新密码（至少8位）"
            required
            minlength="8"
          />
          <span class="material-icons material-input__icon">lock_outline</span>
        </div>

        <div class="material-input">
          <input
            v-model="form.confirmPassword"
            type="password"
            class="material-input__field"
            placeholder="确认新密码"
            required
          />
          <span class="material-icons material-input__icon">verified</span>
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
            <span class="material-icons">save</span>
            确认修改
          </span>
        </button>

        <div class="form-footer">
          <a href="#" class="link-button" @click.prevent="goToLogin">返回登录</a>
        </div>
      </form>

      <!-- 版本信息 -->
      <div class="login-card__version">v1.0.0</div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { authApi } from '@/api/auth'

const router = useRouter()

const userId = ref('')
const username = ref('')
const loading = ref(false)
const errorMessage = ref('')
const successMessage = ref('')

const form = reactive({
  oldPassword: '',
  newPassword: '',
  confirmPassword: ''
})

onMounted(() => {
  // 获取临时存储的用户信息
  userId.value = localStorage.getItem('temp_user_id') || ''
  username.value = localStorage.getItem('temp_username') || ''
  
  if (!userId.value) {
    // 没有用户信息，返回登录
    router.push('/login')
  }
})

const handleChangePassword = async () => {
  errorMessage.value = ''
  successMessage.value = ''
  
  // 验证
  if (!form.oldPassword || !form.newPassword || !form.confirmPassword) {
    errorMessage.value = '请填写所有必填项'
    return
  }
  
  if (form.newPassword.length < 8) {
    errorMessage.value = '密码长度不能少于8位'
    return
  }
  
  if (form.newPassword !== form.confirmPassword) {
    errorMessage.value = '两次输入的密码不一致'
    return
  }
  
  loading.value = true
  
  try {
    await authApi.changePassword({
      user_id: userId.value,
      old_password: form.oldPassword,
      new_password: form.newPassword
    })
    
    successMessage.value = '密码修改成功，请重新登录'
    
    // 清除临时信息
    localStorage.removeItem('temp_user_id')
    localStorage.removeItem('temp_username')
    
    // 2秒后跳转到登录
    setTimeout(() => {
      router.push('/login')
    }, 2000)
    
  } catch (err) {
    errorMessage.value = err.response?.data?.detail || '修改密码失败，请重试'
  } finally {
    loading.value = false
  }
}

const goToLogin = () => {
  localStorage.removeItem('temp_user_id')
  localStorage.removeItem('temp_username')
  router.push('/login')
}
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
