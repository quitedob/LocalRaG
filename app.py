# D:\python_code\LocalAgent\app.py
from flask import Flask, request, jsonify, render_template, session, redirect, url_for
import uuid
import json
import requests
from modules.dialogue_pipeline import DialoguePipeline
from modules.context_manager_module import ContextManagerModule
from modules.summary_module import SummaryModule
from config import (
    AVAILABLE_PROVIDERS, DEFAULT_PROVIDER, DEFAULT_MODEL,
    CONTEXT_FILE, DEEPSEEK_API_KEY, LOCAL_API_KEY
)
from utils import save_context_to_file, remove_session_lines_from_file
import os
from dotenv import load_dotenv

# 确保在 app 创建前加载环境变量
load_dotenv()

app = Flask(__name__)
app.secret_key = "dev-secret-key-123"
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

# --- 辅助函数 (保持不变) ---
def get_current_llm_config() -> tuple[str, str | None]:
    """获取当前会话选择的LLM提供者和模型，并验证有效性"""
    provider = session.get("selected_provider", DEFAULT_PROVIDER)
    model = session.get("selected_model", DEFAULT_MODEL)

    if provider not in AVAILABLE_PROVIDERS:
        provider = DEFAULT_PROVIDER
        session["selected_provider"] = provider
        print(f"[警告] Session 中的提供者无效，回退到默认: {provider}")

    provider_config = AVAILABLE_PROVIDERS.get(provider)
    if not provider_config:
        print(f"[错误] 无法找到提供者 {provider} 的配置！")
        return DEFAULT_PROVIDER, DEFAULT_MODEL

    available_models = provider_config.get("models", [])

    if not available_models:
         print(f"[错误] 提供者 {provider} 没有配置可用模型！")
         # 如果当前 provider 没模型，尝试找第一个有模型的
         for p_name, p_conf in AVAILABLE_PROVIDERS.items():
             if p_conf.get("models"):
                 provider = p_name
                 model = p_conf["models"][0]
                 session["selected_provider"] = provider
                 session["selected_model"] = model
                 print(f"[警告] 切换到第一个有模型的提供者: {provider}/{model}")
                 return provider, model
         return provider, None # 实在没有就返回 None

    if not model or model not in available_models: # 处理 model 为 None 或无效的情况
        model = available_models[0] # 回退到第一个
        session["selected_model"] = model
        print(f"[警告] Session 中的模型对提供者 {provider} 无效或未设置，回退到: {model}")

    return provider, model

def get_api_key_status() -> dict:
     """检查各Provider的API Key配置状态"""
     status = {}
     for provider, config in AVAILABLE_PROVIDERS.items():
          is_configured = config.get("key_configured", False)
          # 再次确认 Key 配置状态检查逻辑
          actual_key = None
          if provider == "DeepSeek":
               actual_key = os.environ.get("DEEPSEEK_API_KEY", DEEPSEEK_API_KEY)
               is_configured = bool(actual_key and actual_key != "YOUR_DEEPSEEK_API_KEY_HERE")
          elif provider == "Local":
              actual_key = os.environ.get("LOCAL_API_KEY", LOCAL_API_KEY)
              is_configured = bool(actual_key) # 本地 Key 存在即视为配置

          status[provider] = {
               "required": config.get("key_required", False),
               "configured": is_configured
          }
     return status


