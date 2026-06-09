<template>
  <button class="material-button outlined audio-recorder" :class="{ recording }" :disabled="transcribing" @click="toggleRecording">
    <span class="material-icons">{{ recording ? 'stop' : 'mic' }}</span>
    {{ label }}
  </button>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useAudio } from '@/composables/useAudio'

const props = defineProps({ language: { type: String, default: 'zh-CN' } })
const emit = defineEmits(['transcribed', 'error'])
const { recording, transcribing, error, startRecording, stopRecording } = useAudio()
const stream = ref(null)

const label = computed(() => {
  if (transcribing.value) return '识别中...'
  return recording.value ? '停止录音' : '语音输入'
})

const toggleRecording = async () => {
  try {
    if (recording.value) {
      const text = await stopRecording(stream.value, props.language)
      if (text) emit('transcribed', text)
      return
    }
    stream.value = await startRecording()
  } catch (exc) {
    emit('error', error.value || exc.message || '语音处理失败')
  }
}
</script>

<style scoped lang="scss">
.audio-recorder.recording { color: $error; border-color: $error; background: rgba($error, 0.08); }
</style>
