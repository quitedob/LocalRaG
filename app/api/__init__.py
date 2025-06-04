# D:\python_code\LocalAgent\app\api\__init__.py
# 文件作用：定义 API 蓝图 (使用修正后的名称 api_v1) 并导入路由

from flask import Blueprint

# 创建名为 'api_v1' 的蓝图对象，并直接定义 URL 前缀
# 使用 'api_v1' 避免了潜在的名称冲突
api_v1 = Blueprint('api_v1', __name__, url_prefix='/api')

# 导入该蓝图下的路由定义 (确保在蓝图对象创建之后)
# 这会执行 routes.py，将其中的路由关联到 api_v1 对象上
from . import routes