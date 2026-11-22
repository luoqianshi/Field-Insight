# 设置模块开发计划书 —— 数据存储位置自定义与安全迁移

> 项目：田间智瞰（UAV 大田农作物智能监测系统）
> 日期：2026-11-20 ｜ 状态：已批准（2026-11-20） ｜ 版本目标：v1.1.0

---

## 0. 摘要（Summary）

在侧边栏新增「设置」模块，首批（P0）实现**数据存储位置自定义**：用户可将统一数据根目录从默认位置（桌面态 `%LOCALAPPDATA%\TianJianZhiKan`，C 盘）迁移至任意磁盘分区。迁移遵循「**完整复制 → 完整性校验 → 切换配置 → 删除旧数据**」的安全流水线，全程进度可视、异常可恢复、数据零丢失。UI 完全沿用现有 Emerald 浅色设计体系，不改动原有风格。桌面态（Electron）与 Web 态均支持，桌面态迁移后自动重启后端，Web 态引导手动重启。

**已确认的关键决策（用户拍板）：**
1. 路径粒度：**统一数据根目录**（六模块目录整体迁移，设置页按模块展示子目录占用）。
2. 适用形态：**桌面 + Web 均支持**（默认行为不变，无自定义配置时仍锚定原位置）。

**本任务交付物 = 本计划书文档**（已归档至 `docs/sdd/plans/` 并记录 `LOG.md`），不含代码实现；代码实现按本计划书第七节阶段划分另行执行。

---

## 1. 现状分析（Current State Analysis）

### 1.1 存储架构（问题根源）

- `backend/config.py` L12-29：`FROZEN = sys.frozen` 门控双根。
  - `RESOURCE_ROOT`：只读资源（`backend/static`、config 模板、内置权重），冻结态为 PyInstaller `_MEIPASS`。
  - `PROJECT_ROOT`：可写数据根。**冻结态固定 `%LOCALAPPDATA%\TianJianZhiKan`（C 盘）**；非冻结态为仓库根。
- L31-80：由 `PROJECT_ROOT` 派生六个运行目录并在**导入时** `mkdir`：
  | 目录 | 常量 | 内容 | 体积特征 |
  |---|---|---|---|
  | `data/` | `DATA_DIR` | `batches.yaml`、`processing_tasks.yaml`、架次图片文件夹 | 大（GB 级） |
  | `output/` | `OUTPUT_DIR` | 处理产物（按 task_id 子目录） | 大 |
  | `datasets/` | `DATASETS_DIR` | `datasets.yaml` + 数据集文件 | 大 |
  | `results/` | `RESULTS_DIR` | 计数结果（`meta.json`/`counting_data.json`/标注图） | 中 |
  | `models/` | `MODELS_DIR` | 用户注册/下载的模型权重 | 大（百 MB 级） |
  | `config/` | `CONFIG_DIR` | `models.yaml` 模型注册表 | 小（KB 级） |
- **所有后端模块在导入时捕获路径常量**（`batch_registry.py`、`processing_registry.py`、`dataset_registry.py`、`result_store.py`、`engine.py`、各 API 均 `from config import XXX_DIR`）→ 运行期热切换路径不可行，**必须「迁移 + 重启后端」生效**。
- 冻结态首启播种：`RESOURCE_ROOT/config/models.yaml` → `CONFIG_DIR/models.yaml`（仅缺失时，L64-70）。

### 1.2 路径引用关系（迁移必须处理）

- `batch_registry.py` L475-486：`_resolve_path` 相对路径相对 `PROJECT_ROOT` 解析；`_to_rel` 优先存相对路径，根外路径存绝对。`processing_registry.py` L297 同模式。
- 结论：迁移后**相对路径引用天然兼容**；**指向旧根内部的绝对路径必须重写**；**指向数据根外部的外部文件夹（用户自选图片目录）绝不移动、绝不改写**。
- 需重写的载体：`data/batches.yaml`（`image_folder_path`）、`data/processing_tasks.yaml`（输入/输出路径）、`datasets/datasets.yaml`（数据集路径）、`results/*/meta.json` 与 `counting_data.json`（可能内嵌源图绝对路径）。

### 1.3 可复用基建

- **异步任务模式**：`core/task_manager.py`（ThreadPoolExecutor(1) + 内存任务表 + `update(progress=...)`），`processing_api.py` L96-121 提交/轮询模式 → 迁移引擎镜像该模式。
- **目录选择**：桌面态 `electron/preload.js` 暴露 `window.tjzk.pickFolder` → `main.js` L226 `tjzk:pick-folder`（原生对话框）；Web 态回退 `POST /api/batches/pick-folder`（`batches_api.py` L184-196，tkinter `filedialog`）。前端封装见 `api/desktop.ts`、`api/batches.ts` L94-98。
- **进程编排**：`electron/main.js` L50-111：spawn 后端 exe `--port 0` → 解析 `BACKEND_PORT`/`BACKEND_READY` → `killBackendTree`（stdin 看门狗 + `taskkill /T /F`）→ 可扩展「重启后端」IPC。
- **UI 体系**：`tailwind.config.js` 设计令牌（brand Emerald 50-900、ink primary/secondary/tertiary、surface bg/border/hover、rounded-card=10px/btn=8px、shadow-card）；`Icon.vue` 已有 `gear`/`folder`/`folder-open`/`arrow-right`/`chevron-*` 等 SVG 图标（stroke-width=1.5）；`Sidebar.vue` navItems 数组 + `isActive(section)` 路由匹配；现有删除确认用原生 `confirm()`（`Batches.vue` L79）。
- **测试基建**：`backend/conftest.py` 对 config 做 tmp 隔离；pytest 全量在 `backend/` 下执行；`electron/npm run smoke` 冒烟（health/models/单图推理）。

