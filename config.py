# ./config.py
# 文件路径: ./config.py
import os
from dotenv import load_dotenv

load_dotenv() # 加载环境变量
basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    # 基础配置类
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'a-very-secret-dev-key-98765' # Flask密钥
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024 # 上传大小限制

    # --- Redis 配置 ---
    REDIS_URL = os.environ.get('REDIS_URL') or 'redis://localhost:6379/0' # Redis地址

    # --- Celery 配置 ---
    CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL') or REDIS_URL # Broker地址
    CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND') or REDIS_URL # 结果后端地址
    CELERY_ACCEPT_CONTENT = ['json'] # 接受内容类型
    CELERY_TASK_SERIALIZER = 'json' # 任务序列化
    CELERY_RESULT_SERIALIZER = 'json' # 结果序列化
    CELERY_TIMEZONE = 'Asia/Shanghai' # 时区设置
    CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True # 启动时重试连接

    # --- 应用特定配置 ---
    PROMPT_FILE_PATH = os.path.join('templates', 'prompt.txt') # Prompt路径 (相对app)
    MAX_CONVERSATION_HISTORY_TURNS = 10 # 最大历史轮数 (user+ai算2轮)

    # --- LLM API 配置 ---
    LOCAL_API_URL = os.environ.get('LOCAL_API_URL', 'http://localhost:11434/api/chat')
    LOCAL_API_KEY = os.environ.get("LOCAL_API_KEY", None)
    LOCAL_MODELS = ["qwen2:latest", "llama3"] # 本地模型列表

    DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY") # 直接从env获取
    # 移除硬编码的默认值: "YOUR_DEEPSEEK_API_KEY_HERE"
    DEEPSEEK_API_URL = os.environ.get('DEEPSEEK_API_URL', "https://api.deepseek.com/v1/chat/completions")
    DEEPSEEK_MODELS = ["deepseek-chat", "deepseek-coder"] # DeepSeek模型

    # 统一管理 Provider
    AVAILABLE_PROVIDERS = {
        "Local": {
            "url": LOCAL_API_URL,
            "models": LOCAL_MODELS,
            "key_required": bool(LOCAL_API_KEY), # 本地Key是否必须
            "key_configured": bool(LOCAL_API_KEY) # 本地Key是否已配
        },
        "DeepSeek": {
            "url": DEEPSEEK_API_URL,
            "models": DEEPSEEK_MODELS,
            "key_required": True, # DeepSeek需要Key
            "key_configured": bool(DEEPSEEK_API_KEY) # 只要环境变量有值就算配置
        }
        # 可添加更多 Provider
    }

    # 确定默认 Provider 和 Model (简化逻辑)
    _default_provider = "Local" if AVAILABLE_PROVIDERS.get("Local", {}).get("models") else ""
    if not _default_provider:
        for p, c in AVAILABLE_PROVIDERS.items():
            if c.get("models"): _default_provider = p; break
    DEFAULT_PROVIDER = _default_provider or (list(AVAILABLE_PROVIDERS.keys())[0] if AVAILABLE_PROVIDERS else "None")
    DEFAULT_MODEL = AVAILABLE_PROVIDERS.get(DEFAULT_PROVIDER, {}).get("models", [None])[0]

    # LLM 请求超时时间（秒）
    LLM_REQUEST_TIMEOUT = 120 # 请求超时

    # 危机干预信息
    CRISIS_HOTLINE_INFO = os.environ.get("CRISIS_HOTLINE_INFO", """
- 希望24热线：400-161-9995
- 北京心理危机研究与干预中心：010-82951332
- 上海市精神卫生中心: 021-12320-5
""") # 危机热线信息 (优先环境变量)

    # 对话总结设置 (简化逻辑)
    _summary_provider = None
    _summary_model = None
    if AVAILABLE_PROVIDERS.get("DeepSeek", {}).get("key_configured") and "deepseek-chat" in AVAILABLE_PROVIDERS.get("DeepSeek", {}).get("models", []):
        _summary_provider = "DeepSeek"; _summary_model = "deepseek-chat"
    elif AVAILABLE_PROVIDERS.get(DEFAULT_PROVIDER, {}).get("models"):
         _summary_provider = DEFAULT_PROVIDER; _summary_model = DEFAULT_MODEL

    SUMMARY_PROVIDER = _summary_provider # 总结用Provider
    SUMMARY_MODEL = _summary_model # 总结用Model
    SUMMARY_PROMPT = os.environ.get("SUMMARY_PROMPT", "请根据对话记录，生成一段简洁的总结报告，包含用户议题、情绪状态、关键点和后续建议。\n对话记录如下：\n{conversation_history}") # 总结提示 (优先环境变量)

    @staticmethod
    def init_app(app):
        # 应用初始化钩子
        pass

class DevelopmentConfig(Config):
    # 开发环境配置
    DEBUG = True

class ProductionConfig(Config):
    # 生产环境配置
    DEBUG = False
    # 生产环境强制从环境变量获取密钥
    SECRET_KEY = os.environ.get('SECRET_KEY')
    if not SECRET_KEY:
        raise ValueError("生产环境未设置 SECRET_KEY 环境变量！")

# 配置名称映射
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig # 默认开发配置
}