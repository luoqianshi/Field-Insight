# 产品需求文档（PRD）：基于无人机图像的大田农作物智能监测与管理系统

**文档版本**：v2.0
**编制日期**：2026-08-06
**文档目标**：整合原有《智能甘蔗幼苗检测与计数服务系统 PRD v3.0》与《UAV 通用农作物数据集处理模块 PRD》两份文档，重新构建一份以"大田农作物"为通用底座、"甘蔗幼苗"为首个典型应用案例的智能监测与管理系统 PRD，指导编程智能体完成系统复现与模块对接。

**取代说明**：本 PRD 完全取代上述两份历史 PRD。历史 PRD 中的能力按本 PRD 的四模块结构重新拆解归并，冲突处以本 PRD 为准。

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

- **数据管理**：按架次管理无人机采集的原始图片数据，提供元数据登记与本机文件系统浏览能力。
- **数据处理**：对载入的图片进行批量 CLAHE 增强、滑窗裁切等预处理，产出待标注的原始数据集。
- **数据集管理**：消费外部标注工具产出的标注数据，完成数据集拆分、多格式导出与统计分析报告。
- **算法广场**：提供模型注册、运行时热切换与单图/批量检测推理能力，输出检测结果。

### 1.3 典型应用案例

以"甘蔗幼苗检测与计数"为典型应用案例。用户通过无人机采集甘蔗田航拍影像，按架次导入系统；对图片进行 CLAHE 增强与滑窗裁切预处理；将处理后的图片交付外部标注工具标注后，构建标准训练数据集；在算法广场选择 YOLO 模型执行检测推理，获取甘蔗幼苗的检测框与计数结果。

### 1.4 整体架构

系统采用四模块 + 前后端两层架构。后端为 Flask RESTful API，前端为 Vue 3 单页应用，前后端通过 HTTP JSON 交互。

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         展示层 (Presentation Layer)                      │
│   Vue 3 + Vite + ECharts                                                │
│   ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐                  │
│   │ 数据管理  │ │ 数据处理  │ │ 数据集   │ │ 算法广场 │                  │
│   │ 面板     │ │ 面板     │ │ 管理面板 │ │ 工作台   │                  │
│   └──────────┘ └──────────┘ └──────────┘ └──────────┘                  │
└───────────────────────────────┬─────────────────────────────────────────┘
                                │ HTTP REST API (JSON / multipart)
┌───────────────────────────────▼─────────────────────────────────────────┐
│                         服务层 (Service Layer)                           │
│   Flask 2.x                                                              │
│   ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌────────────┐ │
│   │ 数据管理服务  │  │ 数据处理服务  │  │ 数据集管理   │  │ 算法广场   │ │
│   │ · 架次登记   │  │ · CLAHE 增强 │  │ 服务         │  │ 服务       │ │
│   │ · 文件浏览   │  │ · 滑窗裁切   │  │ · 拆分构建   │  │ · 模型管理 │ │
│   │ · 元数据管理 │  │ · 处理预览   │  │ · 格式导出   │  │ · 检测推理 │ │
│   │              │  │ · 任务管理   │  │ · 统计分析   │  │ · 结果可视化│ │
│   └──────────────┘  └──────────────┘  └──────────────┘  └────────────┘ │
└───────────────────────────────┬─────────────────────────────────────────┘
                                │ 文件系统 / 配置文件
