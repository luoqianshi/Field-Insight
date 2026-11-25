# 产品需求文档（PRD）：基于无人机图像的大田农作物智能监测与管理系统

**文档版本**：v6
**编制日期**：2026-08-13
**更新说明**：

- v5（2026-08-12）：基于模块一（数据管理）与模块四（算法广场）的完整实现，对齐实际代码与数据存储结构。数据管理存储方案调整为 YAML 持久化（data/batches.yaml），新增自动扫描、路径预检、文件夹选择对话框；算法广场 models.yaml 实际注册 6 个模型；统一目录结构对齐实际项目布局。
- v6（2026-08-13）：① 模块二（数据处理）由 Mock 更新为**完整实现**描述：ProcessingEngine + ProcessingRegistry + 10 个 API 端点，任务持久化到 `data/processing_tasks.yaml`，新增【加工数据】子模块（双 tab 布局，浏览 output/ 处理产物），子图命名规范 `{orig_stem}_tile_{seq:04d}_x{offset_x}_y{offset_y}.jpg`，output 目录按输入源分子目录；② 前端路由更新为 **17 条**（新增 `/data/processed`、`/data/processed/:id`），沉淀数据管理双 tab、4 步任务向导、侧边栏折叠/拖拽、首页流程卡片等 UI 实现；③ 模块三（数据集管理）由 Mock 占位升级为**完整设计方案**：基于真实 SSDC-UAV 自建数据集（14,220 图 / 89,136 框 / 单类别 Sugarcane Seedling），确立"导入注册 + 构建拆分双驱动、YOLO/COCO/VOC 三格式互转导出、实时统计 API + ECharts 可视化报告"的设计（详见第四章，标注 📐 设计完成，待实现）。

**文档目标**：整合原有《智能甘蔗幼苗检测与计数服务系统 PRD v3.0》与《UAV 通用农作物数据集处理模块 PRD》两份文档，重新构建一份以"大田农作物"为通用底座、"甘蔗幼苗"为首个典型应用案例的智能监测与管理系统 PRD，指导编程智能体完成系统复现与模块对接。v6 将已实现的模块一、模块二、模块四细节沉淀为最终需求基线，并给出模块三（数据集管理）的完整设计。

**取代说明**：本 PRD 完全取代上述历史 PRD 及 v6 之前版本。历史 PRD 中的能力按本 PRD 的四模块结构重新拆解归并，冲突处以本 PRD 为准。

---

## 一、系统概述

### 1.1 系统定位

本系统是一个**基于无人机图像的大田农作物智能监测与管理的本地 Web 应用**，定位为通用大田农作物底座平台，以"甘蔗幼苗检测与计数"作为首个典型应用案例。

**核心定位原则**：

- **通用底座 + 典型案例**：系统架构、数据模型、模块接口不与特定作物绑定，作物类别、类别映射、目录层级等均配置化；甘蔗幼苗作为首个落地场景验证全链路。
- **纯像素流程**：本系统不纳入正射影像拼接（ODM）、地理配准、GIS 地图可视化与地理坐标映射。数据流全程基于像素坐标，从无人机原始图片到检测结果均在像素空间内完成。
- **本地部署**：后端读取本机文件系统路径，前端提供文件浏览与参数配置 UI，面向单机/局域网使用场景。

### 1.2 系统目标

构建从无人机图像数据管理、数据处理、数据集构建到算法推理的端到端本地化工作流，形成"数据—处理—数据集—算法"的四模块闭环，支撑大田农作物的智能监测与管理。

**具体目标**：

- **数据管理**：按架次管理无人机采集的原始图片数据，提供元数据登记、自动扫描发现、本机文件系统浏览与图片预览能力。
- **数据处理**：对载入的图片进行批量 CLAHE 增强、滑窗裁切等预处理，产出待标注的原始数据集，并提供加工产物的浏览与管理。
- **数据集管理**：导入注册外部/自建标注数据集（如 SSDC-UAV），支持数据集拆分构建、YOLO/COCO/VOC 三格式互转导出与实时统计分析报告。（**本期重点设计，见第四章**）
- **算法广场**：提供模型注册、运行时热切换、单图/批量检测推理与高分辨率原图作物计数能力，输出检测与计数结果。

### 1.3 典型应用案例

以"甘蔗幼苗检测与计数"为典型应用案例。用户通过无人机采集甘蔗田航拍影像，按架次导入系统；对图片进行 CLAHE 增强与滑窗裁切预处理；将处理后的图片交付外部标注工具标注后，构建标准训练数据集（或直接导入已有的 SSDC-UAV 自建数据集）；在算法广场选择 YOLO 模型执行单图检测或高分辨率原图计数，获取甘蔗幼苗的检测框、株数与空间分布结果。

### 1.4 整体架构

系统采用四模块 + 前后端两层架构。后端为 Flask RESTful API，前端为 Vue 3 单页应用，前后端通过 HTTP JSON 交互。

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         展示层 (Presentation Layer)                      │
│   Vue 3 + Vite + ECharts                                                │
│   ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌───────────────────────────┐  │
│   │ 数据管理  │ │ 数据处理  │ │ 数据集   │ │ 算法广场                  │  │
│   │ 面板     │ │ 面板     │ │ 管理面板 │ │ 算法管理/作物检测/作物计数 │  │
│   └──────────┘ └──────────┘ └──────────┘ └───────────────────────────┘  │
└───────────────────────────────┬─────────────────────────────────────────┘
                                │ HTTP REST API (JSON / multipart)
┌───────────────────────────────▼─────────────────────────────────────────┐
│                         服务层 (Service Layer)                           │
│   Flask 2.x                                                              │
│   ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌────────────┐ │
│   │ 数据管理服务  │  │ 数据处理服务  │  │ 数据集管理   │  │ 算法广场   │ │
│   │ · 架次CRUD   │  │ · 处理引擎   │  │ 服务         │  │ 服务       │ │
│   │ · 自动扫描   │  │ · 任务注册   │  │ · Mock       │  │ · 模型管理 │ │
│   │ · 图片预览   │  │ · 加工数据   │  │   (设计完成, │  │ · 检测推理 │ │
│   │ · YAML持久化 │  │ · YAML持久化 │  │    待实现)   │  │ · 作物计数 │ │
│   └──────────────┘  └──────────────┘  └──────────────┘  └────────────┘ │
└───────────────────────────────┬─────────────────────────────────────────┘
                                │ 文件系统 / 配置文件
