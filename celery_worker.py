# ./celery_worker.py
# 文件路径: ./celery_worker.py
import os
from app import create_app # 导入应用工厂

# 创建一个临时的 Flask 应用实例，主要是为了加载配置给 Celery
# 这个 flask_app 不会用来处理 Web 请求
flask_app = create_app(os.getenv('FLASK_CONFIG') or 'default')

# 获取在 create_app 中初始化并附加到 flask_app 的 Celery 实例
# celery_init_app 已经通过 flask_app.celery 将实例设置为了默认实例
celery = flask_app.celery

# 可在此导入任务模块，确保 Worker 能自动发现它们
# 例如: import app.tasks
# (如果 tasks.py 使用了 @shared_task, Celery 通常能自动发现)
