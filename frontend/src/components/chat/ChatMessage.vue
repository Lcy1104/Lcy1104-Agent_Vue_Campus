<template>
  <article :class="['chat-message', message.role]">
    <div class="avatar">{{ avatarText }}</div>
    <div class="bubble">
      <AgentProgress v-if="message.role === 'assistant'" :progress="message.metadata?.progress" />
      <ThinkBlock v-if="message.metadata?.thinking" :content="message.metadata.thinking" :mode="thinkMode" />
      <AgentStepChain :steps="message.metadata?.agent_steps || []" />
      <div v-if="message.attachments?.length" class="attachments">
        <img v-for="item in message.attachments" :key="item.id" :src="item.preview" :alt="item.name" />
      </div>
      <div class="content" v-html="renderedContent"></div>
      <ToolCallCard v-for="(tool, index) in message.tool_calls || []" :key="index" :tool="tool" />
      <SourceList :sources="message.metadata?.sources || []" />
      <div v-if="message.role === 'assistant' && message.content" class="message-actions">
        <button class="copy-button" @click="copyText">复制</button>
        <AudioPlayer :text="message.content" />
        <span class="elapsed-time">执行时间 {{ elapsedText }}</span>
      </div>
    </div>
  </article>
</template>

<script setup>
import { computed, nextTick } from 'vue'
import MarkdownIt from 'markdown-it'
import hljs from 'highlight.js/lib/core'
import javascript from 'highlight.js/lib/languages/javascript'
import python from 'highlight.js/lib/languages/python'
import json from 'highlight.js/lib/languages/json'
import bash from 'highlight.js/lib/languages/bash'
import DOMPurify from 'dompurify'
import ThinkBlock from './ThinkBlock.vue'
import ToolCallCard from './ToolCallCard.vue'
import SourceList from './SourceList.vue'
import AgentStepChain from './AgentStepChain.vue'
import AgentProgress from './AgentProgress.vue'
import AudioPlayer from '@/components/audio/AudioPlayer.vue'
import 'highlight.js/styles/github.css'

hljs.registerLanguage('javascript', javascript)
hljs.registerLanguage('js', javascript)
hljs.registerLanguage('python', python)
hljs.registerLanguage('py', python)
hljs.registerLanguage('json', json)
hljs.registerLanguage('bash', bash)
hljs.registerLanguage('shell', bash)

const props = defineProps({
  message: { type: Object, required: true },
  thinkMode: { type: String, default: 'collapsed' }
})

const md = new MarkdownIt({
  html: false,
  linkify: true,
  breaks: true,
  highlight(code, lang) {
    if (lang && hljs.getLanguage(lang)) {
      return `<pre class="hljs"><code>${hljs.highlight(code, { language: lang }).value}</code></pre>`
    }
    return `<pre class="hljs"><code>${md.utils.escapeHtml(code)}</code></pre>`
  }
})

const renderedContent = computed(() => DOMPurify.sanitize(md.render(props.message.content || '')))
const elapsedText = computed(() => {
  const ms = props.message.metadata?.elapsed_ms
  if (!ms) return '--'
  if (ms < 1000) return `${ms}ms`
  return `${(ms / 1000).toFixed(ms < 10000 ? 1 : 0)}s`
})
const avatarText = computed(() => {
  if (props.message.role === 'user') return '我'
  const label = props.message.metadata?.run_label || props.message.metadata?.model_name || 'AI'
  if (label === 'Graph') return 'Graph'
  return String(label).replace(/^ollama[:/]/i, '').slice(0, 10)
})

const copyText = async () => {
  await navigator.clipboard.writeText(props.message.content || '')
  await nextTick()
}

</script>

<style scoped lang="scss">
.chat-message { display: grid; grid-template-columns: 38px minmax(0, 1fr); gap: 12px; align-items: start; }
.chat-message.user { direction: rtl; }
.chat-message.user .bubble, .chat-message.user .avatar { direction: ltr; }
.avatar { display: grid; place-items: center; min-width: 38px; max-width: 84px; height: 38px; padding: 0 8px; border-radius: $radius-medium; background: $primary-container; color: $primary-color; font-size: 12px; font-weight: 700; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.bubble { max-width: min(760px, 100%); padding: 14px 16px; border-radius: $radius-large; background: $surface; box-shadow: $shadow-1; color: $on-surface; }
.user .bubble { background: $primary-color; color: $on-primary; }
.content :deep(pre) { overflow-x: auto; padding: 12px; border-radius: $radius-small; }
.content :deep(code) { font-family: Consolas, monospace; }
.attachments { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 10px; }
.attachments img { width: 120px; height: 88px; object-fit: cover; border-radius: $radius-small; border: 1px solid $outline-variant; }
.message-actions { display: flex; gap: 8px; margin-top: 10px; }
.elapsed-time { margin-left: auto; align-self: center; color: $on-surface-variant; font-size: 12px; }
.copy-button { border: 1px solid $outline-variant; border-radius: $radius-small; background: transparent; padding: 5px 10px; cursor: pointer; color: $primary-color; }
</style>
