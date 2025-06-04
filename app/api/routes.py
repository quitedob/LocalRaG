# D:\python_code\LocalAgent\app\api\routes.py
# 文件作用：定义 API 相关的路由 (使用修正后的蓝图变量 api_v1)

from flask import request, jsonify, session, current_app
# !! 修改：导入修正后的蓝图变量名 api_v1 !!
from . import api_v1
from app.utils import get_current_llm_config, get_api_key_status
from app.modules.context_manager_module import ContextManagerModule
from app.tasks import generate_summary_task, get_task_result
from redis import exceptions as redis_exceptions
import uuid

# --- 设置模型 API ---
# !! 修改：使用 @api_v1.route 装饰器 !!
@api_v1.route('/set_model', methods=['POST'])
def api_set_model():
    data = request.json
    new_provider = data.get("provider")
    new_model = data.get("model")
    available_providers = current_app.config.get('AVAILABLE_PROVIDERS', {})

    if not new_provider or new_provider not in available_providers:
        return jsonify(ok=False, error="无效的提供者"), 400

    provider_config = available_providers[new_provider]
    available_models = provider_config.get("models", [])

    if not available_models:
        return jsonify(ok=False, error=f"提供者 {new_provider} 无可用模型"), 400
    if not new_model or new_model not in available_models:
        new_model = available_models[0]

    session["selected_provider"] = new_provider
    session["selected_model"] = new_model

    print(f"[API] 模型已切换至: {new_provider} / {new_model}")
    return jsonify(ok=True, msg=f"模型已切换至: {new_provider}/{new_model}", provider=new_provider, model=new_model)

# --- 设置会话级 API Key API ---
# !! 修改：使用 @api_v1.route 装饰器 !!
@api_v1.route('/set_session_api_key', methods=['POST'])
def api_set_session_api_key():
    data = request.json
    provider = data.get("provider"); api_key = data.get("api_key")
    available_providers = current_app.config.get('AVAILABLE_PROVIDERS', {})

    if not provider or provider not in available_providers: return jsonify(ok=False, error="无效提供者"), 400
    if not api_key: return jsonify(ok=False, error="API Key不能为空"), 400

    current_api_status = get_api_key_status(current_app.config)
    provider_status = current_api_status.get(provider, {})

    if not provider_status.get("configured", False):
        session_key_name = f"{provider}_api_key"
        session[session_key_name] = api_key
        print(f"[API][会话] 用户为 {provider} 设置了临时 Key")
        return jsonify(ok=True, msg=f"{provider} 临时 Key 已设置")
    else:
        print(f"[API][会话] 拒绝设置 {provider} 临时 Key (已有全局配置)")
        return jsonify(ok=False, error=f"{provider} Key 已全局配置"), 403

# --- 清空聊天记录 API ---
# !! 修改：使用 @api_v1.route 装饰器 !!
@api_v1.route('/clear_chat', methods=['POST'])
def api_clear_chat():
    sid = session.get("session_id")
    if not sid: return jsonify(ok=True, msg="无活动会话")

    redis_available = hasattr(current_app, 'redis_client') and current_app.redis_client is not None
    if not redis_available: return jsonify(ok=False, error="会话存储服务不可用"), 503

    try:
        ContextManagerModule.clear_history(sid)
        session.pop("conversation_history", None)
        session.pop("dialogue_state", None)
        for provider in current_app.config.get('AVAILABLE_PROVIDERS', {}):
            session.pop(f"{provider}_api_key", None)

        print(f"[API] 会话已清空 (Redis): {sid}")
        return jsonify(ok=True, msg="当前会话聊天记录已清空")
    except redis_exceptions.ConnectionError as e:
        print(f"[API] 清空会话 {sid} 时 Redis 连接失败: {e}")
        return jsonify(ok=False, error="会话存储服务连接失败"), 503
    except Exception as e:
        print(f"[API] 清空会话 {sid} 时出错: {e}")
        return jsonify(ok=False, error=f"清空会话时发生错误: {e}"), 500

# --- 生成对话总结 API ---
# !! 修改：使用 @api_v1.route 装饰器 !!
@api_v1.route('/summarize_chat', methods=['POST'])
def api_summarize_chat():
    sid = session.get("session_id")
    if not sid: return jsonify(ok=False, error="无活动会话"), 400

    redis_available = hasattr(current_app, 'redis_client') and current_app.redis_client is not None
    if not redis_available: return jsonify(ok=False, error="服务不可用，无法获取历史"), 503
    celery_available = hasattr(current_app, 'celery') and current_app.celery is not None
    if not celery_available: return jsonify(ok=False, error="后台处理服务不可用"), 503

    try:
        if not ContextManagerModule.get_history(sid):
            return jsonify(ok=False, error="对话历史为空，无法总结"), 400

        task = generate_summary_task.delay(session_id=sid)
        print(f"[API] 已启动总结任务: {task.id} for session {sid}")
        return jsonify(ok=True, task_id=task.id, msg="总结任务已启动"), 202
    except redis_exceptions.ConnectionError as e:
        print(f"[API] 检查总结历史时 Redis 连接失败: {e}")
        return jsonify(ok=False, error="会话存储服务连接失败"), 503
    except Exception as e:
        print(f"[API] 启动总结任务时出错: {e}")
        return jsonify(ok=False, error=f"启动总结任务出错: {e}"), 500

