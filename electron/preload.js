// 预加载脚本：仅暴露只读环境信息，不开启 nodeIntegration
const { contextBridge } = require('electron');

contextBridge.exposeInMainWorld('tjzk', {
  platform: process.platform,
  versions: {
    electron: process.versions.electron,
    chrome: process.versions.chrome,
    node: process.versions.node,
  },
});
