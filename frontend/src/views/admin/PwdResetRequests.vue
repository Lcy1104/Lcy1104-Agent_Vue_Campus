<template>
  <div class="admin-page">
    <h2 class="page-title">待审核密码重置</h2>
    
    <div class="stats-bar">
      <div class="stat-card">
        <span class="stat-value">{{ pendingResets.length }}</span>
        <span class="stat-label">待审核</span>
      </div>
      <div class="stat-card">
        <span class="stat-value">{{ approvedToday }}</span>
        <span class="stat-label">今日通过</span>
      </div>
    </div>

    <div class="content-card">
      <div v-if="loading" class="loading-state">
        <div class="material-spinner"></div>
        <p>加载中...</p>
      </div>

      <div v-else-if="pendingResets.length === 0" class="empty-state">
        <span class="material-icons">check_circle</span>
        <p>暂无待审核密码重置请求</p>
      </div>

      <div v-else class="reset-list">
        <div 
          v-for="request in pendingResets" 
          :key="request.id"
          class="reset-card"
        >
          <div class="reset-info">
            <div class="info-row">
              <span class="label">用户名:</span>
              <span class="value">{{ request.username }}</span>
            </div>
            <div class="info-row">
              <span class="label">申请时间:</span>
              <span class="value">{{ formatTime(request.requested_at) }}</span>
            </div>
            <div class="info-row">
              <span class="label">IP地址:</span>
              <span class="value">{{ request.ip_address || '未知' }}</span>
            </div>
          </div>
          
          <div class="reset-actions">
            <button 
              class="material-button filled approve"
              @click="approveReset(request)"
              :disabled="processing === request.id"
            >
              <span v-if="processing === request.id" class="material-spinner small"></span>
              <span v-else>
                <span class="material-icons">check</span>
                同意
              </span>
            </button>
            <button 
              class="material-button outlined reject"
              @click="rejectReset(request)"
              :disabled="processing === request.id"
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
        <p v-if="dialogAction === 'approve'" class="warning-text">
          同意后不会生成临时密码，用户再次点击忘记密码并通过验证码后可自行设置新密码。
        </p>
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

const pendingResets = ref([])
const loading = ref(true)
const processing = ref(null)
const approvedToday = ref(0)

const showDialog = ref(false)
const dialogTitle = ref('')
const dialogMessage = ref('')
const dialogAction = ref('')
const selectedRequest = ref(null)

const fetchPendingResets = async () => {
  try {
    const token = localStorage.getItem('token')
    const response = await axios.get('/api/admin/password-resets/pending', {
      headers: { Authorization: `Bearer ${token}` }
    })
    pendingResets.value = response.data.requests || []
  } catch (error) {
    console.error('Failed to fetch pending resets:', error)
  } finally {
    loading.value = false
  }
}

const formatTime = (time) => {
  return new Date(time).toLocaleString('zh-CN')
}

const approveReset = (request) => {
  selectedRequest.value = request
  dialogTitle.value = '确认通过密码重置'
  dialogMessage.value = `确定要通过 ${request.username} 的密码重置申请吗？`
  dialogAction.value = 'approve'
  showDialog.value = true
}

const rejectReset = (request) => {
  selectedRequest.value = request
  dialogTitle.value = '确认拒绝密码重置'
  dialogMessage.value = `确定要拒绝 ${request.username} 的密码重置申请吗？`
  dialogAction.value = 'reject'
  showDialog.value = true
}

const confirmAction = async () => {
  if (!selectedRequest.value) return
  
  processing.value = selectedRequest.value.id
  showDialog.value = false
  
  try {
    const token = localStorage.getItem('token')
    await axios.post(
      `/api/admin/password-resets/${selectedRequest.value.id}/review`,
      { approved: dialogAction.value === 'approve' },
      { headers: { Authorization: `Bearer ${token}` } }
    )
    
    if (dialogAction.value === 'approve') {
      approvedToday.value++
    }
    
    // 移除已处理的请求
    pendingResets.value = pendingResets.value.filter(
      r => r.id !== selectedRequest.value.id
    )
  } catch (error) {
    alert('操作失败: ' + (error.response?.data?.detail || '请重试'))
  } finally {
    processing.value = null
  }
}

onMounted(() => {
  fetchPendingResets()
})
useAdminRefresh((reason) => {
  if (reason === 'password_reset_pending') fetchPendingResets()
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
}

.reset-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.reset-card {
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

.reset-info {
  flex: 1;
}

.info-row {
  display: flex;
  gap: 12px;
  margin-bottom: 8px;

  &:last-child {
    margin-bottom: 0;
  }

  .label {
    color: #79747e;
    font-size: 14px;
    min-width: 70px;
  }

  .value {
    color: #1c1b1f;
    font-size: 14px;
    font-weight: 500;
  }
}

.reset-actions {
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

@keyframes spin {
  to { transform: rotate(360deg); }
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
    margin-bottom: 16px;
  }

  .warning-text {
    color: #b3261e;
    font-size: 13px;
    background: #f9dedc;
    padding: 12px;
    border-radius: 8px;
    margin-bottom: 16px;
  }
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

.password-display {
  display: flex;
  align-items: center;
  gap: 12px;
  background: #f5f5f5;
  padding: 16px;
  border-radius: 8px;
  margin: 16px 0;

  code {
    flex: 1;
    font-size: 18px;
    font-family: 'Courier New', monospace;
    color: #6750a4;
    word-break: break-all;
  }

  .copy-btn {
    background: none;
    border: none;
    cursor: pointer;
    padding: 8px;
    border-radius: 50%;
    color: #6750a4;

    &:hover {
      background: rgba(103, 80, 164, 0.08);
    }

    .material-icons {
      font-size: 20px;
    }
  }
}
</style>
