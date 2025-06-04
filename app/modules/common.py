# D:\python_code\LocalAgent\config.py
import os
from dotenv import load_dotenv

load_dotenv()
basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'a-very-secret-dev-key-98765'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024

    REDIS_URL = os.environ.get('REDIS_URL') or 'redis://localhost:6379/0'

    CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL') or REDIS_URL
    CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND') or REDIS_URL
    CELERY_ACCEPT_CONTENT = ['json']
    CELERY_TASK_SERIALIZER = 'json'
    CELERY_RESULT_SERIALIZER = 'json'
    CELERY_TIMEZONE = 'Asia/Shanghai'
    CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True

    PROMPT_FILE_PATH = os.path.join('templates', 'prompt.txt')
    MAX_CONVERSATION_HISTORY_TURNS = 10
    CONTEXT_FILE = "context.txt"

    LOCAL_API_URL = os.environ.get('LOCAL_API_URL', 'http://localhost:11434/api/chat')
    LOCAL_API_KEY = os.environ.get("LOCAL_API_KEY", None)
    LOCAL_MODELS = ["qwen2:latest", "llama3"]

    DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY")
    DEEPSEEK_API_URL = os.environ.get('DEEPSEEK_API_URL', "https://api.deepseek.com/v1/chat/completions")
    DEEPSEEK_MODELS = ["deepseek-chat", "deepseek-coder"]

    AVAILABLE_PROVIDERS = {
        "Local": {
            "url": LOCAL_API_URL,
            "models": LOCAL_MODELS,
            "key_required": bool(LOCAL_API_KEY),
            "key_configured": bool(LOCAL_API_KEY)
        },
        "DeepSeek": {
            "url": DEEPSEEK_API_URL,
            "models": DEEPSEEK_MODELS,
            "key_required": True,
            "key_configured": bool(DEEPSEEK_API_KEY)
        }
    }

    _default_provider = "Local" if AVAILABLE_PROVIDERS.get("Local", {}).get("models") else ""
    if not _default_provider:
        for p, c in AVAILABLE_PROVIDERS.items():
            if c.get("models"):
                _default_provider = p
                break
    DEFAULT_PROVIDER = _default_provider or (list(AVAILABLE_PROVIDERS.keys())[0] if AVAILABLE_PROVIDERS else "None")
    DEFAULT_MODEL = AVAILABLE_PROVIDERS.get(DEFAULT_PROVIDER, {}).get("models", [None])[0]

    LLM_REQUEST_TIMEOUT = 120

    CRISIS_HOTLINE_INFO = os.environ.get("CRISIS_HOTLINE_INFO", """
- 希望24热线：400-161-9995
- 北京心理危机研究与干预中心：010-82951332
- 上海市精神卫生中心: 021-12320-5
""")

    _summary_provider = None
    _summary_model = None
    if AVAILABLE_PROVIDERS.get("DeepSeek", {}).get("key_configured") and "deepseek-chat" in AVAILABLE_PROVIDERS.get("DeepSeek", {}).get("models", []):
        _summary_provider = "DeepSeek"
        _summary_model = "deepseek-chat"
    elif AVAILABLE_PROVIDERS.get(DEFAULT_PROVIDER, {}).get("models"):
        _summary_provider = DEFAULT_PROVIDER
        _summary_model = DEFAULT_MODEL

    SUMMARY_PROVIDER = _summary_provider
    SUMMARY_MODEL = _summary_model
    SUMMARY_PROMPT = os.environ.get("SUMMARY_PROMPT", "请根据对话记录，生成一段简洁的总结报告，包含用户议题、情绪状态、关键点和后续建议。\n对话记录如下：\n{conversation_history}")

    MAX_CONVERSATION_HISTORY = MAX_CONVERSATION_HISTORY_TURNS * 2

    @staticmethod
    def init_app(app):
        pass

class DevelopmentConfig(Config):
    DEBUG = True

class ProductionConfig(Config):
    DEBUG = False
    SECRET_KEY = os.environ.get('SECRET_KEY')
    if not SECRET_KEY:
        raise ValueError("生产环境未设置 SECRET_KEY 环境变量！")

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}