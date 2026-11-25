# 产品需求文档（PRD）：基于无人机图像的大田农作物智能监测与管理系统

**文档版本**：v7
**编制日期**：2026-09-20
**更新说明**：

- v1–v5：系统基线建立与四模块架构定义（详见历史版本）。
- v6（2026-08-13）：模块二（数据处理）由 Mock 更新为完整实现；前端路由更新为 17 条；模块三（数据集管理）完整设计方案。
- **v7（2026-09-20）**：① 新增**模块五：智能助手（Agent）**——以插件/工具驱动的对话式交互入口，将系统四大模块的 GUI 操作沉淀为 Agent 可调用的工具目录，支持自然语言驱动数据管理、数据处理、数据集管理、算法注册与推理，以及跨模块复合工作流（如一键生成农作物监测效果报告）；② 更新系统架构图，新增 Agent 层（LLM 推理引擎 + 意图编排器 + 工具执行器）；③ 更新前端路由表（新增 `/agent` 页面）与全局导航（侧边栏新增"智能助手"菜单）；④ 更新实现状态总览表。

**文档目标**：在 v6 基础上，定义系统第五模块"智能助手"的完整产品需求，涵盖可行性分析、架构设计、工具目录、意图编排、迭代路线与前端交互规范，指导编程智能体完成 Agent 模块的设计与实现。

**取代说明**：本 PRD 完全取代 v6 及之前版本。v6 中已实现的模块一至模块四需求基线不变，新增内容以本 PRD 为准。

---

## 零、v7 变更摘要

| 变更项 | 说明 |
|--------|------|
| 新增模块五 | 智能助手（Agent），详见第五章 |
| 架构图更新 | 1.4 节架构图新增 Agent 层 |
| 技术栈更新 | 1.5 节新增 LLM SDK、LangChain/LangGraph 等依赖 |
| 前端路由更新 | 1.8 节路由表新增 `/agent` 路由 |
| 全局导航更新 | 1.8 节侧边栏新增"智能助手"一级菜单 |
| 实现状态更新 | 1.7 节新增模块五行 |

---

## 一、系统概述

### 1.1 系统定位

本系统是一个**基于无人机图像的大田农作物智能监测与管理的本地 Web 应用**，定位为通用大田农作物底座平台，以"甘蔗幼苗检测与计数"作为首个典型应用案例。

**核心定位原则**：

- **通用底座 + 典型案例**：系统架构、数据模型、模块接口不与特定作物绑定，作物类别、类别映射、目录层级等均配置化；甘蔗幼苗作为首个落地场景验证全链路。
- **纯像素流程**：本系统不纳入正射影像拼接（ODM）、地理配准、GIS 地图可视化与地理坐标映射。数据流全程基于像素坐标。
- **本地部署**：后端读取本机文件系统路径，前端提供文件浏览与参数配置 UI，面向单机/局域网使用场景。
- **双模交互**（v7 新增）：系统同时支持传统 GUI 操作和 Agent 对话式交互，两种模式共享同一套后端服务层，互为补充。

### 1.2 系统目标

构建从无人机图像数据管理、数据处理、数据集构建到算法推理的端到端本地化工作流，形成"数据—处理—数据集—算法"的四模块闭环，并通过**智能助手（Agent）** 提供第五维度的**自然语言统一操控入口**，支撑大田农作物的智能监测与管理。

**v7 新增目标**：

- **智能助手**：以对话式交互替代部分繁琐 GUI 操作，将四大模块的功能接口沉淀为 Agent 工具目录，支持自然语言驱动数据管理、数据处理、数据集管理和算法应用，并可通过复合工作流一键生成农作物监测效果报告。

### 1.3 典型应用案例

以"甘蔗幼苗检测与计数"为典型应用案例。（与 v6 一致，此处不重复。）

**v7 新增典型场景**：

> 用户打开智能助手，输入"帮我查看最近一批甘蔗苗数据的计数情况，然后和上一批做个对比"。Agent 自动：① 查询架次列表，按飞行日期排序找到最近两批；② 分别查看两批的计数历史；③ 调用计数结果对比逻辑，生成对比摘要（株数差异、密度变化、置信度分布变化）；④ 以结构化卡片+自然语言描述返回给用户。

### 1.4 整体架构

系统采用**五模块 + Agent 层 + 前后端两层**架构。后端为 Flask RESTful API，前端为 Vue 3 单页应用，前后端通过 HTTP JSON 交互。Agent 层位于前端展示层与后端服务层之间，通过工具协议调用后端 API。

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                         展示层 (Presentation Layer)                           │
│   Vue 3 + Vite + ECharts                                                     │
│   ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────────┐ ┌─────────────────┐ │
│   │ 数据管理  │ │ 数据处理  │ │ 数据集   │ │ 算法广场    │ │ 智能助手(Agent)│ │
│   │ 面板     │ │ 面板     │ │ 管理面板 │ │            │ │ 对话式交互入口  │ │
│   └──────────┘ └──────────┘ └──────────┘ └────────────┘ └─────────────────┘ │
└─────────────────────────────────────┬────────────────────────────────────────┘
                                      │ HTTP REST API
┌─────────────────────────────────────▼────────────────────────────────────────┐
│                         Agent 编排层 (Agent Orchestration Layer)  [v7 新增]   │
│   ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌────────────────┐  │
│   │ LLM 推理引擎  │  │ 意图解析器    │  │ 工作流编排器  │  │ 工具执行器     │  │
│   │ (本地/API)    │  │ (Intent      │  │ (Workflow    │  │ (Tool          │  │
│   │              │  │  Parser)     │  │  Orchestrator)│  │  Executor)     │  │
│   └──────────────┘  └──────────────┘  └──────────────┘  └────────────────┘  │
│   ┌──────────────┐  ┌──────────────┐                                        │
│   │ 对话历史管理  │  │ 上下文窗口    │                                        │
│   │ (Session)    │  │ (Context)    │                                        │
│   └──────────────┘  └──────────────┘                                        │
└─────────────────────────────────────┬────────────────────────────────────────┘
                                      │ 工具调用 (Tool Calls)
