<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { onBeforeRouteLeave } from 'vue-router'
import AppLayout from '@/components/layout/AppLayout.vue'
import Icon from '@/components/common/Icon.vue'
import MigrationDialog from '@/components/settings/MigrationDialog.vue'
import { useSettingsStore } from '@/stores/settings'
import { settingsApi } from '@/api/settings'
import { isDesktop, nativeRestartBackend } from '@/api/desktop'

const store = useSettingsStore()
const dialogVisible = ref(false)
const dialogMode = ref<'wizard' | 'progress'>('wizard')
const initialTarget = ref('')
const picking = ref(false)
const pickError = ref('')
const restarting = ref(false)
const cleaning = ref(false)

onMounted(async () => {
  store.fetchStorage()
  store.fetchAbout()
  try {
    const st = await store.pollMigration()
    if (st.status === 'running') store.startPolling()
  } catch {
    // 迁移状态加载失败不阻断页面
  }
  window.addEventListener('beforeunload', onBeforeUnload)
})

onBeforeUnmount(() => {
  window.removeEventListener('beforeunload', onBeforeUnload)
  store.stopPolling()
})

// 迁移期间离开页面兜底守卫（进度遮罩已阻断侧边栏点击）
onBeforeRouteLeave(() => {
  if (store.migrating) {
    return confirm('迁移正在进行中，离开页面后可在设置页恢复查看进度。确定离开？')
  }
})

function onBeforeUnload(e: BeforeUnloadEvent) {
  if (store.migrating) {
    e.preventDefault()
    e.returnValue = ''
  }
}

const ov = computed(() => store.storage)
const residual = computed(() => store.migration?.residual_files || [])
const showResidual = computed(
  () => residual.value.length > 0 && store.migration?.status === 'completed_with_warnings',
)
const recoveryPreSwitch = computed(() => {
  const p = ov.value?.recovery?.phase || ''
  return ['precheck', 'copying', 'verifying', 'rewriting'].includes(p)
})

const diskPercent = computed(() => {
  const d = ov.value?.disk
  if (!d || !d.total) return 0
  return Math.min(100, Math.round((d.used / d.total) * 100))
})
const diskCritical = computed(() => {
  const d = ov.value?.disk
  return d && d.total ? d.free / d.total < 0.1 : false
})

function fmtBytes(n: number): string {
  if (!n) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB', 'TB']
  let i = 0
  let v = n
  while (v >= 1024 && i < units.length - 1) {
    v /= 1024
    i++
  }
  return `${i === 0 ? v : v.toFixed(1)} ${units[i]}`
}

async function changeLocation() {
  pickError.value = ''
  picking.value = true
  initialTarget.value = ''
  try {
    const res = await settingsApi.pickFolder()
    if (!res.data.cancelled && res.data.path) {
      initialTarget.value = res.data.path
    }
  } catch (e: any) {
    // 对话框不可用时仍打开向导，允许手动输入路径
    pickError.value = e.message || '目录选择失败，可在弹窗中手动输入路径'
  } finally {
    picking.value = false
    dialogMode.value = 'wizard'
    dialogVisible.value = true
  }
}

async function resetDefault() {
  if (!confirm(`将数据迁回默认位置？\n${ov.value?.default_root || ''}`)) return
  try {
    const r = await store.resetDefault()
    if (r.migration_id) {
      dialogMode.value = 'progress'
      dialogVisible.value = true
    }
  } catch (e: any) {
    alert(e.message || '操作失败')
  }
}

async function resumeRecovery() {
  try {
    await store.resumeMigration()
    dialogMode.value = 'progress'
    dialogVisible.value = true
  } catch (e: any) {
    alert(e.message || '恢复失败')
  }
}

async function rollbackRecovery() {
  if (!confirm('放弃本次迁移并清理目标位置的半成品文件？\n（当前数据完好无损）')) return
  try {
    await store.rollbackMigration()
  } catch (e: any) {
    alert(e.message || '操作失败')
  }
}

async function retryCleanup() {
  cleaning.value = true
  try {
    await store.cleanupOld()
  } catch (e: any) {
    alert(e.message || '清理失败')
  } finally {
    cleaning.value = false
  }
}

async function retryConnection() {
  await store.fetchStorage()
  if (ov.value?.root_fallback_warning) {
    alert('自定义数据位置仍不可达。请确认磁盘已连接后重启应用。')
  }
}

async function restartNow() {
  restarting.value = true
  if (isDesktop()) {
    await nativeRestartBackend()
  } else {
    location.reload()
  }
}

function onMigrated() {
  store.fetchStorage()
}
</script>

