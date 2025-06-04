# ./app/modules/context_manager_module.py
# 文件路径: ./app/modules/context_manager_module.py
import json
from flask import current_app # 导入current_app
from redis import exceptions as redis_exceptions # 导入Redis异常

class ContextManagerModule:
    # Redis上下文管理模块

    @classmethod
    def _get_redis_client(cls):
        # 获取Redis连接实例
        if not hasattr(current_app, 'redis_client') or current_app.redis_client is None:
            raise redis_exceptions.ConnectionError("Redis client not available or not initialized.")
        return current_app.redis_client

    @classmethod
    def _get_history_key(cls, session_id: str) -> str:
        # 生成会话历史Redis Key
        return f"history:{session_id}"

    @classmethod
    def add_message(cls, session_id: str, role: str, content: str):
        # Redis添加消息并截断
        redis = cls._get_redis_client() # 获取客户端
        history_key = cls._get_history_key(session_id) # 生成Key
        max_messages = current_app.config.get('MAX_CONVERSATION_HISTORY_TURNS', 10) * 2
        message_item = json.dumps({"role": role, "content": content}, ensure_ascii=False)

        try:
            pipe = redis.pipeline()
            pipe.rpush(history_key, message_item) # RPUSH: 添加到列表末尾
            pipe.ltrim(history_key, -max_messages, -1) # LTRIM: 保留最新的N条
            pipe.execute() # 执行事务
        except redis_exceptions.ConnectionError as conn_err:
             print(f"[错误][Redis] 添加消息时连接失败: {conn_err}")
             raise # 重新抛出连接错误
        except Exception as e:
            print(f"[错误][Redis] 添加消息到会话 {session_id} 失败: {e}")
            raise # 重新抛出其他异常

    @classmethod
    def get_history(cls, session_id: str) -> list:
        # Redis获取完整历史
        redis = cls._get_redis_client() # 获取客户端
        history_key = cls._get_history_key(session_id) # 生成Key
        try:
            history_json_list = redis.lrange(history_key, 0, -1) # 获取所有
            history = [json.loads(item) for item in history_json_list] # 解析JSON
            return history
        except redis_exceptions.ConnectionError as conn_err:
             print(f"[错误][Redis] 获取历史时连接失败: {conn_err}")
             raise # 重新抛出连接错误
        except Exception as e:
            print(f"[错误][Redis] 获取会话 {session_id} 历史失败: {e}")
            return [] # 其他错误返回空列表

    @classmethod
    def clear_history(cls, session_id: str):
        # Redis删除指定会话历史
        redis = cls._get_redis_client() # 获取客户端
        history_key = cls._get_history_key(session_id) # 生成Key
        try:
            redis.delete(history_key) # DEL: 直接删除Key
        except redis_exceptions.ConnectionError as conn_err:
             print(f"[错误][Redis] 清空历史时连接失败: {conn_err}")
             raise # 重新抛出连接错误
        except Exception as e:
            print(f"[错误][Redis] 删除会话 {session_id} 历史失败: {e}")
            raise # 重新抛出其他异常
