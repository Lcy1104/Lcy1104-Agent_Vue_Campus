<template>
  <div class="agent-page">
    <div class="page-header">
      <div>
        <p class="eyebrow">LangGraph Orchestration</p>
        <h2>Agent 设置</h2>
        <p>配置系统内置 Agent 策略、执行边界和子图模型绑定。仅支持内置策略，不允许上传自定义图。</p>
      </div>
      <button class="material-button outlined" @click="loadAll">
        <span class="material-icons">refresh</span>
        刷新
      </button>
    </div>

    <div v-if="notice.message" class="notice" :class="notice.type">
      <span class="material-icons">{{ notice.type === 'error' ? 'error' : 'check_circle' }}</span>
      <span>{{ notice.message }}</span>
    </div>

    <div v-if="loading" class="loading-state">
      <div class="material-spinner"></div>
      <p>加载 Agent 配置中...</p>
    </div>

    <section v-else class="strategy-grid">
      <article v-for="config in configs" :key="config.strategy_name" class="strategy-card">
        <header class="strategy-header">
          <div>
            <p class="eyebrow">{{ config.strategy_name }}</p>
            <h3>{{ config.display_name }}</h3>
            <p>{{ config.description }}</p>
          </div>
          <label class="toggle-row">
            <input v-model="forms[config.strategy_name].is_enabled" type="checkbox" />
            <span>{{ forms[config.strategy_name].is_enabled ? '启用' : '停用' }}</span>
          </label>
        </header>

        <div class="graph-box">
          <div class="graph-nodes">
            <span v-for="node in config.graph_nodes" :key="node">{{ node }}</span>
          </div>
          <div class="graph-edges">
            <small v-for="edge in config.graph_edges" :key="edge">{{ edge }}</small>
          </div>
        </div>

        <div class="param-grid">
          <label>
            <span>最大循环次数</span>
            <input v-model.number="forms[config.strategy_name].max_iterations" type="number" min="1" max="50" />
          </label>
          <label>
            <span>任务超时（秒）</span>
            <input v-model.number="forms[config.strategy_name].timeout_seconds" type="number" min="10" max="3600" />
          </label>
        </div>

        <div class="model-bindings">
          <h4>子图模型绑定</h4>
          <p>不选择则使用全局默认文本模型。</p>
          <label v-for="node in configurableNodes(config)" :key="node">
            <span>{{ node }}</span>
            <select v-model="forms[config.strategy_name].sub_agent_models[node]">
              <option value="">使用全局默认</option>
              <option v-for="model in textModels" :key="model.id" :value="model.id">
                {{ model.display_name || model.model_name }} · {{ model.backend_name || model.backend_type }}
              </option>
            </select>
          </label>
        </div>

        <footer class="card-actions">
          <button class="material-button outlined" @click="resetForm(config)">还原</button>
          <button class="material-button filled" :disabled="saving === config.strategy_name" @click="saveConfig(config)">
            {{ saving === config.strategy_name ? '保存中...' : '保存配置' }}
          </button>
        </footer>
      </article>
    </section>
  </div>
</template>

<script setup>
import { computed, reactive, ref, onMounted } from 'vue'
import agentApi from '@/api/agent'
import modelsApi from '@/api/models'

const loading = ref(true)
const saving = ref('')
const configs = ref([])
const models = ref([])
const forms = reactive({})
const notice = reactive({ type: 'success', message: '' })

const textModels = computed(() => models.value.filter(model => model.capabilities?.text !== false))

const showNotice = (message, type = 'success') => {
  notice.type = type
  notice.message = message
  window.clearTimeout(showNotice.timer)
  showNotice.timer = window.setTimeout(() => {
    notice.message = ''
  }, 3200)
}

const loadAll = async () => {
  loading.value = true
  try {
    const [configsResponse, modelsResponse] = await Promise.all([
      agentApi.listConfigs(),
      modelsApi.listModels()
    ])
    configs.value = configsResponse.data || []
    models.value = modelsResponse.data || []
    configs.value.forEach(resetForm)
  } catch (error) {
    showNotice(error.response?.data?.detail || '加载 Agent 配置失败', 'error')
  } finally {
    loading.value = false
  }
}

const resetForm = (config) => {
  forms[config.strategy_name] = {
    is_enabled: config.is_enabled,
    max_iterations: config.max_iterations,
    timeout_seconds: config.timeout_seconds,
    sub_agent_models: { ...(config.sub_agent_models || {}) }
  }
}

