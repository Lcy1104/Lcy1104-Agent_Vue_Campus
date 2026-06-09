<template>
  <div class="chat-page">
    <SessionList
      :sessions="sessions"
      :active-id="activeSession?.id || ''"
      @create="createSession"
      @select="selectSession"
      @rename="renameSession"
      @delete="deleteSession"
      @search="loadSessions"
    />
    <main class="chat-main">
      <header class="chat-toolbar">
        <div>
          <p class="eyebrow">Agent Campus</p>
          <h2>{{ activeSession?.title || '新对话' }}</h2>
          <small v-if="workingModel" class="working-model">{{ workingModel }}</small>
        </div>
        <div class="toolbar-actions">
          <select v-model="runTarget" class="run-target-select">
            <optgroup label="Agent 模式（后台可绑定多模型）">
              <option v-for="strategy in agentStrategies" :key="`strategy:${strategy.strategy_name}`" :value="`strategy:${strategy.strategy_name}`">
                {{ strategy.display_name || strategy.strategy_name }}
              </option>
            </optgroup>
            <optgroup label="单模型">
              <option v-for="model in visibleModels" :key="`model:${model.id}`" :value="`model:${model.id}`">
                {{ model.display_name || model.model_name }} · {{ modelCapabilityLabel(model) }}
              </option>
            </optgroup>
          </select>
          <small class="run-target-help">{{ runTargetDescription }}</small>
          <div class="tool-dropdown">
            <button class="material-button outlined" @click="showToolPanel = !showToolPanel">工具 {{ selectedToolIds.length ? `(${selectedToolIds.length})` : '' }}</button>
            <div v-if="showToolPanel" class="tool-panel">
              <div class="tool-panel-head">
                <strong>本轮工具</strong>
                <button class="material-button text" @click="router.push('/tools')">管理</button>
              </div>
              <button class="tool-check" @click="toggleAllTools">
                <span class="material-icons">{{ allToolsSelected ? 'check_box' : 'check_box_outline_blank' }}</span>
                全部工具
              </button>
              <button v-for="tool in availableTools" :key="tool.id" class="tool-check" @click="toggleTool(tool.id)">
                <span class="material-icons">{{ selectedToolIds.includes(tool.id) ? 'check_box' : 'check_box_outline_blank' }}</span>
                <span>{{ tool.name }}</span>
                <small>{{ tool.tool_type === 'mcp' ? 'MCP' : 'API' }} · {{ tool.is_public ? '公有' : '私有' }}</small>
              </button>
              <p v-if="!availableTools.length" class="tool-empty">暂无可用工具</p>
            </div>
          </div>
          <div class="tool-dropdown">
            <button class="material-button outlined" @click="showKnowledgePanel = !showKnowledgePanel">知识库 {{ selectedCollectionIds.length ? `(${selectedCollectionIds.length})` : '未开启' }}</button>
            <div v-if="showKnowledgePanel" class="tool-panel">
              <div class="tool-panel-head">
                <strong>本轮知识库</strong>
                <button class="material-button text" @click="clearCollections">全部</button>
              </div>
              <button v-for="collection in knowledgeCollections" :key="collection.id" class="tool-check" @click="toggleCollection(collection.id)">
                <span class="material-icons">{{ selectedCollectionIds.includes(collection.id) ? 'check_box' : 'check_box_outline_blank' }}</span>
                <span>{{ collection.name }}</span>
                <small>{{ collection.description || '知识库' }}</small>
              </button>
              <p v-if="!knowledgeCollections.length" class="tool-empty">暂无知识库</p>
            </div>
          </div>
          <select v-model="thinkMode">
            <option value="off">隐藏思考</option>
            <option value="collapsed">折叠思考</option>
            <option value="full">完整思考</option>
          </select>
          <button class="material-button outlined" @click="router.push('/dashboard')">返回主页</button>
        </div>
      </header>

      <section ref="messageList" class="message-list">
        <div v-if="!activeSession" class="empty-state">
          <span class="material-icons">forum</span>
          <p>创建或选择一个会话开始对话</p>
        </div>
        <ChatMessage v-for="message in messages" :key="message.localId || message.id" :message="message" :think-mode="thinkMode" />
      </section>

      <footer class="composer">
        <div v-if="attachments.length" class="attachment-strip">
          <div v-for="item in attachments" :key="item.id" class="attachment-item">
            <img :src="item.preview" :alt="item.name" />
            <button @click="removeAttachment(item.id)"><span class="material-icons">close</span></button>
          </div>
        </div>
        <textarea
          v-model="draft"
          placeholder="输入消息，Enter 发送，Shift+Enter 换行；可粘贴图片"
          @keydown.enter.exact.prevent="sendMessage"
          @paste="handlePaste"
        ></textarea>
        <div class="composer-actions">
          <label class="material-button outlined upload-button">
            <input type="file" accept="image/*" multiple @change="handleFileChange" />
            <span class="material-icons">image</span>
            图片
          </label>
          <AudioRecorder @transcribed="appendTranscribedText" @error="showAudioError" />
          <button v-if="sending" class="material-button outlined danger" @click="cancelMessage">中止</button>
          <button class="material-button filled" :disabled="sending || (!draft.trim() && attachments.length === 0)" @click="sendMessage">
            {{ sending ? '发送中...' : '发送' }}
          </button>
        </div>
      </footer>
    </main>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import sessionsApi from '@/api/sessions'
