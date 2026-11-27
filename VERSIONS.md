# 版本管理与发版计划（VERSIONS）

> 本文件是「田间智瞰」项目版本历史与发版计划的单一索引。
> 2026-11-25 版本编号体系重构：旧桌面版本线 **v1.0.0 / v1.1.0 全部重置并入 V0.5.5 基线**；2026-11-24 的「无人机型号选择 + 地块地理位置」更新定为 **V0.5.6**；2026-11-25 的「数据处理模块风险收敛与长路径显示修复」定为 **V0.5.7**；2026-11-26 的「详情页/设置页布局对齐与存储路径快捷操作」定为 **V0.5.8（当前基线）**。历史文档（`docs/desktop-build-guide.md`、`.lqs/` 报告等）保留旧编号原文，以本文映射表对照，不回改。
> 历史细节来源：`docs/prd/`（PRD v1~v7）、`docs/update_report/`（001~012）、`docs/bug_report/`（001~011）、`LOG.md`、git 提交树（追溯重构，V0.5.5 及以前版本号为回填编号，非当时实际发布号）。

---

## 一、版本管理规范

| 项 | 约定 |
|---|---|
| 编号体系 | 语义化 `MAJOR.MINOR.PATCH`；当前处于 `0.x` 快速迭代期，`1.0.0` 保留给四模块全部完成、可对外稳定发布时的正式版 |
| 升位规则 | `0.x` 期：模块级功能里程碑 → MINOR；同模块内迭代/优化/修复 → PATCH |
| 版本单一来源 | `electron/package.json` 的 `version`；安装包名、exe 属性、`/api/health`、「设置 → 关于」均读该值 |
| 版本透传链 | 桌面壳以 `TJZK_APP_VERSION` 环境变量传给冻结后端 → `backend/config.py` 的 `APP_VERSION`（开发态回退读 `electron/package.json`） |
| Git tag | 注解 tag `vX.Y.Z`，与 `electron/package.json` 对齐；**截至 V0.5.8 仓库尚无任何 tag**（旧 v1.0.0/v1.1.0 未打过 tag、未发 GitHub Release），`v0.5.8` 将是新编号体系首个 tag |
| 提交规范 | Conventional Commits（见 AGENTS.md） |
| 记录分工 | `VERSIONS.md`＝版本级索引；`LOG.md`＝任务级一行日志；`docs/update_report/`、`docs/bug_report/`＝详细归档；`docs/prd/`＝需求基线 |
| 桌面发布流程 | 冻结验证（pytest → frontend build → 载荷重建 → smoke）→ 版本提交 → 注解 tag → 走代理推送（AGENTS.md Git 工作流）→ 产物 + SHA256 → `gh release create` |

### 新旧编号映射

| 旧编号 | 新编号 | 说明 |
|---|---|---|
| v1.0.0 | **V0.5.5**（并入） | 2026-11-19~20 桌面端首版：Electron 壳 + PyInstaller 冻结后端、zip 便携版流程规划、NSIS 构建配置、原生目录选择对话框修复 |
| v1.1.0 | **V0.5.5**（并入） | 2026-11-21~23 设置模块：存储位置自定义与安全迁移、双栏仪表盘布局、NSIS 向导式安装包 |

---

## 二、版本历史（追溯重构）

### V0.5.8 —— 当前基线（2026-11-26，桌面端与安装包已产出）

**主题：详情页与设置页布局对齐 + 存储路径双击复制/一键打开目录**