┌───────────────────────────────▼─────────────────────────────────────────┐
│                         数据层 (Data Layer)                              │
│   ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                 │
│   │ 原始图片仓库  │  │ 处理输出仓库  │  │ 数据集仓库   │                 │
│   │ (按架次组织)  │  │ (output/时间戳)│  │ (train/val/  │                 │
│   │              │  │              │  │  test)       │                 │
│   └──────────────┘  └──────────────┘  └──────────────┘                 │
│   ┌──────────────┐  ┌──────────────┐                                   │
│   │ 模型仓库     │  │ 配置仓库     │                                   │
│   │ (models/)    │  │ (config/)    │                                   │
│   └──────────────┘  └──────────────┘                                   │
└─────────────────────────────────────────────────────────────────────────┘
```

### 1.5 技术栈规范

**后端技术栈**：

| 组件 | 技术 | 版本 | 用途 |
|------|------|------|------|
| Web 框架 | Flask | 2.2.3 | RESTful API 服务 |
| 深度学习 | PyTorch | ≥1.13.0 | 模型推理 |
| 检测框架 | Ultralytics | ≥8.0.0 | YOLOv5/v8/v9/v10/v11/v12 引擎 |
| 图像处理 | OpenCV | 4.7.0.72 | CLAHE 增强、图像变换、滑窗裁切 |
| 图像库 | Pillow | 9.4.0 | 图像读写、绘制 |
| 数值计算 | NumPy | 1.24.2 | NMS 计算、数组操作 |
| 配置管理 | PyYAML | 6.0 | models.yaml 解析 |

**前端技术栈**：

| 组件 | 技术 | 版本 | 用途 |
|------|------|------|------|
| 框架 | Vue 3 | ^3.3.4 | Composition API |
| 构建工具 | Vite | ^4.4.9 | 开发服务器与构建 |
| HTTP 客户端 | Axios | ^1.5.0 | API 请求 |
| 图表库 | ECharts | ^5.4.3 | 统计图表可视化 |
| 图标 | FontAwesome | ^6.4.2 | UI 图标 |

**端口与网络**：

| 服务 | 端口 | 说明 |
|------|------|------|
| 前端开发服务器 | 3000 | Vite dev server |
| 后端 API 服务 | 5000 | Flask app |
| 前端代理 | /api → :5000 | Vite proxy 配置 |

### 1.6 系统边界

**本期纳入范围**：

- 按架次管理无人机原始图片数据（仅图像，不含多模态数据）
- 图片预处理：批量 CLAHE 增强、批量滑窗裁切
- 数据集构建与拆分（train/val/test）、VOC/COCO/YOLO 格式导出
- 数据集统计分析报告
- 模型注册管理、运行时热切换、单图/批量检测推理
- 检测结果可视化（像素坐标）

**本期不纳入范围**：

- 正射影像拼接（ODM）、地理配准、GIS 地图可视化、地理坐标映射
- 多模态数据（多光谱、点云等）管理
- 标注工具本体开发与标注校验/清洗/坐标回推（标注由外部工具完成）
- 模型训练、训练监控与主动学习闭环
- 检测结果的分析报告（计数/密度/空间分布）与多格式导出（GeoJSON/CSV/COCO）

---

## 二、模块一：数据管理

### 2.1 模块定位与职责边界

**模块定位**：数据管理模块是系统的数据入口，负责管理无人机采集的大田农作物图片数据，并提供初步的数据浏览能力。

**职责边界**：

- 负责：按架次登记 UAV 采集基本参数、管理本机图片存放路径、提供类 Windows 文件系统浏览与图片预览。
- 不负责：图片的任何处理操作（增强/裁切等由模块二负责）；非图像模态数据管理；正射拼接与地理配准。

**核心约定**：每一架次无人机采集的图像存放在一个独立文件夹，系统通过文件夹对不同架次数据进行管理。

### 2.2 功能需求

#### FR-D01：架次数据接入与参数登记

**需求描述**：支持登记新的 UAV 采集架次，记录本批次数据的基本参数信息与本机图片存放路径。

**输入**：架次元数据（见 2.5）、本机图片文件夹绝对路径。

**处理逻辑**：

- 校验本机路径是否存在且可读
- 扫描路径下的图片文件（支持 .jpg/.jpeg/.png/.bmp/.tif/.tiff）
- 统计图片数量、记录文件列表
- 持久化架次元数据与图片索引

**输出**：架次 ID、图片数量、图片文件列表。

**约束**：

- 单架次图片数量上限：2000 张
- 单张图片大小上限：50MB
- 路径必须为本机绝对路径

#### FR-D02：文件夹与图片浏览

**需求描述**：载入架次后，UI 上可如同浏览 Windows 本机文件系统一样查看所载入文件夹下的所有图片数据。

**功能点**：

- 以架次列表为入口，展示所有已登记架次
- 点击架次进入该架次的图片浏览视图
- 图片浏览视图支持：缩略图网格展示、文件名/大小/尺寸显示、分页或虚拟滚动
- 支持单击图片查看大图预览
- 支持按文件名排序

#### FR-D03：架次数据检索与管理

**需求描述**：对已登记的架次数据进行检索与管理。

**功能点**：

- 按采集日期、作物类型、地块名称、无人机型号等条件检索架次
- 查看架次详情（元数据 + 图片统计）
- 删除架次登记（不删除本机原始文件）

### 2.3 UI 需求

**新增数据表单**：

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| 架次名称 | string | 是 | — | 自定义名称 |
| 作物类型 | string | 是 | — | 如：甘蔗 |
| 采集日期 | date | 是 | 20250511      | YYYY-MM-DD |
| 地块名称 | string | 否 | — | 采集地块标识 |
| 无人机型号 | string | 否 | DJI Mavic 3 M | 如：DJI Mavic 3 M |
| 飞行高度（米） | float | 否 | — | 采集飞行高度 |
| 航向重叠率 | float | 否 | 80%           | 0-1 |
| 旁向重叠率 | float | 否 | 70% | 0-1 |
| 图片文件夹路径 | string | 是 | — | 本机绝对路径 |

**文件浏览视图**：

- 左侧：架次列表树（按作物类型分组）
- 右侧：选中架次的图片缩略图网格
- 顶部：面包屑导航 + 检索栏
- 缩略图网格：响应式列数，每张图显示文件名与尺寸

### 2.4 接口

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
  "image_folder_path": "/data/raw_images/sugarcane_20260805_001"
}
```

**响应格式**：

```json
{
  "success": true,
  "batch_id": "batch_20260805_001",
  "image_count": 156,
  "total_size_mb": 1245.6
}
```

**接口路由**：`GET /api/batches`

**查询参数**：`crop_type`、`flight_date`、`plot_name`、`page`、`page_size`

**接口路由**：`GET /api/batches/{batch_id}`

**响应**：架次元数据 + 图片统计信息。

**接口路由**：`GET /api/batches/{batch_id}/images`

**查询参数**：`page`、`page_size`、`sort_by`、`order`

**响应**：图片文件列表（文件名、相对路径、大小、尺寸、缩略图 URL）。

**接口路由**：`GET /api/batches/{batch_id}/images/{filename}/preview`

**响应**：图片二进制流（`image/jpeg` 或 `image/png`）。

**接口路由**：`DELETE /api/batches/{batch_id}`

**说明**：仅删除架次登记记录，不删除本机原始文件。

### 2.5 元数据结构

```python
# 架次元数据
{
    "batch_id": str,              # 架次唯一标识
    "batch_name": str,            # 架次名称
    "crop_type": str,             # 作物类型
    "flight_date": str,           # 采集日期 ISO 8601
    "plot_name": str,             # 地块名称（可选）
    "drone_model": str,           # 无人机型号（可选）
    "flight_altitude_m": float,   # 飞行高度（米，可选）
    "overlap_front": float,       # 航向重叠率（可选）
    "overlap_side": float,        # 旁向重叠率（可选）
    "image_folder_path": str,     # 本机图片文件夹绝对路径
    "image_count": int,           # 图片数量
    "total_size_bytes": int,      # 图片总大小
    "created_at": str,            # 登记时间 ISO 8601
    "image_formats": [str]        # 包含的图片格式列表
}
```

### 2.6 目录与存储规范

原始图片数据保留在用户指定的本机路径，系统不复制。系统在项目根目录下维护元数据索引：

```
project_root/
├── metadata/
│   └── batches/
│       ├── batch_20260805_001.json    # 架次元数据
│       └── batch_20260805_001/
│           └── image_index.json       # 图片索引清单
```

**image_index.json 结构**：

```json
{
  "batch_id": "batch_20260805_001",
  "folder_path": "/data/raw_images/sugarcane_20260805_001",
  "images": [
    {
      "filename": "DJI_0001.jpg",
      "relative_path": "DJI_0001.jpg",
      "size_bytes": 8345612,
      "width": 5472,
      "height": 3648,
      "format": "JPEG"
    }
  ]
}
```

---

## 三、模块二：数据处理

### 3.1 模块定位与职责边界

**模块定位**：数据处理模块负责对载入系统的单一批次或多批次无人机图片数据进行数据预处理操作，把数据处理为待标注的原始数据集。

**职责边界**：

- 负责：批量 CLAHE 增强、批量滑窗裁切、处理结果预览、处理任务管理。
- 不负责：标注相关操作；数据集拆分与导出（由模块三负责）；检测推理（由模块四负责）。

**输出约定**：处理后的图片存放在项目根目录的 `output` 文件夹下，每次处理取时间戳来区分。

### 3.2 功能需求

