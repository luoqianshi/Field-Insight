// 桌面态（Electron）经 preload 桥调用 OS 原生文件夹对话框；
// Web 态无 window.tjzk.pickFolder，返回 null 由调用方回退后端通道。
export interface NativePickResult {
  cancelled: boolean
  path: string | null
}

interface TjzkBridge {
  pickFolder?: () => Promise<NativePickResult>
}

export async function nativePickFolder(): Promise<NativePickResult | null> {
  const tjzk = (window as unknown as { tjzk?: TjzkBridge }).tjzk
  if (!tjzk?.pickFolder) return null
  return tjzk.pickFolder()
}