# --- 获取任务结果 API ---
# !! 修改：使用 @api_v1.route 装饰器 !!
@api_v1.route('/get_task_result/<task_id>', methods=['GET'])
def api_get_task_result(task_id):
    celery_available = hasattr(current_app, 'celery') and current_app.celery is not None
    if not celery_available: return jsonify(ok=False, error="后台处理服务不可用"), 503

    try:
        result_state, result_data = get_task_result(task_id)
        response_data = {"ok": True, "state": result_state}

        if result_state == 'SUCCESS':
            response_data["result"] = result_data
        elif result_state == 'FAILURE':
            response_data["ok"] = False
            error_msg = "未知错误"
            if isinstance(result_data, dict) and 'error' in result_data: error_msg = result_data['error']
            elif isinstance(result_data, dict) and 'message' in result_data: error_msg = result_data['message']
            elif isinstance(result_data, Exception): error_msg = f"{type(result_data).__name__}: {str(result_data)}"
            elif result_data: error_msg = str(result_data)
            response_data["error"] = f"任务执行失败: {error_msg}"
        elif result_state == 'PROGRESS':
            response_data["status"] = result_data.get('status', '处理中...')
            response_data["progress"] = result_data.get('progress', 0)
        elif result_state == 'PENDING':
            response_data["status"] = "任务等待中或不存在"
        else:
            response_data["status"] = f"任务状态: {result_state}"

        return jsonify(response_data)

    except Exception as e:
        print(f"[API] 查询任务 {task_id} 结果时出错: {e}")
        return jsonify(ok=False, error=f"查询任务结果出错: {e}"), 500

# --- 上传 TXT 文件 API ---
# !! 修改：使用 @api_v1.route 装饰器 !!
@api_v1.route('/upload_txt', methods=['POST'])
def api_upload_txt():
    file = request.files.get('file')
    if not file or file.filename == '': return jsonify(ok=False, msg="未选择文件"), 400
    if not file.filename.lower().endswith(".txt"): return jsonify(ok=False, msg="仅支持TXT文件"), 400

    redis_available = hasattr(current_app, 'redis_client') and current_app.redis_client is not None
    if not redis_available: return jsonify(ok=False, msg="服务暂时不可用"), 503

    sid = session.get("session_id")
    if not sid:
        sid = str(uuid.uuid4()); session["session_id"] = sid
        print(f"[API] 为文件上传创建新会话: {sid}")

    try:
        txt_content = file.read().decode("utf-8")
    except UnicodeDecodeError: return jsonify(ok=False, msg="文件编码错误，请使用UTF-8"), 400
    except Exception as e: print(f"读取文件出错: {e}"); return jsonify(ok=False, msg=f"读取文件出错: {e}"), 500

    preview_length = 500
    ellipsis = "..." if len(txt_content) > preview_length else ""
    file_info = f"用户上传了文件 '{file.filename}'。\n内容预览:\n---\n{txt_content[:preview_length]}{ellipsis}\n---"

    try:
        ContextManagerModule.add_message(sid, "system", file_info)
        print(f"[API] 文件 '{file.filename}' 信息已添加到会话 {sid}")
        return jsonify(ok=True, msg=f"文件 '{file.filename}' 摘要已添加")
    except redis_exceptions.ConnectionError as e:
        print(f"[API] 添加文件消息时 Redis 连接失败: {e}")
        return jsonify(ok=False, msg="会话存储服务连接失败"), 503
    except Exception as e:
        print(f"[API] 添加文件消息到历史出错: {e}")
        return jsonify(ok=False, msg=f"处理文件时出错: {e}"), 500

# --- 获取 API Key 状态 API ---
# !! 修改：使用 @api_v1.route 装饰器 !!
@api_v1.route('/get_api_key_status', methods=['GET'])
def api_get_key_status_endpoint():
    try:
        status = get_api_key_status(current_app.config)
        return jsonify(ok=True, status=status)
    except Exception as e:
        print(f"获取 API Key 状态失败: {e}")
        return jsonify(ok=False, error="获取状态失败"), 500