# --- 路由 ---
@app.route('/', methods=['GET', 'POST'])
def index_page():
    if "session_id" not in session:
        session["session_id"] = str(uuid.uuid4())
        session["conversation_history"] = []
        print(f"新会话开始: {session['session_id']}")

    current_provider, current_model = get_current_llm_config()
    api_key_status = get_api_key_status()
    final_response = None # 初始化 final_response
    outputs = {} # 初始化 outputs
    success = True # 默认状态
    error_message = None # 初始化错误消息
    state = None # 初始化状态

    # --- POST 请求处理 ---
    if request.method == 'POST':
        user_input = request.form.get('user_input', '').strip()
        session_deepseek_key = request.form.get('session_deepseek_key')
        session_local_key = request.form.get('session_local_key')

        current_api_status = get_api_key_status()
        if session_deepseek_key and not current_api_status.get("DeepSeek", {}).get("configured"):
            session["DeepSeek_api_key"] = session_deepseek_key
            print("[会话] 存储了用户提供的 DeepSeek Key")
        if session_local_key and not current_api_status.get("Local", {}).get("configured"):
            session["Local_api_key"] = session_local_key
            print("[会话] 存储了用户提供的 Local Key")

        if not user_input:
            error_message = "请输入内容。" # 设置错误消息
            # 注意：这里应该渲染模板并返回，而不是继续执行
            return render_template('index.html',
                                   error=error_message, # 传递错误消息
                                   providers=AVAILABLE_PROVIDERS,
                                   current_provider=current_provider, current_model=current_model,
                                   api_key_status=api_key_status,
                                   history=ContextManagerModule.get_history(),
                                   outputs={}, # 传递空 outputs
                                   final_response=None, # 传递 None
                                   state=None, # 传递 None
                                   success=False) # 标记失败


        user_item = {"role": "user", "content": user_input, "session_id": session["session_id"]}
        ContextManagerModule.add_message_and_save("user", user_input)
        save_context_to_file(user_item)

        result = DialoguePipeline.process_input(user_input, current_provider, current_model)

        # 从 result 中获取需要在模板中使用的变量
        outputs = result.get("outputs", {}) # 获取 outputs，默认为空字典
        final_response = result.get("response") # 获取 final_response
        state = result.get("state") # 获取 state
        success = result.get("success", False) # 获取 success 状态
        if not success and not final_response: # 如果处理失败且没有特定响应
             error_message = result.get("message", "处理请求时发生未知错误。") # 将 pipeline 的 message 作为错误信息

        # 只有在处理成功或有特定响应（如危机响应）时才记录助手消息
        if final_response:
             assistant_response_plain = final_response.replace("<br>", "\n").strip()
             if assistant_response_plain:
                 assistant_item = {"role": "assistant", "content": assistant_response_plain, "session_id": session["session_id"]}
                 ContextManagerModule.add_message_and_save("assistant", assistant_response_plain)
                 save_context_to_file(assistant_item)
             else:
                 print("[app.py] 助手回复内容为空，未添加到历史记录。")
        # 如果处理失败，final_response 可能为 None，此时不应记录助手消息


    # --- 统一渲染逻辑 (GET 和 POST 最终都到这里) ---
    return render_template('index.html',
                           error=error_message, # 使用上面定义的 error_message
                           providers=AVAILABLE_PROVIDERS,
                           current_provider=current_provider,
                           current_model=current_model,
                           api_key_status=api_key_status,
                           history=ContextManagerModule.get_history(), # 获取最新的历史记录
                           outputs=outputs, # 传递 outputs (POST 时有值，GET 时为空字典)
                           final_response=final_response, # 传递 final_response (POST 时可能有值，GET 时为 None)
                           state=state, # 传递 state (POST 时可能有值，GET 时为 None)
                           success=success) # 传递 success 状态


# --- API 路由 (保持不变) ---
@app.route('/api/set_model', methods=['POST'])
def api_set_model():
    data = request.json
    new_provider = data.get("provider")
    new_model = data.get("model")
    if not new_provider or new_provider not in AVAILABLE_PROVIDERS:
        return jsonify({"ok": False, "error": "无效的提供者"}), 400
    provider_config = AVAILABLE_PROVIDERS[new_provider]
    available_models = provider_config.get("models", [])
    if not available_models:
         return jsonify({"ok": False, "error": f"提供者 {new_provider} 无可用模型"}), 400
    # 如果 new_model 为空或无效，则设为该提供者的第一个默认模型
    if not new_model or new_model not in available_models:
        new_model = available_models[0]

    session["selected_provider"] = new_provider
    session["selected_model"] = new_model
    print(f"模型已切换至: {new_provider} / {new_model}")
    return jsonify({"ok": True, "msg": f"模型已切换至: {new_provider} / {new_model}", "provider": new_provider, "model": new_model}) # 返回设置后的值