import agentApi from '@/api/agent'
import toolsApi from '@/api/tools'
import modelsApi from '@/api/models'
import knowledgeApi from '@/api/knowledge'
import SessionList from '@/components/session/SessionList.vue'
import ChatMessage from '@/components/chat/ChatMessage.vue'
import AudioRecorder from '@/components/audio/AudioRecorder.vue'

const router = useRouter()
const sessions = ref([])
const activeSession = ref(null)
const messages = ref([])
const attachments = ref([])
const draft = ref('')
const sending = ref(false)
const thinkMode = ref(localStorage.getItem('think_mode') || 'collapsed')
const workingModel = ref('')
const agentStrategies = ref([])
const selectedStrategy = ref(localStorage.getItem('agent_strategy') || 'react')
const visibleModels = ref([])
const selectedModelId = ref(localStorage.getItem('selected_model_id') || null)
const runTarget = ref(localStorage.getItem('run_target') || `strategy:${selectedStrategy.value}`)
const messageList = ref(null)
const availableTools = ref([])
const selectedToolIds = ref(JSON.parse(localStorage.getItem('selected_tool_ids') || '[]'))
const knowledgeCollections = ref([])
const selectedCollectionIds = ref(JSON.parse(localStorage.getItem('selected_collection_ids') || '[]'))
const showToolPanel = ref(false)
const showKnowledgePanel = ref(false)
const runningSessionId = ref(null)
const sendStartedAt = ref(null)
let ws = null
let wsSessionId = null

watch(thinkMode, value => localStorage.setItem('think_mode', value))
watch(runTarget, value => applyRunTarget(value))

const loadSessions = async (keyword = '') => {
  const response = await sessionsApi.listSessions(keyword ? { keyword } : {})
  sessions.value = response.data || []
  if (!activeSession.value && sessions.value.length) {
    await selectSession(sessions.value[0])
  }
}

const createSession = async () => {
  if (sending.value) {
    messages.value.push({ localId: crypto.randomUUID(), role: 'assistant', content: '当前对话仍在执行。你可以继续浏览或新建对话；结果完成后会保存在原会话中。', metadata: {}, tool_calls: [] })
  }
  const response = await sessionsApi.createSession({ title: '新对话', strategy: selectedStrategy.value === 'single_model' ? 'react' : selectedStrategy.value })
  sessions.value.unshift(response.data)
  await selectSession(response.data)
}

