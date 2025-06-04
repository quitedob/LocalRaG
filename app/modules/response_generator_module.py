# ./app/modules/response_generator_module.py
# 文件路径: ./app/modules/response_generator_module.py
import json
import time
import requests
import os
from flask import current_app, session # 导入 current_app 和 session
from .common import ModuleOutput, DialogueState, UserType # 导入公共类
from ..utils import load_prompt # 导入加载提示词
import copy # 用于深拷贝消息列表

class ResponseGeneratorModule:
    # 大模型回复生成模块

    @classmethod
    def _ensure_alternating_messages(cls, messages: list) -> list:
        # 确保消息角色交替
        if len(messages) <= 1: return messages # 至少需要system+user
        processed = [messages[0]] # 保留 system
        last_role = messages[0]['role']
        for msg in messages[1:]:
            role = msg.get('role')
            if role not in ['user', 'assistant'] or not msg.get('content', '').strip(): continue # 跳过无效
            if role == last_role: continue # 跳过连续相同角色
            processed.append(msg); last_role = role
        # 移除结尾的助手消息 (防止API出错)
        if processed and processed[-1]['role'] == 'assistant': processed.pop()
        return processed

    @classmethod
    def generate(cls, user_input: str, state: DialogueState, history: list,
                 selected_provider: str | None, selected_model: str | None,
                 session_id: str | None = None, # 接收 session_id
                 temp_keys: dict | None = None) -> ModuleOutput: # 接收 temp_keys
        # 生成LLM回复主函数
        provider_name, model_name, api_url = cls._get_provider_info(selected_provider, selected_model)
        if not model_name: return ModuleOutput(False, message="无可用模型")
        print(f"[生成] 使用模型: {provider_name}/{model_name}")

        system_prompt = load_prompt() # 加载系统提示
        messages = [{"role": "system", "content": system_prompt}]
        valid_history = [msg for msg in history if msg.get("role") in ["user", "assistant"] and msg.get("content")]
        messages.extend(valid_history) # 添加有效历史

        # 确保交替 (保险)
        final_messages_to_send = cls._ensure_alternating_messages(copy.deepcopy(messages))
        if len(final_messages_to_send) <= 1 or final_messages_to_send[-1]['role'] != 'user':
            print(f"[错误] 构建消息列表失败: {final_messages_to_send}")
            user_msgs = [m for m in messages if m['role'] == 'user']
            if user_msgs: final_messages_to_send = [messages[0], user_msgs[-1]] # 尝试极简回退
            else: return ModuleOutput(False, message="无法构建有效请求(无用户消息)")

        session_key = None # Celery 任务通常无法访问 session
        start_time = time.time()
        raw_response = cls._call_llm_api( # 调用API
            provider=provider_name, api_url=api_url, model=model_name,
            messages=final_messages_to_send,
            session_key=session_key, # 通常为 None
            temp_keys=temp_keys # 使用任务传递的 Key
        )
        end_time = time.time()
        print(f"[生成] LLM调用耗时: {end_time - start_time:.2f}秒")

        success = "调用失败" not in raw_response and "调用异常" not in raw_response and "调用超时" not in raw_response
        message = f"模型调用 {'成功' if success else '失败'}"
        if not success: message += f": {raw_response.split(':', 1)[-1].strip()}" # 添加错误细节

        return ModuleOutput(
            success=success,
            data={"raw_response": raw_response, "model_used": f"{provider_name}/{model_name}"},
            message=message,
            next_module="response_optimization" # 下一步优化
        )

    @staticmethod
    def _call_llm_api(provider: str, api_url: str, model: str, messages: list,
                      session_key: str | None = None, # 来自 Flask Session (在任务中通常为None)
                      temp_keys: dict | None = None   # 来自 Celery Task
                     ) -> str:
        # 执行LLM API调用 (核心)
        available_providers = current_app.config.get('AVAILABLE_PROVIDERS', {})
        llm_timeout = current_app.config.get('LLM_REQUEST_TIMEOUT', 120)
        deepseek_key_global = os.environ.get("DEEPSEEK_API_KEY", current_app.config.get("DEEPSEEK_API_KEY"))
        local_key_global = os.environ.get("LOCAL_API_KEY", current_app.config.get("LOCAL_API_KEY"))

        payload = {"model": model, "messages": messages, "stream": False, "temperature": 0.7, "max_tokens": 1500}
        headers = {"Content-Type": "application/json"}
        api_key = None # 初始化 API Key
        provider_config = available_providers.get(provider, {})
        key_required = provider_config.get("key_required", False)

        # --- Key 优先级: Celery Task -> Flask Session -> Global Config ---
        if key_required:
            if temp_keys and provider in temp_keys and temp_keys[provider]: api_key = temp_keys[provider] # 1. 任务Key优先
            elif session_key: api_key = session_key # 2. Session Key次之 (任务中通常无)
            else: # 3. 全局配置Key最后
                if provider == "DeepSeek" and provider_config.get("key_configured"): api_key = deepseek_key_global
                elif provider == "Local" and provider_config.get("key_configured"): api_key = local_key_global
            if not api_key: return f"调用失败: {provider} Key缺失"
            headers["Authorization"] = f"Bearer {api_key}"

        # --- 发送请求与处理响应 ---
        assistant_message = "调用失败: 未知错误"
        try:
            resp = requests.post(api_url, headers=headers, json=payload, timeout=llm_timeout)
            resp.raise_for_status() # 检查HTTP错误
            response_data = resp.json()
            if provider == "DeepSeek": assistant_message = response_data["choices"][0]["message"]["content"].strip()
            elif provider == "Local": assistant_message = response_data.get("message", {}).get("content", "") or response_data.get("response", "") or (response_data["choices"][0]["message"]["content"] if "choices" in response_data and response_data["choices"] else "")
            else: return f"调用失败: 未知提供者 '{provider}'"
            assistant_message = assistant_message.strip() or f"模型返回空内容 ({provider})"
        except requests.Timeout: assistant_message = f"调用超时({llm_timeout}秒)"
        except requests.HTTPError as e: error_body = e.response.text[:100]; assistant_message = f"HTTP {e.response.status_code}: {error_body}"
        except requests.RequestException as e: assistant_message = f"网络异常: {type(e).__name__}"
        except Exception as e: assistant_message = f"处理异常: {type(e).__name__}"; print(e)
        return assistant_message

    @classmethod
    def _get_provider_info(cls, provider, model):
        # 获取Provider配置信息
        config = current_app.config # 直接访问配置
        available = config['AVAILABLE_PROVIDERS']
        default_p = config['DEFAULT_PROVIDER']
        provider_name = provider if provider in available else default_p
        provider_config = available.get(provider_name)
        if not provider_config: return provider_name, None, None # 未找到配置
        models = provider_config.get("models", [])
        model_name = model if model in models else (models[0] if models else None) # 选定或选第一个
        return provider_name, model_name, provider_config.get("url") # 返回名称/模型/URL