┌─────────────────────────────────────▼────────────────────────────────────────┐
│                         服务层 (Service Layer)                                │
│   Flask 2.x                                                                   │
│   ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌────────────────┐  │
│   │ 数据管理服务  │  │ 数据处理服务  │  │ 数据集管理   │  │ 算法广场服务   │  │
│   │ · 架次CRUD   │  │ · 处理引擎   │  │ 服务         │  │ · 模型管理     │  │
│   │ · 自动扫描   │  │ · 任务注册   │  │ · 数据集导入 │  │ · 检测推理     │  │
│   │ · 图片预览   │  │ · 加工数据   │  │ · 统计报告   │  │ · 作物计数     │  │
│   │ · YAML持久化 │  │ · YAML持久化 │  │ · 格式转换   │  │ · 计数历史     │  │
│   └──────────────┘  └──────────────┘  └──────────────┘  └────────────────┘  │
└─────────────────────────────────────┬────────────────────────────────────────┘
                                      │ 文件系统 / 配置文件
┌─────────────────────────────────────▼────────────────────────────────────────┐
│                         数据层 (Data Layer)                                   │
│   ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐         │
│   │ 原始图片  │ │ 处理输出  │ │ 数据集   │ │ 模型仓库  │ │ 计数结果  │         │
│   │ data/    │ │ output/  │ │ datasets/│ │ models/  │ │ results/ │         │
│   └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘         │
│   ┌──────────────────────┐  ┌───────────────────────────┐                   │
│   │ Agent 会话持久化      │  │ 工具调用日志               │                   │
│   │ data/agent_sessions/ │  │ data/agent_logs/          │                   │
│   └──────────────────────┘  └───────────────────────────┘                   │
└──────────────────────────────────────────────────────────────────────────────┘
```

### 1.5 技术栈规范

**后端技术栈**（v6 已有部分不变，v7 新增项以 **粗体** 标注）：

| 组件 | 技术 | 版本 | 用途 |
|------|------|------|------|
| Web 框架 | Flask | 2.2.3 | RESTful API 服务 |
| 深度学习 | PyTorch | >=1.13.0 | 模型推理 |
| 检测框架 | Ultralytics | >=8.0.0 | YOLOv5/v8/v9/v10/v11/v12 引擎 |
| 图像处理 | OpenCV | 4.7.0.72 | CLAHE 增强、图像变换、滑窗裁切 |
| 图像库 | Pillow | 9.4.0 | 图像读写、缩略图生成 |
| 数值计算 | NumPy | 1.24.2 | NMS 计算、数组操作 |
| 配置管理 | PyYAML | 6.0 | YAML 配置文件解析与持久化 |
| **LLM 编排框架** | **LangChain / LangGraph** | **>=0.2** | **Agent 工具调用编排、对话管理、多步工作流** |
| **LLM SDK** | **openai** | **>=1.0** | **统一 LLM API 调用层（兼容 OpenAI / DeepSeek / Qwen 等）** |
| **向量存储（可选）** | **ChromaDB / FAISS** | **—** | **知识库检索增强（RAG），存储系统文档、操作手册** |
| **SSE 推送** | **Flask-SSE / 自研** | **—** | **Agent 流式响应推送到前端** |

**前端技术栈**（v7 新增项以 **粗体** 标注）：

| 组件 | 技术 | 版本 | 用途 |
|------|------|------|------|
| 框架 | Vue 3 | ^3.3.4 | Composition API |
| 构建工具 | Vite | ^4.4.9 | 开发服务器与构建 |
| 状态管理 | Pinia | — | 全局状态 |
| HTTP 客户端 | Axios | ^1.5.0 | API 请求 |
| 图表库 | ECharts | ^5.4.3 | 可视化图表 |
| 图标 | 自定义 SVG Icon 组件 | — | 统一 SVG 图标 |
| **Markdown 渲染** | **markdown-it / marked** | **—** | **Agent 对话中的 Markdown 格式化输出** |
| **代码高亮** | **highlight.js** | **—** | **Agent 输出中的代码/数据结构高亮** |
| **SSE 客户端** | **EventSource / fetch SSE** | **—** | **接收 Agent 流式响应** |

**端口与网络**（不变）：

| 服务 | 端口 | 说明 |
|------|------|------|
| 前端开发服务器 | 3000 | Vite dev server |
| 后端 API 服务 | 5000 | Flask app |
| 前端代理 | /api -> :5000 | Vite proxy 配置 |

### 1.6 系统边界

**v7 新增纳入范围**：

- 智能助手对话式交互界面（Chat UI）
- Agent 工具调用层（Tool Catalog）：将四大模块的 API 封装为 Agent 可调用的结构化工具
- 意图解析与工作流编排层（Intent → Workflow）
- LLM 推理集成（支持本地/API 两种部署模式）
- 对话会话管理与历史持久化
- 复合工作流（如一键生成监测效果报告）
- Agent 工具调用日志与审计

**v7 新增不纳入范围**：

- 模型训练、训练监控与主动学习闭环（与 v6 一致）
- 多用户认证与权限管理（本期仍为单用户本地部署）
- 语音交互、多模态输入（仅支持文本输入）
- Agent 自主决策执行（所有涉及数据删除、模型覆盖等破坏性操作需用户确认）
- 第三方工具生态接入（本期仅接入系统内部工具）

### 1.7 实现状态总览

| 模块 | 后端 | 前端 | 状态 |
|------|------|------|------|
| 模块一：数据管理 | 完整实现 | 完整实现 | ✅ 已完成 |
| 模块二：数据处理 | 完整实现 | 完整实现 | ✅ 已完成 |
| 模块三：数据集管理 | 完整实现 | 完整实现 | ✅ 已完成 |
| 模块四：算法广场 | 完整实现 | 完整实现 | ✅ 已完成 |
| **模块五：智能助手** | **待实现** | **待实现** | **📐 设计完成，待实现** |

### 1.8 首页与全局导航

**v7 更新**：侧边栏新增第五个一级菜单"智能助手"，图标为对话气泡/机器人。

**前端路由表**（v7 更新为 **18 条路由**）：

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
| **`/agent`** | **agent** | **Agent.vue** | **智能助手** |

---

## 二～四、模块一至模块四

> 模块一（数据管理）、模块二（数据处理）、模块三（数据集管理）、模块四（算法广场）的需求基线与 v6 一致，此处不重复。请参见 PRD v6 第二至四章。

---

## 五、模块五：智能助手（Agent）（📐 设计完成，待实现）

### 5.1 模块定位与职责边界

**模块定位**：智能助手是系统的**第五模块**，提供一种以自然语言驱动的对话式交互方式，作为传统 GUI 操作的**补充入口**（非替代）。它将系统四大模块的功能接口沉淀为结构化的工具目录（Tool Catalog），通过 LLM 的意图理解与工具调用能力，实现自然语言→系统操作的映射。

**职责边界**：

- **负责**：自然语言意图解析、工具调用编排、多步工作流执行、对话上下文管理、流式响应输出、工具调用日志审计。
- **不负责**：业务逻辑本身（由四大模块各自的 Engine/Registry 承担）；LLM 模型的训练与微调；用户认证与权限管理。
- **与 GUI 的关系**：Agent 是 GUI 的"快捷方式"，不是 GUI 的替代。用户可以在 Agent 中完成的操作，同样可以在 GUI 中完成；Agent 的优势在于跨模块复合操作的自动化编排和低交互成本的查询。

**核心设计原则**：

1. **工具驱动，非硬编码**：Agent 的每一步操作都通过调用明确定义的工具（Tool）完成，而非在 prompt 中硬编码逻辑。工具定义 = API 端点 + 参数 schema + 返回值 schema + 自然语言描述。
2. **安全边界**：所有破坏性操作（删除架次、删除数据集、删除处理结果等）在工具执行前必须通过用户确认机制（confirm dialog），Agent 不可自行执行。
3. **可观测性**：每次工具调用都记录完整的输入参数、返回结果、执行耗时，形成审计日志。
4. **渐进增强**：模块分三个阶段迭代交付，从基础单工具调用到复合工作流，逐步增强 Agent 能力。

### 5.2 可行性分析

#### 5.2.1 技术可行性

| 维度 | 分析 | 结论 |
|------|------|------|
| **API 基础设施** | 系统已有 40+ 结构化 RESTful API 端点，统一 `{success, data, message}` 响应格式，入参/出参明确。这些 API 天然适合封装为 Agent 工具。 | ✅ 高度可行 |
| **LLM Function Calling** | 主流 LLM（GPT-4o、DeepSeek-V3、Qwen-Max、Claude 3.5）均原生支持 function calling / tool use 协议。LangChain/LangGraph 提供成熟的 tool binding 抽象。 | ✅ 高度可行 |
| **异步任务兼容** | 计数/检测/处理均为异步任务（提交→轮询→获取结果）。Agent 工作流需要支持"提交→等待→获取"的 poll 模式，LangGraph 的 interrupt/resume 机制可覆盖。 | ✅ 可行，需设计 poll 适配层 |
| **本地 LLM 部署** | 用户可能希望完全本地运行（不依赖外部 API）。可通过 Ollama + Qwen2.5/DeepSeek-V3 本地部署，LangChain 统一接口兼容。 | ✅ 可行，需提供配置指引 |
| **前端 Chat UI** | Vue 3 生态有成熟的 Chat UI 组件库（如 vue-chat-scroll、chat-ui-kit），SSE 流式推送可实现实时打字效果。 | ✅ 高度可行 |
| **单机性能** | Agent 层增加的计算开销主要是 LLM 推理延迟（本地 7B 模型约 2-5s/轮，API 约 1-2s/轮）。后端现有 ThreadPoolExecutor(max_workers=1) 限制了并发任务，但 Agent 操作以串行为主，不构成瓶颈。 | ✅ 可行 |

#### 5.2.2 风险与应对

| 风险 | 影响 | 应对策略 |
|------|------|----------|
| LLM 意图解析不准确 | 调用错误的工具或传入错误参数 | ① 工具描述中嵌入参数约束和示例；② 关键操作前展示执行计划让用户确认；③ 提供 fallback 到 GUI 的快捷链接 |
| 异步任务超时 | Agent 等待检测/计数任务完成时间过长 | ① 设置合理的轮询超时（默认 300s）；② 超时后返回"任务仍在进行中"提示+任务 ID；③ 提供任务进度查询工具 |
| LLM 上下文窗口限制 | 长对话或大量工具描述挤占上下文 | ① 工具描述精简化（每工具 100-200 token）；② 对话摘要机制（超过 20 轮自动压缩）；③ 仅注入相关工具而非全量工具 |
| 本地 LLM 推理质量不足 | 7B 小模型的 function calling 能力可能不够稳定 | ① 支持云端 API 作为默认选项；② 本地模型限定使用 Qwen2.5-72B 或 DeepSeek-V3 级别；③ 提供 tool calling 准确率测试套件 |
| 安全边界被绕过 | Agent 误执行删除操作 | ① 破坏性工具标记 `destructive: true`，执行前强制 confirm；② 工具执行器做白名单校验；③ 所有操作写审计日志 |

### 5.3 架构设计

#### 5.3.1 Agent 编排层架构

```
用户输入 (自然语言)
    │
    ▼
