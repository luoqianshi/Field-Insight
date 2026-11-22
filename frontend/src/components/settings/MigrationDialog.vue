<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import Icon from '@/components/common/Icon.vue'
import { useSettingsStore, isTerminal } from '@/stores/settings'
import { settingsApi, type PrecheckReport } from '@/api/settings'
import { isDesktop, nativeRestartBackend } from '@/api/desktop'

// 迁移向导弹窗：选择目标 → 确认 → 进度 → 结果（计划书 §5.2）
const props = withDefaults(
  defineProps<{
    modelValue: boolean
    mode?: 'wizard' | 'progress'
    initialTarget?: string
  }>(),
  { mode: 'wizard', initialTarget: '' },
)

const emit = defineEmits<{
  (e: 'update:modelValue', v: boolean): void
  (e: 'migrated'): void
}>()

const store = useSettingsStore()

const step = ref<'select' | 'confirm' | 'progress' | 'result'>('select')
const target = ref('')
const report = ref<PrecheckReport | null>(null)
const validating = ref(false)
const validateError = ref('')
const ack = ref(false)
const starting = ref(false)
const startError = ref('')
const confirmCancel = ref(false)
const restarting = ref(false)
const showDetails = ref(false)
const picking = ref(false)
const cleaning = ref(false)

const mig = computed(() => store.migration)
const canClose = computed(() => step.value !== 'progress')