#### FR-P01：批量 CLAHE 增强

**需求描述**：支持对选定文件夹下的图片进行批量 CLAHE（限制对比度自适应直方图均衡化）增强操作。

**输入**：图片输入目录、图片输出目录、网格数量、阈值（clipLimit）。

**处理逻辑**：

- 遍历输入目录下所有合法图片
- 对每张图片应用 CLAHE 增强：RGB → LAB 色彩空间 → 对 L 通道应用 CLAHE → 转回 RGB
- 灰度图直接应用 CLAHE
- 增强后图片保存到输出目录，保持原文件名

**参数规范**：

| 参数 | 字段名 | 默认值 | 范围 | 说明 |
|------|--------|--------|------|------|
| 网格数量 | clip_grid_size | 8×8 | — | CLAHE 的 tileGridSize |
| 阈值 | clip_limit | 2.0 | — | CLAHE 的 clipLimit |
| 输入目录 | input_dir | 选定架次的图片路径 | — | 必须为已登记架次路径或处理结果路径 |
| 输出目录 | output_dir | `output/clahe_{timestamp}/` | — | 默认存放在项目根 output 下，时间戳区分 |

**输出**：增强后的图片目录、处理日志、处理统计（成功/失败数量）。

#### FR-P02：批量滑窗裁切

**需求描述**：支持对选定文件夹下的图片进行批量滑窗裁切操作。

**输入**：图片输入目录、裁切后图片输出目录、裁切图片大小、重叠率。

**处理逻辑**：

- 遍历输入目录下所有合法图片
- 按滑窗策略裁切：步长 = 裁切大小 × (1 - 重叠率)
- 边缘处理：最后一行/列调整起始位置以确保分块尺寸一致
- 每张子图在原图名称的基础上增加裁切的 x 与 y 坐标的偏移量与 4 位 0 填充的子图序号

**子图命名规则**：

```
{original_stem}_x{offset_x}_y{offset_y}_{seq:04d}.{ext}
```

示例：原图 `DJI_0001.jpg`，裁切大小 640，重叠率 0.1，则子图命名为：

```
DJI_0001_x0_y0_0001.jpg
DJI_0001_x576_y0_0002.jpg
DJI_0001_x0_y576_0003.jpg
...
```

其中 `offset_x`、`offset_y` 为子图左上角在原图中的像素坐标。

**参数规范**：

| 参数 | 字段名 | 默认值 | 范围 | 说明 |
|------|--------|--------|------|------|
| 裁切大小 | tile_size | 640 | 320-1280 | 裁切图片的宽高（像素，正方形） |
| 重叠率 | overlap_ratio | 0.05 | 0-0.3 | 相邻子图的重叠比例 |
| 输入目录 | input_dir | 选定架次的图片路径 | — | 可选自 CLAHE 增强结果目录 |
| 输出目录 | output_dir | `output/crop_{timestamp}/` | — | 默认存放在项目根 output 下，时间戳区分 |

**输出**：裁切后的子图目录、子图索引清单（含原图名、偏移量、子图序号映射）、处理日志、处理统计。

#### FR-P03：处理结果预览

**需求描述**：支持预览处理操作后的图像，预览形式同模块一的图片浏览视图。

**功能点**：

- 选择某次处理任务后，以缩略图网格展示处理结果
- 支持单击查看大图
- 支持原图与处理结果对比预览（左右分栏）

#### FR-P04：多批次选择与任务管理

**需求描述**：支持对载入系统的单一批次或多批次图片数据进行处理。

**功能点**：

- 处理任务可选择输入源：单个架次、多个架次（合并处理）、或已有的处理结果目录
- 处理任务异步执行，提供进度与状态查询
- 任务列表展示历史处理任务及其参数、状态、输出路径

### 3.3 UI 需求

**处理任务创建表单**：

- 处理类型选择：CLAHE 增强 / 滑窗裁切
- 输入源选择：架次多选下拉 / 自定义目录路径
- 参数配置区：根据处理类型动态展示对应参数表单（带默认值）
- 输出目录：默认展示，支持自定义修改

**任务列表面板**：

- 展示所有处理任务：任务类型、状态（进行中/已完成/失败）、创建时间、输入源、输出路径
- 进行中任务显示进度条
- 已完成任务可点击进入结果预览

**结果预览视图**：

- 缩略图网格（同模块一）
- 原图 vs 处理结果对比模式

### 3.4 接口

**接口路由**：`POST /api/processing/clahe`

**请求格式**：`application/json`

```json
{
  "input_dir": "/data/raw_images/sugarcane_20260805_001",
  "output_dir": null,
  "clip_grid_size": [8, 8],
  "clip_limit": 2.0
}
```

**响应格式**：

```json
{
  "success": true,
  "task_id": "clahe_20260805_103000",
  "output_dir": "output/clahe_20260805_103000",
  "status": "processing"
}
```

**接口路由**：`POST /api/processing/crop`

**请求格式**：`application/json`

```json
{
  "input_dir": "/data/raw_images/sugarcane_20260805_001",
  "output_dir": null,
  "tile_size": 640,
  "overlap_ratio": 0.1
}
```

**响应格式**：

```json
{
  "success": true,
  "task_id": "crop_20260805_103500",
  "output_dir": "output/crop_20260805_103500",
  "status": "processing"
}
```

**接口路由**：`GET /api/processing/tasks`

**查询参数**：`status`、`task_type`、`page`、`page_size`

**响应**：处理任务列表。

**接口路由**：`GET /api/processing/tasks/{task_id}`

**响应**：任务详情（参数、状态、进度、输出路径、统计）。

**接口路由**：`GET /api/processing/tasks/{task_id}/preview`

**查询参数**：`page`、`page_size`

**响应**：处理结果图片列表（含缩略图 URL）。

### 3.5 算法参数规范

**CLAHE 增强参数**：

| 参数 | 默认值 | 范围 | 说明 |
|------|--------|------|------|
| clipLimit | 2.0 | — | 对比度限制阈值 |
| tileGridSize | (8, 8) | — | CLAHE 分块网格大小 |
| 色彩空间转换 | RGB→LAB→L通道增强→RGB | — | 彩色图处理流程 |

**滑窗裁切参数**：

| 参数 | 默认值 | 范围 | 说明 |
|------|--------|------|------|
| tile_size | 640 | 320-1280 | 裁切图片宽高（像素） |
| overlap_ratio | 0.05 | 0-0.3 | 相邻子图重叠比例 |
| 步长计算 | tile_size × (1 - overlap_ratio) | — | 滑窗步长 |
| 边缘处理 | 调整起始位置确保尺寸一致 | — | 最后一行/列回退起始点 |

