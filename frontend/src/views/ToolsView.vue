<template>
  <div class="tools-page">
    <header class="tools-header">
      <div>
        <p class="eyebrow">Agent Tools</p>
        <h1>MCP 集成与外部 API</h1>
        <p>配置 Agent 可用工具。私有工具仅自己可用，公有工具所有用户可在对话时选择。</p>
      </div>
      <button class="material-button outlined" @click="router.push('/dashboard')">返回主页</button>
    </header>

    <section class="editor-card">
      <h2>{{ form.id ? '编辑工具' : '新增工具' }}</h2>
      <details class="mcp-import">
        <summary>从 MCP JSON 导入</summary>
        <p>可直接粘贴 Claude / Cherry Studio / ClawHub 常见的 <code>mcpServers</code> 配置。</p>
        <textarea v-model="mcpImportText" placeholder='{"mcpServers":{"gaokao-expert-mcp":{"type":"sse","url":"https://example.com/sse"}}}'></textarea>
        <button class="material-button outlined" @click="importMcpJson">解析并填入表单</button>
      </details>
      <div class="form-grid">
        <label><span>名称</span><input v-model.trim="form.name" placeholder="例如：教务系统查询" /></label>
        <label><span>类型</span><select v-model="form.tool_type"><option value="external_api">外部 API</option><option value="mcp">MCP Server</option></select></label>
        <label v-if="form.tool_type === 'mcp'"><span>MCP 连接方式</span><select v-model="mcpTransport"><option value="stdio">stdio</option><option value="sse">SSE</option><option value="streamable_http">HTTP Stream</option></select></label>
        <label><span>请求方法</span><select v-model="form.method"><option>GET</option><option>POST</option><option>PUT</option><option>PATCH</option><option>DELETE</option></select></label>
        <label><span>{{ endpointLabel }}</span><input v-model.trim="form.endpoint" :placeholder="endpointPlaceholder" /></label>
      </div>
      <label class="full"><span>描述</span><textarea v-model.trim="form.description" placeholder="告诉用户这个工具适合处理什么任务"></textarea></label>
      <label class="full"><span>Headers JSON</span><textarea v-model="headersText" placeholder='{"Authorization":"Bearer xxx"}'></textarea></label>
      <label v-if="form.tool_type === 'mcp'" class="full"><span>MCP 配置 JSON</span><textarea v-model="bodyText" :placeholder="mcpConfigPlaceholder"></textarea></label>
      <label v-else class="full"><span>请求体模板 JSON</span><textarea v-model="bodyText" placeholder='{"query":"会被自动填充，可留空"}'></textarea></label>
      <div class="switches">
        <label><input v-model="form.is_public" type="checkbox" /> 设为公有工具</label>
        <label><input v-model="form.is_enabled" type="checkbox" /> 启用</label>
      </div>
      <div class="actions">
        <button class="material-button filled" @click="saveTool">{{ form.id ? '保存修改' : '创建工具' }}</button>
        <button v-if="form.id" class="material-button text" @click="resetForm">取消编辑</button>
      </div>
      <p v-if="notice" :class="['notice', noticeType]">{{ notice }}</p>
    </section>

    <section class="tool-list">
      <article v-for="tool in tools" :key="tool.id" class="tool-card">
        <div>
          <div class="tool-title">
            <span class="material-icons">{{ tool.tool_type === 'mcp' ? 'hub' : 'api' }}</span>
            <h3>{{ tool.name }}</h3>
          </div>
          <p>{{ tool.description || '暂无描述' }}</p>
          <small>{{ tool.method }} {{ tool.endpoint }}</small>
        </div>
        <div class="badges">
          <span>{{ tool.tool_type === 'mcp' ? 'MCP' : '外部 API' }}</span>
          <span>{{ tool.is_public ? '公有' : '私有' }}</span>
          <span>{{ tool.is_enabled ? '启用' : '停用' }}</span>
          <span v-if="testResults[tool.id]" :class="testResults[tool.id].ok ? 'ok-badge' : 'bad-badge'">{{ testResults[tool.id].ok ? '连接正常' : '连接失败' }}</span>
          <span v-if="tool.owner_name">{{ tool.owner_name }}</span>
        </div>
        <p v-if="testResults[tool.id]" :class="['test-result', testResults[tool.id].ok ? 'ok' : 'bad']">
          {{ testResults[tool.id].message }}
          <template v-if="testResults[tool.id].available_tools?.length">：{{ testResults[tool.id].available_tools.join('、') }}</template>
        </p>
        <div v-if="tool.owned_by_me || user.role === 'admin'" class="card-actions">
          <button class="material-button text" :disabled="testingToolId === tool.id" @click="testTool(tool)">{{ testingToolId === tool.id ? '测试中...' : '测试连接' }}</button>
          <button class="material-button text" @click="editTool(tool)">编辑</button>
          <button class="material-button text danger" @click="removeTool(tool)">删除</button>
        </div>
      </article>
      <p v-if="!tools.length" class="empty">暂无工具。先添加一个外部 API 或 MCP Server。</p>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import toolsApi from '@/api/tools'

