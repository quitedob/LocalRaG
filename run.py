# ./run.py
# 文件作用：应用程序入口点，创建并运行 Flask 应用

import os
from dotenv import load_dotenv

# 加载 .env 文件中的环境变量
load_dotenv()

# 检查并创建模板目录和默认 prompt 文件 (如果不存在)
templates_dir = os.path.join(os.path.dirname(__file__), 'templates') # 指向项目根目录的 templates
if not os.path.exists(templates_dir):
    os.makedirs(templates_dir)
    print(f"创建目录: {templates_dir}")

prompt_file = os.path.join(templates_dir, 'prompt.txt')
if not os.path.exists(prompt_file):
    try:
        with open(prompt_file, 'w', encoding='utf-8') as f:
            # 写入默认的提示词内容
            f.write("你是一个AI心理咨询助手。\n# 核心限制与边界\n...\n# 对用户的指示\n...")
        print(f"创建默认 prompt 文件: {prompt_file}")
    except OSError as e:
        print(f"创建默认 prompt 文件失败: {e}")


# 导入应用工厂函数
from app import create_app

# 创建 Flask 应用实例，从环境变量读取配置名称，默认为 'default'
flask_app = create_app(os.environ.get('FLASK_CONFIG', 'default'))

# !! 移除调试打印语句 !!
# with flask_app.app_context():
#     print("\n--- 已注册的 URL 规则 ---")
#     print(flask_app.url_map)
#     print("-------------------------\n")

# 主程序入口
if __name__ == "__main__":
    # 运行 Flask 开发服务器
    # 从环境变量获取调试模式状态，默认为 True
    debug_mode = os.environ.get('FLASK_DEBUG', 'True').lower() == 'true'
    # 启动服务器，监听所有网络接口 (0.0.0.0) 的 5001 端口
    flask_app.run(host="0.0.0.0", port=5001, debug=debug_mode)