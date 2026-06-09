import { ref } from 'vue'
import audioApi from '@/api/audio'

const globalSpeaking = ref(false)
let globalAudio = null
let globalAudioUrl = ''

const stopGlobalAudio = () => {
  if (globalAudio) {
    globalAudio.pause()
    globalAudio.currentTime = 0
    globalAudio = null
  }
  if (globalAudioUrl) {
    URL.revokeObjectURL(globalAudioUrl)
    globalAudioUrl = ''
  }
  globalSpeaking.value = false
}

export function useAudio() {
  const recording = ref(false)
  const transcribing = ref(false)
  const speaking = globalSpeaking
  const error = ref('')
  let mediaRecorder = null
  let audioChunks = []

  const startRecording = async () => {
    error.value = ''
    if (!navigator.mediaDevices?.getUserMedia) {
      error.value = '当前浏览器不支持麦克风录音，请使用 Chrome/Edge 并通过 localhost 或 HTTPS 访问。'
      throw new Error(error.value)
    }
    let stream
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    } catch (exc) {
      if (exc.name === 'NotAllowedError' || exc.name === 'PermissionDeniedError') {
        error.value = '麦克风权限被拒绝。请点击浏览器地址栏左侧的权限图标，允许本网站使用麦克风后重试。'
      } else if (exc.name === 'NotFoundError') {
        error.value = '没有检测到可用麦克风，请连接麦克风后重试。'
      } else if (window.location.protocol !== 'https:' && window.location.hostname !== 'localhost') {
        error.value = '浏览器只允许在 HTTPS 或 localhost 下使用麦克风，请改用 localhost 或配置 HTTPS。'
      } else {
        error.value = `麦克风启动失败：${exc.message || exc.name || '未知错误'}`
      }
      throw new Error(error.value)
    }
    audioChunks = []
    mediaRecorder = new MediaRecorder(stream)
    mediaRecorder.ondataavailable = event => {
      if (event.data.size > 0) audioChunks.push(event.data)
    }
    mediaRecorder.start()
    recording.value = true
    return stream
  }

  const stopRecording = (stream, language = 'zh-CN') => new Promise((resolve, reject) => {
    if (!mediaRecorder || mediaRecorder.state === 'inactive') return resolve('')
    mediaRecorder.onstop = async () => {
      recording.value = false
      transcribing.value = true
      stream?.getTracks().forEach(track => track.stop())
      try {
        const blob = new Blob(audioChunks, { type: 'audio/webm' })
        const formData = new FormData()
        formData.append('file', blob, 'recording.webm')
        const response = await audioApi.transcribe(formData, language)
        resolve(response.data.text || '')
      } catch (exc) {
        error.value = exc.response?.data?.detail || exc.message || '语音识别失败'
        reject(exc)
      } finally {
        transcribing.value = false
      }
    }
    mediaRecorder.stop()
  })

  const speak = async (text, options = {}) => {
    if (!text?.trim()) return
    if (speaking.value) {
      stopGlobalAudio()
      return
    }
    speaking.value = true
    error.value = ''
    try {
      stopGlobalAudio()
      speaking.value = true
      const response = await audioApi.tts(text, options)
      globalAudioUrl = URL.createObjectURL(response.data)
      globalAudio = new Audio(globalAudioUrl)
      globalAudio.onended = stopGlobalAudio
      globalAudio.onerror = stopGlobalAudio
      await globalAudio.play()
    } catch (exc) {
      stopGlobalAudio()
      error.value = exc.response?.data?.detail || exc.message || '语音合成失败'
      throw exc
    }
  }

  return { recording, transcribing, speaking, error, startRecording, stopRecording, speak, stopSpeaking: stopGlobalAudio }
}
