# D:\python_code\LocalAgent\modules\dialogue_pipeline.py
from flask import session
from modules.common import DialogueState, UserType, EmotionType, ModuleOutput
from modules.safety_module import SafetyModule
from modules.preprocessor_module import PreprocessorModule
from modules.emotion_analyzer_module import EmotionAnalyzerModule
from modules.user_analyzer_module import UserAnalyzerModule
from modules.context_manager_module import ContextManagerModule
from modules.response_generator_module import ResponseGeneratorModule
from modules.response_optimizer_module import ResponseOptimizerModule


class DialoguePipeline:
    @classmethod
    def process_input(cls, user_input: str, selected_provider: str | None = None, selected_model: str | None = None, session_id: str | None = None, temp_keys: dict | None = None) -> dict: # Added parameters based on other files
        if not session_id: return cls._prepare_fallback_response(ModuleOutput(False, message="缺少会话ID"), {})

        state = cls._init_or_load_state(session_id)
        outputs = {}

        safe_res = SafetyModule.check(user_input)
        outputs["安全检测输出"] = safe_res.message
        if not safe_res.success:
            print("[流水线] 安全检测失败，启动危机响应流程。")
            state.is_crisis = True
            state.user_type = UserType.CRISIS
            cls._save_state(session_id, state)
            # Assuming _prepare_crisis_response needs state now
            return cls._prepare_crisis_response(safe_res, state)
        else:
            if state.is_crisis:
                state.is_crisis = False
                print("[流水线] 退出危机状态。")


        pre_res = PreprocessorModule.process(user_input)
        outputs["文本预处理输出"] = pre_res.message
        if not pre_res.success:
            print("[流水线] 文本预处理失败。")
            return cls._prepare_fallback_response(pre_res, outputs, session_id)
        cleaned_text = pre_res.data.get("cleaned_text", user_input)
        preprocessed_words = pre_res.data.get("words", [])


        emo_res = EmotionAnalyzerModule.analyze(cleaned_text)
        outputs["情感分析输出"] = emo_res.message
        if emo_res.success:
            state.user_emotion = emo_res.data.get("emotion_type", EmotionType.UNKNOWN)
            state.emotion_intensity = emo_res.data.get("emotion_intensity", 0.5)
            current_keywords = getattr(state, 'detected_keywords', [])
            if not isinstance(current_keywords, list): current_keywords = []
            new_keywords = emo_res.data.get("keywords", [])
            if isinstance(new_keywords, list):
                 current_keywords.extend(new_keywords)
                 state.detected_keywords = list(set(current_keywords))
            else:
                state.detected_keywords = current_keywords
        else:
            print("[流水线] 情感分析失败（非关键错误，继续）。")
            state.user_emotion = EmotionType.UNKNOWN


        user_ana_res = UserAnalyzerModule.analyze(cleaned_text, state.user_emotion)
        outputs["用户分析输出"] = user_ana_res.message
        if user_ana_res.success:
            state.user_type = user_ana_res.data.get("user_type", UserType.UNKNOWN)
            state.cognitive_distortions = user_ana_res.data.get("cognitive_distortions", [])
        else:
             print("[流水线] 用户分析失败（非关键错误，继续）。")
             state.user_type = UserType.UNKNOWN


        # Context management might be handled differently now (e.g., in routes or tasks)
        # Let's assume history needs to be fetched here for response generation
        try:
            # Assuming ContextManagerModule now uses Redis/session_id
            conversation_history = ContextManagerModule.get_history(session_id)
            outputs["上下文管理输出"] = f"获取历史 {len(conversation_history)} 条"
        except Exception as e:
            print(f"[流水线] 获取上下文失败: {e}")
            # Depending on strategy, either return error or proceed without history
            # For now, let's assume we need history for the next step
            return cls._prepare_fallback_response(ModuleOutput(False, message=f"获取历史失败: {e}"), outputs, session_id)


        # Pass necessary parameters to response generator
        resp_gen_res = ResponseGeneratorModule.generate(
            user_input, state, conversation_history,
            selected_provider, selected_model, session_id, temp_keys
        )
        outputs["大模型生成输出"] = resp_gen_res.message
        outputs["模型"] = resp_gen_res.data.get("model_used", "?") # Added from other version
        if not resp_gen_res.success:
            print("[流水线] 大模型生成失败。")
            return cls._prepare_fallback_response(resp_gen_res, outputs, session_id)
        raw_response = resp_gen_res.data.get("raw_response", "抱歉，我暂时无法回应。")


        opt_res = ResponseOptimizerModule.optimize(raw_response, state)
        outputs["回复优化输出"] = opt_res.message
        final_response = raw_response # Default to raw if optimization fails
        if opt_res.success:
             final_response = opt_res.data.get("optimized_response", final_response)
             if opt_res.data.get("thought_content"): outputs["思考链"] = opt_res.data["thought_content"] # Added from other version
        else:
             print("[流水线] 回复优化失败（非关键错误，使用原始回复）。")
             # Try basic cleanup even on failure
             try:
                 thought_content = ""; cleaned_response = raw_response.strip()
                 match = ResponseOptimizerModule.COT_REGEX.search(cleaned_response) # Assume regex is defined in optimizer
                 if match:
                     thought_content = match.group(1).strip()
                     cleaned_response = ResponseOptimizerModule.COT_REGEX.sub('', cleaned_response).strip()
                 if thought_content: outputs["思考链"] = thought_content
                 cleaned_response = ResponseOptimizerModule.RESPONSE_START_TAG_REGEX.sub('', cleaned_response).strip() # Assume regex is defined
                 cleaned_response = ResponseOptimizerModule.RESPONSE_END_TAG_REGEX.sub('', cleaned_response).strip() # Assume regex is defined
                 final_response = cleaned_response.replace("\n", "<br>").strip()
             except Exception as e_clean:
                 print(f"清理标签出错: {e_clean}")
                 final_response = raw_response.replace("\n", "<br>").strip()


        state.session_turn_count += 1
        cls._save_state(session_id, state)

        state_dict = cls._get_state_dict(state)
        outputs["会话报告输出"] = f"轮次:{state_dict.get('session_turn_count')}, 类型:{state_dict.get('user_type')}, 情绪:{state_dict.get('user_emotion')}"
        return {
            "success": True,
            "response": final_response,
            "state": state_dict,
            "outputs": outputs
        }

    @staticmethod
    def _init_or_load_state(session_id: str) -> DialogueState:
        state_key = f"dialogue_state_{session_id}"
        if state_key in session:
            try:
                d = session[state_key]
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
                 print(f"[警告] 加载会话 {session_id} 状态失败: {e}, 将使用默认状态。")
        return DialogueState()

    @staticmethod
    def _save_state(session_id: str, state: DialogueState):
        state_key = f"dialogue_state_{session_id}"
        try:
            session[state_key] = cls._get_state_dict(state)
            session.modified = True
        except Exception as e:
            print(f"[错误] 保存状态到 Session 失败: {e}")


    @staticmethod
    def _get_state_dict(state: DialogueState) -> dict:
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

    @staticmethod
    def _prepare_crisis_response(safe_res: ModuleOutput, state: DialogueState) -> dict:
        state_dict = cls._get_state_dict(state)
        return {
            "success": False,
            "response": safe_res.data.get("response", "检测到危机，请寻求帮助。"),
            "state": state_dict,
            "outputs": {"安全检测输出": safe_res.message, "响应": "危机处理流程"}
        }

    @staticmethod
    def _prepare_fallback_response(fail_res: ModuleOutput, outputs: dict, session_id: str | None) -> dict:
        fallback_msg = "抱歉，处理时遇到问题，请稍后再试。"
        outputs["错误"] = f"失败: {fail_res.message}"
        current_state_dict = {}
        if session_id:
            try: current_state_dict = cls._get_state_dict(cls._init_or_load_state(session_id))
            except Exception as e: print(f"获取状态失败: {e}")
        return {
            "success": False,
            "response": fallback_msg,
            "state": current_state_dict,
            "outputs": outputs
         }