┌───────────────────────────────▼─────────────────────────────────────────┐
│                         数据层 (Data Layer)                              │
│   ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                 │
│   │ 原始图片仓库  │  │ 处理输出仓库  │  │ 数据集仓库   │                 │
│   │ (data/按架次) │  │ (output/任务) │  │ (datasets/)  │                 │
│   └──────────────┘  └──────────────┘  └──────────────┘                 │
│   ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                 │
│   │ 模型仓库     │  │ 配置仓库     │  │ 计数结果仓库  │                 │
│   │ (models/)    │  │ (config/)    │  │ (results/)   │                 │
│   └──────────────┘  └──────────────┘  └──────────────┘                 │
└─────────────────────────────────────────────────────────────────────────┘
```

### 1.5 技术栈规范

**后端技术栈**：

| 组件 | 技术 | 版本 | 用途 |
|------|------|------|------|
| Web 框架 | Flask | 2.2.3 | RESTful API 服务 |
| 深度学习 | PyTorch | >=1.13.0 | 模型推理 |
| 检测框架 | Ultralytics | >=8.0.0 | YOLOv5/v8/v9/v10/v11/v12 引擎 |
| 图像处理 | OpenCV | 4.7.0.72 | CLAHE 增强、图像变换、滑窗裁切 |
| 图像库 | Pillow | 9.4.0 | 图像读写、缩略图生成 |
| 数值计算 | NumPy | 1.24.2 | NMS 计算、数组操作 |
| 配置管理 | PyYAML | 6.0 | models.yaml / batches.yaml / processing_tasks.yaml 解析与持久化 |

**前端技术栈**：

| 组件 | 技术 | 版本 | 用途 |
|------|------|------|------|
| 框架 | Vue 3 | ^3.3.4 | Composition API |
| 构建工具 | Vite | ^4.4.9 | 开发服务器与构建 |
| 状态管理 | Pinia | — | 全局状态（模型/检测/计数/处理 store） |
| HTTP 客户端 | Axios | ^1.5.0 | API 请求 |
| 图表库 | ECharts | ^5.4.3 | 热力图、置信度分布、数据集统计图表可视化 |
| 图标 | 自定义 SVG Icon 组件 | — | 统一 SVG 图标（stroke-width=1.5） |

**端口与网络**：

| 服务 | 端口 | 说明 |
|------|------|------|
| 前端开发服务器 | 3000 | Vite dev server |
| 后端 API 服务 | 5000 | Flask app |
| 前端代理 | /api -> :5000 | Vite proxy 配置 |

### 1.6 系统边界

**本期纳入范围**：

- 按架次管理无人机原始图片数据（仅图像，不含多模态数据）
- 图片预处理：批量 CLAHE 增强、批量滑窗裁切、加工产物浏览与管理
- 数据集导入注册（发现 datasets/ 下已有数据集）、构建与拆分（train/val/test）、YOLO/COCO/VOC 三格式互转导出（**设计完成，待实现**）
- 数据集实时统计分析报告（**设计完成，待实现**）
- 模型注册管理、运行时热切换、动态注册（含权重上传）、单图/批量检测推理
- 高分辨率原图作物计数（株数统计、密度分布、区域热力图、置信度分布）
- 检测与计数结果可视化、计数结果落盘与历史
- 计数/检测结果数据导出（JSON、结果图、计数报告）

**本期不纳入范围**：

- 正射影像拼接（ODM）、地理配准、GIS 地图可视化、地理坐标映射
- 多模态数据（多光谱、点云等）管理
- 标注工具本体开发与标注校验/清洗/坐标回推（标注由外部工具完成）
- 模型训练、训练监控与主动学习闭环
- 检测/计数结果的多格式导出（GeoJSON/CSV/COCO 等空间格式）

### 1.7 实现状态总览

| 模块 | 后端 | 前端 | 状态 |
|------|------|------|------|
| 模块一：数据管理 | 完整实现（BatchRegistry + 9 个 API） | 完整实现（Batches、BatchNew、BatchDetail） | ✅ 已完成 |
| 模块二：数据处理 | 完整实现（ProcessingEngine + ProcessingRegistry + 10 个 API） | 完整实现（Tasks、TaskNew、TaskDetail + 加工数据 Processed、ProcessedDetail） | ✅ 已完成 |
| 模块三：数据集管理 | Mock（读取 mock/datasets.json，待按本 PRD 第四章实现） | 完整实现（Datasets、DatasetNew、DatasetDetail，待对接真实 API） | 🔶 设计完成，待实现 |
| 模块四：算法广场 | 完整实现（Registry/Detector/Counter + 10 个 API） | 完整实现（Models、ModelDetail、ModelRegister、Detect、Counting） | ✅ 已完成 |

### 1.8 首页与全局导航

**首页布局**：

- **端到端流程区**：以 4 张阶段卡片展示系统数据流（数据管理 → 数据处理 → 数据集管理 → 算法广场），每张卡片动态展示该模块的实时统计（原图数/架次数、执行次数/进行中、数据集数/样本数、模型数/激活模型），点击直达对应模块。
- **快速入口**：以带 icon 的卡片式设计展示常用操作直达入口，包括：登记新架次、新建处理任务、构建数据集、检测工作台、计数工作台。卡片采用图标 + 标题 + 简述的结构。
- **最近活动**：展示系统最近的操作记录时间线，合并处理任务与计数历史，按时间倒序取最近 4 条，含状态标识与相对时间。

**首页不包含**：系统状态监控模块（已移除，本期不纳入）。

**全局导航**：左侧固定侧边栏，包含五个一级菜单：首页、数据管理、数据处理、数据集管理、算法广场。侧边栏折叠按钮位于顶部 Logo 右侧，支持展开/折叠（240px/56px）与右边缘拖拽调宽（200-360px），状态持久化到 localStorage。算法广场下属三个子栏目（页面内 SubTabs）：算法管理、作物检测、作物计数。数据管理下属【原始数据】与【加工数据】双 tab 子栏目（页面内 DataSubTabs），【加工数据】栏目浏览 output/ 目录下的处理产物，与处理任务一一对应。

**前端路由表**（17 条路由）：

| 路径 | 名称 | 组件 | 模块 |
|------|------|------|------|
| `/` | index | Index.vue | 首页 |
| `/data/batches` | batches | Batches.vue | 数据管理 |
| `/data/batches/:id` | batch-detail | BatchDetail.vue | 数据管理 |
| `/data/batch-new` | batch-new | BatchNew.vue | 数据管理 |
| `/data/processed` | processed | Processed.vue | 数据管理 |
| `/data/processed/:id` | processed-detail | ProcessedDetail.vue | 数据管理 |
| `/process/tasks` | tasks | Tasks.vue | 数据处理 |
| `/process/tasks/:id` | task-detail | TaskDetail.vue | 数据处理 |
| `/process/task-new` | task-new | TaskNew.vue | 数据处理 |
| `/dataset/datasets` | datasets | Datasets.vue | 数据集管理 |
| `/dataset/datasets/:id` | dataset-detail | DatasetDetail.vue | 数据集管理 |
| `/dataset/dataset-new` | dataset-new | DatasetNew.vue | 数据集管理 |
| `/algo/models` | models | Models.vue | 算法广场 |
| `/algo/models/:name` | model-detail | ModelDetail.vue | 算法广场 |
| `/algo/model-register` | model-register | ModelRegister.vue | 算法广场 |
| `/algo/detect` | detect | Detect.vue | 算法广场 |
| `/algo/counting` | counting | Counting.vue | 算法广场 |

---

## 二、模块一：数据管理（✅ 已完成）

### 2.1 模块定位与职责边界

**模块定位**：数据管理模块是系统的数据入口，负责管理无人机采集的大田农作物图片数据，并提供数据浏览与图片预览能力。

**职责边界**：

- 负责：按架次登记 UAV 采集基本参数、管理本机图片存放路径、自动扫描发现数据目录、提供图片浏览与缩略图预览。
- 不负责：图片的任何处理操作（增强/裁切等由模块二负责）；非图像模态数据管理；正射拼接与地理配准。

**核心约定**：每一架次无人机采集的图像存放在一个独立文件夹，系统通过文件夹对不同架次数据进行管理。架次注册信息持久化到 `data/batches.yaml`（YAML 格式）。

### 2.2 功能需求

#### FR-D01：架次数据接入与参数登记

**需求描述**：支持登记新的 UAV 采集架次，记录本批次数据的基本参数信息与本机图片存放路径。

**输入**：架次元数据（见 2.4）、本机图片文件夹路径（支持绝对路径和相对路径）。

**处理逻辑**：

- 校验本机路径是否存在且可读
- 扫描路径下的图片文件（支持 .jpg/.jpeg/.png/.bmp/.tif/.tiff）
- 统计图片数量、总大小、格式分布
- 支持路径预检：先扫描路径再决定是否登记
- 持久化架次元数据到 `data/batches.yaml`
- 支持系统原生文件夹选择对话框（tkinter）

**输出**：架次 ID（格式 `batch_{sanitized_batch_name}`）、图片数量、总大小。

**约束**：

- 单架次图片数量上限：2000 张
- 单张图片大小上限：50MB
- 路径支持相对路径（相对于项目根目录）和绝对路径

#### FR-D02：自动扫描发现

**需求描述**：系统启动时自动扫描 `data/` 目录，发现未注册的图片文件夹。

**处理逻辑**：

- 扫描 `data/` 目录下所有子文件夹（跳过隐藏目录和 `ignored_folders` 列表中的目录）
- 检查文件夹内是否包含有效图片
- 从文件夹名推断元数据：`{crop}_{date}_{altitude}m` 格式
  - 作物类型映射：sugarcane->甘蔗、corn->玉米、wheat->小麦、rice->水稻
- 自动注册为新架次并持久化到 `batches.yaml`

**约束**：用户手动删除的自动扫描架次会被加入 `ignored_folders` 列表，防止重复注册。

#### FR-D03：架次数据检索与管理

**需求描述**：对已登记的架次数据进行检索、编辑与管理。

**功能点**：

- 按作物类型（crop_type）、采集日期（flight_date）、地块名称（plot_name）等条件检索架次
- 查看架次详情（完整元数据 + 图片统计）
- 编辑架次元数据（PUT 更新）
- 删除架次登记（不删除本机原始文件）
- 统计概览：总架次数、总图片数、总大小、格式分布、分辨率分布

#### FR-D04：文件夹与图片浏览

**需求描述**：以架次列表为入口查看已登记架次下的所有图片数据。

**功能点**：

- 顶层展示汇总统计卡片（总图片数、架次数、总大小、格式/分辨率）
- 架次列表展示所有已登记架次
- 点击架次查看该架次下的原始图片缩略图网格
- 图片浏览视图支持：缩略图网格展示、文件名/大小/尺寸显示、分页（默认每页 50 张）
- 支持单击图片查看大图预览
- 支持按文件名/大小排序（asc/desc）
- 图片预览支持三种尺寸：thumbnail（400px）、medium（1920px）、original
- 顶部检索栏，支持按采集日期、作物类型、地块名称等条件检索架次

### 2.3 UI 需求

**新增数据表单**：

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| 架次名称 | string | 是 | — | 自定义名称 |
| 作物类型 | string | 是 | 甘蔗 | 如：甘蔗、玉米、小麦、水稻 |
| 采集日期 | date | 是 | — | YYYY-MM-DD |
| 地块名称 | string | 否 | — | 采集地块标识 |
| 无人机型号 | string | 否 | DJI Mavic 3 M | 如：DJI Mavic 3 M |
| 飞行高度（米） | float | 否 | — | 采集飞行高度 |
| 航向重叠率 | float | 否 | 0.8 | 0-1 |
| 旁向重叠率 | float | 否 | 0.7 | 0-1 |
| 图片文件夹路径 | string | 是 | — | 支持绝对路径/相对路径，支持系统对话框选择 |
| 描述 | string | 否 | — | 架次描述信息 |

**文件浏览视图**：

- 顶层：汇总统计卡片（总图片数、架次数、总大小、格式/分辨率）
- 左侧：架次列表（按作物类型分组）
- 右侧：选中架次的图片缩略图网格
- 顶部：面包屑导航 + 检索栏
- 缩略图网格：响应式列数，每张图显示文件名与尺寸
- 层级结构：根目录（架次列表）-> 架次文件夹（直接包含原始图片），无航线中间分层

### 2.4 接口

**接口路由**：`GET /api/batches`

**查询参数**：`crop_type`、`flight_date`、`plot_name`

**响应**：架次列表 + 统计概览（summary），包含 total_batches、total_images、total_size_bytes、resolutions、formats。

**接口路由**：`POST /api/batches`

**请求格式**：`application/json`

```json
{
  "batch_name": "sugarcane_20260805_001",
  "crop_type": "甘蔗",
  "flight_date": "2026-08-05",
  "plot_name": "A区",
  "drone_model": "DJI Mavic 3 M",
  "flight_altitude_m": 5,
  "overlap_front": 0.8,
  "overlap_side": 0.7,
  "image_folder_path": "data/sugarcane_20260805_001"
}
```

**响应格式**：

```json
{
  "success": true,
  "data": {
    "batch_id": "batch_sugarcane_20260805_001",
    "image_count": 156,
    "total_size_mb": 1245.6
  },
  "message": "架次登记成功"
}
```

**接口路由**：`GET /api/batches/{batch_id}`

**响应**：架次完整元数据。

**接口路由**：`PUT /api/batches/{batch_id}`

**请求格式**：`application/json`（部分更新，仅传需要修改的字段）

**响应**：更新后的完整架次元数据。

**接口路由**：`DELETE /api/batches/{batch_id}`

**说明**：仅删除架次登记记录，不删除本机原始文件。自动扫描的架次删除后，其文件夹名加入 `ignored_folders` 列表。

**接口路由**：`GET /api/batches/{batch_id}/images`

**查询参数**：`page`（默认 1）、`page_size`（默认 50）、`sort_by`（filename/size）、`order`（asc/desc）

**响应**：图片文件列表（文件名、大小、宽高、格式、缩略图 URL、预览 URL）+ 分页信息。

**接口路由**：`GET /api/batches/{batch_id}/images/{filename}/preview`

**查询参数**：`size`（thumbnail/medium/original）

**响应**：图片二进制流（`image/jpeg`），带 Cache-Control 头（max-age=3600）。

**接口路由**：`POST /api/batches/scan`

**请求格式**：`application/json`

```json
{"image_folder_path": "data/sugarcane_20260805_001"}
```

**响应**：路径有效性、图片数量、总大小、格式列表。

**接口路由**：`POST /api/batches/pick-folder`

**说明**：弹出系统原生文件夹选择对话框（依赖 tkinter），返回所选绝对路径。

**响应**：`{"path": "D:/data/sugarcane"}` 或 `{"cancelled": true}`。

### 2.5 元数据结构

```python
# 架次元数据（YAML 持久化）
{
    "batch_id": str,              # 架次唯一标识，格式：batch_{sanitized_batch_name}
    "batch_name": str,            # 架次名称
    "crop_type": str,             # 作物类型（中文）
    "flight_date": str,           # 采集日期 YYYY-MM-DD
    "plot_name": str,             # 地块名称（可选，默认空字符串）
    "drone_model": str,           # 无人机型号（默认 "DJI Mavic 3 M"）
    "flight_altitude_m": float,   # 飞行高度（米，可选）
    "overlap_front": float,       # 航向重叠率（默认 0.8）
    "overlap_side": float,        # 旁向重叠率（默认 0.7）
    "image_folder_path": str,     # 图片文件夹路径（相对或绝对路径）
    "image_count": int,           # 图片数量
    "total_size_bytes": int,      # 图片总大小（字节）
    "created_at": str,            # 登记时间 ISO 8601
    "image_formats": [str],       # 包含的图片格式列表（flow style）
    "status": str,                # 状态：ready
    "description": str,           # 架次描述（可选，默认空字符串）
}
```

### 2.6 目录与存储规范

**实际存储结构**：

```
project_root/
├── data/                                  # 数据目录
│   ├── batches.yaml                       # 架次注册配置（YAML 格式）
│   ├── sugarcane_20250419_5m/             # 架次图片文件夹（80张）
│   │   ├── DJI_20250511172207_0003_D.JPG
│   │   └── ...
│   ├── sugarcane_20250419_8m/             # 架次图片文件夹（80张）
│   │   └── ...
│   └── sugarcane_20250419_10m/            # 架次图片文件夹（80张）
│       └── ...
```

**batches.yaml 结构**：

```yaml
batches:
- batch_id: batch_sugarcane_20250419_10m
  batch_name: sugarcane_20250419_10m
  crop_type: 甘蔗
  flight_date: '2025-04-19'
  plot_name: ''
  drone_model: DJI Mavic 3 M
  flight_altitude_m: 10.0
  overlap_front: 0.8
  overlap_side: 0.7
  image_folder_path: data/sugarcane_20250419_10m
  image_count: 80
  total_size_bytes: 793845760
  created_at: '2026-08-11T22:28:25'
  image_formats: [MPO]
  status: ready
  description: 自动扫描注册：甘蔗，10.0m高度采集