const selectSession = async (session) => {
  if (sending.value && activeSession.value?.id !== session.id) {
    messages.value.push({ localId: crypto.randomUUID(), role: 'assistant', content: '已切换会话。原会话仍在后台执行，完成后会保存到原会话。', metadata: {}, tool_calls: [] })
  }
  if (ws && wsSessionId !== session.id) {
    ws.close()
    ws = null
    wsSessionId = null
  }
  activeSession.value = session
  selectedModelId.value = session.model_id || null
  const response = await sessionsApi.listMessages(session.id)
  messages.value = (response.data.messages || []).map(normalizeMessage)
  const restoredStrategy = session.strategy || inferStrategyFromMessages(messages.value) || selectedStrategy.value || 'react'
  if (selectedModelId.value) {
    runTarget.value = `model:${selectedModelId.value}`
  } else {
    selectedStrategy.value = restoredStrategy
    runTarget.value = `strategy:${restoredStrategy}`
    if (!session.strategy) await updateSessionRunConfig(null, restoredStrategy)
  }
  connectWebSocket()
  await scrollToBottom()
}

const updateSessionRunConfig = async (modelId, strategy) => {
  selectedModelId.value = modelId || null
  localStorage.setItem('selected_model_id', selectedModelId.value || '')
  if (!activeSession.value) return
  const response = await sessionsApi.updateSession(activeSession.value.id, { model_id: selectedModelId.value, strategy })
  activeSession.value = response.data
  const session = sessions.value.find(item => item.id === response.data.id)
  if (session) {
    session.model_id = response.data.model_id
    session.strategy = response.data.strategy
  }
}

const inferStrategyFromMessages = (items) => {
  for (const message of [...items].reverse()) {
    const strategy = message.metadata?.strategy
    if (strategy && strategy !== 'single_model') return strategy
  }
  return null
}

const applyRunTarget = async (value) => {
  if (!value) return
  localStorage.setItem('run_target', value)
  if (value.startsWith('model:')) {
    selectedModelId.value = value.slice('model:'.length)
    selectedStrategy.value = 'single_model'
    localStorage.setItem('agent_strategy', selectedStrategy.value)
    if (activeSession.value && (selectedModelId.value !== activeSession.value.model_id || activeSession.value.strategy !== 'single_model')) await updateSessionRunConfig(selectedModelId.value, 'single_model')
    return
  }
  if (value.startsWith('strategy:')) {
    selectedStrategy.value = value.slice('strategy:'.length)
    selectedModelId.value = null
    localStorage.setItem('agent_strategy', selectedStrategy.value)
    localStorage.setItem('selected_model_id', '')
    if (activeSession.value && (activeSession.value.model_id || activeSession.value.strategy !== selectedStrategy.value)) await updateSessionRunConfig(null, selectedStrategy.value)
  }
}

const renameSession = async (session) => {
  const title = window.prompt('请输入新的会话标题', session.title)
  if (!title?.trim()) return
  const response = await sessionsApi.updateSession(session.id, { title: title.trim() })
  const index = sessions.value.findIndex(item => item.id === session.id)
  if (index >= 0) sessions.value[index] = response.data
  if (activeSession.value?.id === session.id) activeSession.value = response.data
}

const deleteSession = async (session) => {
  if (!window.confirm(`确认删除“${session.title}”？`)) return
  await sessionsApi.deleteSession(session.id)
  sessions.value = sessions.value.filter(item => item.id !== session.id)
  if (activeSession.value?.id === session.id) {
    activeSession.value = null
    messages.value = []
    if (sessions.value.length) await selectSession(sessions.value[0])
  }
}

const loadAgentStrategies = async () => {
  const response = await agentApi.listPublicStrategies()
  agentStrategies.value = response.data || []
  if (runTarget.value?.startsWith('model:')) return
  if (!agentStrategies.value.some(item => item.strategy_name === selectedStrategy.value)) {
    selectedStrategy.value = agentStrategies.value[0]?.strategy_name || 'react'
  }
}