const router = useRouter()
const user = JSON.parse(localStorage.getItem('user') || '{}')
const tools = ref([])
const notice = ref('')
const noticeType = ref('success')
const headersText = ref('{}')
const bodyText = ref('{}')
const mcpTransport = ref('sse')
const mcpImportText = ref('')
const testingToolId = ref('')
const testResults = ref({})
const form = reactive({ id: '', name: '', description: '', tool_type: 'external_api', endpoint: '', method: 'POST', is_public: false, is_enabled: true })

const endpointLabel = computed(() => {
  if (form.tool_type !== 'mcp') return '端点地址'
  return mcpTransport.value === 'stdio' ? '启动命令' : 'MCP 服务地址'
})

const endpointPlaceholder = computed(() => {
  if (form.tool_type !== 'mcp') return 'https://example.com/api/search'
  if (mcpTransport.value === 'stdio') return 'python / node / uvx / npx 等命令，例如 npx'
  if (mcpTransport.value === 'streamable_http') return 'https://example.com/mcp'
  return 'https://example.com/sse'
})

const mcpConfigPlaceholder = computed(() => {
  if (mcpTransport.value === 'stdio') {
    return JSON.stringify({ transport: 'stdio', tool_name: 'search', args: ['-y', '@modelcontextprotocol/server-example'], env: {}, cwd: null, arguments: {} }, null, 2)
  }
  return JSON.stringify({ transport: mcpTransport.value, tool_name: 'search', arguments: {} }, null, 2)
})

watch(mcpTransport, () => {
  if (form.tool_type === 'mcp') {
    try {
      const body = parseJson(bodyText.value)
      body.transport = mcpTransport.value
      bodyText.value = JSON.stringify(body, null, 2)
    } catch {
      bodyText.value = mcpConfigPlaceholder.value
    }
  }
})

watch(() => form.tool_type, () => {
  if (form.tool_type === 'mcp') {
    form.method = 'POST'
    bodyText.value = mcpConfigPlaceholder.value
  }
})

const loadTools = async () => {
  const response = await toolsApi.listTools()
  tools.value = response.data || []
}

const parseJson = (text, fallback = {}) => {
  const value = text.trim()
  return value ? JSON.parse(value) : fallback
}

const saveTool = async () => {
  try {
    const payload = { ...form, headers: parseJson(headersText.value), body_template: parseJson(bodyText.value) }
    if (payload.tool_type === 'mcp') payload.body_template.transport = mcpTransport.value
    if (form.id) await toolsApi.updateTool(form.id, payload)
    else await toolsApi.createTool(payload)
    showNotice('工具已保存')
    resetForm()
    await loadTools()
  } catch (error) {
    showNotice(error.response?.data?.detail || error.message || '保存失败，请检查 JSON 格式', 'error')
  }
}

const importMcpJson = () => {
  try {
    const raw = parseJson(mcpImportText.value)
    const servers = raw.mcpServers || raw.servers || raw
    const [serverName, serverConfig] = Object.entries(servers)[0] || []
    if (!serverName || !serverConfig || typeof serverConfig !== 'object') {
      throw new Error('没有找到 mcpServers 配置')
    }

    const type = normalizeMcpTransport(serverConfig.type || serverConfig.transport || (serverConfig.command ? 'stdio' : 'sse'))
    form.tool_type = 'mcp'
    form.name = serverName
    form.description = `MCP Server：${serverName}`
    form.method = 'POST'
    form.endpoint = type === 'stdio' ? serverConfig.command : (serverConfig.url || serverConfig.endpoint || '')
    mcpTransport.value = type
    headersText.value = JSON.stringify(serverConfig.headers || {}, null, 2)
    bodyText.value = JSON.stringify({
      transport: type,
      tool_name: serverConfig.tool_name || '',
      args: serverConfig.args || [],
      env: serverConfig.env || {},
      cwd: serverConfig.cwd || null,
      arguments: serverConfig.arguments || {}
    }, null, 2)
    showNotice('已解析 MCP JSON。请填写 tool_name 后保存；如果不知道工具名，可先查看该 MCP 服务文档。')
  } catch (error) {
    showNotice(error.message || 'MCP JSON 解析失败', 'error')
  }
}

