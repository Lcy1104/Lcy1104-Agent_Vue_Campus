<template>
  <div class="users-page">
    <div class="page-header">
      <div>
        <p class="eyebrow">User Management</p>
        <h2>用户管理</h2>
        <p>查看系统用户、角色、注册状态和强制改密状态。</p>
      </div>
      <button class="material-button outlined" @click="fetchUsers">
        <span class="material-icons">refresh</span>
        刷新
      </button>
    </div>

    <section class="filter-card">
      <label>
        <span>状态</span>
        <select v-model="filters.status" @change="fetchUsers">
          <option value="">全部状态</option>
          <option value="active">正常</option>
          <option value="pending_review">待审核</option>
          <option value="disabled">已禁用</option>
        </select>
      </label>
      <label>
        <span>角色</span>
        <select v-model="filters.role" @change="fetchUsers">
          <option value="">全部角色</option>
          <option value="admin">管理员</option>
          <option value="user">普通用户</option>
        </select>
      </label>
      <label class="search-field">
        <span>搜索</span>
        <input v-model.trim="keyword" type="text" placeholder="按用户名过滤" />
      </label>
    </section>

    <section class="table-card">
      <div v-if="loading" class="loading-state">
        <div class="material-spinner"></div>
        <p>加载中...</p>
      </div>

      <div v-else-if="filteredUsers.length === 0" class="empty-state">
        <span class="material-icons">person_search</span>
        <p>没有匹配的用户</p>
      </div>

      <div v-else class="user-table">
        <div class="table-row table-head">
          <span>用户</span>
          <span>角色</span>
          <span>状态</span>
          <span>强制改密</span>
          <span>最近登录</span>
          <span>创建时间</span>
        </div>
        <div v-for="user in filteredUsers" :key="user.id" class="table-row">
          <div class="user-cell">
            <div class="avatar">{{ user.username.slice(0, 1).toUpperCase() }}</div>
            <div>
              <strong>{{ user.username }}</strong>
              <small>{{ user.id }}</small>
            </div>
          </div>
          <span class="chip" :class="user.role">{{ roleText(user.role) }}</span>
          <span class="chip" :class="user.registration_status">{{ statusText(user.registration_status) }}</span>
          <span class="force-chip" :class="{ on: user.force_password_change }">
            {{ user.force_password_change ? '是' : '否' }}
          </span>
          <span>{{ formatTime(user.last_login_at) }}</span>
          <span>{{ formatTime(user.created_at) }}</span>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, reactive, ref, onMounted } from 'vue'
import api from '@/api'
import { useAdminRefresh } from '@/composables/useAdminRefresh'

const users = ref([])
const loading = ref(true)
const keyword = ref('')
const filters = reactive({
  status: '',
  role: ''
})

const filteredUsers = computed(() => {
  if (!keyword.value) {
    return users.value
  }
  return users.value.filter(user => user.username.toLowerCase().includes(keyword.value.toLowerCase()))
})

const fetchUsers = async () => {
  loading.value = true
  try {
    const params = {}
    if (filters.status) params.status = filters.status
    if (filters.role) params.role = filters.role
    const response = await api.get('/admin/users', { params })
    users.value = response.data || []
  } catch (error) {
    console.error('Failed to fetch users:', error)
  } finally {
    loading.value = false
  }
}

const roleText = (role) => role === 'admin' ? '管理员' : '普通用户'

const statusText = (status) => {
  switch (status) {
    case 'active': return '正常'
    case 'pending_review': return '待审核'
    case 'disabled': return '已禁用'
    default: return status || '未知'
  }
}

const formatTime = (time) => time ? new Date(time).toLocaleString('zh-CN') : '-'

onMounted(fetchUsers)
useAdminRefresh((reason) => {
  if (['registration_pending', 'user_password_changed', 'user_created', 'user_updated'].includes(reason)) fetchUsers()
})
</script>

<style scoped lang="scss">
.users-page {
  max-width: 1240px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: $spacing-lg;
  margin-bottom: $spacing-lg;

  h2 {
    font-size: 28px;
    color: $on-surface;
    margin-bottom: $spacing-xs;
  }

  p {
    color: $on-surface-variant;
  }
}

.eyebrow {
  color: $primary-color;
  font-size: 12px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  margin-bottom: $spacing-xs;
}

.filter-card,
.table-card {
  background: $surface;
  border-radius: $radius-xlarge;
  box-shadow: $shadow-1;
}

.filter-card {
  display: grid;
  grid-template-columns: repeat(3, minmax(180px, 1fr));
  gap: $spacing-md;
  padding: $spacing-lg;
  margin-bottom: $spacing-lg;

  label {
    display: flex;
    flex-direction: column;
    gap: $spacing-xs;
    color: $on-surface-variant;
    font-size: 13px;
  }

  select,
  input {
    height: 44px;
    border: 1px solid $outline;
    border-radius: $radius-small;
    padding: 0 12px;
    background: transparent;
    color: $on-surface;
    font-size: 14px;

    &:focus {
      outline: none;
      border-color: $primary-color;
      box-shadow: 0 0 0 2px rgba($primary-color, 0.12);
    }
  }
}

.table-card {
  min-height: 420px;
  overflow: hidden;
}

.loading-state,
.empty-state {
  display: grid;
  place-items: center;
  gap: $spacing-md;
  min-height: 420px;
  color: $on-surface-variant;

  .material-icons {
    font-size: 48px;
    color: $outline;
  }
}

.user-table {
  overflow-x: auto;
}

.table-row {
  display: grid;
  grid-template-columns: minmax(260px, 1.5fr) 110px 120px 100px 170px 170px;
  align-items: center;
  gap: $spacing-md;
  min-width: 980px;
  padding: 16px 20px;
  border-bottom: 1px solid $outline-variant;
  color: $on-surface-variant;
  font-size: 14px;
}

.table-head {
  background: rgba($primary-color, 0.06);
  color: $on-primary-container;
  font-weight: 600;
}

.user-cell {
  display: flex;
  align-items: center;
  gap: $spacing-md;
  min-width: 0;

  strong,
  small {
    display: block;
  }

  strong {
    color: $on-surface;
  }

  small {
    max-width: 220px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    color: $outline;
  }
}

.avatar {
  display: grid;
  place-items: center;
  width: 40px;
  height: 40px;
  border-radius: $radius-full;
  background: $primary-container;
  color: $primary-color;
  font-weight: 700;
}

.chip,
.force-chip {
  justify-self: start;
  padding: 5px 12px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 600;
  background: $surface-variant;
  color: $on-surface-variant;
}

.chip.admin {
  background: $primary-container;
  color: $on-primary-container;
}

.chip.user,
.chip.active {
  background: #dff7e8;
  color: #146c2e;
}

.chip.pending_review,
.force-chip.on {
  background: $tertiary-container;
  color: $on-tertiary-container;
}

.chip.disabled {
  background: $error-container;
  color: $error;
}

@media (max-width: 760px) {
  .page-header,
  .filter-card {
    grid-template-columns: 1fr;
  }

  .page-header {
    flex-direction: column;
  }
}
</style>
