import client from './client'
import { nativePickFolder } from './desktop'

// 设置模块 API（计划书 docs/sdd/plans/2026-11-20-settings-storage-migration.md §3.3）

export interface StorageModule {
  key: string
  label: string
  dir: string
  size_bytes: number
  file_count: number
}

export interface DiskInfo {
  total: number
  free: number
  used: number
}

export interface RecoveryInfo {
  migration_id: string
  source_root: string
  target_root: string
  phase: string
  status?: string
  started_at?: string
}

export interface StorageOverview {
  active_root: string
  configured_root: string | null
  default_root: string
  frozen: boolean
  is_custom: boolean
  pending_restart: boolean
  root_fallback_warning: string | null
  modules: StorageModule[]
  disk: DiskInfo
  recovery: RecoveryInfo | null
}

export interface PrecheckReport {
  ok: boolean
  errors: string[]
  warnings: string[]
  source_root: string
  target: string
  source_size_bytes: number
  source_file_count: number
  target_free_bytes: number
}

export interface MigrationFileIssue {
  path: string
  error?: string
  reason?: string
}

export interface MigrationStatus {
  migration_id?: string
  phase: string
  status: string
  progress: number
  copied_files: number
  total_files: number
  copied_bytes: number
  total_bytes: number
  speed_bps: number
  elapsed_s?: number
  current_file?: string
  error: string | null
  errors: MigrationFileIssue[]
  warnings: string[]
  residual_files: MigrationFileIssue[]
  verify_mismatches: MigrationFileIssue[]
  switched?: boolean
  source_root?: string
  target_root?: string
  completed_at?: number | null
}

export interface AboutInfo {
  app: string
  version: string | null
  mode: string
  data_root: string
  python: string
}

export const settingsApi = {
  storage: () => client.get<unknown, { data: StorageOverview }>('/settings/storage'),

  pending: () =>
    client.get<unknown, { data: { pending_restart: boolean; root_fallback_warning: string | null } }>(
      '/settings/storage/pending',
    ),

  validate: (target: string) =>
    client.post<unknown, { data: PrecheckReport }>('/settings/storage/validate', { target }),

  migrate: (target: string) =>
    client.post<unknown, { data: { migration_id: string } }>('/settings/storage/migrate', { target }),

  migration: () => client.get<unknown, { data: MigrationStatus }>('/settings/storage/migration'),

  cancel: () => client.post<unknown, { data: null }>('/settings/storage/migration/cancel', {}),

  resume: () =>
    client.post<unknown, { data: { migration_id: string } }>('/settings/storage/migration/resume', {}),

  rollback: () =>
    client.post<unknown, { data: { residual_files: MigrationFileIssue[] } }>(
      '/settings/storage/migration/rollback',
      {},
    ),

  cleanupOld: () =>
    client.post<unknown, { data: { residual_files: MigrationFileIssue[] } }>(
      '/settings/storage/cleanup-old',
      {},
    ),

  resetDefault: () =>
    client.post<unknown, { data: { migration_id?: string; cleared_anchor?: boolean } }>(
      '/settings/storage/reset-default',
      {},
    ),

  about: () => client.get<unknown, { data: AboutInfo }>('/settings/about'),

  // 打开受管目录（key: root | data | output | datasets | results | models | config）
  openFolder: (key: string) =>
    client.post<unknown, { data: { path: string } }>('/settings/open-folder', { key }),

  // 桌面态原生桥优先，Web 态回退后端对话框（镜像 batches.pickFolder）
  pickFolder: async () => {
    const native = await nativePickFolder()
    if (native) return { data: { cancelled: native.cancelled, path: native.path ?? undefined } }
    return client.post<unknown, { data: { cancelled?: boolean; path?: string } }>(
      '/settings/pick-folder',
      {},
    )
  },
}