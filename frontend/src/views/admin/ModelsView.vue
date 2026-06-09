<template>
  <div class="models-page">
    <div class="page-header">
      <div>
        <p class="eyebrow">Model Management</p>
        <h2>模型管理</h2>
        <p>接入本地 Ollama、vLLM 或在线 API，按需注册模型并配置全局默认用途。</p>
      </div>
      <div class="header-actions">
        <button class="material-button outlined" @click="refreshAll">
          <span class="material-icons">refresh</span>
          刷新
        </button>
        <button class="material-button filled" @click="createOllamaBackend">
          <span class="material-icons">add_link</span>
          添加本地 Ollama
        </button>
      </div>
    </div>

    <div v-if="notice.message" class="notice" :class="notice.type">
      <span class="material-icons">{{ notice.type === 'error' ? 'error' : 'check_circle' }}</span>
      <span>{{ notice.message }}</span>
    </div>

    <section class="content-grid">
      <div class="panel-card">
        <div class="card-header">
          <div>
            <h3>模型后端</h3>
            <p>管理本地或云端模型服务连接。</p>
          </div>
          <button class="material-button text" @click="showBackendForm = !showBackendForm">
            {{ showBackendForm ? '收起' : '手动添加' }}
          </button>
        </div>

        <form v-if="showBackendForm" class="backend-form" @submit.prevent="saveBackend">
          <label>
            <span>名称</span>
            <input v-model.trim="backendForm.name" required placeholder="例如：本地 Ollama" />
          </label>
          <label>
            <span>类型</span>
            <select v-model="backendForm.type">
              <option value="ollama">Ollama</option>
              <option value="vllm">vLLM</option>
              <option value="openai">OpenAI</option>
              <option value="anthropic">Anthropic</option>
              <option value="custom">Custom</option>
            </select>
          </label>
          <div class="backend-help wide">
            <span class="material-icons">info</span>
            <p>{{ backendTypeHelp }}</p>
          </div>
          <label class="wide">
            <span>API 地址</span>
            <input v-model.trim="backendForm.base_url" required :placeholder="backendBaseUrlPlaceholder" />
          </label>
          <label v-if="backendNeedsApiKey" class="wide">
            <span>API Key</span>
            <input v-model.trim="backendForm.api_key" type="password" :placeholder="backendForm.id ? '留空表示不修改当前密钥' : '请输入服务商 API Key'" />
          </label>
          <label class="switch-row wide">
            <input v-model="backendForm.is_enabled" type="checkbox" />
            <span>启用该后端</span>
          </label>
          <div class="form-actions wide">
            <button class="material-button outlined" type="button" @click="resetBackendForm">取消</button>
            <button class="material-button filled" type="submit" :disabled="savingBackend">
              {{ savingBackend ? '保存中...' : backendForm.id ? '保存修改' : '创建后端' }}
            </button>
          </div>
        </form>

        <div v-if="loading" class="loading-state">
          <div class="material-spinner"></div>
          <p>加载中...</p>
        </div>

        <div v-else-if="backends.length === 0" class="empty-state">
          <span class="material-icons">cloud_off</span>
          <p>还没有模型后端，建议先添加本地 Ollama。</p>
        </div>

        <div v-else class="backend-list">
          <article v-for="backend in backends" :key="backend.id" class="backend-item">
            <div class="backend-main">
              <div class="backend-icon">
                <span class="material-icons">dns</span>
              </div>
              <div>
                <div class="backend-title">
                  <strong>{{ backend.name }}</strong>
                  <span class="chip">{{ backend.type }}</span>
                  <span class="chip" :class="backend.is_enabled ? 'active' : 'disabled'">
                    {{ backend.is_enabled ? '启用' : '停用' }}
                  </span>
                </div>
                <p>{{ backend.base_url }}</p>
                <small>{{ backend.has_api_key ? '已配置 API Key' : '未配置 API Key' }}</small>
              </div>
            </div>
            <div class="backend-actions">
              <button class="material-button text" @click="testBackend(backend)">测试</button>
              <button v-if="backend.type === 'ollama'" class="material-button text" @click="scanBackend(backend)">扫描</button>
              <button class="material-button text" @click="editBackend(backend)">编辑</button>
              <button class="material-button text danger" @click="deleteBackend(backend)">删除</button>
            </div>
          </article>
        </div>
      </div>

      <div class="panel-card">
        <div class="card-header">
          <div>
            <h3>模型清单</h3>
            <p>扫描或手动注册后，可配置可见性和默认用途。</p>
          </div>
          <button class="material-button text" @click="showModelForm = !showModelForm">
            {{ showModelForm ? '收起' : '手动注册' }}
          </button>
        </div>

        <form v-if="showModelForm" class="model-form" @submit.prevent="saveModel">
          <label>
            <span>后端</span>
            <select v-model="modelForm.backend_id" required>
              <option value="" disabled>请选择后端</option>
              <option v-for="backend in backends" :key="backend.id" :value="backend.id">
                {{ backend.name }}
              </option>
            </select>
          </label>
          <label>
            <span>模型 ID</span>
            <input v-model.trim="modelForm.model_name" required placeholder="qwen2.5:7b" />
          </label>
          <label>
            <span>显示名称</span>
            <input v-model.trim="modelForm.display_name" placeholder="默认同模型 ID" />
          </label>
          <label>
            <span>温度</span>
            <input v-model.number="modelForm.temperature" type="number" min="0" max="2" step="0.1" />
          </label>
          <div class="check-grid wide">
            <label><input v-model="modelForm.capabilities.text" type="checkbox" /> 文本</label>
            <label><input v-model="modelForm.capabilities.vision" type="checkbox" /> 视觉</label>
            <label><input v-model="modelForm.capabilities.tool_calling" type="checkbox" /> 工具调用</label>
            <label><input v-model="modelForm.is_visible" type="checkbox" /> 普通用户可见</label>
            <label><input v-model="modelForm.is_default_text" type="checkbox" /> 默认文本模型</label>
            <label><input v-model="modelForm.is_default_embed" type="checkbox" /> 默认嵌入模型</label>
            <label><input v-model="modelForm.is_default_vision" type="checkbox" /> 默认视觉模型</label>
          </div>
          <div class="form-actions wide">
            <button class="material-button outlined" type="button" @click="resetModelForm">取消</button>
            <button class="material-button filled" type="submit" :disabled="savingModel">
              {{ savingModel ? '保存中...' : modelForm.id ? '保存修改' : '注册模型' }}
            </button>
          </div>
        </form>

        <div v-if="models.length === 0 && !loading" class="empty-state">
          <span class="material-icons">model_training</span>
          <p>暂无模型。可扫描 Ollama 后选择导入，或手动注册在线模型 ID。</p>
        </div>

        <div v-else class="model-table">
          <div class="table-row table-head">
            <span>模型</span>
            <span>后端</span>
            <span>能力</span>
            <span>默认</span>
            <span>可见</span>
            <span>操作</span>
          </div>
          <div v-for="model in models" :key="model.id" class="table-row">
            <div>
              <strong>{{ model.display_name || model.model_name }}</strong>
              <small>{{ model.model_name }}</small>
            </div>
            <span>{{ model.backend_name || '-' }}</span>
            <div class="cap-list">
              <span v-if="model.capabilities?.text">文本</span>
              <span v-if="model.capabilities?.vision || model.is_multimodal">视觉</span>
              <span v-if="model.capabilities?.tool_calling">工具</span>
            </div>
            <div class="cap-list">
              <span v-if="model.is_default_text">文本</span>
              <span v-if="model.is_default_embed">嵌入</span>
              <span v-if="model.is_default_vision">视觉</span>
              <span v-if="!model.is_default_text && !model.is_default_embed && !model.is_default_vision">-</span>
            </div>
            <span class="chip" :class="model.is_visible ? 'active' : 'disabled'">
              {{ model.is_visible ? '可见' : '隐藏' }}
            </span>
            <div class="row-actions">
              <button class="material-button text" @click="editModel(model)">编辑</button>
              <button class="material-button text danger" @click="deleteModel(model)">删除</button>
            </div>
          </div>
        </div>
      </div>
    </section>

    <section class="embedding-card panel-card">
      <div class="card-header">
        <div>
          <p class="eyebrow">Embedding Model</p>
          <h3>嵌入模型管理（分词模型）</h3>
          <p>用于知识库文档分块后的向量化检索。切换嵌入模型后，已有知识库文档需要重新索引以保证向量维度一致。</p>
        </div>
        <span class="material-icons">hub</span>
      </div>
      <div class="embedding-grid">
        <article>
          <strong>当前默认嵌入模型</strong>
          <p v-if="defaultEmbedModel">{{ defaultEmbedModel.display_name || defaultEmbedModel.model_name }} · {{ defaultEmbedModel.backend_name || defaultEmbedModel.backend_type }}</p>
          <p v-else>尚未指定默认嵌入模型。可登记多个本地、Ollama 或在线 Embedding 模型后选择其一作为全局默认。</p>
        </article>
        <article>
          <strong>使用规则</strong>
          <p>本地模型、Ollama 嵌入模型和在线 Embedding API 都可以登记多个。全局默认嵌入模型用于知识库向量化，切换后已有文档需要重新索引。</p>
        </article>
      </div>
      <form class="embedding-form" @submit.prevent="registerEmbeddingModel">
        <label>
          <span>来源类型</span>
          <select v-model="embeddingForm.source">
            <option value="local">本地模型路径</option>
            <option value="ollama">Ollama 嵌入模型</option>
            <option value="online">在线 Embedding API</option>
          </select>
        </label>
        <label>
          <span>绑定后端</span>
          <select v-model="embeddingForm.backend_id" required>
            <option value="" disabled>请选择后端</option>
            <option v-for="backend in backends" :key="backend.id" :value="backend.id">
              {{ backend.name }} · {{ backend.type }}
            </option>
          </select>
        </label>
        <label>
          <span>模型名称 / 路径</span>
          <input v-model.trim="embeddingForm.model_name" required :placeholder="embeddingPlaceholder" />
        </label>
        <label>
          <span>显示名称</span>
          <input v-model.trim="embeddingForm.display_name" placeholder="例如：本地 text2vec 中文嵌入" />
        </label>
        <label>
          <span>向量维度（可选）</span>
          <input v-model.number="embeddingForm.dimension" type="number" min="1" placeholder="如 768、1024、1536" />
        </label>
        <label class="switch-row">
          <input v-model="embeddingForm.is_default_embed" type="checkbox" />
          <span>登记后设为默认嵌入模型</span>
        </label>
        <div class="form-actions wide">
          <button class="material-button outlined" type="button" @click="fillLocalEmbedding('text2vec-base-chinese')">填入 text2vec</button>
          <button class="material-button text" type="button" @click="fillLocalEmbedding('bert-base-chinese')">填入 bert</button>
          <button class="material-button filled" type="submit" :disabled="savingEmbedding || !backends.length">
            {{ savingEmbedding ? '登记中...' : '登记嵌入模型' }}
          </button>
        </div>
        <small v-if="!backends.length" class="wide">请先添加至少一个后端；本地路径模型可绑定到 custom 或本地后端作为管理载体。</small>
      </form>
      <div class="embedding-list">
        <div class="table-row table-head compact">
          <span>嵌入候选模型</span>
          <span>后端</span>
          <span>状态</span>
          <span>操作</span>
        </div>
        <div v-for="model in embeddingModels" :key="model.id" class="table-row compact">
          <div>
            <strong>{{ model.display_name || model.model_name }}</strong>
            <small>{{ model.model_name }}<template v-if="model.virtual"> · 系统配置中正在使用</template></small>
          </div>
          <span>{{ model.backend_name || model.backend_type || '-' }}</span>
          <span class="chip" :class="model.is_default_embed ? 'active' : 'disabled'">
            {{ model.is_default_embed ? '默认嵌入' : model.virtual ? '内置可用' : '候选' }}
          </span>
          <div class="row-actions">
            <button v-if="model.virtual" class="material-button text" @click="registerConfiguredEmbedding(model)">登记到模型清单</button>
            <button v-else class="material-button text" :disabled="model.is_default_embed" @click="setDefaultEmbed(model)">设为默认嵌入</button>
            <button v-if="!model.virtual" class="material-button text" @click="editModel(model)">编辑</button>
          </div>
        </div>
        <div v-if="embeddingModels.length === 0" class="empty-state compact">
          <span class="material-icons">hub</span>
          <p>暂无嵌入模型。可登记本地模型路径、Ollama 嵌入模型或在线 Embedding API，并选择一个作为全局默认。</p>
        </div>
      </div>
    </section>

    <div v-if="scanDialog.open" class="dialog-mask" @click.self="closeScanDialog">
      <section class="scan-dialog">
        <div class="card-header">
          <div>
            <h3>选择要导入的 Ollama 模型</h3>
            <p>只导入当前系统需要使用的模型，已存在的模型不会重复导入。</p>
          </div>
          <button class="material-button text" @click="closeScanDialog">关闭</button>
        </div>

        <div v-if="scanDialog.loading" class="loading-state compact">
          <div class="material-spinner"></div>
          <p>正在读取 Ollama 模型...</p>
        </div>

        <div v-else-if="scanDialog.models.length === 0" class="empty-state compact">
          <span class="material-icons">search_off</span>
          <p>该 Ollama 后端没有返回可用模型。</p>
        </div>

        <div v-else class="scan-list">
          <label v-for="item in scanDialog.models" :key="item.name" class="scan-item" :class="{ disabled: item.exists }">
            <input v-model="scanDialog.selected" type="checkbox" :value="item.name" :disabled="item.exists" />
            <div>
              <strong>{{ item.name }}</strong>
              <small>{{ item.exists ? '已在模型清单中' : formatModelSize(item.size) }}</small>
            </div>
          </label>
        </div>

        <div class="dialog-actions">
          <button class="material-button outlined" @click="selectAllScanned">选择全部未导入</button>
          <button class="material-button filled" :disabled="scanDialog.selected.length === 0 || scanDialog.importing" @click="importScannedModels">
            {{ scanDialog.importing ? '导入中...' : `导入 ${scanDialog.selected.length} 个模型` }}
          </button>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup>