### 1.4 硬约束（来自 AGENTS.md / 项目记忆）

- 不修改 `backend/api/` 既有路由文件签名；新接口走新文件/新 Blueprint。
- 非冻结态默认行为必须与 Web 开发一致（锚定仓库根）；新增运行目录走 config 常量。
- 冻结态可写数据根与安装位置解耦；**严禁整目录删除 `%LOCALAPPDATA%\TianJianZhiKan`**（锚点文件留守）。
- 仓库根 `config/` 为 **git 跟踪的模板目录**（非冻结态 RESOURCE_ROOT == PROJECT_ROOT）→ Web 态迁移必须排除 `config/`（见 4.2 决策 D5）。
- 单文件失败只做错误隔离，不中断整批；清理不得强杀开发进程、被占用文件报告并跳过。
- 前端浅色 Emerald 主题、Gradio 风极简；禁玻璃拟态/霓虹/脉冲动画；过渡 ≤200ms。
- 发布仅 Windows zip；版本单一来源 `electron/package.json`（当前 1.0.0）；未签名 SmartScreen 提示属预期。
- `.gitignore` 运行目录根锚定（R-FS-02）；任务完成追加 `LOG.md` 一行。

---

## 2. 功能清单（完整梳理）

### 2.1 P0 —— 首批实现（存储位置自定义，本计划书核心）

| ID | 功能点 | 说明 |
|---|---|---|
| F01 | 设置入口 | 侧边栏 navItems 末位新增「设置」（gear 图标），路由 `/settings`，折叠态图标模式自动兼容 |
| F02 | 存储概览 | 当前数据根路径、自定义/默认徽标；六模块目录卡片（路径、占用大小、文件数）；所在磁盘容量/剩余空间条 |
| F03 | 更改数据位置 | 目录选择：桌面态原生对话框（`tjzk.pickFolder`）；Web 态后端对话框回退 + 手动输入绝对路径 |
| F04 | 目标预检 | 可写性探测、剩余空间 ≥ 源大小×1.1+100MB、禁嵌套（目标在源内/源在目标内/同路径）、禁系统目录、运行中任务检查；预检报告可视化 |
| F05 | 迁移确认 | 应用内确认弹窗：源→目标、总大小/文件数、影响说明（迁移期间暂停其他操作、完成后重启服务）、红色警示「校验通过后旧数据将被删除」；勾选确认制（见 5.2） |
| F06 | 迁移进度 | 阶段指示（复制→校验→切换→清理）+ 文件数/字节双进度条 + 实时速率 + 已用时间 + 取消按钮；1s 轮询 |
| F07 | 完整性校验 | 文件清单一致性 + 逐文件 size + SHA-256 全量哈希比对；校验结果（通过/失败明细）展示 |
| F08 | 旧数据清理 | 校验通过并切换后自动删除旧根下受管目录；被占用文件错误隔离、残留清单展示 + 「重试清理」入口 |
| F09 | 异常提示 | 错误矩阵（空间不足/权限拒绝/文件占用/校验失败/目标丢失/锚点损坏）→ 友好文案 + 恢复引导（见 5.4） |
| F10 | 中断恢复 | 启动时检测未完成迁移（锚点目录 `migration_pending.json` + 目标 `.tjzk_migration.json`）→ 恢复卡片：继续迁移 / 放弃并清理半成品 |
| F11 | 恢复默认位置 | 一键迁回默认根（复用同一迁移流水线，方向相反） |
| F12 | 重启衔接 | 桌面态：迁移完成 → 自动重启后端并重载页面（保留当前路由）；Web 态：完成面板 + 手动重启指引 + 「新路径待重启生效」全局横幅（`pending_restart`） |
| F13 | 配置根丢失回退 | 启动时自定义根不可达（盘符拔出）→ 回退默认根并记录警告；设置页警示 + 「重试连接 / 重置为默认」 |
| F14 | 关于信息（轻量） | 版本号、运行形态（桌面/Web）、当前数据根、构建信息；为后续设置项预留分区结构 |

### 2.2 P1 —— 第二批（存储增强，本期仅预留不实现）

| ID | 功能点 | 说明 |
|---|---|---|
| F15 | 各模块独立路径 | 配置模型预留 `module_overrides` 字段；开放 data/output/datasets/results/models 独立根（需重构相对路径解析，风险高，单独评审） |
| F16 | 存储占用分析 | 按模块/架次/任务维度的占用排行与图表，辅助清理决策 |
| F17 | 迁移历史日志 | 历次迁移记录（时间、源/目标、大小、结果）持久化与查看 |
| F18 | 残留清理工具 | 历次迁移旧根残留的统一扫描与清理 |

### 2.3 P2 —— 远期（设置模块完整版图）

