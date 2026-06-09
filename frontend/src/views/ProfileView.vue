<template>
  <div class="profile-page">
    <header class="profile-header">
      <button class="material-button outlined" @click="router.push('/dashboard')">
        <span class="material-icons">arrow_back</span>
        返回主页
      </button>
      <button class="material-button text" @click="loadProfile">
        <span class="material-icons">refresh</span>
        刷新
      </button>
    </header>

    <div v-if="notice.message" class="notice" :class="notice.type">
      <span class="material-icons">{{ notice.type === 'error' ? 'error' : 'check_circle' }}</span>
      <span>{{ notice.message }}</span>
    </div>

    <main class="profile-grid">
      <section class="profile-card identity-card">
        <div class="avatar-box">
          <span>{{ avatarText }}</span>
        </div>
        <div>
          <p class="eyebrow">Personal Profile</p>
          <h2>{{ profile.username || '-' }}</h2>
          <p>{{ roleText(profile.role) }} · {{ statusText(profile.registration_status) }}</p>
        </div>
      </section>

      <section class="profile-card info-card">
        <div class="card-header">
          <h3>账号资料</h3>
          <span class="material-icons">badge</span>
        </div>
        <div v-if="loading" class="loading-state">
          <div class="material-spinner"></div>
          <p>加载资料中...</p>
        </div>
        <div v-else class="info-list">
          <div><span>用户 ID</span><strong>{{ profile.id }}</strong></div>
          <div><span>用户名</span><strong>{{ profile.username }}</strong></div>
          <div><span>角色</span><strong>{{ roleText(profile.role) }}</strong></div>
          <div><span>账号状态</span><strong>{{ statusText(profile.registration_status) }}</strong></div>
          <div><span>强制改密</span><strong>{{ profile.force_password_change ? '是' : '否' }}</strong></div>
          <div><span>创建时间</span><strong>{{ formatTime(profile.created_at) }}</strong></div>
          <div><span>更新时间</span><strong>{{ formatTime(profile.updated_at) }}</strong></div>
          <div><span>最近登录</span><strong>{{ formatTime(profile.last_login_at) }}</strong></div>
        </div>
      </section>

      <section class="profile-card password-card">
        <div class="card-header">
          <h3>修改密码</h3>
          <span class="material-icons">lock_reset</span>
        </div>
        <form @submit.prevent="changePassword">
          <label>
            <span>旧密码</span>
            <input v-model="passwordForm.old_password" type="password" autocomplete="current-password" required />
          </label>
          <label>
            <span>新密码</span>
            <input v-model="passwordForm.new_password" type="password" autocomplete="new-password" minlength="8" required />
          </label>
          <label>
            <span>确认新密码</span>
            <input v-model="passwordForm.confirm_password" type="password" autocomplete="new-password" minlength="8" required />
          </label>
          <button class="material-button filled" type="submit" :disabled="savingPassword">
            {{ savingPassword ? '提交中...' : '保存新密码' }}
          </button>
        </form>
      </section>
    </main>
  </div>
</template>

