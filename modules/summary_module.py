# D:\python_code\LocalAgent\modules\summary_module.py
import json
from flask import session, current_app
from modules.common import ModuleOutput
from modules.response_generator_module import ResponseGeneratorModule

class SummaryModule:

    @classmethod
    def generate_summary(cls, conversation_history: list, temp_keys: dict | None = None) -> ModuleOutput:
        if not conversation_history:
            return ModuleOutput(success=False, message="对话历史为空，无法生成总结。")

        provider_name = current_app.config.get('SUMMARY_PROVIDER')
        model_name = current_app.config.get('SUMMARY_MODEL')
        summary_prompt_template = current_app.config.get('SUMMARY_PROMPT')
        available_providers = current_app.config.get('AVAILABLE_PROVIDERS', {})

        if not provider_name or not model_name:
             return ModuleOutput(success=False, message="未配置用于总结的模型或提供者。")
        if not summary_prompt_template:
             return ModuleOutput(success=False, message="未配置总结提示词模板 (SUMMARY_PROMPT)。")

        provider_config = available_providers.get(provider_name)
        if not provider_config:
             return ModuleOutput(success=False, message=f"未找到总结提供者配置: {provider_name}")
        api_url = provider_config.get("url")
        if not api_url:
            return ModuleOutput(success=False, message=f"总结提供者 '{provider_name}' 未配置 API URL。")

        formatted_history = ""
        for msg in conversation_history:
            role = "用户" if msg.get("role") == "user" else "AI助手" if msg.get("role") == "assistant" else msg.get("role", "系统")
            content = str(msg.get('content', ''))
            if msg.get("role") == "system" and len(content) > 500:
                  content = content[:500] + "... (内容过长已截断)"
            formatted_history += f"{role}: {content}\n---\n"

        prompt_text = summary_prompt_template.format(conversation_history=formatted_history.strip())
        summary_messages = [{"role": "user", "content": prompt_text}]

        print(f"[总结模块] 使用模型 {provider_name}/{model_name} 请求总结...")

        session_key = None
        try:
            if 'session' in globals() and session and f"{provider_name}_api_key" in session:
                session_key = session.get(f"{provider_name}_api_key")
        except RuntimeError: # Handle cases outside request context
            session_key = None


        summary_response = ResponseGeneratorModule._call_llm_api(
            provider=provider_name,
            api_url=api_url,
            model=model_name,
            messages=summary_messages,
            session_key=session_key,
            temp_keys=temp_keys
        )

        success = "调用失败" not in summary_response and "调用异常" not in summary_response and "调用超时" not in summary_response and "Key缺失" not in summary_response
        message = f"总结生成 {'成功' if success else '失败'}"
        if not success: message += f": {summary_response.split(':', 1)[-1].strip()}"
        summary_text = summary_response if success else ""

        return ModuleOutput(
            success=success,
            data={"summary": summary_text},
            message=message
        )