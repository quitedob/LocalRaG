# D:\python_code\LocalAgent\modules\response_generator_module.py
import json
import time
import requests
import os
from flask import current_app, session
from modules.common import ModuleOutput, DialogueState, UserType
from utils import load_prompt
import copy

class ResponseGeneratorModule:

    @classmethod
    def _ensure_alternating_messages(cls, messages: list) -> list:
        if len(messages) <= 1: return messages
        processed = [messages[0]]
        last_role = messages[0]['role']
        for msg in messages[1:]:
            role = msg.get('role')
            if role not in ['user', 'assistant'] or not msg.get('content', '').strip(): continue
            if role == last_role: continue
            processed.append(msg); last_role = role
        if processed and processed[-1]['role'] == 'assistant': processed.pop()
        return processed

    @classmethod
    def generate(cls, user_input: str, state: DialogueState, history: list,
                 selected_provider: str | None, selected_model: str | None,
                 session_id: str | None = None,
                 temp_keys: dict | None = None) -> ModuleOutput:

        provider_name, model_name, api_url = cls._get_provider_info(selected_provider, selected_model)
        if not model_name or not api_url:
             fallback_msg = "无可用模型或API URL配置"
             if not provider_name or provider_name == 'None': fallback_msg = "未选择有效的LLM提供者"
             print(f"[生成错误] {fallback_msg} for provider '{selected_provider}', model '{selected_model}'")
             return ModuleOutput(False, message=fallback_msg)

        print(f"[生成] 使用模型: {provider_name}/{model_name}")

        system_prompt = load_prompt()
        messages = [{"role": "system", "content": system_prompt}]
        valid_history = [msg for msg in history if msg.get("role") in ["user", "assistant"] and msg.get("content")]
        messages.extend(valid_history)

        final_messages_to_send = cls._ensure_alternating_messages(copy.deepcopy(messages))
        if len(final_messages_to_send) <= 1 or final_messages_to_send[-1]['role'] != 'user':
            print(f"[错误] 构建消息列表失败: {final_messages_to_send}")
            user_msgs = [m for m in messages if m['role'] == 'user']
            if user_msgs: final_messages_to_send = [messages[0], user_msgs[-1]]
            else: return ModuleOutput(False, message="无法构建有效请求(无用户消息)")


        session_key = None
        if session_id: # Try to get from Flask session if session_id is passed (might not work in celery task directly)
             try:
                 session_key = session.get(f"{provider_name}_api_key")
             except RuntimeError: # Handle cases outside request context
                 session_key = None

        start_time = time.time()
        raw_response = cls._call_llm_api(
            provider=provider_name, api_url=api_url, model=model_name,
            messages=final_messages_to_send,
            session_key=session_key,
            temp_keys=temp_keys
        )
        end_time = time.time()
        print(f"[生成] LLM调用耗时: {end_time - start_time:.2f}秒")

        success = "调用失败" not in raw_response and "调用异常" not in raw_response and "调用超时" not in raw_response and "Key缺失" not in raw_response
        message = f"模型调用 {'成功' if success else '失败'}"
        if not success: message += f": {raw_response.split(':', 1)[-1].strip()}"

        return ModuleOutput(
            success=success,
            data={"raw_response": raw_response, "model_used": f"{provider_name}/{model_name}"},
            message=message,
            next_module="response_optimization"
        )

    @staticmethod
    def _call_llm_api(provider: str, api_url: str, model: str, messages: list,
                      session_key: str | None = None,
                      temp_keys: dict | None = None
                     ) -> str:
        available_providers = current_app.config.get('AVAILABLE_PROVIDERS', {})
        llm_timeout = current_app.config.get('LLM_REQUEST_TIMEOUT', 120)
        deepseek_key_global = os.environ.get("DEEPSEEK_API_KEY", current_app.config.get("DEEPSEEK_API_KEY"))
        local_key_global = os.environ.get("LOCAL_API_KEY", current_app.config.get("LOCAL_API_KEY"))

        payload = {"model": model, "messages": messages, "stream": False, "temperature": 0.7, "max_tokens": 1500}
        headers = {"Content-Type": "application/json"}
        api_key = None
        provider_config = available_providers.get(provider, {})
        key_required = provider_config.get("key_required", False)

        if key_required:
            effective_temp_keys = temp_keys or {}
            if provider in effective_temp_keys and effective_temp_keys[provider]: api_key = effective_temp_keys[provider]
            elif session_key: api_key = session_key
            else:
                if provider == "DeepSeek" and provider_config.get("key_configured"): api_key = deepseek_key_global
                elif provider == "Local" and provider_config.get("key_configured"): api_key = local_key_global
            if not api_key: return f"调用失败: {provider} Key缺失"
            headers["Authorization"] = f"Bearer {api_key}"

        assistant_message = "调用失败: 未知错误"
        try:
            resp = requests.post(api_url, headers=headers, json=payload, timeout=llm_timeout)
            resp.raise_for_status()
            response_data = resp.json()

            content = ""
            if provider == "DeepSeek":
                content = response_data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
            elif provider == "Local":
                content = response_data.get("message", {}).get("content", "") or \
                          response_data.get("response", "") or \
                          (response_data.get("choices", [{}])[0].get("message", {}).get("content", "") if response_data.get("choices") else "")
                content = content.strip()
            else:
                return f"调用失败: 未知提供者 '{provider}'"

            assistant_message = content or f"模型返回空内容 ({provider})"

        except requests.Timeout: assistant_message = f"调用超时({llm_timeout}秒)"
        except requests.HTTPError as e:
             error_body = "未知响应体"
             try: error_body = e.response.text[:100]
             except Exception: pass
             assistant_message = f"调用失败: HTTP {e.response.status_code}: {error_body}"
        except requests.RequestException as e: assistant_message = f"调用失败: 网络异常 {type(e).__name__}"
        except Exception as e:
             import traceback
             print(f"处理LLM响应时发生未知错误: {traceback.format_exc()}")
             assistant_message = f"调用失败: 处理异常 {type(e).__name__}"
        return assistant_message

    @classmethod
    def _get_provider_info(cls, provider_input, model_input):
        config = current_app.config
        available = config.get('AVAILABLE_PROVIDERS', {})
        default_p = config.get('DEFAULT_PROVIDER', 'None')
        default_m = config.get('DEFAULT_MODEL', None)

        provider_name = provider_input if provider_input and provider_input in available else default_p
        provider_config = available.get(provider_name)

        if not provider_config:
             print(f"[配置错误] 无法找到提供者 '{provider_name}' 的配置。")
             return provider_name, None, None

        models = provider_config.get("models", [])
        model_name = model_input if model_input and model_input in models else (models[0] if models else None)

        if not model_name and default_p == provider_name:
            model_name = default_m # Fallback to default model if initial selection is invalid

        api_url = provider_config.get("url")

        if not models: print(f"[配置警告] 提供者 '{provider_name}' 没有配置可用模型。")
        if not model_name: print(f"[配置警告] 无法为提供者 '{provider_name}' 确定有效模型。")
        if not api_url: print(f"[配置错误] 提供者 '{provider_name}' 未配置 API URL。")

        return provider_name, model_name, api_url