┌─────────────────────────────────────────────────────┐
│                   Agent 编排层                        │
│                                                     │
│  ① 意图解析 (Intent Parsing)                         │
│     · LLM 理解用户意图                                │
│     · 识别：查询型 / 操作型 / 复合工作流型             │
│     · 提取关键实体（架次 ID、模型名称、日期范围等）     │
│                                                     │
│  ② 工具选择 (Tool Selection)                         │
│     · 从工具目录中选择合适的工具                       │
│     · 一个意图可能映射到 1~N 个工具调用                │
│                                                     │
│  ③ 工作流编排 (Workflow Orchestration)                │
│     · 单步：直接调用单个工具                           │
│     · 多步：编排工具调用链，前序结果传递给后续工具       │
│     · 循环：轮询异步任务直到完成                       │
│                                                     │
│  ④ 工具执行 (Tool Execution)                         │
│     · 参数校验 → 调用后端 API → 解析返回值             │
│     · 破坏性操作 → 用户确认 → 执行/取消               │
│                                                     │
│  ⑤ 响应生成 (Response Generation)                    │
│     · 将工具执行结果转化为用户可读的自然语言描述        │
│     · 格式化：表格、列表、摘要、图表引用               │
│     · 流式输出到前端                                  │
└─────────────────────────────────────────────────────┘
    │
    ▼
