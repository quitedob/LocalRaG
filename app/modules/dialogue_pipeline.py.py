# ./app/modules/dialogue_pipeline.py
# 文件路径: ./app/modules/dialogue_pipeline.py
from flask import current_app, session # 导入 current_app 和 session (用于状态管理)
# 导入所需模块和类型
from .common import DialogueState, UserType, EmotionType, ModuleOutput
from .safety_module import SafetyModule
from .preprocessor_module import PreprocessorModule
from .emotion_analyzer_module import EmotionAnalyzerModule
from .user_analyzer_module import UserAnalyzerModule # 导入用户分析
from .context_manager_module import ContextManagerModule # Redis上下文
from .response_generator_module import ResponseGeneratorModule
from .response_optimizer_module import ResponseOptimizerModule
from ..utils import load_prompt # 导入加载提示词函数
from redis import exceptions as redis_exceptions # 导入 Redis 异常
import re

class DialoguePipeline:
    # 对话流水线协调器

    @classmethod
    def process_input(cls, user_input: str,
                      selected_provider: str | None = None, selected_model: str | None = None,
                      session_id: str | None = None, # 新增: 会话ID
                      temp_keys: dict | None = None   # 新增: 临时API Keys
                     ) -> dict:
        # 处理用户输入的完整流程
        if not session_id: return cls._prepare_fallback_response(ModuleOutput(False, message="缺少会话ID"), {})

        # 1. 初始化/加载状态 (从 Flask Session)
        state = cls._init_or_load_state(session_id)
        outputs = {} # 存储各模块输出信息

        # --- 流水线开始 ---

        # 2. 安全检测
        safe_res = SafetyModule.check(user_input)
        outputs["安全"] = safe_res.message
        if not safe_res.success: # 检测到危机
            print("[流水线] 安全检测失败，启动危机响应。")
            state.is_crisis = True; state.user_type = UserType.CRISIS
            cls._save_state(session_id, state) # 更新状态到Session
            return cls._prepare_crisis_response(safe_res, state) # 返回危机响应
        else: # 确保如果之前是危机状态，现在恢复正常
            if state.is_crisis:
                state.is_crisis = False
                print("[流水线] 退出危机状态。")

        # 3. 文本预处理
        pre_res = PreprocessorModule.process(user_input)
        outputs["预处理"] = pre_res.message
        if not pre_res.success: return cls._prepare_fallback_response(pre_res, outputs)
        cleaned_text = pre_res.data.get("cleaned_text", user_input) # 获取清理后文本

        # 4. 情感分析
        emo_res = EmotionAnalyzerModule.analyze(cleaned_text)
        outputs["情感"] = emo_res.message
        if emo_res.success: # 更新状态
            state.user_emotion = emo_res.data.get("emotion_type", EmotionType.UNKNOWN)
            state.emotion_intensity = emo_res.data.get("emotion_intensity", 0.5)
            # 合并关键词 (去重)
            current_keywords = getattr(state, 'detected_keywords', [])
            if not isinstance(current_keywords, list): current_keywords = []
            new_keywords = emo_res.data.get("keywords", [])
            if isinstance(new_keywords, list):
                current_keywords.extend(new_keywords)
                state.detected_keywords = list(set(current_keywords))
            else:
                state.detected_keywords = current_keywords
        else: state.user_emotion = EmotionType.UNKNOWN # 失败则未知

        # 5. 用户分析 (意图与认知扭曲)
        user_ana_res = UserAnalyzerModule.analyze(cleaned_text, state.user_emotion)
        outputs["用户"] = user_ana_res.message
        if user_ana_res.success: # 更新状态
            state.user_type = user_ana_res.data.get("user_type", UserType.UNKNOWN)
            state.cognitive_distortions = user_ana_res.data.get("cognitive_distortions", [])
        else: state.user_type = UserType.UNKNOWN # 失败则未知

        # 6. 获取对话历史 (从 Redis)
        # 注意：此时获取的历史应包含当前用户输入（由路由添加）
        redis_available = hasattr(current_app, 'redis_client') and current_app.redis_client is not None
        conversation_history = []
        if redis_available:
            try:
                conversation_history = ContextManagerModule.get_history(session_id)
                outputs["历史"] = f"获取 {len(conversation_history)} 条"
            except redis_exceptions.ConnectionError as e:
                 print(f"获取历史时 Redis 连接失败: {e}")
                 outputs["历史"] = "连接失败"
                 # 抛出或返回错误，让调用者处理
                 return cls._prepare_fallback_response(ModuleOutput(False, message="会话存储服务连接失败"), outputs)
            except Exception as e:
                 print(f"获取历史失败: {e}")
                 outputs["历史"] = "获取失败"
                 # 根据策略决定是否继续，这里假设无历史也可继续
        else:
            outputs["历史"] = "服务不可用"
            return cls._prepare_fallback_response(ModuleOutput(False, message="会话存储服务不可用"), outputs)


        # 7. 大模型生成回复 (传递 session_id 和 temp_keys)
        resp_gen_res = ResponseGeneratorModule.generate(
            user_input=user_input, # 虽然历史里有，为清晰明确传递
            state=state,
            history=conversation_history, # 传递获取到的历史
            selected_provider=selected_provider,
            selected_model=selected_model,
            session_id=session_id, # 传递 session_id
            temp_keys=temp_keys # 传递 临时 Keys
        )
        outputs["生成"] = resp_gen_res.message
        outputs["模型"] = resp_gen_res.data.get("model_used", "?") # 记录使用模型
        if not resp_gen_res.success: return cls._prepare_fallback_response(resp_gen_res, outputs)
        raw_response = resp_gen_res.data.get("raw_response", "抱歉，无法回应。") # 获取原始回复

        # 8. 回复优化 (处理CoT等)
        opt_res = ResponseOptimizerModule.optimize(raw_response, state)
        outputs["优化"] = opt_res.message
        final_response = raw_response # 默认原始回复
        if opt_res.success:
            final_response = opt_res.data.get("optimized_response", final_response) # 最终回复
            if opt_res.data.get("thought_content"): outputs["思考链"] = opt_res.data["thought_content"] # 记录思考链
        else: # 优化失败也尝试清理标签
            print("[流水线] 回复优化失败，尝试清理标签。")
            try:
                thought_content = ""; cleaned_response = raw_response.strip()
                match = ResponseOptimizerModule.COT_REGEX.search(cleaned_response)
                if match:
                    thought_content = match.group(1).strip()
                    cleaned_response = ResponseOptimizerModule.COT_REGEX.sub('', cleaned_response).strip()
                    if thought_content: outputs["思考链"] = thought_content
                cleaned_response = ResponseOptimizerModule.RESPONSE_START_TAG_REGEX.sub('', cleaned_response).strip()
                cleaned_response = ResponseOptimizerModule.RESPONSE_END_TAG_REGEX.sub('', cleaned_response).strip()
                final_response = cleaned_response.replace("\n", "<br>").strip()
            except Exception as e_clean:
                print(f"清理标签出错: {e_clean}")
                final_response = raw_response.replace("\n", "<br>").strip() # 保险起见，只做换行处理

        # 9. 更新状态计数并保存 (到 Flask Session)
        state.session_turn_count += 1
        cls._save_state(session_id, state) # 保存最终状态

        # 10. 准备最终返回结果
        state_dict = cls._get_state_dict(state) # 获取状态字典
        outputs["会话报告"] = f"轮次:{state_dict.get('session_turn_count')}, 类型:{state_dict.get('user_type')}, 情绪:{state_dict.get('user_emotion')}"
        return {
            "success": True,
            "response": final_response, # 最终优化后的回复
            "state": state_dict, # 最终状态字典
            "outputs": outputs # 各模块输出信息
        }

    # --- 辅助方法 ---
    @classmethod
    def _init_or_load_state(cls, session_id: str) -> DialogueState:
        # 从Flask Session加载状态
        state_key = f"dialogue_state_{session_id}" # 每个会话独立的状态Key
        if state_key in session:
            try:
                d = session[state_key] # 从 Session 加载字典
                # 从字典安全地重建 DialogueState 对象
                return DialogueState(
                    user_type=UserType(d.get("user_type", UserType.UNKNOWN.value)),
                    user_emotion=EmotionType(d.get("user_emotion", EmotionType.UNKNOWN.value)),
                    emotion_intensity=float(d.get("emotion_intensity", 0.5)),
                    detected_keywords=list(d.get("detected_keywords", [])),
                    cognitive_distortions=list(d.get("cognitive_distortions", [])),
                    is_crisis=bool(d.get("is_crisis", False)),
                    session_turn_count=int(d.get("session_turn_count", 0)),
                    dialogue_goals=list(d.get("dialogue_goals", []))
                )
            except (ValueError, TypeError, KeyError, AttributeError) as e:
                 print(f"[警告] 加载会话 {session_id} 状态失败: {e}, 使用默认状态。")
        return DialogueState() # 不存在或加载失败，返回新实例

    @classmethod
    def _save_state(cls, session_id: str, state: DialogueState):
        # 保存状态到Flask Session
        state_key = f"dialogue_state_{session_id}"
        try:
            session[state_key] = cls._get_state_dict(state) # 保存为字典
            session.modified = True # 确保 Session 被保存
        except Exception as e:
            print(f"[错误] 保存状态到 Session 失败: {e}")


    @classmethod
    def _get_state_dict(cls, state: DialogueState) -> dict:
        # 将状态对象转为字典
        if not isinstance(state, DialogueState): return {"error": "Invalid state"}
        return {
            "user_type": getattr(state.user_type, 'value', UserType.UNKNOWN.value),
            "user_emotion": getattr(state.user_emotion, 'value', EmotionType.UNKNOWN.value),
            "emotion_intensity": getattr(state, 'emotion_intensity', 0.5),
            "detected_keywords": getattr(state, 'detected_keywords', []),
            "cognitive_distortions": getattr(state, 'cognitive_distortions', []),
            "is_crisis": getattr(state, 'is_crisis', False),
            "session_turn_count": getattr(state, 'session_turn_count', 0),
            "dialogue_goals": getattr(state, 'dialogue_goals', [])
         }

    @classmethod
    def _prepare_crisis_response(cls, safe_res: ModuleOutput, state: DialogueState) -> dict:
        # 准备危机响应字典
        state_dict = cls._get_state_dict(state) # 获取当前状态字典
        return {
            "success": False, # 标记处理失败（中断）
            "response": safe_res.data.get("response", "检测到危机，请寻求帮助。"), # 标准危机回复
            "state": state_dict, # 返回更新后的危机状态
            "outputs": {"安全": safe_res.message, "响应": "危机处理流程"}
        }

    @classmethod
    def _prepare_fallback_response(cls, fail_res: ModuleOutput, outputs: dict) -> dict:
        # 准备模块失败的回退响应
        fallback_msg = "抱歉，处理时遇到问题，请稍后再试。"
        outputs["错误"] = f"失败: {fail_res.message}" # 记录失败信息
        # 尝试获取当前状态，失败则为空字典
        current_state_dict = {}
        if 'session_id' in session: # 确保 session_id 存在
            try: current_state_dict = cls._get_state_dict(cls._init_or_load_state(session['session_id']))
            except Exception as e: print(f"获取状态失败: {e}")
        return {
            "success": False, # 标记处理失败
            "response": fallback_msg, # 通用回退消息
            "state": current_state_dict, # 返回当前状态
            "outputs": outputs
        }