const loadTools = async () => {
  const response = await toolsApi.listEnabledTools()
  availableTools.value = response.data || []
  selectedToolIds.value = selectedToolIds.value.filter(id => availableTools.value.some(tool => tool.id === id))
}

const loadKnowledgeCollections = async () => {
  const response = await knowledgeApi.listCollections()
  knowledgeCollections.value = response.data?.collections || []
  selectedCollectionIds.value = selectedCollectionIds.value.filter(id => knowledgeCollections.value.some(collection => collection.id === id))
}

const loadModels = async () => {
  const response = await modelsApi.listVisibleModels()
  visibleModels.value = response.data || []
}

const allToolsSelected = computed(() => availableTools.value.length > 0 && selectedToolIds.value.length === availableTools.value.length)
const runTargetDescription = computed(() => {
  if (selectedStrategy.value === 'single_model') {
    return `单模型直连：使用 ${selectedModelName.value} 直接回答，适合普通问答。`
  }
  const descriptions = {
    react: 'ReAct：适合需要工具/知识库的问答，会先判断行动再生成答案。',
    plan_execute: 'Plan-Execute：先规划再执行，适合复杂、多步骤任务。',
    multi_agent: '多 Agent：分析、执行、校验分工协作，适合更复杂的问题。'
  }
  return descriptions[selectedStrategy.value] || 'Agent 图：由多个步骤协作完成回答。'
})
const selectedModelName = computed(() => {
  const model = visibleModels.value.find(item => item.id === selectedModelId.value)
  return modelLabel(model)
})

const modelLabel = (model) => model?.display_name || model?.model_name || 'Model'

const toggleTool = (toolId) => {
  selectedToolIds.value = selectedToolIds.value.includes(toolId) ? selectedToolIds.value.filter(id => id !== toolId) : [...selectedToolIds.value, toolId]
  localStorage.setItem('selected_tool_ids', JSON.stringify(selectedToolIds.value))
}

const toggleAllTools = () => {
  selectedToolIds.value = allToolsSelected.value ? [] : availableTools.value.map(tool => tool.id)
  localStorage.setItem('selected_tool_ids', JSON.stringify(selectedToolIds.value))
}

const toggleCollection = (collectionId) => {
  selectedCollectionIds.value = selectedCollectionIds.value.includes(collectionId) ? selectedCollectionIds.value.filter(id => id !== collectionId) : [...selectedCollectionIds.value, collectionId]
  localStorage.setItem('selected_collection_ids', JSON.stringify(selectedCollectionIds.value))
}

const clearCollections = () => {
  selectedCollectionIds.value = []
  localStorage.setItem('selected_collection_ids', '[]')
}

const modelCapabilityLabel = (model) => {
  const caps = []
  if (model.capabilities?.text !== false) caps.push('文本')
  if (model.capabilities?.vision || model.is_multimodal) caps.push('视觉')
  if (model.capabilities?.tool_calling) caps.push('工具')
  return caps.join('/') || '未标注能力'
}

const connectWebSocket = () => {
  if (!activeSession.value) return
  if (ws && wsSessionId === activeSession.value.id && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) return
  if (ws && wsSessionId !== activeSession.value.id) {
    ws.close()
    ws = null
  }
  const token = localStorage.getItem('token')
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const host = window.location.port === '5173' ? 'localhost:8000' : window.location.host
  wsSessionId = activeSession.value.id
  ws = new WebSocket(`${protocol}//${host}/ws/chat/${activeSession.value.id}?token=${encodeURIComponent(token)}`)
  ws.onopen = () => {
    if (sending.value && runningSessionId.value === activeSession.value?.id) updateAgentProgress('connect', 'WebSocket 已连接，等待后端确认')
  }
  ws.onmessage = handleSocketMessage
  ws.onerror = () => {
    sending.value = false
    workingModel.value = ''
    messages.value.push({ localId: crypto.randomUUID(), role: 'assistant', content: 'WebSocket 连接失败，请确认后端服务已启动。', metadata: {}, tool_calls: [] })
  }
  ws.onclose = () => {
    if (sending.value && runningSessionId.value === activeSession.value?.id) {
      updateAgentProgress('connect', 'WebSocket 已断开；后端会继续处理并保存结果', { done: true })
      workingModel.value = ''
    }
  }
}