import { computed, reactive, ref, onMounted, watch } from 'vue'
import modelsApi from '@/api/models'

const loading = ref(true)
const savingBackend = ref(false)
const savingModel = ref(false)
const savingEmbedding = ref(false)
const showBackendForm = ref(false)
const showModelForm = ref(false)
const backends = ref([])
const models = ref([])
const notice = reactive({ type: 'success', message: '' })
const scanDialog = reactive({
  open: false,
  loading: false,
  importing: false,
  backend: null,
  models: [],
  selected: []
})

const backendForm = reactive({
  id: '',
  name: '',
  type: 'ollama',
  base_url: 'http://localhost:11434',
  api_key: '',
  is_enabled: true
})

const modelForm = reactive({
  id: '',
  backend_id: '',
  model_name: '',
  display_name: '',
  temperature: 0.7,
  capabilities: {
    text: true,
    vision: false,
    tool_calling: true
  },
  is_visible: true,
  is_default_text: false,
  is_default_embed: false,
  is_default_vision: false
})

const embeddingForm = reactive({
  source: 'local',
  backend_id: '',
  model_name: '',
  display_name: '',
  dimension: null,
  is_default_embed: true
})

const backendTypeHelp = computed(() => {
  switch (backendForm.type) {
    case 'ollama': return '本地 Ollama 通常只需要 API 地址，默认是 http://localhost:11434，可扫描本机已安装模型后选择导入。'
    case 'vllm': return 'vLLM 通常兼容 OpenAI 接口，填写服务地址，例如 http://localhost:8001/v1，模型 ID 需要手动注册。'
    case 'openai': return 'OpenAI 或兼容服务需要填写 base URL 和 API Key，模型 ID 通过下方“手动注册”添加。'
    case 'anthropic': return 'Anthropic 需要填写 API 地址和 API Key，模型 ID 通过下方“手动注册”添加。'
    default: return '自定义后端请填写可访问的 API 地址；如果需要鉴权，请填写 API Key。'
  }
})