| ID | 功能点 |
|---|---|
| F19 | 数据处理默认参数（CLAHE/裁剪默认值、并发与缓存策略） |
| F20 | 模型管理设置（权重缓存清理、注册目录快捷入口） |
| F21 | 日志级别与导出、诊断信息打包 |
| F22 | 设置导入/导出（YAML 备份恢复） |
| F23 | 关于与更新检查（版本说明、GitHub Release 链接） |

---

## 3. 总体技术方案

### 3.1 配置锚点与生效机制

**锚点文件（永不随数据迁移，KB 级）：**
- 冻结态：`%LOCALAPPDATA%\TianJianZhiKan\settings.yaml`（默认根留守，仅存锚点）。
- 非冻结态：`<仓库根>/settings.local.yaml`（新增 `.gitignore` 根锚定条目 `/settings.local.yaml`）。

```yaml
# settings.yaml / settings.local.yaml
data_root: "D:\\TJZKData"     # 绝对路径；缺失/空 = 使用默认根
updated_at: "2026-11-20T12:00:00+08:00"
# module_overrides: {}        # P1 预留，本期不读取
```

**config.py 改造（唯一入口，下游常量派生逻辑不变）：**
1. `_user_root()` 先算默认根（现逻辑），再读锚点 `data_root`：合法绝对路径且目录可达 → 采用；否则回退默认根并记录 `ROOT_FALLBACK_WARNING`（模块级变量，供 API 暴露）。
2. 新增 `ACTIVE_ROOT`（本进程启动时实际生效根）与 `DEFAULT_ROOT`（默认根）常量；`configured_root ≠ ACTIVE_ROOT` 或锚点已写但进程未重启 → API 报告 `pending_restart`。
3. `CONFIG_DIR` 特例（D5）：冻结态随根迁移；非冻结态恒为 `<仓库根>/config`（git 跟踪模板，不迁移）。
4. 导入时 `mkdir` 与冻结播种逻辑保持不变（作用于生效根）。
5. 锚点损坏（YAML 解析失败）→ 回退默认根 + 警告，不崩溃。

**生效方式：重启后端。** 不做运行期热切换（所有模块导入时捕获常量，热切换需全量重构，风险不可控）。

### 3.2 迁移引擎状态机

```
idle → precheck → copying → verifying → rewriting → switching → cleaning → completed
                     │           │           │           │          │
                     └───────────┴───────────┴───────────┘          └→ completed_with_warnings
                          任一阶段失败/取消 → failed / cancelled        （残留报告，可重试清理）
                          进程中断 → interrupted（启动时恢复卡片）
```

- **switching 之前**：源数据始终完整，失败/取消/中断 = 安全态（目标半成品可续传或清除）。
- **switching**：原子写锚点（临时文件 + `os.replace`）。此后目标即权威数据。
- **cleaning**：删除旧根受管目录；失败不回滚锚点（目标已验证有效），转 `completed_with_warnings`。
- **并发防护（v1）**：precheck 拒绝存在 running/pending 处理任务（`engine.get_processing_task_manager().list()`）；迁移期间前端全屏进度遮罩 + 路由离开守卫 + `beforeunload` 警示；设置 API 拒绝并发迁移（409）。不改既有路由文件内部逻辑（残留风险见 §9 假设 A6）。

### 3.3 新增 API（新文件 `backend/api/settings_api.py`，Blueprint `settings_bp`，统一响应信封）

| 端点 | 方法 | 说明 |
|---|---|---|
| `/api/settings/storage` | GET | 存储概览：`active_root/configured_root/default_root/frozen/pending_restart/root_fallback_warning/modules[{key,label,dir,size_bytes,file_count}]/disk{total,free}/recovery` |
| `/api/settings/storage/validate` | POST | 目标预检 `{target}` → `{ok, errors[], warnings[], source_size_bytes, source_file_count, target_free_bytes}` |
| `/api/settings/storage/migrate` | POST | 启动迁移 `{target}` → `{migration_id}`；409=任务运行中/迁移进行中；400=预检失败 |
| `/api/settings/storage/migration` | GET | 迁移状态：`{phase, progress, copied_files, total_files, copied_bytes, total_bytes, speed_bps, elapsed_s, error, warnings[], residual_files[]}` |
| `/api/settings/storage/migration/cancel` | POST | 协作式取消（文件间隙检查标志位） |
| `/api/settings/storage/migration/resume` | POST | 中断恢复：继续迁移 |
| `/api/settings/storage/migration/rollback` | POST | 中断恢复：放弃并清理目标半成品（仅 switching 前允许） |
| `/api/settings/storage/cleanup-old` | POST | 重试清理旧根残留 |
| `/api/settings/storage/reset-default` | POST | 语法糖：以默认根为目标启动迁移 |
| `/api/settings/pick-folder` | POST | Web 态目录选择回退（tkinter，镜像 batches 实现；FROZEN 态返回信封错误，桌面走原生桥） |
| `/api/settings/about` | GET | 版本/形态/数据根（F14） |

进度上报镜像 `task_manager` 模式：独立迁移任务表 + `threading.Thread`（单任务），前端 1s 轮询 GET migration。

### 3.4 文件改动清单（具体到文件）