### 3.6 输出规范

**输出目录结构**：

```
project_root/
└── output/
    ├── clahe_20260805_103000/
    │   ├── DJI_0001.jpg
    │   ├── DJI_0002.jpg
    │   └── ...
    ├── crop_20260805_103500/
    │   ├── DJI_0001_x0_y0_0001.jpg
    │   ├── DJI_0001_x576_y0_0002.jpg
    │   └── ...
    └── crop_20260805_103500_index.json
```

**裁切索引文件**（`crop_{timestamp}_index.json`）：

```json
{
  "task_id": "crop_20260805_103500",
  "tile_size": 640,
  "overlap_ratio": 0.1,
  "created_at": "2026-08-05T10:35:00Z",
  "tiles": [
    {
      "filename": "DJI_0001_x0_y0_0001.jpg",
      "original_filename": "DJI_0001.jpg",
      "offset_x": 0,
      "offset_y": 0,
      "seq": 1,
      "tile_size": 640
    }
  ]
}
```

---

## 四、模块三：数据集管理

### 4.1 模块定位与职责边界

**模块定位**：数据集管理模块负责消费外部标注工具产出的标注数据，完成训练数据集的拆分构建、多格式导出与统计分析报告。

**职责边界**：

- 负责：数据集拆分（train/val/test）、标准目录生成、VOC/COCO/YOLO 格式导出、数据集统计分析报告。
- 不负责：标注的创建（由外部标注工具完成）；标注校验、空标注清洗、非法框检查、子图→原图坐标回推（标注处理不在本期范围）。
- **标注来源约定**：标注由外部标注工具（如 LabelImg）完成，模块三仅消费已有标注数据，假定标注数据合法有效。

### 4.2 功能需求

#### FR-S01：数据集构建与拆分

**需求描述**：从图片目录与标注目录构建标准训练数据集，按策略拆分为 train/val/test 三个子集。

**输入**：图片目录路径、标注目录路径、拆分策略配置、输出目录。

**处理逻辑**：

- 扫描图片目录与标注目录，建立同名映射关系（图片文件名 ↔ 标注文件名）
- 按选定拆分策略将样本分配到 train/val/test
- 生成标准目录结构
- 生成拆分清单（list.csv 或 split_manifest）

**拆分策略**：

| 策略 | 说明 |
|------|------|
| 按原图粒度拆分  | 默认策略，同一原图衍生的子图不跨集合（防止数据泄露） |
| 按批次/地块拆分 | 按采集批次或地块划分集合                             |

**默认拆分比例**：train:val:test = 6:1:1

**输出**：标准数据集目录、拆分清单、拆分统计报告。

#### FR-S02：多格式导出

**需求描述**：将构建的数据集导出为 VOC、COCO、YOLO 三种主流标注格式。

**处理逻辑**：

- 统一从内部标准样本模型导出
- 支持类别映射表配置
- 每种格式生成对应的标注文件与配置文件

**支持格式**：

| 格式 | 标注文件 | 配置文件 | 说明 |
|------|----------|----------|------|
| Pascal VOC | 每张图一个 `.xml` | `voc_classes.txt` | XML 格式，bbox 为绝对像素坐标 [x_min, y_min, x_max, y_max] |
| COCO Detection | 每个集合一个 `.json` | — | JSON 格式，bbox 为 [x, y, width, height] 绝对像素坐标 |
| YOLO Detection | 每张图一个 `.txt` | `data.yaml` | 归一化坐标 `class_id center_x center_y width height`，值范围 [0,1] |

**坐标转换公式**：

- 像素→YOLO：`cx = (x1 + x2) / (2W)`，`cy = (y1 + y2) / (2H)`，`w = (x2 - x1) / W`，`h = (y2 - y1) / H`
- 像素→COCO：`bbox = [x1, y1, x2 - x1, y2 - y1]`

#### FR-S03：数据集统计分析报告

**需求描述**：对构建的数据集进行多维度统计分析，生成自动化分析报告。

**统计指标**：

| 维度 | 指标 | 说明 |
|------|------|------|
| 数据规模 | 原图数量、子图数量、非空样本数量 | 按集合/批次/地块汇总 |
| 类别分布 | 类别样本数、类别占比、类别均衡性 | 含失衡告警 |
| 目标框尺度 | bbox 平均宽高、bbox 面积分布、COCO small/medium/large 分布 | 按集合对比 |
| 像素质量 | 图像分辨率分布、宽高比分布、像素均值/方差 | 异常样本标注 |

**报告格式**：Markdown / HTML，含统计表格与图表（柱状图、直方图、饼图）。

### 4.3 UI 需求

**数据集创建表单**：

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| 数据集名称 | string | 是 | — | 唯一标识 |
| 图片目录 | string | 是 | — | 图片所在目录路径 |
| 标注目录 | string | 是 | — | 标注所在目录路径 |
| 标注格式 | enum | 是 | VOC | 输入标注的当前格式：VOC/COCO/YOLO |
| 拆分策略 | enum | 是 | 随机 | 随机/按原图/按批次 |
| 拆分比例 | object | 是 | 6:1:1    | train:val:test |
| 输出格式 | multiselect | 是 | VOC+COCO | 导出格式：VOC/COCO/YOLO |
| 类别映射 | object | 否 | — | 类别名称到 ID 的映射 |

**数据集列表面板**：

- 展示所有已构建数据集：名称、样本数、标注数、创建时间
- 点击进入数据集详情

**数据集详情视图**：

- 概览卡片：图片数、标注数、类别数、集合分布
- 统计分析报告展示（嵌入图表）
- 导出操作按钮

### 4.4 接口

**接口路由**：`POST /api/datasets`

**请求格式**：`application/json`

```json
{
  "dataset_name": "sugarcane_v1",
  "image_dir": "output/crop_20260805_103500",
  "annotation_dir": "/data/annotations/sugarcane_v1",
  "input_format": "voc",
  "split_strategy": "random",
  "split_ratio": {"train": 0.7, "val": 0.2, "test": 0.1},
  "export_formats": ["voc", "coco", "yolo"],
  "class_mapping": {"Sugarcane Seedling": 0}
}
```

**响应格式**：