const normalizeMcpTransport = (type) => {
  const value = String(type || '').toLowerCase().replace('-', '_')
  if (value === 'http' || value === 'streamable_http' || value === 'streamablehttp') return 'streamable_http'
  if (value === 'stdio') return 'stdio'
  return 'sse'
}

const editTool = (tool) => {
  Object.assign(form, { id: tool.id, name: tool.name, description: tool.description || '', tool_type: tool.tool_type, endpoint: tool.endpoint, method: tool.method, is_public: tool.is_public, is_enabled: tool.is_enabled })
  headersText.value = JSON.stringify(tool.headers || {}, null, 2)
  bodyText.value = JSON.stringify(tool.body_template || {}, null, 2)
  mcpTransport.value = tool.body_template?.transport || 'sse'
}

const removeTool = async (tool) => {
  if (!window.confirm(`确认删除工具“${tool.name}”？`)) return
  await toolsApi.deleteTool(tool.id)
  await loadTools()
}

const testTool = async (tool) => {
  testingToolId.value = tool.id
  try {
    const response = await toolsApi.testTool(tool.id)
    testResults.value = { ...testResults.value, [tool.id]: response.data }
  } catch (error) {
    const result = { ok: false, message: error.response?.data?.detail || error.message || '测试连接失败' }
    testResults.value = { ...testResults.value, [tool.id]: result }
  } finally {
    testingToolId.value = ''
  }
}

const resetForm = () => {
  Object.assign(form, { id: '', name: '', description: '', tool_type: 'external_api', endpoint: '', method: 'POST', is_public: false, is_enabled: true })
  mcpTransport.value = 'sse'
  headersText.value = '{}'
  bodyText.value = '{}'
}

const showNotice = (message, type = 'success') => {
  notice.value = message
  noticeType.value = type
}

onMounted(loadTools)
</script>

<style scoped lang="scss">
.tools-page { min-height: 100vh; padding: 32px; background: #f5f5f5; color: $on-surface; }
.tools-header { display: flex; justify-content: space-between; gap: 20px; align-items: flex-start; margin: 0 auto 24px; max-width: 1120px; }
.eyebrow { color: $primary-color; letter-spacing: .14em; text-transform: uppercase; font-size: 12px; }
.tools-header h1 { margin: 6px 0; font-size: 30px; }
.editor-card, .tool-list { max-width: 1120px; margin: 0 auto 20px; }
.editor-card, .tool-card { background: $surface; border: 1px solid $outline-variant; border-radius: $radius-large; box-shadow: $shadow-1; }
.editor-card { padding: 20px; display: grid; gap: 14px; }
.mcp-import { padding: 12px; border: 1px dashed $outline; border-radius: $radius-medium; background: rgba($primary-color, .04); }
.mcp-import summary { cursor: pointer; color: $primary-color; font-weight: 700; }
.mcp-import p { margin: 8px 0; color: $on-surface-variant; font-size: 13px; }
.mcp-import textarea { width: 100%; min-height: 120px; margin-bottom: 10px; }
.form-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px; }
label { display: grid; gap: 6px; color: $on-surface-variant; font-size: 13px; }
input, select, textarea { border: 1px solid $outline; border-radius: $radius-small; padding: 10px; background: transparent; color: $on-surface; }
textarea { min-height: 78px; resize: vertical; font-family: Consolas, monospace; }
.full { display: grid; }
.switches, .actions, .badges, .card-actions { display: flex; gap: 10px; flex-wrap: wrap; align-items: center; }
.switches label { display: flex; align-items: center; gap: 6px; }
.tool-list { display: grid; gap: 14px; }
.tool-card { padding: 18px; display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: 12px; }
.tool-title { display: flex; align-items: center; gap: 8px; }
.tool-title .material-icons { color: $primary-color; }
.tool-card p { margin: 6px 0; color: $on-surface-variant; }
.tool-card small { color: $on-surface-variant; word-break: break-all; }
.badges span { padding: 4px 8px; border-radius: $radius-small; background: $primary-container; color: $primary-color; font-size: 12px; }
.badges .ok-badge { background: rgba($primary-color, .12); color: $primary-color; }
.badges .bad-badge { background: $error-container; color: $error; }
.test-result { grid-column: 1 / -1; margin: 0; font-size: 13px; }
.test-result.ok { color: $primary-color; }
.test-result.bad { color: $error; }
.card-actions { grid-column: 1 / -1; justify-content: flex-end; }
.danger { color: $error !important; }
.notice.error { color: $error; }
.notice.success { color: $primary-color; }
.empty { padding: 22px; text-align: center; color: $on-surface-variant; }
@media (max-width: 760px) { .tools-page { padding: 18px; } .tools-header, .tool-card { grid-template-columns: 1fr; flex-direction: column; } .form-grid { grid-template-columns: 1fr; } }
</style>
