# ./app/utils.py
# 文件路径: ./app/utils.py
import os
import json
from flask import session, current_app # 导入 current_app

# 备用提示词
FALLBACK_PROMPT = "你是一位友好的AI助手。"

def load_prompt() -> str:
    # 加载系统提示词
    # PROMPT_FILE_PATH 来自 config.py，是相对于 app 目录的路径
    # 需要拼接 app.root_path (Flask 应用根目录)
    prompt_full_path = os.path.join(current_app.root_path, current_app.config['PROMPT_FILE_PATH'])

    prompt_dir = os.path.dirname(prompt_full_path)
    if prompt_dir and not os.path.exists(prompt_dir): # 检查目录
        try: os.makedirs(prompt_dir); print(f"创建目录: {prompt_dir}")
        except OSError as e: print(f"创建提示词目录失败: {e}")

    if not os.path.exists(prompt_full_path): # 文件不存在
        print(f"提示词文件不存在: {prompt_full_path}，使用备用。")
        return FALLBACK_PROMPT
    try:
        with open(prompt_full_path, 'r', encoding='utf-8') as f:
            content = f.read().strip()
        return content if content else FALLBACK_PROMPT # 文件为空也用备用
    except OSError as e: print(f"读取提示词失败: {e}"); return FALLBACK_PROMPT
    except Exception as e: print(f"加载提示词未知错误: {e}"); return FALLBACK_PROMPT

def get_current_llm_config(session, config) -> tuple[str, str | None]:
    # 获取当前LLM配置
    default_provider = config.get('DEFAULT_PROVIDER', 'None')
    default_model = config.get('DEFAULT_MODEL', None)
    available_providers = config.get('AVAILABLE_PROVIDERS', {})

    provider = session.get("selected_provider", default_provider) # session优先
    model = session.get("selected_model", default_model) # session优先

    # --- 验证 Provider 和 Model ---
    if provider not in available_providers: # Provider无效
        provider = default_provider # 回退默认
        print(f"[警告] Session Provider '{provider}' 无效，回退默认")

    provider_config = available_providers.get(provider)
    if not provider_config: # 连默认Provider配置都没找到
         print(f"[错误] 无法找到Provider配置: {provider}!")
         return "None", None # 无法提供服务

    available_models = provider_config.get("models", [])
    if not available_models: # 当前Provider无模型
        print(f"[错误] Provider {provider} 无可用模型！")
        model = None # 清空模型
    elif not model or model not in available_models: # Model无效或未选
        model = available_models[0] # 回退第一个
        print(f"[警告] Session Model '{model}' 无效/未设，回退: {provider}/{model}")

    # --- 更新 Session ---
    # 无论是否回退，都更新 session 为当前有效值
    session["selected_provider"] = provider
    session["selected_model"] = model

    return provider, model

def get_api_key_status(config) -> dict:
    # 获取API Key配置状态
    status = {}
    available_providers = config.get('AVAILABLE_PROVIDERS', {})
    for name, conf in available_providers.items():
        # 直接使用 config.py 中预计算好的 key_configured 状态
        status[name] = {
            "required": conf.get("key_required", False),
            "configured": conf.get("key_configured", False)
        }
    return status

# --- 移除 context.txt 相关函数 ---
# load_context_from_file, save_context_to_file, remove_session_lines_from_file 已删除
