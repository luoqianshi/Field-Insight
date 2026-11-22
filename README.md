# 田间智瞰 · 基于无人机图像的大田农作物智能监测与管理系统

基于无人机（UAV）图像的大田农作物智能监测平台，覆盖 **数据管理 → 数据处理 → 数据集管理 → 算法广场** 四模块闭环，同时提供 **Web 全栈** 与 **Electron 桌面端** 两种运行形态。

**当前研发阶段：V4 第一阶段**。四模块均已真实实现：数据管理（架次注册/图片浏览）、数据处理（CLAHE 增强/滑窗裁切/加工数据）、数据集管理（导入注册/统计报告/样本浏览与抽样/删除，支持 COCO/YOLO/VOC 三格式）、算法广场（11 模型注册/热切换/单图检测/作物计数）。桌面端已完成 Electron 壳 + PyInstaller 后端冻结构建；数据集 **构建/拆分/导出** 为 V4 第二阶段内容（前端入口已预留，暂禁用）。

## 双形态架构

| 形态 | 组成 | 数据根 | 适用场景 |
|------|------|--------|----------|
| **Web 全栈** | Flask :5000 单端口托管 API + Vue 构建产物 | 仓库根（`backend/config.py` 锚定） | 开发调试、服务器部署（见 [DEPLOYMENT.md](DEPLOYMENT.md)） |
| **桌面端** | Electron 壳拉起 PyInstaller 冻结后端（动态端口，仅 127.0.0.1） | `%LOCALAPPDATA%\TianJianZhiKan\` | 本机免环境安装使用 |
| **Pages 静态演示** | `npm run build:pages` + GitHub Actions 自动部署 | 无后端（仅 UI 预览，hash 路由） | 界面展示 |

桌面端关键机制（`electron/main.js` + `electron/desktop_backend.py` + `backend/config.py`）：

- **进程编排**：单实例锁 → 拉起冻结后端 exe（`--port 0` 动态选端口）→ 解析 stdout 协议 `BACKEND_PORT <port>` / `BACKEND_READY` → 载入本地页面；退出时 stdin 看门狗 + `taskkill /T` 回收进程树，杜绝孤儿进程。
- **FROZEN 双根配置**：`RESOURCE_ROOT`（只读资源：static/config 模板/内置权重，PyInstaller `_MEIPASS`）与 `PROJECT_ROOT`（可写数据根：config/models/data/output/datasets/results/logs）分离；非冻结态与 Web 开发行为完全一致。首次启动自动把内置 `models.yaml` 模板播种到用户目录（仅缺失时）。
- **冒烟测试**：`npm run smoke` 自动执行 health/models/单图推理并输出耗时与内存报告（`TJZK_SMOKE_OUT` 可指定输出路径）。

## 目录结构

```
project_root/
├── backend/                    # Flask 后端（Web/桌面共享）
│   ├── app.py                  # 应用入口（注册 Blueprint、托管静态资源、SPA 兜底）
│   ├── config.py               # FROZEN 双根配置 + 路径/端口/并发/各模块常量
│   ├── api/                    # 路由 Blueprint（全部真实实现）
│   │   ├── health_api.py       # GET /api/health
│   │   ├── models_api.py       # /api/models, /switch, /load
│   │   ├── detect_api.py       # /api/detect 单图同步+批量异步
│   │   ├── counting_api.py     # /api/counting 异步+轮询+历史
│   │   ├── batches_api.py      # /api/batches/* 架次 CRUD/图片/预览/扫描
│   │   ├── processing_api.py   # /api/processing/* CLAHE/裁切任务+加工数据
│   │   └── datasets_api.py     # /api/datasets/* 导入/统计/样本/删除（9 端点）
│   ├── core/                   # 核心引擎
│   │   ├── registry.py         # 模型注册中心（YAML+LRU+热切换+动态注册）
│   │   ├── batch_registry.py   # 架次注册中心（YAML+自动扫描+图片索引+缩略图）
│   │   ├── processing_engine.py / processing_registry.py   # 处理执行+任务持久化
│   │   ├── dataset_registry.py # 数据集注册中心（YAML+导入+样本索引+预览）
│   │   ├── dataset_analyzer.py # 数据集统计报告（类别/划分/尺寸分布等）
│   │   ├── dataset_formats.py  # COCO/YOLO/VOC 格式识别 + 统一 IR 解析
│   │   ├── detector.py         # 检测引擎（原子化单图 YOLO 推理）
│   │   ├── counter.py          # 计数引擎（CLAHE→分块→检测→NMS→计数编排）
│   │   ├── clahe.py / tiling.py / nms.py   # 共享算法工具
│   │   ├── task_manager.py     # 异步任务管理（ThreadPoolExecutor, 并发=1）
│   │   ├── engine.py           # 引擎单例容器
│   │   └── result_store.py     # 计数结果持久化
│   ├── mock/                   # 历史遗留 JSON（batches/datasets，均已被真实 API 取代，不再引用）
│   ├── tests/                  # 核心引擎 + API TDD 测试（131 项，17 个文件）
│   └── static/                 # Vue 构建产物（gitignore，由前端构建生成）
├── frontend/                   # Vue 3 前端（Web/桌面/Pages 共享）
│   ├── vite.config.ts          # 双模式构建：默认→backend/static；--mode pages→dist（仓库子路径 base）
│   ├── tailwind.config.js      # 色板（brand/ink/surface，Emerald #10B981）
│   └── src/
│       ├── router/             # 17 条路由（pages 模式自动切换 hash 路由）
│       ├── api/                # axios 模块（models/detect/counting/batches/processing/datasets）
│       ├── stores/             # Pinia（model/detect/counting/processing/datasets）
│       ├── components/         # layout / algo / common
│       └── views/              # index / algo / data / process / dataset
├── electron/                   # Electron 桌面壳（桌面端唯一方案）
│   ├── main.js / preload.js    # 主进程（进程编排/冒烟）+ 预加载
│   ├── desktop_backend.py      # 纯后端入口（动态端口+stdout 协议+stdin 看门狗，无 GUI 依赖）
│   ├── desktop_backend.spec    # PyInstaller onedir 载荷 spec
│   ├── build-backend.ps1       # 一键重建后端载荷（-PythonExe 指定构建环境）
│   ├── package.json            # electron-builder 配置（win x64 dir，extraResources→resources/backend）
│   ├── build/app.ico           # 桌面图标
│   └── backend-dist/ dist/ .cache/   # 构建产物（gitignore）
├── .github/workflows/          # deploy-frontend.yml（GitHub Pages 自动部署）
├── config/models.yaml          # 模型注册配置（11 个甘蔗模型）
├── models/                     # YOLO 权重放置目录（需手动放入）
├── data/                       # 架次登记 + 处理任务持久化（batches.yaml / processing_tasks.yaml）
├── output/                     # 数据处理产物（output/{task_id}/）
├── datasets/                   # 数据集注册（datasets.yaml）+ 导入数据集
├── results/                    # 计数结果输出
├── docs/sdd/                   # 正式 SDD 文档唯一跟踪目录（specs + plans + prd）
├── reports/                    # 报告交付物（HTML 报告/截图/架构图）
├── AGENTS.md                   # AI 编码代理项目指引（目录规范/Git 工作流）
├── DEPLOYMENT.md               # 线上部署指南（Docker/Nginx/HTTPS/CI-CD）
├── requirements.txt            # GPU 版依赖
├── requirements-cpu.txt        # CPU 版依赖（torch +cpu，约 200MB 替代 2.4GB CUDA 版）
├── start.ps1                   # Web 一键启动脚本
└── README.md
```

> 私有工作区 `.lqs/`（PRD 草稿/原型/图标设计/bug 与更新报告/AI 分析归档）与 AI 工具目录（`.trae/`、`.codex/`、`.qoder/`、`.workbuddy/` 等）不入库；大媒体工作区 `paper_chapter/`、`remotion/` 同样忽略。新文件落位规则见 [AGENTS.md](AGENTS.md)「目录规范」章节。

## 目录治理（SDD 方案）

仓库按 SDD（Spec-Driven Development）方案统一管理文档与文件落位，规则固化在 [AGENTS.md](AGENTS.md)：

- **正式 SDD 文档**（spec/plan/PRD 定稿）唯一跟踪目录为 `docs/sdd/{specs,plans,prd}/`，命名 `YYYY-MM-DD-<topic>.md`；草稿与过程版放 `.lqs/{prd,specs,plans}/`。
- **AI 分析/验证/调研产出** → `.lqs/<YYYY-MM-DD>/<topic>/outputs/`，禁止在仓库根散放分析文件或创建日期目录。
- **Bug/更新报告** → `.lqs/bug_report/`、`.lqs/update_report/`；**轻量交付物**（HTML/PNG/PPTX）→ `reports/`。
- **运行目录**（`config/ models/ data/ output/ datasets/ results/`）由 `backend/config.py` 锚定：Web 态锚定仓库根，桌面冻结态锚定用户数据根，**禁止移动/改名**。
- **Git 卫生**：`.gitignore` 运行目录必须根锚定（`/data/` 而非 `data/`），防止误忽略 `frontend/src/views/data/` 等同名子目录；禁止跟踪日志、大图片、模型权重、运行数据与私有草稿。

## 环境要求

| 依赖 | 版本 | 说明 |
|------|------|------|
| Python | 3.8+（推荐 3.8.20） | 后端运行时 |
| Node.js | 18+ | 前端构建；桌面端另需 Electron 33 / electron-builder 25（`electron/package.json`） |
| NVIDIA GPU | RTX 4060 Ti 16G（推荐） | YOLO 推理加速；CPU 亦可运行（`requirements-cpu.txt`） |
| PyTorch | ≥2.1.0 | GPU 版 `pip install -r requirements.txt`；无独显用 `requirements-cpu.txt`（torch 2.1.0+cpu） |
| Ultralytics | ≥8.4.60 | `pip install ultralytics` |
| PyInstaller | 6.22.3（仅桌面打包） | 构建环境：conda `uav-vis` 基础上 `venv --system-site-packages` + CPU 版 torch 三件套 |

> **说明**：未安装 torch/ultralytics 时，系统仍可启动，模型管理/列表、数据管理、数据集管理页面正常；检测/计数推理不可用（API 返回降级提示）。数据处理依赖 cv2/numpy，缺失时处理 API 返回 503 而非 500。

## 模型权重放置

将 11 个甘蔗幼苗检测权重放入 `models/` 目录（桌面端为用户数据根 `%LOCALAPPDATA%\TianJianZhiKan\models\`），文件名需与 `config/models.yaml` 中 `weight` 字段一致：

```
models/
├── yolov5su_sugarcane.pt      # YOLOv5su
├── yolov8s_sugarcane.pt       # YOLOv8s
├── yolo11s_sugarcane.pt       # YOLOv11s
├── yolo12s_sugarcane.pt       # YOLOv12s（默认激活）
├── yolo12n_sugarcane.pt       # YOLO12n
├── yolo26s_sugarcane.pt       # YOLO26s
├── yolo26n_sugarcane.pt       # YOLO26n
├── yolo11n_sugarcane.pt       # YOLOv11n
├── yolov8n_sugarcane.pt       # YOLOv8n
├── yolov5n_sugarcane.pt       # YOLOv5nu
└── yolo10_sugarcane.pt        # YOLOv10n
```

默认激活模型为 `yolo12s-sugarcane`，可在前端「算法广场 → 算法管理」热切换，也可动态注册新权重。

## 启动方式

### 方式一：Web 一键脚本（生产部署，单端口）

```powershell
.\start.ps1
```

脚本自动：检查环境 → 安装依赖 → 构建前端（若 `backend/static` 缺失）→ 启动 Flask :5000 → 打开浏览器。

访问 **http://localhost:5000**，Flask 同时提供 API 与前端静态资源。线上服务器部署（Docker/Nginx/HTTPS/CI-CD）见 [DEPLOYMENT.md](DEPLOYMENT.md)。

### 方式二：Web 开发模式（双服务器热更新）

```powershell
# 首次使用：环境配置
conda create -n uav-vis python=3.8.20 -y
conda activate uav-vis
pip install -r requirements.txt        # 无独显改用 requirements-cpu.txt