const handleSocketMessage = async (event) => {
  const data = JSON.parse(event.data)
  if (data.type === 'user_saved') {
    updateAgentProgress('save', '用户消息已保存，Agent 即将开始执行')
    return
  }
  if (data.type === 'message_start') {
    updateAgentProgress('start', '后端已开始生成回复', { done: false })
    return
  }
  if (data.type === 'agent_received') {
    updateAgentProgress('received', data.message || '后端已收到消息', { done: false })
    return
  }
  if (data.type === 'session_title') {
    if (activeSession.value) activeSession.value.title = data.title
    const session = sessions.value.find(item => item.id === activeSession.value?.id)
    if (session) session.title = data.title
    return
  }
  if (data.type === 'model_status') {
    const status = `${nodeLabel(data.node)} 正在调用 ${data.display_name || data.model_name}（${data.backend}）`
    workingModel.value = status
    const draft = ensureAssistantDraft()
    draft.metadata.model_name = data.display_name || data.model_name
    draft.metadata.run_label = selectedStrategy.value === 'single_model' ? (data.display_name || data.model_name) : 'Graph'
    updateAgentProgress('model', status, {
      node: data.node,
      model: data.display_name || data.model_name,
      backend: data.backend,
      detail: data.ollama_base_url ? `Ollama 地址：${data.ollama_base_url}` : ''
    })
  }
  if (data.type === 'thinking') {
    ensureAssistantDraft().metadata.thinking.push({ node: data.node, model_name: data.model_name, backend: data.backend, content: data.content })
    updateAgentProgress('thinking', data.node ? `${nodeLabel(data.node)} 已完成思考` : data.content, { node: data.node, detail: data.content })
  } else if (data.type === 'agent_step') {
    ensureAssistantDraft().metadata.agent_steps.push(data)
    updateAgentProgress('step', `${nodeLabel(data.node)} 输出中间结果`, { node: data.node, model: data.model, backend: data.backend, detail: data.content })
  } else if (data.type === 'sources') {
    ensureAssistantDraft().metadata.sources = data.sources || []
    updateAgentProgress('sources', `知识库返回 ${data.sources?.length || 0} 条参考来源`, { detail: data.sources?.map(item => item.filename).filter(Boolean).slice(0, 3).join('、') })
  } else if (data.type === 'tool_call') {
    ensureAssistantDraft().tool_calls.push(data)
    updateAgentProgress('tool', `正在执行工具：${data.name || '工具调用'}`, { detail: data.input ? JSON.stringify(data.input) : '' })
  } else if (data.type === 'token') {
    ensureAssistantDraft().content += data.content
    updateAgentProgress('answer', '正在生成最终回复', { done: false })
  } else if (data.type === 'message_done') {
    const index = messages.value.findIndex(item => item.streaming)
    const doneMessage = normalizeMessage(data.message)
    if (sendStartedAt.value) {
      doneMessage.metadata.elapsed_ms = Date.now() - sendStartedAt.value
    }
    if (index >= 0) messages.value[index] = doneMessage
    sending.value = false
    runningSessionId.value = null
    sendStartedAt.value = null
    workingModel.value = ''
    await loadSessions()
  } else if (data.type === 'message_cancelled') {
    updateAgentProgress('cancel', data.message || '本次对话已中止', { failed: true })
    const draft = ensureAssistantDraft()
    draft.content = data.message || '本次对话已中止'
    draft.streaming = false
    sending.value = false
    runningSessionId.value = null
    sendStartedAt.value = null
    workingModel.value = ''
  } else if (data.type === 'error') {
    const draft = ensureAssistantDraft()
    updateAgentProgress('error', 'Agent 执行失败', { detail: data.message, failed: true })
    draft.content = data.message
    draft.streaming = false
    sending.value = false
    sendStartedAt.value = null
    workingModel.value = ''
  }
  await scrollToBottom()
}

