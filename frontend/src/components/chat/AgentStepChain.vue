<template>
  <div v-if="steps?.length" class="agent-step-chain">
    <strong>Agent 步骤链</strong>
    <div class="steps">
      <details v-for="(step, index) in steps" :key="`${step.node || 'step'}-${index}`" class="step" :open="index === steps.length - 1">
        <summary>
          <span class="material-icons">account_tree</span>
          {{ stepLabel(step.node, index) }}
          <small v-if="step.model">{{ step.model }}<template v-if="step.backend">（{{ step.backend }}）</template></small>
        </summary>
        <p>{{ step.content }}</p>
      </details>
    </div>
  </div>
</template>

<script setup>
defineProps({ steps: { type: Array, default: () => [] } })

const labels = {
  analyst: '分析',
  planner: '规划',
  executor: '执行',
  validator: '校验',
  agent: 'ReAct'
}

const stepLabel = (node, index) => labels[node] || node || `步骤 ${index + 1}`
</script>

<style scoped lang="scss">
.agent-step-chain { display: grid; gap: 8px; margin: 10px 0; padding: 10px; border-radius: $radius-medium; background: rgba($primary-color, 0.04); border: 1px solid $outline-variant; }
.agent-step-chain strong { color: $on-surface; }
.steps { display: grid; gap: 8px; }
.step { border-radius: $radius-small; background: $surface; padding: 8px; }
.step summary { display: flex; align-items: center; gap: 6px; cursor: pointer; color: $primary-color; font-weight: 600; }
.step small { margin-left: auto; color: $on-surface-variant; font-weight: 400; }
.step p { margin-top: 8px; color: $on-surface-variant; white-space: pre-wrap; }
.material-icons { font-size: 18px; }
</style>
