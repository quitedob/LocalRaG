```markdown
# 智能对话助手 (LocalAgent)

**LocalAgent** 是一个基于 `Flask`、`Celery` 和 `Redis` 构建的模块化、可扩展的智能对话Web应用。它旨在提供一个灵活的框架，用于处理和响应用户输入，同时支持多种大型语言模型（LLM）提供者（如本地部署的Ollama和远程的DeepSeek API）。

该项目通过将对话处理流程分解为一系列独立的模块（安全检查、预处理、情感分析、回复生成等），实现了高度的解耦和可维护性。利用 `Celery` 进行异步任务处理，确保了长时间运行的LLM请求不会阻塞用户界面，从而提供了流畅的交互体验。

---

## ✨ 功能特性

- **模块化对话流水线**：
    - **安全模块**：优先检测并响应潜在的危机言论，提供安全警示。
    - **预处理模块**：清理、分词用户输入，为后续分析做准备。
    - **分析模块**：包括情感分析和用户意图分析，识别用户的情绪、意图和潜在的认知扭曲。
    - **响应生成模块**：调用选择的LLM（本地或云端）生成回复。
    - **响应优化模块**：解析并清理LLM的原始输出，提取“思考链”（Chain of Thought）等元数据。
- **异步处理**：
    - 使用 `Celery` 和 `Redis` 将耗时的对话处理任务放入后台队列，主应用立即响应。
    - 前端通过轮询机制获取任务结果，实现了非阻塞的实时更新体验。
- **多模型支持**：
    - 可通过配置文件轻松切换和添加不同的LLM提供者（例如 `Local`、`DeepSeek`）。
    - 支持在会话级别临时提供API密钥，方便测试和共享。
- **丰富的前端交互**：
    - 使用原生 `JavaScript` 构建的单页应用，动态更新聊天记录和分析面板。
    - 包含设置模态框，用于切换模型、配置API密钥和上传文件。
    - 支持对话总结、清空聊天记录等实用功能。
    - 界面包含深色/浅色模式切换。
- **详细的配置与状态展示**：
    - 可通过 `.env` 文件和 `config.py` 灵活配置应用参数、API密钥和模型列表。
    - 前端界面提供一个可展开的“对话处理分析”面板，展示每个模块的输出和最终的对话状态，便于调试和理解。
- **上下文管理**：
    - 利用 `Redis` 高效地存储和管理每个用户的会话历史。
    - 自动处理历史记录的截断，以符合模型的上下文长度限制。

---

## 🛠️ 技术栈

- **后端**：`Python`, `Flask`, `Celery`
- **数据存储 & 消息队列**：`Redis`
- **前端**：`HTML`, `CSS`, `JavaScript` (无框架)
- **Python库**：`requests`, `python-dotenv`, `jieba` 等

---

## 📂 项目结构

```
LocalAgent/
│
├── app/                      # Flask应用核心目录
│   ├── api/                  # API蓝图 (处理Ajax请求)
│   │   ├── __init__.py
│   │   └── routes.py
│   ├── main/                 # 主功能蓝图 (处理Web页面)
│   │   ├── __init__.py
│   │   └── routes.py
│   ├── modules/              # 对话处理流水线的核心模块
│   │   ├── common.py
│   │   ├── context_manager_module.py
│   │   ├── dialogue_pipeline.py
│   │   ├── emotion_analyzer_module.py
│   │   ├── preprocessor_module.py
│   │   ├── response_generator_module.py
│   │   ├── response_optimizer_module.py
│   │   ├── safety_module.py
│   │   ├── summary_module.py
│   │   └── user_analyzer_module.py
│   ├── static/               # 静态文件 (CSS, JS, 图像)
│   ├── templates/            # HTML模板
│   │   └── index.html
│   ├── __init__.py           # 应用工厂 (create_app)
│   ├── tasks.py              # Celery异步任务定义
│   └── utils.py              # 通用工具函数
│
├── .env                      # 环境变量配置文件 (本地)
├── .env.example              # 环境变量示例文件
├── celery_worker.py          # Celery Worker启动脚本
├── config.py                 # 应用配置文件
├── readme.md                 # 项目说明文件
├── requirements.txt          # Python依赖列表
└── run.py                    # 应用入口脚本
```

---

## 🚀 快速开始

### 1. 环境准备

- 安装 [Python 3.10+](https://www.python.org/)
- 安装并运行 [Redis](https://redis.io/docs/getting-started/installation/)

### 2. 克隆与安装依赖

```bash
# 克隆仓库
git clone <your-repository-url>
cd LocalAgent

# (推荐) 创建并激活虚拟环境
python -m venv venv
source venv/bin/activate  # on Linux/macOS
# venv\Scripts\activate   # on Windows

# 安装依赖
pip install -r requirements.txt
```

### 3. 配置

复制示例配置文件，并根据您的环境填写。

```bash
cp .env.example .env
```

编辑 `.env` 文件，至少配置 `REDIS_URL`。如果需要使用 `DeepSeek`，请填入 `DEEPSEEK_API_KEY`。

```env
# .env

# Flask配置
FLASK_CONFIG='development' # 'production' 或 'development'
SECRET_KEY='your-very-secret-key-for-flask-sessions'

# Redis 配置 (用于Celery和会话存储)
REDIS_URL='redis://localhost:6379/0'

# LLM 提供者配置
# DeepSeek API (如果需要)
DEEPSEEK_API_KEY='YOUR_DEEPSEEK_API_KEY_HERE'

# 本地模型 API (例如Ollama)
LOCAL_API_URL='http://localhost:11434/api/chat'
```

### 4. 运行服务

您需要打开 **3个** 终端窗口：

- **终端 1：启动 Redis 服务**（如果尚未在后台运行）
  ```bash
  redis-server
  ```

- **终端 2：启动 Celery Worker**
  ```bash
  celery -A celery_worker.celery worker --loglevel=info
  ```

- **终端 3：启动 Flask Web 应用**
  ```bash
  python run.py
  ```

### 5. 访问应用

打开浏览器并访问 `http://127.0.0.1:5001`。

---

## ⚙️ 配置说明

- **`config.py`**: 定义了不同环境（开发、生产）的配置类。
    - `AVAILABLE_PROVIDERS`: 在此注册所有可用的LLM提供者、它们的API URL、模型列表以及是否需要API密钥。
    - `DEFAULT_PROVIDER` / `DEFAULT_MODEL`: 设置默认加载的模型。
    - `SUMMARY_PROVIDER` / `SUMMARY_MODEL`: 配置用于生成对话总结的特定模型。
- **`.env`**: 存储敏感信息和环境特定的变量，如API密钥、数据库URL等。

---
## 📄 `requirements.txt`
```
# ./requirements.txt
# 核心框架
flask
redis
celery
python-dotenv

# 网络请求
requests

# 中文分词
jieba
```
```