前端 Chat UI (SSE 流式渲染)
```

#### 5.3.2 工具协议定义

每个 Agent 工具遵循统一的协议格式：

```yaml
tool:
  name: "tool_name"                    # 工具唯一标识
  description: "自然语言描述"            # LLM 用于理解工具用途
  module: "data|processing|dataset|algo" # 所属模块
  category: "query|action|composite"    # 工具类别
  destructive: false                    # 是否为破坏性操作
  parameters:                           # JSON Schema 格式的参数定义
    type: object
    properties:
      param1:
        type: string
        description: "参数说明"
    required: ["param1"]
  returns:                              # 返回值 schema
    type: object
    properties:
      field1:
        type: string
  api_mapping:                          # 映射到的后端 API
    method: "GET|POST|PUT|DELETE"
    path: "/api/xxx"
    param_mapping:                      # 工具参数 → API 参数的映射规则
      param1: "query.param1"
```

#### 5.3.3 工具目录（Tool Catalog）

以下为完整的工具目录设计，基于现有 40+ API 端点梳理为 22 个 Agent 工具：

**模块一：数据管理（4 个工具）**

| 工具名 | 描述 | 类别 | API 映射 | 破坏性 |
|--------|------|------|----------|--------|
| `list_batches` | 查询架次列表，可按作物类型、飞行日期、地块名称筛选 | query | `GET /api/batches` | 否 |
| `get_batch_detail` | 查看某个架次的详细信息（元数据、图片数量、存放路径） | query | `GET /api/batches/{id}` | 否 |
| `create_batch` | 注册新的无人机采集架次 | action | `POST /api/batches` | 否 |
| `delete_batch` | 删除架次注册（不删除物理文件） | action | `DELETE /api/batches/{id}` | **是** |

**模块二：数据处理（4 个工具）**

| 工具名 | 描述 | 类别 | API 映射 | 破坏性 |
|--------|------|------|----------|--------|
| `list_processing_tasks` | 查询处理任务列表，可按类型（CLAHE/裁切）和状态筛选 | query | `GET /api/processing/tasks` | 否 |
| `create_clahe_task` | 对指定架次创建 CLAHE 增强任务 | action | `POST /api/processing/clahe` | 否 |
| `create_crop_task` | 对指定架次创建滑窗裁切任务 | action | `POST /api/processing/crop` | 否 |
| `get_task_status` | 查询某个处理任务的执行状态和进度 | query | `GET /api/processing/tasks/{id}` | 否 |

**模块三：数据集管理（4 个工具）**

| 工具名 | 描述 | 类别 | API 映射 | 破坏性 |
|--------|------|------|----------|--------|
| `list_datasets` | 查询已注册的数据集列表 | query | `GET /api/datasets` | 否 |
| `get_dataset_detail` | 查看数据集详情（格式、标注统计、图片数量） | query | `GET /api/datasets/{id}` | 否 |
| `get_dataset_report` | 获取数据集的统计分析报告（类别分布、尺寸分布等） | query | `GET /api/datasets/{id}/report` | 否 |
| `delete_dataset` | 删除数据集注册 | action | `DELETE /api/datasets/{id}` | **是** |

**模块四：算法广场（6 个工具）**

| 工具名 | 描述 | 类别 | API 映射 | 破坏性 |
|--------|------|------|----------|--------|
| `list_models` | 查询已注册的检测模型列表及当前激活模型 | query | `GET /api/models` | 否 |
| `switch_model` | 切换当前激活的检测模型 | action | `POST /api/models/switch` | 否 |
| `detect_image` | 对单张图片执行作物检测推理 | action | `POST /api/detect` (单图模式) | 否 |
| `count_crop` | 对高分辨率原图执行作物计数（异步） | action | `POST /api/counting` | 否 |
| `get_counting_result` | 获取计数任务的结果报告 | query | `GET /api/counting/tasks/{id}/result` | 否 |
| `list_counting_history` | 查询历史计数记录 | query | `GET /api/counting/history` | 否 |

**跨模块：复合工作流（4 个工具）**

| 工具名 | 描述 | 类别 | 说明 |
|--------|------|------|------|
| `generate_monitoring_report` | 生成农作物监测效果报告：自动查询最新架次数据→选择最优模型→执行计数→对比历史→生成结构化报告 | composite | 编排 `list_batches` → `count_crop` → `get_counting_result` → `list_counting_history` |
| `compare_counting_results` | 对比两次计数结果，生成差异分析 | composite | 编排 `get_counting_result` x2 → 差异计算 |
| `batch_health_check` | 检查系统所有模块的健康状态 | composite | 编排 `GET /api/health` + 各模块元数据聚合 |
| `data_quality_summary` | 对指定架次数据的质量概览（图片数量、分辨率分布、是否有处理结果） | composite | 编排 `get_batch_detail` + `list_processing_tasks` |

#### 5.3.4 意图分类与路由

Agent 将用户输入分为三类意图，采用不同的处理策略：

| 意图类型 | 示例 | 处理策略 | 工具调用次数 |
|----------|------|----------|-------------|
| **查询型** | "当前有多少个模型？""最近一批数据是什么时候的？" | 单步查询 → 格式化返回 | 1 |
| **操作型** | "帮我注册一个新架次""切换到 YOLOv12s 模型" | 参数提取 → 用户确认（如需） → 执行 | 1-2 |
| **复合工作流型** | "帮我看看最近甘蔗苗长势怎么样""对比一下最近两次计数结果" | 意图分解 → 多步编排 → 中间结果传递 → 汇总输出 | 3-8 |

**意图识别策略**：不使用传统的 NLU 分类器，而是直接利用 LLM 的 function calling 能力。将工具目录作为 function schema 注入 LLM prompt，由 LLM 自主决定调用哪些工具、传入什么参数。对于复合工作流，使用 LangGraph 的 graph 机制实现多步编排。

#### 5.3.5 异步任务适配

系统中有三类异步任务（检测批处理、计数、数据处理），Agent 需要适配其"提交→轮询→获取"模式：

```
Agent 调用异步工具（如 count_crop）
    │
    ▼
