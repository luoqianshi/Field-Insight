# 改动日志（LOG）

> 每行一条操作记录：`- [YYYY-MM-DD HH:mm] type(scope): 一句话摘要`，时间为任务完成时的本地时间（Asia/Shanghai）。
> 新条目追加到文件末尾（时间正序），历史条目不改不删。写入规则见 AGENTS.md「改动日志」章节。
> 2026-11-20 之前的条目为历史回填，来源：`.lqs/update_report/`（报告编号）与 git 提交（哈希）。

- [2026-08-10 00:00] feat(algo): 算法管理模块优化——FP16 清理、注册持久化、文件上传与图标统一（报告001）
- [2026-08-10 21:34] feat(algo): 作物检测与计数新增图片查看交互（报告002）
- [2026-08-11 01:12] feat(algo): 作物计数管线五项改进——批量推理与 max_det 告警（报告003）
- [2026-08-11 11:15] feat(algo): 计数参数默认值调整与前端 UI/UX 质感升级（报告004）
- [2026-08-11 23:33] feat(data): 数据管理架次真实功能替代 Mock（报告005）
- [2026-08-12 00:03] feat(data): 架次登记表单增强——命名格式/作物自定义/文件夹选择（报告006）
- [2026-08-12 20:10] feat(process): 数据处理真实实现——CLAHE/滑窗裁切/任务持久化/加工数据双tab（报告007）
- [2026-08-12 21:54] feat(ui): 导航折叠拖拽、检测计数图片持久化、处理输入源与差异化预览（报告008）
- [2026-08-13 01:21] style(ui): 首页卡片高度对齐、原始数据卡片化、侧边栏吸附与处理任务顶部Tab（报告009）
- [2026-08-13 18:25] style(ui): 侧边栏折叠态图标布局优化——水平居中与间距调整（报告010）
- [2026-08-14 01:23] feat(dataset): 数据集管理真实实现——9 端点 API/ECharts 统计报告/样本浏览与删除（224c23a–383f1a1）
- [2026-08-15 10:59] feat(dataset): 数据集详情页布局重排、统计口径调整、5% 抽样与翻页优化（报告011）
- [2026-09-02 21:08] build: 新增 CPU 版依赖 requirements-cpu.txt（b2faf74）
- [2026-10-01 17:32] docs: 新增 AGENTS.md AI 编码代理项目指引（82f7e5e）
- [2026-10-12 01:30] feat: 应用名称与模型配置更新，页面布局与侧边栏调整（1b6a791）
- [2026-11-02 17:01] build(frontend): 双模式构建与 GitHub Pages 自动部署工作流（471df63）
- [2026-11-02 19:03] docs: 全栈开发经验沉淀与调研证据清单（52471b5）
- [2026-11-12 16:04] docs: 替换新应用图标并更新引用（5156773）
- [2026-11-13 08:09] refactor(algo): 移除算法管理页顶部静态统计卡片（7a5f96d）
- [2026-11-19 21:14] chore(repo): 目录规范梳理——SDD/AI 分析/图标源迁移与 gitignore 根锚定修复（43ec57b）
- [2026-11-19 21:39] feat(desktop): Electron 桌面壳与 PyInstaller 后端冻结构建（975f537）
- [2026-11-19 22:38] docs: README 更新至 V4 阶段并更新应用图标（6569e94+75fd01b）
- [2026-11-19 23:14] docs: Win 压缩包发布流程规划与 exe 产物分类归档（报告012，仅规划）
- [2026-11-20 00:36] build(electron): Windows 安装包构建脚本与 NSIS 安装配置（862e9b1+89d546c）
- [2026-11-20 16:06] docs: 删除废弃 DEPLOYMENT.md 并移除 Electron 默认菜单栏（69b03e4）
- [2026-11-20 17:25] docs(agents): 新增 LOG.md 改动日志并回填里程碑，AGENTS.md 沉淀日志规则与桌面端研发细则
- [2026-11-20 18:20] fix(desktop): 文件夹选择改走 Electron 原生对话框 IPC，修复桌面端无 OS 对话框并重打包验证
- [2026-11-20 20:46] build(electron): 重建 NSIS 安装包（含对话框修复），静默安装/冒烟/卸载验证通过
- [2026-11-20 23:54] docs(settings): 新增设置模块存储迁移开发计划书（docs/sdd/plans）
- [2026-11-21 00:43] feat(settings): 设置模块存储位置自定义与安全迁移（迁移引擎/前端向导/桌面重启IPC，pytest 168 绿）
- [2026-11-23 00:06] style(settings): 设置页改宽屏双栏仪表盘布局（存储2/3+磁盘/关于右栏），消除全屏右侧空白
- [2026-11-23 00:37] build(desktop): 重建含设置模块的桌面端并产出 v1.1.0 NSIS 安装包（窗口自适应/F11/版本透传，新增构建说明文档）
- [2026-11-24 15:12] feat(data): 架次登记无人机型号更新——预设补充 DJI Agras T 系列现役机型，选"其他"支持自填型号并持久化加入预选列表（BatchNew.vue）
- [2026-11-24 15:16] feat(data): 无人机型号预设收敛为农田监测设备——移除 Agras T 系列，新增极飞 M2000/M500 2025 款巡田无人机（BatchNew.vue）
- [2026-11-24 15:45] feat(data): 地块信息升级为地理位置信息——Leaflet 地图选点弹窗 + DJI 图片 EXIF GPS 提取接口，架次存 WGS84 经纬度/海拔/来源（geo_api/GeoLocationEditor）
- [2026-11-25 13:33] chore(aoci): 安装 AOCI-CODE v0.2.0-rc4（校验和+attestation 双层校验通过）并完成 init/scan 初始化，生成认知资产骨架与基线，MCP 接入待 Trae 重启生效（aoci.exe @ %LOCALAPPDATA%\Programs\aoci）
- [2026-11-25 15:07] chore(aoci): MCP 接入后经 Guide 完成首次索引创作——117 条 Code Entry（3 并行批+末批）+ Root 概览，verify/check 对齐
- [2026-11-25 15:50] fix(desktop,data): 补齐 BatchDetail.vue 缺失的 DataSubTabs 导入；Electron 窗口最小尺寸由 1024×620 对齐规范 1100×760（小屏回退），前端已重新 build
- [2026-11-25 17:05] docs(versions): 新建 VERSIONS.md 版本管理与发版计划——旧 v1.0.0/v1.1.0 重置并入 V0.5.5 基线，追溯重构 V0.1.0~V0.5.6 版本历史；electron/package.json 与 backend/config.py 版本号同步改为 0.5.6
- [2026-11-25 17:22] docs(versions): 补全 VERSIONS.md 遗漏细节（V0.1.0 前端页面与 SPA 修复、V0.2.0 计数管线/字体图标、V0.4.0 项目更名与 Icon 统一、V0.5.2 品牌信息修正等），移除 PRD v7 智能助手相关版本规划
- [2026-11-25 18:05] docs(repo): 文档目录规范化收口——bug/update 报告、PRD、问答记录统一迁入 docs/，同步更新 bug_report/update_report SKILL 输出目录、AGENTS/README/VERSIONS 路径引用与目录树
- [2026-11-25 21:05] docs(qna): 新增 DJI Mavic 3M 图像 EXIF 扩展信息解析与农业巡检价值分析（docs/qna_record/）
- [2026-11-25 21:53] fix(process): 移除自定义目录输入源并加后端校验，删详情静态冗余字段，长路径缩略显示
- [2026-11-25 23:50] build(desktop): 版本升至 0.5.7 并产出 Electron 便携目录与 NSIS 安装包（CPU torch 载荷重建/冒烟与静默安装卸载验证，VERSIONS.md 同步）
