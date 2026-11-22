<script setup lang="ts">
import { onMounted, ref } from 'vue'
import Sidebar from './Sidebar.vue'
import Icon from '@/components/common/Icon.vue'
import client from '@/api/client'

// 布局壳：左侧 Sidebar 固定全高 + 右侧主内容区独立滚动
// 全局横幅：存储迁移待重启 / 自定义根不可达回退（轻量端点，不扫描目录）
const pendingRestart = ref(false)
const fallbackWarning = ref<string | null>(null)

onMounted(async () => {
  try {
    const res = await client.get<
      unknown,
      { data: { pending_restart: boolean; root_fallback_warning: string | null } }
    >('/settings/storage/pending')
    pendingRestart.value = res.data.pending_restart
    fallbackWarning.value = res.data.root_fallback_warning
  } catch {
    // 横幅加载失败不影响页面
  }
})
</script>

<template>
  <div class="flex h-screen w-full overflow-hidden">
    <Sidebar />
    <main class="flex-1 h-full min-h-0 overflow-y-auto p-8 bg-surface-bg/30 min-w-0">
      <div
        v-if="fallbackWarning"
        class="mb-4 flex items-center gap-2 px-4 py-2.5 rounded-card border border-amber-200 bg-amber-50 text-sm text-amber-700"
      >
        <Icon name="warning" :size="16" class="flex-shrink-0" />
        <span class="min-w-0 truncate">{{ fallbackWarning }}</span>
        <router-link to="/settings" class="ml-auto flex-shrink-0 font-medium hover:underline">前往设置</router-link>
      </div>
      <div
        v-else-if="pendingRestart"
        class="mb-4 flex items-center gap-2 px-4 py-2.5 rounded-card border border-brand-200 bg-brand-50 text-sm text-brand-700"
      >
        <Icon name="info" :size="16" class="flex-shrink-0" />
        <span>新数据位置将在重启服务后生效</span>
        <router-link to="/settings" class="ml-auto flex-shrink-0 font-medium hover:underline">前往设置</router-link>
      </div>
      <slot />
    </main>
  </div>
</template>