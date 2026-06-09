<template>
  <div class="admin-layout">
    <!-- 顶部导航 -->
    <header class="admin-header">
      <div class="header-brand">
        <span class="material-icons">smart_toy</span>
        <span>Agent Campus - 管理后台</span>
      </div>
      <div class="header-actions">
        <button class="material-button text home-button" @click="goHome">
          <span class="material-icons">home</span>
          返回主页
        </button>
        <div class="notification-bell" @click="showNotifications = !showNotifications">
          <span class="material-icons">notifications</span>
          <span v-if="unreadCount > 0" class="badge">{{ unreadCount }}</span>
        </div>
        <span class="user-name">{{ user?.username }}</span>
        <button class="material-button text" @click="logout">
          <span class="material-icons">logout</span>
        </button>
      </div>
    </header>

    <!-- 侧边栏 -->
    <aside class="admin-sidebar">
      <nav class="sidebar-nav">
        <router-link to="/admin/dashboard" class="nav-item" exact-active-class="active">
          <span class="material-icons">dashboard</span>
          <span>概览</span>
        </router-link>
        
        <router-link to="/admin/pending-users" class="nav-item" exact-active-class="active">
          <span class="material-icons">person_add</span>
          <span>待审核用户</span>
          <span v-if="pendingUsersCount > 0" class="nav-badge">{{ pendingUsersCount }}</span>
        </router-link>
        
        <router-link to="/admin/pending-resets" class="nav-item" exact-active-class="active">
          <span class="material-icons">lock_reset</span>
          <span>密码重置</span>
          <span v-if="pendingResetsCount > 0" class="nav-badge">{{ pendingResetsCount }}</span>
        </router-link>
        
        <router-link to="/admin/users" class="nav-item" exact-active-class="active">
          <span class="material-icons">people</span>
          <span>用户管理</span>
        </router-link>
        
        <div class="nav-divider"></div>
        
        <router-link to="/admin/models" class="nav-item" exact-active-class="active">
          <span class="material-icons">model_training</span>
          <span>模型管理</span>
        </router-link>

        <router-link to="/admin/agent" class="nav-item" exact-active-class="active">
          <span class="material-icons">psychology</span>
          <span>Agent配置</span>
        </router-link>
        
        <router-link to="/admin/system" class="nav-item" exact-active-class="active">
          <span class="material-icons">settings</span>
          <span>系统设置</span>
        </router-link>
      </nav>
    </aside>

    <!-- 主内容区 -->
    <main class="admin-main">
      <router-view v-slot="{ Component, route }">
        <keep-alive>
          <component :is="Component" :key="route.name" />
        </keep-alive>
      </router-view>
    </main>

    <!-- 通知弹窗 -->
    <div v-if="showNotifications" class="notification-panel">
      <div class="notification-header">
        <h3>通知</h3>
        <button class="material-button text" @click="markAllRead">
          全部已读
        </button>
      </div>
      <div class="notification-list">
        <div 
          v-for="notif in notifications" 
          :key="notif.id"
          class="notification-item"
          :class="{ 'unread': !notif.read }"
          @click="handleNotification(notif)"
        >
          <span class="material-icons">{{ getNotificationIcon(notif.type) }}</span>
          <div class="notification-content">
            <h4>{{ notif.title }}</h4>
            <p>{{ notif.message }}</p>
            <time>{{ notif.time }}</time>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import api from '@/api'

const router = useRouter()

const user = ref({ username: 'admin', role: 'admin' })
const showNotifications = ref(false)
const notifications = ref([])
const unreadCount = ref(0)
const pendingUsersCount = ref(0)
const pendingResetsCount = ref(0)

// WebSocket 连接
let ws = null

const connectWebSocket = () => {
  const token = localStorage.getItem('token')
  if (!token) return
  
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const host = window.location.port === '5173' ? 'localhost:8000' : window.location.host
  ws = new WebSocket(`${protocol}//${host}/ws/notifications?token=${token}`)
  
  ws.onmessage = (event) => {
    const data = JSON.parse(event.data)
    handleWebSocketMessage(data)
  }
  
  ws.onerror = (error) => {
    console.error('WebSocket error:', error)
  }
  
  ws.onclose = () => {
    // 5秒后重连
    setTimeout(connectWebSocket, 5000)
  }
}

const fetchPendingCounts = async () => {
  try {
    const [usersResponse, resetsResponse] = await Promise.all([
      api.get('/admin/users/pending'),
      api.get('/admin/password-resets/pending')
    ])
    pendingUsersCount.value = usersResponse.data.total || 0
    pendingResetsCount.value = resetsResponse.data.total || 0
  } catch (error) {
    console.error('Failed to fetch pending counts:', error)
  }
}

const refreshAdminData = (reason) => {
  fetchPendingCounts()
  window.dispatchEvent(new CustomEvent('admin-refresh', { detail: { reason } }))
}