- **处理任务详情页布局收敛**（`594f9e7`，TaskDetail.vue）：【任务参数】与【任务信息】并入同一三列栅格（参数 `col-span-2` + 信息右列），栅格默认拉伸使两卡同高、底部严格齐平；【快速预览】移出栅格独占整行，右边界与【任务信息】卡片齐平（1100/1600/1920 宽实测 bottom 436=436、right 一致）；删除无真实数据来源的静态「执行日志」块。
- **设置页双栏底部对齐**（`594f9e7`，Settings.vue）：外层栅格去掉 `items-start`，右栏改 flex 列并对【关于】卡加 `flex-1` 撑满，左右两栏谁高谁矮都能对齐（1280/1440/1920 宽实测 bottom 616/455/579 完全一致）；窄于 1280px 自动纵向堆叠。
- **存储路径快捷操作**（`594f9e7`，Settings.vue + settings_api.py + settings.ts）：当前根目录与 5 个模块目录路径**双击复制完整路径**（复制接口原始值，不受界面截断影响；Clipboard API 被拒时回退 `execCommand`，右下角提示「已复制路径」）；新增根目录「打开目录」按钮与各模块文件夹图标，对应后端新端点 `POST /api/settings/open-folder`——只接受受管目录标识（`root|data|output|datasets|results|models|config`），路径由后端解析、缺失时 mkdir 后交给系统文件管理器打开（Windows `os.startfile` / macOS `open` / Linux `xdg-open`），拒绝前端传入任意路径。
- **修复：打开目录窗口置顶**（2026-11-27，settings_api.py）：Windows 下 explorer 新窗口受前台锁限制会被拥有焦点的应用窗口压在底层，打开后改为识别新出现的资源管理器窗口（`CabinetWClass` 枚举对比）并置顶激活——`ShowWindow(SW_RESTORE)` → `SetForegroundWindow`（被拒时模拟 ALT 按键事件解锁前台权限重试）→ `SetWindowPos(HWND_TOP)`；复用已有窗口的场景由 explorer 自身激活（实测同样到前台）；打开行为不受置顶失败影响。新增 4 个窗口置顶单元测试（新窗口识别/句柄选取/超时静默/ALT 回退）。
- **修复：自定义路径架次可作处理输入**（2026-11-27，processing_api.py）：数据管理允许任意本机目录登记架次，但数据处理输入源白名单只放行 `data/`、`output/` 根下目录，导致自定义路径登记的架次提交 CLAHE/裁切一律 400。改为白名单并入**已登记架次的目录树**（`batch_registry.list_batches()` 逐项 `resolve` 后比对，相对路径与 BatchRegistry 同基准按 PROJECT_ROOT 解析），未登记目录仍拒绝、路径穿越防护不变；新增已登记外部架次可提交用例，后端全套 **186 passed**。
- **测试**：open-folder 用例（非法 key 400、受管目录、根目录、冻结态 `config`）+ 窗口置顶 4 用例，后端全套 **185 passed**；前端 `vue-tsc --noEmit && vite build` 通过。
- **产物与验证**：
  - 冻结后端载荷 `electron/backend-dist/TianJianZhiKanBackend/`：3,382 文件 / 851.5 MB；直接启动打包后端校验 `/api/health` 返回 `v0.5.8`、`/api/settings/open-folder` 路由存在（非法 key 400）；**窗口置顶修复在冻结载荷实测通过**（新开窗口 `is_foreground=True`、Z 序顶端，取证脚本 `.lqs/2026-11-27/open-folder-topfix/outputs/`）。
  - 便携目录 `electron/dist/win-unpacked`：3,455 文件 / 1,119.5 MB，`TianJianZhiKan.exe` 文件版本 **0.5.8**；打包前端已含新设置页逻辑（产物 `Settings-*.js` 含 `open-folder` 调用）。
  - NSIS 安装包 `electron/dist/TianJianZhiKan-v0.5.8-win-x64-setup.exe`：382,879,127 B（365.1 MiB），文件版本 0.5.8，SHA256 `915F39DB86917407FC5507EB1DA538E86D21BCECAEC7FF809584D576F0FB55B2`（2026-11-27 含输入源白名单修复的重建版；历史链：`6647665B…A7F52` 首版 → `C9881154…22C5E` 窗口置顶修复版 → 此版）。
  - 开发态冒烟（`npm run smoke`）：后端 2.9s 就绪、health `v0.5.8`、11 个模型、单图推理 2,992ms 成功（3 个检出）。
  - 重建验证（2026-11-27 输入源修复版）：开发态冒烟就绪 2.6s、推理 3,685ms 成功；打包态冒烟（win-unpacked `TianJianZhiKan.exe --smoke`）就绪 0.9s、health `v0.5.8`、11 模型、推理 3,053ms 成功（3 个检出）。
  - 静默安装（`setup.exe /S /D=%TEMP%\tjzk-install-v058`）：退出码 0、38.0s，安装目录 exe 版本 0.5.8、卸载器与桌面「田间智瞰」快捷方式齐全；安装版冒烟 health `v0.5.8`、11 模型、单图推理 2,960ms 成功。
  - 卸载（`Uninstall TianJianZhiKan.exe /S`）：退出码 0，快捷方式与卸载注册表项清理干净、安装目录仅剩空目录（已知问题），`%LOCALAPPDATA%\TianJianZhiKan` 业务数据 443 个文件保留。