const backendBaseUrlPlaceholder = computed(() => {
  switch (backendForm.type) {
    case 'ollama': return 'http://localhost:11434'
    case 'vllm': return 'http://localhost:8001/v1'
    case 'openai': return 'https://api.openai.com/v1'
    case 'anthropic': return 'https://api.anthropic.com'
    default: return 'https://example.com/v1'
  }
})

const backendNeedsApiKey = computed(() => ['openai', 'anthropic', 'custom'].includes(backendForm.type))
const registeredEmbeddingModels = computed(() => models.value.filter(model => model.is_default_embed || model.capabilities?.embedding || /embed|embedding|bge|text2vec|nomic/i.test(model.model_name)))
const configuredLocalEmbedding = {
  id: 'configured-text2vec-base-chinese',
  virtual: true,
  model_name: 'text2vec-base-chinese',
  display_name: '系统内置本地 text2vec 中文嵌入模型',
  backend_name: '本地路径配置',
  backend_type: 'local',
  is_default_embed: true,
  default_params: { local_path: 'F:\\MaxKB-2.1.2\\MaxKB-2.1.2\\models\\text2vec-base-chinese' },
  capabilities: { embedding: true, source: 'local' }
}
const embeddingModels = computed(() => registeredEmbeddingModels.value.length ? registeredEmbeddingModels.value : [configuredLocalEmbedding])
const defaultEmbedModel = computed(() => models.value.find(model => model.is_default_embed) || configuredLocalEmbedding)
const embeddingPlaceholder = computed(() => {
  if (embeddingForm.source === 'local') return 'F:\\...\\models\\text2vec-base-chinese 或 text2vec-base-chinese'
  if (embeddingForm.source === 'ollama') return 'nomic-embed-text 或 bge-m3'
  return 'text-embedding-3-small 或服务商模型 ID'
})

