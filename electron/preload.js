// 预加载脚本：暴露只读环境信息 + 原生文件夹选择桥，不开启 nodeIntegration
const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('tjzk', {
  platform: process.platform,
  versions: {
    electron: process.versions.electron,
    chrome: process.versions.chrome,
    node: process.versions.node,
  },
  // 桌面态目录选择：主进程 dialog.showOpenDialog，返回 { cancelled, path }
  pickFolder: () => ipcRenderer.invoke('tjzk:pick-folder'),
  // 存储迁移后重启后端：主进程杀旧进程树并重新拉起，按新端口重载原路由
  restartBackend: () => ipcRenderer.invoke('tjzk:restart-backend'),
});
