<template>
  <aside class="session-panel">
    <button class="material-button filled new-button" @click="$emit('create')">
      <span class="material-icons">add</span>
      新建会话
    </button>
    <input v-model="localKeyword" class="search-input" placeholder="搜索会话" @input="$emit('search', localKeyword)" />
    <div class="session-list">
      <article v-for="session in sessions" :key="session.id" :class="['session-item', { active: session.id === activeId }]" @click="$emit('select', session)">
        <div>
          <strong>{{ session.title }}</strong>
          <small>{{ formatTime(session.updated_at) }}</small>
        </div>
        <div class="actions" @click.stop>
          <button @click="$emit('rename', session)"><span class="material-icons">edit</span></button>
          <button @click="$emit('delete', session)"><span class="material-icons">delete</span></button>
        </div>
      </article>
    </div>
  </aside>
</template>

<script setup>
import { ref } from 'vue'
defineProps({ sessions: { type: Array, default: () => [] }, activeId: { type: String, default: '' } })
defineEmits(['create', 'select', 'rename', 'delete', 'search'])
const localKeyword = ref('')
const formatTime = (time) => {
  if (!time) return '-'
  const value = String(time)
  const normalized = /[zZ]|[+-]\d{2}:?\d{2}$/.test(value) ? value : `${value}Z`
  const date = new Date(normalized)
  if (Number.isNaN(date.getTime())) return '-'
  return date.toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}
</script>

<style scoped lang="scss">
.session-panel { width: 300px; min-width: 300px; height: 100%; padding: 16px; background: $surface; border-right: 1px solid $outline-variant; display: flex; flex-direction: column; gap: 12px; }
.new-button { width: 100%; }
.search-input { height: 42px; border: 1px solid $outline; border-radius: $radius-small; padding: 0 12px; background: transparent; color: $on-surface; }
.session-list { display: flex; flex-direction: column; gap: 8px; overflow: auto; }
.session-item { display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: 8px; padding: 12px; border-radius: $radius-medium; cursor: pointer; color: $on-surface; border: 1px solid transparent; }
.session-item:hover, .session-item.active { background: $primary-container; border-color: $primary-color; }
.session-item strong, .session-item small { display: block; overflow: hidden; white-space: nowrap; text-overflow: ellipsis; }
.session-item small { color: $on-surface-variant; font-size: 12px; }
.actions { display: flex; align-items: center; gap: 2px; }
.actions button { width: 28px; height: 28px; border: 0; border-radius: $radius-small; background: transparent; color: $on-surface-variant; cursor: pointer; }
.actions .material-icons { font-size: 17px; }
@media (max-width: 860px) { .session-panel { width: 100%; min-width: 0; height: 260px; border-right: 0; border-bottom: 1px solid $outline-variant; } }
</style>
