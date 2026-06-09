<template>
  <div class="login-page">
    <!-- 修改密码弹窗 -->
    <div v-if="showChangePassword" class="modal-overlay">
      <div class="modal-card">
        <h3>首次登录 - 修改密码</h3>
        <p>请修改默认密码后再继续使用</p>
        <input v-model="changePasswordForm.oldPassword" type="password" placeholder="原密码 (admin123)" />
        <input v-model="changePasswordForm.newPassword" type="password" placeholder="新密码（至少8位）" />
        <input v-model="changePasswordForm.confirmPassword" type="password" placeholder="确认新密码" />
        <button @click="submitChangePassword" :disabled="changing">
          {{ changing ? '提交中...' : '确认修改' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
const showChangePassword = ref(false)
const changePasswordForm = reactive({
  userId: '',
  oldPassword: '',
  newPassword: '',
  confirmPassword: ''
})

// 在登录失败处理中检测是否需要修改密码
if (error.response?.status === 403 && error.response.data?.require_password_change) {
  showChangePassword.value = true
  changePasswordForm.userId = error.response.data.user_id
}
</script>