<template>
  <AppLayout>
    <div class="max-w-5xl">
      <!-- 页头 -->
      <div class="mb-5">
        <div class="text-xs text-ink-tertiary mb-1">系统</div>
        <h1 class="text-2xl font-bold text-ink-primary tracking-tight">设置</h1>
        <p class="text-sm text-ink-secondary mt-1.5">管理数据存储位置与应用偏好</p>
      </div>

      <!-- 自定义根不可达警示 -->
      <div
        v-if="ov?.root_fallback_warning"
        class="mb-4 flex items-center gap-2 px-4 py-3 rounded-card border border-amber-200 bg-amber-50 text-sm text-amber-700"
      >
        <Icon name="warning" :size="16" class="flex-shrink-0" />
        <span class="min-w-0 flex-1">{{ ov.root_fallback_warning }}</span>
        <button @click="retryConnection" class="flex-shrink-0 px-3 py-1.5 bg-white border border-amber-300 rounded-btn text-xs font-medium hover:bg-amber-100 transition-colors">重试连接</button>
        <button @click="resetDefault" class="flex-shrink-0 px-3 py-1.5 bg-white border border-amber-300 rounded-btn text-xs font-medium hover:bg-amber-100 transition-colors">恢复默认位置</button>
      </div>

      <!-- 待重启横幅 -->
      <div
        v-if="ov?.pending_restart"
        class="mb-4 flex items-center gap-2 px-4 py-3 rounded-card border border-brand-200 bg-brand-50 text-sm text-brand-700"
      >
        <Icon name="info" :size="16" class="flex-shrink-0" />
        <span class="min-w-0 flex-1">
          新数据位置将在重启服务后生效。{{ isDesktop() ? '' : '请停止并重新运行 start.ps1（或 python -m backend.app）。' }}
        </span>
        <button
          @click="restartNow"
          :disabled="restarting"
          class="flex-shrink-0 px-3 py-1.5 bg-brand-700 hover:bg-brand-800 text-white rounded-btn text-xs font-semibold transition-colors disabled:opacity-50"
        >{{ isDesktop() ? (restarting ? '重启中…' : '立即重启') : '刷新页面' }}</button>
      </div>

      <!-- 中断恢复卡片 -->
      <div
        v-if="ov?.recovery"
        class="mb-4 bg-white border border-amber-200 rounded-card shadow-card px-5 py-4"
      >
        <div class="flex items-center gap-2 mb-2">
          <Icon name="warning" :size="16" class="text-amber-500" />
          <span class="font-semibold text-ink-primary text-sm">检测到未完成的迁移</span>
        </div>
        <div class="text-xs text-ink-secondary font-mono space-y-0.5 mb-3">
          <div class="truncate" :title="ov.recovery.source_root">源：{{ ov.recovery.source_root }}</div>
          <div class="truncate" :title="ov.recovery.target_root">目标：{{ ov.recovery.target_root }}</div>
        </div>
        <div class="flex gap-2">
          <button @click="resumeRecovery" class="px-3 py-1.5 bg-brand-700 hover:bg-brand-800 text-white rounded-btn text-xs font-semibold transition-colors">
            {{ recoveryPreSwitch ? '继续迁移' : '继续完成清理' }}
          </button>
          <button
            v-if="recoveryPreSwitch"
            @click="rollbackRecovery"
            class="px-3 py-1.5 bg-white border border-surface-border hover:bg-surface-hover rounded-btn text-xs text-red-600 transition-colors"
          >放弃并清理</button>
        </div>
      </div>

      <!-- 数据存储 -->
      <div class="bg-white border border-surface-border rounded-card shadow-card mb-4">
        <div class="flex items-center justify-between px-5 py-4 border-b border-surface-border">
          <div class="flex items-center gap-2">
            <Icon name="hard-drive" :size="18" class="text-brand-700" />
            <span class="font-semibold text-ink-primary">数据存储</span>
            <span v-if="ov?.is_custom" class="badge badge-success">自定义位置</span>
            <span v-else class="badge badge-pending">默认位置</span>
          </div>
          <div class="flex gap-2">
            <button
              v-if="ov?.is_custom"
              @click="resetDefault"
              class="px-3 py-2 bg-white border border-surface-border hover:bg-surface-hover rounded-btn text-sm text-ink-secondary transition-colors"
            >恢复默认位置</button>
            <button
              @click="changeLocation"
              :disabled="picking || store.migrating"
              class="px-4 py-2 bg-brand-700 hover:bg-brand-800 active:bg-brand-900 text-white rounded-btn text-sm font-semibold inline-flex items-center gap-2 transition-colors disabled:opacity-50"
            >
              <Icon name="folder-open" :size="14" /> {{ picking ? '选择中…' : '更改位置' }}
            </button>
          </div>
        </div>

        <div class="px-5 py-4 space-y-4">
          <div v-if="store.loading && !ov" class="text-sm text-ink-secondary flex items-center gap-2">
            <Icon name="spinner" :size="14" spin /> 正在读取存储信息…
          </div>
          <div v-if="store.error" class="text-sm text-red-600">{{ store.error }}</div>

          <template v-if="ov">
            <!-- 当前根 + 磁盘 -->
            <div>
              <div class="text-xs text-ink-tertiary mb-1">当前数据根目录</div>
              <div class="font-mono text-sm text-ink-primary break-all">{{ ov.active_root }}</div>
              <div class="mt-2.5">
                <div class="flex justify-between text-xs text-ink-secondary mb-1 font-numeric">
                  <span>磁盘占用 {{ diskPercent }}%</span>
                  <span>剩余 {{ fmtBytes(ov.disk.free) }} / {{ fmtBytes(ov.disk.total) }}</span>
                </div>
                <div class="h-1.5 bg-surface-hover rounded-full overflow-hidden">
                  <div
                    class="h-full rounded-full transition-all duration-200"
                    :class="diskCritical ? 'bg-amber-500' : 'bg-brand-300'"
                    :style="{ width: diskPercent + '%' }"
                  ></div>
                </div>
              </div>
            </div>

            <!-- 模块目录卡片 -->
            <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
              <div
                v-for="m in ov.modules"
                :key="m.key"
                class="border border-surface-border rounded-btn px-3 py-2.5"
              >
                <div class="flex items-center justify-between mb-1">
                  <span class="text-sm font-medium text-ink-primary">{{ m.label }}</span>
                  <span class="tag">{{ m.key }}</span>
                </div>
                <div class="text-xs text-ink-tertiary font-mono truncate mb-1.5" :title="m.dir">{{ m.dir }}</div>
                <div class="text-xs text-ink-secondary font-numeric">{{ fmtBytes(m.size_bytes) }} · {{ m.file_count }} 个文件</div>
              </div>
            </div>

            <!-- 残留清理 -->
            <div v-if="showResidual" class="px-3 py-2.5 rounded-btn border border-amber-200 bg-amber-50 space-y-2">
              <div class="flex items-center gap-2 text-sm text-amber-700">
                <Icon name="warning" :size="15" />
                旧位置有 {{ residual.length }} 个文件未能删除（被占用或权限不足）
              </div>
              <div class="max-h-28 overflow-y-auto space-y-0.5">
                <div v-for="(r, i) in residual" :key="i" class="text-xs text-ink-secondary font-mono truncate" :title="r.path">{{ r.path }}</div>
              </div>
              <button
                @click="retryCleanup"
                :disabled="cleaning"
                class="px-3 py-1.5 bg-white border border-amber-300 rounded-btn text-xs text-amber-700 font-medium hover:bg-amber-100 inline-flex items-center gap-1.5 transition-colors disabled:opacity-50"
              >
                <Icon name="refresh" :size="13" /> {{ cleaning ? '清理中…' : '重试清理' }}
              </button>
            </div>

            <div v-if="pickError" class="text-xs text-amber-600">{{ pickError }}</div>
          </template>
        </div>
      </div>

      <!-- 关于 -->
      <div class="bg-white border border-surface-border rounded-card shadow-card">
        <div class="flex items-center gap-2 px-5 py-4 border-b border-surface-border">
          <Icon name="info" :size="18" class="text-brand-700" />
          <span class="font-semibold text-ink-primary">关于</span>
        </div>
        <div class="px-5 py-4 grid grid-cols-1 sm:grid-cols-2 gap-x-8 gap-y-2.5 text-sm">
          <div class="flex justify-between gap-4">
            <span class="text-ink-tertiary">应用名称</span>
            <span class="text-ink-primary font-medium">{{ store.about?.app || '田间智瞰' }}</span>
          </div>
          <div class="flex justify-between gap-4">
            <span class="text-ink-tertiary">版本</span>
            <span class="text-ink-primary font-numeric">{{ store.about?.version || '—' }}</span>
          </div>
          <div class="flex justify-between gap-4">
            <span class="text-ink-tertiary">运行形态</span>
            <span class="text-ink-primary">{{ store.about?.mode === 'desktop' ? '桌面端（Electron）' : 'Web' }}</span>
          </div>
          <div class="flex justify-between gap-4">
            <span class="text-ink-tertiary">Python</span>
            <span class="text-ink-primary font-numeric">{{ store.about?.python || '—' }}</span>
          </div>
        </div>
      </div>
    </div>

    <MigrationDialog
      v-model="dialogVisible"
      :mode="dialogMode"
      :initial-target="initialTarget"
      @migrated="onMigrated"
    />
  </AppLayout>
</template>