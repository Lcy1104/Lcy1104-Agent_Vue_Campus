<template>
  <details class="tool-card" :class="{ ignored: isIgnored }">
    <summary>
      <span class="material-icons">{{ isIgnored ? 'info' : 'construction' }}</span>
      {{ tool.name || 'tool' }}
      <small v-if="isIgnored">已跳过</small>
    </summary>
    <p v-if="isIgnored" class="tool-notice">{{ ignoredReason }}</p>
    <pre>输入：{{ format(tool.input) }}</pre>
    <pre>输出：{{ format(tool.output || tool) }}</pre>
  </details>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({ tool: { type: Object, default: () => ({}) } })

const isIgnored = computed(() => Boolean(props.tool.output?.ignored))
const ignoredReason = computed(() => props.tool.output?.reason || '外部工具服务当前不可用，本轮已忽略该工具结果。')
const format = (value) => JSON.stringify(value || {}, null, 2)
</script>

<style scoped lang="scss">
.tool-card { margin: 8px 0; padding: 10px; border: 1px solid $outline-variant; border-radius: $radius-medium; background: rgba($primary-color, 0.04); }
.tool-card summary { display: flex; align-items: center; gap: 6px; cursor: pointer; color: $primary-color; font-weight: 600; }
.tool-card summary small { margin-left: auto; font-size: 12px; color: $on-surface-variant; }
.tool-card.ignored { border-color: rgba($error, .35); background: rgba($error, .05); }
.tool-card.ignored summary { color: $error; }
.tool-notice { margin: 8px 0 0; color: $error; font-size: 13px; }
pre { white-space: pre-wrap; margin-top: 8px; font-size: 12px; color: $on-surface-variant; }
</style>
