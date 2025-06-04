# D:\python_code\LocalAgent\modules\context_manager_module.py
from flask import session, current_app
from modules.common import ModuleOutput, DialogueState

class ContextManagerModule:

    @classmethod
    def update_context(cls, user_input: str, state: DialogueState) -> ModuleOutput:
        history = session.get("conversation_history", [])

        max_messages = current_app.config.get('MAX_CONVERSATION_HISTORY', 20)
        if len(history) > max_messages:
             history = history[-max_messages:]
             print(f"[上下文管理] 历史记录已截断至 {len(history)} 条消息。")

        token_count = sum(len(str(msg.get("content", ""))) for msg in history)
        session["conversation_history"] = history

        return ModuleOutput(True, {"history": history, "token_count": token_count},
                            "上下文加载/截断完成", next_module=None)

    @classmethod
    def add_message_and_save(cls, role: str, content: str):
         history = session.get("conversation_history", [])
         history.append({"role": role, "content": content})

         max_messages = current_app.config.get('MAX_CONVERSATION_HISTORY', 20)
         if len(history) > max_messages:
             history = history[-max_messages:]

         session["conversation_history"] = history

    @classmethod
    def get_history(cls) -> list:
         return session.get("conversation_history", [])