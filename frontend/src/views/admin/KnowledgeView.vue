<template>
  <div class="knowledge-page">
    <div class="page-header">
      <div>
        <p class="eyebrow">Knowledge Base</p>
        <h2>知识库管理</h2>
        <p>上传文档或添加网页来源，默认私有，管理员可按需设为公共。</p>
      </div>
      <div class="page-actions">
        <button class="material-button outlined" @click="goHome">
          <span class="material-icons">home</span>
          返回主页
        </button>
        <button class="material-button outlined" @click="fetchDocuments">
          <span class="material-icons">refresh</span>
          刷新
        </button>
        <button class="material-button outlined" :disabled="reindexing" @click="reindexAllDocuments">
          <span class="material-icons">sync</span>
          {{ reindexing ? '提交中...' : '按当前嵌入模型重新索引' }}
        </button>
      </div>
    </div>

    <div v-if="notice.message" class="notice" :class="notice.type">
      <span class="material-icons">{{ notice.type === 'error' ? 'error' : 'check_circle' }}</span>
      <span>{{ notice.message }}</span>
    </div>

    <section class="action-grid">
      <form class="panel-card upload-card" @submit.prevent="uploadDocument">
        <div class="card-header">
          <div>
            <h3>文档上传</h3>
          <p>支持 {{ uploadPolicy.allowedExtensions.join('、').toUpperCase() }}；单文件最大 {{ uploadPolicy.maxFileSizeMb }}MB。</p>
          </div>
          <span class="material-icons">upload_file</span>
        </div>
        <label class="file-drop" :class="{ disabled: uploading }">
          <input ref="fileInput" type="file" multiple :accept="fileAccept" :disabled="uploading" @change="handleFileChange" />
          <span class="material-icons">drive_folder_upload</span>
          <strong>{{ uploading ? '当前上传列表已锁定' : selectedFiles.length ? `已选择 ${selectedFiles.length} 个文件` : '选择一个或多个文件' }}</strong>
          <small>{{ uploading ? '上传和处理过程中不允许增删文件。' : '点击上传前可删除已选文件；默认私有，可勾选设为公共。' }}</small>
        </label>
        <label class="archive-field">
          <span>所属知识库（可选，不存在会自动创建）</span>
          <input v-model.trim="uploadCollectionName" list="knowledge-collections" placeholder="留空则不加入任何知识库" :disabled="uploading" />
        </label>
        <div class="upload-rules">
          <span>支持：{{ uploadPolicy.allowedExtensions.join('、').toUpperCase() }}</span>
          <span>单文件不超过 {{ uploadPolicy.maxFileSizeMb }}MB</span>
          <span>单次最多 {{ uploadPolicy.maxFilesPerBatch }} 个文件</span>
        </div>
        <div v-if="selectedFiles.length" class="selected-files">
          <span v-for="file in selectedFiles" :key="`${file.name}-${file.size}`">{{ file.name }}</span>
        </div>
        <div v-if="acceptedFiles.length" class="accepted-files">
          <strong>将上传的文件</strong>
          <p v-for="item in acceptedFiles" :key="`${item.name}-${item.size}`">
            {{ item.name }}：{{ formatFileSize(item.size) }}，符合上传规则
          </p>
        </div>
        <div v-if="rejectedFiles.length" class="rejected-files">
          <strong>以下文件不会上传</strong>
          <p v-for="item in rejectedFiles" :key="`${item.name}-${item.reason}`">{{ item.name }}：{{ item.reason }}</p>
        </div>
        <div v-if="uploadQueue.length" class="upload-queue">
          <div class="queue-header">
            <strong>上传列表</strong>
            <small>{{ uploading ? '上传开始后不允许删除单个文件' : '点击上传并处理前可删除单个文件' }}</small>
          </div>
          <article v-for="item in uploadQueue" :key="item.id" class="upload-item">
            <div class="upload-title">
              <strong>{{ item.name }}</strong>
              <small>{{ formatFileSize(item.size) }}</small>
              <span :class="['upload-state', item.state]">{{ uploadStateText(item) }}</span>
              <button class="queue-remove" type="button" title="移除列表并删除记录" @click="removeUploadQueueItem(item)">
                <span class="material-icons">delete</span>
              </button>
            </div>
            <div class="step-track">
              <span v-for="step in uploadSteps" :key="step.key" :class="['step-dot', stepClass(item, step.key)]">
                <i class="material-icons">{{ stepIcon(item, step.key) }}</i>
                <em>{{ step.label }}</em>
              </span>
            </div>
            <div class="progress-line">
              <span :style="{ width: `${item.progress}%` }"></span>
            </div>
            <small v-if="item.message">{{ item.message }}</small>
            <small v-if="item.startedAt" class="elapsed-time">已用时 {{ elapsedTime(item) }}</small>
          </article>
        </div>
        <label class="switch-row">
          <input v-model="uploadPublic" type="checkbox" />
          <span>上传后设为公共文档</span>
        </label>
        <button class="material-button filled" type="submit" :disabled="uploading || selectedFiles.length === 0 || uploadCompleted">
          {{ uploading ? '上传中...' : selectedFiles.length > 1 ? '批量上传并处理' : '上传并处理' }}
        </button>
      </form>

      <form class="panel-card" @submit.prevent="addUrls">
        <div class="card-header">
          <div>
            <h3>网页抓取</h3>
            <p>每行一个 URL，系统会记录来源并验证可访问性。</p>
          </div>
          <span class="material-icons">travel_explore</span>
        </div>
        <textarea v-model="urlText" placeholder="https://example.edu/page\nhttps://example.edu/help"></textarea>
        <label class="archive-field">
          <span>所属知识库（可选，不存在会自动创建）</span>
          <input v-model.trim="urlCollectionName" list="knowledge-collections" placeholder="留空则不加入任何知识库" :disabled="addingUrls" />
        </label>
        <label class="switch-row">
          <input v-model="urlPublic" type="checkbox" />
          <span>添加后设为公共文档</span>
        </label>
        <button class="material-button filled" type="submit" :disabled="addingUrls || !urlText.trim()">
          {{ addingUrls ? '添加中...' : '添加网页来源' }}
        </button>
        <div v-if="urlQueue.length" class="upload-queue url-queue">
          <div class="queue-header">
            <strong>网页抓取列表</strong>
            <small>提交后自动跟踪抓取和向量化进度</small>
          </div>
          <article v-for="item in urlQueue" :key="item.id" class="upload-item">
            <div class="upload-title">
              <strong>{{ item.name }}</strong>
              <small>URL</small>
              <span :class="['upload-state', item.state]">{{ urlStateText(item) }}</span>
              <button class="queue-remove" type="button" title="移除列表并删除记录" @click="removeUrlQueueItem(item)">
                <span class="material-icons">delete</span>
              </button>
            </div>
            <div class="step-track url-track">
              <span v-for="step in urlSteps" :key="step.key" :class="['step-dot', urlStepClass(item, step.key)]">
                <i class="material-icons">{{ urlStepIcon(item, step.key) }}</i>
                <em>{{ step.label }}</em>
              </span>
            </div>
            <div class="progress-line">
              <span :style="{ width: `${item.progress}%` }"></span>
            </div>
            <small v-if="item.message">{{ item.message }}</small>
            <small v-if="item.startedAt" class="elapsed-time">已用时 {{ elapsedTime(item) }}</small>
          </article>
        </div>
      </form>
    </section>

    <section class="collection-create-card">
      <div>
        <p class="eyebrow">Knowledge Collection</p>
        <h3>单独新建知识库</h3>
        <p>可以先建立空知识库，之后上传文档、抓取网页或在列表中手动把已有内容加入该知识库。</p>
      </div>
      <form class="create-collection" @submit.prevent="createCollection">
        <input v-model.trim="newCollectionName" placeholder="输入知识库名称，例如：高数真题" />
        <button class="material-button filled" type="submit" :disabled="creatingCollection || !newCollectionName">
          {{ creatingCollection ? '创建中...' : '新建知识库' }}
        </button>
      </form>
    </section>

    <section class="filter-card">
      <label>
        <span>处理状态</span>
        <select v-model="filters.status" @change="fetchDocuments">
          <option value="">全部</option>
          <option value="processing">处理中</option>
          <option value="ready">就绪</option>
          <option value="error">失败</option>
        </select>
      </label>
      <label>
        <span>可见性</span>
        <select v-model="filters.visibility" @change="fetchDocuments">
          <option value="">全部</option>
          <option value="public">公共</option>
          <option value="private">私有</option>
        </select>
      </label>
      <label>
        <span>搜索</span>
        <input v-model.trim="keyword" placeholder="按文件名或 URL 过滤" />
      </label>
    </section>

    <datalist id="knowledge-collections">
      <option v-for="collection in collections" :key="collection.id" :value="collection.name" />
    </datalist>

    <section class="table-card">
      <div v-if="loading" class="loading-state">
        <div class="material-spinner"></div>
        <p>加载文档中...</p>
      </div>
      <div v-else-if="filteredDocuments.length === 0 && collections.length === 0" class="empty-state">
        <span class="material-icons">folder_off</span>
        <p>暂无匹配文档</p>
      </div>
      <div v-else class="collection-tree">
        <article v-for="group in collectionGroups" :key="group.id" class="collection-group">
          <header class="collection-header" @click="toggleCollectionGroup(group.id)">
            <div>
              <span class="material-icons expand-icon" :class="{ collapsed: isCollectionCollapsed(group.id) }">expand_more</span>
              <span class="material-icons">{{ group.id === 'unfiled' ? 'folder_off' : 'folder' }}</span>
              <strong>{{ group.name }}</strong>
            </div>
            <div class="collection-header-actions">
              <small>{{ group.documents.length }} 项</small>
              <template v-if="group.id !== 'unfiled'">
                <button class="icon-action" type="button" title="重命名知识库" @click.stop="renameCollection(group)">
                  <span class="material-icons">edit</span>
                </button>
                <button class="icon-action danger" type="button" title="删除知识库" @click.stop="deleteCollectionGroup(group)">
                  <span class="material-icons">delete</span>
                </button>
              </template>
            </div>
          </header>
          <div v-if="!isCollectionCollapsed(group.id) && group.documents.length === 0" class="empty-collection">暂无文档或网页来源</div>
          <div v-else-if="!isCollectionCollapsed(group.id)" class="document-table nested">
            <div class="table-row table-head">
              <span>文档 / URL</span>
              <span>类型</span>
              <span>状态</span>
              <span>可见性</span>
              <span>所属知识库</span>
              <span>创建时间</span>
              <span>操作</span>
            </div>
            <div v-for="doc in group.documents" :key="doc.id" class="table-row">
              <div class="doc-cell">
                <span class="material-icons">{{ fileIcon(doc.file_type) }}</span>
                <div>
                  <strong>{{ doc.filename }}</strong>
                  <small :title="doc.file_path">{{ doc.file_path }}</small>
                  <em v-if="doc.error_message">{{ doc.error_message }}</em>
                </div>
              </div>
              <span class="chip">{{ doc.file_type }}</span>
              <span class="chip" :class="doc.status">{{ statusText(doc.status) }}</span>
              <button class="visibility-button" @click="toggleVisibility(doc)">
                {{ doc.is_public ? '公共' : '私有' }}
              </button>
              <select class="collection-select" :value="doc.collection_id || ''" @change="setDocumentCollection(doc, $event.target.value)">
                <option value="">不加入知识库</option>
                <option v-for="collection in collections" :key="collection.id" :value="collection.id">{{ collection.name }}</option>
              </select>
              <span>{{ formatTime(doc.created_at) }}</span>
              <div class="row-actions">
                <button class="material-button text" @click="openDetail(doc)">分段</button>
                <button v-if="doc.status === 'error'" class="material-button text" @click="retryDocument(doc)">重试</button>
                <button class="material-button text danger" @click="deleteDocument(doc)">删除</button>
              </div>
            </div>
          </div>
        </article>
      </div>
    </section>

    <div v-if="detail.open" class="drawer-mask" @click.self="closeDetail">
      <aside class="detail-drawer">
        <div class="drawer-header">
          <div>
            <p class="eyebrow">Document Chunks</p>
            <h3>文档分段</h3>
          </div>
          <button class="material-button text" @click="closeDetail">关闭</button>
        </div>

        <form v-if="detail.document" class="title-form" @submit.prevent="saveTitle">
          <label>
            <span>文档标题</span>
            <input v-model.trim="detail.title" />
          </label>
          <button class="material-button outlined" type="submit">保存标题</button>
        </form>

        <div v-if="detail.loading" class="loading-state compact">
          <div class="material-spinner"></div>
          <p>加载分段中...</p>
        </div>

        <div v-else-if="detail.chunks.length === 0" class="empty-state compact">
          <span class="material-icons">subject</span>
          <p>暂无分段内容</p>
        </div>

        <div v-else class="chunk-list">
          <article v-for="chunk in detail.chunks" :key="chunk.id" class="chunk-card">
            <div class="chunk-header">
              <strong>#{{ chunk.chunk_index + 1 }}</strong>
              <div>
                <button class="material-button text" @click="startEditChunk(chunk)">编辑</button>
                <button class="material-button text danger" @click="deleteChunk(chunk)">删除</button>
              </div>
            </div>

            <template v-if="editingChunkId === chunk.id">
              <textarea v-model="editingChunkText" class="chunk-editor"></textarea>
              <div class="chunk-actions">
                <button class="material-button outlined" @click="cancelEditChunk">取消</button>
                <button class="material-button filled" @click="saveChunk(chunk)">保存并重算向量</button>
              </div>
            </template>
            <p v-else class="chunk-text">{{ chunk.chunk_text }}</p>
          </article>
        </div>
      </aside>
    </div>

    <div v-if="duplicateDialog.open" class="modal-mask" @click.self="resolveDuplicateDialog('cancel')">
      <section class="confirm-dialog">
        <div class="dialog-icon">
          <span class="material-icons">difference</span>
        </div>
        <div>
          <p class="eyebrow">Duplicate Document</p>
          <h3>{{ duplicateDialog.title }}</h3>
          <p>{{ duplicateDialog.message }}</p>
          <div v-if="duplicateDialog.duplicates.length" class="duplicate-list">
            <span v-for="doc in duplicateDialog.duplicates.slice(0, 5)" :key="doc.id">{{ doc.filename }}</span>
          </div>
        </div>
        <div class="dialog-actions">
          <button class="material-button text" type="button" @click="resolveDuplicateDialog('cancel')">取消操作</button>
          <button class="material-button outlined" type="button" @click="resolveDuplicateDialog('keep_existing')">保留已有资料</button>
          <button class="material-button filled" type="button" @click="resolveDuplicateDialog('keep_current')">保留当前资料</button>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup>