# 终端 1：后端
conda activate uav-vis
python -m backend.app                  # Flask :5000

# 终端 2：前端
cd frontend
npm install
npm run build                          # 建议每次改动后重新 build
npm run dev                            # Vite :3000，/api 代理到 :5000
```

访问 **http://localhost:3000**，前端改动热更新。

### 方式三：桌面端（Electron）

```powershell
# 1) 前端构建（桌面载荷前置条件，产物 backend/static/index.html 必须存在）
cd frontend
npm run build

# 2) PyInstaller 冻结后端 → electron/backend-dist/TianJianZhiKanBackend/
#    构建环境按 electron/build-backend.ps1 头部注释重建（venv + pyinstaller 6.22.3 + CPU torch）
powershell -NoProfile -ExecutionPolicy Bypass -File electron\build-backend.ps1 -PythonExe <构建环境 python.exe>

# 3) Electron 壳
cd electron
npm install
npm start                              # 开发运行（加载 backend-dist 载荷）
npm run smoke                          # 冒烟测试（health/models/单图推理 + 耗时/内存报告）
npm run build:dir                      # electron-builder 打包 → dist/win-unpacked 便携目录
npm run build:installer                # NSIS 向导式安装包 → dist/TianJianZhiKan-v{version}-win-x64-setup.exe
```

桌面端运行时数据统一写入 `%LOCALAPPDATA%\TianJianZhiKan\`（config/models/data/output/datasets/results/logs），与安装目录解耦；`models.yaml` 首次启动自动播种。安装包默认当前用户级安装、支持自定义目录、创建桌面/开始菜单快捷方式、卸载保留业务数据；完整构建与验证说明见 [docs/desktop-build-guide.md](docs/desktop-build-guide.md)。

### 方式四：GitHub Pages 静态演示

```powershell
cd frontend
npm run build:pages                    # base=仓库子路径，hash 路由，产物 frontend/dist
```

推送 master 且 `frontend/**` 有改动时，`.github/workflows/deploy-frontend.yml` 自动构建并部署到 GitHub Pages（需在仓库 Settings → Pages 将 Source 设为 GitHub Actions）。Pages 为纯静态托管，**无后端 API**，仅作界面预览。

### 前端构建（双模式）

```powershell
cd frontend
npm run build                          # 默认：产物 → backend/static/（Flask/Electron 托管）
npm run build:pages                    # Pages：产物 → frontend/dist/（静态演示）
```

## 四模块说明

| 模块 | 状态 | 说明 |
|------|------|------|
| 首页 | ✅ 真实 | 端到端流程卡片、快速入口、最近活动（数据集统计接真实 datasets store） |
| 数据管理 | ✅ 真实 | 架次登记/列表/详情、启动自动扫描注册、图片分页浏览/懒加载/缩略图、元数据编辑、删除（不删原始文件） |
| 数据处理 | ✅ 真实 | 批量 CLAHE 增强/滑窗裁切异步任务、进度轮询、结果预览、加工数据（output/ 自扫描、双 tab 浏览） |
| 数据集管理 | ✅ 真实（V4 一阶段） | COCO/YOLO/VOC 格式识别、路径预检扫描、导入注册、ECharts 统计报告、样本分页浏览/抽样/预览、删除（可选物理删除）；构建/拆分/导出为二阶段（入口预留禁用） |
| 算法广场-算法管理 | ✅ 真实 | 11 模型列表、热切换激活、动态注册、模型详情 |
| 算法广场-作物检测 | ✅ 真实 | 上传图片 → 选模型 → 同步检测 → 结果图+检测列表 |
| 算法广场-作物计数 | ✅ 真实 | 高分辨率原图 → 异步计数 → 总数/密度/热力图/置信度/标注图 |

## 核心引擎

- **DetectionEngine**：原子化单图 YOLO 推理，无状态可复用。
- **CountingEngine**：高分辨率原图编排 —— CLAHE 增强 → 滑窗分块 → 逐块检测 → 坐标映射 → 全局 NMS → 计数统计（总数/密度/面积/热力图/置信度分布）。
- **ModelRegistry**：YAML 加载 + LRU 缓存（上限 3）+ 热切换 + 动态注册。
- **BatchRegistry**：架次注册中心 —— YAML 持久化 + `data/` 自动扫描注册 + 图片索引（Pillow 读尺寸）+ 动态缩略图/预览生成 + ignored_folders 忽略机制。
- **ProcessingEngine / ProcessingRegistry**：无状态批量 CLAHE/裁切执行器（单图失败隔离，输出 `output/{task_id}/` + `index.json` 快照）+ YAML 任务持久化与 `output/` 自扫描重建 + 任务状态机。
- **DatasetRegistry**：数据集注册中心 —— `datasets/datasets.yaml` 持久化 + `datasets/` 自动发现（ignored_folders 忽略机制）+ 路径预检扫描 + 原位导入注册 + 样本索引/分页/抽样 + 缩略图预览。
- **DatasetAnalyzer + dataset_formats**：COCO/YOLO/VOC 三格式自动识别并解析为统一 IR，生成统计报告（类别分布/划分统计/尺寸分布等，支持强制重算）。
- **TaskManager**：ThreadPoolExecutor（并发=1）+ 内存任务表，支持进度回调；处理队列独立（max_workers=1）。

## 技术栈

- **后端**：Flask 2.2.3 · Ultralytics · PyTorch · OpenCV · Pillow · NumPy · PyYAML
- **前端**：Vue 3 · Vite · Tailwind CSS · Pinia · Vue Router · ECharts · Axios · 自定义 SVG 图标组件
- **桌面端**：Electron 33 · electron-builder 25 · PyInstaller 6.22.3（onedir 冻结后端）
- **CI/CD**：GitHub Actions（GitHub Pages 前端自动部署）

## 测试

```powershell
cd backend
python -m pytest -v            # 131 项测试（17 个测试文件）
```

覆盖：检测/计数/注册中心/任务管理/缩略图、架次注册（自动扫描/CRUD/路径校验/分页/忽略列表）、处理引擎（CLAHE/裁切/命名规范/错误隔离）、处理注册（YAML 持久化/自扫描/状态机）、处理 API（端点/降级 503）、端到端处理集成、数据集（COCO/YOLO/VOC 格式解析/导入注册/统计报告/API 端点）、SPA 路由回退回归。

## API 概览

统一响应信封：`{ "success": bool, "data": <data>|null, "message": str }`

### 算法广场

| 方法 | 路由 | 说明 |
|------|------|------|
| GET | `/api/health` | 健康检查 + 引擎状态 |
| GET | `/api/models` | 模型列表 + 当前激活 |
| POST | `/api/models/switch` | 热切换激活模型 |
| POST | `/api/models/load` | 动态注册模型 |
| POST | `/api/detect` | 单图同步 / 批量异步检测 |
| GET | `/api/detect/tasks/{id}` | 批量检测任务进度 |
| POST | `/api/counting` | 作物计数（异步） |
| GET | `/api/counting/tasks/{id}` | 计数任务进度 |
| GET | `/api/counting/tasks/{id}/result` | 计数报告 |
| GET | `/api/counting/history` | 历史计数 |

### 数据管理

| 方法 | 路由 | 说明 |
|------|------|------|
| GET | `/api/batches` | 架次列表（支持 crop_type/flight_date/plot_name 过滤）+ 汇总 |
| POST | `/api/batches` | 注册新架次 |
| GET | `/api/batches/{id}` | 架次详情 |
| PUT | `/api/batches/{id}` | 更新架次元数据 |
| DELETE | `/api/batches/{id}` | 删除架次登记（不删原始文件） |
| GET | `/api/batches/{id}/images` | 架次图片分页列表 |
| GET | `/api/batches/{id}/images/{filename}/preview` | 图片预览（?size=thumbnail\|medium\|original） |
| POST | `/api/batches/scan` | 路径预检扫描（表单扫描按钮） |
| POST | `/api/batches/pick-folder` | 目录选择 |

### 数据处理

| 方法 | 路由 | 说明 |
|------|------|------|
| POST | `/api/processing/clahe` | 提交 CLAHE 任务（异步） |
| POST | `/api/processing/crop` | 提交裁切任务（异步） |
| GET | `/api/processing/tasks` | 任务列表（?type=&status= 过滤） |
| GET | `/api/processing/tasks/{id}` | 任务详情 |
| GET | `/api/processing/tasks/{id}/files` | 结果文件清单（分页） |
| GET | `/api/processing/tasks/{id}/preview` | 结果图片预览 |
| GET | `/api/processing/processed` | 加工数据列表 |
| GET | `/api/processing/processed/{id}` | 加工数据详情 |
| GET | `/api/processing/processed/{id}/files` | 加工数据文件清单 |
| DELETE | `/api/processing/processed/{id}` | 删除加工数据（?delete_output=true） |

### 数据集管理（V4 一阶段）

| 方法 | 路由 | 说明 |
|------|------|------|
| GET | `/api/datasets` | 数据集列表（?format= 过滤）+ 格式分布 |
| POST | `/api/datasets/scan` | 路径预检：格式识别 + 轻量统计 |
| POST | `/api/datasets/import` | 导入注册（name/description 可选） |
| GET | `/api/datasets/{id}` | 数据集详情 |
| DELETE | `/api/datasets/{id}` | 删除登记（?delete_files=true 物理删除） |
| GET | `/api/datasets/{id}/report` | 统计报告（?force=true 强制重算） |
| GET | `/api/datasets/{id}/images` | 样本分页浏览（?split=&page=&page_size=&sample_ratio= 抽样） |
| GET | `/api/datasets/{id}/images/{filename}/preview` | 样本预览（?split=&size=） |
| POST | `/api/datasets/pick-folder` | 系统原生文件夹选择对话框 |

## 算法默认参数

> 以下参数汇总自三个来源：**配置** `config/models.yaml`、**前端表单默认值** `frontend/src/views/algo/{Detect,Counting}.vue`、**引擎代码默认值** `backend/core/{detector,counter,clahe,tiling,nms}.py`。
> 参数生效优先级（detector/counter 内逻辑）：请求参数 > 模型配置（models.yaml）> 引擎内置默认值。
> ⚠️ 多处来源默认值**不一致**，下表已并列标注，请据此与你的算法工程统一对齐。

### 1）模型级推理参数（config/models.yaml，11 个甘蔗模型共用）

| 参数 | 值 | 说明 |
|------|-----|------|
| imgsz | 640 | 推理输入尺寸 |
| conf | 0.25 | 检测置信度阈值 |
| iou | 0.7 | NMS IoU 阈值（模型内，ultralytics 推理阶段） |
| max_det | 300 | 单张最大检测框数 |
| device | null（自动） | GPU 优先，无则 CPU |

### 2）单图检测（算法广场-单图检测，Detect.vue）

| 参数 | 前端表单默认 | models.yaml | 引擎内置默认(detector.py) | 说明 |
|------|------|------|------|------|
| conf | 0.25 | 0.25 | 0.25 | 已统一 |
| iou | 0.7 | 0.7 | 0.7 | 已统一 |
| imgsz | 640 | 640 | 640 | 一致 |
| max_det | 300 | 300 | 300 | 一致 |
| device | 空 | null | null | 自动 |

> 已移除单图检测前端的分块参数（overlap_ratio / nms_iou）与 half 字段，单图无分块逻辑，与后端 detect_api 仅解析 imgsz/conf/iou/max_det/device 保持一致。

### 3）作物计数（算法广场-作物计数，Counting.vue / counter.py）

| 参数 | 前端表单默认 | 引擎内置默认(counter.py) | 说明 |
|------|------|------|------|
| conf | 0.25 | （走 detector，见上） | 逐块检测置信度 |
| iou | 0.7 | （走 detector，见上） | 逐块检测 NMS |
| imgsz | — | 640 | 逐块检测推理尺寸 |
| tile_size | 640 | 640 | 滑窗分块边长（px） |
| overlap_ratio | 0.05 | 0.05 | 分块重叠比例，步长=tile_size×(1-overlap) |
| nms_iou | 0.5 | 0.5 | **全局 NMS**（合并分块边界重复框），nms.py 默认 0.5 |
| max_det | 300 | 300 | 已统一 |
| global_conf | 0.5 | 0.0（关闭） | 全局二次过滤阈值（合并后按置信度过滤） |
| batch_size | 16 | 8 | 批量分块推理 batch 大小 |
| enhance | true | false | 是否启用 CLAHE 预处理（单块模式自动禁用） |
| save_tiles | false | false | 是否保存分块调试数据（子块原图+标注+tiles_meta.json） |
| ground_resolution | 0.85 | 0.85 | 地面分辨率 cm/px，用于面积/密度换算 |
| grid_n | 8 | 8 | 热力图网格 n×n |

### 4）预处理 / 后处理常量（引擎代码内置，不可配置）

| 参数 | 值 | 位置 |
|------|-----|------|
| CLAHE clip_limit | 2.0 | clahe.py |
| CLAHE grid_size | (8, 8) | clahe.py |
| 全局 NMS IoU | 0.5 | nms.py（与计数 nms_iou 同源） |
| 置信度分档（high/mid/low） | ≥0.7 / ≥0.4 / 其余 | counter.py `_conf_dist` |

### 5）后端并发 / 资源常量（config.py）

| 参数 | 值 | 说明 |
|------|-----|------|
| MAX_WORKERS | 1 | TaskManager 并发=1（检测/计数队列） |
| LRU_CACHE_SIZE | 3 | 模型引擎实例缓存上限 |
| MAX_IMAGES_PER_BATCH | 2000 | 单架次图片数量上限 |
| MAX_IMAGE_SIZE_BYTES | 50MB | 单张图片大小上限 |
| THUMBNAIL_MAX_SIZE / PREVIEW_MEDIUM_SIZE | 400 / 1920 | 图片预览尺寸（px） |
| HOST / PORT / DEBUG | Web：0.0.0.0:5000/debug；桌面：127.0.0.1 动态端口/关 debug | FROZEN 门控 |

### 待统一的对齐点

1. ~~**conf**~~：✅ 已按 models.yaml=0.25 统一（前端表单 + detector 内置默认均已修正）。
2. ~~**iou**~~：✅ 已按 models.yaml=0.7 统一（前端表单 + detector 内置默认均已修正）。
3. ~~**max_det**~~：✅ 计数前端已从 500 对齐为配置 300。
4. ~~**单图检测分块**~~：✅ 已从前端移除 overlap_ratio / nms_iou（单图无分块逻辑，后端也未接入）。
5. ~~**half**~~：✅ 已从前端与 models.yaml 移除 half 字段（FP16 未启用，detector.py 仅透传 imgsz/conf/iou/max_det/device）。
6. 🔶 **计数增强开关（enhance）**：前端表单默认 `true`（开启 CLAHE），引擎内置默认 `false`（关闭，训练未用 CLAHE 致分布偏移）。请与算法工程确认统一方向。
7. 🔶 **计数 batch_size**：前端默认 `16`，引擎内置默认 `8`，请统一。
8. 🔶 **计数 global_conf**：前端默认 `0.5`，引擎内置默认 `0.0`（关闭全局二次过滤），请统一。

## 数据目录约定

Web 态（仓库根）与桌面态（`%LOCALAPPDATA%\TianJianZhiKan\`）结构一致：

```
data/
├── batches.yaml               # 架次登记（启动自动扫描 data/ 一级子目录并注册）
├── processing_tasks.yaml      # 处理任务记录
└── {crop}_{date}_{altitude}m/ # 原始架次目录（文件夹名自动推断元数据）

output/
└── {task_type}_{ts}_{ms}/     # 处理产物目录，目录名 = task_id
    ├── {sub_dir}/             # 按输入源（架次/自定义目录）分子目录
    │   ├── DJI_0001.jpg        # CLAHE：保持原文件名
    │   └── {stem}_tile_{seq:04d}_x{ox}_y{oy}.jpg   # 裁切：子图命名规范
    └── index.json             # 任务参数 + 输出统计快照

datasets/
├── datasets.yaml              # 数据集注册表（导入登记 + 自动发现 + 统计缓存）
└── {数据集目录}/               # 放置于此的 COCO/YOLO/VOC 数据集自动发现注册；
                               # 导入也可原位引用外部路径（不复制，向源目录写 dataset_meta.json）
```

## 后续阶段

- **V4 第二阶段**：数据集构建/拆分/多格式导出（前端「新建数据集」已预留双 tab，构建入口暂禁用）。
- **桌面端**：已提供 NSIS 向导式安装包（v1.1.0 起），自动更新尚未配置；构建与安装说明见 [docs/desktop-build-guide.md](docs/desktop-build-guide.md)。

## 相关文档

- [AGENTS.md](AGENTS.md) —— AI 编码代理项目指引（目录规范/代码约定/Git 工作流）
- [docs/desktop-build-guide.md](docs/desktop-build-guide.md) —— 桌面端构建、安装包生成与验证说明
- [docs/sdd/](docs/sdd/) —— 正式 SDD 文档（数据管理/数据处理/数据集管理 specs + plans）