**后端新增：**
- `backend/core/storage_settings.py` — 锚点读写（原子写）、根解析/回退、存储统计（目录大小/文件数/磁盘）、受管目录清单（按 FROZEN 区分 6/5）。
- `backend/core/storage_migration.py` — 迁移引擎：预检、复制（分块+源哈希）、校验（目标回读哈希）、引用重写、切换、清理、日志（journal）、取消/恢复、残留报告。
- `backend/api/settings_api.py` — §3.3 全部端点。
- `backend/tests/test_storage_settings.py` / `test_storage_migration.py` / `test_settings_api.py`。

**后端修改：**
- `backend/config.py` — 锚点读取 + 根覆盖 + `ACTIVE_ROOT/DEFAULT_ROOT/ROOT_FALLBACK_WARNING` + CONFIG_DIR 特例（§3.1）。
- `backend/app.py` — 注册 `settings_bp`（仅加一行 import + register，不动既有路由）。
- `.gitignore` — 追加 `/settings.local.yaml`（根锚定）。

**前端新增：**
- `frontend/src/api/settings.ts` — typed API 封装（含 `pickFolder` 原生桥优先 + 后端回退，镜像 `batches.ts` L94-98）。
- `frontend/src/stores/settings.ts` — Pinia：存储概览、迁移轮询（1s）、恢复态。
- `frontend/src/views/settings/Settings.vue` — 设置页（存储分区 + 关于分区）。
- `frontend/src/components/settings/MigrationDialog.vue` — 迁移向导弹窗（确认→进度→结果三态一体）。

**前端修改：**
- `frontend/src/router/index.ts` — 新增 `{ path: '/settings', name: 'settings', component: () => import('@/views/settings/Settings.vue') }`（注释 15→16 条）。
- `frontend/src/components/layout/Sidebar.vue` — navItems 追加 `{ to: '/settings', label: '设置', icon: 'gear', section: 'settings' }`（isActive 现有逻辑自动兼容）。
- `frontend/src/components/common/Icon.vue` — 按现有清单补缺：`hard-drive`、`check-circle`、`alert-triangle`、`x-circle`、`refresh`（stroke-width=1.5，24 viewBox，与现有图标同风格）。
- `frontend/src/api/desktop.ts` — 新增 `nativeRestartBackend()` 桥封装（`window.tjzk.restartBackend`，Web 态返回 null）。

**Electron 修改：**
- `electron/main.js` — 新增 `tjzk:restart-backend` IPC：置 `restarting=true`（抑制 L89-97 意外退出报错弹窗）→ `killBackendTree()` → `startBackend()` → 取当前 URL 的 path+query → `win.loadURL(新端口 + 原路径)` → 复位标志；失败走 `dialog.showErrorBox` 并复位。
- `electron/preload.js` — `tjzk` 桥追加 `restartBackend: () => ipcRenderer.invoke('tjzk:restart-backend')`。

**文档：**
- `docs/sdd/plans/2026-11-20-settings-storage-migration.md` — 本计划书正式归档。
- `LOG.md` — 任务完成追加一行。

---

## 4. 路径变更核心逻辑规范（迁移流水线）

### 4.1 阶段规范

**① 预检（precheck）**
- 目标规范化为绝对路径；拒绝：与源相同、目标在源内、源在目标内（祖先/后代关系）、系统目录（`C:\Windows`、`Program Files` 等）、盘符不存在。
- 可写性探测：目标内创建/删除临时探针文件。
- 空间：`shutil.disk_usage(目标盘).free ≥ source_size × 1.1 + 100MB`；源大小/文件数由全量扫描得出（作为进度分母）。
- 任务检查：处理任务管理器存在 running/pending → 拒绝（提示先等待/取消任务）。
- 已有迁移进行中 → 409。
- 预检结果（含警告：目标非空、跨盘提示、预估耗时量级）返回前端确认弹窗展示。

**② 复制（copying）**
- 遍历源受管目录（冻结 6 / 非冻结 5，见 D5），逐文件分块复制（1MB chunk）：写目标同时计算**源文件 SHA-256**；`shutil.copystat` 保留时间戳；目录结构镜像创建。
- 每文件完成即更新 journal（节流：每 50 文件或 2s 落盘）与内存进度（copied_files/copied_bytes/speed 滑动窗口）。
- 单文件失败（占用/权限）：错误隔离记录 `errors[]`，继续后续文件；复制阶段结束若存在失败文件 → 整体 failed（不进入校验），源完好。
- 取消标志在文件间隙检查；取消 → cancelled，源完好，目标半成品保留待恢复决策。
- 复制顺序：先小文件（YAML/JSON 注册表）后大文件，保证 journal 早期可用。

**③ 校验（verifying）——独立全量复核，不信任复制期记录**
- 清单一致性：源/目标相对路径集合完全相等（多出/缺失即失败）。
- 逐文件：size 相等 + 目标回读 SHA-256 == 源哈希（复制期记录）；不一致 → 失败明细（路径、原因）。
- 汇总：total_files/total_bytes 相等。
- 任一失败 → failed，**绝不切换**，源完好；目标保留供排查，UI 提供「重试迁移」（幂等续传）或「放弃并清理」。

