<div align="center">

# 🌌 CausalMind | 观因知行

**证据优先的复杂决策推演引擎** *An evidence-first inference engine for complex decision analysis.*

<a href="https://github.com/your-username/causal-mind-backend">
  <img src="./banner.svg" alt="CausalMind (观因知行) - Dynamic Panoramic Inference Map" width="100%" />
</a>

<br/>

<a href="https://github.com/your-username/causal-mind-backend">
  <img src="https://readme-typing-svg.demolab.com?font=Fira+Code&weight=500&size=16&duration=3000&pause=1000&color=5BC0BE&center=true&vCenter=true&width=800&lines=From+user+dilemma+to+search+strategy;From+raw+evidence+to+auditable+facts;From+causal+sandbox+to+worldline+simulation;From+analysis+to+decision+whitepaper" alt="Typing SVG" />
</a>

[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.116-009688.svg?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Huey](https://img.shields.io/badge/Huey-Async_Worker-4B8BBE.svg?style=flat-square)](https://huey.readthedocs.io/)
[![SQLite](https://img.shields.io/badge/SQLite-Local_First-003B57.svg?style=flat-square&logo=sqlite&logoColor=white)](https://www.sqlite.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg?style=flat-square)](LICENSE)

</div>

<br/>

> **"CausalMind (观因知行)" 不是传统的“提问-回答”套壳接口，而是一条围绕复杂决策建立的完整分析链路。** > 
> 它通过采集外部信息、提炼事实、审查偏差、构建因果沙盘、注入用户真实变量，最终生成推演世界线与行动白皮书。适用于职业转型、高风险投入判断、路径选择及机会成本分析等高不确定性场景。

## ✨ Why It Exists | 为什么做这个项目

很多现有的 AI 决策工具往往“过早得出结论”（Collapse too early）：
- ❌ 用户只得到一个空泛的结论，**缺乏可追溯的证据链**。
- ❌ 事实、情绪、偏见和模型幻觉**混杂在一起**。
- ❌ 缺乏**用户变量注入**，推演只能停留在“正确的废话”。
- ❌ 没有可复查的中间层，前端很难将其包装成完整的商业产品。

**CausalMind 的破局点：** 将推演过程进行“解构”。让每一层数据（证据、事实、因果节点、世界线）都可独立存储、可追踪、可复查，为前端提供构建真正专业级产品的底层支撑。

## 🔄 End-to-End Flow | 全链路流程

```mermaid
flowchart LR
    A[Create Case] --> B[Search Strategy]
    B --> C[Collection Task]
    C --> D[Evidence]
    D --> E[Facts]
    E --> F[Audit Elements]
    F --> G[Causal Sandbox]
    G --> H[Context Injection]
    H --> I[Worldline]
    I --> J[Whitepaper]
    
    style A fill:#0F766E,stroke:#fff,stroke-width:2px,color:#fff
    style J fill:#C2410C,stroke:#fff,stroke-width:2px,color:#fff
````

## 🎯 Core Capabilities | 核心能力

| Module | 中文说明 | English |
| :--- | :--- | :--- |
| **Collection** | 根据背景生成策略，触发异步采集任务 | Run async collection with progress tracking |
| **Fact Audit** | 从冗余证据中提炼“可审阅”的脱水事实 | Extract auditable facts from evidence |
| **Sandbox** | 聚合事实生成因果图，执行干预推演 | Build causal graphs and run interventions |
| **Context** | 注入用户真实的资产、技能与约束条件 | Inject verified user state and constraints |
| **Worldline** | 推演多条可能的未来演化路径 | Simulate possible future paths |
| **Whitepaper** | 输出包含主要矛盾与风险对冲的行动建议 | Produce conflict, risk, and action summaries |

## 🏗️ Architecture | 架构视图

```mermaid
flowchart TB
    FE[Frontend / Client] -->|X-Causal-Config| API[FastAPI Router]
    API --> DB[(SQLite)]
    API --> H[Huey Queue]
    H --> DB
    H --> MC[MediaCrawler]
    H --> LLM[LLM Providers]
    API --> LLM
    
    subgraph Storage [Data Artifacts]
        META[data/crawler/run_meta.json]
    end
    
    H -.-> META
```

## 📁 Repo Layout | 目录结构

```text
./
├── app/
│   ├── api/            # 路由与请求级配置解析 (Routes & Config Parsing)
│   ├── core/           # 核心配置、Prompt与统一响应格式 (Core Setup)
│   ├── db/             # 数据库初始化 (Database Setup)
│   ├── models/         # SQLAlchemy 实体模型 (Entities)
│   ├── schemas/        # Pydantic 数据传输对象 (DTOs)
│   ├── services/       # 爬虫/大模型/推演核心逻辑 (Services)
│   └── workers/        # Huey 队列与后台任务 (Async Jobs)
├── data/               # SQLite / Huey / 爬虫运行产物 (Runtime Artifacts)
├── tests/              # 路由级全链路闭环测试 (Flow Tests)
├── debug_llm.py
├── patch_db.py
└── requirements.txt
```

## 🚀 Quick Start | 快速开始

### 1\. 基础安装 (Install Dependencies)

```bash
python3 -m pip install -r requirements.txt
```

### 2\. 准备采集器 (Prepare MediaCrawler) *[可选]*

如果你希望启用真实平台（如小红书、知乎）采集，需要本地克隆 `MediaCrawler` 并配置路径。若仅做接口测试，可跳过此步并参考下文的「演示模式」。

```bash
export CRAWLER_REPO_PATH=/path/to/MediaCrawler
cd $CRAWLER_REPO_PATH && python3 -m pip install -r requirements.txt
```

### 3\. 配置运行环境 (Configure Env)

```bash
export CRAWLER_REPO_PATH=/path/to/MediaCrawler
export CRAWLER_PLATFORMS=xhs,zhihu
export CRAWLER_LOGIN_TYPE=qrcode
export CRAWLER_HEADLESS=false
export CRAWLER_ENABLED=true  # 设置为 false 则进入无爬虫演示模式
```

### 4\. 启动服务 (Start Services)

启动主 API 服务：

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

在另一个终端启动 Huey 异步任务消费者：

```bash
huey_consumer app.workers.worker.huey
```

### 5\. 健康检查 (Health Check)

```bash
curl [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)
# 预期输出: {"status": "ok"}
```

## 🎭 Demo Mode | 本地演示模式

如果你只想先联调接口，而不接真实爬虫，可以关闭采集开关：

```bash
export CRAWLER_ENABLED=false
```

在此模式下，你依然可以跑通大部分前端联调流程（如创建案例、生成基础事实占位、生成启发式沙盘结构等）。真实的数据生成仍依赖于请求头传入的模型配置。

## 🎛️ 动态模型注入 (Provider Injection)

CausalMind 放弃了服务端静态写死模型 Key 的做法。通过在请求头中传入 `X-Causal-Config`（或原 `X-Wolong-Config`，Base64 编码的 JSON），前端可以实现：

  - 单次请求无缝切换 OpenAI/Anthropic/本地大模型。
  - 按不同决策案例分配抓取预算和平台。
  - 精细控制不同推演阶段（如 `audit`, `sandbox`, `worldline`）使用的底层模型。

\<details\>
\<summary\>\<b\>点击查看 Config JSON 结构示例\</b\>\</summary\>

```json
{
  "providers": [
    {
      "id": "openai-main",
      "name": "OpenAI",
      "baseUrl": "[https://api.openai.com/v1](https://api.openai.com/v1)",
      "apiKey": "sk-***",
      "defaultModel": "gpt-4o-mini"
    }
  ],
  "stageAssignments": {
    "collection": "openai-main",
    "audit": "openai-main",
    "sandbox": "openai-main",
    "worldline": "openai-main"
  },
  "crawlerPlatforms": [
    {
      "name": "xhs",
      "max_notes": 30,
      "get_comments": true,
      "max_comments_count_singlenotes": 10
    }
  ],
  "extraction": {
    "chunk_size": 12,
    "chunk_overlap": 0,
    "max_chunk_tokens": 0
  }
}
```

\</details\>

## 🗺️ API Map | 接口地图

### Base & Case | 基础与案例生命周期

| Method | Path | Description |
| :--- | :--- | :--- |
| `GET` | `/health` | Health check |
| `POST` | `/cases` | Create a case |
| `GET` | `/cases/history` | List historical cases |
| `DELETE` | `/cases/{case_id}` | Delete a case and its artifacts |

### Collection & Facts | 采集与事实层

| Method | Path | Description |
| :--- | :--- | :--- |
| `POST` | `/cases/{id}/start-collection` | Start background collection |
| `GET` | `/cases/{id}/collection-status` | Query collection and extraction status |
| `GET` | `/cases/{id}/facts` | Get fact cards |
| `GET` | `/cases/{id}/audit-elements` | Get audit element cards |
| `GET` | `/cases/{id}/evidences` | Get evidence items |

### Causal Sandbox & Worldline | 沙盘、世界线与白皮书

| Method | Path | Description |
| :--- | :--- | :--- |
| `GET` | `/cases/{id}/sandbox` | Get or generate sandbox graph |
| `POST` | `/cases/{id}/sandbox/intervene` | Apply intervention and simulate effects |
| `PUT` | `/cases/{id}/context` | Inject verified user context |
| `GET` | `/cases/{id}/worldline` | Get or generate worldline |
| `GET` | `/cases/{id}/whitepaper` | Get or generate whitepaper |

## 💾 Data Artifacts | 数据落地

运行后主要会产生以下文件：

  - `data/app.db`：业务数据库
  - `data/huey.db`：任务数据库
  - `data/crawler/<case_id>/run_meta.json`：**核心元数据文件**。包含平台与关键词请求参数、采集步进统计、抓取漏斗数据，以及各推演阶段的模型元信息，是前端展示执行进度的重要数据源。

## 🧪 Testing & Frontend | 测试与前端联调

**运行测试：**

```bash
pytest -q tests/test_cycle_routes.py
```

当前测试重点是路由级链路闭环，覆盖案例创建、策略生成、采集流转、事实读取及沙盘干预等。

**前端联调注意：**

  - 确保 Axios `baseURL` 指向 `http://localhost:8000`。
  - 关闭本地 mock 拦截，避免与真实接口冲突。

-----

\<div align="center"\>
\<p\>\<i\>CausalMind Backend is designed not to answer too early, but to turn complex decisions into a traceable, reviewable, and product-ready inference process.\</i\>\</p\>
\</div\>
```
