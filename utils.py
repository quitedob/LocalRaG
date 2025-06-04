# D:\python_code\LocalAgent\utils.py
import os
import json
from flask import session, current_app

FALLBACK_PROMPT = "你是一位友好的AI助手。"

def load_prompt() -> str:
    prompt_file_path = current_app.config.get('PROMPT_FILE_PATH')
    if not prompt_file_path:
        print("[警告] 配置中未找到 PROMPT_FILE_PATH，使用备用提示词。")
        return FALLBACK_PROMPT

    prompt_dir = os.path.dirname(prompt_file_path)
    if prompt_dir and not os.path.exists(prompt_dir):
        try:
            os.makedirs(prompt_dir)
            print(f"创建目录: {prompt_dir}")
        except OSError as e:
            print(f"创建提示词目录失败: {e}")

    if not os.path.exists(prompt_file_path):
        print(f"提示词文件不存在: {prompt_file_path}，将使用备用提示词。")
        return FALLBACK_PROMPT
    try:
        with open(prompt_file_path, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if not content:
                 print(f"提示词文件 {prompt_file_path} 为空，使用备用提示词。")
                 return FALLBACK_PROMPT
            return content
    except OSError as e:
        print(f"读取提示词文件失败: {e}")
        return FALLBACK_PROMPT
    except Exception as e:
        print(f"加载提示词时发生未知错误: {e}")
        return FALLBACK_PROMPT


def load_context_from_file(temp_context: list):
    sid = session.get("session_id")
    context_file = current_app.config.get('CONTEXT_FILE')
    if not sid or not context_file or not os.path.exists(context_file):
        if not context_file: print("[警告] 配置中未找到 CONTEXT_FILE。")
        temp_context.clear()
        return
    try:
        with open(context_file, 'r', encoding='utf-8') as f:
            current_session_lines = []
            for line in f:
                if line.strip():
                    try:
                        data = json.loads(line)
                        if data.get("session_id") == sid:
                            current_session_lines.append(data)
                    except json.JSONDecodeError:
                         print(f"跳过无效的JSON行: {line.strip()}")
            temp_context.clear()
            temp_context.extend(current_session_lines)

    except OSError as e:
        print(f"加载聊天记录文件失败: {e}")
    except Exception as e:
        print(f"加载聊天记录时发生未知错误: {e}")


def save_context_to_file(item: dict):
    context_file = current_app.config.get('CONTEXT_FILE')
    if not context_file:
        print("[错误] 配置中未找到 CONTEXT_FILE，无法保存聊天记录。")
        return
    try:
        with open(context_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
    except OSError as e:
        print(f"保存聊天记录到文件失败: {e}")
    except Exception as e:
        print(f"保存聊天记录时发生未知错误: {e}")


def remove_session_lines_from_file(sid: str):
    context_file = current_app.config.get('CONTEXT_FILE')
    if not context_file or not os.path.exists(context_file):
        if not context_file: print("[警告] 配置中未找到 CONTEXT_FILE，无法清理聊天记录。")
        return
    try:
        kept_lines = []
        with open(context_file, 'r', encoding='utf-8') as f:
            for line in f:
                if not line.strip():
                     continue
                try:
                    obj = json.loads(line)
                    if obj.get("session_id") != sid:
                        kept_lines.append(line.strip())
                except json.JSONDecodeError:
                    print(f"清理时跳过无效JSON行: {line.strip()}")

        with open(context_file, 'w', encoding='utf-8') as f:
            if kept_lines:
                 f.write("\n".join(kept_lines) + "\n")
    except OSError as e:
        print(f"清理聊天记录文件失败: {e}")
    except Exception as e:
        print(f"清理聊天记录时发生未知错误: {e}")