```json
{
  "success": true,
  "dataset_id": "ds_sugarcane_v1_20260805",
  "dataset_path": "datasets/sugarcane_v1/",
  "statistics": {
    "total_images": 156,
    "total_annotations": 1247,
    "train_images": 109,
    "val_images": 32,
    "test_images": 15
  }
}
```

**接口路由**：`GET /api/datasets`

**响应**：数据集列表。

**接口路由**：`GET /api/datasets/{dataset_id}`

**响应**：数据集详情 + 统计摘要。

**接口路由**：`GET /api/datasets/{dataset_id}/report`

**查询参数**：`format`（markdown/html）

**响应**：统计分析报告内容。

**接口路由**：`GET /api/datasets/{dataset_id}/export`

**查询参数**：`format`（voc/coco/yolo）

**响应**：导出文件下载或导出目录路径。

### 4.5 拆分策略与目录规范

**标准数据集目录结构**：

```
project_root/
└── datasets/
    └── {dataset_name}/
        ├── images/
        │   ├── train/
        │   │   ├── DJI_0001_x0_y0_0001.jpg
        │   │   └── ...
        │   ├── val/
        │   └── test/
        ├── labels/                    # YOLO 格式标注
        │   ├── train/
        │   │   ├── DJI_0001_x0_y0_0001.txt
        │   │   └── ...
        │   ├── val/
        │   └── test/
        ├── annotations/               # VOC XML 格式标注
        │   ├── train/
        │   ├── val/
        │   └── test/
        ├── train.json                 # COCO 格式标注
        ├── val.json
        ├── test.json
        ├── data.yaml                  # YOLO 配置文件
        ├── voc_classes.txt            # VOC 类别文件
        ├── list.csv                   # 拆分清单
        └── dataset_meta.json          # 数据集元信息
```

**list.csv 结构**：

```csv
Set,Filename,ImageCount,AnnotationCount
train,DJI_0001_x0_y0_0001.jpg,1,5
train,DJI_0001_x576_y0_0002.jpg,1,3
val,DJI_0002_x0_y0_0001.jpg,1,4
test,DJI_0003_x0_y0_0001.jpg,1,2
```

**data.yaml 配置文件规范**：

```yaml
path: datasets/sugarcane_v1
train: images/train
val: images/val
test: images/test

names:
  0: Sugarcane Seedling
```

**dataset_meta.json 结构**：

```json
{
  "dataset_id": "ds_sugarcane_v1_20260805",
  "dataset_name": "sugarcane_v1",
  "created_at": "2026-08-05T11:00:00Z",
  "split_strategy": "random",
  "split_ratio": {"train": 0.7, "val": 0.2, "test": 0.1},
  "export_formats": ["voc", "coco", "yolo"],
  "class_mapping": {"Sugarcane Seedling": 0},
  "source_image_dir": "output/crop_20260805_103500",
  "source_annotation_dir": "/data/annotations/sugarcane_v1"
}
```

### 4.6 统计指标与报告规范

**报告内容结构**：

1. **数据集概览**：数据集名称、创建时间、样本总数、标注总数、类别数、拆分策略与比例
2. **数据规模统计**：按集合（train/val/test）汇总图片数、标注数、非空样本数；表格 + 饼图
3. **类别分布分析**：各类别样本数、占比、均衡性评价；柱状图 + 失衡告警
4. **目标框尺度分析**：bbox 平均宽高、面积分布、COCO small/medium/large 分布；直方图
5. **像素与图像质量统计**：分辨率分布、宽高比分布、像素均值/方差；统计表 + 异常样本列表
6. **结论与建议**：数据质量评价、潜在风险提示

**报告输出格式**：

- Markdown：纯文本报告，含表格
- HTML：含 ECharts 图表的富文本报告

---

## 五、模块四：算法广场

### 5.1 模块定位与职责边界

**模块定位**：算法广场模块是系统的算法工程核心，负责模型注册管理、运行时热切换与检测推理，输出基于像素坐标的检测结果。

**职责边界**：

- 负责：模型注册中心管理、多引擎支持、运行时热切换、动态注册、单图/批量检测推理、CLAHE 分块、坐标映射、全局 NMS、结果可视化。
- 不负责：检测结果的分析报告（计数/密度/空间分布）；多格式导出（GeoJSON/CSV/COCO）；模型训练与迭代闭环。

### 5.2 功能需求

#### FR-A01：模型注册与管理

**需求描述**：通过 YAML 配置文件声明式管理所有检测模型，支持多引擎配置。

**配置文件**：`config/models.yaml`

**模型配置字段**：

| 字段 | 类型 | 说明 |
|------|------|------|
| `name` | string | 模型唯一标识 |
| `engine` | string | 引擎类型：`ultralytics` / `custom` |
| `weight` | string | 权重文件路径 |
| `display_name` | string | 显示名称 |
| `category` | string | 模型类别（如作物类型） |
| `imgsz` | int | 输入尺寸，默认 640 |
| `conf` | float | 置信度阈值 |
| `iou` | float | IoU 阈值 |
| `device` | string | 设备：`auto` / `cpu` / `cuda:0` |
| `classes` | string[] | 类别名称列表 |
| `max_det` | int | 最大检测数，默认 300 |
| `half` | bool | 是否启用 FP16，默认 false |

#### FR-A02：运行时热切换与动态注册

**需求描述**：支持在系统运行时切换当前激活的检测模型，无需重启服务；支持动态注册新模型到内存。

**处理逻辑**：

- 模型注册中心维护所有已注册模型的元数据
- 切换模型时，加载目标模型到推理引擎（采用 LRU 缓存，最多缓存 3 个引擎实例）
- 动态注册：运行时将新模型配置加入内存注册表（不持久化到 YAML）

#### FR-A03：单图与批量检测推理

**需求描述**：对单张图片或批量图片执行 YOLO 目标检测推理。

**输入**：单张图片文件或图片目录路径、模型名称（可选，默认当前激活模型）、推理参数。

**处理逻辑**（批量检测）：

1. 对每张图片应用 CLAHE 分块（tile_size + overlap）
2. 对每个分块执行 YOLO 检测
3. 将分块检测坐标映射回原图坐标系
4. 执行全局 NMS 消除重叠区域的重复检测
5. 汇总输出原图级检测结果

**推理参数**：

