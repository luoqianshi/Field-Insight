# 桌面端构建与安装包说明（Windows）

> 适用版本：**v1.1.0**（含「设置」模块）｜构建日期：2026-11-23｜形态：Electron + 冻结 Flask 后端
> 本文覆盖：交付产物、安装/卸载、构建环境、重建步骤、验证结果、已知问题与排错。

---

## 一、交付产物

| 产物 | 路径 | 体积 | 说明 |
|---|---|---|---|
| **安装包（交付物）** | `electron/dist/TianJianZhiKan-v1.1.0-win-x64-setup.exe` | 382,819,214 B（365.1 MiB） | NSIS 向导式安装程序，当前用户级安装、无需管理员 |
| SHA256 | 同上 | — | `E4F4C92DE69211AD54EF155236A61ABD51C6F9610706A22E574EF08DEAC759DA` |
| 免安装目录（原材料） | `electron/dist/win-unpacked/` | 1,119.3 MB / 3,452 文件 | 双击 `TianJianZhiKan.exe` 可直接运行 |
| 冻结后端载荷 | `electron/backend-dist/TianJianZhiKanBackend/` | 851.3 MB / 3,379 文件 | 由 PyInstaller onedir 生成，被打入安装包 |

产物目录 `electron/dist/`、`electron/backend-dist/` 均被 gitignore，不随仓库分发。

---

## 二、安装与卸载

### 安装（向导式）
1. 双击 `TianJianZhiKan-v1.1.0-win-x64-setup.exe`。
2. 默认安装目录：`%LOCALAPPDATA%\Programs\TianJianZhiKan`；安装向导允许**自定义安装目录**。
3. 自动创建**桌面快捷方式**与**开始菜单快捷方式**（名称「田间智瞰」）。
4. 安装完成后勾选「运行田间智瞰」可直接启动；窗口默认 1440×900、按显示器工作区自适应并居中，支持最大化、拖拽缩放与 **F11 全屏切换**。

### 卸载
- 入口：Windows「设置 → 应用 → 田间智瞰 → 卸载」，或安装目录下 `Uninstall TianJianZhiKan.exe`。
- 卸载仅移除程序文件、快捷方式与注册表项；**业务数据保留**（`deleteAppDataOnUninstall: false`）。

### 数据位置
- 可写数据根固定为 `%LOCALAPPDATA%\TianJianZhiKan`（与安装位置解耦），含 `data/output/datasets/results/models/config/logs`。
- 可在「设置 → 数据存储 → 更改位置」整体迁移到其他磁盘；迁移完成后自动重启后端生效。
- **严禁手动删除** `%LOCALAPPDATA%\TianJianZhiKan`（除非确认不再需要历史数据）。

### 未签名提示
安装包未做代码签名，Windows SmartScreen 可能提示「未知发布者」。点击「更多信息 → 仍要运行」即可。

---

## 三、构建环境

| 组件 | 版本 / 位置 |
|---|---|
| 操作系统 | Windows 10/11 x64 |
| Node.js | 18+（本机 nvm4w，npm 可用） |
| 前端依赖 | `frontend/`（Vue 3 + Vite + Tailwind + Pinia，`npm install`） |
| 冻结后端 Python | `C:\Users\lqs\tjzk-build-venv\Scripts\python.exe`（Python 3.8.20） |
| PyInstaller | 6.22.3 |
| torch / torchvision / torchaudio | 2.1.0+cpu / 0.16.1+cpu / 2.1.0+cpu（**必须 CPU 版**，CUDA 版载荷约 4.2GB 不可分发） |
| Electron / electron-builder | 33.4.11 / 25.1.8 |
| 打包工具缓存 | `%LOCALAPPDATA%\electron-builder\Cache`（NSIS、winCodeSign 已缓存，可离线复用） |

构建 venv 重建方式（若环境丢失）：

