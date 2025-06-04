# D:\python_code\LocalAgent\app\main\routes.py
from flask import (
    render_template, request, session, jsonify, current_app, g,
    redirect, url_for, flash
)
import uuid
import json
from . import main
from app.modules.context_manager_module import ContextManagerModule # Use absolute import
from app.utils import get_current_llm_config, get_api_key_status  # Use absolute import
from app.tasks import process_dialogue_task                      # Use absolute import
from redis import exceptions as redis_exceptions

@main.route('/', methods=['GET', 'POST'])
def index_page():
    session_id = session.get("session_id")
    redis_available = hasattr(current_app, 'redis_client') and current_app.redis_client is not None

    if not session_id:
        if redis_available:
            session_id = str(uuid.uuid4())
            session["session_id"] = session_id
            print(f"新会话开始 (Redis): {session_id}")
        else:
            flash("服务暂时不可用 (无法连接到会话存储)，请稍后重试。", "error")
            # Provide default values for rendering template when Redis is unavailable
            return render_template('index.html', error="服务暂时不可用", history=[], providers={}, current_provider="None", current_model=None, api_key_status={}, outputs={}, final_response=None, state=None, success=False, status_text="错误")


    current_provider, current_model = get_current_llm_config(session, current_app.config)
    api_key_status = get_api_key_status(current_app.config)

    error_message = None; outputs = {}; final_response = None; state_dict = {}; success = True

    if request.method == 'POST':
        if not redis_available:
             flash("服务暂时不可用，无法处理您的请求。", "error")
             success = False
        else:
            user_input = request.form.get('user_input', '').strip()
            temp_keys = {}
            session_deepseek_key = request.form.get('session_deepseek_key')
            session_local_key = request.form.get('session_local_key')
            if session_deepseek_key and not api_key_status.get("DeepSeek", {}).get("configured"):
                temp_keys["DeepSeek"] = session_deepseek_key
            if session_local_key and not api_key_status.get("Local", {}).get("configured"):
                temp_keys["Local"] = session_local_key

            if not user_input:
                error_message = "请输入内容。"
                success = False
            else:
                try:
                    ContextManagerModule.add_message(session_id, "user", user_input)
                except redis_exceptions.ConnectionError as e:
                     print(f"添加用户消息时 Redis 连接失败: {e}")
                     flash("会话存储服务连接失败，请稍后重试。", "error")
                     success = False
                     error_message = "服务连接失败"
                except Exception as e:
                    print(f"添加用户消息到 Redis 失败: {e}")
                    flash("无法保存您的消息，请稍后重试。", "error")
                    error_message = "消息保存失败"
                    success = False

                if success:
                    celery_available = hasattr(current_app, 'celery') and current_app.celery is not None
                    if celery_available:
                        try:
                            task = process_dialogue_task.delay(
                                session_id=session_id,
                                user_input=user_input,
                                selected_provider=current_provider,
                                selected_model=current_model,
                                session_api_keys=temp_keys
                            )
                            print(f"启动Celery任务: {task.id}")

                            try:
                                llm_timeout_config = current_app.config.get('LLM_REQUEST_TIMEOUT', 120)
                                wait_timeout = llm_timeout_config + 15
                                result = task.get(timeout=wait_timeout)
                                if result and isinstance(result, dict):
                                    success = result.get("success", False)
                                    final_response = result.get("response")
                                    state_dict = result.get("state", {})
                                    outputs = result.get("outputs", {})
                                    if not success:
                                        error_message = result.get("message", "处理请求出错")
                                        flash(error_message, "warning")
                                else:
                                    success = False; error_message = "任务返回格式不正确"
                                    print(f"任务 {task.id} 返回异常: {result}")
                                    flash(error_message, "error")
                            except TimeoutError:
                                success = False; error_message = "请求处理超时，请重试"
                                print(f"任务 {task.id} 超时")
                                flash(error_message, "error")
                            except Exception as e:
                                success = False; error_message = f"获取结果出错: {type(e).__name__}"
                                print(f"获取任务 {task.id} 结果错误: {e}")
                                import traceback; traceback.print_exc()
                                flash(error_message, "error")

                        except Exception as e:
                            success = False; error_message = f"无法启动处理任务: {e}"
                            print(f"启动 Celery 任务失败: {e}")
                            flash(error_message, "error")
                    else:
                        success = False; error_message = "后台处理服务不可用"
                        print("Celery 不可用，无法处理请求。")
                        flash(error_message, "error")

    conversation_history = []
    if redis_available:
        try:
            conversation_history = ContextManagerModule.get_history(session_id)
        except redis_exceptions.ConnectionError as e:
             print(f"获取历史时 Redis 连接失败: {e}")
             flash("会话存储服务连接失败，无法加载历史记录。", "error")
             if not error_message: error_message = "服务连接失败"
        except Exception as e:
            print(f"获取会话 {session_id} 历史失败: {e}")
            if not error_message:
                flash("无法加载对话历史。", "error")
                error_message = "历史加载失败"

    status_text = f"模型: {current_provider}/{current_model or 'N/A'}"
    if state_dict: status_text += f" | 状态: {state_dict.get('user_type', '?')}"
    elif error_message: status_text = "错误"

    return render_template(
         'index.html',
        error=error_message,
        providers=current_app.config.get('AVAILABLE_PROVIDERS', {}), # Ensure providers is passed
        current_provider=current_provider,
        current_model=current_model,
        api_key_status=api_key_status,
        history=conversation_history,
        outputs=outputs,
        final_response=final_response,
        state=state_dict,
        success=success,
        status_text=status_text
    )