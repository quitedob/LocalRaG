# D:\python_code\LocalAgent\app\tasks.py
# 文件作用：定义 Celery 异步任务

from celery import shared_task # 导入共享任务装饰器
from flask import current_app # 导入 Flask 当前应用代理
from modules.dialogue_pipeline import DialoguePipeline # 导入对话处理模块
from modules.context_manager_module import ContextManagerModule # 导入上下文管理模块
from modules.summary_module import SummaryModule # 导入总结模块
# !! 移除: from app import celery_app as current_celery_app !!
from celery.result import AsyncResult # 导入获取异步结果的类
from redis import exceptions as redis_exceptions # 导入 Redis 异常
import traceback # 用于打印错误堆栈

# -- 异步处理对话的任务 ---
# bind=True 让任务函数的第一个参数 self 指向任务实例本身
# ignore_result=False 表示需要存储任务结果 (默认即是 False)
@shared_task(bind=True, ignore_result=False)
def process_dialogue_task(self, session_id: str, user_input: str,
                          selected_provider: str | None, selected_model: str | None,
                          session_api_keys: dict | None = None):
    """Celery 任务：处理单轮用户对话"""
    # 打印任务开始日志，包含任务 ID
    print(f"[任务 {self.request.id}] 开始处理会话 {session_id} 的用户输入...")
    # 获取临时的 API Keys
    temp_keys = session_api_keys or {}
    try:
        # 调用对话处理流水线
        result = DialoguePipeline.process_input(
            user_input=user_input,
            selected_provider=selected_provider,
            selected_model=selected_model,
            session_id=session_id,
            temp_keys=temp_keys # 传递临时 Key
        )

        # 如果处理成功且有回复内容
        if result.get("success") and result.get("response"):
            # 清理回复文本中的 <br> 标签
            response_plain = result["response"].replace("<br>", "\n").strip()
            # 确保回复不为空
            if response_plain:
                try:
                    # 将助手的回复添加到 Redis 历史记录
                    ContextManagerModule.add_message(session_id, "assistant", response_plain)
                except redis_exceptions.ConnectionError as redis_err:
                    # 处理 Redis 连接错误
                    print(f"[任务 {self.request.id} 错误] 保存助手回复时 Redis 连接失败: {redis_err}")
                    # 标记结果为失败，并设置错误消息
                    result["success"] = False
                    result["message"] = "生成回复成功，但保存会话失败。"
                except Exception as save_err:
                    # 处理其他保存错误
                    print(f"[任务 {self.request.id} 错误] 保存助手回复时发生未知错误: {save_err}")
                    result["success"] = False
                    result["message"] = "生成回复成功，但保存会话时发生内部错误。"

        # 返回处理结果 (包含 success, response, state, outputs 等)
        return result

    except redis_exceptions.ConnectionError as e:
        # 处理任务执行过程中的 Redis 连接错误
        print(f"[任务 {self.request.id}] 处理对话时 Redis 连接错误: {e}")
        return {"success": False, "message": "会话存储服务暂时不可用，请稍后重试。"}
    except Exception as e:
        # 处理任务执行过程中的其他未知异常
        print(f"[任务 {self.request.id}] 处理对话异常: {e}")
        traceback.print_exc() # 打印详细的错误堆栈信息
        # 返回包含错误信息的失败结果
        return {"success": False, "message": f"处理请求时发生内部错误: {type(e).__name__}"}

# --- 异步生成总结的任务 ---
@shared_task(bind=True, ignore_result=False)
def generate_summary_task(self, session_id: str):
    """Celery 任务：为指定会话生成总结"""
    # 打印任务开始日志
    print(f"[任务 {self.request.id}] 开始为会话 {session_id} 生成总结...")
    try:
        # 从 Redis 获取对话历史
        history = ContextManagerModule.get_history(session_id)
        # 如果历史为空，返回错误
        if not history: return {"ok": False, "error": "历史为空，无法生成总结"}

        # 调用总结模块生成总结
        summary_result = SummaryModule.generate_summary(history)

        # 根据总结结果返回成功或失败信息
        if summary_result.success:
            return {"ok": True, "summary": summary_result.data.get("summary", "")}
        else:
            return {"ok": False, "error": f"总结失败: {summary_result.message}"}

    except redis_exceptions.ConnectionError as e:
        # 处理 Redis 连接错误
        print(f"[任务 {self.request.id}] 生成总结时 Redis 连接错误: {e}")
        return {"ok": False, "error": "会话存储服务暂时不可用"}
    except Exception as e:
        # 处理其他未知异常
        print(f"[任务 {self.request.id}] 生成总结异常: {e}")
        traceback.print_exc() # 打印详细错误堆栈
        return {"ok": False, "error": f"生成总结时发生内部错误: {type(e).__name__}"}


# --- 获取任务结果的辅助函数 ---
def get_task_result(task_id: str) -> tuple[str, any]:
    """根据任务 ID 从 Celery 后端获取任务状态和结果"""
    # !! 修改：从 current_app 获取 Celery 实例 !!
    celery = current_app.celery
    if not celery:
        print("[错误] Celery App 在 get_task_result 中不可用！")
        return 'FAILURE', {"error": "Celery服务未初始化"}

    try:
        # 使用任务 ID 创建 AsyncResult 对象
        task_result = AsyncResult(task_id, app=celery) # 使用从 current_app 获取的 celery 实例
        # 获取任务状态
        state = task_result.state
        result_data = None
        # 根据状态获取结果或信息
        if state == 'SUCCESS':
            result_data = task_result.get() # 获取任务返回值
        elif state == 'FAILURE':
            result_data = task_result.result # 获取异常信息
        elif state == 'PROGRESS':
            result_data = task_result.info # 获取进度信息 (如果任务上报了)
        # 返回状态和结果数据
        return state, result_data
    except Exception as e:
        # 处理查询任务结果时的异常
        print(f"[错误] 查询任务 {task_id} 结果异常: {e}")
        return 'FAILURE', {"error": f"查询任务异常: {e}"}