ignored_folders: []
```

**自动扫描文件夹名解析规则**：

- 格式：`{crop}_{date}_{altitude}m`
- 示例：`sugarcane_20250419_10m` -> crop_type="甘蔗", flight_date="2025-04-19", flight_altitude_m=10.0
- 作物类型映射：sugarcane->甘蔗、corn->玉米、wheat->小麦、rice->水稻

---

## 三、模块二：数据处理（✅ 已完成）

### 3.1 模块定位与职责边界

**模块定位**：数据处理模块负责对载入系统的单一批次或多批次无人机图片数据进行数据预处理操作，把数据处理为待标注的原始数据集，并提供加工产物的浏览与管理。

**职责边界**：

- 负责：批量 CLAHE 增强、批量滑窗裁切、处理结果预览、处理任务管理、加工产物浏览与删除。
- 不负责：标注相关操作；数据集拆分与导出（由模块三负责）；检测推理（由模块四负责）。

**输出约定**：处理后的图片存放在项目根目录的 `output` 文件夹下，每次处理以任务 ID（含时间戳）命名目录予以区分。

**后端核心模块**：

| 模块文件 | 类/功能 | 说明 |
|----------|--------|------|
| `api/processing_api.py` | processing_bp | 10 个 REST 端点，异步任务提交与查询 |
| `core/processing_engine.py` | ProcessingEngine | 无状态批处理执行器（CLAHE / 滑窗裁切 / 输入源收集） |
| `core/processing_registry.py` | ProcessingRegistry | 任务注册中心，YAML 持久化 + output/ 自扫描自愈 |
| `core/clahe.py` | apply_clahe | CLAHE 增强算法（与模块四共用） |
| `core/tiling.py` | slide_window | 滑窗分块算法（与模块四共用） |
| `core/task_manager.py` | TaskManager | 异步任务队列（processing 使用独立实例，MAX_WORKERS=1） |

### 3.2 功能需求

#### FR-P01：批量 CLAHE 增强

**需求描述**：支持对选定文件夹下的图片进行批量 CLAHE（限制对比度自适应直方图均衡化）增强操作。

**输入**：图片输入路径列表（`input_paths`，支持架次目录/加工产物目录/自定义目录，可多个）、任务名称、增强参数。

**处理逻辑**：

- 遍历各输入源下所有合法图片（.jpg/.jpeg/.png/.bmp/.tif/.tiff）
- 对每张图片应用 CLAHE 增强：BGR -> LAB 色彩空间 -> 对 L 通道应用 CLAHE -> 转回 BGR
- 灰度图直接应用 CLAHE
- 增强后图片保存到输出子目录，**保持原文件名**
- **容错策略**：单张图片读取失败或处理异常仅记录 warning 并跳过，不中断整个任务（尽力而为）
- 每成功处理一张回调进度

**参数规范**：

| 参数 | 字段名 | 默认值 | 范围 | 说明 |
|------|--------|--------|------|------|
| 阈值 | clip_limit | 2.0 | — | CLAHE 的 clipLimit（推荐 2.0-3.0） |
| 网格数量 | grid_size | [8, 8] | — | CLAHE 的 tileGridSize |
| 输入路径 | input_paths | — | — | 字符串数组，至少一个 |
| 任务名称 | name | "CLAHE 任务" | — | 可选 |

#### FR-P02：批量滑窗裁切

**需求描述**：支持对选定文件夹下的图片进行批量滑窗裁切操作。

**输入**：图片输入路径列表（同 FR-P01）、任务名称、裁切参数。

**处理逻辑**：

- 遍历各输入源下所有合法图片
- 按滑窗策略裁切：步长 = int(tile_size x (1 - overlap_ratio))
- **边缘处理**：起点序列按步长推进，若最后一个起点未贴到右/下边缘，追加一个贴边起点（length - tile_size），保证边缘区域完整覆盖且所有子图尺寸一致；边长小于等于 tile_size 时仅取起点 0
- 遍历顺序：外层 y、内层 x
- **子图命名规则**：`{orig_stem}_tile_{seq:04d}_x{offset_x}_y{offset_y}.jpg`，seq 为每张原图内部从 1 开始的序号，offset 为子图左上角像素偏移，统一输出为 .jpg
- 进度按**原图**粒度上报（非子图粒度）

**参数规范**：

| 参数 | 字段名 | 默认值 | 范围 | 说明 |
|------|--------|--------|------|------|
| 裁切大小 | tile_size | 640 | 320-1280 | 裁切图片的宽高（像素，正方形） |
| 重叠率 | overlap_ratio | 0.05 | 0-0.3 | 相邻子图的重叠比例 |
| 输入路径 | input_paths | — | — | 字符串数组，至少一个 |
| 任务名称 | name | "裁切任务" | — | 可选 |

#### FR-P03：处理结果预览

**需求描述**：支持预览处理操作后的图像。

**功能点**：

- 任务完成后以缩略图网格展示处理结果，支持分页（默认每页 50 张，上限 200）与文件名前缀过滤
- 支持单击查看大图，预览三种尺寸：thumbnail（最长边 400px）、medium（最长边 1920px）、original
- **裁切任务差异化预览**：从文件名解析原图 stem，展示首张子图（`_tile_0001_x0_y0`）作为"左上角分块预览"，并按 `filename_prefix={stem}_tile_` 过滤出同一原图的全部子图渲染缩略图网格
- **CLAHE 任务差异化预览**：展示首张图片的增强前后对比双栏（注：当前实现左右两栏均取输出目录文件，原图侧未回溯源架次原图）

#### FR-P04：多批次选择与任务管理

**需求描述**：支持对载入系统的单一批次或多批次图片数据进行处理，并对处理任务进行全生命周期管理。

**功能点**：

- **三类输入源**（按优先级判定）：
  1. **加工产物目录**：目录含 `index.json` 时识别为处理产物，读取其 sub_dirs 清单逐子目录收集图片，支持"处理结果再处理"的级联
  2. **原始架次目录**：图片直接在目录根部，`input_paths` 为数组，天然支持多架次合并处理
  3. **兜底递归**：根目录无图但有子目录时，扫描一级子目录
- 输出子目录命名：架次目录名 / `{产物目录名}_{sub_dir名}`（级联）/ `{父目录名}_{子目录名}`（兜底）；同名冲突追加 `_2`、`_3` 后缀
- 处理任务异步执行（独立 TaskManager 实例，max_workers=1），进度实时回写注册中心
- 任务列表支持按类型（clahe/crop）与状态过滤，按创建时间倒序
- **任务持久化**：所有任务记录持久化到 `data/processing_tasks.yaml`，每次状态变更立即落盘
- **状态机**：`pending -> processing -> completed / failed`；服务重启后残留的 processing 状态自动转为 `interrupted`（error="服务重启，任务被中断"），不做自动重试
- **启动自扫描自愈**：服务启动时扫描 output/ 目录，发现含 index.json 但未注册的 `clahe_*`/`crop_*` 目录，自动按 index.json 重建为 completed 任务记录（应对 YAML 丢失或手工拷贝产物场景）

### 3.3 接口（已实现）

**接口路由**：`POST /api/processing/clahe`

**请求格式**：`application/json`

```json
{
  "name": "CLAHE增强_20260812_153045",
  "input_paths": ["data/sugarcane_20250419_5m", "data/sugarcane_20250419_8m"],
  "params": {"clip_limit": 2.0, "grid_size": [8, 8]}
}
```

**响应**：`data` 为任务记录快照（status 恒为 pending），message="任务已提交"。

**错误语义**：`input_paths` 为空 -> 400"必须指定 input_paths（至少一个架次或目录）"；处理引擎未初始化（缺 cv2/numpy）-> 503。

**接口路由**：`POST /api/processing/crop`

**请求格式**：与 clahe 对称，`params` 为 `{"tile_size": 640, "overlap_ratio": 0.05}`。

**接口路由**：`GET /api/processing/tasks`

**查询参数**：`type`（clahe/crop）、`status`，可组合过滤。

**响应**：`data: {tasks: [...], total: int}`，按 created_at 倒序。

**接口路由**：`GET /api/processing/tasks/{task_id}`

**响应**：完整任务记录（status/progress/params/input_paths/output_path/sub_dirs/error 等）。不存在 -> 404。

**接口路由**：`GET /api/processing/tasks/{task_id}/files`

**查询参数**：`sub_dir`（输出子目录名）、`page`（默认 1）、`page_size`（默认 50，钳制 1-200）、`filename_prefix`（文件名前缀过滤）

**响应**：`data: {files, total, page, page_size, total_pages, sub_dir}`；每个 file 含 filename/size_bytes/width/height/format/thumbnail_url/preview_url。目录不存在 -> 404。

**接口路由**：`GET /api/processing/tasks/{task_id}/preview`

**查询参数**：`filename`（必填）、`sub_dir`、`size`（thumbnail/medium/original，默认 medium）

**响应**：图片二进制流（image/jpeg）。filename 缺失 -> 400；文件不存在 -> 404。

**接口路由**：`GET /api/processing/processed`

**说明**：扫描 output/ 物理目录（仅认 `clahe_`/`crop_` 前缀目录），与注册中心任务表融合。

**响应**：`data: {items, total}`；每项含 output_path/task_id/task_type/name/status/params/image_count/total_tiles/created_at/sub_dirs/has_task。

**接口路由**：`GET /api/processing/processed/{processed_id}`

**说明**：processed_id 即 output 下的目录名（= task_id）。不存在 -> 404。

**接口路由**：`GET /api/processing/processed/{processed_id}/files`

**说明**：复用任务文件清单逻辑，参数同 `/tasks/{task_id}/files`。

**接口路由**：`DELETE /api/processing/processed/{processed_id}`

**查询参数**：`delete_output=true` 时物理删除 output 目录（默认 false 仅删任务记录，产物保留在加工数据列表中）

**响应**：message="加工数据已删除"。不存在 -> 404。

### 3.4 任务持久化与状态机

**持久化文件**：`data/processing_tasks.yaml`，顶层结构 `{tasks: [...]}`，YAML dump 参数：allow_unicode=True、sort_keys=False、default_flow_style=False、indent=2。

**任务记录字段顺序**（固定）：

```yaml
tasks:
- task_id: crop_20260812_153045_456        # 格式：{task_type}_{YYYYMMDD}_{HHMMSS}_{毫秒:03d}
  name: 滑窗裁切_20260812_153045
  task_type: crop                           # clahe / crop
  status: completed                         # pending/processing/completed/failed/interrupted
  progress: 100
  input_paths: [data/sugarcane_20250419_5m]
  output_path: output/crop_20260812_153045_456   # 目录名与 task_id 一致
  params: {tile_size: 640, overlap_ratio: 0.05}
  total_images: 80
  processed_images: 80
  total_tiles: 504                          # 仅 crop 任务
  created_at: '2026-08-12T15:30:45'
  started_at: '2026-08-12T15:30:46'
  completed_at: '2026-08-12T15:31:20'
  error: null
  sub_dirs:
  - sub_dir: sugarcane_20250419_5m
    image_count: 80
    tiles_count: 504
```

**状态机**：

```
create_task          worker 启动           成功
pending ──────────> processing ──────────> completed (progress=100)
                        │
                        │ 异常
                        ▼
                      failed (error=str(e))

服务重启加载时：残留 processing ──> interrupted (error="服务重启，任务被中断")
```

**index.json 结构**（任务成功后写入 `output/{task_id}/index.json`）：

```json
{
  "task_id": "crop_20260812_153045_456",
  "task_type": "crop",
  "params": {"tile_size": 640, "overlap_ratio": 0.05},
  "created_at": "2026-08-12T15:30:45",
  "total_images": 80,
  "processed_images": 80,
  "sub_dirs": [{"sub_dir": "sugarcane_20250419_5m", "image_count": 80, "tiles_count": 504}],
  "total_tiles": 504
}
```

### 3.5 输出规范

**输出目录结构**：

```
project_root/
└── output/
    ├── clahe_{task_id}/                    # 目录名 == task_id，如 clahe_20260812_153000_456
    │   ├── {sub_dir}/                      # 按输入源分子目录（架次文件夹名）
    │   │   ├── DJI_0001.jpg                # CLAHE 保持原文件名
    │   │   └── ...
    │   ├── {sub_dir_2}/
    │   │   └── ...
    │   └── index.json                      # 任务参数 + 输出统计快照
    ├── crop_{task_id}/
    │   ├── {sub_dir}/
    │   │   ├── {orig_stem}_tile_0001_x0_y0.jpg
    │   │   ├── {orig_stem}_tile_0002_x608_y0.jpg
    │   │   └── ...
    │   └── index.json
    └── ...
```

**子目录命名规则汇总**：

| 输入源类型 | 子目录命名 |
|-----------|-----------|
| 原始架次目录 | 架次目录名（如 `sugarcane_20250419_5m`） |
| 加工产物目录级联 | `{产物目录名}_{原sub_dir名}` |
| 兜底一级子目录 | `{父目录名}_{一级子目录名}` |
| 同名冲突 | 追加 `_2`、`_3` 后缀 |

### 3.6 UI 需求

**任务列表页（Tasks.vue）**：

- 页内双 tab：CLAHE 增强 / 滑窗裁切（客户端过滤，各带算法描述副标题），页头展示累计执行次数
- 状态筛选下拉：全部状态 / 进行中 / 已完成 / 失败
- 分组统计卡片：当前类型的执行次数 / 已完成 / 进行中
- 任务表格：执行编号（#NNN 倒序展示号）、任务名（+参数摘要）、类型（中性灰 tag）、输入架次、输出路径、进度条、状态 badge、创建时间、详情入口
- 状态色方案（语义色）：pending/interrupted 中性灰、processing 琥珀、completed 绿、failed 红

**新建任务页（TaskNew.vue）**：

- 4 步引导式向导：选择类型 → 选择输入源 → 配置参数 → 确认提交，右侧固定任务摘要栏
- 输入源三模式：
  1. 架次选择：已登记架次表格多选（含全选），展示架次名称/作物·地块/原图数/采集高度，底部统计已选架次与合计原图数
  2. 数据选择：加工产物表格多选（任务名/类型/图片数/输出路径/生成时间）
  3. 自定义目录：路径输入框 + 系统文件夹选择对话框（pick-folder）
- 参数表单：任务名（默认自动生成）、CLAHE 的 clipLimit（默认 2.0）与网格数量（默认 '8 × 8'）、裁切的切片尺寸（默认 640）与重叠率（默认 0.05）、输出目录（提示实际写入 output/{task_id}/）
- 默认任务名格式：`CLAHE增强_YYYYMMDD_HHMMSS` / `滑窗裁切_YYYYMMDD_HHMMSS`
- 提交成功后跳转任务详情页

**任务详情页（TaskDetail.vue）**：

- 状态为 processing/pending 时每 2 秒轮询任务状态，终态停止轮询
- 统计卡片（5 张）：总图像 / 已处理 / 失败 / 成功率 / 类型指标（crop 显示子图总数，clahe 显示平均速度）
- 任务参数卡 + 快速预览（CLAHE 对比预览 / crop 同原图子图网格）+ 执行日志（前端拼装）
- failed 状态展示错误信息条

**加工数据列表页（Processed.vue）**：

- 统计卡片（4 张）：加工产物总数 / CLAHE 增强产物 / 滑窗裁切产物 / 总图片数
- 表格：任务名 / ID、类型（CLAHE 蓝 / 裁切 琥珀）、状态、输出路径、图片数、生成时间、操作（查看/删除）
- 删除语义：确认后物理删除 output 目录（delete_output=true）

**加工数据详情页（ProcessedDetail.vue）**：

- 头部：名称 + 状态 + 类型 + 生成时间 + 真实输出路径；has_task=true 时展示"查看处理任务"回链
- 参数与统计卡 + 子目录手风琴（展开时渐进式加载图片，每批 36 张，"加载更多"分页追加）

### 3.7 引擎降级与任务驱动

- 处理引擎依赖 cv2/numpy，缺失时 ProcessingEngine/ProcessingRegistry 保持 None，提交接口返回 503"处理引擎未初始化（依赖 cv2/numpy）"，其余功能不受影响
- 数据处理使用**独立的 TaskManager 实例**（processing_task_manager，max_workers=1），与算法广场的检测/计数任务队列互不抢占
- 任务提交时显式以注册中心生成的 task_id 投递线程池，保证 TaskManager 内部任务表与 YAML 注册表 ID 一致；API 查询一律以注册中心 YAML 为准

---

## 四、模块三：数据集管理（📐 设计完成，待实现）

### 4.1 模块定位与职责边界

**模块定位**：数据集管理模块负责消费外部标注工具产出的标注数据与已有的自建数据集，提供**导入注册 + 构建拆分双驱动**的数据集管理能力：① 自动发现并导入 `datasets/` 下已有的外部/自建数据集（如 SSDC-UAV 自建数据集）；② 从模块二处理产物与标注目录构建新数据集（拆分 + 标准目录生成）。同时提供 YOLO/COCO/VOC 三格式互转导出与实时统计分析报告。

**当前状态**：前端页面（Datasets.vue、DatasetNew.vue、DatasetDetail.vue）已创建完整 UI，后端 datasets_api.py 仅提供只读 Mock 接口（读取 `backend/mock/datasets.json`）。本章为完整设计方案，待实现后替换 Mock。

**职责边界**：

- 负责：数据集自动发现/导入注册/浏览/删除、数据集拆分构建（train/val/test）、YOLO/COCO/VOC 三格式互转导出、实时统计分析报告、样本浏览预览。
- 不负责：标注的创建（由外部标注工具完成）；标注校验、空标注清洗、非法框检查、子图->原图坐标回推。
- **标注来源约定**：标注由外部标注工具（如 LabelImg）完成，本模块仅消费已有标注数据，假定标注数据合法有效。

**真实数据基准**：以 `datasets/` 目录下真实的 **SSDC-UAV 自建数据集**（甘蔗幼苗无人机检测与计数数据集，14,220 张切片图 / 89,136 个标注框 / 单类别 Sugarcane Seedling）作为本模块设计与验收的基准案例，详见 4.7 节。

### 4.2 数据模型与存储

**注册表**：`datasets/datasets.yaml`（对齐 `data/batches.yaml` 的就地持久化模式），顶层结构：

```yaml
datasets:
- dataset_id: dataset_ssdc-uav_coco
  name: SSDC-UAV (COCO)
  format: COCO                    # YOLO / COCO / VOC（单数据集单格式）
  source: imported                # imported（导入注册）/ built（构建生成）
  path: datasets/SSDC-UAV_coco    # 相对项目根目录
  classes: [Sugarcane Seedling]
  splits:
    train: {image_count: 10707, object_count: 66420}
    val: {image_count: 1810, object_count: 11453}
    test: {image_count: 1703, object_count: 11263}
  image_count: 14220
  object_count: 89136
  origin_image_count: 230         # 原图级数量（可按 tile 文件名聚合时）
  image_size: 640x640             # 主导分辨率
  version: '1.0'
  description: A Dataset for Field Sugarcane Seedling Detection and Counting Based on UAV Images
  created_at: '2026-08-13T10:00:00'
  status: ready                   # ready / building / failed