const ensureAssistantDraft = () => {
  let message = messages.value.find(item => item.streaming)
  if (!message) {
    message = {
      localId: crypto.randomUUID(),
      role: 'assistant',
      content: '',
      metadata: {
        strategy: selectedStrategy.value,
        run_label: selectedStrategy.value === 'single_model' ? selectedModelName.value : 'Graph',
        thinking: [],
        agent_steps: [],
        sources: [],
        progress: { status: selectedStrategy.value === 'single_model' ? `等待连接 ${selectedModelName.value}` : '等待 Agent 图连接', items: [] }
      },
      tool_calls: [],
      streaming: true
    }
    messages.value.push(message)
  }
  return message
}

const updateAgentProgress = (type, label, extra = {}) => {
  const message = ensureAssistantDraft()
  const progress = message.metadata.progress || { status: '', items: [] }
  const item = {
    id: crypto.randomUUID(),
    type,
    label,
    node: extra.node,
    model: extra.model,
    backend: extra.backend,
    detail: extra.detail,
    failed: Boolean(extra.failed),
    done: extra.done !== false,
    time: new Date().toLocaleTimeString()
  }
  progress.status = label
  progress.items = [...(progress.items || []), item].slice(-8)
  message.metadata.progress = progress
}

const sendMessage = async () => {
  if (sending.value || (!draft.value.trim() && attachments.value.length === 0)) return
  if (selectedModelId.value) {
    await updateSessionRunConfig(selectedModelId.value, 'single_model')
  } else if (activeSession.value && activeSession.value.strategy !== selectedStrategy.value) {
    await updateSessionRunConfig(null, selectedStrategy.value)
  }
  if (!activeSession.value) await createSession()
  const content = draft.value.trim()
  const sentAttachments = [...attachments.value]
  try {
    await sessionsApi.preflightMessage(activeSession.value.id, {
      strategy: selectedStrategy.value,
      tool_ids: selectedToolIds.value,
      attachments: sentAttachments.map(({ id, name, type, size, preview }) => ({ id, name, type, size, preview }))
    })
  } catch (error) {
    const message = error.response?.data?.detail || error.message || '本轮配置校验失败'
    messages.value.push({ localId: crypto.randomUUID(), role: 'assistant', content: message, metadata: {}, tool_calls: [] })
    return
  }
  if (!ws || ws.readyState === WebSocket.CLOSED || ws.readyState === WebSocket.CLOSING) connectWebSocket()
  sendStartedAt.value = Date.now()
  runningSessionId.value = activeSession.value?.id || null
  messages.value.push({ localId: crypto.randomUUID(), role: 'user', content, attachments: sentAttachments, metadata: {}, tool_calls: [] })
  const draftMessage = ensureAssistantDraft()
  draftMessage.metadata.progress = {
    status: selectedStrategy.value === 'single_model' ? `正在连接 ${selectedModelName.value}` : '正在连接 Agent 图',
    items: [{ id: crypto.randomUUID(), type: 'connect', label: '正在建立 WebSocket 连接', done: false, time: new Date().toLocaleTimeString() }]
  }
  draft.value = ''
  attachments.value = []
  sending.value = true
  workingModel.value = selectedStrategy.value === 'single_model' ? `正在连接 ${selectedModelName.value}` : '正在连接 Agent 图'
  try {
    await waitForSocket()
    updateAgentProgress('connect', 'WebSocket 已连接，正在发送用户消息')
    localStorage.setItem('agent_strategy', selectedStrategy.value)
    localStorage.setItem('selected_tool_ids', JSON.stringify(selectedToolIds.value))
    localStorage.setItem('selected_collection_ids', JSON.stringify(selectedCollectionIds.value))
    const toolIds = selectedToolIds.value
    const collectionIds = selectedCollectionIds.value
    ws.send(JSON.stringify({ type: 'user_message', strategy: selectedStrategy.value, tool_ids: toolIds, collection_ids: collectionIds, content, attachments: sentAttachments.map(({ id, name, type, size, preview }) => ({ id, name, type, size, preview })) }))
    updateAgentProgress('graph', selectedStrategy.value === 'single_model' ? `已提交到 ${selectedModelName.value}，外部工具 ${toolIds.length} 个，知识库 ${collectionIds.length || '未开启'}` : `已提交到 ${selectedStrategy.value} Agent 图，外部工具 ${toolIds.length} 个，知识库 ${collectionIds.length || '未开启'}`, { done: false })
    await scrollToBottom()
  } catch (error) {
    sending.value = false
    workingModel.value = ''
    const draft = ensureAssistantDraft()
    updateAgentProgress('error', '连接 Agent 图失败', { detail: error.message || '连接 Agent 图失败', failed: true })
    draft.content = error.message || '连接 Agent 图失败'
    draft.streaming = false
  }
}