| 参数 | 默认值 | 范围 | 说明 |
|------|--------|------|------|
| imgsz | 640 | — | YOLO 输入尺寸 |
| conf | 0.5 | 0.1-0.9 | 置信度阈值 |
| iou | 0.7 | 0.1-0.9 | 推理 IoU 阈值 |
| max_det | 300 | — | 单图最大检测数 |
| device | auto | auto/cpu/cuda:0 | 推理设备 |
| tile_size | 640 | 320-1280 | CLAHE 分块大小 |
| overlap_ratio | 0.05 | 0-0.3 | 分块重叠比例 |
| nms_iou | 0.5 | 0.1-0.9 | 全局 NMS 的 IoU 阈值 |

#### FR-A04：CLAHE 分块与坐标映射与全局 NMS

**需求描述**：将高分辨率图像分块检测后，映射坐标回原图并消除重叠检测。

**CLAHE 分块**：

- 参数：clipLimit=2.0, tileGridSize=(8,8)
- 色彩空间：RGB → LAB → 增强 L 通道 → RGB
- 分块大小：默认 640，范围 320-1280
- 重叠比例：默认 0.05，范围 0-0.3
- 边界处理：最后一行/列调整起始位置

**坐标映射**：

```
原图坐标 = 分块坐标 + 分块偏移量
```

**全局 NMS**：

- 算法：基于 IoU 的贪心抑制
- IoU 阈值：默认 0.5，范围 0.1-0.9

#### FR-A05：检测结果可视化

**需求描述**：在原图上绘制检测框与置信度文本，生成结果图像。

**绘制规范**：

- 检测框：红色矩形框，线宽 2px
- 置信度文本：格式 `{confidence:.2f}`，显示在检测框上方
- 输出格式：JPEG，Base64 编码（用于 API 响应）或文件（用于批量结果）

### 5.3 UI 需求

**模型广场列表**：

- 展示所有已注册模型：名称、显示名、引擎类型、类别、当前状态（激活/未激活）
- 支持切换激活模型
- 支持动态注册新模型（表单填写模型配置）

**检测工作台**：

- 图片上传/目录选择
- 模型选择（默认当前激活模型）
- 推理参数调节面板
- 检测执行按钮
- 结果展示区：原图 + 检测框绘制图
- 检测结果列表：bbox 坐标、置信度、类别

### 5.4 接口

**接口路由**：`GET /api/models`

**响应格式**：

```json
{
  "success": true,
  "models": [
    {
      "name": "yolov8s-sugarcane",
      "display_name": "YOLOv8s 甘蔗幼苗",
      "engine": "ultralytics",
      "category": "sugarcane_seedling",
      "imgsz": 640,
      "conf": 0.4,
      "iou": 0.3,
      "device": "auto",
      "classes": ["Sugarcane Seedling"],
      "is_active": true
    }
  ],
  "current_model": "yolov8s-sugarcane"
}
```

**接口路由**：`POST /api/models/switch`

**请求格式**：

```json
{"model_name": "yolov8n-sugarcane"}
```

**接口路由**：`POST /api/models/load`

**请求格式**：模型配置 JSON（同 models.yaml 中单个模型配置）

**接口路由**：`POST /api/detect`

**请求格式**：`multipart/form-data`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `image` | File | 是* | — | 单张待检测图像 |
| `image_dir` | string | 是* | — | 图片目录路径（批量检测） |
| `model_name` | string | 否 | 当前激活模型 | 指定检测模型 |
| `tile_size` | int | 否 | 640 | CLAHE 分块大小 |
| `overlap_ratio` | float | 否 | 0.05 | 分块重叠比例 |
| `nms_iou` | float | 否 | 0.5 | 全局 NMS IoU 阈值 |
| `conf` | float | 否 | 模型配置 | 置信度阈值 |
| `iou` | float | 否 | 模型配置 | 推理 IoU 阈值 |

**响应格式**：

```json
{
  "success": true,
  "detection_count": 247,
  "result_image": "<base64_encoded_jpeg>",
  "detection_data": [
    {
      "id": 1,
      "x": 156.0,
      "y": 234.0,
      "width": 64.0,
      "height": 64.0,
      "confidence": 0.92,
      "class_name": "Sugarcane Seedling"
    }
  ],
  "model_info": {
    "name": "yolov8s-sugarcane",
    "display_name": "YOLOv8s 甘蔗幼苗",
    "imgsz": 640
  }
}
```

**接口路由**：`GET /api/health`

**响应格式**：

```json
{
  "status": "ok",
  "version": "1.0.0",
  "detector_ready": true,
  "registry_ready": true,
  "current_model": "yolov8s-sugarcane"
}
```

### 5.5 模型配置规范

**models.yaml 完整配置示例**：

```yaml
default_model: yolov8s-sugarcane

engines:
  - name: ultralytics
    description: "Ultralytics 引擎，支持 YOLOv5/v8/v9/v10/v11/v12 全系列"
  - name: custom
    description: "自定义 YOLOv5 引擎，作为 fallback 保留"

models:
  - name: yolov8n-sugarcane
    engine: ultralytics
    weight: models/yolov8n_sugarcane.pt
    display_name: "YOLOv8n 甘蔗幼苗"
    category: sugarcane_seedling
    imgsz: 640
    conf: 0.5
    iou: 0.3
    device: auto
    classes:
      - Sugarcane Seedling

  - name: yolov8s-sugarcane
    engine: ultralytics
    weight: models/yolov8s_sugarcane.pt
    display_name: "YOLOv8s 甘蔗幼苗"
    category: sugarcane_seedling
    imgsz: 640
    conf: 0.4
    iou: 0.3
    device: auto
    classes:
      - Sugarcane Seedling
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

**API 响应格式**：`detection_data` 数组将 `bbox` 展开为 `x, y, width, height` 字段（左上角坐标 + 宽高），便于前端处理。

---

## 六、跨模块公共规格

### 6.1 端到端数据流

系统的数据流从 UAV 数据采集开始，经过四个阶段流转至检测结果输出：

```
[阶段1: 数据管理]     [阶段2: 数据处理]      [阶段3: 数据集管理]    [阶段4: 算法广场]
     │                    │                    │                    │
     ▼                    ▼                    ▼                    ▼
原始图片        →→→  CLAHE增强/滑窗裁切  →→→  训练数据集       →→→  检测结果
(按架次管理)         (output/时间戳)         (train/val/test)     (bbox+conf+class)
                       ↓                                         ↑
                  待标注原始数据集 ──→ 外部标注工具 ──→ 标注数据 ──┘