工具执行器提交任务到后端 API → 拿到 task_id
    │
    ▼
工具执行器进入 poll 循环：
    │  while task_status != "completed" and not timeout:
    │      sleep(3s)
    │      GET /api/{module}/tasks/{task_id}
    │      report_progress(current_progress)
    │
    ▼
任务完成 → 返回结果给 Agent
```

**超时策略**：
- 默认超时：300 秒
- 进度上报：每 3 秒轮询一次，将进度信息通过 SSE 推送给前端（如"计数任务进度 67%：已完成分块检测，正在进行 NMS 合并"）
- 超时处理：返回"任务仍在进行中，task_id=xxx，您可以稍后查询结果"

#### 5.3.6 安全机制

```
用户输入 → LLM 意图解析 → 工具选择
                               │
                    ┌──────────▼──────────┐
                    │  工具是否 destructive? │
                    └──────────┬──────────┘
                         ┌─────┴─────┐
                        是           否
                         │            │
                    ┌────▼────┐  ┌───▼────┐
                    │ 生成确认 │  │ 直接   │
                    │ 对话框   │  │ 执行   │
                    │ "即将删除│  └───┬────┘
                    │ 架次X，  │      │
                    │ 确认？"  │      │
                    └────┬────┘      │
                    ┌────┴────┐      │
                   确认      取消     │
                    │         │      │
                ┌───▼──┐  ┌──▼──┐   │
                │ 执行  │  │ 取消 │   │
                │ 工具  │  │ 操作 │   │
                └───┬──┘  └─────┘   │
                    │                │
                    └───────┬────────┘
                            │
                    ┌───────▼────────┐
                    │ 写入审计日志    │
                    └────────────────┘
```

### 5.4 前端交互设计

#### 5.4.1 页面布局

`/agent` 页面采用**左侧对话 + 右侧信息面板**的双栏布局：

```
┌─────────────────────────────────────────────────────────────┐
│  智能助手                                    [清空对话] [历史] │
├────────────────────────────────┬────────────────────────────┤
│                                │                            │
│  🤖 你好！我是田间智瞰的智能    │  📋 工具调用日志            │
│     助手，可以帮你管理数据、     │                            │
│     执行检测和计数任务。        │  ┌──────────────────────┐  │
│     试试问我...               │  │ ① list_batches       │  │
│                                │  │   → 查询架次列表      │  │
│  👤 帮我看看最近甘蔗苗计数情况  │  │   ✅ 成功 (120ms)    │  │
│                                │  ├──────────────────────┤  │
│  🤖 正在为您查询最近的架次数据  │  │ ② count_crop         │  │
│     ...                        │  │   → 批次 #3 计数中    │  │
│                                │  │   ⏳ 进度 67%        │  │
│  🤖 查询完成！最近一批数据是    │  └──────────────────────┘  │
│     2026-09-18 采集的甘蔗田     │                            │
│     数据（批次 #3），共 456 张。│  📊 快捷操作               │
│                                │  · 查看模型列表            │
│     已对该批次执行计数分析：     │  · 创建 CLAHE 任务        │
│     · 检测株数：12,847 株       │  · 查看计数历史            │
│     · 平均密度：4.2 株/m²       │  · 生成监测报告            │
│     · 置信度均值：0.87          │                            │
│                                │                            │
├────────────────────────────────┤                            │
│  [输入消息...]           [发送] │                            │
└────────────────────────────────┴────────────────────────────┘
```

#### 5.4.2 消息类型

| 消息类型 | 渲染方式 | 说明 |
|----------|----------|------|
| 纯文本 | Markdown 渲染 | Agent 的自然语言回复 |
| 数据表格 | 表格组件 | 查询结果列表（架次列表、模型列表等） |
| 工具执行状态 | 内联状态卡片 | 显示工具调用名称、参数、状态（执行中/成功/失败）、耗时 |
| 确认对话框 | 模态弹窗 | 破坏性操作前的用户确认 |
| 进度条 | 内联进度条 | 异步任务的实时进度 |
| 错误信息 | 高亮错误块 | 工具执行失败的错误详情 |
| 报告卡片 | 结构化卡片 | 监测效果报告的可视化展示（含关键指标、对比数据） |

#### 5.4.3 前端状态管理

新增 Pinia store `useAgentStore`：

```typescript
interface AgentMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  type: 'text' | 'table' | 'tool_status' | 'confirm' | 'progress' | 'report';
  metadata?: {
    tool_calls?: ToolCallRecord[];
    table_data?: Record<string, any>[];
    confirm_action?: ConfirmAction;
    progress?: ProgressInfo;
  };
  timestamp: number;
}

interface AgentSession {
  id: string;
  title: string;
  messages: AgentMessage[];
  created_at: number;
  updated_at: number;
}

interface AgentState {
  sessions: AgentSession[];
  currentSessionId: string | null;
  isStreaming: boolean;
  toolLogs: ToolCallLog[];
}
```

### 5.5 API 设计

Agent 模块新增以下后端 API 端点：

#### 5.5.1 对话接口

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/api/agent/chat` | 发送消息，返回 SSE 流式响应 |
| `GET` | `/api/agent/sessions` | 查询会话列表 |
| `POST` | `/api/agent/sessions` | 创建新会话 |
| `GET` | `/api/agent/sessions/{id}` | 获取会话详情（含历史消息） |
| `DELETE` | `/api/agent/sessions/{id}` | 删除会话 |
| `POST` | `/api/agent/sessions/{id}/confirm` | 用户确认/取消破坏性操作 |

#### 5.5.2 系统接口

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/agent/tools` | 获取完整工具目录（含 schema） |
| `GET` | `/api/agent/health` | Agent 模块健康检查（LLM 连通性、工具加载状态） |
| `GET` | `/api/agent/logs` | 查询工具调用审计日志（支持分页和时间范围筛选） |

#### 5.5.3 SSE 流式响应格式

`POST /api/agent/chat` 返回 Server-Sent Events 流，事件类型如下：

```
event: text_delta
data: {"content": "正在为您"}

event: text_delta
data: {"content": "查询架次数据"}

event: tool_call
data: {"tool": "list_batches", "params": {"crop_type": "sugarcane"}, "status": "executing"}