const STAGES = [
  { key: 'copying', label: '复制数据' },
  { key: 'verifying', label: '完整性校验' },
  { key: 'switching', label: '切换配置' },
  { key: 'cleaning', label: '清理旧数据' },
]
const stageIndex = computed(() => {
  const p = mig.value?.phase || ''
  if (p === 'copying') return 0
  if (p === 'verifying') return 1
  if (p === 'rewriting' || p === 'switching') return 2
  return 3
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

function fmtDuration(s?: number): string {
  if (!s) return '0 秒'
  const m = Math.floor(s / 60)
  const sec = Math.round(s % 60)
  return m > 0 ? `${m} 分 ${sec} 秒` : `${sec} 秒`
}

watch(
  () => props.modelValue,
  (v) => {
    if (!v) return
    startError.value = ''
    confirmCancel.value = false
    showDetails.value = false
    restarting.value = false
    if (props.mode === 'progress' || store.migrating) {
      step.value = isTerminal(mig.value?.status) ? 'result' : 'progress'
    } else {
      step.value = 'select'
      target.value = props.initialTarget || ''
      report.value = null
      validateError.value = ''
      ack.value = false
      if (target.value) runValidate()
    }
  },
)

// 进度 → 结果自动流转；桌面态完全成功后自动重启服务
watch(
  () => mig.value?.status,
  (s) => {
    if (step.value === 'progress' && isTerminal(s)) {
      step.value = 'result'
      emit('migrated')
      if (s === 'completed' && isDesktop()) {
        restarting.value = true
        window.setTimeout(() => {
          nativeRestartBackend()
        }, 1500)
      }
    }
  },
)

async function browse() {
  picking.value = true
  validateError.value = ''
  try {
    const res = await settingsApi.pickFolder()
    if (!res.data.cancelled && res.data.path) {
      target.value = res.data.path
      await runValidate()
    }
  } catch (e: any) {
    validateError.value = e.message || '目录选择失败，可手动输入路径'
  } finally {
    picking.value = false
  }
}

async function runValidate() {
  if (!target.value.trim()) {
    report.value = null
    return
  }
  validating.value = true
  validateError.value = ''
  try {
    report.value = await store.validate(target.value.trim())
  } catch (e: any) {
    report.value = null
    validateError.value = e.message || '预检失败'
  } finally {
    validating.value = false
  }
}

function toConfirm() {
  if (!report.value?.ok) return
  ack.value = false
  startError.value = ''
  step.value = 'confirm'
}

async function startMigration() {
  starting.value = true
  startError.value = ''
  try {
    await store.startMigration(target.value.trim())
    step.value = 'progress'
  } catch (e: any) {
    startError.value = e.message || '启动迁移失败'
  } finally {
    starting.value = false
  }
}

async function doCancel() {
  try {
    await store.cancelMigration()
  } catch {
    // 状态轮询会反映结果
  }
  confirmCancel.value = false
}

async function retry() {
  step.value = 'select'
  report.value = null
  await runValidate()
}

async function resume() {
  try {
    await store.resumeMigration()
    step.value = 'progress'
  } catch (e: any) {
    startError.value = e.message || '恢复失败'
  }
}

async function rollback() {
  if (!confirm('放弃本次迁移并清理目标位置的半成品文件？\n（当前数据完好无损）')) return
  try {
    await store.rollbackMigration()
    emit('migrated')
    close()
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

function reloadPage() {
  location.reload()
}

async function restartNow() {
  restarting.value = true
  await nativeRestartBackend()
}

function close() {
  if (!canClose.value) return
  emit('update:modelValue', false)
}

const filePercent = computed(() => {
  const m = mig.value
  if (!m || !m.total_files) return 0
  return Math.min(100, Math.round((m.copied_files / m.total_files) * 100))
})
const bytePercent = computed(() => {
  const m = mig.value
  if (!m || !m.total_bytes) return 0
  return Math.min(100, Math.round((m.copied_bytes / m.total_bytes) * 100))
})
const residual = computed(() => mig.value?.residual_files || [])
const issueDetails = computed(() => {
  const m = mig.value
  if (!m) return []
  return [...(m.verify_mismatches || []), ...(m.errors || [])]
})
const isSuccess = computed(
  () => mig.value?.status === 'completed' || mig.value?.status === 'completed_with_warnings',
)
</script>

<template>
  <div v-if="modelValue" class="fixed inset-0 z-50 flex items-center justify-center">
    <div class="absolute inset-0 bg-black/30" @click="close"></div>
    <div
      class="relative bg-white border border-surface-border rounded-card shadow-card-hover w-full max-w-lg mx-4 max-h-[85vh] overflow-y-auto"
    >
      <!-- 头部 -->
      <div class="flex items-center justify-between px-5 py-4 border-b border-surface-border">
        <div class="flex items-center gap-2">
          <Icon name="hard-drive" :size="18" class="text-brand-700" />
          <span class="font-semibold text-ink-primary">
            {{ step === 'select' ? '更改数据位置' : step === 'confirm' ? '确认迁移' : step === 'progress' ? '正在迁移数据' : '迁移结果' }}
          </span>
        </div>
        <button
          v-if="canClose"
          @click="close"
          class="p-1 rounded-btn text-ink-tertiary hover:text-ink-primary hover:bg-surface-hover transition-colors"
          title="关闭"
        >
          <Icon name="close" :size="16" />
        </button>
      </div>

      <!-- ① 选择目标 -->
      <div v-if="step === 'select'" class="px-5 py-4 space-y-4">
        <div>
          <label class="block text-sm font-medium text-ink-primary mb-1.5">目标位置</label>
          <div class="flex gap-2">
            <input
              v-model="target"
              type="text"
              placeholder="如 D:\TJZKData"
              class="flex-1 min-w-0 px-3 py-2 border border-surface-border rounded-btn text-sm text-ink-primary focus:outline-none focus:border-brand-500 transition-colors"
              @change="runValidate"
            />
            <button
              @click="browse"
              :disabled="picking"
              class="px-3 py-2 bg-white border border-surface-border hover:bg-surface-hover rounded-btn text-sm text-ink-secondary inline-flex items-center gap-1.5 transition-colors flex-shrink-0 disabled:opacity-50"
            >
              <Icon name="folder-open" :size="14" /> 浏览
            </button>
          </div>
          <p class="text-xs text-ink-tertiary mt-1.5">选择其他磁盘分区的文件夹，各模块数据将整体迁移至该位置。</p>
        </div>

        <div v-if="validating" class="text-sm text-ink-secondary flex items-center gap-2">
          <Icon name="spinner" :size="14" spin /> 正在预检目标目录…
        </div>
        <div v-if="validateError" class="text-sm text-red-600">{{ validateError }}</div>

        <template v-if="report && !validating">
          <div v-if="report.errors.length" class="space-y-1.5">
            <div v-for="(err, i) in report.errors" :key="i" class="flex items-start gap-2 text-sm text-red-600">
              <Icon name="x-circle" :size="15" class="flex-shrink-0 mt-0.5" /> {{ err }}
            </div>
          </div>
          <div v-if="report.warnings.length" class="space-y-1.5">
            <div v-for="(w, i) in report.warnings" :key="i" class="flex items-start gap-2 text-sm text-amber-600">
              <Icon name="warning" :size="15" class="flex-shrink-0 mt-0.5" /> {{ w }}
            </div>
          </div>
          <div v-if="report.ok" class="bg-surface-bg rounded-btn px-3 py-2.5 text-xs text-ink-secondary space-y-1 font-numeric">
            <div>待迁移：{{ report.source_file_count }} 个文件 · {{ fmtBytes(report.source_size_bytes) }}</div>
            <div>目标剩余空间：{{ fmtBytes(report.target_free_bytes) }}</div>
          </div>
        </template>

        <div class="flex justify-end gap-2 pt-1">
          <button @click="close" class="px-4 py-2 bg-white border border-surface-border hover:bg-surface-hover rounded-btn text-sm text-ink-secondary transition-colors">取消</button>
          <button
            @click="toConfirm"
            :disabled="!report?.ok || validating"
            class="px-4 py-2 bg-brand-700 hover:bg-brand-800 text-white rounded-btn text-sm font-semibold transition-colors disabled:opacity-50 disabled:hover:bg-brand-700"
          >下一步</button>
        </div>
      </div>

      <!-- ② 确认 -->
      <div v-else-if="step === 'confirm'" class="px-5 py-4 space-y-4">
        <div class="bg-surface-bg rounded-btn px-3 py-3 space-y-2">
          <div class="flex items-center gap-2 text-sm">
            <Icon name="folder" :size="15" class="text-ink-tertiary flex-shrink-0" />
            <span class="text-ink-secondary truncate font-mono text-xs" :title="report?.source_root">{{ report?.source_root }}</span>
          </div>
          <div class="flex items-center gap-2 text-sm pl-0.5">
            <Icon name="arrow-right" :size="14" class="text-brand-600 flex-shrink-0 rotate-90" />
            <span class="text-ink-primary truncate font-mono text-xs font-medium" :title="report?.target">{{ report?.target }}</span>
          </div>
          <div class="text-xs text-ink-secondary font-numeric pt-1 border-t border-surface-border">
            {{ report?.source_file_count }} 个文件 · {{ fmtBytes(report?.source_size_bytes || 0) }}
          </div>
        </div>

        <ul class="text-sm text-ink-secondary space-y-1.5 list-disc pl-5">
          <li>迁移期间请勿进行其他操作，页面将被进度面板锁定。</li>
          <li>{{ isDesktop() ? '迁移完成后应用将自动重启服务。' : '迁移完成后需手动重启后端服务（停止后运行 start.ps1）。' }}</li>
          <li>数据根外的外部文件夹（如自选图片目录）不会被移动。</li>
        </ul>

        <div class="flex items-start gap-2 px-3 py-2.5 rounded-btn border border-red-200 bg-red-50 text-sm text-red-600">
          <Icon name="warning" :size="16" class="flex-shrink-0 mt-0.5" />
          <span>完整性校验通过后，旧位置的数据将被删除。请确认目标位置可靠。</span>
        </div>

        <label class="flex items-center gap-2 text-sm text-ink-primary cursor-pointer select-none">
          <input v-model="ack" type="checkbox" class="w-4 h-4 accent-brand-600" />
          我已了解上述影响
        </label>

        <div v-if="startError" class="text-sm text-red-600">{{ startError }}</div>

        <div class="flex justify-end gap-2 pt-1">
          <button @click="step = 'select'" class="px-4 py-2 bg-white border border-surface-border hover:bg-surface-hover rounded-btn text-sm text-ink-secondary transition-colors">上一步</button>
          <button
            @click="startMigration"
            :disabled="!ack || starting"
            class="px-4 py-2 bg-brand-700 hover:bg-brand-800 text-white rounded-btn text-sm font-semibold inline-flex items-center gap-1.5 transition-colors disabled:opacity-50 disabled:hover:bg-brand-700"
          >
            <Icon v-if="starting" name="spinner" :size="14" spin /> 开始迁移
          </button>
        </div>
      </div>

      <!-- ③ 进度 -->
      <div v-else-if="step === 'progress'" class="px-5 py-4 space-y-4">
        <div class="flex items-center justify-between">
          <div v-for="(s, i) in STAGES" :key="s.key" class="flex items-center gap-1.5">
            <Icon
              v-if="i < stageIndex"
              name="check-circle"
              :size="16"
              class="text-brand-600"
            />
            <span
              v-else
              class="w-4 h-4 rounded-full border flex-shrink-0"
              :class="i === stageIndex ? 'border-brand-500 bg-brand-100' : 'border-surface-border bg-white'"
            ></span>
            <span class="text-xs" :class="i <= stageIndex ? 'text-ink-primary font-medium' : 'text-ink-tertiary'">{{ s.label }}</span>
            <Icon v-if="i < STAGES.length - 1" name="chevron-right" :size="12" class="text-ink-tertiary mx-0.5" />
          </div>
        </div>

        <div>
          <div class="flex justify-between text-xs text-ink-secondary mb-1 font-numeric">
            <span>总进度</span>
            <span>{{ (mig?.progress || 0).toFixed(0) }}%</span>
          </div>
          <div class="h-2 bg-surface-hover rounded-full overflow-hidden">
            <div class="h-full bg-brand-500 rounded-full transition-all duration-200" :style="{ width: (mig?.progress || 0) + '%' }"></div>
          </div>
        </div>

        <div class="grid grid-cols-2 gap-3 text-xs">
          <div class="bg-surface-bg rounded-btn px-3 py-2">
            <div class="text-ink-tertiary mb-0.5">文件</div>
            <div class="text-ink-primary font-numeric font-medium">{{ mig?.copied_files || 0 }} / {{ mig?.total_files || 0 }}</div>
            <div class="h-1 bg-surface-hover rounded-full overflow-hidden mt-1.5">
              <div class="h-full bg-brand-400 rounded-full" :style="{ width: filePercent + '%' }"></div>
            </div>
          </div>
          <div class="bg-surface-bg rounded-btn px-3 py-2">
            <div class="text-ink-tertiary mb-0.5">数据量</div>
            <div class="text-ink-primary font-numeric font-medium">{{ fmtBytes(mig?.copied_bytes || 0) }} / {{ fmtBytes(mig?.total_bytes || 0) }}</div>
            <div class="h-1 bg-surface-hover rounded-full overflow-hidden mt-1.5">
              <div class="h-full bg-brand-400 rounded-full" :style="{ width: bytePercent + '%' }"></div>
            </div>
          </div>
          <div class="bg-surface-bg rounded-btn px-3 py-2">
            <div class="text-ink-tertiary mb-0.5">速率</div>
            <div class="text-ink-primary font-numeric font-medium">{{ fmtBytes(mig?.speed_bps || 0) }}/s</div>
          </div>
          <div class="bg-surface-bg rounded-btn px-3 py-2">
            <div class="text-ink-tertiary mb-0.5">已用时间</div>
            <div class="text-ink-primary font-numeric font-medium">{{ fmtDuration(mig?.elapsed_s) }}</div>
          </div>
        </div>

        <div v-if="mig?.current_file" class="text-xs text-ink-tertiary truncate font-mono" :title="mig.current_file">
          {{ mig.current_file }}
        </div>

        <div v-if="!confirmCancel" class="flex justify-end pt-1">
          <button @click="confirmCancel = true" class="px-4 py-2 bg-white border border-surface-border hover:bg-surface-hover rounded-btn text-sm text-ink-secondary transition-colors">取消迁移</button>
        </div>
        <div v-else class="flex items-center justify-between gap-2 px-3 py-2.5 rounded-btn border border-amber-200 bg-amber-50">
          <span class="text-xs text-amber-700">取消后当前数据完好，可稍后恢复迁移。确定取消？</span>
          <div class="flex gap-2 flex-shrink-0">
            <button @click="confirmCancel = false" class="px-3 py-1.5 text-xs text-ink-secondary hover:underline">继续迁移</button>
            <button @click="doCancel" class="px-3 py-1.5 bg-white border border-amber-300 rounded-btn text-xs text-amber-700 font-medium hover:bg-amber-100 transition-colors">确定取消</button>
          </div>
        </div>
      </div>

      <!-- ④ 结果 -->
      <div v-else class="px-5 py-4 space-y-4">
        <!-- 成功 -->
        <template v-if="isSuccess">
          <div class="flex items-start gap-3">
            <Icon :name="residual.length ? 'warning' : 'check-circle'" :size="22" :class="residual.length ? 'text-amber-500' : 'text-brand-600'" class="flex-shrink-0 mt-0.5" />
            <div>
              <div class="font-semibold text-ink-primary">
                {{ residual.length ? '迁移完成，部分旧文件未能删除' : '迁移完成，完整性校验通过' }}
              </div>
              <div class="text-sm text-ink-secondary mt-1 font-numeric">
                {{ mig?.total_files || 0 }} 个文件 · {{ fmtBytes(mig?.total_bytes || 0) }} · 耗时 {{ fmtDuration(mig?.elapsed_s) }}
              </div>
            </div>
          </div>

          <div v-if="residual.length" class="space-y-2">
            <div class="max-h-32 overflow-y-auto border border-surface-border rounded-btn px-3 py-2 space-y-1">
              <div v-for="(r, i) in residual" :key="i" class="text-xs text-ink-secondary font-mono truncate" :title="r.path">{{ r.path }}</div>
            </div>
            <button
              @click="retryCleanup"
              :disabled="cleaning"
              class="px-3 py-1.5 bg-white border border-surface-border hover:bg-surface-hover rounded-btn text-xs text-ink-secondary inline-flex items-center gap-1.5 transition-colors disabled:opacity-50"
            >
              <Icon name="refresh" :size="13" /> {{ cleaning ? '清理中…' : '重试清理' }}
            </button>
          </div>

          <div v-if="restarting" class="flex items-center gap-2 text-sm text-brand-700">
            <Icon name="spinner" :size="15" spin /> 正在重启服务，请稍候…
          </div>
          <div v-else-if="isDesktop()" class="flex justify-end">
            <button @click="restartNow" class="px-4 py-2 bg-brand-700 hover:bg-brand-800 text-white rounded-btn text-sm font-semibold transition-colors">立即重启服务</button>
          </div>
          <div v-else class="bg-surface-bg rounded-btn px-3 py-2.5 text-sm text-ink-secondary space-y-2">
            <p>新数据位置将在重启后端服务后生效：停止当前服务，重新运行 <span class="font-mono text-xs">.\start.ps1</span>（或 <span class="font-mono text-xs">python -m backend.app</span>）。</p>
            <button @click="reloadPage" class="px-3 py-1.5 bg-white border border-surface-border hover:bg-surface-hover rounded-btn text-xs text-ink-secondary transition-colors">重启后刷新页面</button>
          </div>
        </template>

        <!-- 失败 -->
        <template v-else-if="mig?.status === 'failed'">
          <div class="flex items-start gap-3">
            <Icon name="x-circle" :size="22" class="text-red-500 flex-shrink-0 mt-0.5" />
            <div>
              <div class="font-semibold text-ink-primary">迁移失败</div>
              <div class="text-sm text-red-600 mt-1">{{ mig?.error }}</div>
              <div class="text-xs text-ink-tertiary mt-1">旧位置数据完好无损，可重试或放弃。</div>
            </div>
          </div>
          <div v-if="issueDetails.length">
            <button @click="showDetails = !showDetails" class="text-xs text-brand-700 hover:underline">
              {{ showDetails ? '收起明细' : `查看明细（${issueDetails.length}）` }}
            </button>
            <div v-if="showDetails" class="max-h-32 overflow-y-auto border border-surface-border rounded-btn px-3 py-2 space-y-1 mt-1.5">
              <div v-for="(d, i) in issueDetails" :key="i" class="text-xs text-ink-secondary font-mono truncate" :title="d.path">
                {{ d.path }} — {{ d.reason || d.error }}
              </div>
            </div>
          </div>
          <div v-if="startError" class="text-sm text-red-600">{{ startError }}</div>
          <div class="flex justify-end gap-2">
            <button @click="rollback" class="px-4 py-2 bg-white border border-surface-border hover:bg-surface-hover rounded-btn text-sm text-red-600 transition-colors">放弃并清理</button>
            <button @click="retry" class="px-4 py-2 bg-brand-700 hover:bg-brand-800 text-white rounded-btn text-sm font-semibold transition-colors">重试迁移</button>
          </div>
        </template>

        <!-- 已取消 -->
        <template v-else>
          <div class="flex items-start gap-3">
            <Icon name="info" :size="22" class="text-ink-tertiary flex-shrink-0 mt-0.5" />
            <div>
              <div class="font-semibold text-ink-primary">迁移已取消</div>
              <div class="text-sm text-ink-secondary mt-1">当前数据完好无损，目标位置的半成品可继续迁移或清除。</div>
            </div>
          </div>
          <div v-if="startError" class="text-sm text-red-600">{{ startError }}</div>
          <div class="flex justify-end gap-2">
            <button @click="rollback" class="px-4 py-2 bg-white border border-surface-border hover:bg-surface-hover rounded-btn text-sm text-red-600 transition-colors">放弃并清理</button>
            <button @click="resume" class="px-4 py-2 bg-brand-700 hover:bg-brand-800 text-white rounded-btn text-sm font-semibold transition-colors">继续迁移</button>
          </div>
        </template>
      </div>
    </div>
  </div>
</template>