const showNotice = (message, type = 'success') => {
  notice.type = type
  notice.message = message
  window.clearTimeout(showNotice.timer)
  showNotice.timer = window.setTimeout(() => {
    notice.message = ''
  }, 3600)
}

const refreshAll = async () => {
  loading.value = true
  try {
    const [backendResponse, modelResponse] = await Promise.all([
      modelsApi.listBackends(),
      modelsApi.listModels()
    ])
    backends.value = backendResponse.data || []
    models.value = modelResponse.data || []
  } catch (error) {
    showNotice(error.response?.data?.detail || '加载模型管理数据失败', 'error')
  } finally {
    loading.value = false
  }
}

const createOllamaBackend = async () => {
  const exists = backends.value.some(backend => backend.type === 'ollama' && backend.base_url === 'http://localhost:11434')
  if (exists) {
    showNotice('本地 Ollama 后端已存在')
    return
  }
  savingBackend.value = true
  try {
    await modelsApi.createBackend({
      name: '本地 Ollama',
      type: 'ollama',
      base_url: 'http://localhost:11434',
      api_key: '',
      is_enabled: true
    })
    showNotice('已添加本地 Ollama 后端')
    await refreshAll()
  } catch (error) {
    showNotice(error.response?.data?.detail || '添加 Ollama 后端失败', 'error')
  } finally {
    savingBackend.value = false
  }
}

