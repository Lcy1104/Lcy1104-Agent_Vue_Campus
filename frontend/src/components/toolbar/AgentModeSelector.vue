<template>
  <label class="agent-mode-selector" :title="currentDescription">
    <span class="material-icons">account_tree</span>
    <select :value="modelValue" @change="$emit('update:modelValue', $event.target.value)">
      <option v-for="strategy in normalizedStrategies" :key="strategy.strategy_name" :value="strategy.strategy_name">
        {{ strategy.display_name }}
      </option>
    </select>
    <span class="mode-help">{{ currentShortDescription }}</span>
  </label>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  modelValue: { type: String, default: 'react' },
  strategies: { type: Array, default: () => [] }
})

defineEmits(['update:modelValue'])

const fallbackStrategies = [
  { strategy_name: 'react', display_name: 'ReAct 模式', description: '适合工具调用型问答，边思考边行动。' },
  { strategy_name: 'plan_execute', display_name: 'Plan-Execute 模式', description: '先规划再执行，适合复杂多步骤任务。' },
  { strategy_name: 'multi_agent', display_name: '多 Agent 协作模式', description: '分析、执行、校验三个子图协同，适合复杂校验任务。' }
]

const normalizedStrategies = computed(() => props.strategies.length ? props.strategies : fallbackStrategies)
const currentStrategy = computed(() => normalizedStrategies.value.find(item => item.strategy_name === props.modelValue) || normalizedStrategies.value[0])
const currentDescription = computed(() => currentStrategy.value?.description || '')
const currentShortDescription = computed(() => currentDescription.value.replace(/，.*/, ''))
</script>

<style scoped lang="scss">
.agent-mode-selector { display: inline-flex; align-items: center; gap: 6px; min-height: 40px; padding: 0 10px; border: 1px solid $outline; border-radius: $radius-small; color: $primary-color; }
.agent-mode-selector select { height: 36px; min-width: 172px; border: 0; outline: 0; background: transparent; color: $on-surface; }
.agent-mode-selector .material-icons { font-size: 20px; }
.mode-help { max-width: 180px; color: $on-surface-variant; font-size: 12px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
@media (max-width: 980px) { .mode-help { display: none; } }
</style>