import { computed, reactive, ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import knowledgeApi from '@/api/knowledge'

const router = useRouter()

const documents = ref([])
const collections = ref([])
const loading = ref(true)
const uploading = ref(false)
const addingUrls = ref(false)
const creatingCollection = ref(false)
const reindexing = ref(false)
const selectedFiles = ref([])
const acceptedFiles = ref([])
const rejectedFiles = ref([])
const urlQueue = ref([])
const fileInput = ref(null)
const uploadPublic = ref(false)
const uploadCollectionName = ref('')
const uploadQueue = ref([])
const urlPublic = ref(false)
const urlCollectionName = ref('')
const urlText = ref('')
const keyword = ref('')
const newCollectionName = ref('')
const now = ref(Date.now())
const collapsedCollectionIds = ref(new Set())
let clockTimer = null
const filters = reactive({ status: '', visibility: '' })
const notice = reactive({ type: 'success', message: '' })
const detail = reactive({ open: false, loading: false, document: null, title: '', chunks: [] })
const duplicateDialog = reactive({ open: false, title: '', message: '', duplicates: [], resolver: null })
const editingChunkId = ref('')
const editingChunkText = ref('')
const activeProgressWatchers = new Set()
const uploadPolicy = reactive({
  allowedExtensions: ['pdf', 'docx', 'txt', 'md', 'html', 'xlsx', 'png', 'jpg', 'jpeg', 'bmp', 'webp', 'tif', 'tiff'],
  maxFileSizeMb: 50,
  maxFileSizeBytes: 50 * 1024 * 1024,
  maxFilesPerBatch: 20
})
const fileAccept = computed(() => uploadPolicy.allowedExtensions.map(ext => `.${ext}`).join(','))
const uploadCompleted = computed(() => uploadQueue.value.length > 0 && uploadQueue.value.every(item => ['done', 'error'].includes(item.state)))
const uploadSteps = [
  { key: 'prepare', label: '准备' },
  { key: 'upload', label: '上传' },
  { key: 'saved', label: '入库' },
  { key: 'process', label: '处理' },
  { key: 'done', label: '完成' }
]
const urlSteps = [
  { key: 'prepare', label: '准备' },
  { key: 'saved', label: '入库' },
  { key: 'crawl', label: '抓取' },
  { key: 'process', label: '向量化' },
  { key: 'done', label: '完成' }
]
const PROCESS_POLL_INTERVAL_MS = 2000
const DOCUMENT_PROCESS_MAX_ATTEMPTS = 1800
const URL_PROCESS_MAX_ATTEMPTS = 450
const UPLOAD_RECOVERY_MAX_ATTEMPTS = 60
const loadUploadPolicy = async () => {
  try {
    const response = await knowledgeApi.getUploadPolicy()
    uploadPolicy.allowedExtensions = response.data.allowed_extensions || uploadPolicy.allowedExtensions
    uploadPolicy.maxFileSizeMb = response.data.max_file_size_mb || uploadPolicy.maxFileSizeMb
    uploadPolicy.maxFileSizeBytes = response.data.max_file_size_bytes || uploadPolicy.maxFileSizeBytes
    uploadPolicy.maxFilesPerBatch = response.data.max_files_per_batch || uploadPolicy.maxFilesPerBatch
  } catch (error) {
    console.warn('Failed to load upload policy:', error)
  }
}

const filteredDocuments = computed(() => {
  if (!keyword.value) return documents.value
  const term = keyword.value.toLowerCase()
  return documents.value.filter(doc => `${doc.filename} ${doc.file_path} ${doc.collection_name || ''}`.toLowerCase().includes(term))
})

const collectionGroups = computed(() => {
  const groups = collections.value.map(collection => ({
    id: collection.id,
    name: collection.name,
    documents: []
  }))
  const groupMap = new Map(groups.map(group => [group.id, group]))
  const unfiled = { id: 'unfiled', name: '未加入知识库', documents: [] }
  for (const doc of filteredDocuments.value) {
    const group = doc.collection_id ? groupMap.get(doc.collection_id) : null
    if (group) {
      group.documents.push(doc)
    } else {
      unfiled.documents.push(doc)
    }
  }
  return [unfiled, ...groups].filter(group => group.id === 'unfiled' || group.documents.length > 0 || !keyword.value)
})

const isCollectionCollapsed = (groupId) => collapsedCollectionIds.value.has(groupId)

const toggleCollectionGroup = (groupId) => {
  const next = new Set(collapsedCollectionIds.value)
  if (next.has(groupId)) {
    next.delete(groupId)
  } else {
    next.add(groupId)
  }
  collapsedCollectionIds.value = next
}

const showNotice = (message, type = 'success') => {
  notice.type = type
  notice.message = message
  window.clearTimeout(showNotice.timer)
  showNotice.timer = window.setTimeout(() => {
    notice.message = ''
  }, 3600)
}

const goHome = () => {
  router.push('/dashboard')
}

const fetchDocuments = async (showLoading = true) => {
  if (showLoading) loading.value = true
  try {
    const params = {}
    if (filters.status) params.status = filters.status
    if (filters.visibility) params.is_public = filters.visibility === 'public'
    const response = await knowledgeApi.listDocuments(params)
    documents.value = response.data.documents || []
    localStorage.setItem('knowledge_documents_cache', JSON.stringify(documents.value))
  } catch (error) {
    showNotice(error.response?.data?.detail || '加载知识库文档失败', 'error')
  } finally {
    if (showLoading) loading.value = false
  }
}

const fetchCollections = async () => {
  try {
    const response = await knowledgeApi.listCollections()
    collections.value = response.data.collections || []
  } catch (error) {
    showNotice(error.response?.data?.detail || '加载知识库列表失败', 'error')
  }
}

const createCollection = async () => {
  if (!newCollectionName.value) return
  creatingCollection.value = true
  try {
    await knowledgeApi.createCollection({ name: newCollectionName.value })
    showNotice('知识库已创建')
    newCollectionName.value = ''
    await fetchCollections()
  } catch (error) {
    showNotice(error.response?.data?.detail || '创建知识库失败', 'error')
  } finally {
    creatingCollection.value = false
  }
}

const renameCollection = async (group) => {
  const nextName = window.prompt('请输入新的知识库名称', group.name)
  if (nextName === null) return
  const cleanName = nextName.trim()
  if (!cleanName) {
    showNotice('知识库名称不能为空', 'error')
    return
  }
  if (cleanName === group.name) return
  if (collections.value.some(collection => collection.id !== group.id && collection.name === cleanName)) {
    showNotice('同名知识库已存在', 'error')
    return
  }
  try {
    await knowledgeApi.updateCollectionName(group.id, { name: cleanName })
    showNotice('知识库名称已更新')
    await Promise.all([fetchCollections(), fetchDocuments(false)])
  } catch (error) {
    showNotice(error.response?.data?.detail || '修改知识库名称失败', 'error')
  }
}

const deleteCollectionGroup = async (group) => {
  const firstConfirm = window.confirm(`确认删除知识库“${group.name}”？`)
  if (!firstConfirm) return
  const deleteDocuments = window.confirm(`是否同时删除知识库“${group.name}”中的 ${group.documents.length} 个资料？\n\n选择“确定”：删除知识库，并同时删除其中资料。\n选择“取消”：只删除知识库，资料移动到“未加入知识库”。`)
  if (!deleteDocuments) {
    const unfiledDocs = documents.value.filter(doc => !doc.collection_id)
    const duplicateDocs = group.documents.filter(doc => unfiledDocs.some(item => item.filename === doc.filename && item.file_type === doc.file_type))
    if (duplicateDocs.length > 0) {
      const examples = duplicateDocs.slice(0, 5).map(doc => `“${doc.filename}”`).join('、')
      const continueMove = window.confirm(`未加入知识库中已存在 ${duplicateDocs.length} 个同名资料：${examples}${duplicateDocs.length > 5 ? ' 等' : ''}。\n\n继续后这些资料会同时保留，列表中会出现同名条目。是否仍然只删除知识库并移动资料？`)
      if (!continueMove) return
    }
  }
  try {
    const response = await knowledgeApi.deleteCollection(group.id, { delete_documents: deleteDocuments })
    collapsedCollectionIds.value = new Set([...collapsedCollectionIds.value].filter(id => id !== group.id))
    showNotice(response.data.message || '知识库已删除')
    await Promise.all([fetchCollections(), fetchDocuments(false)])
  } catch (error) {
    showNotice(error.response?.data?.detail || '删除知识库失败', 'error')
  }
}

const collectionNameForId = (collectionId) => {
  if (collectionId?.startsWith?.('__new__:')) return collectionId.slice('__new__:'.length)
  if (!collectionId) return '未加入知识库'
  return collections.value.find(collection => collection.id === collectionId)?.name || '目标知识库'
}

const collectionIdByName = (name) => {
  const cleanName = (name || '').trim()
  if (!cleanName) return ''
  return collections.value.find(collection => collection.name === cleanName)?.id || `__new__:${cleanName}`
}

const fileTypeFromName = (name) => name.includes('.') ? name.split('.').pop().toLowerCase() : ''

const duplicateDocumentsForPlacement = (filename, fileType, collectionId, excludeId = '') => {
  if (collectionId?.startsWith?.('__new__:')) return []
  return documents.value.filter(doc => {
    const sameCollection = (doc.collection_id || '') === (collectionId || '')
    return sameCollection && doc.id !== excludeId && doc.filename === filename && doc.file_type === fileType
  })
}

const askDuplicateResolution = ({ title, message, duplicates }) => {
  duplicateDialog.open = true
  duplicateDialog.title = title
  duplicateDialog.message = message
  duplicateDialog.duplicates = duplicates
  return new Promise(resolve => {
    duplicateDialog.resolver = resolve
  })
}

const resolveDuplicateDialog = (action) => {
  duplicateDialog.open = false
  const resolver = duplicateDialog.resolver
  duplicateDialog.resolver = null
  duplicateDialog.title = ''
  duplicateDialog.message = ''
  duplicateDialog.duplicates = []
  if (resolver) resolver(action)
}

const deleteDuplicateDocuments = async (duplicates) => {
  for (const duplicate of duplicates) {
    await knowledgeApi.deleteDocument(duplicate.id)
  }
}

const resolveDuplicateBeforePlacement = async ({ filename, fileType, collectionId, excludeId = '', currentDocumentId = '', currentDocumentLabel = '当前资料' }) => {
  const duplicates = duplicateDocumentsForPlacement(filename, fileType, collectionId, excludeId)
  if (duplicates.length === 0) return 'continue'
  const action = await askDuplicateResolution({
    title: '发现同名资料',
    message: `“${collectionNameForId(collectionId)}”中已存在 ${duplicates.length} 个同名同类型资料“${filename}”。请选择保留哪一份。`,
    duplicates,
  })
  if (action === 'keep_current') {
    await deleteDuplicateDocuments(duplicates)
    return 'continue'
  }
  if (action === 'keep_existing') {
    if (currentDocumentId) {
      await knowledgeApi.deleteDocument(currentDocumentId)
      showNotice(`已保留已有资料，并删除${currentDocumentLabel}`)
      await fetchDocuments(false)
      return 'deleted_current'
    }
    return 'stop'
  }
  return 'stop'
}

const handleFileChange = (event) => {
  const files = Array.from(event.target.files || [])
  if (uploading.value) {
    rejectedFiles.value = [{ name: '上传列表已锁定', reason: '上传和处理过程中不允许继续增删文件。' }]
    if (fileInput.value) fileInput.value.value = ''
    return
  }
  rejectedFiles.value = []
  if (files.length > uploadPolicy.maxFilesPerBatch) {
    rejectedFiles.value.push({ name: '批量选择', reason: `单次最多选择 ${uploadPolicy.maxFilesPerBatch} 个文件` })
  }
  const accepted = [...selectedFiles.value]
  const existingKeys = new Set(selectedFiles.value.map(file => `${file.name}-${file.size}-${file.lastModified}`))
  for (const file of files.slice(0, uploadPolicy.maxFilesPerBatch)) {
    if (accepted.length >= uploadPolicy.maxFilesPerBatch) {
      rejectedFiles.value.push({ name: file.name, reason: `已达到单次最多 ${uploadPolicy.maxFilesPerBatch} 个文件` })
      continue
    }
    const key = `${file.name}-${file.size}-${file.lastModified}`
    if (existingKeys.has(key)) {
      rejectedFiles.value.push({ name: file.name, reason: '该文件已在待上传列表中' })
      continue
    }
    const ext = file.name.includes('.') ? file.name.split('.').pop().toLowerCase() : ''
    if (!uploadPolicy.allowedExtensions.includes(ext)) {
      rejectedFiles.value.push({ name: file.name, reason: `文件类型不支持，仅支持 ${uploadPolicy.allowedExtensions.join(', ')}` })
      continue
    }
    if (file.size > uploadPolicy.maxFileSizeBytes) {
      rejectedFiles.value.push({ name: file.name, reason: `文件超过 ${uploadPolicy.maxFileSizeMb}MB，当前 ${formatFileSize(file.size)}` })
      continue
    }
    accepted.push(file)
  }
  selectedFiles.value = accepted
  acceptedFiles.value = selectedFiles.value.map(file => ({ name: file.name, size: file.size }))
  uploadQueue.value = selectedFiles.value.map((file, index) => ({
    id: `${file.name}-${file.size}-${index}`,
    file,
    name: file.name,
    size: file.size,
    state: 'waiting',
    progress: 0,
    documentId: '',
    failedStep: '',
    startedAt: null,
    completedAt: null,
    cancelled: false,
    abortController: null,
    message: '等待开始上传'
  }))
  if (fileInput.value) fileInput.value.value = ''
}

const removeFileSelection = (item) => {
  if (!item.file) return
  selectedFiles.value = selectedFiles.value.filter(file => file !== item.file)
  acceptedFiles.value = selectedFiles.value.map(file => ({ name: file.name, size: file.size }))
}

const removeUploadQueueItem = async (item) => {
  item.cancelled = true
  item.abortController?.abort()
  activeProgressWatchers.delete(item.documentId)
  uploadQueue.value = uploadQueue.value.filter(queueItem => queueItem.id !== item.id)
  removeFileSelection(item)
  rejectedFiles.value = []
  if (fileInput.value) fileInput.value.value = ''
  if (item.documentId) {
    try {
      await knowledgeApi.deleteDocument(item.documentId)
      await fetchDocuments(false)
      showNotice('已从上传列表移除并删除文档记录')
    } catch (error) {
      showNotice(error.response?.data?.detail || '已移除列表项，但删除文档记录失败', 'error')
    }
  }
}

const uploadDocument = async () => {
  if (selectedFiles.value.length === 0) return
  if (selectedFiles.value.length > 20) {
    showNotice('单次最多上传 20 个文件', 'error')
    return
  }
  const targetCollectionId = collectionIdByName(uploadCollectionName.value)
  for (const file of selectedFiles.value) {
    const result = await resolveDuplicateBeforePlacement({
      filename: file.name,
      fileType: fileTypeFromName(file.name),
      collectionId: targetCollectionId,
      currentDocumentLabel: `待上传资料“${file.name}”`,
    })
    if (result !== 'continue') return
  }
  uploading.value = true
  try {
    for (const item of [...uploadQueue.value]) {
      if (item.cancelled || !uploadQueue.value.some(queueItem => queueItem.id === item.id)) continue
      await uploadSingleFile(item)
    }
    const failedCount = uploadQueue.value.filter(item => item.state === 'error').length
    showNotice(failedCount ? `${failedCount} 个文件上传失败，其余文件已提交处理` : `${uploadQueue.value.length} 个文档已提交处理`)
    uploadPublic.value = false
    uploadCollectionName.value = ''
    if (fileInput.value) fileInput.value.value = ''
    await fetchCollections()
    await fetchDocuments()
    window.setTimeout(fetchDocuments, 2500)
  } catch (error) {
    showNotice(error.response?.data?.detail || '上传文档失败', 'error')
  } finally {
    uploading.value = false
  }
}

const uploadSingleFile = async (item) => {
  if (item.cancelled) return
  item.state = 'uploading'
  item.progress = 10
  item.startedAt = item.startedAt || Date.now()
  item.message = '正在上传文件到服务器'
  try {
    const formData = new FormData()
    formData.append('file', item.file)
    formData.append('is_public', String(uploadPublic.value))
    formData.append('collection_name', uploadCollectionName.value || '')
    item.abortController = new AbortController()
    const response = await knowledgeApi.uploadDocument(formData, {
      timeout: 0,
      signal: item.abortController.signal,
      onUploadProgress: (event) => {
        if (item.cancelled) return
        if (!event.total) return
        const uploadPart = Math.round((event.loaded / event.total) * 45)
        item.progress = Math.max(item.progress, Math.min(55, 10 + uploadPart))
        if (event.loaded >= event.total) {
          item.progress = Math.max(item.progress, 58)
          item.message = '文件已发送，等待服务器登记并进入后台处理队列'
        }
      }
    })
    if (item.cancelled) {
      if (response.data?.id) await knowledgeApi.deleteDocument(response.data.id).catch(() => {})
      return
    }
    item.state = 'saved'
    item.progress = 65
    item.documentId = response.data.id
    item.message = '文件已入库，等待后台处理'
    await waitDocumentReady(item)
  } catch (error) {
    if (item.cancelled || error.code === 'ERR_CANCELED') return
    if (error.code === 'ECONNABORTED') {
      await recoverTimedOutUpload(item)
      return
    }
    item.state = 'error'
    item.failedStep = 'upload'
    item.progress = 100
    item.completedAt = Date.now()
    item.message = friendlyUploadError(error, item)
  }
}

const recoverTimedOutUpload = async (item) => {
  if (item.cancelled) return
  item.state = 'processing'
  item.failedStep = ''
  item.progress = 62
  item.message = '大文件已发送，服务器可能仍在登记或处理，正在尝试同步处理进度'
  for (let attempt = 0; attempt < UPLOAD_RECOVERY_MAX_ATTEMPTS; attempt++) {
    if (item.cancelled) return
    await new Promise(resolve => window.setTimeout(resolve, PROCESS_POLL_INTERVAL_MS))
    const doc = await findLatestDocumentByName(item.name)
    if (doc) {
      item.documentId = doc.id
      item.message = doc.status === 'processing' ? '文件已入库，后台正在解析和向量化' : '已找回文件处理记录，正在同步状态'
      await waitDocumentReady(item)
      return
    }
    item.progress = Math.min(76, item.progress + 2)
  }
  item.state = 'error'
  item.failedStep = 'upload'
  item.progress = 100
  item.completedAt = Date.now()
  item.message = '暂未在文档列表中找到该文件。大文件可能仍在上传登记中，请稍后刷新文档列表确认是否已入库。'
}

const waitDocumentReady = async (item) => {
  if (item.cancelled) return
  item.state = 'processing'
  item.progress = Math.max(item.progress, 78)
  item.startedAt = item.startedAt || Date.now()
  item.message = item.message || '正在解析文本、分词分块并生成向量'
  activeProgressWatchers.add(item.documentId)
  for (let attempt = 0; attempt < DOCUMENT_PROCESS_MAX_ATTEMPTS; attempt++) {
    if (item.cancelled) return
    await new Promise(resolve => window.setTimeout(resolve, PROCESS_POLL_INTERVAL_MS))
    const doc = await findDocumentForProgress(item.documentId)
    syncProgressFromDocument(item, doc)
    if (doc?.status === 'ready') {
      item.state = 'done'
      item.progress = 100
      item.completedAt = Date.now()
      item.message = '处理完成，已写入知识库向量分段'
      await fetchDocuments(false)
      activeProgressWatchers.delete(item.documentId)
      removeCompletedUploadItem(item)
      return
    }
    if (doc?.status === 'error') {
      item.state = 'error'
      item.failedStep = 'process'
      item.progress = 100
      item.completedAt = Date.now()
      item.message = doc.error_message || '后台处理失败'
      await fetchDocuments(false)
      activeProgressWatchers.delete(item.documentId)
      return
    }
    item.progress = Math.min(96, item.progress + 1)
  }
  item.state = 'error'
  item.failedStep = 'process'
  item.progress = 100
  item.completedAt = Date.now()
  item.message = '文件过大，处理超时。请拆分 PDF、降低图片页数量或稍后重试。'
  activeProgressWatchers.delete(item.documentId)
}

const removeCompletedUploadItem = (item) => {
  window.setTimeout(() => {
    if (item.cancelled) return
    uploadQueue.value = uploadQueue.value.filter(queueItem => queueItem.id !== item.id)
    removeFileSelection(item)
  }, 1200)
}

const removeCompletedUrlItem = (item) => {
  window.setTimeout(() => {
    if (item.cancelled) return
    urlQueue.value = urlQueue.value.filter(queueItem => queueItem.id !== item.id)
  }, 1200)
}

const removeUrlQueueItem = async (item) => {
  item.cancelled = true
  activeProgressWatchers.delete(item.documentId)
  urlQueue.value = urlQueue.value.filter(queueItem => queueItem.id !== item.id)
  if (item.documentId) {
    try {
      await knowledgeApi.deleteDocument(item.documentId)
      await fetchDocuments(false)
      showNotice('已从网页抓取列表移除并删除文档记录')
    } catch (error) {
      showNotice(error.response?.data?.detail || '已移除列表项，但删除文档记录失败', 'error')
    }
  }
}

const syncProgressFromDocument = (item, doc) => {
  const progress = doc?.processing_progress
  if (!progress) return
  if (typeof progress.percent === 'number') {
    item.progress = Math.max(item.progress, Math.min(96, progress.percent))
  }
  if (progress.page && progress.total_pages) {
    item.message = `${progress.message}（第 ${progress.page}/${progress.total_pages} 页）`
  } else if (progress.message) {
    item.message = progress.message
  }
}

const findDocumentForProgress = async (documentId) => {
  if (!documentId) return null
  const response = await knowledgeApi.listDocuments({ limit: 200 })
  return (response.data.documents || []).find(document => document.id === documentId) || null
}

const findLatestDocumentByName = async (filename) => {
  const response = await knowledgeApi.listDocuments({ limit: 200 })
  return (response.data.documents || []).find(document => document.filename === filename) || null
}

const uploadStateText = (item) => {
  switch (item.state) {
    case 'waiting': return '等待上传'
    case 'uploading': return '上传文件'
    case 'saved': return '已入库'
    case 'processing': return '后台处理'
    case 'done': return '完成'
    case 'error': return '失败'
    default: return item.state
  }
}

const stepRank = (state) => {
  switch (state) {
    case 'waiting': return 0
    case 'uploading': return 1
    case 'saved': return 2
    case 'processing': return 3
    case 'done': return 4
    case 'error': return 4
    default: return 0
  }
}

const stepClass = (item, key) => {
  return stepClassForSteps(item, key, uploadSteps)
}

const stepClassForSteps = (item, key, steps) => {
  const index = steps.findIndex(step => step.key === key)
  if (item.state === 'error') {
    const failedIndex = steps.findIndex(step => step.key === item.failedStep)
    if (index < failedIndex) return 'done'
    if (index === failedIndex) return 'error'
    return ''
  }
  if (index < stepRank(item.state)) return 'done'
  if (index === stepRank(item.state)) return 'active'
  return ''
}

const stepIcon = (item, key) => {
  return stepIconForSteps(item, key, uploadSteps)
}

const stepIconForSteps = (item, key, steps) => {
  const cls = stepClassForSteps(item, key, steps)
  if (cls === 'error') return 'close'
  if (cls === 'done') return 'check'
  if (cls === 'active') return key === 'process' ? 'settings' : 'hourglass_top'
  return 'radio_button_unchecked'
}

const friendlyUploadError = (error, item) => {
  if (error.response?.status === 413) {
    return `服务器拒绝了本次上传请求：${item.name} 当前 ${formatFileSize(item.size)}，页面策略允许最大 ${uploadPolicy.maxFileSizeMb}MB。这通常表示后端、Nginx 或代理的请求体限制没有同步，或服务修改后未重启。`
  }
  if (error.response?.status === 401) {
    return '登录状态已过期，请重新登录后再上传。'
  }
  if (error.response?.status === 403) {
    return '当前账号没有上传权限，请确认已登录。'
  }
  if (error.response?.data?.detail) {
    return error.response.data.detail
  }
  if (error.code === 'ECONNABORTED') {
    return '大文件上传等待超时，正在尝试从文档列表同步后台处理进度。'
  }
  if (!error.response) {
    return '没有收到服务器响应。请确认后端服务已启动，或检查 Nginx/代理的上传大小限制。'
  }
  return `上传失败，服务器返回 ${error.response.status}。请查看后端日志确认具体原因。`
}

const addUrls = async () => {
  const urls = urlText.value.split('\n').map(url => url.trim()).filter(Boolean)
  if (urls.length === 0) return
  const targetCollectionId = collectionIdByName(urlCollectionName.value)
  for (const url of urls) {
    const result = await resolveDuplicateBeforePlacement({
      filename: url,
      fileType: 'url',
      collectionId: targetCollectionId,
      currentDocumentLabel: `待抓取网页“${url}”`,
    })
    if (result !== 'continue') return
  }
  addingUrls.value = true
  urlQueue.value = urls.map((url, index) => ({
    id: `${url}-${index}`,
    name: url,
    state: 'waiting',
      progress: 0,
      documentId: '',
      failedStep: '',
      startedAt: null,
      completedAt: null,
      cancelled: false,
      message: '等待提交网页来源'
    }))
  const submittedItems = [...urlQueue.value]
  try {
    const response = await knowledgeApi.addUrls({ urls, is_public: urlPublic.value, collection_name: urlCollectionName.value || null })
    const docs = response.data || []
    submittedItems.forEach((item, index) => {
      const documentId = docs[index]?.id || ''
      if (item.cancelled) {
        if (documentId) knowledgeApi.deleteDocument(documentId).catch(() => {})
        return
      }
      item.state = 'saved'
      item.progress = 35
      item.documentId = documentId
      item.startedAt = item.startedAt || Date.now()
      item.message = '网页来源已入库，等待抓取正文'
    })
    showNotice('网页来源已入库，后台正在抓取和向量化')
    urlText.value = ''
    urlPublic.value = false
    urlCollectionName.value = ''
    await fetchCollections()
    await fetchDocuments()
    await Promise.all(submittedItems.map(item => item.cancelled ? Promise.resolve() : waitUrlReady(item)))
  } catch (error) {
    urlQueue.value.forEach(item => {
      item.state = 'error'
      item.failedStep = 'saved'
      item.progress = 100
      item.completedAt = Date.now()
      item.message = error.response?.data?.detail || '提交网页来源失败'
    })
    showNotice(error.response?.data?.detail || '添加网页来源失败', 'error')
  } finally {
    addingUrls.value = false
  }
}

const waitUrlReady = async (item) => {
  if (item.cancelled) return
  if (!item.documentId) return
  item.state = 'processing'
  item.progress = Math.max(item.progress, 55)
  item.startedAt = item.startedAt || Date.now()
  item.message = item.message || '正在抓取网页正文并准备分块'
  activeProgressWatchers.add(item.documentId)
  for (let attempt = 0; attempt < URL_PROCESS_MAX_ATTEMPTS; attempt++) {
    if (item.cancelled) return
    await new Promise(resolve => window.setTimeout(resolve, PROCESS_POLL_INTERVAL_MS))
    const doc = await findDocumentForProgress(item.documentId)
    syncProgressFromDocument(item, doc)
    if (doc?.status === 'ready') {
      item.state = 'done'
      item.progress = 100
      item.completedAt = Date.now()
      item.message = '网页内容已写入知识库向量分段'
      await fetchDocuments(false)
      activeProgressWatchers.delete(item.documentId)
      removeCompletedUrlItem(item)
      return
    }
    if (doc?.status === 'error') {
      item.state = 'error'
      item.failedStep = 'process'
      item.progress = 100
      item.completedAt = Date.now()
      item.message = doc.error_message || '网页抓取或向量化失败'
      await fetchDocuments(false)
      activeProgressWatchers.delete(item.documentId)
      return
    }
    item.progress = Math.min(96, item.progress + 2)
    item.message = item.progress < 72 ? '正在抓取网页正文' : '正在分词、分块并生成向量'
  }
  item.state = 'error'
  item.failedStep = 'process'
  item.progress = 100
  item.completedAt = Date.now()
  item.message = '网页内容过大或抓取耗时过长，处理超时。请拆分网页来源或稍后重试。'
  activeProgressWatchers.delete(item.documentId)
}

const restoreProcessingQueues = () => {
  const processingDocs = documents.value.filter(doc => doc.status === 'processing')
  for (const doc of processingDocs) {
    const progress = doc.processing_progress || {}
    const item = {
      id: `restore-${doc.id}`,
      name: doc.filename,
      size: doc.file_size,
      state: 'processing',
      progress: typeof progress.percent === 'number' ? Math.max(20, Math.min(96, progress.percent)) : 35,
      documentId: doc.id,
      failedStep: '',
      startedAt: doc.created_at ? new Date(doc.created_at).getTime() : Date.now(),
      completedAt: null,
      cancelled: false,
      message: progress.message || '后台正在处理，已从文档状态恢复进度'
    }
    if (progress.page && progress.total_pages) {
      item.message = `${progress.message}（第 ${progress.page}/${progress.total_pages} 页）`
    }
    if (doc.file_type === 'url') {
      if (!urlQueue.value.some(queueItem => queueItem.documentId === doc.id)) {
        urlQueue.value.unshift(item)
      }
      if (!activeProgressWatchers.has(doc.id)) waitUrlReady(item)
    } else {
      if (!uploadQueue.value.some(queueItem => queueItem.documentId === doc.id)) {
        uploadQueue.value.unshift(item)
      }
      if (!activeProgressWatchers.has(doc.id)) waitDocumentReady(item)
    }
  }
}

const urlStateText = (item) => {
  switch (item.state) {
    case 'waiting': return '等待提交'
    case 'saved': return '已入库'
    case 'processing': return '抓取处理中'
    case 'done': return '完成'
    case 'error': return '失败'
    default: return item.state
  }
}

const urlStepClass = (item, key) => stepClassForSteps(item, key, urlSteps)
const urlStepIcon = (item, key) => stepIconForSteps(item, key, urlSteps)

const toggleVisibility = async (doc) => {
  try {
    await knowledgeApi.updateVisibility(doc.id, !doc.is_public)
    showNotice(`已设为${doc.is_public ? '私有' : '公共'}文档`)
    await fetchDocuments()
  } catch (error) {
    showNotice(error.response?.data?.detail || '更新可见性失败', 'error')
  }
}

const setDocumentCollection = async (doc, collectionId) => {
  try {
    const duplicateResult = await resolveDuplicateBeforePlacement({
      filename: doc.filename,
      fileType: doc.file_type,
      collectionId: collectionId || '',
      excludeId: doc.id,
      currentDocumentId: doc.id,
      currentDocumentLabel: `当前资料“${doc.filename}”`,
    })
    if (duplicateResult === 'stop') {
      await fetchDocuments(false)
      return
    }
    if (duplicateResult === 'deleted_current') return
    await knowledgeApi.updateCollection(doc.id, { collection_id: collectionId || null })
    showNotice(collectionId ? '已更新文档所属知识库' : '已从知识库中移出')
    await Promise.all([fetchCollections(), fetchDocuments(false)])
  } catch (error) {
    showNotice(error.response?.data?.detail || '更新所属知识库失败', 'error')
    await fetchDocuments(false)
  }
}

const retryDocument = async (doc) => {
  try {
    const retryItem = {
      id: `retry-${doc.id}-${Date.now()}`,
      name: doc.filename,
      size: 0,
      state: 'processing',
      progress: 35,
      documentId: doc.id,
      failedStep: '',
      startedAt: Date.now(),
      completedAt: null,
      cancelled: false,
      message: '已从失败列表移回处理队列，正在重新解析并向量化'
    }
    uploadQueue.value = [retryItem, ...uploadQueue.value.filter(item => item.documentId !== doc.id)]
    documents.value = documents.value.filter(item => item.id !== doc.id)
    await knowledgeApi.retryDocument(doc.id)
    showNotice('已重新提交处理，进度已显示在上传列表')
    await fetchDocuments(false)
    await waitDocumentReady(retryItem)
  } catch (error) {
    showNotice(error.response?.data?.detail || '重新处理失败', 'error')
  }
}

const reindexAllDocuments = async () => {
  if (!window.confirm('重新索引会按当前默认嵌入模型重建全部文档向量。切换嵌入模型后建议执行，是否继续？')) return
  reindexing.value = true
  try {
    const response = await knowledgeApi.reindexAllDocuments()
    showNotice(response.data.message || '已提交重新索引任务')
    await fetchDocuments(false)
  } catch (error) {
    showNotice(error.response?.data?.detail || '提交重新索引任务失败', 'error')
  } finally {
    reindexing.value = false
  }
}

const deleteDocument = async (doc) => {
  if (!window.confirm(`确认删除“${doc.filename}”？`)) return
  try {
    await knowledgeApi.deleteDocument(doc.id)
    showNotice('文档已删除')
    await fetchDocuments()
  } catch (error) {
    showNotice(error.response?.data?.detail || '删除文档失败', 'error')
  }
}

const openDetail = async (doc) => {
  detail.open = true
  detail.document = doc
  detail.title = doc.filename
  editingChunkId.value = ''
  editingChunkText.value = ''
  await fetchChunks()
}

const closeDetail = () => {
  detail.open = false
  detail.loading = false
  detail.document = null
  detail.title = ''
  detail.chunks = []
  editingChunkId.value = ''
  editingChunkText.value = ''
}

const fetchChunks = async () => {
  if (!detail.document) return
  detail.loading = true
  try {
    const response = await knowledgeApi.listChunks(detail.document.id)
    detail.chunks = response.data.chunks || []
  } catch (error) {
    showNotice(error.response?.data?.detail || '加载分段失败', 'error')
  } finally {
    detail.loading = false
  }
}

const saveTitle = async () => {
  if (!detail.document || !detail.title) return
  try {
    const cleanTitle = detail.title.trim()
    const duplicateResult = await resolveDuplicateBeforePlacement({
      filename: cleanTitle,
      fileType: detail.document.file_type,
      collectionId: detail.document.collection_id || '',
      excludeId: detail.document.id,
      currentDocumentId: detail.document.id,
      currentDocumentLabel: `当前资料“${detail.document.filename}”`,
    })
    if (duplicateResult === 'stop') return
    if (duplicateResult === 'deleted_current') {
      closeDetail()
      return
    }
    const response = await knowledgeApi.updateTitle(detail.document.id, cleanTitle)
    detail.document.filename = response.data.filename
    showNotice('文档标题已更新')
    await fetchDocuments()
  } catch (error) {
    showNotice(error.response?.data?.detail || '更新标题失败', 'error')
  }
}

const startEditChunk = (chunk) => {
  editingChunkId.value = chunk.id
  editingChunkText.value = chunk.chunk_text
}

const cancelEditChunk = () => {
  editingChunkId.value = ''
  editingChunkText.value = ''
}

const saveChunk = async (chunk) => {
  if (!editingChunkText.value.trim()) {
    showNotice('分段内容不能为空', 'error')
    return
  }
  try {
    await knowledgeApi.updateChunk(chunk.id, editingChunkText.value)
    showNotice('分段已更新，并已重新生成向量')
    cancelEditChunk()
    await fetchChunks()
  } catch (error) {
    showNotice(error.response?.data?.detail || '保存分段失败', 'error')
  }
}

const deleteChunk = async (chunk) => {
  if (!window.confirm(`确认删除第 ${chunk.chunk_index + 1} 个分段？`)) return
  try {
    await knowledgeApi.deleteChunk(chunk.id)
    showNotice('分段已删除')
    await fetchChunks()
  } catch (error) {
    showNotice(error.response?.data?.detail || '删除分段失败', 'error')
  }
}

const statusText = (status) => {
  switch (status) {
    case 'processing': return '处理中'
    case 'ready': return '就绪'
    case 'error': return '失败'
    default: return status || '未知'
  }
}

const fileIcon = (type) => type === 'url' ? 'link' : type === 'pdf' ? 'picture_as_pdf' : ['png', 'jpg', 'jpeg', 'bmp', 'webp', 'tif', 'tiff'].includes(type) ? 'image' : 'description'
const formatTime = (time) => time ? new Date(time).toLocaleString('zh-CN') : '-'
const formatFileSize = (size) => typeof size === 'number' && size > 0 ? `${(size / 1024 / 1024).toFixed(1)}MB` : '未知大小'
const elapsedTime = (item) => {
  if (!item.startedAt) return '0秒'
  const endTime = item.completedAt || now.value
  const seconds = Math.max(0, Math.floor((endTime - item.startedAt) / 1000))
  const minutes = Math.floor(seconds / 60)
  const hours = Math.floor(minutes / 60)
  const remainMinutes = minutes % 60
  const remainSeconds = seconds % 60
  if (hours > 0) return `${hours}小时${remainMinutes}分${remainSeconds}秒`
  if (minutes > 0) return `${minutes}分${remainSeconds}秒`
  return `${remainSeconds}秒`
}

onMounted(async () => {
  clockTimer = window.setInterval(() => {
    now.value = Date.now()
  }, 1000)
  const cached = localStorage.getItem('knowledge_documents_cache')
  if (cached) {
    try {
      documents.value = JSON.parse(cached)
      loading.value = false
    } catch (error) {
      localStorage.removeItem('knowledge_documents_cache')
    }
  }
  await loadUploadPolicy()
  await Promise.all([fetchCollections(), fetchDocuments()])
  restoreProcessingQueues()
})

onUnmounted(() => {
  if (clockTimer) window.clearInterval(clockTimer)
})
</script>

<style scoped lang="scss">
.knowledge-page { width: 100%; max-width: none; }
.page-header, .card-header, .switch-row, .notice, .row-actions { display: flex; align-items: center; }
.page-actions { display: flex; gap: $spacing-sm; align-items: center; }
.page-header { justify-content: space-between; gap: $spacing-lg; margin-bottom: $spacing-md; }
.page-header h2 { font-size: 28px; color: $on-surface; margin-bottom: $spacing-xs; }
.page-header p, .card-header p { color: $on-surface-variant; }
.eyebrow { color: $primary-color; font-size: 12px; letter-spacing: 0.14em; text-transform: uppercase; margin-bottom: $spacing-xs; }
.notice { gap: $spacing-sm; padding: 12px 16px; border-radius: $radius-large; background: #dff7e8; color: #146c2e; margin-bottom: $spacing-md; }
.notice.error { background: $error-container; color: $error; }
.action-grid { display: grid; grid-template-columns: minmax(480px, 1.15fr) minmax(380px, 0.85fr); gap: $spacing-lg; margin-bottom: $spacing-lg; }
.panel-card, .collection-create-card, .filter-card, .table-card { background: $surface; border-radius: $radius-large; box-shadow: $shadow-1; }
.panel-card { padding: $spacing-lg; }
.card-header { justify-content: space-between; gap: $spacing-md; margin-bottom: $spacing-md; }
.card-header h3 { color: $on-surface; font-size: 18px; }
.card-header > .material-icons { color: $primary-color; font-size: 32px; }
.file-drop { display: grid; place-items: center; gap: $spacing-sm; min-height: 180px; border: 1px dashed $outline; border-radius: $radius-medium; color: $on-surface-variant; cursor: pointer; margin-bottom: $spacing-sm; }
.file-drop:hover { background: rgba($primary-color, 0.06); border-color: $primary-color; }
.file-drop.disabled { cursor: not-allowed; background: rgba($surface-variant, 0.35); border-style: solid; }
.file-drop input { display: none; }
.file-drop .material-icons { color: $primary-color; font-size: 40px; }
.upload-rules { display: flex; flex-wrap: wrap; gap: $spacing-xs; margin-bottom: $spacing-md; color: $on-surface-variant; font-size: 12px; }
.upload-rules span { padding: 4px 8px; border: 1px solid $outline-variant; border-radius: $radius-small; }
.archive-field { display: flex; flex-direction: column; gap: $spacing-xs; margin-bottom: $spacing-md; color: $on-surface-variant; font-size: 13px; }
.archive-field input { height: 42px; border: 1px solid $outline; border-radius: $radius-small; padding: 0 12px; background: transparent; color: $on-surface; }
.selected-files { display: flex; flex-wrap: wrap; gap: $spacing-xs; margin: -4px 0 $spacing-md; }
.selected-files span { max-width: 220px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; padding: 4px 8px; border-radius: $radius-small; background: rgba($primary-color, 0.08); color: $on-surface-variant; font-size: 12px; }
.accepted-files { padding: 10px 12px; border-radius: $radius-medium; background: #dff7e8; color: #146c2e; margin-bottom: $spacing-md; font-size: 13px; }
.accepted-files strong { display: block; margin-bottom: 4px; }
.accepted-files p { margin: 2px 0; }
.rejected-files { padding: 10px 12px; border-radius: $radius-medium; background: $error-container; color: $error; margin-bottom: $spacing-md; font-size: 13px; }
.rejected-files strong { display: block; margin-bottom: 4px; }
.rejected-files p { margin: 2px 0; }
.upload-queue { display: grid; gap: $spacing-sm; margin-bottom: $spacing-md; }
.url-queue { margin-top: $spacing-md; }
.queue-header { display: flex; justify-content: space-between; align-items: center; gap: $spacing-md; color: $on-surface; }
.upload-item { border: 1px solid $outline-variant; border-radius: $radius-medium; padding: 12px; background: rgba($surface-variant, 0.22); }
.upload-title { display: grid; grid-template-columns: minmax(0, 1fr) auto auto auto; gap: $spacing-sm; align-items: center; margin-bottom: $spacing-sm; }
.upload-title strong { max-width: 320px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: $on-surface; }
.upload-title small { color: $outline; }
.queue-remove { display: grid; place-items: center; width: 28px; height: 28px; border: 1px solid $outline-variant; border-radius: $radius-small; background: $surface; color: $error; cursor: pointer; }
.queue-remove .material-icons { font-size: 18px; }
.queue-remove:hover { background: $error-container; }
.upload-state { padding: 3px 8px; border-radius: $radius-small; background: $secondary-container; color: $on-secondary-container; font-size: 12px; font-weight: 600; }
.upload-state.done { background: #dff7e8; color: #146c2e; }
.upload-state.error { background: $error-container; color: $error; }
.step-track { display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: $spacing-xs; margin-bottom: $spacing-sm; }
.step-dot { display: grid; gap: 2px; justify-items: center; color: $outline; font-size: 11px; }
.step-dot .material-icons { width: 22px; height: 22px; display: grid; place-items: center; border-radius: $radius-small; border: 1px solid $outline-variant; font-size: 15px; background: $surface; }
.step-dot.done, .step-dot.active { color: $primary-color; }
.step-dot.done .material-icons { background: $primary-container; border-color: $primary-container; }
.step-dot.active .material-icons { border-color: $primary-color; }
.step-dot.error { color: $error; }
.step-dot.error .material-icons { background: $error-container; border-color: $error-container; }
.progress-line { height: 4px; border-radius: $radius-small; background: $outline-variant; overflow: hidden; }
.progress-line span { display: block; height: 100%; background: $primary-color; transition: width 0.25s ease; }
.upload-item small { display: block; margin-top: $spacing-xs; color: $on-surface-variant; }
.elapsed-time { color: $primary-color !important; }
textarea { width: 100%; min-height: 150px; resize: vertical; border: 1px solid $outline; border-radius: $radius-large; padding: 12px; background: transparent; color: $on-surface; margin-bottom: $spacing-md; }
.switch-row { gap: $spacing-sm; color: $on-surface-variant; margin-bottom: $spacing-md; }
.switch-row input { width: 18px; height: 18px; }
.collection-create-card { display: grid; grid-template-columns: minmax(260px, 1fr) minmax(360px, 0.9fr); gap: $spacing-lg; align-items: center; padding: $spacing-lg; margin-bottom: $spacing-lg; }
.collection-create-card h3 { color: $on-surface; font-size: 20px; margin-bottom: $spacing-xs; }
.collection-create-card p:not(.eyebrow) { color: $on-surface-variant; }
.filter-card { display: grid; grid-template-columns: 180px 180px minmax(260px, 1fr); gap: $spacing-md; padding: $spacing-lg; margin-bottom: $spacing-lg; }
.filter-card label { display: flex; flex-direction: column; gap: $spacing-xs; color: $on-surface-variant; font-size: 13px; }
.filter-card select, .filter-card input { height: 44px; border: 1px solid $outline; border-radius: $radius-small; padding: 0 12px; background: transparent; color: $on-surface; }
.create-collection { display: grid; grid-template-columns: 1fr auto; gap: $spacing-sm; align-items: center; }
.create-collection input { height: 46px; border: 1px solid $outline; border-radius: $radius-small; padding: 0 12px; background: transparent; color: $on-surface; }
.table-card { min-height: 420px; overflow: hidden; }
.loading-state, .empty-state { display: grid; place-items: center; gap: $spacing-md; min-height: 420px; color: $on-surface-variant; }
.compact { min-height: 180px; }
.empty-state .material-icons { font-size: 48px; color: $outline; }
.collection-tree { display: grid; gap: $spacing-md; padding: $spacing-md; }
.collection-group { border: 1px solid $outline-variant; border-radius: $radius-large; overflow: hidden; background: rgba($surface-variant, 0.16); }
.collection-header { width: 100%; display: flex; justify-content: space-between; align-items: center; gap: $spacing-md; padding: 14px 18px; border: 0; background: rgba($primary-color, 0.06); color: $on-surface; cursor: pointer; text-align: left; }
.collection-header:hover { background: rgba($primary-color, 0.1); }
.collection-header div { display: flex; align-items: center; gap: $spacing-sm; }
.collection-header .material-icons { color: $primary-color; }
.collection-header small { color: $on-surface-variant; }
.collection-header-actions { margin-left: auto; }
.icon-action { width: 34px; height: 34px; display: grid; place-items: center; border: 0; border-radius: $radius-small; background: transparent; color: $primary-color; cursor: pointer; }
.icon-action:hover { background: rgba($primary-color, 0.1); }
.icon-action .material-icons { font-size: 19px; color: inherit; }
.icon-action.danger { color: $error; }
.icon-action.danger:hover { background: $error-container; }
.expand-icon { transition: transform 0.2s ease; }
.expand-icon.collapsed { transform: rotate(-90deg); }
.empty-collection { padding: 18px; color: $outline; }
.document-table { overflow-x: auto; }
.table-row { display: grid; grid-template-columns: minmax(360px, 1.7fr) 80px 90px 90px 160px 160px 170px; align-items: center; gap: $spacing-md; min-width: 1220px; padding: 16px 20px; border-bottom: 1px solid $outline-variant; color: $on-surface-variant; font-size: 14px; }
.nested .table-row:last-child { border-bottom: 0; }
.table-head { background: rgba($primary-color, 0.06); color: $on-primary-container; font-weight: 600; }
.doc-cell { display: flex; align-items: center; gap: $spacing-md; min-width: 0; }
.doc-cell > .material-icons { color: $primary-color; }
.doc-cell strong, .doc-cell small, .doc-cell em { display: block; }
.doc-cell strong { color: $on-surface; }
.doc-cell small { max-width: 420px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: $outline; }
.doc-cell em { color: $error; font-style: normal; font-size: 12px; }
.chip, .visibility-button { justify-self: start; padding: 5px 12px; border-radius: $radius-small; border: 0; font-size: 12px; font-weight: 600; background: $surface-variant; color: $on-surface-variant; }
.chip.ready, .visibility-button { background: #dff7e8; color: #146c2e; }
.chip.processing { background: $tertiary-container; color: $on-tertiary-container; }
.chip.error { background: $error-container; color: $error; }
.visibility-button { cursor: pointer; }
.collection-select { height: 36px; border: 1px solid $outline-variant; border-radius: $radius-small; padding: 0 8px; background: $surface; color: $on-surface; }
.row-actions { gap: $spacing-sm; }
.danger { color: $error !important; }
.drawer-mask, .modal-mask { position: fixed; inset: 0; background: rgba(28, 27, 31, 0.32); z-index: 300; display: flex; }
.drawer-mask { justify-content: flex-end; }
.modal-mask { justify-content: center; align-items: center; padding: $spacing-lg; }
.detail-drawer { width: min(760px, 100%); height: 100vh; overflow: auto; background: $surface; box-shadow: $shadow-4; padding: $spacing-lg; }
.drawer-header { display: flex; justify-content: space-between; align-items: center; gap: $spacing-md; margin-bottom: $spacing-lg; }
.drawer-header h3 { color: $on-surface; font-size: 22px; }
.title-form { display: grid; grid-template-columns: 1fr auto; gap: $spacing-md; align-items: end; padding: $spacing-md; border: 1px solid $outline-variant; border-radius: $radius-medium; margin-bottom: $spacing-lg; }
.title-form label { display: flex; flex-direction: column; gap: $spacing-xs; color: $on-surface-variant; font-size: 13px; }
.title-form input { height: 42px; border: 1px solid $outline; border-radius: $radius-small; padding: 0 12px; background: transparent; color: $on-surface; }
.chunk-list { display: flex; flex-direction: column; gap: $spacing-md; }
.chunk-card { border: 1px solid $outline-variant; border-radius: $radius-medium; padding: $spacing-md; background: rgba($surface-variant, 0.24); }
.chunk-header { display: flex; justify-content: space-between; align-items: center; gap: $spacing-md; margin-bottom: $spacing-sm; }
.chunk-header strong { color: $primary-color; }
.chunk-text { white-space: pre-wrap; color: $on-surface; line-height: 1.7; }
.chunk-editor { min-height: 180px; margin-bottom: $spacing-md; }
.chunk-actions { display: flex; justify-content: flex-end; gap: $spacing-sm; }
.confirm-dialog { width: min(560px, 100%); display: grid; grid-template-columns: auto 1fr; gap: $spacing-md; padding: $spacing-lg; border-radius: $radius-large; background: $surface; box-shadow: $shadow-4; color: $on-surface; }
.dialog-icon { width: 48px; height: 48px; display: grid; place-items: center; border-radius: $radius-medium; background: $tertiary-container; color: $on-tertiary-container; }
.dialog-icon .material-icons { color: inherit; }
.confirm-dialog h3 { font-size: 20px; margin-bottom: $spacing-xs; }
.confirm-dialog p:not(.eyebrow) { color: $on-surface-variant; line-height: 1.6; }
.duplicate-list { display: flex; flex-wrap: wrap; gap: $spacing-xs; margin-top: $spacing-md; }
.duplicate-list span { max-width: 220px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; padding: 5px 9px; border-radius: $radius-small; background: rgba($primary-color, 0.08); color: $on-surface-variant; font-size: 12px; }
.dialog-actions { grid-column: 1 / -1; display: flex; justify-content: flex-end; gap: $spacing-sm; margin-top: $spacing-sm; }
@media (max-width: 1080px) { .action-grid, .collection-create-card, .filter-card { grid-template-columns: 1fr; } .page-header { flex-direction: column; align-items: stretch; } }
</style>
