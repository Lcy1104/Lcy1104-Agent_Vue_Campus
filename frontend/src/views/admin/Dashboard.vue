<template>
  <div class="dashboard-page">
    <section class="hero-card">
      <div>
        <p class="eyebrow">Admin Overview</p>
        <h2>校园智能 Agent 管理概览</h2>
        <p class="hero-text">集中查看用户审核、密码重置和系统入口状态，优先处理需要管理员介入的事项。</p>
      </div>
      <span class="material-icons hero-icon">admin_panel_settings</span>
    </section>

    <section class="metric-grid">
      <article class="metric-card primary">
        <span class="material-icons">people</span>
        <div>
          <strong>{{ stats.totalUsers }}</strong>
          <p>全部用户</p>
        </div>
      </article>
      <article class="metric-card warning" @click="router.push('/admin/pending-users')">
        <span class="material-icons">person_add</span>
        <div>
          <strong>{{ stats.pendingUsers }}</strong>
          <p>待审核注册</p>
        </div>
      </article>
      <article class="metric-card tertiary" @click="router.push('/admin/pending-resets')">
        <span class="material-icons">lock_reset</span>
        <div>
          <strong>{{ stats.pendingResets }}</strong>
          <p>待审核密码重置</p>
        </div>
      </article>
      <article class="metric-card secondary">
        <span class="material-icons">verified_user</span>
        <div>
          <strong>{{ stats.adminUsers }}</strong>
          <p>管理员账户</p>
        </div>
      </article>
      <article class="metric-card model-status" @click="router.push('/admin/models')">
        <span class="material-icons">monitor_heart</span>
        <div>
          <strong>{{ stats.modelBackends }}</strong>
          <p>已配置模型后端</p>
        </div>
      </article>
    </section>

    <section class="content-grid">
      <div class="content-card">
        <div class="card-header">
          <h3>待处理事项</h3>
          <button class="material-button text" @click="refresh">刷新</button>
        </div>

        <div v-if="loading" class="loading-state">
          <div class="material-spinner"></div>
          <p>加载中...</p>
        </div>
        <div v-else class="action-list">
          <button class="action-item" @click="router.push('/admin/pending-users')">
            <span class="material-icons">person_add</span>
            <div>
              <strong>注册审核</strong>
              <p>{{ stats.pendingUsers }} 个用户等待审核</p>
            </div>
            <span class="material-icons arrow">chevron_right</span>
          </button>
          <button class="action-item" @click="router.push('/admin/pending-resets')">
            <span class="material-icons">lock_reset</span>
            <div>
              <strong>密码重置审核</strong>
              <p>{{ stats.pendingResets }} 个重置申请等待处理</p>
            </div>
            <span class="material-icons arrow">chevron_right</span>
          </button>
          <button class="action-item" @click="router.push('/admin/users')">
            <span class="material-icons">manage_accounts</span>
            <div>
              <strong>用户管理</strong>
              <p>查看用户状态、角色和最近登录时间</p>
            </div>
            <span class="material-icons arrow">chevron_right</span>
          </button>
        </div>
      </div>

      <div class="content-card system-card">
        <div class="card-header">
          <h3>模型后端状态</h3>
          <button class="material-button text" :disabled="statusLoading" @click="loadBackendStatuses">
            {{ statusLoading ? '检测中...' : '检测连接' }}
          </button>
        </div>
        <div v-if="statusLoading" class="loading-state slim">
          <div class="material-spinner"></div>
          <p>检测模型后端中...</p>
        </div>
        <div v-else-if="backendStatuses.length === 0" class="module-list">
          <button class="action-item" @click="loadBackendStatuses">
            <span class="material-icons">monitor_heart</span>
            <div>
              <strong>未进行连接检测</strong>
              <p>已配置 {{ stats.modelBackends }} 个模型后端。连接检测较慢，点击上方按钮后执行。</p>
            </div>
            <span class="material-icons arrow">chevron_right</span>
          </button>
        </div>
        <div v-else class="backend-status-list">
          <button v-for="backend in backendStatuses" :key="backend.backend_id" class="backend-status-item" @click="router.push('/admin/models')">
            <span class="status-dot" :class="{ ok: backend.ok, warn: backend.quota_warning }"></span>
            <div>
              <strong>{{ backend.name }}</strong>
              <p>
                {{ backend.type }} ·
                {{ backend.ok ? `连接正常 ${backend.latency_ms ?? '-'}ms` : backend.message }}
              </p>
              <small v-if="backend.quota_warning">{{ backend.quota_message || '云端模型额度可能不足' }}</small>
            </div>
            <span v-if="backend.quota_warning" class="warning-chip">额度告警</span>
            <span v-else class="status-chip" :class="backend.ok ? 'ok' : 'down'">
              {{ backend.ok ? '在线' : '异常' }}
            </span>
          </button>
        </div>
      </div>

      <div class="content-card system-card">
        <h3>系统模块</h3>
        <div class="module-list">
          <div class="module-item ready">
            <span class="material-icons">group</span>
            <span>用户与审核</span>
          </div>
          <div class="module-item ready">
            <span class="material-icons">model_training</span>
            <span>模型管理已接入</span>
          </div>
          <div class="module-item ready clickable" @click="router.push('/admin/agent')">
            <span class="material-icons">psychology</span>
            <span>Agent 配置已接入</span>
          </div>
          <div class="module-item ready clickable" @click="router.push('/admin/system')">
            <span class="material-icons">settings</span>
            <span>系统设置已接入</span>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, reactive, ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import api from '@/api'