**④ 引用重写（rewriting）——只改目标副本，源不动**
- 对目标内 `data/batches.yaml`、`data/processing_tasks.yaml`、`datasets/datasets.yaml`：解析 YAML，字符串值中**以旧根为前缀的绝对路径**替换为新根前缀；相对路径与根外绝对路径一律不动；保持字段顺序与 flow style 约定。
- 对 `results/*/meta.json`、`counting_data.json`：JSON 字符串值同规则前缀替换。
- 重写后 YAML/JSON 必须可重新解析（写前校验），失败 → failed（源完好）。

**⑤ 切换（switching）**
- 原子写锚点 `settings.yaml`（tmp + `os.replace`），`data_root=新根`。
- 写锚点目录 `migration_pending.json` 标记 phase=switched（供中断恢复判定）。
- 此步之后目标为权威数据；**任何后续失败不回滚锚点**。

**⑥ 清理（cleaning）**
- 删除旧根下受管目录（冻结 6 / 非冻结 5）。**绝不删除旧根本身**（冻结态锚点留守；非冻结态旧根=仓库根，只删数据子目录）。
- 逐文件错误隔离：被占用/权限失败 → 跳过并记入 `residual_files[]`，不中断。
- 全部成功 → 删除 `migration_pending.json` 与目标 `.tjzk_migration.json` → completed。
- 有残留 → completed_with_warnings；设置页展示残留清单 + 「重试清理」（`cleanup-old`）。

**⑦ 生效（restart）**
- 桌面态：前端收到 completed → 调 `tjzk.restartBackend` → 主进程重启后端 → 重载原路由 → 设置页展示新根。
- Web 态：完成面板展示重启指引（停止服务后 `.\start.ps1` 或 `python -m backend.app`）+ 刷新按钮；重启前全局横幅 `pending_restart`。

### 4.2 关键决策记录

| # | 决策 | 理由 |
|---|---|---|
| D1 | 统一数据根，整体迁移 | 用户确认；契合 PROJECT_ROOT 架构，相对路径天然兼容 |
| D2 | 重启生效，不做热切换 | 全模块导入期捕获常量；热切换需全量重构，风险不可控 |
| D3 | 锚点文件留守默认位置（KB 级） | 避免鸡生蛋问题；C 盘仅留几 KB 配置，业务数据全量迁走 |
| D4 | SHA-256 全量哈希校验（复制期算源哈希 + 校验期回读目标） | 满足「校验完整性通过」硬要求；磁盘 IO 为瓶颈，哈希开销可接受 |
| D5 | 非冻结态迁移排除 `config/`（5 目录），冻结态含 `config/`（6 目录） | 仓库根 `config/` 是 git 跟踪模板（RESOURCE_ROOT==PROJECT_ROOT），删除会破坏仓库；冻结态用户 config 仅含播种的 models.yaml，可安全迁移 |
| D6 | 清理在切换后、重启前执行，错误隔离 + 残留重试 | 迁移遮罩期无业务打开句柄；残留不影响新根有效性 |
| D7 | journal 仅为提示，恢复以磁盘实况为准（幂等续传：目标已存在且 size+hash 匹配则跳过） | 崩溃后 journal 可能滞后，磁盘才是真相 |
| D8 | 外部文件夹（数据根外的架次图片目录）不移动不改写 | 用户资产，非系统受管数据 |
| D9 | v1 并发防护 = 预检 + UI 遮罩 + 409，不改既有路由内部 | 遵守「不改既有路由文件」约束；残留风险见 A6 |
| D10 | 自定义根启动不可达 → 回退默认根 + 警告 | 盘符拔出不能阻止应用启动；数据在原盘安全无损 |

### 4.3 中断恢复规范

- 迁移启动即写 `<锚点目录>/migration_pending.json`：`{migration_id, source_root, target_root, phase, started_at}`。
- 后端启动时读取：存在且 phase ≠ completed → `GET /api/settings/storage` 返回 `recovery` 对象；设置页顶部恢复卡片：
  - phase < switching：「继续迁移」（幂等续传）/「放弃并清理目标半成品」（rollback，源完好）。
  - phase ≥ switching：「继续完成清理」（新根已权威，仅补清理）。
- 完成/放弃后删除 pending 标记。锚点损坏 → 回退默认根 + 警告（F13 同通道）。

---

## 5. 交互设计规范

### 5.1 入口与页面结构

- 侧边栏「设置」位于导航列表末位（算法广场之下），gear 图标；激活态/折叠态与现有 nav-item 完全一致。
- 设置页单列布局：页头（标题「设置」+ 副标题）→ 分区卡片「数据存储」（F02-F13）→ 分区卡片「关于」（F14）。分区标题沿用现有 section header 风格。

### 5.2 更改位置主流程（向导式）

