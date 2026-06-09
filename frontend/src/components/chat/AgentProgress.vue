<template>
  <div v-if="progress" :class="['agent-progress', hasFailure ? 'failed' : '']">
    <div class="progress-head">
      <span class="pulse"></span>
      <div>
        <strong>{{ progress.status || 'Agent 正在执行' }}</strong>
        <small>实时执行状态</small>
      </div>
    </div>

    <div v-if="progress.items?.length" class="progress-list">
      <div v-for="item in progress.items" :key="item.id" :class="['progress-item', item.failed ? 'failed' : '', item.done ? 'done' : 'running']">
        <span class="material-icons">{{ iconFor(item) }}</span>
        <div class="item-body">
          <div class="item-title">
            <b>{{ item.label }}</b>
            <time>{{ item.time }}</time>
          </div>
          <p v-if="item.model || item.backend">{{ item.model || '内部工具' }}<template v-if="item.backend">（{{ item.backend }}）</template></p>
          <p v-if="item.detail" class="detail">{{ item.detail }}</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({ progress: { type: Object, default: null } })

const hasFailure = computed(() => props.progress?.items?.some(item => item.failed))

const iconFor = (item) => {
  if (item.failed) return 'error'
  if (item.type === 'connect') return item.done ? 'settings_ethernet' : 'sync'
  if (item.type === 'model') return 'memory'
  if (item.type === 'tool') return 'build'
  if (item.type === 'sources') return 'library_books'
  if (item.type === 'answer') return 'edit_note'
  if (item.type === 'step') return 'account_tree'
  return item.done ? 'check_circle' : 'sync'
}
</script>

<style scoped lang="scss">
.agent-progress { display: grid; gap: 10px; margin-bottom: 12px; padding: 12px; border: 1px solid rgba($primary-color, .28); border-radius: $radius-medium; background: linear-gradient(135deg, rgba($primary-color, .08), rgba($surface, .92)); }
.agent-progress.failed { border-color: $error; background: $error-container; }
.progress-head { display: flex; align-items: center; gap: 10px; }
.progress-head strong { display: block; color: $on-surface; }
.progress-head small { color: $on-surface-variant; }
.pulse { width: 10px; height: 10px; border-radius: 50%; background: $primary-color; box-shadow: 0 0 0 0 rgba($primary-color, .45); animation: pulse 1.4s infinite; }
.failed .pulse { background: $error; animation: none; }
.progress-list { display: grid; gap: 8px; }
.progress-item { display: grid; grid-template-columns: 24px minmax(0, 1fr); gap: 8px; padding: 8px; border-radius: $radius-small; background: rgba(255,255,255,.7); border: 1px solid $outline-variant; }
.progress-item .material-icons { font-size: 20px; color: $primary-color; }
.progress-item.running .material-icons { animation: spin 1.2s linear infinite; }
.progress-item.failed .material-icons { color: $error; animation: none; }
.item-title { display: flex; align-items: baseline; justify-content: space-between; gap: 10px; }
.item-title b { color: $on-surface; font-size: 13px; }
.item-title time { color: $on-surface-variant; font-size: 11px; white-space: nowrap; }
.item-body p { margin-top: 4px; color: $on-surface-variant; font-size: 12px; }
.detail { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
@keyframes pulse { 70% { box-shadow: 0 0 0 8px rgba($primary-color, 0); } 100% { box-shadow: 0 0 0 0 rgba($primary-color, 0); } }
@keyframes spin { to { transform: rotate(360deg); } }
</style>
