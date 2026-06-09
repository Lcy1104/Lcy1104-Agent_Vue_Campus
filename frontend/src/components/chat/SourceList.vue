<template>
  <div v-if="sources?.length" class="source-list">
    <strong>参考来源</strong>
    <article v-for="(source, index) in sources" :key="index">
      <span>{{ source.filename || source.source || `来源 ${index + 1}` }}</span>
      <p>{{ source.snippet }}</p>
    </article>
  </div>
</template>

<script setup>
defineProps({ sources: { type: Array, default: () => [] } })
</script>

<style scoped lang="scss">
.source-list { display: grid; gap: 8px; margin-top: 10px; padding-top: 10px; border-top: 1px solid $outline-variant; }
.source-list strong { color: $on-surface; }
article { padding: 8px; border-radius: $radius-small; background: rgba($surface-variant, 0.45); }
span { color: $primary-color; font-weight: 600; }
p { color: $on-surface-variant; font-size: 13px; }
</style>