```
[存储概览卡片] 「更改位置」按钮
  → 目录选择（桌面原生对话框 / Web 后端对话框；输入框可手动编辑绝对路径）
  → 预检报告面板（空间对比条：源大小 vs 目标剩余；错误红字阻断「下一步」；警告黄字可继续）
  → 确认弹窗（MigrationDialog 确认态）：
      · 源 → 目标 路径对照（folder 图标 + arrow-right）
      · 总量：N 个文件 / X.X GB
      · 影响说明：迁移期间请勿进行其他操作；完成后桌面态自动重启 / Web 态需手动重启
      · 红色警示区：「完整性校验通过后，旧位置数据将被删除」
      · 勾选「我已了解上述影响」后「开始迁移」按钮方可点击（防误操作）
  → 进度态（弹窗不可关闭，遮罩阻断页面交互；路由离开守卫 + beforeunload 警示）
      · 阶段 stepper：复制 → 校验 → 切换 → 清理（当前阶段 brand 色，完成 check-circle）
      · 双进度条：文件数 / 字节数；速率、已用时间、当前文件名（truncate）
      · 「取消迁移」按钮 → 二次确认（说明源数据完好、可稍后恢复）
  → 结果态：
      · 成功：check-circle 绿色摘要（文件数/大小/耗时/校验通过）→ 桌面态「正在重启服务…」自动重载；Web 态重启指引 + 刷新按钮
      · 失败：x-circle 红色原因 + 恢复操作（重试 / 放弃并清理 / 查看明细）
      · 有残留：alert-triangle 黄色残留清单 + 「重试清理」
```

### 5.3 恢复默认位置

存储概览卡片在自定义态显示「恢复默认位置」次级按钮 → 复用同一向导（目标=默认根，预检/确认/进度一致）。

### 5.4 异常提示矩阵

| 场景 | 时机 | 提示与引导 |
|---|---|---|
| 空间不足 | 预检 | 红色错误：需 X GB / 仅剩 Y GB；阻断下一步；建议更换目标 |
| 无写权限 | 预检/复制 | 「目标目录不可写，请更换目录或以当前用户权限重试」 |
| 嵌套/同路径/系统目录 | 预检 | 明确文案阻断（「目标不能位于当前数据目录内部」等） |
| 运行中任务 | 预检 | 「有 N 个处理任务进行中，请等待完成后再迁移」 |
| 单文件占用（复制期） | 复制 | 错误隔离；阶段末汇总失败明细 → failed，引导关闭占用程序后重试 |
| 校验失败 | 校验 | 「完整性校验未通过（N 个文件不一致），旧数据未受影响」；重试/放弃 |
| 清理残留 | 清理 | 黄色警告 + 残留文件清单 + 重试清理；不阻断重启 |
| 进程中断 | 下次启动 | 恢复卡片：继续 / 放弃并清理（§4.3） |
| 配置根丢失 | 启动 | 全局警示横幅「自定义数据位置不可达，已临时使用默认位置」+ 重试连接/重置默认 |
| 锚点损坏 | 启动 | 同上通道，文案「存储配置损坏，已恢复默认位置」 |
| 重启失败（桌面） | 重启 | 主进程 showErrorBox「服务重启失败，请重启应用」；数据已安全切换 |

### 5.5 防误操作要点

- 确认弹窗勾选制 + 红色删除警示；进度态弹窗禁止 ESC/遮罩关闭；取消需二次确认。
- 迁移期间侧边栏导航被遮罩阻断（路由守卫兜底）；`beforeunload` 提示。
- 所有破坏性动作（删除旧数据）只发生在「全量校验通过 + 锚点切换」之后，UI 明示该因果。

---

## 6. UI 规范（与现有设计体系完全一致）

| 维度 | 规范（引用现有令牌，不新增风格） |
|---|---|
| 主题 | 浅色；页面背景 `surface-bg #F9FAFB`，卡片白底 + `border-surface-border #E5E7EB` + `rounded-card 10px` + `shadow-card` |
| 主色 | Emerald `brand-500 #10B981`（主按钮/进度条/激活态）；hover `brand-600`；浅底 `brand-50/100` |
| 文字 | `ink-primary #1F2937` 标题/正文，`ink-secondary #6B7280` 说明，`ink-tertiary #9CA3AF` 辅助；字体 Inter/Noto Sans SC 现有栈；数字 `tabular-nums` |
| 按钮 | 主按钮 brand 实底白字 `rounded-btn 8px`；次级白底细边框 hover `surface-hover`；危险操作红字/红底（沿用现有删除按钮风格）；禁用态灰化 |
| 状态色 | 成功 brand/绿、警告 amber、错误 red、进行中 brand；**静态色块状态，过渡 ≤200ms，禁脉冲/霓虹/玻璃拟态** |
| 图标 | 一律 `Icon.vue` SVG（stroke-width=1.5，24 viewBox）；缺失图标按同风格补绘（hard-drive/check-circle/alert-triangle/x-circle/refresh）；禁 emoji |
| 弹窗 | 白底卡片 + 细边框 + shadow-card-hover，遮罩 `bg-black/30`，圆角 rounded-card；与现有页面弹窗模式一致（替代原生 confirm 用于高风险迁移确认，视觉语言不变） |
| 进度条 | 轨道 `surface-hover`，填充 `brand-500`，高度 6-8px，圆角；stepper 用 check-circle/圆点静态态 |
| 布局 | 设置页最大宽度与现有视图一致（max-w-5xl 量级，以现有页面实测为准），分区卡片纵向堆叠，表单行左标签右控件 |
| 容量条 | 磁盘占用细条：已用 `brand-300`/剩余 `surface-hover`，临界（<10%）转 amber/red 静态色 |

**禁止项**：改动任何现有页面/组件的视觉风格；引入新色板/新圆角体系/动画库；玻璃拟态、霓虹光效、脉冲动画。

---

## 7. 开发阶段划分（任务节点 + 验收标准）