event: tool_result
data: {"tool": "list_batches", "status": "success", "duration_ms": 85, "result_count": 3}

event: text_delta
data: {"content": "找到 3 个甘蔗架次数据，最近一批是..."}

event: done
data: {"session_id": "xxx", "message_id": "yyy"}
```

### 5.6 分阶段迭代计划

#### Phase 1：基础 Agent 框架（预计 2 周）

**目标**：搭建 Agent 编排层基础框架，实现单步工具调用。

| 任务 | 说明 | 交付物 |
|------|------|--------|
| P1-1：LLM 接入层 | 封装 OpenAI-compatible API 调用，支持 DeepSeek/Qwen/GPT 统一接口 | `backend/core/llm_client.py` |
| P1-2：工具协议定义 | 定义 Tool schema（YAML/Python dataclass），实现工具注册机制 | `backend/core/tool_registry.py` |
| P1-3：基础工具封装 | 封装模块一的 4 个查询类工具 + 模块四的 2 个查询类工具（共 6 个） | `backend/agent/tools/` |
| P1-4：Agent 编排器 | 基于 LangChain/LangGraph 实现单轮 tool calling 循环 | `backend/core/agent.py` |
| P1-5：Chat API | 实现 `/api/agent/chat`（SSE 流式）和会话管理 API | `backend/api/agent_api.py` |
| P1-6：前端 Chat UI | 实现基础对话界面（文本输入、消息列表、Markdown 渲染） | `frontend/src/views/agent/Agent.vue` |
| P1-7：前端 Agent Store | 实现 `useAgentStore` 和 SSE 客户端 | `frontend/src/stores/agent.ts` |

**Phase 1 交付后用户可做到**：
- 通过对话查询架次列表、模型列表、数据集列表等只读信息
- 查看单个架次/模型/数据集的详情
- 对话中展示 Markdown 格式化的查询结果

**验收标准**：
- 能正确响应至少 5 种不同类型的查询意图
- 工具调用正确率 ≥ 90%（基于 20 条测试 query）
- SSE 流式响应正常工作，延迟 < 3s（API 模式）

---

#### Phase 2：操作型工具 + 异步任务支持（预计 2 周）

**目标**：扩展到操作型工具和异步任务，覆盖四大模块的核心操作。

| 任务 | 说明 | 交付物 |
|------|------|--------|
| P2-1：操作型工具封装 | 封装剩余 12 个工具（创建架次、CLAHE、裁切、切换模型、检测、计数等） | `backend/agent/tools/` 补充 |
| P2-2：异步任务适配器 | 实现 poll 循环机制，支持提交→轮询→返回的异步任务流程 | `backend/core/async_task_adapter.py` |
| P2-3：进度推送 | 通过 SSE 实时推送异步任务进度到前端 | Agent SSE 扩展 |
| P2-4：安全确认机制 | 实现 destructive 操作的前端确认弹窗 + 后端白名单校验 | 前端/后端协同 |
| P2-5：审计日志 | 实现工具调用日志记录和查询接口 | `backend/core/agent_logger.py` + API |
| P2-6：前端增强 | 工具执行状态卡片、进度条、确认弹窗、工具调用日志面板 | 前端组件扩展 |
| P2-7：对话上下文管理 | 实现多轮对话的上下文维护和历史压缩 | Agent 对话管理扩展 |

**Phase 2 交付后用户可做到**：
- 通过对话执行所有四大模块的操作（创建、修改、删除）
- 提交异步任务（计数、检测、数据处理）并实时查看进度
- 破坏性操作前收到确认提示
- 查看工具调用历史日志

**验收标准**：
- 22 个工具全部可正确调用
- 异步任务 poll 机制稳定（10 次连续测试无超时误报）
- destructive 工具 100% 弹出确认提示

---

#### Phase 3：复合工作流 + 监测报告（预计 2 周）

**目标**：实现跨模块复合工作流，支持一键生成监测效果报告。

| 任务 | 说明 | 交付物 |
|------|------|--------|
| P3-1：复合工作流引擎 | 基于 LangGraph 实现多步工作流编排（graph + conditional edges） | `backend/core/workflow_engine.py` |
| P3-2：报告生成器 | 实现 `generate_monitoring_report` 工作流：查最新架次→选模型→计数→对比历史→生成报告 | `backend/agent/workflows/` |
| P3-3：对比分析工具 | 实现 `compare_counting_results`，支持两次计数结果的差异分析 | `backend/agent/tools/composite.py` |
| P3-4：报告可视化 | 前端报告卡片组件：关键指标展示、历史趋势图表、对比数据 | 前端报告组件 |
| P3-5：会话持久化 | 对话历史持久化到 YAML 文件，支持恢复 | `data/agent_sessions/` |
| P3-6：知识库增强（可选） | 将系统操作手册、常见问题嵌入 RAG，提升 Agent 的领域理解 | `backend/core/knowledge_base.py` |
| P3-7：端到端测试 | 覆盖 10 个典型复合场景的自动化测试 | `backend/tests/test_agent.py` |

**Phase 3 交付后用户可做到**：
- 说"帮我看看最近甘蔗苗长势"，Agent 自动完成数据查询→计数→分析→报告的全流程
- 对比不同时间/不同模型的计数结果
- 一键生成包含株数、密度、置信度、历史趋势的监测效果报告
- 会话历史可恢复

**验收标准**：
- `generate_monitoring_report` 从输入到输出完整报告 < 5 分钟（含计数时间）
- 报告包含≥5 个关键指标（株数、密度、置信度均值、与上次对比、趋势）
- 10 个端到端测试场景全部通过

### 5.7 配置设计

Agent 模块的配置项新增到 `config/agent.yaml`：

```yaml
# Agent 模块配置
agent:
  # LLM 配置
  llm:
    provider: "deepseek"           # deepseek | openai | qwen | ollama
    model: "deepseek-chat"         # 模型名称
    api_key: ""                    # API Key（从环境变量读取）
    api_base: "https://api.deepseek.com"  # API 基础地址
    temperature: 0.1               # 低温度保证工具调用稳定性
    max_tokens: 4096

  # 本地模型配置（当 provider=ollama 时使用）
  ollama:
    base_url: "http://localhost:11434"
    model: "qwen2.5:72b"

  # Agent 行为配置
  behavior:
    max_tool_calls_per_turn: 10    # 单轮最大工具调用次数
    async_poll_interval_sec: 3     # 异步任务轮询间隔
    async_timeout_sec: 300         # 异步任务超时
    confirm_destructive: true      # 破坏性操作是否需要确认
    context_window_turns: 20       # 上下文保留的对话轮数
    auto_summarize_after: 30       # 超过此轮数自动压缩历史

  # 工具配置
  tools:
    enabled_modules:               # 启用的工具模块
      - data
      - processing
      - dataset
      - algo
    disabled_tools: []             # 禁用的特定工具

  # 日志配置
  logging:
    enabled: true
    log_dir: "data/agent_logs"
    retention_days: 30