### V0.5.7 —— 数据处理风险收敛（2026-11-25，桌面端与安装包已产出）

**主题：数据处理模块风险收敛——输入源准入、冗余信息清理与长路径显示**

- **移除自定义目录输入源**（`01811e4`，TaskNew.vue + processing_api.py）：新建任务仅支持「已登记架次」与「已有加工产物」两类输入；后端 `_validate_input_paths` 在 CLAHE/裁切提交前强制校验，仅接受 `data/`（上传数据）或 `output/`（加工产物）根下目录，`resolve()` 防路径穿越，自定义目录直接 400，杜绝任意路径注入风险。
- **清理详情页静态占位信息**（`01811e4`，TaskDetail.vue）：删除写死的「创建者 李研究员」「设备 CPU · 8 workers」「平均速度 0.65 s/张」与失效的「下游数据集 甘蔗幼苗 v1.2.0」入口；CLAHE 统计卡收敛为 4 张真实指标，裁切保留真实「子图总数」。
- **长路径显示统一修复**（`01811e4`，新增 `frontend/src/components/common/PathText.vue`）：超过两级的路径仅显示末两级并以 `…/` 前缀缩略，单行截断防列溢出；悬停提示完整路径、点击展开/收起。接入处理任务列表、任务详情、新建任务向导、加工数据列表与详情页，覆盖 CLAHE 与滑窗裁切两种处理操作。
- **测试与环境**：processing 相关测试同步改造输入源夹具并新增安全用例（自定义目录 400 / 加工产物可再加工），后端全套 **179 passed**；构建环境重建为 `C:\Users\lqs\UAVDesktopBuild\venv`（Python 3.8.20 + PyInstaller 6.22.3 + **torch/torchvision/torchaudio 2.1.0/0.16.0/2.1.0 +cpu**，CUDA 版不可分发）。
- **产物与验证**：Electron 便携目录 `electron/dist/win-unpacked`（`TianJianZhiKan.exe` 文件版本 0.5.7）与 NSIS 安装包 `TianJianZhiKan-v0.5.7-win-x64-setup.exe`（365.1 MB，SHA256 `86224BF400808295C9D94E87088856AE5CC4A3D34C2EFDC70443E1538B1ED898`）；打包版与静默安装版均冒烟通过（health v0.5.7 / 11 模型 / 单图推理成功），静默安装后快捷方式与卸载注册表项随卸载清理干净。后端载荷 851.5 MB / 3382 文件。

### V0.5.6 —— 架次登记增强（2026-11-24 ~ 2026-11-25）

**主题：架次登记增强——无人机型号选择 + 地块地理位置信息**

- **无人机型号预设更新与自定义持久化**（`a03c60b`，BatchNew.vue）：预设收敛为农田监测设备（移除 DJI Agras T 系列喷洒机型，新增极飞 M2000/M500 2025 款巡田无人机等）；选「其他」支持自填型号，持久化后加入预选列表。
- **地块信息升级为地理位置信息**（`20d8fb1`，geo_api + GeoLocationEditor）：Leaflet 地图选点弹窗；DJI 图片 EXIF GPS 提取接口；架次存储 WGS84 经纬度/海拔/来源。
- 基线后增量（2026-11-25，并入 V0.5.7 发布）：
  - `5c87590` fix：补齐 BatchDetail.vue 缺失的 DataSubTabs 导入；Electron 窗口最小尺寸对齐规范 1100×760。
  - `be61106`/`66f3be3` chore：接入 AOCI-CODE v0.2.0-rc4 仓库认知资产（117 条 Code Entry 索引）。
  - `39482b1` chore：清理 `reports/` 报告相关冗余图片与文件。
  - 版本编号重构：`electron/package.json` 1.1.0 → **0.5.6**，`backend/config.py` 版本回退默认值同步；新建本文件。