### 阶段 0：需求细化与设计冻结
- 任务：本计划书评审；确认 D1-D10 决策；冻结 P0 范围（F01-F14）。
- 交付：正式计划书 `docs/sdd/plans/2026-11-20-settings-storage-migration.md`。
- **验收**：用户批准计划书；决策无未决项。

### 阶段 1：后端配置基座与存储信息
- 任务：`storage_settings.py`（锚点读写/根解析/统计）；`config.py` 覆盖与回退（§3.1）；`settings_api.py` 骨架 + GET storage / pick-folder / about；`.gitignore`；单元测试。
- **验收**：`cd backend; python -m pytest -v` 全绿（含既有回归）；无锚点时 Web/桌面默认行为与改造前完全一致；锚点覆盖/损坏/根丢失三态单测通过。

### 阶段 2：迁移引擎
- 任务：`storage_migration.py` 全状态机（预检/复制/校验/重写/切换/清理/journal/取消/恢复/残留）；migrate/validate/migration/cancel/resume/rollback/cleanup-old/reset-default 端点；测试（含中断注入、校验失败注入、占用模拟）。
- **验收**：测试矩阵 T01-T16、T20-T23、T26-T27 的自动化子集全绿；任何 switching 前失败源数据哈希审计零差异；并发迁移 409。

### 阶段 3：前端设置页与迁移向导
- 任务：`settings.ts` api/store；`Settings.vue` + `MigrationDialog.vue`；router/Sidebar/Icon/desktop.ts 改动；`npm run build`。
- **验收**：构建通过；UI 走查符合 §6 规范（与现有页面并排截图比对）；主流程/恢复默认/恢复卡片/异常矩阵交互完整；迁移遮罩与路由守卫生效。

### 阶段 4：桌面集成与双形态联调
- 任务：`main.js` restart IPC + restarting 标志；`preload.js` 桥；前端重启衔接；载荷重建（`build-backend.ps1 -PythonExe <uav-vis python>`）；`npm start` 联调；`npm run smoke`。
- **验收**：桌面态 C→D 迁移后自动重启、路由保留、数据完整（T24）；smoke 通过（health/models/单图推理）；Web 态迁移 + 手动重启生效、pending 横幅正确；重启失败兜底弹窗。

### 阶段 5：测试验证（全量）
- 任务：执行 §8 全矩阵（自动化 + 手工）；大文件/跨盘/中断/长路径专项；迁移后全功能回归（上传/处理/数据集/检测/计数/模型注册）；测试报告归档 `.lqs/2026-11-XX/settings-storage-migration/outputs/`。
- **验收**：T01-T28 全部通过；**数据零丢失零损坏（哈希审计）**；性能记录（GB 级迁移速率/内存）；无 P0/P1 缺陷遗留。

### 阶段 6：上线发布
- 任务：`electron/package.json` 版本 1.0.0 → **1.1.0**；冻结验证链（pytest → frontend build → 载荷重建 → smoke）；`npm run build:dir` → 干净目录解压验证 + SHA256；注解 tag `v1.1.0`；按 AGENTS.md Git 工作流走代理推送；`gh release create` 上传 `TianJianZhiKan-v1.1.0-win-x64.zip` + sha256（**实际发布须经用户确认**）。
- 交付：Release notes（新功能说明 + 迁移使用指引 + SmartScreen「更多信息→仍要运行」提示 + 已知限制）。
- **验收**：发布检查单全过；zip 解压即运行；旧版本数据目录升级后无损（锚点缺失=默认行为）。

---

## 8. 测试验证要求

### 8.1 测试用例矩阵

