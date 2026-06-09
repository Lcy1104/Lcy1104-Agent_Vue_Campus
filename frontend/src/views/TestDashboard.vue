<template>
  <div class="dashboard-page">
    <!-- 顶部导航 -->
    <header class="dashboard-header">
      <div class="header-brand">
        <span class="material-icons">smart_toy</span>
        <span>Agent Campus</span>
      </div>
      <div class="header-user">
        <span class="user-name">{{ user?.username }}</span>
        <span class="user-role">{{ user?.role === 'admin' ? '管理员' : '普通用户' }}</span>
        <button class="material-button text" @click="logout">
          <span class="material-icons">logout</span>
          退出
        </button>
      </div>
    </header>

    <!-- 主内容 -->
    <main class="dashboard-main">
      <!-- 欢迎区域 -->
      <div class="welcome-card">
        <div class="welcome-icon">
          <span class="material-icons">check_circle</span>
        </div>
        <div class="welcome-content">
          <h1>登录成功！</h1>
          <p>欢迎回来，{{ user?.username }}</p>
          <p class="login-time">登录时间: {{ loginTime }}</p>
        </div>
      </div>

      <!-- 功能卡片 -->
      <div class="feature-grid">
        <div class="feature-card" @click="goToChat">
          <span class="material-icons feature-icon">chat</span>
          <h3>开始对话</h3>
          <p>与 AI 助手进行对话</p>
        </div>

        <div class="feature-card" @click="goToTools">
          <span class="material-icons feature-icon">hub</span>
          <h3>MCP 与外部 API</h3>
          <p>管理 Agent 可用工具、公有/私有和接口配置</p>
        </div>

        <div class="feature-card" @click="goToKnowledge">
          <span class="material-icons feature-icon">folder_managed</span>
          <h3>知识库</h3>
          <p>上传资料、管理文档分段</p>
        </div>

        <div v-if="user?.role === 'admin'" class="feature-card admin-card" @click="goToAdmin">
          <span class="material-icons feature-icon">admin_panel_settings</span>
          <h3>管理后台</h3>
          <p>用户审核、系统配置</p>
        </div>

        <div class="feature-card" @click="goToProfile">
          <span class="material-icons feature-icon">person</span>
          <h3>个人中心</h3>
          <p>修改密码、个人信息</p>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()

const user = ref({})
const loginTime = ref('')

onMounted(() => {
  // 获取用户信息
  const userData = localStorage.getItem('user')
  if (userData) {
    user.value = JSON.parse(userData)
  }
  
  loginTime.value = new Date().toLocaleString('zh-CN')
})

const logout = () => {
  localStorage.removeItem('token')
  localStorage.removeItem('user')
  router.push('/login')
}

const goToChat = () => {
  router.push('/chat')
}

const goToTools = () => {
  router.push('/tools')
}

const goToKnowledge = () => {
  router.push('/knowledge')
}

const goToAdmin = () => {
  router.push('/admin')
}

const goToProfile = () => {
  router.push('/profile')
}
</script>

<style scoped lang="scss">
.dashboard-page {
  min-height: 100vh;
  background: #f5f5f5;
}

.dashboard-header {
  background: #fff;
  padding: 16px 32px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  box-shadow: 0 2px 4px rgba(0,0,0,0.05);
}

.header-brand {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 20px;
  font-weight: 500;
  color: #6750a4;

  .material-icons {
    font-size: 28px;
  }
}

.header-user {
  display: flex;
  align-items: center;
  gap: 16px;
}

.user-name {
  font-weight: 500;
  color: #1c1b1f;
}

.user-role {
  font-size: 13px;
  color: #6750a4;
  background: #eaddff;
  padding: 4px 12px;
  border-radius: 16px;
}

.material-button.text {
  display: flex;
  align-items: center;
  gap: 8px;
  background: none;
  border: none;
  cursor: pointer;
  color: #49454f;
  font-size: 14px;
  padding: 8px 16px;
  border-radius: 20px;
  transition: background 0.2s;

  &:hover {
    background: rgba(103, 80, 164, 0.08);
  }

  .material-icons {
    font-size: 20px;
  }
}

.dashboard-main {
  max-width: 1000px;
  margin: 0 auto;
  padding: 40px 20px;
}

.welcome-card {
  background: #fff;
  border-radius: 16px;
  padding: 40px;
  display: flex;
  align-items: center;
  gap: 24px;
  margin-bottom: 32px;
  box-shadow: 0 4px 12px rgba(0,0,0,0.08);
}

.welcome-icon {
  width: 80px;
  height: 80px;
  background: #e8f5e9;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;

  .material-icons {
    font-size: 40px;
    color: #2e7d32;
  }
}

.welcome-content {
  h1 {
    font-size: 28px;
    font-weight: 500;
    color: #1c1b1f;
    margin-bottom: 8px;
  }

  p {
    font-size: 16px;
    color: #49454f;
    margin-bottom: 4px;
  }

  .login-time {
    font-size: 14px;
    color: #79747e;
  }
}

.feature-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 20px;
}

.feature-card {
  background: #fff;
  border-radius: 16px;
  padding: 32px 24px;
  text-align: center;
  cursor: pointer;
  transition: all 0.3s;
  border: 2px solid transparent;

  &:hover {
    transform: translateY(-4px);
    box-shadow: 0 8px 24px rgba(0,0,0,0.12);
    border-color: #6750a4;
  }

  .feature-icon {
    font-size: 48px;
    color: #6750a4;
    margin-bottom: 16px;
  }

  h3 {
    font-size: 18px;
    font-weight: 500;
    color: #1c1b1f;
    margin-bottom: 8px;
  }

  p {
    font-size: 14px;
    color: #79747e;
  }

  &.admin-card {
    background: linear-gradient(135deg, #6750a4 0%, #7c67b8 100%);
    color: #fff;

    .feature-icon,
    h3,
    p {
      color: #fff;
    }

    &:hover {
      box-shadow: 0 8px 24px rgba(103, 80, 164, 0.3);
    }
  }
}
</style>