```

**阶段间衔接**：

- 阶段1→阶段2：模块一登记的架次图片路径作为模块二的输入源
- 阶段2→阶段3：模块二产出的处理结果目录（output/时间戳）作为模块三的图片输入；标注由外部工具完成
- 阶段3→阶段4：模块三导出的标准数据集可供后续训练使用（训练不在本期范围）；模块四直接对图片执行检测推理

### 6.2 共享数据模型

**图片记录（ImageRecord）**：

```python
{
    "filename": str,           # 文件名
    "relative_path": str,      # 相对路径
    "absolute_path": str,      # 绝对路径
    "size_bytes": int,         # 文件大小
    "width": int,              # 图片宽度（像素）
    "height": int,             # 图片高度（像素）
    "format": str              # 图片格式（JPEG/PNG/BMP/TIFF）
}
```

**处理任务记录（ProcessingTask）**：

```python
{
    "task_id": str,            # 任务唯一标识
    "task_type": str,          # 任务类型：clahe / crop
    "input_dir": str,          # 输入目录
    "output_dir": str,         # 输出目录
    "params": dict,            # 任务参数
    "status": str,             # 状态：pending/processing/completed/failed
    "progress": float,         # 进度（0-1）
    "created_at": str,         # 创建时间
    "completed_at": str,       # 完成时间
    "total_count": int,        # 处理总数
    "success_count": int,      # 成功数
    "failed_count": int        # 失败数
}
```

**数据集清单（DatasetManifest）**：

```python
{
    "dataset_id": str,         # 数据集唯一标识
    "dataset_name": str,       # 数据集名称
    "created_at": str,         # 创建时间
    "split_strategy": str,     # 拆分策略
    "split_ratio": dict,       # 拆分比例
    "export_formats": [str],   # 导出格式列表
    "class_mapping": dict,     # 类别映射
    "statistics": {            # 统计信息
        "total_images": int,
        "total_annotations": int,
        "train_images": int,
        "val_images": int,
        "test_images": int
    }
}
```

### 6.3 统一目录结构规范

```
project_root/
├── metadata/                         # 元数据（模块一）
│   └── batches/
│       ├── {batch_id}.json
│       └── {batch_id}/
│           └── image_index.json
├── output/                           # 处理输出（模块二）
│   ├── clahe_{timestamp}/
│   └── crop_{timestamp}/
├── datasets/                         # 数据集（模块三）
│   └── {dataset_name}/
│       ├── images/
│       ├── labels/
│       ├── annotations/
│       ├── train.json
│       ├── val.json
│       ├── test.json
│       ├── data.yaml
│       └── list.csv
├── models/                           # 模型权重（模块四）
│   ├── yolov8n_sugarcane.pt
│   └── yolov8s_sugarcane.pt
├── config/                           # 配置文件
│   └── models.yaml
├── results/                          # 检测结果（模块四）
│   └── {result_id}/
│       ├── result_image.jpg
│       └── detection_data.json
└── app.py                            # Flask 应用入口
```

### 6.4 API 设计约定

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
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "图片路径不存在"
  }
}
```

**错误码规范**：

| 错误码 | 说明 |
|--------|------|
| `VALIDATION_ERROR` | 参数校验失败 |
| `NOT_FOUND` | 资源不存在 |
| `FILE_NOT_FOUND` | 文件/路径不存在 |
| `PROCESSING_ERROR` | 处理过程出错 |
| `MODEL_ERROR` | 模型加载/推理出错 |
| `INTERNAL_ERROR` | 内部错误 |

**路径规范**：所有接受路径参数的接口，路径必须为绝对路径或相对于项目根目录的路径。

### 6.5 配置驱动与可追溯

- 所有处理任务的参数必须持久化到任务记录中
- 每次处理输出包含配置快照（JSON 文件）
- 数据集导出包含元信息文件（dataset_meta.json）
- 检测结果包含模型信息与推理参数

---

## 七、系统边界与技术参数

### 7.1 输入/输出边界

**系统输入**：

| 输入类型 | 格式 | 约束 |
|----------|------|------|
| UAV 原始图片 | JPEG/JPG/PNG/BMP/TIF/TIFF | 单张 ≤50MB |
| 处理输入图片 | 同上 | 单次处理 ≤2000 张 |
| 标注数据 | VOC XML / COCO JSON / YOLO TXT | 由外部标注工具产出 |
| 模型权重 | .pt (PyTorch) | Ultralytics 格式 |
| 配置文件 | YAML | models.yaml 格式 |

**系统输出**：

| 输出类型 | 格式 | 说明 |
|----------|------|------|
| 处理后图片 | JPEG/PNG | CLAHE 增强或滑窗裁切结果 |
| 标准数据集 | 文件系统 | VOC/COCO/YOLO 目录结构 |
| 统计报告 | Markdown/HTML | 含图表 |
| 检测结果图 | JPEG (Base64) | 红色框标注，宽度 2px |
| 检测数据 | JSON | 标准检测数据结构 |

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

**检测推理参数**：

| 参数 | 默认值 | 范围 | 说明 |
|------|--------|------|------|
| imgsz | 640 | — | YOLO 输入尺寸 |
| conf | 0.5 | 0.1-0.9 | 置信度阈值 |
| iou | 0.7 | 0.1-0.9 | 推理 IoU 阈值 |
| max_det | 300 | — | 单图最大检测数 |
| device | auto | auto/cpu/cuda:0 | 推理设备 |
| LRU 缓存上限 | 3 | — | 引擎实例缓存数 |

**分块检测参数**：

| 参数 | 默认值 | 范围 | 说明 |
|------|--------|------|------|
| tile_size | 640 | 320-1280 | CLAHE 分块大小 |
| overlap_ratio | 0.05 | 0-0.3 | 分块重叠比例 |
| nms_iou | 0.5 | 0.1-0.9 | 全局 NMS IoU 阈值 |

### 7.3 性能边界

| 指标 | 目标值 | 说明 |
|------|--------|------|
| 单张 640×640 分块检测延迟 | ≤500ms | GPU 推理（RTX 3060+） |
| 单张 640×640 分块检测延迟 | ≤3s | CPU 推理 |
| 10000×10000 图像分块检测 | ≤60s | GPU，约 25 个分块 |
| CLAHE 增强（100 张图） | ≤30s | — |
| 滑窗裁切（100 张图） | ≤20s | — |
| API 响应超时 | 120s | 单次检测请求 |
| 并发检测请求 | 1 | 当前为单线程同步处理 |

### 7.4 系统依赖