### V0.5.5 —— 桌面端基线（2026-11-19 ~ 2026-11-23）＝旧 v1.0.0 + v1.1.0 合并

**主题：Electron 桌面端落地 + 设置模块**

- **仓库工程化**（`43ec57b`）：目录规范梳理——SDD/AI 分析/图标源文档迁移，`.gitignore` 运行目录根锚定修复；`LOG.md` 改动日志制度建立（历史里程碑回填）。
- **README 与桌面目录规范**：README 更新至 V4 阶段（桌面端 + 数据集管理详情，`75fd01b`）；应用图标文件更新（`6569e94`）；新增 `electron/.gitignore` 隔离构建产物（`d9614f1`）。
- **Electron 桌面壳 + PyInstaller 冻结后端**（`975f537`，旧 v1.0.0 核心）：
  - FROZEN 门控双根配置：RESOURCE_ROOT（只读资源）与 PROJECT_ROOT（可写数据根 `%LOCALAPPDATA%\TianJianZhiKan\`）分离；首启播种 `models.yaml`。
  - 进程编排：单实例锁 → spawn 后端 `--port 0` → stdout 协议 `BACKEND_PORT`/`BACKEND_READY` → 载入动态端口；stdin 看门狗 + taskkill 兜底防孤儿进程。
  - 窗口 1440×900（min 1100×760）、隐藏默认菜单栏、contextIsolation=true。
  - `npm run smoke` 冒烟（health/models/单图推理 + 耗时内存报告）。
- **发布流程规划**（报告 012）：仅发布 Win zip 便携版、exe 产物分类；zip target/artifactName 配置规划未实施。
- **NSIS 安装包构建链**（`862e9b1`/`89d546c`）：向导式/自定义目录/当前用户级/桌面与开始菜单快捷方式；删除废弃 DEPLOYMENT.md、移除 Electron 默认菜单栏（`69b03e4`）。
- **修复：桌面端文件夹选择**（`ecc334d`）：改走 Electron 原生目录选择对话框 IPC（`tjzk:pick-folder`），替代后端接口调用，重打包验证通过。
- **设置模块——存储位置自定义与安全迁移**（`f3ed819`，计划 `docs/sdd/plans/2026-11-20-settings-storage-migration.md`）：锚点文件（settings.yaml/settings.local.yaml）永不随数据迁移；迁移引擎 + 前端向导 + 桌面重启 IPC；数据根不可达回退默认并告警；pytest 168 全绿。
- **设置页宽屏双栏仪表盘布局**（`d940015`）：存储 2/3 + 磁盘/关于右栏，消除全屏右侧空白。
- **v1.1.0 NSIS 安装包产出与验证**（`0824247`）：窗口自适应/F11/版本透传（`TJZK_APP_VERSION`）；安装/冒烟/卸载全链路验证，构建说明沉淀 `docs/desktop-build-guide.md`（该文档保留旧 v1.1.0 编号原文）。

### V0.5.4 —— 视觉资产与算法页精简（2026-11-12 ~ 11-13）

- 新应用图标替换与全局引用更新（`5156773`）。
- 移除算法管理页顶部静态统计卡片（`7a5f96d`）。

### V0.5.3 —— 双模式构建与 GitHub Pages 部署（2026-11-02 ~ 11-03）

- 前端双模式构建（`471df63`）：`npm run build`（产物 → `backend/static/`，Flask/Electron 托管）与 `npm run build:pages`（产物 → `frontend/dist/`，静态演示）；新增 GitHub Pages 自动部署工作流。
- 系统架构图与演示文稿归档 `reports/`（`1f13480`）；全栈开发经验沉淀与调研证据清单（`52471b5`，中间稿后清理 `b24490c`）。

### V0.5.2 —— 首页品牌信息修正与模型库扩容（2026-10-12）

- 首页标题错字修正「田间智监」→「田间智瞰」，副标题改为「无人机智能巡检的大田甘蔗幼苗监测与管理软件」；侧边栏用户信息简化为「观察员」（`1b6a791`。注：项目重命名发生在 2026-08-13 `728c270`，见 V0.4.0）。
- `config/models.yaml` 扩容甘蔗幼苗专用模型族（YOLOv5nu/v8n/v10/v11n/yolo26n 等），模型清单达 **11 个**，支持热切换激活。

### V0.5.1 —— 部署准备与工程规范（2026-09-02 ~ 10-01）

- 新增 CPU 版依赖 `requirements-cpu.txt`（torch 2.1.0+cpu 三件套，`b2faf74`）。
- 部署指南 DEPLOYMENT.md（`bd273d5`，V0.5.5 期间废弃删除）。
- 新增 `AGENTS.md` AI 编码代理项目指引（`82f7e5e`）。
- 研究进展汇报材料整理归档（`e957932` 等）。
- 工具产物目录陆续纳入忽略规则（2026-09-02 ~ 11-03）：`.qwenwork/`、`.qoder/`、`.workbuddy/`、`.codex/`、`remotion/`（`a83413c`/`a66262c`/`3c3167d`/`503aebd`/`d90fb23`）。

### V0.5.0 —— 数据集管理（模块三）一阶段真实实现（2026-08-13 ~ 08-15）

- 设计文档 + 实施计划（`4a3efa3`/`81639fa`，`docs/sdd/specs/2026-08-13-dataset-management-phase1-design.md`）。
- **后端**：DatasetRegistry YAML 持久化（`datasets/datasets.yaml`）+ 自动发现 + 路径预检扫描（`1c0b156`）；`detect_format` 与 COCO/YOLO/VOC 三格式解析 → 统一 IR（`13c817a`/`8382a3a`）；DatasetAnalyzer 轻量统计（仅解析标注不解码像素）+ compute_report 重统计/缓存/类别失衡告警（`33c46bc`/`fce3aa7`）；import/scan/delete/images/preview（`6c2e66f`）；`datasets_api` 9 端点真实实现（`759a05e`）。
- **前端**：datasets API 客户端 + Pinia store（`0f540c5`）；首页对接真实数据集 store（`dd7e951`）；DatasetNew 双 tab（导入可用/构建禁用预留）（`b0a215d`）；DatasetDetail ECharts 统计报告 + 样本分页浏览 + 删除（`383f1a1`）。
- **修复**：dataset_formats Python 3.8 联合类型注解兼容崩溃（bug010，`ca04582`）；详情页统计图表首载空白（bug011，`b7ec771`）。
- **迭代**（报告 011，`7051765`）：详情页删改布局重排、统计口径调整、5% 抽样与翻页优化。
- 构建/拆分/多格式导出为二阶段（入口预留禁用，见发版计划 V0.6.0）。

### V0.4.0 —— 数据处理（模块二）真实实现与全局 UI 优化（2026-08-12 ~ 08-13）

- **数据处理真实实现**（报告 007）：ProcessingEngine + ProcessingRegistry + 10 个 API 端点；批量 CLAHE 增强/滑窗裁切异步任务；任务持久化 `data/processing_tasks.yaml` + 状态机（pending→processing→completed/failed，服务重启残留转 interrupted）+ `output/` 自扫描重建；【加工数据】子模块双 tab；子图命名 `{orig_stem}_tile_{seq:04d}_x{offset_x}_y{offset_y}.jpg`；单图失败错误隔离不中断整批。
- **交互增强**（报告 008）：导航折叠拖拽、检测计数图片持久化、数据处理输入源与差异化预览、加工数据浏览增强。
- **UI 体系优化**（报告 009/010）：首页卡片高度对齐、原始数据卡片化、侧边栏吸附、处理任务顶部 Tab；侧边栏折叠态图标水平居中与间距。
- **工程与品牌**：项目统一更名「田间智瞰」，同步 README、`start.ps1` 与后端系统名称（`728c270`）；FontAwesome 图标全面替换为内置 `Icon` 组件、任务名称按类型自动生成、加工产物目录加入输入源扫描（`20fb72c`）；`.gitignore` 的 `/data/` 规则首次修正为根锚定，避免误忽略前端同名子目录（`09aa02a`）。
- **修复**：数据处理增强与 UI 多项修复（bug008）；侧边栏随主内容滚动悬空（bug009）。
- **PRD v6**（2026-08-13）：模块二完整实现沉淀为需求基线；前端路由 17 条；模块三完整设计方案（基于自建 SSDC-UAV 数据集：14,220 图 / 89,136 框 / 单类别 Sugarcane Seedling）。

### V0.3.0 —— 数据管理（模块一）真实实现（2026-08-11 ~ 08-12）

- **架次真实功能替代 Mock**（报告 005）：BatchRegistry 注册中心——YAML 持久化（`data/batches.yaml`）、启动自动扫描注册、图片索引（Pillow 读尺寸）、动态缩略图/预览生成、ignored_folders 忽略机制、路径预检。
- **架次登记表单三项增强**（报告 006）：命名格式、作物自定义、文件夹选择对话框。
- **修复**：batch_registry Python 3.8 内置泛型兼容崩溃（bug007）。
- **PRD v5**（2026-08-12）：数据管理存储方案由 JSON 调整为 YAML；API 新增 PUT 更新/scan 预检/pick-folder；算法广场 `models.yaml` 实际注册 6 模型（新增 yolo12n、yolo26s）；模块二/三标记 Mock 待实现。

### V0.2.0 —— 算法广场（模块四）真实实现（2026-08-10 ~ 08-11）

- **算法管理模块优化**（报告 001）：FP16 半精度清理、模型注册 YAML 持久化、权重文件上传、图标统一（SVG stroke-width=1.5，弃 emoji）。
- **图片查看交互**（报告 002，`0ddc3db`）：全局图片查看组件（缩放/拖拽/旋转），检测结果与原图点击放大；`max_det` 上限 300 → 1000，后在报告 003 归位为单块上限 300。
- **计数管线五项改进**（报告 003）：`max_det` 归位为「单块上限」并统一 300；全局二次过滤 `global_conf` 默认 0.5（块内 conf 0.25 保召回）；子块结果日志 `tile_results` 随结果落盘；批量分块推理 `batch_size=16`；max_det 触顶告警提示密植截断风险。
- **计数参数默认值调整与 UI/UX 质感升级**（报告 004）：计数工作台 CLAHE 预处理默认开启（`4a8d98a`）；字体升级 Inter + Noto Sans SC 双栈（`fonts.font.im` 镜像）；新建 `Icon.vue`（40+ 内置 SVG）替换 FontAwesome；品牌色 Material Green → Emerald `#10B981`，Gradio 风格极简布局确立。
- **修复**：计数工作台颜色通道反转致检测失准（bug006）。
- **PRD v4**（2026-08-11）：算法广场调整为三子栏目（算法管理/作物检测/作物计数）；检测工作台＝单图原子化推理，计数工作台＝完整分块计数流水线；模型动态注册 + 权重上传 + YAML 持久化。

