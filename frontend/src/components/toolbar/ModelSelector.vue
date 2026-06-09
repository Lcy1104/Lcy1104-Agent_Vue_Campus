<template>
  <label class="model-selector">
    <span class="material-icons">smart_toy</span>
    <select :value="modelValue || ''" @change="$emit('update:modelValue', $event.target.value || null)">
      <option value="">默认模型</option>
      <option v-for="model in models" :key="model.id" :value="model.id">
        {{ model.display_name || model.model_name }} · {{ capabilityLabel(model) }}
      </option>
    </select>
  </label>
</template>

<script setup>
defineProps({
  modelValue: { type: String, default: null },
  models: { type: Array, default: () => [] }
})

defineEmits(['update:modelValue'])

const capabilityLabel = (model) => {
  const caps = []
  if (model.capabilities?.text !== false) caps.push('文本')
  if (model.capabilities?.vision || model.is_multimodal) caps.push('视觉')
  if (model.capabilities?.tool_calling) caps.push('工具')
  if (model.is_default_text) caps.push('默认文本')
  if (model.is_default_vision) caps.push('默认视觉')
  return caps.join('/') || '未标注能力'
}
</script>

<style scoped lang="scss">
.model-selector { display: inline-flex; align-items: center; gap: 6px; height: 40px; padding: 0 10px; border: 1px solid $outline; border-radius: $radius-small; color: $primary-color; }
.model-selector select { height: 36px; min-width: 160px; border: 0; outline: 0; background: transparent; color: $on-surface; }
.model-selector .material-icons { font-size: 20px; }
</style>