| ID | 场景 | 步骤要点 | 预期 |
|---|---|---|---|
| T01 | 正常跨盘迁移 | 桌面态 C→D，含架次/处理产物/数据集/结果/模型 | 全阶段成功；哈希审计零差异；旧受管目录删除；重启后各模块数据可见 |
| T02 | 同盘换目录 | D:\A→D:\B | 同 T01（同盘复制路径） |
| T03 | 大文件迁移 | 单 50MB 图 + ≥2GB 数据集（稀疏文件构造） | 进度字节准确；校验通过；内存平稳（分块流式，无整文件读入） |
| T04 | 海量小文件 | ≥10000 小文件 | 进度文件数准确；journal 节流不拖垮速率；清单校验通过 |
| T05 | 中文/空格/长路径 | 目标含中文、空格、>200 字符路径 | 复制/校验/重写/清理全通；YAML 中文无损 |
| T06 | 复制期中断 | copying 阶段 kill 后端 → 重启 | 恢复卡片出现；继续迁移幂等续传成功；源始终完好 |
| T07 | 校验期中断 | verifying 阶段 kill → 重启 → 继续 | 同 T06 |
| T08 | 清理期中断 | cleaning 阶段 kill → 重启 | 新根已权威；残留报告；重试清理完成 |
| T09 | 用户取消 | copying 中取消 → 二次确认 | cancelled；源完好；目标半成品可 resume 或 rollback 清除 |
| T10 | 校验失败注入 | 复制后篡改目标某文件 → 触发校验 | failed；不切换；源完好；明细列出篡改文件；重试可修复 |
| T11 | 空间不足 | 目标盘剩余 < 源×1.1 | 预检红色阻断，文案含具体数值 |
| T12 | 权限拒绝 | 目标为只读目录 | 预检/复制报错友好；源完好 |
| T13 | 非法目标 | 目标=源 / 目标在源内 / 源在目标内 | 预检分别明确拒绝 |
| T14 | 系统目录 | 目标 C:\Windows 等 | 预检拒绝 |
| T15 | 运行中任务 | 提交处理任务后立即发起迁移 | 409 + 「等待任务完成」提示 |
| T16 | 并发迁移 | 两个 migrate 请求 | 第二个 409 |
| T17 | 相对路径兼容 | 迁移后打开相对路径架次 | 图片列表/预览/处理正常 |
| T18 | 绝对路径重写 | 构造指向旧根内部的绝对路径架次/任务/数据集 | 迁移后 YAML 指向新根；功能正常 |
| T19 | 外部文件夹 | 架次图片在数据根外（如 E:\photos） | 不移动不改写；迁移后仍可访问 |
| T20 | 恢复默认 | 自定义态 → 恢复默认位置 | 反向迁移成功；锚点清除/回默认；C 盘数据恢复 |
| T21 | 连续迁移 | A→B→C 两次 | 每次完整流水线；无残留累积（除占用模拟） |
| T22 | 空数据根 | 全新安装无业务数据迁移 | 成功；目录骨架创建；播种逻辑正常 |
| T23 | 配置根丢失 | 自定义根盘符移除后启动 | 回退默认根 + 警示横幅；重试连接/重置默认可用 |
| T24 | 双形态生效 | 桌面自动重启 / Web 手动重启 | 桌面路由保留重载；Web pending 横幅 + 重启后生效 |
| T25 | 迁移后全功能回归 | 上传/扫描/处理/数据集构建/检测/计数/模型注册 | 全模块正常（冻结态 smoke + 手工） |
| T26 | 清理期文件占用 | 清理时锁定旧根某文件 | 跳过 + 残留报告；不崩溃；重试清理（释放后）完成 |
| T27 | 锚点损坏 | settings.yaml 写入非法 YAML | 启动回退默认 + 警告；不崩溃 |
| T28 | 桌面冒烟 | `npm run smoke` | health/models/单图推理通过；耗时/内存报告正常 |

### 8.2 测试分层与工具

- **单元/集成（pytest，自动化）**：`test_storage_settings.py`（锚点三态/统计/受管清单）、`test_storage_migration.py`（tmp_path 构造迷你数据根；中断=阶段钩子抛异常模拟；校验失败=篡改注入；占用=monkeypatch 删除失败）、`test_settings_api.py`（Flask test client 全端点信封/状态码）。
- **手工 E2E**：T01/T03/T05/T11-T15/T19/T23-T26 在真实桌面态 + Web 态各执行一遍；大文件用稀疏/随机数据构造（fixture 放 `backend/tests/` 或 `.lqs/imgs/`，禁仓库根）。
- **数据安全审计**：每次迁移测试前后对源/目标做独立哈希清单比对（脚本归档 outputs/），**零差异为硬性门槛**。
- **回归门槛**：既有 pytest 全绿 + smoke 通过 + 现有页面 UI 无变化（截图比对）。

---

## 9. 风险与假设

| # | 内容 | 缓解 |
|---|---|---|
| A1 | 重启生效带来秒级服务中断 | 桌面自动重启（编排链已验证）；UI 明示；Web 指引 |
| A2 | GB 级数据迁移耗时较长 | 分块流式 + 实时速率/进度；预检给出量级预估；可取消可恢复 |
| A3 | Windows 长路径/权限/占用 | 错误隔离 + 残留重试；T05/T12/T26 专项 |
| A4 | 非冻结态 config/ 为 git 跟踪模板 | D5 排除迁移；测试覆盖 Web 态仓库完整性 |
| A5 | 锚点留守 C 盘（KB 级） | 符合「业务数据迁走」目标；文档明示 |
| A6 | v1 迁移期间非 UI 通道（直接 API 调用）仍可能写入旧根 | 预检清场 + UI 遮罩覆盖正常用户路径；迁移窗口短；P1 可加全局迁移锁中间件 |
| A7 | 外部盘符拔出 | D10 启动回退 + 警示；数据无损 |
| A8 | 未签名 SmartScreen | 发布说明沿用现有提示文案 |
| A9 | 发布动作 | 阶段 6 实际 push/release 须经用户确认（AGENTS.md Git 工作流 + 代理） |

---

## 10. 文档任务执行记录（本任务范围）

本任务交付物为计划书文档，批准后执行：
1. 将本计划书正式归档至 `docs/sdd/plans/2026-11-20-settings-storage-migration.md`（SDD 跟踪目录，命名符合 AGENTS.md）。
2. 向 `LOG.md` 末尾追加一行：`- [2026-11-20 23:54] docs(settings): 新增设置模块存储迁移开发计划书（docs/sdd/plans）`。
3. 向用户交付文档链接与要点摘要。**不启动代码实现**（代码实现按 §7 阶段另行立项执行）。

## 11. 验证（Verification）

- 文档落位正确：`docs/sdd/plans/2026-11-20-settings-storage-migration.md` 存在且内容完整（六项核心要求全覆盖）。
- `LOG.md` 追加格式符合规范（时间正序、一行、≤50 字摘要）。
- `git status --porcelain` 确认仅新增文档与 LOG 改动，无其他文件污染。