### V0.1.1 —— 首轮联调稳定化与计数链路补全（2026-08-09）

- **计数链路补全**（`2b02ddd`）：计数接口支持 multipart 文件上传、结果加载时补全标注图 base64；前端上传预览与拖拽、统一 `DetectionViewer` 展示、小图分块提示。
- **修复**：模型清单展示异常与算法注册 500（bug001）；前端 3000 端口无数据显示（bug002）；检测推理 device 无效值（bug003）；导航栏「数据集管理」连带高亮「数据管理」（bug004）；计数与检测结果图偏蓝及分块感知（bug005）。

### V0.1.0 —— 项目启动与系统骨架（2026-08-05 ~ 08-08）

- **PRD v1.0/v2.0/v2.1**（08-05/06/08）：整合《智能甘蔗幼苗检测与计数服务系统 PRD v3.0》与《UAV 通用农作物数据集处理模块 PRD》，确立「通用大田农作物底座 + 甘蔗幼苗首个典型案例」定位、纯像素流程（不含正射拼接/GIS）、本地部署、四模块架构（数据管理/数据处理/数据集管理/算法广场）；v2.1 整合首页优化、数据管理优化、数据集单一格式管理、算法广场双子栏目与作物计数 4 项需求。
- **后端骨架**（`ca8e2ce` 起）：全局配置、CLAHE 增强工具、滑窗分块与坐标映射、全局 NMS、ModelRegistry（YAML 加载 + LRU 缓存上限 3 + 热切换）、DetectionEngine、CountingEngine（CLAHE→滑窗分块→逐块检测→坐标映射→全局 NMS→计数统计）、TaskManager（ThreadPoolExecutor 并发=1）、引擎集成与结果持久化。
- **API 层**：模型管理、检测推理、作物计数接口 + mock 数据端点；blueprint 注册与接线测试。
- **前端脚手架**（`f783b92`）：Vue 3 + Vite + Tailwind + Pinia，布局组件/API 层/Store。
- **前端页面**：首页（`8f87c17`）、算法管理三页（`cca50d4`）、检测工作台（`b7fb1c3`）、计数工作台（`c8c3aa1`）、数据管理与数据集各三页先以 mock 数据接通（`115c4a7`）。
- **修复**：SPA 客户端路由被 Flask 内置 static 端点拦截，改为 `serve_spa` 统一静态资源与回退（`e661968`）。

