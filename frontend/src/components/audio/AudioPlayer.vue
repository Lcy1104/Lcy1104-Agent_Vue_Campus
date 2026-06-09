<template>
  <button class="copy-button audio-player" :disabled="!text" @click="play">
    <span class="material-icons">{{ speaking ? 'stop' : 'volume_up' }}</span>
    {{ speaking ? '停止' : '朗读' }}
  </button>
</template>

<script setup>
import { useAudio } from '@/composables/useAudio'

const props = defineProps({
  text: { type: String, default: '' },
  language: { type: String, default: 'zh-CN' },
  rate: { type: Number, default: null }
})

const { speaking, speak } = useAudio()
const play = async () => {
  await speak(props.text, { language: props.language, rate: props.rate })
}
</script>

<style scoped lang="scss">
.audio-player { display: inline-flex; align-items: center; gap: 4px; }
.audio-player .material-icons { font-size: 16px; }
</style>
