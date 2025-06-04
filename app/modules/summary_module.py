# ./app/modules/summary_module.py
# 文件路径: ./app/modules/summary_module.py
import json
from flask import current_app, session # 导入 current_app 和 session
from .common import ModuleOutput # 导入公共输出类
from .response_generator_module import ResponseGeneratorModule # 复用LLM调用
# 导入配置
from config import SUMMARY_PROMPT, SUMMARY_PROVIDER, SUMMARY_MODEL, AVAILABLE_PROVIDERS

class SummaryModule:
    # 对话总结模块

    @classmethod
    def generate_summary(cls, conversation_history: list,
                         temp_keys: dict | None = None) -> ModuleOutput: # 添加temp_keys参数
        # 根据历史生成总结报告
        if not conversation_history: return ModuleOutput(False, message="历史为空")

        # --- 获取总结配置 ---
        provider_name = current_app.config.get('SUMMARY_PROVIDER') # 从配置获取
        model_name = current_app.config.get('SUMMARY_MODEL') # 从配置获取
        summary_prompt_template = current_app.config.get('SUMMARY_PROMPT') # 从配置获取

        if not provider_name or not model_name: return ModuleOutput(False, message="未配置总结模型")

        provider_config = current_app.config['AVAILABLE_PROVIDERS'].get(provider_name)
        if not provider_config: return ModuleOutput(False, message=f"未找到总结Provider配置:{provider_name}")
        api_url = provider_config["url"]

        # --- 格式化历史记录 ---
        formatted_history = ""
        role_map = {"user": "用户", "assistant": "AI助手", "system": "系统"}
        for msg in conversation_history:
            role = role_map.get(msg.get("role"), msg.get("role", "未知"))
            content = str(msg.get('content', '')).strip()
            if len(content) > 500: content = content[:500] + "...(截断)" # 限制长度
            formatted_history += f"{role}: {content}\n---\n"

        # --- 构建总结Prompt ---
        prompt_text = summary_prompt_template.format(conversation_history=formatted_history.strip())
        summary_messages = [{"role": "user", "content": prompt_text}]

        print(f"[总结] 使用模型 {provider_name}/{model_name} 请求总结...")

        # --- 获取API Key (Session Key - 如果需要的话，但总结一般用全局Key) ---
        session_key = None
        # if 'session' in globals() and f"{provider_name}_api_key" in session:
        #     session_key = session.get(f"{provider_name}_api_key")

        # --- 调用LLM API ---
        # 复用 ResponseGenerator 的调用方法，传递 temp_keys
        summary_response = ResponseGeneratorModule._call_llm_api(
            provider=provider_name, api_url=api_url, model=model_name,
            messages=summary_messages,
            session_key=session_key, # 传递Session Key (如有)
            temp_keys=temp_keys # 传递任务提供的Key (如有)
        )

        # --- 处理结果 ---
        success = "调用失败" not in summary_response and "调用异常" not in summary_response and "调用超时" not in summary_response
        message = f"总结生成 {'成功' if success else '失败'}"
        if not success: message += f": {summary_response.split(':', 1)[-1].strip()}"
        summary_text = summary_response if success else ""

        return ModuleOutput(success=success, data={"summary": summary_text}, message=message)
