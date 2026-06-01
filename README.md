# 安筑AI — 建筑施工安全智能合规审查系统

<p align="center">
  <img src="https://img.shields.io/badge/OpenAI-Powered-111827" alt="OpenAI Powered">
  <img src="https://img.shields.io/badge/Python-3.11+-green" alt="Python 3.11+">
  <img src="https://img.shields.io/badge/License-MIT-yellow" alt="MIT License">
</p>

<p align="center">
  <strong>基于 OpenAI 模型驱动多 Agent 长链协作的建筑安全合规审查系统</strong>
</p>

---

## 项目简介

安筑AI 是一套面向建筑施工安全领域的智能合规审查 Agent 系统。系统根据施工场景匹配 GB/JGJ 安全规范条文，识别现场隐患并评估风险等级，最终生成结构化安全巡检报告。

项目支持两种运行方式：

- **OpenAI 智能审查模式**：配置 `OPENAI_API_KEY` 后，后端会调用 OpenAI Responses API 生成隐患识别、风险评估和报告内容。
- **本地规则回退模式**：未配置 API Key 或网络不可用时，系统会自动使用内置规范库和规则逻辑完成演示流程。

## 核心痛点

1. **规范检索效率低** — 查找适用条文耗时，且容易遗漏关联条款。
2. **隐患识别依赖经验** — 新手安全员容易漏检高风险问题。
3. **报告撰写耗时** — 安全巡检报告需要统一结构、规范依据和整改建议。

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

| Agent | 职责 | OpenAI 能力依赖 |
|-------|------|----------------|
| **Regulation Agent** | 输入施工场景，检索 GB/JGJ 标准条文，生成合规检查清单 | 长上下文理解、规范条文归纳 |
| **Hazard Agent** | 基于场景描述识别安全隐患，关联对应规范条款编号 | 多步推理、风险因果分析 |
| **Assessment Agent** | 多维数据动态计算风险等级（红/橙/黄/蓝），输出整改优先级 | 综合评估、优先级排序 |
| **Report Agent** | 自动生成结构化安全巡检报告，支持导出归档 | 结构化生成、专业中文表达 |

## 技术栈

- **前端**：Vanilla JS + CSS，零框架依赖。
- **后端**：Python 3 + SQLite，轻量级部署。
- **模型层**：OpenAI Responses API，默认模型为 `gpt-5-mini`，可通过 `OPENAI_MODEL` 修改。
- **部署**：本地、Docker、云服务器均可。

## 快速开始

### 1. 本地运行

```bash
git clone https://github.com/YOUR_USERNAME/anzhu-ai.git
cd anzhu-ai

# 可选：启用 OpenAI 智能审查
export OPENAI_API_KEY="sk-..."
export OPENAI_MODEL="gpt-5-mini"

# 启动后端 API
python api_server.py
```

然后打开 `index.html`。如果后端运行在默认端口，前端会请求 `http://localhost:8000/api/review`；如果后端未启动，前端会自动使用本地规则演示。

Windows PowerShell 示例：

```powershell
$env:OPENAI_API_KEY="sk-..."
$env:OPENAI_MODEL="gpt-5-mini"
python api_server.py
```

### 2. Docker 部署

```bash
docker build -t anzhu-ai .
docker run -d -p 8000:8000 \
  -e OPENAI_API_KEY="sk-..." \
  -e OPENAI_MODEL="gpt-5-mini" \
  anzhu-ai
```

## OpenAI API 配置

后端通过环境变量读取 OpenAI 配置：

| 变量 | 必填 | 默认值 | 说明 |
|------|------|--------|------|
| `OPENAI_API_KEY` | 否 | 空 | 配置后启用 OpenAI 智能审查；不配置则使用本地规则 |
| `OPENAI_MODEL` | 否 | `gpt-5-mini` | OpenAI 模型名称 |
| `OPENAI_API_URL` | 否 | `https://api.openai.com/v1/responses` | Responses API 地址 |

后端请求 OpenAI Responses API 的核心逻辑在 `api_server.py` 中，会要求模型只返回 JSON：

```json
{
  "hazards": [
    {
      "name": "基坑坍塌风险",
      "risk_level": "red",
      "description": "监测数据显示桩顶位移偏大，雨天施工增加边坡失稳风险。",
      "ref_code": "JGJ 120-2012 第5.2.2条"
    }
  ],
  "compliance": 65,
  "risk_level": "重大",
  "report": "建筑施工安全合规审查报告..."
}
```

## API 文档

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/stats` | 获取统计概览 |
| GET | `/api/regulations?category=excavation` | 查询规范条文 |
| GET | `/api/reviews` | 获取审查历史 |
| POST | `/api/review` | 提交合规审查请求，优先使用 OpenAI，失败时回退本地规则 |
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
    {
      "ref_code": "JGJ 120-2012 第4.2.1条",
      "title": "基坑支护方案审查",
      "level": "fail"
    }
  ],
  "hazards": [
    {
      "name": "基坑支护方案审查问题",
      "risk_level": "red",
      "description": "开挖深度超过3m的基坑，必须由具有相应资质的设计单位进行支护设计",
      "ref_code": "JGJ 120-2012 第4.2.1条"
    }
  ],
  "compliance": 65,
  "risk_level": "重大",
  "report": "建筑施工安全合规审查报告...",
  "provider": "openai",
  "model": "gpt-5-mini"
}
```

## 项目结构

```
anzhu-ai/
├── index.html          # 前端主界面，可独立运行
├── api_server.py       # 后端 API 服务，OpenAI + SQLite + 本地规则回退
├── Dockerfile          # Docker 构建文件
├── deploy.sh           # 云服务器部署脚本
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

本系统基于 OpenAI 模型能力构建，用于探索建筑施工安全合规审查中的智能 Agent 协作流程。

## License

[MIT](LICENSE)