<script setup>
import { computed, reactive, ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import authApi from '@/api/auth'

const router = useRouter()
const loading = ref(true)
const savingPassword = ref(false)
const profile = reactive({})
const notice = reactive({ type: 'success', message: '' })
const passwordForm = reactive({ old_password: '', new_password: '', confirm_password: '' })

const avatarText = computed(() => (profile.username || '?').slice(0, 1).toUpperCase())

const showNotice = (message, type = 'success') => {
  notice.type = type
  notice.message = message
  window.clearTimeout(showNotice.timer)
  showNotice.timer = window.setTimeout(() => {
    notice.message = ''
  }, 3200)
}

const loadProfile = async () => {
  loading.value = true
  try {
    const response = await authApi.getProfile()
    Object.assign(profile, response.data)
    localStorage.setItem('user', JSON.stringify({ id: profile.id, username: profile.username, role: profile.role }))
  } catch (error) {
    showNotice(error.response?.data?.detail || '加载个人资料失败', 'error')
  } finally {
    loading.value = false
  }
}

const changePassword = async () => {
  if (passwordForm.new_password !== passwordForm.confirm_password) {
    showNotice('两次输入的新密码不一致', 'error')
    return
  }
  savingPassword.value = true
  try {
    await authApi.changePassword({
      user_id: profile.id,
      old_password: passwordForm.old_password,
      new_password: passwordForm.new_password
    })
    passwordForm.old_password = ''
    passwordForm.new_password = ''
    passwordForm.confirm_password = ''
    showNotice('密码已修改')
  } catch (error) {
    showNotice(error.response?.data?.detail || '修改密码失败', 'error')
  } finally {
    savingPassword.value = false
  }
}

const roleText = (role) => role === 'admin' ? '管理员' : role === 'user' ? '普通用户' : '-'
const statusText = (status) => ({ active: '正常', pending_review: '待审核', disabled: '已禁用' }[status] || status || '-')
const formatTime = (time) => time ? new Date(time).toLocaleString('zh-CN') : '-'

onMounted(loadProfile)
</script>

<style scoped lang="scss">
.profile-page { min-height: 100vh; padding: $spacing-xl; background: #f5f5f5; }
.profile-header, .notice, .card-header { display: flex; align-items: center; }
.profile-header { justify-content: space-between; gap: $spacing-md; margin-bottom: $spacing-lg; }
.notice { gap: $spacing-sm; padding: 12px 16px; border-radius: $radius-large; background: #dff7e8; color: #146c2e; margin-bottom: $spacing-md; }
.notice.error { background: $error-container; color: $error; }
.profile-grid { display: grid; grid-template-columns: minmax(300px, 0.8fr) minmax(420px, 1.2fr); gap: $spacing-lg; max-width: 1180px; margin: 0 auto; }
.profile-card { background: $surface; border-radius: $radius-large; box-shadow: $shadow-1; padding: $spacing-lg; }
.identity-card { grid-column: 1 / -1; display: flex; align-items: center; gap: $spacing-lg; background: linear-gradient(135deg, $primary-container, $secondary-container); }
.avatar-box { display: grid; place-items: center; width: 84px; height: 84px; border-radius: $radius-large; background: $primary-color; color: $on-primary; font-size: 34px; font-weight: 700; }
.eyebrow { color: $primary-color; font-size: 12px; letter-spacing: 0.14em; text-transform: uppercase; margin-bottom: $spacing-xs; }
h2 { color: $on-surface; font-size: 30px; }
h3 { color: $on-surface; }
.card-header { justify-content: space-between; margin-bottom: $spacing-md; }
.card-header .material-icons { color: $primary-color; }
.loading-state { min-height: 260px; display: grid; place-items: center; gap: $spacing-md; color: $on-surface-variant; }
.info-list { display: grid; gap: $spacing-sm; }
.info-list div { display: grid; grid-template-columns: 110px minmax(0, 1fr); gap: $spacing-md; padding: 12px 0; border-bottom: 1px solid $outline-variant; }
.info-list span { color: $on-surface-variant; }
.info-list strong { color: $on-surface; overflow-wrap: anywhere; }
form { display: grid; gap: $spacing-md; }
label { display: flex; flex-direction: column; gap: $spacing-xs; color: $on-surface-variant; font-size: 13px; }
input { height: 44px; border: 1px solid $outline; border-radius: $radius-small; padding: 0 12px; background: transparent; color: $on-surface; }
@media (max-width: 900px) { .profile-grid { grid-template-columns: 1fr; } .identity-card { align-items: flex-start; flex-direction: column; } }
@media (max-width: 560px) { .profile-page { padding: $spacing-md; } .info-list div { grid-template-columns: 1fr; gap: 4px; } }
</style>