```

### 5.8 目录结构设计

```
backend/
├── api/
│   ├── agent_api.py              # [新增] Agent Chat/Sessions/Tools API
│   └── ...                       # 已有 API 模块
├── agent/                        # [新增] Agent 模块目录
│   ├── __init__.py
│   ├── tools/                    # 工具定义
│   │   ├── __init__.py
│   │   ├── data_tools.py         # 数据管理工具 (list_batches, get_batch_detail, ...)
│   │   ├── processing_tools.py   # 数据处理工具 (list_tasks, create_clahe, ...)
│   │   ├── dataset_tools.py      # 数据集工具 (list_datasets, get_report, ...)
│   │   ├── algo_tools.py         # 算法工具 (list_models, detect, count, ...)
│   │   └── composite_tools.py    # 复合工具 (monitoring_report, compare, ...)
│   ├── workflows/                # 复合工作流定义
│   │   ├── __init__.py
│   │   └── monitoring_report.py  # 监测效果报告工作流
│   ├── prompts/                  # Prompt 模板
│   │   ├── system_prompt.md      # 系统 prompt（角色定义、工具使用指南）
│   │   └── report_template.md    # 报告模板
│   └── knowledge/                # 知识库（可选）
│       └── operation_manual.md   # 系统操作手册
├── core/
│   ├── agent.py                  # [新增] Agent 编排器（LangGraph）
│   ├── llm_client.py             # [新增] LLM 统一调用客户端
│   ├── tool_registry.py          # [新增] 工具注册与管理
│   ├── async_task_adapter.py     # [新增] 异步任务 poll 适配器
│   ├── agent_logger.py           # [新增] 工具调用审计日志
│   └── ...                       # 已有 core 模块
├── config/
│   └── agent.yaml                # [新增] Agent 配置文件
└── tests/
    ├── test_agent.py             # [新增] Agent 端到端测试
    ├── test_tools.py             # [新增] 工具单元测试
    └── test_workflows.py         # [新增] 工作流测试

frontend/
└── src/
    ├── views/
    │   └── agent/
    │       └── Agent.vue         # [新增] 智能助手页面
    ├── stores/
    │   └── agent.ts              # [新增] Agent 状态管理
    ├── components/
    │   └── agent/                # [新增] Agent 组件
    │       ├── ChatMessage.vue   # 消息气泡组件
    │       ├── ToolCallCard.vue  # 工具调用状态卡片
    │       ├── ConfirmDialog.vue # 破坏性操作确认弹窗
    │       ├── ProgressBar.vue   # 异步任务进度条
    │       └── ReportCard.vue    # 监测报告卡片
    └── api/
        └── agent.ts              # [新增] Agent API 客户端（SSE）

data/
├── agent_sessions/               # [新增] 会话持久化
│   └── session_{id}.yaml
└── agent_logs/                   # [新增] 工具调用日志
    └── {date}.yaml

config/
└── agent.yaml                    # [新增] Agent 配置
```

### 5.9 非功能性需求

| 维度 | 要求 |
|------|------|
| **响应时间** | 单步查询类工具 < 3s（API 模式），操作类工具提交 < 2s + 异步执行时间 |
| **并发** | 同一时刻仅支持一个 Agent 会话（与现有 TaskManager 单线程模型一致） |
| **可用性** | Agent 模块不可用时不影响四大模块的正常 GUI 操作 |
| **可观测性** | 所有工具调用记录完整的输入/输出/耗时/状态，保留 30 天 |
| **降级** | LLM 服务不可用时，Agent 页面显示"智能助手暂不可用"提示，并提供跳转到 GUI 操作的快捷链接 |
| **兼容性** | 支持 DeepSeek / Qwen / GPT 系列 API，支持 Ollama 本地部署 |

### 5.10 依赖与前置条件

| 依赖项 | 说明 | 必要性 |
|--------|------|--------|
| LLM API Key | 至少一个可用的 LLM API（DeepSeek/OpenAI/Qwen）或本地 Ollama | 必要 |
| LangChain / LangGraph | Python 包，Agent 编排框架 | 必要 |
| openai Python SDK | 统一 API 调用 | 必要 |
| markdown-it / marked | 前端 Markdown 渲染 | 必要 |
| SSE 支持 | Flask SSE 或自研 EventSource | 必要 |
| ChromaDB / FAISS | 向量存储（RAG） | 可选 |
| highlight.js | 代码高亮 | 可选 |

---

## 六、数据模型与持久化

### 6.1 Agent 会话持久化

会话数据存储为 YAML 文件 `data/agent_sessions/session_{session_id}.yaml`：

```yaml
session_id: "sess_20260920_001"
title: "甘蔗苗计数查询"
created_at: "2026-09-20T16:30:00"
updated_at: "2026-09-20T16:35:00"
messages:
  - role: user
    content: "帮我看看最近甘蔗苗计数情况"
    timestamp: "2026-09-20T16:30:00"
  - role: assistant
    content: "正在为您查询..."
    tool_calls:
      - tool: list_batches
        params: { crop_type: "sugarcane" }
        result: { ... }
        status: success
        duration_ms: 85
    timestamp: "2026-09-20T16:30:01"
```

### 6.2 工具调用日志

日志存储为 `data/agent_logs/{YYYY-MM-DD}.yaml`：

```yaml
- timestamp: "2026-09-20T16:30:01"
  session_id: "sess_20260920_001"
  tool: "list_batches"
  params: { crop_type: "sugarcane" }
  status: "success"
  duration_ms: 85
  result_summary: "返回 3 个架次"