const saveBackend = async () => {
  savingBackend.value = true
  try {
    const payload = {
      name: backendForm.name,
      type: backendForm.type,
      base_url: backendForm.base_url,
      is_enabled: backendForm.is_enabled
    }
    if (!backendForm.id || backendForm.api_key) {
      payload.api_key = backendForm.api_key
    }
    if (backendForm.id) {
      await modelsApi.updateBackend(backendForm.id, payload)
      showNotice('模型后端已更新')
    } else {
      await modelsApi.createBackend(payload)
      showNotice('模型后端已创建')
    }
    resetBackendForm()
    await refreshAll()
  } catch (error) {
    showNotice(error.response?.data?.detail || '保存模型后端失败', 'error')
  } finally {
    savingBackend.value = false
  }
}

const editBackend = (backend) => {
  Object.assign(backendForm, {
    id: backend.id,
    name: backend.name,
    type: backend.type,
    base_url: backend.base_url,
    api_key: '',
    is_enabled: backend.is_enabled
  })
  showBackendForm.value = true
}

const resetBackendForm = () => {
  Object.assign(backendForm, {
    id: '',
    name: '',
    type: 'ollama',
    base_url: 'http://localhost:11434',
    api_key: '',
    is_enabled: true
  })
  showBackendForm.value = false
}

const deleteBackend = async (backend) => {
  if (!window.confirm(`确认删除模型后端“${backend.name}”？关联模型也会被删除。`)) return
  try {
    await modelsApi.deleteBackend(backend.id)
    showNotice('模型后端已删除')
    await refreshAll()
  } catch (error) {
    showNotice(error.response?.data?.detail || '删除模型后端失败', 'error')
  }
}

const testBackend = async (backend) => {
  try {
    const response = await modelsApi.testBackend(backend.id)
    const data = response.data
    showNotice(data.ok ? `连接正常，延迟 ${data.latency_ms}ms` : data.message, data.ok ? 'success' : 'error')
  } catch (error) {
    showNotice(error.response?.data?.detail || '测试连接失败', 'error')
  }
}

const scanBackend = async (backend) => {
  scanDialog.open = true
  scanDialog.loading = true
  scanDialog.backend = backend
  scanDialog.models = []
  scanDialog.selected = []
  try {
    const response = await modelsApi.scanBackend(backend.id)
    scanDialog.models = response.data.models || []
    scanDialog.selected = scanDialog.models.filter(item => !item.exists).map(item => item.name)
    showNotice(`扫描完成：发现 ${response.data.found} 个模型`)
  } catch (error) {
    scanDialog.open = false
    showNotice(error.response?.data?.detail || '扫描 Ollama 失败，请确认 Ollama 服务已启动', 'error')
  } finally {
    scanDialog.loading = false
  }
}

const closeScanDialog = () => {
  scanDialog.open = false
  scanDialog.loading = false
  scanDialog.importing = false
  scanDialog.backend = null
  scanDialog.models = []
  scanDialog.selected = []
}

const selectAllScanned = () => {
  scanDialog.selected = scanDialog.models.filter(item => !item.exists).map(item => item.name)
}

const importScannedModels = async () => {
  if (!scanDialog.backend || scanDialog.selected.length === 0) return
  scanDialog.importing = true
  try {
    const response = await modelsApi.importBackendModels(scanDialog.backend.id, scanDialog.selected)
    showNotice(`导入完成：新增 ${response.data.imported} 个模型`)
    closeScanDialog()
    await refreshAll()
  } catch (error) {
    showNotice(error.response?.data?.detail || '导入 Ollama 模型失败', 'error')
  } finally {
    scanDialog.importing = false
  }
}

