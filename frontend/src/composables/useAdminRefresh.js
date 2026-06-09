import { onMounted, onUnmounted } from 'vue'

export function useAdminRefresh(callback) {
  const handler = event => callback?.(event.detail?.reason)
  onMounted(() => window.addEventListener('admin-refresh', handler))
  onUnmounted(() => window.removeEventListener('admin-refresh', handler))
}
