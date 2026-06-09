<template>
  <details v-if="mode !== 'off'" class="think-block" :open="mode === 'full'">
    <summary>思考过程</summary>
    <div v-if="normalizedItems.length" class="think-items">
      <article v-for="(item, index) in normalizedItems" :key="index">
        <strong>{{ nodeLabel(item.node) }}</strong>
        <small v-if="item.model_name">{{ item.model_name }}<template v-if="item.backend">（{{ item.backend }}）</template></small>
        <p>{{ item.content }}</p>
      </article>
    </div>
  </details>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  content: { type: [String, Array], default: '' },
  mode: { type: String, default: 'collapsed' }
})

const normalizedItems = computed(() => {
  if (Array.isArray(props.content)) return props.content.filter(item => item?.content)
  return props.content ? [{ content: props.content }] : []
})

const nodeLabel = (node) => ({
  analyst: '分析节点',
  planner: '规划节点',
  executor: '执行节点',
  validator: '校验节点',
  agent: 'ReAct 节点'
}[node] || 'Agent 节点')
</script>

<style scoped lang="scss">
.think-block { margin: 8px 0; padding: 10px; border-radius: $radius-medium; background: rgba($surface-variant, 0.45); color: $on-surface-variant; }
.think-block summary { cursor: pointer; font-weight: 600; }
.think-items { display: grid; gap: 8px; margin-top: 8px; }
.think-items article { padding: 8px; border-radius: $radius-small; background: rgba($surface, 0.75); }
.think-items strong { color: $primary-color; }
.think-items small { margin-left: 8px; color: $on-surface-variant; }
.think-block p { margin-top: 6px; font-style: italic; white-space: pre-wrap; }
</style>