@app.route('/api/set_session_api_key', methods=['POST'])
def api_set_session_api_key():
    data = request.json
    provider = data.get("provider")
    api_key = data.get("api_key")
    if not provider or provider not in AVAILABLE_PROVIDERS:
         return jsonify({"ok": False, "error": "无效的提供者"}), 400
    if not api_key:
        return jsonify({"ok": False, "error": "API Key 不能为空"}), 400

    # 使用 get_api_key_status 获取最新的配置状态
    current_api_status = get_api_key_status()
    provider_status = current_api_status.get(provider, {})

    if not provider_status.get("configured", True): # 仅在未配置时允许设置
        session_key_name = f"{provider}_api_key"
        session[session_key_name] = api_key
        print(f"[会话] 用户为 {provider} 设置了 API Key (Session-level)")
        return jsonify({"ok": True, "msg": f"{provider} 的会话级 API Key 已设置"})
    else:
        print(f"[会话] 拒绝设置 {provider} 的会话级 API Key，因为已有全局配置。")
        return jsonify({"ok": False, "error": f"{provider} 的 API Key 已在全局配置，请修改配置文件或环境变量。"}), 403

@app.route('/api/clear_chat', methods=['POST'])
def api_clear_chat():
    sid = session.get("session_id")
    if not sid: return jsonify({"ok": True, "msg": "无会话记录"})
    remove_session_lines_from_file(sid)
    session.pop("conversation_history", None)
    session.pop("dialogue_state", None)
    for provider in AVAILABLE_PROVIDERS: session.pop(f"{provider}_api_key", None)
    # 清空后可能需要重置模型选择为默认值？可选。
    # session.pop("selected_provider", None)
    # session.pop("selected_model", None)
    print(f"会话已清空: {sid}")
    return jsonify({"ok": True, "msg": "会话已清空"})

@app.route('/api/summarize_chat', methods=['POST'])
def api_summarize_chat():
    sid = session.get("session_id")
    if not sid: return jsonify({"ok": False, "error": "无活动会话"}), 400
    history = ContextManagerModule.get_history()
    if not history: return jsonify({"ok": False, "error": "对话历史为空"}), 400
    summary_result = SummaryModule.generate_summary(history)
    if summary_result.success:
        return jsonify({"ok": True, "summary": summary_result.data.get("summary", "总结生成成功但内容为空。")})
    else:
        return jsonify({"ok": False, "error": f"总结生成失败: {summary_result.message}"}), 500

@app.route('/api/upload_txt', methods=['POST'])
def api_upload_txt():
    file = request.files.get("file")
    if not file: return jsonify({"ok": False, "msg": "未选择文件"})
    filename = file.filename
    if not filename.lower().endswith(".txt"): return jsonify({"ok": False, "msg": "仅支持TXT文件"})
    try: txt = file.read().decode("utf-8")
    except UnicodeDecodeError as e: return jsonify({"ok": False, "msg": f"解码失败: {e}"})
    sid = session.get("session_id", str(uuid.uuid4()))
    if "session_id" not in session: session["session_id"] = sid
    file_content_for_history = f"用户上传了文件 '{filename}'，内容如下：\n---\n{txt[:1000]}...\n---" # 截断预览
    ContextManagerModule.add_message_and_save("system", file_content_for_history) # 添加系统消息到历史
    file_item = {"role": "file_upload", "filename": filename, "content_preview": txt[:200], "session_id": sid}
    save_context_to_file(file_item) # 保存上传事件日志
    return jsonify({"ok": True, "msg": f"文件 '{filename}' 内容摘要已添加到对话历史"})


if __name__ == "__main__":
    if not os.path.exists("templates"):
        os.makedirs("templates")
        print("创建 templates 目录")
    # 确保 prompt 文件存在或有备用 (utils.load_prompt 会处理)
    # import utils
    # utils.load_prompt() # 可以在启动时预加载检查一下

    app.run(host="0.0.0.0", port=5001, debug=True)