---

## 三、发版计划

### V0.5.8 发布清单（打包已完成，待提交/打 tag/推送）

1. 冻结验证：`cd backend; python -m pytest -q` 全绿（185 passed）→ `cd frontend; npm run build` → `electron\build-backend.ps1 -PythonExe C:\Users\lqs\UAVDesktopBuild\venv\Scripts\python.exe` 重建载荷（3,382 文件 / 851.5 MB）→ `cd electron; npm run smoke`（v0.5.8 通过）。
2. 版本号已升至 `0.5.8`（`electron/package.json` 单一来源，`backend/config.py` 回退默认值同步），本文件已更新。
3. 产物已产出：`npm run build:dir` → `win-unpacked`（3,455 文件 / 1,119.5 MB）；`npm run build:installer` → `TianJianZhiKan-v0.5.8-win-x64-setup.exe`（382,879,127 B / 365.1 MiB，SHA256 `915F39DB86917407FC5507EB1DA538E86D21BCECAEC7FF809584D576F0FB55B2`，2026-11-27 含输入源白名单修复的重建版）。
4. 安装/卸载验证已完成（静默安装 + 安装版冒烟 + 静默卸载）；窗口置顶修复已在冻结载荷实测（新窗口 `is_foreground=True`）。
5. 待执行：提交版本号与文档变更 → 打注解 tag `v0.5.8`（新编号体系首个正式 tag）→ 按 AGENTS.md Git 工作流走本地系统代理推送 → `gh release create v0.5.8` 上传安装包（Release notes 注明未签名 SmartScreen「更多信息 → 仍要运行」）。

> V0.5.7 的便携目录与安装包（`TianJianZhiKan-v0.5.7-win-x64-setup.exe`）已于 2026-11-25 产出并验证；V0.5.8 构建时 `electron/dist` 保留历史安装包，仅新增 0.5.8 产物。

### 后续版本规划（候选，按优先级）

| 版本 | 主题 | 依据 |
|---|---|---|
| V0.5.x 补丁 | zip target/artifactName 配置落地；桌面自动更新评估；发布产物 CI 化 | 报告 012（已规划未实施） |
| V0.6.0 | 数据集管理二阶段：数据集构建/拆分/多格式导出（「新建数据集」构建 tab 启用） | README「V4 第二阶段」、PRD v6 第四章 |
| V1.0.0 | 四模块全量完成、文档/测试/安装包齐备后的正式对外版本 | 本文件编号规范 |
