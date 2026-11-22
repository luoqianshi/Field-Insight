// 桌面态（Electron）经 preload 桥调用 OS 原生文件夹对话框；
// Web 态无 window.tjzk.pickFolder，返回 null 由调用方回退后端通道。
export interface NativePickResult {
  cancelled: boolean
  path: string | null
}

interface TjzkBridge {
  pickFolder?: () => Promise<NativePickResult>
  restartBackend?: () => Promise<{ success: boolean; message?: string }>
}

export async function nativePickFolder(): Promise<NativePickResult | null> {
  const tjzk = (window as unknown as { tjzk?: TjzkBridge }).tjzk
  if (!tjzk?.pickFolder) return null
  return tjzk.pickFolder()
}

// 桌面态判定：preload 桥存在即为 Electron 壳
export function isDesktop(): boolean {
  return typeof (window as unknown as { tjzk?: TjzkBridge }).tjzk?.pickFolder === 'function'
}

// 存储迁移完成后重启后端（桌面态）；Web 态返回 null 由调用方展示手动重启指引
export async function nativeRestartBackend(): Promise<{ success: boolean; message?: string } | null> {
  const tjzk = (window as unknown as { tjzk?: TjzkBridge }).tjzk
  if (!tjzk?.restartBackend) return null
  return tjzk.restartBackend()
}