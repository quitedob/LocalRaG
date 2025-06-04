# D:\python_code\LocalAgent\modules\response_optimizer_module.py
from modules.common import ModuleOutput, DialogueState

class ResponseOptimizerModule:
    """
    回复优化模块 - 主要负责格式化和最终检查。
    (Response optimization module - mainly handles formatting and final checks.)
    """
    @classmethod
    def optimize(cls, raw_response: str, state: DialogueState) -> ModuleOutput:
        """
        对原始回复进行格式化或微调。
        (Formats or fine-tunes the raw response.)

        Args:
            raw_response (str): 从LLM获取的原始回复 (Raw response from LLM).
            state (DialogueState): 当前对话状态 (Current dialogue state).

        Returns:
            ModuleOutput: 包含优化后的回复。 (Contains the optimized response.)
        """
        optimized_response = raw_response

        # 1. 移除可能的内部指令或标记 (Remove possible internal instructions or markers)
        #    (如果 response_generator 中添加了内部指令，这里需要清理)
        #    (If internal instructions were added in response_generator, clean them here)
        #    Example: optimized_response = re.sub(r"\[内部指令\].*?\n?", "", optimized_response)

        # 2. 格式化 (例如，替换换行符为HTML换行) (Formatting, e.g., replace newlines with HTML breaks)
        final_reply = optimized_response.replace("\n", "<br>").strip()

        # 3. (可选) 根据用户类型或情绪添加固定短语 (Optional: Add fixed phrases based on user type or emotion)
        #    (可以取消注释或移除，因为Prompt可能已处理好语气)
        #    (Can uncomment or remove, as the prompt might handle the tone well)
        # if state.user_emotion == EmotionType.NEGATIVE and not final_reply.startswith("非常抱歉"):
        #     final_reply = "听到你这样说，我感到很难过。" + final_reply # 换个更共情的开头 (Use a more empathetic opening)
        # elif state.user_emotion == EmotionType.AMBIVALENT:
        #     final_reply = "听起来你的心情很复杂，" + final_reply

        # 4. 最终安全检查 (Final safety check - 确保没有意外的危机词汇)
        #    (这可以是一个简化的检查，或调用 SafetyModule 的检查逻辑)
        #    (This could be a simplified check or call SafetyModule's logic)
        #    if contains_crisis_keywords(final_reply):
        #        print("[警告] 优化后的回复中仍检测到危机词汇，进行屏蔽或替换！")
        #        final_reply = "抱歉，我无法生成包含潜在风险内容的回应。请注意安全并寻求专业帮助。"


        return ModuleOutput(
            success=True,
            data={"optimized_response": final_reply, "original_response": raw_response},
            message="优化完成",
            next_module="finalize_response" # 指示流程结束 (Indicates end of flow)
        )