const configurableNodes = (config) => {
  const nodes = new Set(Object.keys(forms[config.strategy_name]?.sub_agent_models || {}))
  if (config.strategy_name === 'react') nodes.add('agent')
  if (config.strategy_name === 'plan_execute') ['planner', 'executor', 'validator'].forEach(node => nodes.add(node))
  if (config.strategy_name === 'multi_agent') ['analyst', 'executor', 'validator'].forEach(node => nodes.add(node))
  return Array.from(nodes)
}

const saveConfig = async (config) => {
  saving.value = config.strategy_name
  try {
    const form = forms[config.strategy_name]
    const payload = {
      is_enabled: form.is_enabled,
      max_iterations: form.max_iterations,
      timeout_seconds: form.timeout_seconds,
      sub_agent_models: form.sub_agent_models
    }
    const response = await agentApi.updateConfig(config.strategy_name, payload)
    const index = configs.value.findIndex(item => item.strategy_name === config.strategy_name)
    if (index >= 0) configs.value[index] = response.data
    resetForm(response.data)
    showNotice('Agent 配置已保存')
  } catch (error) {
    showNotice(error.response?.data?.detail || '保存 Agent 配置失败', 'error')
  } finally {
    saving.value = ''
  }
}

onMounted(loadAll)
</script>

<style scoped lang="scss">
.agent-page { width: 100%; }
.page-header { display: flex; justify-content: space-between; align-items: center; gap: $spacing-lg; margin-bottom: $spacing-lg; }
.page-header h2 { font-size: 28px; color: $on-surface; margin-bottom: $spacing-xs; }
.page-header p { color: $on-surface-variant; }
.eyebrow { color: $primary-color; font-size: 12px; letter-spacing: 0.14em; text-transform: uppercase; margin-bottom: $spacing-xs; }
.notice { display: flex; align-items: center; gap: $spacing-sm; padding: 12px 16px; border-radius: $radius-large; background: #dff7e8; color: #146c2e; margin-bottom: $spacing-md; }
.notice.error { background: $error-container; color: $error; }
.loading-state { min-height: 360px; display: grid; place-items: center; gap: $spacing-md; color: $on-surface-variant; }
.strategy-grid { display: grid; grid-template-columns: repeat(3, minmax(320px, 1fr)); gap: $spacing-lg; }
.strategy-card { background: $surface; border-radius: $radius-large; box-shadow: $shadow-1; padding: $spacing-lg; display: flex; flex-direction: column; gap: $spacing-md; }
.strategy-header { display: flex; justify-content: space-between; gap: $spacing-md; align-items: flex-start; }
.strategy-header h3 { color: $on-surface; font-size: 20px; }
.strategy-header p { color: $on-surface-variant; }
.toggle-row { display: flex; align-items: center; gap: $spacing-xs; color: $on-surface-variant; white-space: nowrap; }
.graph-box { border: 1px solid $outline-variant; border-radius: $radius-medium; padding: $spacing-md; background: rgba($primary-color, 0.04); }
.graph-nodes { display: flex; flex-wrap: wrap; gap: $spacing-xs; margin-bottom: $spacing-sm; }
.graph-nodes span { padding: 6px 10px; border-radius: $radius-small; background: $primary-container; color: $on-primary-container; font-weight: 600; }
.graph-edges { display: grid; gap: 4px; color: $on-surface-variant; }
.param-grid { display: grid; grid-template-columns: 1fr 1fr; gap: $spacing-md; }
label { display: flex; flex-direction: column; gap: $spacing-xs; color: $on-surface-variant; font-size: 13px; }
input, select { height: 42px; border: 1px solid $outline; border-radius: $radius-small; padding: 0 12px; background: transparent; color: $on-surface; }
.model-bindings { display: grid; gap: $spacing-sm; }
.model-bindings h4 { color: $on-surface; }
.model-bindings p { color: $on-surface-variant; font-size: 13px; }
.card-actions { display: flex; justify-content: flex-end; gap: $spacing-sm; margin-top: auto; }
@media (max-width: 1280px) { .strategy-grid { grid-template-columns: 1fr; } }
@media (max-width: 720px) { .page-header, .strategy-header { flex-direction: column; align-items: stretch; } .param-grid { grid-template-columns: 1fr; } }
</style>