const cancelMessage = () => {
  if (ws?.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ type: 'cancel_message' }))
    updateAgentProgress('cancel', '正在中止本次对话', { done: false })
  }
}

const waitForSocket = () => new Promise((resolve, reject) => {
  if (ws?.readyState === WebSocket.OPEN) return resolve()
  if (!ws || ws.readyState === WebSocket.CLOSED || ws.readyState === WebSocket.CLOSING) {
    connectWebSocket()
  }
  const startedAt = Date.now()
  const timer = window.setInterval(() => {
    if (ws?.readyState === WebSocket.OPEN) {
      window.clearInterval(timer)
      resolve()
    } else if (!ws || ws.readyState === WebSocket.CLOSED || ws.readyState === WebSocket.CLOSING) {
      window.clearInterval(timer)
      reject(new Error('WebSocket 连接已关闭，请确认后端服务是否正常'))
    } else if (Date.now() - startedAt > 5000) {
      window.clearInterval(timer)
      reject(new Error(selectedStrategy.value === 'single_model' ? '连接模型超时，请确认后端服务和登录状态' : '连接 Agent 图超时，请确认后端服务和登录状态'))
    }
  }, 50)
})

const handlePaste = async (event) => {
  const files = Array.from(event.clipboardData?.files || []).filter(file => file.type.startsWith('image/'))
  if (files.length) await addAttachments(files)
}

const handleFileChange = async (event) => {
  await addAttachments(Array.from(event.target.files || []))
  event.target.value = ''
}

const addAttachments = async (files) => {
  const imageFiles = files.filter(file => file.type.startsWith('image/'))
  for (const file of imageFiles) {
    attachments.value.push({ id: crypto.randomUUID(), name: file.name, type: file.type, size: file.size, preview: await readFileAsDataUrl(file) })
  }
}

const readFileAsDataUrl = (file) => new Promise((resolve, reject) => {
  const reader = new FileReader()
  reader.onload = () => resolve(reader.result)
  reader.onerror = () => reject(reader.error)
  reader.readAsDataURL(file)
})

const removeAttachment = (id) => {
  attachments.value = attachments.value.filter(item => item.id !== id)
}

const appendTranscribedText = (text) => {
  draft.value = draft.value ? `${draft.value} ${text}` : text
}

const showAudioError = (message) => {
  messages.value.push({ localId: crypto.randomUUID(), role: 'assistant', content: message, metadata: {}, tool_calls: [] })
}

const nodeLabel = (node) => ({
  analyst: '分析节点',
  planner: '规划节点',
  executor: '执行节点',
  validator: '校验节点',
  agent: 'ReAct 节点'
}[node] || node || 'Agent 节点')

const normalizeMessage = (message) => ({
  ...message,
  metadata: {
    ...(message.metadata || {}),
    thinking: Array.isArray(message.metadata?.thinking) ? message.metadata.thinking : (message.metadata?.thinking ? [{ content: message.metadata.thinking }] : []),
    agent_steps: message.metadata?.agent_steps || [],
    sources: message.metadata?.sources || [],
    progress: message.metadata?.progress || null
  },
  tool_calls: message.tool_calls || [],
  attachments: message.metadata?.attachments || []
})