const formatModelSize = (size) => {
  if (!size) return '未返回大小信息'
  const gb = size / 1024 / 1024 / 1024
  return `${gb.toFixed(1)} GB`
}

const saveModel = async () => {
  savingModel.value = true
  try {
    const payload = {
      backend_id: modelForm.backend_id,
      model_name: modelForm.model_name,
      display_name: modelForm.display_name || modelForm.model_name,
      capabilities: modelForm.capabilities,
      default_params: { temperature: modelForm.temperature },
      is_multimodal: modelForm.capabilities.vision,
      is_visible: modelForm.is_visible,
      is_default_text: modelForm.is_default_text,
      is_default_embed: modelForm.is_default_embed,
      is_default_vision: modelForm.is_default_vision
    }
    if (modelForm.id) {
      await modelsApi.updateModel(modelForm.id, payload)
      showNotice('模型配置已更新')
    } else {
      await modelsApi.createModel(payload)
      showNotice('模型已注册')
    }
    resetModelForm()
    await refreshAll()
  } catch (error) {
    showNotice(error.response?.data?.detail || '保存模型失败', 'error')
  } finally {
    savingModel.value = false
  }
}

const editModel = (model) => {
  Object.assign(modelForm, {
    id: model.id,
    backend_id: model.backend_id,
    model_name: model.model_name,
    display_name: model.display_name || '',
    temperature: model.default_params?.temperature ?? 0.7,
    capabilities: {
      text: Boolean(model.capabilities?.text),
      vision: Boolean(model.capabilities?.vision || model.is_multimodal),
      tool_calling: Boolean(model.capabilities?.tool_calling)
    },
    is_visible: model.is_visible,
    is_default_text: model.is_default_text,
    is_default_embed: model.is_default_embed,
    is_default_vision: model.is_default_vision
  })
  showModelForm.value = true
}

const resetModelForm = () => {
  Object.assign(modelForm, {
    id: '',
    backend_id: backends.value[0]?.id || '',
    model_name: '',
    display_name: '',
    temperature: 0.7,
    capabilities: { text: true, vision: false, tool_calling: true },
    is_visible: true,
    is_default_text: false,
    is_default_embed: false,
    is_default_vision: false
  })
  showModelForm.value = false
}

const deleteModel = async (model) => {
  if (!window.confirm(`确认删除模型“${model.display_name || model.model_name}”？`)) return
  try {
    await modelsApi.deleteModel(model.id)
    showNotice('模型已删除')
    await refreshAll()
  } catch (error) {
    showNotice(error.response?.data?.detail || '删除模型失败', 'error')
  }
}

const setDefaultEmbed = async (model) => {
  try {
    await modelsApi.updateModel(model.id, {
      backend_id: model.backend_id,
      model_name: model.model_name,
      display_name: model.display_name || model.model_name,
      capabilities: { ...(model.capabilities || {}), embedding: true },
      default_params: model.default_params,
      is_multimodal: model.is_multimodal,
      is_visible: model.is_visible,
      is_default_text: model.is_default_text,
      is_default_embed: true,
      is_default_vision: model.is_default_vision
    })
    showNotice('默认嵌入模型已更新。请到知识库管理执行“按当前嵌入模型重新索引”。')
    await refreshAll()
  } catch (error) {
    showNotice(error.response?.data?.detail || '设置默认嵌入模型失败', 'error')
  }
}

const fillLocalEmbedding = (modelName) => {
  embeddingForm.source = 'local'
  embeddingForm.model_name = modelName
  embeddingForm.display_name = modelName === 'text2vec-base-chinese' ? '本地 text2vec 中文嵌入模型' : '本地 BERT 中文分词模型'
  embeddingForm.dimension = modelName === 'text2vec-base-chinese' ? 768 : null
  if (!embeddingForm.backend_id) embeddingForm.backend_id = backends.value.find(item => ['custom', 'ollama'].includes(item.type))?.id || backends.value[0]?.id || ''
}

const registerEmbeddingModel = async () => {
  const backend = backends.value.find(item => item.id === embeddingForm.backend_id)
  if (!backend) return
  const exists = models.value.find(model => model.model_name === embeddingForm.model_name && model.backend_id === backend.id)
  savingEmbedding.value = true
  try {
    if (exists) {
      if (embeddingForm.is_default_embed) await setDefaultEmbed(exists)
      else showNotice('该嵌入模型已存在')
      return
    }
    await modelsApi.createModel({
      backend_id: backend.id,
      model_name: embeddingForm.model_name,
      display_name: embeddingForm.display_name || embeddingForm.model_name,
      capabilities: { embedding: true, text: false, tool_calling: false, source: embeddingForm.source },
      default_params: {
        source: embeddingForm.source,
        dimension: embeddingForm.dimension || undefined,
        local_path: embeddingForm.source === 'local' ? embeddingForm.model_name : undefined
      },
      is_multimodal: false,
      is_visible: false,
      is_default_text: false,
      is_default_embed: embeddingForm.is_default_embed,
      is_default_vision: false
    })
    showNotice('嵌入模型已登记到模型清单')
    await refreshAll()
  } catch (error) {
    showNotice(error.response?.data?.detail || '登记嵌入模型失败', 'error')
  } finally {
    savingEmbedding.value = false
  }
}

