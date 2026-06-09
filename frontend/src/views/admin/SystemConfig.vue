<template>
  <div class="system-page">
    <div class="page-header">
      <div>
        <p class="eyebrow">System Runtime</p>
        <h2>系统设置</h2>
        <p>只开放适合管理员调整的全局运行参数。审计日志仅保存在数据库中，不在前端展示。</p>
      </div>
      <div class="header-actions">
        <button class="material-button outlined" @click="loadConfigs">刷新</button>
        <button class="material-button filled" :disabled="saving" @click="saveAll">{{ saving ? '保存中...' : '保存全部' }}</button>
      </div>
    </div>

    <div v-if="notice.message" class="notice" :class="notice.type">
      <span class="material-icons">{{ notice.type === 'error' ? 'error' : 'check_circle' }}</span>
      <span>{{ notice.message }}</span>
    </div>

    <section class="policy-card">
      <span class="material-icons">policy</span>
      <div>
        <strong>配置边界</strong>
        <p>这里不提供审计日志查看、不暴露数据库连接和密钥编辑、不允许上传自定义 Agent 图。敏感信息仍应通过服务器环境变量和数据库直查管理。</p>
      </div>
    </section>

    <div v-if="loading" class="loading-state">
      <div class="material-spinner"></div>
      <p>加载系统设置中...</p>
    </div>

    <section v-else class="config-groups">
      <article v-for="group in groupedConfigs" :key="group.category" class="config-card">
        <h3>{{ group.category }}</h3>
        <div class="config-list">
          <label v-for="config in group.items" :key="config.key" class="config-item">
            <span>{{ config.description }}</span>
            <select v-if="config.value_type === 'select'" v-model="formValues[config.key]">
              <option v-for="option in config.options" :key="option" :value="option">{{ optionLabel(config.key, option) }}</option>
            </select>
            <select v-else-if="config.value_type === 'boolean'" v-model="formValues[config.key]">
              <option value="true">启用</option>
              <option value="false">停用</option>
            </select>
            <input v-else v-model.trim="formValues[config.key]" type="number" />
            <small>{{ config.key }}</small>
          </label>
        </div>
      </article>
    </section>
  </div>
</template>

<script setup>
import { computed, reactive, ref, onMounted } from 'vue'
import systemApi from '@/api/system'

const loading = ref(true)
const saving = ref(false)
const configs = ref([])
const formValues = reactive({})
const notice = reactive({ type: 'success', message: '' })

const groupedConfigs = computed(() => {
  const groups = []
  const byCategory = new Map()
  for (const config of configs.value) {
    if (!byCategory.has(config.category)) {
      byCategory.set(config.category, { category: config.category, items: [] })
      groups.push(byCategory.get(config.category))
    }
    byCategory.get(config.category).items.push(config)
  }
  return groups
})

const showNotice = (message, type = 'success') => {
  notice.type = type
  notice.message = message
  window.clearTimeout(showNotice.timer)
  showNotice.timer = window.setTimeout(() => {
    notice.message = ''
  }, 3200)
}

const loadConfigs = async () => {
  loading.value = true
  try {
    const response = await systemApi.listConfigs()
    configs.value = response.data || []
    configs.value.forEach(config => {
      formValues[config.key] = config.value
    })
  } catch (error) {
    showNotice(error.response?.data?.detail || '加载系统设置失败', 'error')
  } finally {
    loading.value = false
  }
}

const saveAll = async () => {
  saving.value = true
  try {
    const values = {}
    configs.value.forEach(config => {
      values[config.key] = formValues[config.key]
    })
    const response = await systemApi.updateConfigs(values)
    configs.value = response.data || []
    showNotice('系统设置已保存')
  } catch (error) {
    showNotice(error.response?.data?.detail || '保存系统设置失败', 'error')
  } finally {
    saving.value = false
  }
}

const optionLabel = (key, option) => {
  const labels = {
    default_think_mode: { off: '关闭', collapsed: '默认折叠', full: '完整显示' },
    default_agent_strategy: { react: 'ReAct 模式', plan_execute: 'Plan-Execute 模式', multi_agent: '多 Agent 协作模式' }
  }
  return labels[key]?.[option] || option
}

onMounted(loadConfigs)
</script>

<style scoped lang="scss">
.system-page { width: 100%; max-width: 1180px; }
.page-header, .header-actions, .notice, .policy-card { display: flex; align-items: center; }
.page-header { justify-content: space-between; gap: $spacing-lg; margin-bottom: $spacing-lg; }
.page-header h2 { font-size: 28px; color: $on-surface; margin-bottom: $spacing-xs; }
.page-header p { color: $on-surface-variant; }
.header-actions { gap: $spacing-sm; }
.eyebrow { color: $primary-color; font-size: 12px; letter-spacing: 0.14em; text-transform: uppercase; margin-bottom: $spacing-xs; }
.notice { gap: $spacing-sm; padding: 12px 16px; border-radius: $radius-large; background: #dff7e8; color: #146c2e; margin-bottom: $spacing-md; }
.notice.error { background: $error-container; color: $error; }
.policy-card { gap: $spacing-md; padding: $spacing-md; border: 1px solid $outline-variant; border-radius: $radius-large; background: rgba($primary-color, 0.05); margin-bottom: $spacing-lg; }
.policy-card .material-icons { color: $primary-color; }
.policy-card strong { color: $on-surface; }
.policy-card p { color: $on-surface-variant; }
.loading-state { min-height: 320px; display: grid; place-items: center; gap: $spacing-md; color: $on-surface-variant; }
.config-groups { display: grid; grid-template-columns: repeat(2, minmax(320px, 1fr)); gap: $spacing-lg; }
.config-card { background: $surface; border-radius: $radius-large; box-shadow: $shadow-1; padding: $spacing-lg; }
.config-card h3 { color: $on-surface; margin-bottom: $spacing-md; }
.config-list { display: grid; gap: $spacing-md; }
.config-item { display: grid; grid-template-columns: minmax(0, 1fr) 180px; gap: $spacing-md; align-items: center; color: $on-surface-variant; }
.config-item span { color: $on-surface; }
.config-item small { grid-column: 1 / -1; color: $outline; margin-top: -10px; }
input, select { height: 42px; border: 1px solid $outline; border-radius: $radius-small; padding: 0 12px; background: transparent; color: $on-surface; }
@media (max-width: 980px) { .config-groups { grid-template-columns: 1fr; } .page-header { flex-direction: column; align-items: stretch; } }
@media (max-width: 640px) { .config-item { grid-template-columns: 1fr; } .config-item small { margin-top: 0; } }
</style>