| 依赖 | 类型 | 说明 |
|------|------|------|
| Ultralytics | Python 包 | YOLO 推理引擎，pip 安装 |
| PyTorch | Python 包 | 深度学习框架，需根据 GPU 环境安装对应 CUDA 版本 |
| OpenCV | Python 包 | 图像处理、CLAHE、裁切 |
| Pillow | Python 包 | 图像读写 |
| NumPy | Python 包 | 数值计算 |
| PyYAML | Python 包 | YAML 配置解析 |

---

## 八、验收与复现检查清单

编程智能体完成系统复现后，应按以下检查清单验证：

### 8.1 模块一验收

1. **架次登记验证**：`POST /api/batches` 登记新架次，填写 UAV 参数与本机路径，返回 batch_id 与图片数量
2. **架次列表验证**：`GET /api/batches` 返回所有已登记架次列表
3. **图片浏览验证**：`GET /api/batches/{batch_id}/images` 返回图片列表，`GET /api/batches/{batch_id}/images/{filename}/preview` 返回图片预览
4. **前端验证**：访问数据管理面板，可看到架次列表与类 Windows 文件浏览视图

### 8.2 模块二验收

5. **CLAHE 增强验证**：`POST /api/processing/clahe` 提交增强任务，默认参数网格 8×8、阈值 2.0，输出到 `output/clahe_{timestamp}/`
6. **滑窗裁切验证**：`POST /api/processing/crop` 提交裁切任务，子图命名包含原图名 + x/y 偏移 + 4 位序号
7. **处理预览验证**：`GET /api/processing/tasks/{task_id}/preview` 返回处理结果图片列表
8. **多批次验证**：处理任务支持选择多个架次作为输入源

### 8.3 模块三验收

9. **数据集构建验证**：`POST /api/datasets` 构建数据集，生成 train/val/test 标准目录结构与 list.csv
10. **格式导出验证**：`GET /api/datasets/{dataset_id}/export?format=voc` 导出 VOC 格式；同理导出 COCO 与 YOLO 格式
11. **统计报告验证**：`GET /api/datasets/{dataset_id}/report` 返回包含数据规模、类别分布、bbox 尺度、像素质量的统计报告

### 8.4 模块四验收

12. **模型管理验证**：`GET /api/models` 返回模型列表，`POST /api/models/switch` 可热切换模型
13. **单图检测验证**：`POST /api/detect` 上传单张图片，返回包含 detection_count、result_image、detection_data 的 JSON
14. **批量检测验证**：`POST /api/detect` 传入 image_dir，返回批量检测结果
15. **健康检查验证**：`GET /api/health` 返回 `{"status":"ok", "version":"1.0.0", "detector_ready":true, "registry_ready":true, "current_model":"yolov8s-sugarcane"}`

### 8.5 端到端验收

16. **前端验证**：`npm run dev` 启动前端，访问 `http://localhost:3000`，可看到数据管理、数据处理、数据集管理、算法广场四个功能页面
17. **端到端流程验证**：登记架次 → CLAHE 增强 → 滑窗裁切 → 外部标注 → 构建数据集 → 导出格式 → 检测推理，全流程可跑通

---

## 九、附录

### 9.1 现有能力迁移映射

| 历史 PRD 能力 | 来源 | 归入新 PRD 模块 |
|---------------|------|-----------------|
| UAV 影像上传与项目管理 | PRD1 FR-D01 | 模块一（调整为按架次管理本机路径） |
| EXIF 元数据提取 | PRD1 FR-D03 | 模块一（简化为手动登记参数） |
| 正射影像拼接 | PRD1 FR-D02 | 不纳入 |
| 正射影像分块提取 | PRD1 FR-D04 | 模块二（调整为通用滑窗裁切） |
| 数据存储仓库 | PRD1 FR-D05 | 跨模块公共规格（6.3 目录结构） |
| 图像分块与 CLAHE 增强 | PRD1 FR-A01 | 模块二（CLAHE）+ 模块四（分块检测） |
| YOLO 目标检测 | PRD1 FR-A02 | 模块四 |
| 坐标映射与全局 NMS | PRD1 FR-A03 | 模块四 |
| 模型注册与管理 | PRD1 FR-A04 | 模块四 |
| 数据集构建 | PRD1 FR-A05 | 模块三 |
| 数据闭环与主动学习 | PRD1 FR-A06 | 不纳入 |
| 计数与密度估计 | PRD1 FR-C01 | 不纳入 |
| 空间分布分析 | PRD1 FR-C02 | 不纳入 |
| 多格式数据导出 | PRD1 FR-C03 | 不纳入（仅数据集导出在模块三） |
| 统计报告生成 | PRD1 FR-C04 | 不纳入（检测分析报告） |
| GIS 地图可视化 | PRD1 FR-U05 | 不纳入 |
| 多格式 UAV 影像接入 | PRD2 5.1.1 | 模块一 |
| 可配置图像清洗 | PRD2 5.1.2 | 不纳入（本期简化） |
| 可配置增强与归一化 | PRD2 5.1.3 | 模块二（CLAHE） |
| 图像切块与命名标准化 | PRD2 5.1.4 | 模块二（滑窗裁切） |
| 标注数据接入与校验 | PRD2 5.2.1 | 不纳入（外部标注） |
| 空标注与异常标注清洗 | PRD2 5.2.2 | 不纳入 |
| 原图级与子图级标注映射 | PRD2 5.2.3 | 不纳入 |
| 自定义数据集拆分策略 | PRD2 5.2.4 | 模块三 |
| 主流格式导出 | PRD2 5.2.5 | 模块三 |
| 数据规模统计 | PRD2 5.3.1 | 模块三 |
| 类别与样本分布分析 | PRD2 5.3.2 | 模块三 |
| 目标框尺度分析 | PRD2 5.3.3 | 模块三 |
| 像素与图像质量统计 | PRD2 5.3.4 | 模块三 |
| 自动化可视化分析报告 | PRD2 5.3.5 | 模块三 |

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

### 9.3 关键参考文献

1. Ultralytics YOLO Documentation — 检测引擎 API 参考
2. COCO Common Objects in Context — 标注格式规范
3. Pascal VOC Devkit Documentation — VOC 标注格式规范
4. MatchPlant: An Open-Source Pipeline for UAV-Based Single-Plant Detection and Data Extraction (arXiv:2506.12295, 2025) — 模块化 UAV 植物检测流水线设计参考
5. Valente et al., Automated crop plant counting from very high-resolution aerial imagery, Precision Agriculture (2020) — UAV 农作物检测方法参考