```

---

## 七、测试策略

### 7.1 测试层级

| 层级 | 范围 | 工具 |
|------|------|------|
| **单元测试** | 每个工具函数的输入/输出正确性 | pytest |
| **集成测试** | Agent 编排器 → 工具 → 后端 API 的完整链路 | pytest + httpx |
| **LLM 调用测试** | function calling 准确率（20 条测试 query） | pytest + mock LLM |
| **端到端测试** | 10 个典型复合场景（含异步任务、确认流程） | pytest + 手动验证 |
| **前端测试** | Chat UI 交互、SSE 连接、消息渲染 | 手动验证 |

### 7.2 典型测试场景

| 编号 | 场景 | 期望行为 |
|------|------|----------|
| TC-01 | "当前有哪些模型？" | 调用 `list_models`，返回模型列表表格 |
| TC-02 | "切换到 YOLOv12s" | 调用 `switch_model`，确认切换成功 |
| TC-03 | "删除批次 #5" | 弹出确认框，确认后执行 `delete_batch` |
| TC-04 | "对第三批次跑计数" | 提交 `count_crop` → poll → 返回计数结果 |
| TC-05 | "最近甘蔗苗长势怎么样？" | 复合工作流：查批次→计数→对比→报告 |
| TC-06 | "用 CLAHE 增强一下最新数据" | 创建 CLAHE 任务 → 返回任务 ID 和状态 |
| TC-07 | "对比批次 #2 和 #3 的计数结果" | 获取两次结果 → 生成差异分析 |
| TC-08 | LLM 不可用时的降级 | 显示"智能助手暂不可用"+ GUI 跳转链接 |
| TC-09 | 异步任务超时 | 返回"任务进行中"提示 + task_id |
| TC-10 | 连续多轮对话 | 上下文正确维护，第 N 轮可引用第 1 轮的结果 |

---

## 八、术语表

| 术语 | 定义 |
|------|------|
| **Agent** | 以 LLM 为推理核心的智能体，能够理解自然语言并通过调用工具与系统交互 |
| **Tool（工具）** | Agent 可调用的结构化接口，对应后端的一个或一组 API 端点 |
| **Tool Catalog（工具目录）** | 系统中所有可用工具的注册表，包含工具名称、描述、参数 schema 和 API 映射 |
| **Function Calling** | LLM 的工具调用能力——根据用户意图，生成结构化的工具调用请求（函数名 + 参数 JSON） |
| **Intent（意图）** | 用户通过自然语言表达的目标或需求，由 Agent 解析为具体的工具调用序列 |
| **Workflow（工作流）** | 由多个工具调用步骤编排而成的复合操作流程 |
| **SSE** | Server-Sent Events，服务端向客户端推送实时事件的 HTTP 协议 |
| **RAG** | Retrieval-Augmented Generation，检索增强生成，将外部知识注入 LLM 上下文 |
| **LangGraph** | LangChain 生态的工作流编排框架，基于有向图定义 Agent 的多步推理逻辑 |
| **destructive 操作** | 不可逆的操作（如删除数据），执行前需用户明确确认 |

---

## 附录 A：工具目录完整 schema 示例

```yaml
# list_batches 工具完整定义
name: "list_batches"
description: "查询系统中已注册的无人机采集架次列表。支持按作物类型、飞行日期范围、地块名称筛选。返回每个架次的 ID、名称、作物类型、飞行日期、图片数量等基本信息。"
module: "data"
category: "query"
destructive: false
parameters:
  type: object
  properties:
    crop_type:
      type: string
      description: "按作物类型筛选，如 'sugarcane'（甘蔗）、'rice'（水稻）"
    flight_date_from:
      type: string
      format: date
      description: "飞行日期起始（YYYY-MM-DD），筛选此日期之后的架次"
    flight_date_to:
      type: string
      format: date
      description: "飞行日期截止（YYYY-MM-DD），筛选此日期之前的架次"
    plot_name:
      type: string
      description: "按地块名称模糊搜索"
  required: []
returns:
  type: object
  properties:
    batches:
      type: array
      items:
        type: object
        properties:
          id: { type: string }
          name: { type: string }
          crop_type: { type: string }
          flight_date: { type: string }
          plot_name: { type: string }
          image_count: { type: integer }
          drone_model: { type: string }
    total:
      type: integer
api_mapping:
  method: "GET"
  path: "/api/batches"
  param_mapping:
    crop_type: "query.crop_type"
    flight_date_from: "query.flight_date_from"
    flight_date_to: "query.flight_date_to"
    plot_name: "query.plot_name"
```

---

## 附录 B：System Prompt 设计

```
你是"田间智瞰"大田农作物智能监测与管理系统的智能助手。你的职责是帮助用户通过自然语言完成系统中的各项操作。

## 你的能力
你可以调用以下工具来帮助用户：
- 数据管理：查询/创建/删除无人机采集架次
- 数据处理：创建 CLAHE 增强、滑窗裁切任务，查看任务状态
- 数据集管理：查询数据集、获取统计报告
- 算法广场：查询模型、切换模型、执行检测和计数
- 综合分析：生成监测效果报告、对比计数结果

## 工作原则
1. **先理解意图，再选择工具**：不要急于调用工具，先确认理解用户的真实需求
2. **查询优先**：在执行操作前，先查询当前状态（如先查有哪些架次，再执行操作）
3. **安全第一**：删除操作必须提示用户确认
4. **结果可视化**：尽量用表格和列表展示数据，用关键数字概括结果
5. **异常处理**：工具调用失败时，解释原因并建议替代方案
6. **上下文记忆**：记住对话中的关键信息（如用户提到的批次 ID、模型名称），后续交互中引用

## 领域知识
- 本系统管理无人机采集的大田农作物图像数据
- 当前主要应用场景是甘蔗幼苗检测与计数
- 使用 YOLO 系列模型（v5/v8/v11/v12/v26）进行目标检测
- 计数结果包含：株数、密度（株/m²）、置信度分布、空间热力图
- CLAHE 是对比度增强算法，用于提升图像质量
- 滑窗裁切将大图切分为小块，便于模型推理

## 语言
请使用中文与用户交流。技术术语可附带英文原文。
```

---

*文档结束*