const registerConfiguredEmbedding = async () => {
  if (!backends.value.length) {
    showNotice('请先添加一个后端作为本地嵌入模型登记载体', 'error')
    return
  }
  embeddingForm.source = 'local'
  embeddingForm.backend_id = backends.value.find(item => ['custom', 'ollama'].includes(item.type))?.id || backends.value[0].id
  embeddingForm.model_name = configuredLocalEmbedding.model_name
  embeddingForm.display_name = configuredLocalEmbedding.display_name
  embeddingForm.dimension = 768
  embeddingForm.is_default_embed = true
  await registerEmbeddingModel()
}

onMounted(async () => {
  await refreshAll()
  resetModelForm()
})

watch(() => backendForm.type, (type) => {
  if (!backendForm.id) {
    backendForm.base_url = backendBaseUrlPlaceholder.value
    if (type === 'ollama') backendForm.api_key = ''
  }
})
</script>

<style scoped lang="scss">
.models-page {
  max-width: 1380px;
}

.page-header,
.card-header,
.backend-main,
.backend-title,
.backend-actions,
.header-actions,
.form-actions,
.row-actions,
.notice {
  display: flex;
  align-items: center;
}

.backend-help {
  display: flex;
  gap: $spacing-sm;
  padding: 12px 14px;
  border-radius: $radius-large;
  background: rgba($primary-color, 0.08);
  color: $on-surface-variant;
  font-size: 13px;

  .material-icons {
    color: $primary-color;
    font-size: 20px;
    flex: 0 0 auto;
  }
}

.page-header {
  justify-content: space-between;
  gap: $spacing-lg;
  margin-bottom: $spacing-md;

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

.header-actions,
.backend-actions,
.form-actions,
.row-actions {
  gap: $spacing-sm;
}

.notice {
  gap: $spacing-sm;
  padding: 12px 16px;
  border-radius: $radius-large;
  background: #dff7e8;
  color: #146c2e;
  margin-bottom: $spacing-md;

  &.error {
    background: $error-container;
    color: $error;
  }
}

.content-grid {
  display: grid;
  grid-template-columns: minmax(340px, 0.9fr) minmax(0, 1.4fr);
  gap: $spacing-lg;
  margin-bottom: $spacing-lg;
}

.panel-card {
  background: $surface;
  border-radius: $radius-xlarge;
  box-shadow: $shadow-1;
  padding: $spacing-lg;
  min-width: 0;
}

.card-header {
  justify-content: space-between;
  gap: $spacing-md;
  margin-bottom: $spacing-md;

  h3 {
    font-size: 18px;
    color: $on-surface;
  }

  p {
    color: $on-surface-variant;
    font-size: 13px;
  }
}

.backend-form,
.model-form,
.embedding-form {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: $spacing-md;
  padding: $spacing-md;
  border: 1px solid $outline-variant;
  border-radius: $radius-large;
  margin-bottom: $spacing-md;

  label {
    display: flex;
    flex-direction: column;
    gap: $spacing-xs;
    color: $on-surface-variant;
    font-size: 13px;
  }

  input,
  select {
    height: 42px;
    border: 1px solid $outline;
    border-radius: $radius-small;
    padding: 0 12px;
    background: transparent;
    color: $on-surface;
  }

  input:focus,
  select:focus {
    outline: none;
    border-color: $primary-color;
    box-shadow: 0 0 0 2px rgba($primary-color, 0.12);
  }
}

.wide,
.switch-row,
.check-grid,
.form-actions {
  grid-column: 1 / -1;
}

.switch-row {
  flex-direction: row !important;
  align-items: center;

  input {
    width: 18px;
    height: 18px;
  }
}

.check-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: $spacing-sm;

  label {
    flex-direction: row;
    align-items: center;
  }

  input {
    width: 18px;
    height: 18px;
  }
}

.form-actions {
  justify-content: flex-end;
}

.loading-state,
.empty-state {
  display: grid;
  place-items: center;
  gap: $spacing-md;
  min-height: 220px;
  color: $on-surface-variant;

  .material-icons {
    font-size: 46px;
    color: $outline;
  }
}

.compact {
  min-height: 150px;
}

