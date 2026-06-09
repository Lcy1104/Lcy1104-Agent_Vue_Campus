<template>
  <div class="admin-page">
    <h2 class="page-title">待审核用户</h2>
    
    <div class="stats-bar">
      <div class="stat-card">
        <span class="stat-value">{{ pendingUsers.length }}</span>
        <span class="stat-label">待审核</span>
      </div>
      <div class="stat-card">
        <span class="stat-value">{{ approvedToday }}</span>
        <span class="stat-label">今日通过</span>
      </div>
      <div class="stat-card">
        <span class="stat-value">{{ rejectedToday }}</span>
        <span class="stat-label">今日拒绝</span>
      </div>
    </div>

    <div class="content-card">
      <div v-if="loading" class="loading-state">
        <div class="material-spinner"></div>
        <p>加载中...</p>
      </div>

      <div v-else-if="pendingUsers.length === 0" class="empty-state">
        <span class="material-icons">check_circle</span>
        <p>暂无待审核用户</p>
      </div>

      <div v-else class="user-list">
        <div 
          v-for="user in pendingUsers" 
          :key="user.id"
          class="user-card"
        >
          <div class="user-info">
            <div class="user-avatar">
              <span class="material-icons">person</span>
            </div>
            <div class="user-details">
              <h4>{{ user.username }}</h4>
              <p>申请时间: {{ formatTime(user.created_at) }}</p>
            </div>
          </div>
          
          <div class="user-actions">
            <button 
              class="material-button filled approve"
              @click="approveUser(user)"
              :disabled="processing === user.id"
            >
              <span v-if="processing === user.id" class="material-spinner small"></span>
              <span v-else>
                <span class="material-icons">check</span>
                通过
              </span>
            </button>
            <button 
              class="material-button outlined reject"
              @click="rejectUser(user)"
              :disabled="processing === user.id"
            >
              <span class="material-icons">close</span>
              拒绝
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- 确认对话框 -->
    <div v-if="showDialog" class="modal-overlay">
      <div class="modal-card">
        <h3>{{ dialogTitle }}</h3>
        <p>{{ dialogMessage }}</p>
        <div class="modal-actions">
          <button class="material-button text" @click="showDialog = false">
            取消
          </button>
          <button 
            class="material-button filled"
            :class="{ 'danger': dialogAction === 'reject' }"
            @click="confirmAction"
          >
            确认
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import axios from 'axios'
import { useAdminRefresh } from '@/composables/useAdminRefresh'

const pendingUsers = ref([])
const loading = ref(true)
const processing = ref(null)
const approvedToday = ref(0)
const rejectedToday = ref(0)

const showDialog = ref(false)
const dialogTitle = ref('')
const dialogMessage = ref('')
const dialogAction = ref('')
const selectedUser = ref(null)

const fetchPendingUsers = async () => {
  try {
    const token = localStorage.getItem('token')
    const response = await axios.get('/api/admin/users/pending', {
      headers: { Authorization: `Bearer ${token}` }
    })
    pendingUsers.value = response.data.users || []
  } catch (error) {
    console.error('Failed to fetch pending users:', error)
  } finally {
    loading.value = false
  }
}

const formatTime = (time) => {
  return new Date(time).toLocaleString('zh-CN')
}

const approveUser = (user) => {
  selectedUser.value = user
  dialogTitle.value = '确认通过'
  dialogMessage.value = `确定要通过用户 ${user.username} 的注册申请吗？`
  dialogAction.value = 'approve'
  showDialog.value = true
}

const rejectUser = (user) => {
  selectedUser.value = user
  dialogTitle.value = '确认拒绝'
  dialogMessage.value = `确定要拒绝用户 ${user.username} 的注册申请吗？`
  dialogAction.value = 'reject'
  showDialog.value = true
}