const scrollToBottom = async () => {
  await nextTick()
  if (messageList.value) messageList.value.scrollTop = messageList.value.scrollHeight
}

onMounted(async () => {
  await loadAgentStrategies()
  await loadModels()
  await applyRunTarget(runTarget.value)
  await loadTools()
  await loadKnowledgeCollections()
  await loadSessions()
})
</script>

<style scoped lang="scss">
.chat-page { height: 100vh; display: flex; background: #f5f5f5; overflow: hidden; }
.chat-main { flex: 1; min-width: 0; display: grid; grid-template-rows: auto 1fr auto; }
.chat-toolbar { display: flex; align-items: center; justify-content: space-between; gap: 16px; padding: 16px 24px; background: $surface; border-bottom: 1px solid $outline-variant; }
.eyebrow { color: $primary-color; font-size: 12px; letter-spacing: 0.14em; text-transform: uppercase; }
.chat-toolbar h2 { color: $on-surface; font-size: 22px; }
.working-model { display: block; margin-top: 4px; color: $primary-color; }
.toolbar-actions { display: flex; align-items: center; gap: 10px; }
.run-target-help { max-width: 280px; color: $on-surface-variant; font-size: 12px; line-height: 1.35; }
select { height: 40px; border: 1px solid $outline; border-radius: $radius-small; padding: 0 10px; background: transparent; color: $on-surface; }
.message-list { overflow: auto; padding: 24px; display: flex; flex-direction: column; gap: 18px; }
.tool-dropdown { position: relative; }
.tool-panel { position: absolute; right: 0; top: calc(100% + 8px); z-index: 10; width: min(360px, 92vw); display: grid; gap: 8px; padding: 12px; border: 1px solid $outline-variant; border-radius: $radius-large; background: $surface; box-shadow: $shadow-2; }
.tool-panel-head { display: flex; justify-content: space-between; gap: 14px; align-items: center; }
.tool-panel-head strong { color: $on-surface; }
.tool-empty { margin-top: 4px; color: $on-surface-variant; font-size: 13px; }
.tool-check { display: flex; align-items: center; gap: 8px; width: 100%; border: 1px solid $outline-variant; border-radius: $radius-small; padding: 9px; background: transparent; color: $on-surface; cursor: pointer; text-align: left; }
.tool-check:hover { background: rgba($primary-color, .06); }
.tool-check .material-icons { color: $primary-color; font-size: 20px; }
.tool-check small { margin-left: auto; color: $on-surface-variant; }
.danger { color: $error !important; border-color: rgba($error, .4) !important; }
.empty-state { min-height: 360px; display: grid; place-items: center; color: $on-surface-variant; }
.empty-state .material-icons { font-size: 52px; color: $outline; }
.composer { padding: 16px 24px; background: $surface; border-top: 1px solid $outline-variant; }
.composer textarea { width: 100%; min-height: 84px; max-height: 180px; resize: vertical; border: 1px solid $outline; border-radius: $radius-large; padding: 12px; color: $on-surface; background: transparent; }
.composer-actions { display: flex; justify-content: space-between; align-items: center; margin-top: 10px; gap: 12px; }
.upload-button input { display: none; }
.attachment-strip { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 10px; }
.attachment-item { position: relative; }
.attachment-item img { width: 96px; height: 72px; object-fit: cover; border-radius: $radius-small; border: 1px solid $outline-variant; }
.attachment-item button { position: absolute; top: 4px; right: 4px; width: 24px; height: 24px; border: 0; border-radius: $radius-small; background: rgba(0,0,0,.55); color: white; cursor: pointer; }
.attachment-item .material-icons { font-size: 16px; }
@media (max-width: 860px) { .chat-page { flex-direction: column; } .chat-toolbar { flex-direction: column; align-items: stretch; } }
</style>
