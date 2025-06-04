# D:\python_code\LocalAgent\app\__init__.py
# 文件作用：Flask 应用工厂，初始化应用、扩展和注册蓝图

import os
from flask import Flask
from redis import Redis
from celery import Celery, Task
from config import config # 导入应用配置

# 全局变量，存储 Celery 和 Redis 实例
celery_app = None
redis_client = None

# --- 计算项目根目录 ---
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
# print(f"Calculated project root: {project_root}") # 清理调试打印

# 定义 Celery 任务类，使其能在 Flask 应用上下文中运行
def celery_init_app(app: Flask) -> Celery:
    class FlaskTask(Task):
        def __call__(self, *args: object, **kwargs: object) -> object:
            with app.app_context():
                return self.run(*args, **kwargs)
    _celery_app = Celery(app.name, task_cls=FlaskTask)
    _celery_app.config_from_object(app.config["CELERY"])
    _celery_app.set_default()
    return _celery_app

# Flask 应用工厂函数
def create_app(config_name=None) -> Flask:
    global celery_app, redis_client
    if config_name is None:
        config_name = os.environ.get('FLASK_CONFIG', 'default')

    # 创建 Flask 应用实例，设置根路径
    app = Flask(__name__,
                instance_relative_config=True,
                root_path=project_root)

    # 加载配置
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)

    # 初始化 Redis
    try:
        redis_client = Redis.from_url(app.config['REDIS_URL'], decode_responses=True)
        redis_client.ping()
        app.redis_client = redis_client
        print("Redis 连接成功。")
    except Exception as e:
        print(f"错误：无法连接到 Redis {app.config.get('REDIS_URL', 'N/A')}: {e}")
        redis_client = None
        app.redis_client = None

    # 初始化 Celery
    try:
        app.config.update(CELERY=dict(
            broker_url=app.config["CELERY_BROKER_URL"],
            result_backend=app.config["CELERY_RESULT_BACKEND"],
            broker_connection_retry_on_startup=app.config.get("CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP", True)
        ))
        celery_app = celery_init_app(app)
        app.celery = celery_app
        print("Celery 初始化完成。")
    except Exception as e:
        print(f"Celery 初始化失败: {e}")
        celery_app = None
        app.celery = None

    # --- 蓝图注册 ---
    # 注册 main 蓝图
    # print("--- Registering main blueprint ---") # 清理调试打印
    from .main import main as main_blueprint
    app.register_blueprint(main_blueprint)
    # print("--- Main blueprint registered ---") # 清理调试打印

    # 注册 api 蓝图 (使用新名称)
    # print("--- Importing api_v1 blueprint ---") # 清理调试打印
    try:
        # !! 修改：导入并注册新的蓝图变量名 api_v1 !!
        from .api import api_v1 as api_blueprint
        # print("--- api_v1 blueprint imported successfully ---") # 清理调试打印
        # print("--- Registering api_v1 blueprint ---") # 清理调试打印
        # !! 修改：注册时不指定 url_prefix !!
        app.register_blueprint(api_blueprint)
        # print("--- api_v1 blueprint registered (call completed) ---") # 清理调试打印
    except ImportError as e_imp:
        print(f"--- FAILED to import api_v1 blueprint: {e_imp} ---")
    except Exception as e_reg:
        print(f"--- FAILED during api_v1 blueprint registration: {e_reg} ---")

    print(f"Flask 应用 '{app.name}' 创建成功，使用配置: {config_name}, 根路径: {app.root_path}")
    return app