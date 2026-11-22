import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import {
  settingsApi,
  type StorageOverview,
  type MigrationStatus,
  type PrecheckReport,
  type AboutInfo,
} from '@/api/settings'

const TERMINAL = ['completed', 'completed_with_warnings', 'failed', 'cancelled', 'rolled_back']

export function isTerminal(status?: string): boolean {
  return !!status && TERMINAL.includes(status)
}

export const useSettingsStore = defineStore('settings', () => {
  const storage = ref<StorageOverview | null>(null)
  const about = ref<AboutInfo | null>(null)
  const migration = ref<MigrationStatus | null>(null)
  const loading = ref(false)
  const error = ref('')
  let timer: number | null = null

  const migrating = computed(() => migration.value?.status === 'running')
  const pendingRestart = computed(() => storage.value?.pending_restart ?? false)

  async function fetchStorage() {
    loading.value = true
    error.value = ''
    try {
      const res = await settingsApi.storage()
      storage.value = res.data
    } catch (e: any) {
      error.value = e.message || '加载存储信息失败'
    } finally {
      loading.value = false
    }
  }

  async function fetchAbout() {
    try {
      const res = await settingsApi.about()
      about.value = res.data
    } catch {
      // 关于信息加载失败不阻断页面
    }
  }

  async function validate(target: string): Promise<PrecheckReport> {
    const res = await settingsApi.validate(target)
    return res.data
  }

  async function pollMigration(): Promise<MigrationStatus> {
    const res = await settingsApi.migration()
    migration.value = res.data
    return res.data
  }

  function startPolling() {
    stopPolling()
    timer = window.setInterval(async () => {
      try {
        const st = await pollMigration()
        if (st.status !== 'running') {
          stopPolling()
          await fetchStorage()
        }
      } catch {
        // 轮询瞬时错误忽略，下一轮重试
      }
    }, 1000)
  }

  function stopPolling() {
    if (timer !== null) {
      clearInterval(timer)
      timer = null
    }
  }

  async function startMigration(target: string) {
    const res = await settingsApi.migrate(target)
    await pollMigration()
    startPolling()
    return res.data.migration_id
  }

  async function cancelMigration() {
    await settingsApi.cancel()
  }

  async function resumeMigration() {
    const res = await settingsApi.resume()
    await pollMigration()
    startPolling()
    return res.data.migration_id
  }

  async function rollbackMigration() {
    const res = await settingsApi.rollback()
    migration.value = null
    await fetchStorage()
    return res.data
  }

  async function cleanupOld() {
    const res = await settingsApi.cleanupOld()
    if (migration.value) {
      migration.value.residual_files = res.data.residual_files
      if (res.data.residual_files.length === 0) {
        migration.value.status = 'completed'
      }
    }
    await fetchStorage()
    return res.data
  }

  async function resetDefault() {
    const res = await settingsApi.resetDefault()
    if (res.data.migration_id) {
      await pollMigration()
      startPolling()
    } else {
      await fetchStorage()
    }
    return res.data
  }

  return {
    storage,
    about,
    migration,
    loading,
    error,
    migrating,
    pendingRestart,
    fetchStorage,
    fetchAbout,
    validate,
    pollMigration,
    startPolling,
    stopPolling,
    startMigration,
    cancelMigration,
    resumeMigration,
    rollbackMigration,
    cleanupOld,
    resetDefault,
  }
})