ignored_folders: []
```

**dataset_meta.json**：每个数据集目录内生成/更新 `dataset_meta.json`（类别、划分统计、分辨率、来源路径、格式布局描述、统计报告缓存），解决外部数据集元信息残缺问题（SSDC-UAV 无 README/meta 文件）。

**格式自动识别规则**（用于自动发现与导入预检）：

| 格式 | 识别特征 |
|------|----------|
| COCO | 存在 `annotations/*.json` 且 JSON 含 images/annotations/categories 键；图片目录兼容 `{split}/` 直放与 `images/{split}/` 两种布局 |
| YOLO | 存在 `images/{split}` + `labels/{split}` 目录，且根目录有含 `names` 字段的 .yaml 配置文件 |
| VOC | 存在 `{split}/images` + `{split}/annotations/*.xml`，或标准 `JPEGImages/` + `Annotations/` 布局 |
| 无法识别 | 跳过并记录，不注册 |

**自动扫描**：服务启动时扫描 `datasets/` 目录发现未注册数据集（对齐模块一自动扫描模式，跳过隐藏目录与 `ignored_folders`）；用户手动删除的自动发现数据集，其文件夹名加入 `ignored_folders` 列表防止重复注册。

### 4.3 功能需求

#### FR-S01：数据集发现与导入注册

**需求描述**：支持发现并导入 `datasets/` 下或任意本机路径下已有的标注数据集（YOLO/COCO/VOC 任一格式）。

**处理逻辑**：

1. **路径预检**（scan）：识别标注格式、统计规模（图片数/框数/划分）、抽取类别列表，返回预检结果供用户确认
2. **确认导入**（import）：解析元数据并注册
   - COCO：优先读取 JSON 的 `info` 块（description/version/contributor/date_created）作为元信息来源
   - YOLO：读取 .yaml 配置文件的 `names` 字段获取类别
   - VOC：扫描 XML 标注的 `<name>` 标签聚合类别
3. 生成/更新数据集目录内的 `dataset_meta.json`
4. 注册到 `datasets/datasets.yaml`

**输入**：数据集目录路径（支持相对/绝对路径，支持 pick-folder 系统对话框）、可选的名称与描述覆盖。

**SSDC-UAV 特性处理**：

- YOLO 配置与 VOC XML 中的过期绝对路径字段（`path`）**忽略不采信**，以当前实际目录为准
- tile 文件名（`{stem}_tile_{seq}_x{ox}_y{oy}.jpg`）解析原图 stem，聚合统计原图级数量
- 空切片缺失容忍：tile 序号不连续属正常情况（无目标切片被丢弃），按实际文件统计

#### FR-S02：数据集构建与拆分

**需求描述**：从图片目录与标注目录构建标准训练数据集，按策略拆分为 train/val/test 三个子集。

**输入**：图片目录（可选模块二加工产物或自定义路径）、标注目录（单一格式，自动识别）、数据集名称、目标格式、拆分比例、拆分粒度。

**拆分策略**：

| 策略 | 说明 |
|------|------|
| 按原图粒度拆分（默认） | 按 tile 文件名解析原图 stem 分组，同一原图衍生的子图不跨集合（防止数据泄露，与 SSDC-UAV 实际划分方式一致） |
| 按图片粒度拆分 | 每张图片独立参与划分（仅当图片间无同源关系时使用） |

**默认拆分比例**：train:val:test = 7:2:1（可配置，三者之和须为 100）。

**处理逻辑**：异步任务执行（复用 TaskManager 模式），进度可查；输出到 `datasets/{name}_{format}/` 标准目录，生成 dataset_meta.json 与 list.csv（拆分清单，记录每张图所属划分），完成后自动注册。

#### FR-S03：三格式互转导出

**需求描述**：支持将任一已注册数据集导出/转换为 YOLO、COCO、VOC 任意目标格式。

**内部统一中间表示**：

```python
{
    "images": [
        {
            "filename": str,          # 图片文件名
            "width": int, "height": int,
            "boxes": [
                {"bbox": [x, y, w, h],  # 绝对像素坐标（左上角 + 宽高）
                 "class_id": int,        # 统一从 0 开始的内部类别 ID
                 "class_name": str}
            ]
        }
    ],
    "classes": [str]                   # 类别名列表，索引即内部 class_id
}
```

**处理逻辑**：

- 三种格式解析器（COCO JSON / YOLO txt+yaml / VOC XML）读入中间表示，三种格式写出器互相转换，共 6 条转换路径
- **类别 ID 映射**：COCO category_id 从 1 起，YOLO class_id 从 0 起，互转时注意差 1；VOC 按类别名映射
- YOLO 归一化坐标与绝对像素坐标互转：`x_center = (x + w/2) / width` 等
- 导出产物写入 `datasets/{name}_{目标格式小写}/` 并**自动注册为新数据集**（对齐 SSDC-UAV 三目录同源形态），不做 zip 下载
- YOLO 导出时重写配置文件的 `path` 为当前实际路径（修复过期 path 问题）
- 异步任务执行，进度可查

#### FR-S04：数据集统计分析报告

**需求描述**：对已注册数据集进行多维度实时统计分析，前端以 ECharts 图表可视化呈现。

**实现约束**：仅解析标注文件（COCO JSON / YOLO txt / VOC XML）与文件名，**不解码图片像素**，保证万级样本规模下的实时性；统计结果缓存进 dataset_meta.json（数据集变更时失效）。

**统计维度**：

| 维度 | 指标 | 说明 |
|------|------|------|
| 数据规模 | 各划分图片数、框数、原图数、非空样本数 | 按 train/val/test 汇总 |
| 类别分布 | 各类别框数、占比、均衡性 | 最大类占比 >90% 时给出失衡告警 |
| 目标框尺度 | bbox 平均宽高、面积分布直方图、COCO small/medium/large 分布 | small<32²、medium 32²~96²、large>96² |
| 图像质量 | 分辨率分布、宽高比分布 | 取自标注文件中的尺寸字段 |

**前端可视化**（ECharts）：划分占比（饼图/条形）、类别分布（柱状图）、bbox 面积分布（直方图）、small/medium/large 占比（堆叠条）。

#### FR-S05：数据集浏览与删除

**需求描述**：提供数据集样本浏览与删除管理能力。

**功能点**：

- 详情页样本浏览：按划分（train/val/test）分页展示缩略图网格（默认每页 50 张），单击查看大图预览（thumbnail/medium/original 三尺寸，复用模块一/二预览模式）
- 删除数据集：默认仅移除注册记录与 dataset_meta.json，**不删除原始文件**（对齐模块一删除语义）；`?delete_files=true` 时物理删除数据集目录
- 自动发现的数据集删除后加入 `ignored_folders`

### 4.4 接口设计

对齐 batches_api 风格：统一响应信封 `{"success", "data", "message"}`；ValueError -> 400、KeyError -> 404、创建成功 -> 201。

| 路由 | 方法 | 说明 |
|------|------|------|
| `/api/datasets` | GET | 数据集列表，`?format=` 过滤，返回 `{datasets, total, format_dist}` |
| `/api/datasets/scan` | POST | 路径预检：格式识别 + 规模统计 + 类别抽取（请求体 `{path}`） |
| `/api/datasets/import` | POST | 导入注册（请求体 `{path, name?, description?}`） |
| `/api/datasets` | POST | 构建数据集（异步任务，请求体 `{source_image_dir, source_annotation_dir, name, format, split_ratio, split_granularity}`），返回 task_id |
| `/api/datasets/tasks/{task_id}` | GET | 构建/导出任务状态与进度 |
| `/api/datasets/{dataset_id}` | GET | 数据集详情 |
| `/api/datasets/{dataset_id}` | DELETE | 删除（`?delete_files=true` 物理删除目录） |
| `/api/datasets/{dataset_id}/report` | GET | 实时统计报告（FR-S04 统计维度全量数据） |
| `/api/datasets/{dataset_id}/export` | POST | 格式转换导出（请求体 `{target_format}`），异步任务，产物注册为新数据集 |
| `/api/datasets/{dataset_id}/images` | GET | 样本分页浏览（`?split=&page=&page_size=`） |
| `/api/datasets/{dataset_id}/images/{filename}/preview` | GET | 样本预览（`?split=&size=thumbnail/medium/original`） |
| `/api/datasets/pick-folder` | POST | 系统原生文件夹选择对话框（复用模块一实现） |

**report 响应结构**：

```json
{
  "success": true,
  "data": {
    "dataset_id": "dataset_ssdc-uav_coco",
    "summary": {
      "total_images": 14220, "total_objects": 89136,
      "origin_image_count": 230, "non_empty_images": 14220,
      "splits": {"train": {"image_count": 10707, "object_count": 66420},
                  "val": {"image_count": 1810, "object_count": 11453},
                  "test": {"image_count": 1703, "object_count": 11263}}
    },
    "class_dist": [{"name": "Sugarcane Seedling", "class_id": 0, "count": 89136, "pct": 100.0}],
    "bbox_stats": {"avg_width": 41.2, "avg_height": 47.8,
                    "area_hist": [[0, 120], [200, 3400]],
                    "size_dist": {"small": 0.12, "medium": 0.75, "large": 0.13}},
    "image_stats": {"resolutions": {"640x640": 14220}, "aspect_ratios": {"1.00": 14220}},
    "warnings": [],
    "generated_at": "2026-08-13T10:30:00"
  },
  "message": "ok"
}
```

### 4.5 标准目录结构规范

**三种格式的标准目录结构**（构建输出与导入兼容的目标形态）：

```
datasets/
├── {name}_yolo/                       # YOLO 格式
│   ├── images/{train,val,test}/       # 图片按划分
│   ├── labels/{train,val,test}/       # 每图一个 .txt（归一化坐标）
│   ├── {name}.yaml                    # 配置：path/train/val/test/nc/names
│   ├── list.csv                       # 拆分清单
│   └── dataset_meta.json              # 元信息
├── {name}_coco/                       # COCO 格式
│   ├── images/{train,val,test}/       # 图片按划分（导入时兼容 {split}/ 直放布局）
│   ├── annotations/{train,val,test}.json
│   ├── list.csv
│   └── dataset_meta.json
└── {name}_voc/                        # Pascal VOC 格式
    ├── {split}/images/ + {split}/annotations/   # 导入时兼容此布局（SSDC-UAV 形态）
    ├── JPEGImages/ + Annotations/ + ImageSets/Main/   # 构建输出的标准布局
    ├── voc_classes.txt
    ├── list.csv
    └── dataset_meta.json
```

**list.csv 结构**：`filename,split,origin_stem`（origin_stem 为按 tile 文件名解析的原图 stem，无 tile 后缀时等于文件名 stem）。

### 4.6 UI 需求

**数据集列表页（Datasets.vue）**：

- 统计卡片：数据集总数、YOLO/COCO/VOC 各格式数量、总样本数
- 格式筛选按钮组（全部 / YOLO / COCO / VOC）
- 表格：数据集名称（+路径副行）、标注格式 tag、样本数、标注框数、数据划分三色条、来源 tag（导入/构建）、状态 badge、创建时间、操作（查看）
- "新建数据集"入口

**新建数据集页（DatasetNew.vue）**：入口双模式切换——

1. **导入已有数据集**：路径输入 + pick-folder 对话框 -> 扫描预检结果展示（格式/规模/类别）-> 确认导入
2. **构建新数据集**：4 步向导扩展——基础信息（名称/版本/作物类型/描述）-> 来源选择（图片目录可挑选模块二加工产物 + 标注目录，均支持 pick-folder）-> 标注格式与拆分策略（格式三选一、拆分比例默认 70/20/10、拆分粒度默认原图级）-> 目录结构预览（按格式动态渲染）

**数据集详情页（DatasetDetail.vue）**：

- 统计卡片：样本总数、训练集、验证集、测试集、标注框数
- 数据划分：三色条 + 各划分数量与占比
- 统计分析报告区（ECharts 可视化）：数据规模表格、类别分布柱状图、bbox 面积直方图、small/medium/large 占比、分辨率分布
- 格式转换导出操作：目标格式选择 -> 提交 -> 异步任务 -> 生成新数据集并跳转
- 样本浏览：划分切换 + 缩略图网格分页 + 大图预览
- 基本信息侧栏：ID、版本、格式、来源、类别数、存储路径、创建时间、描述

**前端工程调整**：

- 新增 `frontend/src/api/datasets.ts`（替换 mock.ts 中数据集部分）与 `frontend/src/stores/datasets.ts`
- Dataset 类型补齐字段：object_count、split_ratio、source_image_dir、source_annotation_dir、source、origin_image_count

### 4.7 SSDC-UAV 基准案例

`datasets/` 目录下真实的 SSDC-UAV 自建数据集（甘蔗幼苗无人机检测与计数数据集）共 4 个顶层目录，为同一批数据的多种形态：

| 目录 | 形态 | 组织方式 |
|------|------|----------|
| `SSDC-UAV_coco/` | COCO | `annotations/{train,val,test}.json` + `{train,val,test}/*.jpg`（图片直放划分目录） |
| `SSDC-UAV_yolo/` | YOLO | `images/{train,val,test}` + `labels/{train,val,test}` + `ssdc-uav.yaml` |
| `SSDC-UAV_PASCAL-VOC/` | VOC | `{split}/images/*.jpg` + `{split}/annotations/*.xml`（非标准布局，无 ImageSets） |
| `SSDC-UAV_Original/` | 原图参考集 | 30 张 5280x3956 原图（.JPG）+ 30 个原图坐标 VOC XML，仅对应测试集 |

**权威统计**（以 COCO JSON 为准）：

| 项目 | train | val | test | 合计 |
|------|-------|-----|------|------|
| 切片图片数 | 10,707 | 1,810 | 1,703 | **14,220** |
| 标注框数 | 66,420 | 11,453 | 11,263 | **89,136** |
| 对应原图数 | 173 | 29 | 28 | **230** |

- 单类别 `Sugarcane Seedling`（COCO category_id=1，YOLO class_id=0）；切片统一 640x640
- COCO annotation 含 bbox[x,y,w,h] 绝对像素、area、iscrowd=0，无 segmentation（纯目标检测）
- COCO info 块：description/version 1.0/contributor LUO Kunhong/date_created 2025-11-26（最权威元信息来源）
- **划分为原图粒度**：同一原图的所有切片在同一 split 内，不跨集合

**切片几何参数**（从文件名偏移量反推）：

- 切片尺寸 640x640，滑动步长 608（重叠 32px）
- 每张原图最多 9 列 x 7 行 = 63 片，末行/列做边界钳制
- **无目标的空切片被直接丢弃**，tile 序号不连续（聚合统计时以文件名为准，不假设 63 片齐全）

**文件名规律**：`DJI_{拍摄时间戳}_{帧号}_D_tile_{seq:04d}_x{offset_x}_y{offset_y}.jpg`，去掉 `_tile_...` 后缀即原图 stem（如 `DJI_20250511172207_0003_D`）。

**已知元信息缺陷与应对**：

| 缺陷 | 应对 |
|------|------|
| YOLO yaml 的 `path` 为过期绝对路径 | 导入时忽略，重写为当前实际路径 |
| VOC XML 的 `<path>` 为旧机器路径 | 忽略不采信 |
| 无 README / dataset_meta.json | 导入时自动生成 dataset_meta.json |
| tile 序号不连续（空片丢弃） | 按实际文件统计，原图聚合以文件名解析为准 |

---

## 五、模块四：算法广场（✅ 已完成）

### 5.1 模块定位与职责边界

**模块定位**：算法广场模块是系统的算法工程核心，负责模型注册管理、运行时热切换、单图/批量检测推理与高分辨率原图作物计数，输出基于像素坐标的检测与计数结果。

**职责边界**：

- 负责：模型注册中心管理、多引擎支持、运行时热切换、动态注册（含权重文件上传与 YAML 持久化）、单图检测推理、批量检测（异步任务）、高分辨率原图计数流水线（CLAHE 预处理 + 滑窗分块 + 批量检测 + 坐标映射 + 全局 NMS + 全局置信度二次过滤 + 计数统计）、结果可视化、计数结果落盘与历史。
- 不负责：模型训练与迭代闭环；检测/计数结果的多格式导出（GeoJSON/CSV/COCO）。
- **子栏目**：算法广场包含三个子栏目——"算法管理"（模型注册、热切换、模型详情）、"作物检测"（单图原子化检测推理工作台）、"作物计数"（高分辨率原图检测与计数案例应用，输出株数统计、密度分布、区域热力图与置信度分布）。

**后端核心模块**：

| 模块文件 | 类/功能 | 说明 |
|----------|--------|------|
| `core/registry.py` | ModelRegistry | 模型注册中心，YAML 加载/持久化，LRU 引擎缓存 |
| `core/detector.py` | DetectionEngine | 单图/批量检测推理，GPU 降级 |
| `core/counter.py` | CountingEngine | 高分辨率原图计数流水线编排 |
| `core/tiling.py` | slide_window | 滑窗分块算法 |
| `core/clahe.py` | apply_clahe | CLAHE 增强 |
| `core/nms.py` | global_nms | 全局 NMS 与置信度过滤 |
| `core/result_store.py` | save/load/list | 计数结果落盘与历史查询 |
| `core/task_manager.py` | TaskManager | 异步任务队列（MAX_WORKERS=1） |
| `core/engine.py` | init_engines | 引擎初始化与单例容器 |

### 5.2 功能需求

#### FR-A01：模型注册与管理

**需求描述**：通过 YAML 配置文件声明式管理所有检测模型，支持多引擎配置。

**配置文件**：`config/models.yaml`

**已注册模型**（6 个）：

| 序号 | name | display_name | engine | imgsz | conf | iou |
|------|------|-------------|--------|-------|------|-----|
| 1 | yolov5su-sugarcane | YOLOv5su 甘蔗幼苗 | ultralytics | 640 | 0.25 | 0.7 |
| 2 | yolov8s-sugarcane | YOLOv8s 甘蔗幼苗 | ultralytics | 640 | 0.25 | 0.7 |
| 3 | yolo11s-sugarcane | YOLOv11s 甘蔗幼苗 | ultralytics | 640 | 0.25 | 0.7 |
| 4 | yolo12s-sugarcane | YOLOv12s 甘蔗幼苗 | ultralytics | 640 | 0.25 | 0.7 |
| 5 | yolo12n-sugarcane | YOLO12n 甘蔗幼苗 | ultralytics | 640 | 0.25 | 0.7 |
| 6 | yolo26s-sugarcane | YOLO26s 甘蔗幼苗 | ultralytics | 640 | 0.25 | 0.7 |

默认激活模型：`yolo12s-sugarcane`

**模型配置字段**：

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `name` | string | 是 | — | 模型唯一标识（仅字母、数字、下划线、连字符） |
| `engine` | string | 是 | ultralytics | 引擎类型：`ultralytics` / `custom` |
| `weight` | string | 是 | — | 权重文件路径（相对项目根，如 `models/yolov8s_sugarcane.pt`） |
| `display_name` | string | 否 | name | 显示名称 |
| `category` | string | 否 | sugarcane_seedling | 模型类别（如作物类型） |
| `imgsz` | int | 否 | 640 | 输入尺寸 |
| `conf` | float | 否 | 0.25 | 置信度阈值 |
| `iou` | float | 否 | 0.7 | 推理 IoU 阈值 |
| `device` | string/null | 否 | null | 设备：`null`（自动）/ `cpu` / `0`（cuda:0） |
| `classes` | string[] | 否 | ["Sugarcane Seedling"] | 类别名称列表 |
| `max_det` | int | 否 | 300 | 单图最大检测数 |

#### FR-A02：运行时热切换与动态注册

**需求描述**：支持在系统运行时切换当前激活的检测模型，无需重启服务；支持动态注册新模型（含权重文件上传）并持久化。

**处理逻辑**：

- 模型注册中心维护所有已注册模型的元数据（由 `models.yaml` 加载），并确定默认激活模型
- **热切换**：`switch` 时预加载目标模型引擎（提前暴露加载错误，切换失败保持原激活模型）；引擎实例按需懒加载，采用 LRU 缓存，最多缓存 3 个引擎实例
- **动态注册**：运行时提交模型配置（支持 multipart 上传权重文件 `.pt/.pth/.onnx` 或 JSON 提供 weight 路径）；权重自动按模型名重命名保存到 `models/` 目录；配置自动持久化回 `models.yaml`
- **校验**：模型名称非空、仅字母数字下划线连字符、名称唯一（重名拒绝）；注册后若当前无激活模型则自动激活

#### FR-A03：单图与批量检测推理

**需求描述**：对单张图片或批量图片执行 YOLO 目标检测推理。

**单图检测（同步）**：

- 输入：multipart 上传 `image` 文件 + 推理参数
- 处理：原子化单图推理（**不做** CLAHE/分块/NMS），直接对整张图执行 YOLO 推理
- 输出：`detection_count`、`result_image`（标注图 base64）、`detection_data`（bbox 展开为 x/y/width/height）、`model_info`

**批量检测（异步）**：

- 输入：`image_dir` 目录路径 + 推理参数
- 处理：异步任务，逐图原子化检测，进度经 `task_manager` 上报
- 输出：`{results, total}`，每张图含 `filename`、`detection_count`、`detection_data`、`model_info`

**推理参数**：

| 参数 | 默认值 | 范围 | 说明 |
|------|--------|------|------|
| imgsz | 640 | — | YOLO 输入尺寸 |
| conf | 模型配置（默认 0.25） | 0-1 | 置信度阈值 |
| iou | 模型配置（默认 0.7） | 0-1 | 推理 IoU 阈值 |
| max_det | 300 | — | 单图最大检测数 |
| device | 模型配置（默认自动） | auto/cpu/cuda:0 | 推理设备 |

**设备归一化**：`auto`/`''`/`null` -> `None`（Ultralytics 自动选择，GPU 优先）；`cuda:0` -> `0`；数字字符串 -> int；`cpu` 原样保留。

**GPU 降级**：GPU 推理失败（CUDA/device 相关异常）时自动降级到 CPU 重试一次。

#### FR-A04：高分辨率原图计数流程（作物计数）

**需求描述**：对高分辨率原图执行 CLAHE 预处理、滑窗分块、批量检测、坐标映射、全局 NMS 与全局置信度二次过滤，输出株数统计与空间分布分析。

**处理逻辑**（`CountingEngine.count` 编排）：

1. **加载原图**：保持 BGR 色彩通道（与 cv2/ultralytics ndarray 期望一致）
2. **单块短路**：若原图宽高均 <= tile_size，则整图作为单块送检，自动禁用 CLAHE / 全局 conf 过滤 / 全局 NMS，避免无意义计算
3. **CLAHE 预处理（可选）**：默认关闭；开启时先对高分辨率原图整体 CLAHE（RGB->LAB->增强 L 通道->RGB），再对增强图分块
4. **滑窗分块**：`tiling.slide_window` 按 tile_size + overlap_ratio 分块，边缘行/列调整起始位置确保尺寸一致
5. **批量分块检测**：按 batch_size 分批调用批量推理；单批失败时回退批内逐块串行检测
6. **坐标映射**：子块局部坐标 + 分块偏移量 -> 原图全局坐标（`原图坐标 = 分块坐标 + 分块偏移量`）
7. **全局置信度二次过滤**：`global_conf > 0` 时按置信度过滤低分检测（默认 0.5；单块模式关闭）
8. **全局 NMS**：基于 IoU 的贪心抑制，消除重叠区域重复检测（nms_iou 默认 0.5；单块模式跳过）
9. **编号与统计**：为存活框按序编号，汇总计数总数、覆盖面积与平均密度
10. **可视化**：在原图上绘制红色检测框与编号，输出 base64 JPEG

**计数统计参数**：

| 参数 | 默认值 | 范围 | 说明 |
|------|--------|------|------|
| ground_resolution (cm/px) | 0.85 | — | 用于计算实际覆盖面积（株/m^2） |
| grid_n | 8 | — | 统计区域网格 NxN |
| global_conf | 0.5 | 0-1 | 合并后全局二次过滤阈值，<=0 关闭 |
| batch_size | 16 | >=1 | 批量分块推理的 batch 大小 |
| enhance | false（前端默认 true） | bool | 是否启用 CLAHE 预处理 |
| save_tiles | false | bool | 是否保存分块调试数据（子块原图 + 检测框可视化 + tiles_meta.json） |

**输出**：计数总数（株）、平均密度（株/m^2）、覆盖面积（m^2）、区域分布热力图（NxN 网格）、置信度分布（高/中/低）、计数结果图（红色框 + 编号）、分块级检测明细（tile_results）与 max_det 触顶告警、计数数据 JSON。

#### FR-A05：检测结果可视化

**需求描述**：在原图上绘制检测框与置信度/编号文本，生成结果图像。

**绘制规范**：

- 检测框：红色矩形框（BGR 53,57,229），线宽 2px
- 文本：作物检测绘制置信度 `{confidence:.2f}`；作物计数绘制检测框编号 `{id}`
- 输出格式：JPEG，Base64 编码（用于 API 响应与前端展示），落盘时解码为 `result_image.jpg`

### 5.3 UI 需求

**子栏目导航**：算法广场顶部提供子栏目切换 Tab，包含"算法管理"、"作物检测"、"作物计数"三个子栏目。

**算法管理 - 模型列表页**：

- 顶部统计卡片：注册模型数、支持框架数、最佳 mAP@0.5、推理设备
- 模型表格：模型名称、框架/规格、类别、推理参数、状态（已激活/已发布）、操作（详情/激活）
- "注册模型"入口按钮

**算法管理 - 模型详情页**：

- 参数卡片：imgsz、conf、iou、max_det、device、类别数
- 推理参数 / 检测类别 / 模型信息
- 操作：激活此模型、返回列表、"一键推理"跳转作物检测

**算法管理 - 注册模型页**：

- 基础配置：name、display_name、engine、category、权重文件（点击选择或拖拽，支持 .pt/.pth/.onnx，<=500MB）、classes（逗号分隔）
- 推理参数：imgsz、conf、iou、max_det、device
- 注册摘要侧栏 + 提交（校验 name 必填/格式、权重必传）

**作物检测 - 检测工作台**：

- 输入源：拖拽/点击上传单张图片（JPG/PNG/BMP/TIFF，<=50MB），展示缩略图 + 文件名 + 大小 + 尺寸
- 推理参数：检测模型下拉（默认当前激活）、conf、iou、imgsz、max_det、device
- 执行检测按钮
- 结果总览卡片：检测目标数、最高置信度、推理尺寸
- 结果展示区：原图 vs 检测标注图（DetectionViewer）
- 检测结果列表：序号、x、y、width、height、置信度、类别（按置信度降序）
- 导出：下载结果图、导出 detection_data.json

**作物计数 - 计数工作台**：

- 输入源：拖拽/点击上传原图；或本机路径（单张路径 / 目录路径，目录取首图）
- 计数参数：检测模型（默认当前激活）、conf、iou、max_det、CLAHE 预处理开关、tile_size、overlap_ratio、global_conf、nms_iou、batch_size、地面分辨率、统计区域网格
- 调试选项：保存分块调试数据（save_tiles）
- 计数总览 4 卡片：计数总数（株）、平均密度（株/m^2）、覆盖面积（m^2）、平均置信度
- 检测结果与计数标注图：原图 vs 标注图（红色框 + 编号），图像尺寸、分块数、计数
- 告警提示：单块未触发分块提示（tile_count=1）、max_det 触顶密植截断告警
- 区域分布热力图：按 NxN 网格展示各区域计数分布（ECharts Heatmap + 最大/最小/标准差）
- 置信度分布统计：高/中/低分段（ECharts）
- 历史计数案例列表：结果ID/时间、模型、计数、密度、面积、查看
- 导出：下载结果图、导出 counting_data.json、导出计数报告

### 5.4 接口

**接口路由**：`GET /api/models`

**响应格式**：

```json
{
  "success": true,
  "data": {
    "models": [
      {
        "name": "yolov8s-sugarcane",
        "display_name": "YOLOv8s 甘蔗幼苗",
        "engine": "ultralytics",
        "weight": "models/yolov8s_sugarcane.pt",
        "category": "sugarcane_seedling",
        "imgsz": 640,
        "conf": 0.25,
        "iou": 0.7,
        "device": null,
        "classes": ["Sugarcane Seedling"],
        "max_det": 300,
        "is_active": true
      }
    ],
    "current_model": "yolov8s-sugarcane"
  },
  "message": "ok"
}
```

**接口路由**：`POST /api/models/switch`

**请求格式**：

```json
{"model_name": "yolov8n-sugarcane"}
```

**响应**：`data` 含 `current_model` 与更新后的 `models` 列表。

**接口路由**：`POST /api/models/load`

**说明**：动态注册模型。支持两种 Content-Type：

- `multipart/form-data`：文本字段 + `weight_file` 文件字段（权重自动保存到 `models/`，自动按模型名重命名）
- `application/json`：仅配置（需 `weight` 为已有路径）

**multipart 请求字段**：`name`、`display_name`、`engine`、`category`、`classes`（逗号分隔字符串）、`imgsz`、`conf`、`iou`、`max_det`、`device`、`weight_file`

**校验规则**：name 非空、仅字母数字下划线连字符、名称唯一（重名拒绝）

**响应**：`data` 含 `models` 与 `current_model`；注册后配置持久化到 `models.yaml`。

**接口路由**：`POST /api/detect`

**单图同步模式**（multipart）：

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `image` | File | 是 | — | 单张待检测图像 |
| `model_name` | string | 否 | 当前激活模型 | 指定检测模型 |
| `imgsz` | int | 否 | 模型配置 | YOLO 输入尺寸 |
| `conf` | float | 否 | 模型配置 | 置信度阈值 |
| `iou` | float | 否 | 模型配置 | 推理 IoU 阈值 |
| `max_det` | int | 否 | 模型配置 | 单图最大检测数 |
| `device` | string | 否 | 模型配置 | 推理设备 |

**响应格式**：

```json
{
  "success": true,
  "data": {
    "detection_count": 247,
    "result_image": "<base64_encoded_jpeg>",
    "detection_data": [
      {
        "x": 156.0,
        "y": 234.0,
        "width": 64.0,
        "height": 64.0,
        "confidence": 0.92,
        "class": 0,
        "class_name": "Sugarcane Seedling"
      }
    ],
    "model_info": {
      "name": "yolov8s-sugarcane",
      "display_name": "YOLOv8s 甘蔗幼苗",
      "imgsz": 640
    }
  },
  "message": "ok"
}
```

**批量异步模式**（form 或 json 传 `image_dir`）：返回 `data.task_id`，异步逐图检测。

**接口路由**：`GET /api/detect/tasks/{task_id}`

**响应**：任务全量状态字典（status/progress/result/error）。

**接口路由**：`GET /api/detect/tasks/{task_id}/result`

**响应**：任务完成时返回 `{results, total}`。

**接口路由**：`POST /api/counting`

**说明**：提交作物计数任务（异步）。支持两种输入：

- multipart：`image` 文件 + 表单参数
- JSON：`image_path`（单张）或 `image_dir`（目录，取首图）

**参数**：`model_name`、`tile_size`、`overlap_ratio`、`nms_iou`、`global_conf`、`batch_size`、`ground_resolution`、`grid_n`、`conf`、`iou`、`max_det`、`imgsz`、`save_tiles`、`enhance`

**响应格式**：

```json
{
  "success": true,
  "data": {"task_id": "count_xxx"},
  "message": "ok"
}
```

**接口路由**：`GET /api/counting/tasks/{task_id}`

**响应**：任务全量状态字典（status/progress/result/error）。

**接口路由**：`GET /api/counting/tasks/{task_id}/result`

**说明**：任务完成时从 result_store 加载完整计数结果，包含落盘的 `counting_data.json`。

**响应**：

```json
{
  "success": true,
  "data": {
    "result_id": "count_20260805103000_abc123",
    "count": 247,
    "density_per_m2": 1.23,
    "area_m2": 201.5,
    "heatmap": [[12, 9, 3, ...], ...],
    "confidence_dist": {"high": 180, "mid": 50, "low": 17},
    "detection_data": [{"id": 1, "bbox": [x1,y1,x2,y2], "confidence": 0.92, "class": 0, "class_name": "Sugarcane Seedling"}],
    "annotated_image": "<base64_encoded_jpeg>",
    "model_info": {"name": "...", "display_name": "...", "imgsz": 640},
    "params_snapshot": {...},
    "image_size": [5472, 3648],
    "tile_count": 25,
    "tile_results": [{"tile_index": 0, "offset_x": 0, "offset_y": 0, "det_count": 12, "max_det_reached": false}],
    "max_det_reached_tiles": [],
    "filtered_count": 0
  },
  "message": "ok"
}
```

**接口路由**：`GET /api/counting/history`

**响应**：所有历史计数结果（meta 摘要，按 created_at 倒序）。

**接口路由**：`GET /api/health`

**响应格式**：

```json
{
  "success": true,
  "data": {
    "status": "ok",
    "version": "v1.0.0",
    "detector_ready": true,
    "registry_ready": true,
    "current_model": "yolo12s-sugarcane"
  },
  "message": "服务运行中"
}
```

### 5.5 模型配置规范

**models.yaml 完整配置**（6 个模型，`default_model` 指定默认激活模型）：

```yaml
default_model: yolo12s-sugarcane
models:
- name: yolov5su-sugarcane
  engine: ultralytics
  weight: models/yolov5su_sugarcane.pt
  display_name: YOLOv5su 甘蔗幼苗
  category: sugarcane_seedling
  imgsz: 640
  conf: 0.25
  iou: 0.7
  device: null
  classes: [Sugarcane Seedling]
  max_det: 300
- name: yolov8s-sugarcane
  engine: ultralytics
  weight: models/yolov8s_sugarcane.pt
  display_name: YOLOv8s 甘蔗幼苗
  category: sugarcane_seedling
  imgsz: 640
  conf: 0.25
  iou: 0.7
  device: null
  classes: [Sugarcane Seedling]
  max_det: 300
- name: yolo11s-sugarcane
  engine: ultralytics
  weight: models/yolo11s_sugarcane.pt
  display_name: YOLOv11s 甘蔗幼苗
  category: sugarcane_seedling
  imgsz: 640
  conf: 0.25
  iou: 0.7
  device: null
  classes: [Sugarcane Seedling]
  max_det: 300
- name: yolo12s-sugarcane
  engine: ultralytics
  weight: models/yolo12s_sugarcane.pt
  display_name: YOLOv12s 甘蔗幼苗
  category: sugarcane_seedling
  imgsz: 640
  conf: 0.25
  iou: 0.7
  device: null
  classes: [Sugarcane Seedling]
  max_det: 300
- name: yolo12n-sugarcane
  engine: ultralytics
  weight: models/yolo12n_sugarcane.pt
  display_name: YOLO12n 甘蔗幼苗
  category: sugarcane_seedling
  imgsz: 640
  conf: 0.25
  iou: 0.7
  device: null
  classes: [Sugarcane Seedling]
  max_det: 300
- name: yolo26s-sugarcane
  engine: ultralytics
  weight: models/yolo26s_sugarcane.pt
  display_name: YOLO26s 甘蔗幼苗
  category: sugarcane_seedling
  imgsz: 640
  conf: 0.25
  iou: 0.7
  device: null
  classes: [Sugarcane Seedling]
  max_det: 300
```

### 5.6 检测结果数据结构

**内部标准检测结果格式**（贯穿算法广场模块内部）：

```python
{
    "bbox": [x1, y1, x2, y2],   # float, 像素坐标, 左上角(x1,y1)+右下角(x2,y2)
    "confidence": float,          # [0, 1], 检测置信度
    "class": int,                 # 类别ID, 从0开始
    "class_name": str             # 类别名称字符串
}
```

**API 响应格式**：`/api/detect` 的 `detection_data` 将 `bbox` 展开为 `x, y, width, height` 字段（左上角坐标 + 宽高），便于前端处理。`/api/counting` 的 `detection_data` 保留内部 `bbox` 结构并附加 `id` 编号。

### 5.7 计数结果落盘规范

**计数结果持久化**（`result_store.save_counting_result`），产物目录 `results/{result_id}/`：

```
project_root/
└── results/
    └── {result_id}/                  # 如 count_20260811082749_2e0983
        ├── result_image.jpg          # 标注图（base64 解码后写入）
        ├── meta.json                 # 轻量元信息（历史列表用）
        ├── counting_data.json        # 完整计数数据（除 annotated_image）
        └── tiles/                    # 仅当 save_tiles=true
            ├── tile_0001_x0_y0.jpg
            ├── tile_0001_x0_y0_annotated.jpg
            ├── ...
            └── tiles_meta.json       # 分块元数据汇总
```

---

## 六、跨模块公共规格

### 6.1 端到端数据流

系统的数据流从 UAV 数据采集开始，经过四个阶段流转至检测/计数结果输出：

```
[阶段1: 数据管理]     [阶段2: 数据处理]      [阶段3: 数据集管理]    [阶段4: 算法广场]
     │                    │                    │                    │
     ▼                    ▼                    ▼                    ▼
原始图片        >>>   CLAHE增强/滑窗裁切  >>>  训练数据集       >>>  检测/计数结果
(按架次管理)         (output/任务ID)         (train/val/test)     (bbox+conf+class / 株数+热力图)
                       ↓                      ↑ 导入已有数据集      ↑
                  待标注原始数据集 --> 外部标注工具 --> 标注数据 ---┘
```

**阶段间衔接**：

- 阶段1->阶段2：模块一登记的架次图片路径作为模块二的输入源
- 阶段2->阶段3：模块二产出的处理结果目录（output/任务ID）作为模块三构建数据集的图片输入；标注由外部工具完成；模块三也可直接导入 datasets/ 下已有的外部数据集（如 SSDC-UAV）
- 阶段3->阶段4：模块三导出/转换的标准数据集（YOLO/COCO/VOC）可供后续训练使用（训练不在本期范围）；模块四直接对图片执行单图检测或高分辨率原图计数

### 6.2 统一目录结构规范

**实际项目目录结构**：

```
project_root/
├── backend/                          # 后端源码
│   ├── app.py                        # Flask 应用入口
│   ├── config.py                     # 全局配置常量
│   ├── api/                          # Blueprint 路由
│   │   ├── health_api.py
│   │   ├── models_api.py
│   │   ├── detect_api.py
│   │   ├── counting_api.py
│   │   ├── batches_api.py
│   │   ├── processing_api.py         # 已实现（10 端点）
│   │   └── datasets_api.py           # Mock（待按 v6 第四章设计实现）
│   ├── core/                         # 核心引擎
│   │   ├── engine.py                 # 单例容器
│   │   ├── registry.py               # 模型注册中心
│   │   ├── batch_registry.py         # 架次注册中心
│   │   ├── processing_engine.py      # 数据处理执行引擎
│   │   ├── processing_registry.py    # 处理任务注册中心
│   │   ├── detector.py               # 检测引擎
│   │   ├── counter.py                # 计数引擎
│   │   ├── tiling.py                 # 滑窗分块
│   │   ├── clahe.py                  # CLAHE 增强
│   │   ├── nms.py                    # 全局 NMS
│   │   ├── result_store.py           # 计数结果落盘
│   │   └── task_manager.py           # 异步任务队列
│   ├── mock/                         # Mock 数据
│   │   └── datasets.json
│   ├── tests/                        # 单元测试
│   └── static/                       # 前端构建产物
├── frontend/                         # 前端源码
│   └── src/
│       ├── router/index.ts           # 17 条路由
│       ├── api/                      # API 客户端
│       │   ├── client.ts
│       │   ├── batches.ts
│       │   ├── processing.ts
│       │   ├── models.ts
│       │   ├── detect.ts
│       │   ├── counting.ts
│       │   └── mock.ts
│       ├── views/                    # 页面组件
│       │   ├── index/Index.vue
│       │   ├── data/Batches.vue, BatchNew.vue, BatchDetail.vue, Processed.vue, ProcessedDetail.vue
│       │   ├── process/Tasks.vue, TaskNew.vue, TaskDetail.vue
│       │   ├── dataset/Datasets.vue, DatasetNew.vue, DatasetDetail.vue
│       │   └── algo/Models.vue, ModelDetail.vue, ModelRegister.vue, Detect.vue, Counting.vue
│       ├── components/               # 通用组件
│       │   ├── layout/AppLayout.vue, Sidebar.vue, SubTabs.vue, DataSubTabs.vue
│       │   ├── common/Icon.vue, ImageViewer.vue
│       │   └── algo/DetectionViewer.vue, HeatmapChart.vue, ConfidenceDistChart.vue
│       └── stores/                   # Pinia 状态管理（model/detect/counting/processing/mock）
├── data/                             # 数据目录（模块一 + 模块二任务注册）
│   ├── batches.yaml                  # 架次注册配置
│   ├── processing_tasks.yaml         # 处理任务注册配置（模块二）
│   ├── sugarcane_20250419_5m/        # 架次图片（80张）
│   ├── sugarcane_20250419_8m/        # 架次图片（80张）
│   └── sugarcane_20250419_10m/       # 架次图片（80张）
├── output/                           # 处理输出（模块二）
│   ├── clahe_{task_id}/              # CLAHE 产物（按输入源分子目录 + index.json）
│   └── crop_{task_id}/               # 裁切产物（子图 + index.json）
├── datasets/                         # 数据集（模块三）
│   ├── SSDC-UAV_coco/                # SSDC-UAV COCO 格式（14,220 图 / 89,136 框）
│   ├── SSDC-UAV_yolo/                # SSDC-UAV YOLO 格式
│   ├── SSDC-UAV_PASCAL-VOC/          # SSDC-UAV Pascal VOC 格式
│   └── SSDC-UAV_Original/            # SSDC-UAV 原图参考集（30 张 5280x3956）
├── models/                           # 模型权重（模块四）
│   ├── yolov5su_sugarcane.pt
│   ├── yolov8s_sugarcane.pt
│   ├── yolo11s_sugarcane.pt
│   ├── yolo12s_sugarcane.pt
│   ├── yolo12n_sugarcane.pt
│   └── yolo26s_sugarcane.pt
├── config/                           # 配置文件
│   └── models.yaml                   # 模型注册配置
└── results/                          # 计数结果（模块四）
    ├── count_20260811082749_2e0983/
    ├── count_20260811092731_02991b/
    └── count_20260811092821_e614ef/
```

### 6.3 API 设计约定

**统一响应格式**：

```json
{
  "success": true,
  "data": {},
  "message": "操作成功"
}
```

**错误响应格式**：

```json
{
  "success": false,
  "data": null,
  "message": "参数校验失败"
}
```

**错误语义**：实际实现以 `message` 承载错误信息，未严格区分错误码字段；约定错误语义如下：

| 错误语义 | 说明 |
|----------|------|
| 参数校验失败 | 缺少必填字段或格式不正确（400） |
| 资源不存在 | 架次/模型/任务/数据集等不存在（404） |
| 文件/路径不存在 | 指定的文件或目录路径无效（404） |
| 处理过程出错 | 处理操作执行异常（500） |
| 引擎未初始化 | 处理/检测/计数引擎依赖缺失时降级返回 503 或 success:false 而非 500 |
| 内部错误 | 未预期异常（500） |

**路径规范**：所有接受路径参数的接口，路径支持绝对路径或相对于项目根目录的路径。

### 6.4 配置驱动与可追溯

- 所有处理任务的参数必须持久化到任务记录中（`data/processing_tasks.yaml`）
- 每次处理输出包含配置快照（`output/{task_id}/index.json`）
- 数据集注册信息持久化到 `datasets/datasets.yaml`，每个数据集目录含 `dataset_meta.json` 元信息与 `list.csv` 拆分清单（待实现）
- 检测结果包含模型信息与推理参数
- 计数结果包含 `params_snapshot`（推理参数快照）与 `model_info`，并落盘 `meta.json`/`counting_data.json` 保证可追溯
- 架次注册信息持久化到 `data/batches.yaml`（YAML 格式）

### 6.5 引擎降级设计

- `registry` 与 `batch_registry`：仅依赖 PyYAML/Pillow/标准库，始终初始化成功
- `task_manager`：仅依赖标准库，始终初始化成功
- `processing_engine` / `processing_registry`：依赖 cv2/numpy，缺失时保持 None，提交接口返回 503，数据管理/模型管理不受影响
- `detector` / `counter`：依赖 cv2/numpy/ultralytics，缺失时以降级模式运行（保持 None），模型管理/数据管理/前端页面仍可正常使用，仅检测/计数推理功能不可用
- 检测/计数 API 在引擎未初始化时返回 success:false 而非 500

---

## 七、系统边界与技术参数

### 7.1 输入/输出边界

**系统输入**：

| 输入类型 | 格式 | 约束 |
|----------|------|------|
| UAV 原始图片 | JPEG/JPG/PNG/BMP/TIF/TIFF | 单张 <=50MB |
| 处理输入图片 | 同上 | 单次处理 <=2000 张 |
| 标注数据 | VOC XML / COCO JSON / YOLO TXT | 由外部标注工具产出 |
| 已有数据集 | YOLO/COCO/VOC 目录（如 SSDC-UAV） | 导入注册，单数据集单格式 |
| 模型权重 | .pt/.pth/.onnx (PyTorch) | 上传 <=500MB |
| 配置文件 | YAML | models.yaml / batches.yaml / processing_tasks.yaml 格式 |

**系统输出**：

| 输出类型 | 格式 | 说明 |
|----------|------|------|
| 处理后图片 | JPEG/PNG | CLAHE 增强或滑窗裁切结果（output/{task_id}/） |
| 标准数据集 | 文件系统 | VOC/COCO/YOLO 目录结构（构建或格式互转产物） |
| 统计报告 | 实时 API + ECharts 可视化 | 数据规模/类别分布/bbox 尺度/图像质量 |
| 检测结果图 | JPEG (Base64) | 红色框标注，宽度 2px |
| 检测数据 | JSON | 标准检测数据结构 |
| 计数结果图 | JPEG | 红色框 + 编号标注 |
| 计数数据/报告 | JSON | counting_data.json、计数报告 |

### 7.2 核心算法参数总表

**CLAHE 增强参数**：

| 参数 | 默认值 | 范围 | 说明 |
|------|--------|------|------|
| clipLimit | 2.0 | — | 对比度限制 |
| tileGridSize | (8, 8) | — | CLAHE 分块网格大小 |

**滑窗裁切参数**：

| 参数 | 默认值 | 范围 | 说明 |
|------|--------|------|------|
| tile_size | 640 | 320-1280 | 裁切大小（像素） |
| overlap_ratio | 0.05 | 0-0.3 | 重叠比例 |
| 步长计算 | int(tile_size x (1 - overlap_ratio)) | — | 滑窗步长 |
| 边缘处理 | 追加贴边起点确保尺寸一致 | — | 最后一行/列贴边 |

**数据集拆分参数**（待实现）：

| 参数 | 默认值 | 说明 |
|------|--------|------|
| split_ratio | 7:2:1 | train:val:test，三者之和为 100 |
| split_granularity | origin | 原图级（origin）/ 图片级（image） |

**检测推理参数**：

| 参数 | 默认值 | 范围 | 说明 |
|------|--------|------|------|
| imgsz | 640 | — | YOLO 输入尺寸 |
| conf | 0.25（模型配置） | 0-1 | 置信度阈值 |
| iou | 0.7 | 0-1 | 推理 IoU 阈值 |
| max_det | 300 | — | 单图最大检测数 |
| device | null（自动） | auto/cpu/cuda:0 | 推理设备 |
| LRU 缓存上限 | 3 | — | 引擎实例缓存数 |

**分块计数参数**：

| 参数 | 默认值 | 范围 | 说明 |
|------|--------|------|------|
| tile_size | 640 | 320-1280 | 分块大小 |
| overlap_ratio | 0.05 | 0-0.3 | 分块重叠比例 |
| nms_iou | 0.5 | 0-1 | 全局 NMS IoU 阈值 |
| global_conf | 0.5 | 0-1 | 全局置信度二次过滤阈值 |
| batch_size | 16 | >=1 | 批量分块推理 batch 大小 |
| ground_resolution | 0.85 | — | 地面分辨率 (cm/px) |
| grid_n | 8 | — | 统计区域网格 NxN |
| enhance | false | bool | 是否启用 CLAHE 预处理 |

### 7.3 性能边界

| 指标 | 目标值 | 说明 |
|------|--------|------|
| 单张 640x640 分块检测延迟 | <=500ms | GPU 推理（RTX 3060+） |
| 单张 640x640 分块检测延迟 | <=3s | CPU 推理 |
| 10000x10000 图像分块计数 | <=60s | GPU，约 25 个分块 |
| CLAHE 增强（100 张图） | <=30s | — |
| 滑窗裁切（100 张图） | <=20s | — |
| 数据集统计报告（万级样本） | <=10s | 仅解析标注文件，不解码图片 |
| API 响应超时 | 120s | 单次检测请求 |
| 并发任务 | 1 | 当前为单线程任务队列（MAX_WORKERS=1，processing 独立实例） |

### 7.4 系统依赖

| 依赖 | 类型 | 说明 |
|------|------|------|
| Ultralytics | Python 包 | YOLO 推理引擎，pip 安装 |
| PyTorch | Python 包 | 深度学习框架，需根据 GPU 环境安装对应 CUDA 版本 |
| OpenCV | Python 包 | 图像处理、CLAHE、裁切、分块 |
| Pillow | Python 包 | 图像读写、缩略图生成 |
| NumPy | Python 包 | 数值计算、NMS |
| PyYAML | Python 包 | YAML 配置解析与持久化 |
| tkinter | Python 标准库 | 系统原生文件夹选择对话框（可选） |

**依赖降级设计**：注册中心（registry）与架次注册中心（batch_registry）仅依赖 PyYAML/Pillow/标准库，始终可用；处理引擎依赖 cv2/numpy，缺失时提交接口返回 503；检测/计数引擎依赖 cv2/numpy/ultralytics，缺失时以降级模式返回提示而非 500，模型管理/数据管理仍可正常使用。

---

## 八、验收与复现检查清单

### 8.1 模块一验收（✅ 已通过）

1. **架次登记验证**：`POST /api/batches` 登记新架次，支持相对路径和绝对路径，返回 batch_id 与图片数量
2. **架次列表验证**：`GET /api/batches` 返回所有已登记架次列表 + 统计概览（summary）
3. **架次更新验证**：`PUT /api/batches/{batch_id}` 更新架次元数据
4. **图片浏览验证**：`GET /api/batches/{batch_id}/images` 分页返回图片列表，支持 sort_by/order
5. **图片预览验证**：`GET /api/batches/{batch_id}/images/{filename}/preview` 支持 thumbnail/medium/original 三种尺寸
6. **路径扫描验证**：`POST /api/batches/scan` 路径预检，返回图片数量、格式、有效性
7. **文件夹选择验证**：`POST /api/batches/pick-folder` 弹出系统对话框，返回所选路径
8. **自动扫描验证**：启动时自动扫描 data/ 目录发现未注册架次，文件夹名解析作物类型/日期/高度
9. **删除架次验证**：`DELETE /api/batches/{batch_id}` 删除登记但不删除原始文件，自动扫描架次加入 ignored_folders
10. **前端验证**：访问数据管理面板，可看到架次列表、缩略图网格、分页浏览、检索过滤

### 8.2 模块二验收（✅ 已通过）

11. **CLAHE 增强验证**：`POST /api/processing/clahe` 提交增强任务（input_paths 数组），返回 task_id（clahe_ 前缀）与 pending 状态；完成后 output/{task_id}/ 按输入源分子目录存放增强图（保持原文件名）并生成 index.json
12. **滑窗裁切验证**：`POST /api/processing/crop` 提交裁切任务，子图命名 `{orig_stem}_tile_{seq:04d}_x{ox}_y{oy}.jpg`，total_tiles 统计正确
13. **任务列表与过滤验证**：`GET /api/processing/tasks?type=&status=` 过滤生效，按 created_at 倒序
14. **任务详情验证**：`GET /api/processing/tasks/{task_id}` 返回完整任务记录；不存在返回 404
15. **文件清单验证**：`GET /api/processing/tasks/{task_id}/files` 分页返回（page_size 钳制 1-200），支持 sub_dir 与 filename_prefix 过滤
16. **结果预览验证**：`GET /api/processing/tasks/{task_id}/preview` 支持 thumbnail/medium/original 三种尺寸
17. **加工数据验证**：`GET /api/processing/processed` 扫描 output/ 目录返回产物列表（含 has_task 标志）；详情与文件清单端点可用；`DELETE` 默认仅删记录，`?delete_output=true` 物理删除目录
18. **持久化与恢复验证**：任务记录持久化到 data/processing_tasks.yaml；服务重启后残留 processing 任务转为 interrupted；output/ 中含 index.json 的未注册目录自动重建为 completed 任务
19. **多批次验证**：处理任务支持选择多个架次作为输入源（input_paths 多元素），输出按架次分子目录
20. **前端验证**：任务列表双 tab 与状态筛选、4 步新建向导（三类输入源）、任务详情 2 秒轮询与差异化预览、加工数据双 tab 页面均正常

### 8.3 模块三验收（📐 设计完成，待实现）

以 SSDC-UAV 数据集为验收基准数据：

21. **导入识别验证**：`POST /api/datasets/scan` 分别对 `datasets/SSDC-UAV_coco`、`datasets/SSDC-UAV_yolo`、`datasets/SSDC-UAV_PASCAL-VOC` 预检，均正确识别格式并返回规模统计与类别（Sugarcane Seedling）
22. **导入注册验证**：`POST /api/datasets/import` 导入三个格式目录，注册到 datasets/datasets.yaml 并生成 dataset_meta.json；COCO 导入时 info 块元信息（version 1.0、contributor）被采信
23. **统计准确性验证**：`GET /api/datasets/{dataset_id}/report` 返回的统计与权威值一致——总图片 14,220（train 10,707 / val 1,810 / test 1,703）、总框数 89,136、原图数 230、分辨率 640x640
24. **格式转换验证**：`POST /api/datasets/{dataset_id}/export` 执行 COCO->YOLO 转换，产物自动注册为新数据集；抽样比对同一图片的标注框坐标一致（注意 COCO id 从 1 起、YOLO id 从 0 起的映射）；YOLO 产物 yaml 的 path 为当前实际路径
25. **构建拆分验证**：`POST /api/datasets` 从图片目录 + 标注目录构建数据集，默认 7:2:1 拆分；原图级粒度下同一原图的 tile 不跨集合（无数据泄露）；生成 list.csv 与 dataset_meta.json
26. **样本浏览验证**：`GET /api/datasets/{dataset_id}/images?split=` 分页返回样本，preview 端点支持三种尺寸
27. **删除验证**：`DELETE /api/datasets/{dataset_id}` 默认仅删注册记录不删文件；`?delete_files=true` 物理删除；自动发现的数据集删除后加入 ignored_folders
28. **自动发现验证**：服务启动时扫描 datasets/ 目录自动发现未注册数据集（跳过无法识别的目录如 SSDC-UAV_Original）
29. **前端验证**：数据集列表统计卡片与格式筛选、新建页导入/构建双模式、详情页 ECharts 统计报告与格式转换导出均正常

### 8.4 模块四验收（✅ 已通过）

30. **模型列表验证**：`GET /api/models` 返回 6 个模型与当前激活模型
31. **热切换验证**：`POST /api/models/switch` 传入 model_name，切换激活模型并返回更新后的列表
32. **动态注册验证**：`POST /api/models/load` multipart 上传权重文件 + 配置，注册成功后写入 `config/models.yaml`，权重保存到 `models/`
33. **单图检测验证**：`POST /api/detect` 上传单张图片（multipart），返回包含 detection_count、result_image、detection_data、model_info 的 JSON
34. **批量检测验证**：`POST /api/detect` 传入 image_dir，返回 task_id，异步逐图检测，`GET /api/detect/tasks/{task_id}` 可查状态/进度
35. **作物计数验证**：`POST /api/counting` 提交原图（上传或 image_path/image_dir），返回 task_id；`GET /api/counting/tasks/{task_id}/result` 返回 count、density、heatmap、confidence_dist、annotated_image 等；`GET /api/counting/history` 返回历史
36. **结果落盘验证**：计数结果写入 `results/{result_id}/`（result_image.jpg、meta.json、counting_data.json、tiles/）
37. **健康检查验证**：`GET /api/health` 返回 `{"status":"ok", "version":"v1.0.0", "detector_ready":true, "registry_ready":true, "current_model":"..."}`

### 8.5 端到端验收

38. **前端验证**：`npm run dev` 启动前端，访问 `http://localhost:3000`，可看到数据管理（原始数据/加工数据双 tab）、数据处理、数据集管理、算法广场四个功能页面；算法广场含算法管理/作物检测/作物计数三子栏目
39. **端到端流程验证**：登记架次 -> CLAHE 增强 -> 滑窗裁切 -> 外部标注 -> 导入/构建数据集 -> 格式转换导出 -> 注册模型 -> 单图检测 -> 原图计数，全流程可跑通

---

## 九、附录

### 9.1 现有能力迁移映射

| 历史 PRD 能力 | 来源 | 归入新 PRD 模块 | 状态 |
|---------------|------|-----------------|------|
| UAV 影像上传与项目管理 | PRD1 FR-D01 | 模块一（调整为按架次管理本机路径） | ✅ |
| EXIF 元数据提取 | PRD1 FR-D03 | 模块一（简化为手动登记参数） | — |
| 正射影像拼接 | PRD1 FR-D02 | 不纳入 | — |
| 正射影像分块提取 | PRD1 FR-D04 | 模块二（调整为通用滑窗裁切） | ✅ |
| 数据存储仓库 | PRD1 FR-D05 | 跨模块公共规格 | ✅ |
| 图像分块与 CLAHE 增强 | PRD1 FR-A01 | 模块二（CLAHE）+ 模块四（分块计数） | ✅ |
| YOLO 目标检测 | PRD1 FR-A02 | 模块四 | ✅ |
| 坐标映射与全局 NMS | PRD1 FR-A03 | 模块四（作物计数） | ✅ |
| 模型注册与管理 | PRD1 FR-A04 | 模块四（算法管理） | ✅ |
| 数据集构建 | PRD1 FR-A05 | 模块三 | 📐 设计完成 |
| 数据闭环与主动学习 | PRD1 FR-A06 | 不纳入 | — |
| 计数与密度估计 | PRD1 FR-C01 | 模块四（作物计数） | ✅ |
| 空间分布分析 | PRD1 FR-C02 | 模块四（作物计数，区域热力图） | ✅ |
| 多格式数据导出 | PRD1 FR-C03 | 不纳入 | — |
| 统计报告生成 | PRD1 FR-C04 | 不纳入 | — |
| GIS 地图可视化 | PRD1 FR-U05 | 不纳入 | — |
| 多格式 UAV 影像接入 | PRD2 5.1.1 | 模块一 | ✅ |
| 可配置图像清洗 | PRD2 5.1.2 | 不纳入 | — |
| 可配置增强与归一化 | PRD2 5.1.3 | 模块二（CLAHE） | ✅ |
| 图像切块与命名标准化 | PRD2 5.1.4 | 模块二（滑窗裁切） | ✅ |
| 标注数据接入与校验 | PRD2 5.2.1 | 不纳入 | — |
| 空标注与异常标注清洗 | PRD2 5.2.2 | 不纳入 | — |
| 原图级与子图级标注映射 | PRD2 5.2.3 | 不纳入 | — |
| 自定义数据集拆分策略 | PRD2 5.2.4 | 模块三 | 📐 设计完成 |
| 主流格式导出 | PRD2 5.2.5 | 模块三（三格式互转） | 📐 设计完成 |
| 数据规模统计 | PRD2 5.3.1 | 模块三 | 📐 设计完成 |
| 类别与样本分布分析 | PRD2 5.3.2 | 模块三 | 📐 设计完成 |
| 目标框尺度分析 | PRD2 5.3.3 | 模块三 | 📐 设计完成 |
| 像素与图像质量统计 | PRD2 5.3.4 | 模块三（不含像素解码指标） | 📐 设计完成 |
| 自动化可视化分析报告 | PRD2 5.3.5 | 模块三（实时 API + ECharts） | 📐 设计完成 |

### 9.2 标注格式规范

**Pascal VOC XML 格式**：

```xml
<annotation>
  <folder>images</folder>
  <filename>DJI_0001_x0_y0_0001.jpg</filename>
  <size>
    <width>640</width>
    <height>640</height>
    <depth>3</depth>
  </size>
  <object>
    <name>Sugarcane Seedling</name>
    <bndbox>
      <xmin>156</xmin>
      <ymin>234</ymin>
      <xmax>220</xmax>
      <ymax>298</ymax>
    </bndbox>
  </object>
</annotation>
```

**COCO JSON 格式**：

```json
{
  "images": [
    {"id": 1, "file_name": "DJI_0001_x0_y0_0001.jpg", "width": 640, "height": 640}
  ],
  "annotations": [
    {"id": 1, "image_id": 1, "category_id": 1, "bbox": [156, 234, 64, 64], "area": 4096, "iscrowd": 0}
  ],
  "categories": [
    {"id": 1, "name": "Sugarcane Seedling"}
  ]
}
```

**YOLO TXT 格式**（每张图一个 `.txt` 文件，每行一条标注）：

```
0 0.523 0.612 0.100 0.094
0 0.234 0.456 0.087 0.091
```

所有坐标值归一化到 [0,1] 范围，相对于图像宽高。`class_id` 从 0 开始，与 `data.yaml` 中的 `names` 字段严格一一对应。空标注图像保留空的 `.txt` 文件。

**格式互转坐标换算**：

- COCO bbox `[x, y, w, h]`（绝对像素，左上角 + 宽高）
- YOLO：`x_center = (x + w/2) / width`、`y_center = (y + h/2) / height`、`w_norm = w / width`、`h_norm = h / height`
- VOC：`xmin = x`、`ymin = y`、`xmax = x + w`、`ymax = y + h`
- 类别 ID：COCO category_id 从 1 起，YOLO class_id 从 0 起，互转差 1；VOC 按类别名映射

### 9.3 关键参考文献

1. Ultralytics YOLO Documentation — 检测引擎 API 参考
2. COCO Common Objects in Context — 标注格式规范
3. Pascal VOC Devkit Documentation — VOC 标注格式规范
4. MatchPlant: An Open-Source Pipeline for UAV-Based Single-Plant Detection and Data Extraction (arXiv:2506.12295, 2025) — 模块化 UAV 植物检测流水线设计参考
5. Valente et al., Automated crop plant counting from very high-resolution aerial imagery, Precision Agriculture (2020) — UAV 农作物检测与计数方法参考
6. SSDC-UAV: A Dataset for Field Sugarcane Seedling Detection and Counting Based on UAV Images (v1.0, 2025-11-26, LUO Kunhong) — 本系统数据集管理模块的基准自建数据集
