# ./app/main/__init__.py
# 文件路径: ./app/main/__init__.py
from flask import Blueprint

# 创建主蓝图实例
main = Blueprint('main', __name__,
                 template_folder='../templates', # 指定模板目录
                 static_folder='../static')      # 指定静态目录

# 导入蓝图的路由 (必须在蓝图创建后导入)
from . import routes