```powershell
C:\Users\lqs\.conda\envs\uav-vis\python.exe -m venv --system-site-packages C:\Users\lqs\tjzk-build-venv
C:\Users\lqs\tjzk-build-venv\Scripts\pip install pyinstaller==6.22.3 `
  torch==2.1.0+cpu torchvision==0.16.1+cpu torchaudio==2.1.0+cpu `
  --extra-index-url https://download.pytorch.org/whl/cpu
```

---

## 四、重建步骤（顺序执行）

```powershell
# 1. 前端构建（含 vue-tsc 类型检查，产物 → backend/static/）
cd frontend
npm install
npm run build

# 2. 冻结后端载荷（PyInstaller onedir → electron/backend-dist/）
cd ..
powershell -NoProfile -ExecutionPolicy Bypass -File electron\build-backend.ps1 `
  -PythonExe "C:\Users\lqs\tjzk-build-venv\Scripts\python.exe"

# 3. 生成 NSIS 安装包（→ electron/dist/TianJianZhiKan-v{version}-win-x64-setup.exe）
cd electron
npm install
npm run build:installer

# 4. 可选：仅生成免安装目录（调试用）
npm run build:dir
```

前置条件：`backend/static/index.html` 必须存在（步骤 1 产物），否则步骤 2 会直接报错退出。

---

## 五、关键配置说明

- **版本单一来源**：`electron/package.json` 的 `version`（当前 `1.1.0`）。安装包名、exe 文件属性、健康检查与「设置 → 关于」均读取该值。
- **版本透传**：主进程以 `TJZK_APP_VERSION` 环境变量传给后端；`backend/config.py` 的 `APP_VERSION` 优先读环境变量，开发态回退读 `electron/package.json`。
- **NSIS 关键参数**（`electron/package.json > build.nsis`）：
  - `oneClick: false` + `allowToChangeInstallationDirectory: true`：向导式、可选安装目录。
  - `perMachine: false`：当前用户级安装，不触发 UAC。
  - `createDesktopShortcut` / `createStartMenuShortcut`：创建「田间智瞰」快捷方式。
  - `deleteAppDataOnUninstall: false`：卸载保留业务数据。
  - `artifactName`：`TianJianZhiKan-v${version}-win-x64-setup.${ext}`。
- **载荷打包**：`extraResources` 将 `backend-dist/TianJianZhiKanBackend` 拷贝为 `resources/backend`；主进程按「打包态 `resources/backend` → 开发态 `electron/backend-dist`」两级查找后端 exe。
- **双根配置**：`backend/config.py` 以 `FROZEN` 门控，冻结态可写根固定 `%LOCALAPPDATA%\TianJianZhiKan`，只读资源走 `_MEIPASS`。
- **桌面桥**：`preload.js` 暴露 `tjzk.pickFolder`（原生目录选择）与 `tjzk.restartBackend`（迁移后重启后端），`contextIsolation` 开启、`nodeIntegration` 关闭。

---

## 六、本次验证结果（v1.1.0 实测）

| 验证项 | 方式 | 结果 |
|---|---|---|
| 后端全量测试 | `backend: python -m pytest -q` | **168 passed**（含设置/迁移 37 项） |
| 前端构建 | `npm run build`（vue-tsc + vite） | 通过，产物写入 `backend/static` |
| 开发态冒烟 | `electron: npm run smoke` | 后端 3.0s 就绪、窗口 3.2s 可见、单图推理成功 |
| 冻结后端 API | 直接启动打包后端，逐模块调用 | health/models/batches/processing/datasets/counting/settings 全部 200；SPA 深路径与静态资源 200 |
| 全页面 UI 巡检 | 1366×768 浏览器驱动打包后端 | 首页、数据管理、数据处理、数据集、算法广场（含检测/计数/注册）、设置均正常渲染，无 console error |
| 最小窗口布局 | 1024×620 视口 | 设置页单列布局，`scrollWidth == clientWidth`，无横向溢出 |
| 设置读取 | 打包后端 `/api/settings/storage`、`/about` | 数据根、六模块占用、磁盘、版本 1.1.0 正确 |
| 设置预检 | 输入嵌套路径 | 正确返回「目标不能位于当前数据目录内部」等错误并阻断下一步 |
| 迁移生效链路 | 隔离沙箱 `LOCALAPPDATA` 下执行迁移 | 迁移 completed（3/3 文件）、锚点写入、旧数据清理；**重启后自定义根生效** |
| 迁回默认 | 沙箱内 `reset-default` + 重启 | 回到默认根，探针文件完整恢复 |
| 静默安装 | `setup.exe /S /D=<自定义目录>` | 退出码 0，耗时 29.6s，文件与卸载器齐全 |
| 快捷方式/注册表 | 安装后检查 | 桌面「田间智瞰.lnk」、开始菜单快捷方式、卸载注册表项均存在，显示版本 1.1.0 |
| 安装版冒烟 | 安装目录 exe `--smoke` | health `v1.1.0`、11 个模型、单图推理成功（3.06s）、Electron 308MB + 后端 390MB |
| 窗口与全屏 | Win32 实测窗口矩形 | 默认 1440×900 居中；F11 → 1920×1080 全屏；再按 F11 恢复 1440×900 |
| 退出回收 | 关闭主窗口 | 优雅退出，无残留后端进程 |
| 卸载 | `Uninstall TianJianZhiKan.exe /S` | 快捷方式与注册表项清除，业务数据目录保留（22 个文件） |

---

## 七、已知问题与限制

1. **未代码签名**：SmartScreen 提示「未知发布者」属预期，需在分发说明中写明绕过方式。
2. **体积**：安装包约 365 MiB，安装后约 1.1 GB（Electron 运行时 + CPU 版 torch）；首次启动后端就绪约 2.6–3.0 秒。
3. **仅 CPU 推理**：为保证可分发体积，发行版不含 CUDA；大批量推理速度低于 GPU 开发环境。
4. **空目录残留**：个别环境下静默卸载可能留下空的安装目录（文件已全部删除），不影响使用，可手动删除。
5. **智能提示语言**：安装向导固定简体中文（LCID 2052）。

---

## 八、故障排查

| 现象 | 处理 |
|---|---|
| `PythonExe 不存在` | 按第三节重建构建 venv，并用 `-PythonExe` 显式传入 |
| `缺少 backend/static/index.html` | 先执行 `cd frontend; npm run build` |
| 打包失败于 rcedit / 写图标 | Windows Defender 实时扫描会短暂锁 exe；重试构建（必要时临时关闭实时保护） |
| 启动报「找不到后端可执行文件」 | 确认 `electron/backend-dist/TianJianZhiKanBackend/TianJianZhiKanBackend.exe` 存在后重新执行步骤 3 |
| 启动报「后端 60 秒内未就绪」 | 查看 `%LOCALAPPDATA%\TianJianZhiKan\logs\backend-stdout.log` 与安装目录下后端 exe 是否被杀软隔离 |
| 设置页提示自定义位置不可达 | 确认目标磁盘已连接后重启应用；或在设置页「恢复默认位置」 |
| 迁移后配置未生效 | 设置页点击「立即重启」；桌面态会由主进程重启后端并重载当前路由 |

---

## 九、日志与验证记录

- PyInstaller 构建日志：`.lqs/build-backend-final.log`
- 安装包构建日志：`%TEMP%\tjzk-installer-build.log`
- 开发态冒烟：`%TEMP%\tjzk-smoke-dev.json`；安装版冒烟：`%TEMP%\tjzk-smoke-installed.json`
- 安装版主进程日志：`%TEMP%\tjzk-main-installed.log`、`%TEMP%\tjzk-main-gui.log`
- 最小窗口布局截图：`.lqs/2026-11-23/desktop-installer-test/outputs/`