import modelsApi from '@/api/models'
import { useAdminRefresh } from '@/composables/useAdminRefresh'

const router = useRouter()
const loading = ref(true)
const statusLoading = ref(false)
const backendStatuses = ref([])
const stats = reactive({
  totalUsers: 0,
  adminUsers: 0,
  pendingUsers: 0,
  pendingResets: 0,
  modelBackends: 0
})

const onlineBackendCount = computed(() => backendStatuses.value.filter(backend => backend.ok).length)

const refresh = async () => {
  loading.value = true
  try {
    const [response, backendResponse] = await Promise.all([
      api.get('/admin/overview'),
      modelsApi.listBackends()
    ])
    stats.totalUsers = response.data.total_users || 0
    stats.adminUsers = response.data.admin_users || 0
    stats.pendingUsers = response.data.pending_users || 0
    stats.pendingResets = response.data.pending_resets || 0
    stats.modelBackends = backendResponse.data?.length ?? response.data.model_backends ?? 0
  } catch (error) {
    console.error('Failed to load dashboard:', error)
  } finally {
    loading.value = false
  }
}

const loadBackendStatuses = async () => {
  statusLoading.value = true
  try {
    const response = await modelsApi.listBackendStatuses()
    backendStatuses.value = response.data || []
  } catch (error) {
    console.error('Failed to load backend statuses:', error)
    backendStatuses.value = []
  } finally {
    statusLoading.value = false
  }
}

onMounted(() => {
  refresh()
})

useAdminRefresh((reason) => {
  if (['registration_pending', 'password_reset_pending', 'user_password_changed', 'user_created', 'user_updated'].includes(reason)) {
    refresh()
  }
})
</script>

<style scoped lang="scss">
.dashboard-page {
  max-width: 1240px;
}

.hero-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: $spacing-lg;
  padding: $spacing-xl;
  border-radius: 28px;
  background: linear-gradient(135deg, $primary-container, $secondary-container);
  color: $on-primary-container;
  box-shadow: $shadow-2;
  margin-bottom: $spacing-lg;
}

.eyebrow {
  font-size: 12px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: $primary-color;
  margin-bottom: $spacing-sm;
}

h2 {
  font-size: 30px;
  font-weight: 600;
  margin-bottom: $spacing-sm;
}

.hero-text {
  max-width: 620px;
  color: $on-surface-variant;
}

.hero-icon {
  display: grid;
  place-items: center;
  width: 88px;
  height: 88px;
  border-radius: 26px;
  background: rgba($primary-color, 0.14);
  font-size: 46px;
  color: $primary-color;
}

.metric-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
  gap: $spacing-md;
  margin-bottom: $spacing-lg;
}