.backend-list {
  display: flex;
  flex-direction: column;
  gap: $spacing-md;
}

.backend-item {
  display: flex;
  justify-content: space-between;
  gap: $spacing-md;
  padding: $spacing-md;
  border: 1px solid $outline-variant;
  border-radius: $radius-large;
}

.backend-main {
  gap: $spacing-md;
  min-width: 0;

  p,
  small {
    color: $on-surface-variant;
  }
}

.backend-icon {
  display: grid;
  place-items: center;
  width: 44px;
  height: 44px;
  border-radius: 14px;
  background: $primary-container;
  color: $primary-color;
}

.backend-title {
  flex-wrap: wrap;
  gap: $spacing-sm;
  margin-bottom: $spacing-xs;
}

.chip {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: max-content;
  padding: 4px 10px;
  border-radius: 999px;
  background: $surface-variant;
  color: $on-surface-variant;
  font-size: 12px;
  font-weight: 600;

  &.active {
    background: #dff7e8;
    color: #146c2e;
  }

  &.disabled {
    background: $error-container;
    color: $error;
  }
}

.danger {
  color: $error !important;
}

.model-table {
  overflow-x: auto;
}

.embedding-card { margin-bottom: $spacing-lg; }
.embedding-card .card-header .material-icons { color: $primary-color; font-size: 32px; }
.embedding-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: $spacing-md; margin-bottom: $spacing-md; }
.embedding-grid article { padding: 14px 16px; border: 1px solid $outline-variant; border-radius: $radius-large; background: rgba($primary-color, 0.04); }
.embedding-grid strong { display: block; color: $on-surface; margin-bottom: 6px; }
.embedding-grid p { color: $on-surface-variant; font-size: 13px; }
.embedding-actions { display: flex; align-items: center; flex-wrap: wrap; gap: $spacing-sm; margin-bottom: $spacing-md; }
.embedding-actions small { color: $on-surface-variant; }
.embedding-form { margin-bottom: $spacing-md; }
.embedding-list { overflow-x: auto; }

.table-row {
  display: grid;
  grid-template-columns: minmax(220px, 1.4fr) 130px 150px 150px 90px 150px;
  align-items: center;
  gap: $spacing-md;
  min-width: 900px;
  padding: 14px 12px;
  border-bottom: 1px solid $outline-variant;
  color: $on-surface-variant;
  font-size: 14px;

  strong,
  small {
    display: block;
  }

  strong {
    color: $on-surface;
  }

  small {
    color: $outline;
  }
}

.table-row.compact {
  grid-template-columns: minmax(260px, 1.6fr) 160px 130px 230px;
  min-width: 780px;
}

.table-head {
  background: rgba($primary-color, 0.06);
  color: $on-primary-container;
  font-weight: 600;
}

.cap-list {
  display: flex;
  flex-wrap: wrap;
  gap: $spacing-xs;

  span {
    padding: 3px 8px;
    border-radius: 999px;
    background: $secondary-container;
    color: $on-secondary-container;
    font-size: 12px;
  }
}

.dialog-mask {
  position: fixed;
  inset: 0;
  display: grid;
  place-items: center;
  padding: $spacing-lg;
  background: rgba(28, 27, 31, 0.32);
  z-index: 300;
}

.scan-dialog {
  width: min(720px, 100%);
  max-height: min(760px, 90vh);
  overflow: auto;
  background: $surface;
  border-radius: 28px;
  box-shadow: $shadow-4;
  padding: $spacing-lg;
}

.scan-list {
  display: grid;
  gap: $spacing-sm;
  margin: $spacing-md 0;
}

.scan-item {
  display: flex;
  align-items: center;
  gap: $spacing-md;
  padding: 14px 16px;
  border: 1px solid $outline-variant;
  border-radius: $radius-large;
  cursor: pointer;

  &:hover {
    background: rgba($primary-color, 0.06);
  }

  &.disabled {
    cursor: not-allowed;
    opacity: 0.62;
  }

  input {
    width: 18px;
    height: 18px;
  }

  strong,
  small {
    display: block;
  }

  strong {
    color: $on-surface;
  }

  small {
    color: $on-surface-variant;
  }
}

.dialog-actions {
  display: flex;
  justify-content: flex-end;
  gap: $spacing-sm;
  padding-top: $spacing-md;
  border-top: 1px solid $outline-variant;
}

@media (max-width: 1080px) {
  .content-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 720px) {
  .page-header,
  .backend-item,
  .header-actions {
    flex-direction: column;
    align-items: stretch;
  }

  .backend-form,
  .model-form {
    grid-template-columns: 1fr;
  }

  .dialog-actions {
    flex-direction: column;
  }
}
</style>