const handleWebSocketMessage = (data) => {
  if (data.type === 'registration_pending') {
    pendingUsersCount.value++
    notifications.value.unshift({
      id: Date.now(),
      type: data.type,
      title: data.title,
      message: data.message,
      time: new Date().toLocaleTimeString(),
      read: false,
      data: data.data
    })
    unreadCount.value++
    window.dispatchEvent(new CustomEvent('admin-refresh', { detail: { reason: data.type } }))
  } else if (data.type === 'password_reset_pending') {
    pendingResetsCount.value++
    notifications.value.unshift({
      id: Date.now(),
      type: data.type,
      title: data.title,
      message: data.message,
      time: new Date().toLocaleTimeString(),
      read: false,
      data: data.data
    })
    unreadCount.value++
    window.dispatchEvent(new CustomEvent('admin-refresh', { detail: { reason: data.type } }))
  } else if (data.type === 'user_password_changed' || data.type === 'user_created' || data.type === 'user_updated') {
    refreshAdminData(data.type)
  }
}

const getNotificationIcon = (type) => {
  switch (type) {
    case 'registration_pending': return 'person_add'
    case 'password_reset_pending': return 'lock_reset'
    default: return 'notifications'
  }
}

const handleNotification = (notif) => {
  notif.read = true
  unreadCount.value = Math.max(0, unreadCount.value - 1)
  
  if (notif.data?.action === 'review_registration') {
    router.push('/admin/pending-users')
  } else if (notif.data?.action === 'review_password_reset') {
    router.push('/admin/pending-resets')
  }
  
  showNotifications.value = false
}

const markAllRead = () => {
  notifications.value.forEach(n => n.read = true)
  unreadCount.value = 0
}

const goHome = () => {
  router.push('/dashboard')
}

const logout = () => {
  localStorage.removeItem('token')
  localStorage.removeItem('user')
  router.push('/login')
}

onMounted(() => {
  const storedUser = JSON.parse(localStorage.getItem('user') || '{}')
  if (storedUser.username) {
    user.value = storedUser
  }
  fetchPendingCounts()
  connectWebSocket()
})

onUnmounted(() => {
  if (ws) {
    ws.close()
  }
})
</script>

<style scoped lang="scss">
.admin-layout {
  display: grid;
  grid-template-columns: 260px 1fr;
  grid-template-rows: 64px 1fr;
  grid-template-areas: 
    "header header"
    "sidebar main";
  min-height: 100vh;
  background: #f5f5f5;
}

.admin-header {
  grid-area: header;
  background: #fff;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
  z-index: 100;
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

.header-actions {
  display: flex;
  align-items: center;
  gap: 16px;
}

.notification-bell {
  position: relative;
  cursor: pointer;
  padding: 8px;
  border-radius: 8px;
  transition: background 0.2s;

  &:hover {
    background: rgba(103, 80, 164, 0.08);
  }

  .material-icons {
    font-size: 24px;
    color: #49454f;
  }

  .badge {
    position: absolute;
    top: 4px;
    right: 4px;
    background: #b3261e;
    color: white;
    font-size: 11px;
    padding: 2px 5px;
    border-radius: 10px;
    min-width: 16px;
    text-align: center;
  }
}

.user-name {
  font-size: 14px;
  color: #49454f;
}

.material-button.text {
  background: none;
  border: none;
  cursor: pointer;
  padding: 8px;
  border-radius: 8px;
  color: #49454f;

  &:hover {
    background: rgba(103, 80, 164, 0.08);
  }
}

.home-button {
  border-radius: 8px;
  gap: 6px;
  color: #6750a4;
}

.admin-sidebar {
  grid-area: sidebar;
  background: #fff;
  border-right: 1px solid #e0e0e0;
  padding: 16px 0;
}

.sidebar-nav {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 12px 24px;
  color: #49454f;
  text-decoration: none;
  font-size: 14px;
  position: relative;
  transition: all 0.2s;

  .material-icons {
    font-size: 20px;
  }

  &:hover {
    background: rgba(103, 80, 164, 0.08);
    color: #6750a4;
  }

  &.active {
    background: #eaddff;
    color: #21005d;
    font-weight: 500;

    &::before {
      content: '';
      position: absolute;
      left: 0;
      top: 0;
      bottom: 0;
      width: 3px;
      background: #6750a4;
    }
  }
}

.nav-badge {
  margin-left: auto;
  background: #b3261e;
  color: white;
  font-size: 11px;
  padding: 2px 6px;
  border-radius: 6px;
}

.nav-divider {
  height: 1px;
  background: #e0e0e0;
  margin: 16px 24px;
}

.admin-main {
  grid-area: main;
  padding: 24px;
  overflow-y: auto;
}

.notification-panel {
  position: fixed;
  top: 64px;
  right: 24px;
  width: 360px;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 4px 20px rgba(0,0,0,0.15);
  z-index: 200;
}

.notification-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid #e0e0e0;

  h3 {
    font-size: 16px;
    font-weight: 500;
    color: #1c1b1f;
  }
}

.notification-list {
  max-height: 400px;
  overflow-y: auto;
}

.notification-item {
  display: flex;
  gap: 16px;
  padding: 16px 20px;
  border-bottom: 1px solid #f0f0f0;
  cursor: pointer;
  transition: background 0.2s;

  &:hover {
    background: #f5f5f5;
  }

  &.unread {
    background: #eaddff;
  }

  .material-icons {
    color: #6750a4;
    font-size: 20px;
  }
}

.notification-content {
  flex: 1;

  h4 {
    font-size: 14px;
    font-weight: 500;
    color: #1c1b1f;
    margin-bottom: 4px;
  }

  p {
    font-size: 13px;
    color: #49454f;
    margin-bottom: 4px;
  }

  time {
    font-size: 12px;
    color: #79747e;
  }
}
</style>