.metric-card {
  display: flex;
  align-items: center;
  gap: $spacing-md;
  padding: 22px;
  border-radius: $radius-xlarge;
  background: $surface;
  box-shadow: $shadow-1;
  cursor: default;
  transition: transform 0.2s, box-shadow 0.2s;

  &.warning,
  &.tertiary {
    cursor: pointer;
  }

  &:hover {
    transform: translateY(-2px);
    box-shadow: $shadow-2;
  }

  .material-icons {
    display: grid;
    place-items: center;
    width: 48px;
    height: 48px;
    border-radius: 16px;
    background: $primary-container;
    color: $primary-color;
  }

  strong {
    display: block;
    font-size: 30px;
    color: $on-surface;
  }

  p {
    color: $on-surface-variant;
    font-size: 14px;
  }
}

.metric-card.warning .material-icons {
  background: $tertiary-container;
  color: $tertiary-color;
}

.metric-card.secondary .material-icons {
  background: $secondary-container;
  color: $secondary-color;
}

.metric-card.model-status {
  cursor: pointer;

  .material-icons {
    background: rgba($primary-color, 0.12);
    color: $primary-color;
  }
}

.content-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.4fr) minmax(280px, 0.8fr);
  gap: $spacing-lg;
}

.content-card {
  background: $surface;
  border-radius: $radius-xlarge;
  box-shadow: $shadow-1;
  padding: $spacing-lg;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: $spacing-md;
}

h3 {
  font-size: 18px;
  color: $on-surface;
}

.loading-state {
  display: grid;
  place-items: center;
  gap: $spacing-md;
  min-height: 220px;
  color: $on-surface-variant;

  &.slim {
    min-height: 150px;
  }
}

.action-list,
.module-list {
  display: flex;
  flex-direction: column;
  gap: $spacing-sm;
}

.action-item {
  display: flex;
  align-items: center;
  gap: $spacing-md;
  width: 100%;
  padding: $spacing-md;
  border: 1px solid $outline-variant;
  border-radius: $radius-large;
  background: transparent;
  text-align: left;
  cursor: pointer;
  color: $on-surface;
  transition: background 0.2s, border-color 0.2s;

  &:hover {
    background: rgba($primary-color, 0.08);
    border-color: $primary-color;
  }

  > .material-icons:first-child {
    color: $primary-color;
  }

  div {
    flex: 1;
  }

  p {
    color: $on-surface-variant;
    font-size: 13px;
  }
}

.arrow {
  color: $outline;
}

.module-item {
  display: flex;
  align-items: center;
  gap: $spacing-md;
  padding: 14px 0;
  color: $on-surface-variant;
  border-bottom: 1px solid $outline-variant;

  &:last-child {
    border-bottom: 0;
  }

  &.ready {
    color: $primary-color;
  }

  &.clickable {
    cursor: pointer;
  }

  &.clickable:hover {
    background: rgba($primary-color, 0.06);
  }
}

.backend-status-list {
  display: flex;
  flex-direction: column;
  gap: $spacing-sm;
}

.backend-status-item {
  display: grid;
  grid-template-columns: 14px minmax(0, 1fr) auto;
  align-items: center;
  gap: $spacing-md;
  width: 100%;
  padding: 14px 0;
  border: 0;
  border-bottom: 1px solid $outline-variant;
  background: transparent;
  text-align: left;
  cursor: pointer;

  &:last-child {
    border-bottom: 0;
  }

  &:hover strong {
    color: $primary-color;
  }

  strong {
    color: $on-surface;
  }

  p,
  small {
    display: block;
    color: $on-surface-variant;
    font-size: 13px;
  }

  small {
    color: $error;
    margin-top: 3px;
  }
}

.status-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: $error;

  &.ok {
    background: #2e7d32;
  }

  &.warn {
    background: $tertiary-color;
  }
}

.status-chip,
.warning-chip {
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 600;
}

.status-chip.ok {
  background: #dff7e8;
  color: #146c2e;
}

.status-chip.down,
.warning-chip {
  background: $error-container;
  color: $error;
}

@media (max-width: 860px) {
  .hero-card,
  .content-grid {
    grid-template-columns: 1fr;
  }

  .hero-card {
    align-items: flex-start;
  }
}
</style>
