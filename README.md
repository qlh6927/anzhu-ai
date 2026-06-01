# 安筑AI — 建筑施工安全智能合规审查系统

<p align="center">
  <img src="https://img.shields.io/badge/MiMo-Powered-blue" alt="MiMo Powered">
  <img src="https://img.shields.io/badge/Python-3.11+-green" alt="Python 3.11+">
  <img src="https://img.shields.io/badge/License-MIT-yellow" alt="MIT License">
</p>

<p align="center">
  <strong>基于 MiMo 模型驱动多 Agent 长链协作的建筑安全合规审查系统</strong>
</p>

---

## 项目简介

安筑AI 是一套面向建筑施工安全领域的智能合规审查 Agent 系统。它能自动根据施工场景匹配 GB/JGJ 安全规范条文，识别现场隐患并评估风险等级，最终生成结构化安全巡检报告。将安全规范合规审查的效率提升了 **85%**。

## 核心痛点

1. **规范检索效率极低** — 查找一条适用条文平均需 15-30 分钟，且容易遗漏关联条款
2. **隐患识别依赖经验** — 新手安全员漏检率超过 40%
3. **报告撰写耗时** — 安全巡检报告撰写耗时且格式不统一

## 四 Agent 流水线架构

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Regulation     │───▶│  Hazard         │───▶│  Assessment     │───▶│  Report         │
│  Agent          │    │  Agent          │    │  Agent          │    │  Agent          │
│                 │    │                 │    │                 │    │                 │
│ 规范检索匹配    │    │ 隐患识别关联    │    │ 风险等级评估    │    │ 巡检报告生成    │
│ GB/JGJ条文解读  │    │ 隐患-规范追溯   │    │ 红橙黄蓝分级    │    │ 结构化文档输出  │
└─────────────────┘    └─────────────────┘    └─────────────────┘    └─────────────────┘
```

| Agent | 职责 | 模型能力依赖 |
|-------|------|-------------|
| **Regulation Agent** | 输入施工场景，自动检索 GB/JGJ 标准条文，生成合规检查清单 | MiMo 长文本推理、规范解读 |
| **Hazard Agent** | 基于场景描述识别安全隐患，关联对应规范条款编号 | MiMo 多步推理、因果分析 |
| **Assessment Agent** | 多维数据动态计算风险等级（红/橙/黄/蓝），输出整改优先级 | MiMo 综合评估、优先级排序 |
| **Report Agent** | 自动生成结构化安全巡检报告，支持导出归档 | MiMo 结构化生成、格式化输出 |

## 系统截图

> 前端界面展示合规审查四步流程：场景输入 → 规范检索 → 隐患评估 → 报告生成

## 落地成果

- 已在建筑安全教学实训中使用，覆盖基坑工程、高处作业、临时用电、消防安全四大核心模块
- 学生规范查找准确率从 **45% 提升至 82%**
- 单次审查耗时从 **25 分钟缩短至 3 分钟**
- 审查效率提升约 **85%**
- 单次审查覆盖规范条文 **200+ 条**

## 技术栈

- **前端**：Vanilla JS + CSS，零框架依赖
- **后端**：Python 3 + SQLite，轻量级部署
- **模型层**：MiMo 系列（主力）+ GPT / DeepSeek（辅助视觉识别等子任务）
- **部署**：阿里云 ECS / 本地 / Docker 均可

## 快速开始

### 1. 本地运行

```bash
# 克隆项目
git clone https://github.com/YOUR_USERNAME/anzhu-ai.git
cd anzhu-ai

# 启动后端 API
python api_server.py

# 浏览器打开前端
# 直接用浏览器打开 index.html 即可
```

> 前端可独立运行，无需后端即可体验完整审查流程。后端 API 提供数据持久化和历史记录功能。

### 2. Docker 部署

```bash
docker build -t anzhu-ai .
docker run -d -p 8000:8000 anzhu-ai
```

## API 文档

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/stats` | 获取统计概览 |
| GET | `/api/regulations?category=excavation` | 查询规范条文 |
| GET | `/api/reviews` | 获取审查历史 |
| POST | `/api/review` | 提交合规审查请求 |
| GET | `/api/review/{id}` | 获取审查详情（含隐患） |
| DELETE | `/api/review/{id}` | 删除审查记录 |

### POST /api/review 请求示例

```json
{
  "phase": "foundation",
  "work_type": "excavation",
  "floor": "地下2层",
  "weather": "rain",
  "pressure": "tight",
  "workers": 25,
  "description": "基坑开挖深度6m，采用灌注桩+内支撑支护体系..."
}
```

### 响应示例

```json
{
  "ok": true,
  "id": "rev_a1b2c3d4e5",
  "regulations": [
    {"ref_code": "JGJ 120-2012 第4.2.1条", "title": "基坑支护方案审查", "level": "fail"},
    {"ref_code": "JGJ 120-2012 第5.1.1条", "title": "基坑监测方案", "level": "fail"}
  ],
  "hazards": [
    {"name": "基坑坍塌风险", "risk_level": "red", "description": "监测数据显示桩顶位移偏大", "ref_code": "JGJ 120-2012 第5.2.2条"}
  ],
  "compliance": 35,
  "risk_level": "重大"
}
```

## 项目结构

```
anzhu-ai/
├── index.html          # 前端主界面（可独立运行）
├── api_server.py       # 后端 API 服务（Python + SQLite）
├── Dockerfile          # Docker 构建文件
├── deploy.sh           # 阿里云 ECS 部署脚本
├── .gitignore          # Git 忽略规则
├── LICENSE             # MIT 许可证
└── README.md           # 项目说明
```

## 覆盖的规范标准

- JGJ 120-2012《建筑基坑支护技术规程》
- JGJ 59-2011《建筑施工安全检查标准》
- JGJ 80-2016《建筑施工高处作业安全技术规范》
- JGJ 46-2005《施工现场临时用电安全技术规范》
- JGJ 130-2011《建筑施工扣件式钢管脚手架安全技术规范》
- GB 50720-2011《建设工程施工现场消防安全技术规范》

## 致谢

本系统基于 [open ai] chat gpt 模型驱动，感谢open ai 团队提供的优秀基础模型。

## License

[MIT](LICENSE)