const confirmAction = async () => {
  if (!selectedUser.value) return
  
  processing.value = selectedUser.value.id
  showDialog.value = false
  
  try {
    const token = localStorage.getItem('token')
    await axios.post(
      `/api/admin/users/${selectedUser.value.id}/review`,
      { approved: dialogAction.value === 'approve' },
      { headers: { Authorization: `Bearer ${token}` } }
    )
    
    // 移除已处理的用户
    pendingUsers.value = pendingUsers.value.filter(
      u => u.id !== selectedUser.value.id
    )
    
    if (dialogAction.value === 'approve') {
      approvedToday.value++
    } else {
      rejectedToday.value++
    }
  } catch (error) {
    alert('操作失败: ' + (error.response?.data?.detail || '请重试'))
  } finally {
    processing.value = null
    selectedUser.value = null
  }
}

onMounted(() => {
  fetchPendingUsers()
})
useAdminRefresh((reason) => {
  if (reason === 'registration_pending') fetchPendingUsers()
})
</script>

<style scoped lang="scss">
.admin-page {
  max-width: 1200px;
}

.page-title {
  font-size: 24px;
  font-weight: 500;
  color: #1c1b1f;
  margin-bottom: 24px;
}

.stats-bar {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 16px;
  margin-bottom: 24px;
}

.stat-card {
  background: #fff;
  border-radius: 12px;
  padding: 20px 24px;
  display: flex;
  flex-direction: column;
  box-shadow: 0 2px 4px rgba(0,0,0,0.05);

  .stat-value {
    font-size: 32px;
    font-weight: 500;
    color: #6750a4;
  }

  .stat-label {
    font-size: 14px;
    color: #49454f;
    margin-top: 4px;
  }
}

.content-card {
  background: #fff;
  border-radius: 12px;
  padding: 24px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.05);
  min-height: 400px;
}

.loading-state,
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 300px;
  color: #79747e;

  .material-icons {
    font-size: 48px;
    margin-bottom: 16px;
  }

  .material-spinner {
    width: 32px;
    height: 32px;
    border: 3px solid rgba(103, 80, 164, 0.3);
    border-top-color: #6750a4;
    border-radius: 50%;
    animation: spin 1s linear infinite;
    margin-bottom: 16px;
  }
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.user-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.user-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px;
  background: #f9f9f9;
  border-radius: 8px;
  border: 1px solid #e0e0e0;
  transition: box-shadow 0.2s;

  &:hover {
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
  }
}

.user-info {
  display: flex;
  align-items: center;
  gap: 16px;
}

.user-avatar {
  width: 48px;
  height: 48px;
  background: #eaddff;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #6750a4;

  .material-icons {
    font-size: 24px;
  }
}

.user-details {
  h4 {
    font-size: 16px;
    font-weight: 500;
    color: #1c1b1f;
    margin-bottom: 4px;
  }

  p {
    font-size: 13px;
    color: #79747e;
  }
}

.user-actions {
  display: flex;
  gap: 12px;
}

.material-button {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 10px 20px;
  border-radius: 20px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  border: none;

  &.filled {
    background: #6750a4;
    color: white;

    &:hover {
      background: #5a4496;
    }

    &.approve {
      background: #2e7d32;

      &:hover {
        background: #1b5e20;
      }
    }

    &.danger {
      background: #b3261e;

      &:hover {
        background: #9c2220;
      }
    }
  }

  &.outlined {
    background: transparent;
    border: 1px solid #6750a4;
    color: #6750a4;

    &.reject {
      border-color: #b3261e;
      color: #b3261e;

      &:hover {
        background: rgba(179, 38, 30, 0.08);
      }
    }
  }

  &:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }

  .material-spinner.small {
    width: 16px;
    height: 16px;
    border: 2px solid rgba(255,255,255,0.3);
    border-top-color: white;
    border-radius: 50%;
    animation: spin 1s linear infinite;
  }
}

.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0,0,0,0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-card {
  background: white;
  border-radius: 12px;
  padding: 24px;
  max-width: 400px;
  width: 90%;

  h3 {
    font-size: 18px;
    font-weight: 500;
    color: #1c1b1f;
    margin-bottom: 12px;
  }

  p {
    color: #49454f;
    margin-bottom: 24px;
  }
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}
</style>
