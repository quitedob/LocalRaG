# D:\python_code\LocalAgent\modules\emotion_analyzer_module.py
from modules.common import ModuleOutput, EmotionType
import re

class EmotionAnalyzerModule:
    """
    （增强版）情感分析模块，使用扩展关键词识别主要情绪。
    (Enhanced) Emotion analysis module, using expanded keywords to identify primary emotions.
    注意：这仍然是基于关键词的简单实现，更精确的分析需要更复杂的模型或API。
    (Note: This is still a simple keyword-based implementation. More accurate analysis requires more complex models or APIs.)
    """
    # 扩展的情感关键词库 (Expanded emotion keyword dictionary)
    EMOTION_KEYWORDS = {
        EmotionType.POSITIVE: ['开心', '高兴', '满意', '喜欢', '棒', '不错', '有希望', '放松', '平静', '自豪', '感恩', '安心'],
        EmotionType.NEGATIVE: [
            # 抑郁相关 (Depression-related)
            '抑郁', '低落', '难过', '悲伤', '沮丧', '没意思', '无助', '空虚', '绝望', '无价值', '自责', '疲惫', '兴趣丧失',
            # 焦虑相关 (Anxiety-related)
            '焦虑', '担心', '害怕', '紧张', '恐惧', '恐慌', '不安', '心慌', '坐立不安', '烦躁', '压力大', '强迫',
            # 愤怒相关 (Anger-related)
            '生气', '愤怒', '火大', '气死了', '不满', '怨恨', '敌意', '挫败',
            # 其他负面 (Other Negative)
            '讨厌', '烦', '痛苦', '后悔', '内疚', '羞耻', '丢脸', '尴尬', '孤独', '失望'
        ],
        EmotionType.AMBIVALENT: ['又爱又恨', '纠结', '矛盾', '说不清', '喜忧参半', '复杂'],
        EmotionType.CRISIS: ['绝望', '想死', '活不下去', '崩溃', '无法承受'] # 与安全模块有重叠，用于情感标记
    }
    # 中性/疑惑类关键词可以放在 UserAnalyzerModule 处理意图 (Neutral/Confused keywords can be handled in UserAnalyzerModule for intent)

    # 编译正则表达式以提高效率 (Compile regex for efficiency)
    EMOTION_REGEX = {
        etype: re.compile(r'\b(?:' + '|'.join(re.escape(k) for k in kws) + r')\b', re.IGNORECASE)
        for etype, kws in EMOTION_KEYWORDS.items()
    }

    @classmethod
    def analyze(cls, text: str) -> ModuleOutput:
        """
        分析文本中的主要情绪。
        (Analyzes the primary emotion in the text.)

        Args:
            text (str): 用户输入文本 (User input text).

        Returns:
            ModuleOutput: 包含识别出的情绪类型和强度（简单估计）。
                          (Contains the identified emotion type and intensity (simple estimate).)
        """
        detected_emotions = {}
        highest_intensity = 0.5 # 基础强度 (Base intensity)
        primary_emotion = EmotionType.NEUTRAL # 默认情绪 (Default emotion)
        detected_keywords = []

        # 检查是否包含危机情绪关键词 (Check for crisis emotion keywords first)
        crisis_match = cls.EMOTION_REGEX[EmotionType.CRISIS].findall(text)
        if crisis_match:
            primary_emotion = EmotionType.CRISIS
            highest_intensity = 1.0
            detected_keywords.extend(crisis_match)
            # 注意：安全模块应该已经处理了危机响应，这里只是标记情绪状态
            # Note: Safety module should have handled the crisis response, this just marks the emotional state
            return ModuleOutput(True,
                                {"emotion_type": primary_emotion, "emotion_intensity": highest_intensity, "keywords": list(set(detected_keywords))},
                                f"情感: {primary_emotion.value} (危机信号)",
                                next_module="user_analysis") # 继续分析用户类型 (Continue to analyze user type)

        # 查找其他情绪关键词 (Find other emotion keywords)
        for etype, regex in cls.EMOTION_REGEX.items():
            if etype == EmotionType.CRISIS: continue # 跳过危机类别 (Skip crisis category here)
            matches = regex.findall(text)
            if matches:
                detected_emotions[etype] = len(matches) # 记录匹配次数 (Record match count)
                detected_keywords.extend(matches)
                # 简单强度估计：次数越多，强度越高 (Simple intensity estimate: more matches = higher intensity)
                intensity = 0.6 + len(matches) * 0.1
                if intensity > highest_intensity:
                    highest_intensity = min(intensity, 1.0) # 强度上限为1 (Cap intensity at 1)
                    primary_emotion = etype

        # 如果同时检测到积极和消极，标记为矛盾 (If both positive and negative detected, mark as ambivalent)
        has_positive = EmotionType.POSITIVE in detected_emotions
        has_negative = EmotionType.NEGATIVE in detected_emotions
        if has_positive and has_negative:
            primary_emotion = EmotionType.AMBIVALENT
            highest_intensity = max(0.7, highest_intensity) # 矛盾情绪强度较高 (Ambivalent emotion has higher intensity)
        elif not detected_emotions and primary_emotion == EmotionType.NEUTRAL:
             # 如果没有任何匹配，保持中性 (If no matches, remain neutral)
             highest_intensity = 0.5


        # 基于标点符号简单调整强度 (Simple intensity adjustment based on punctuation)
        if "！" in text or "!" in text:
            highest_intensity = min(1.0, highest_intensity + 0.1)
        if "..." in text or "。。。" in text:
             highest_intensity = max(0.3, highest_intensity - 0.1) # 省略号可能降低强度 (Ellipsis might lower intensity)

        # 如果没有识别到情绪，则标记为未知 (If no emotion identified, mark as unknown)
        if primary_emotion == EmotionType.NEUTRAL and not detected_emotions:
             primary_emotion = EmotionType.UNKNOWN


        return ModuleOutput(True,
                            {"emotion_type": primary_emotion, "emotion_intensity": round(highest_intensity, 2), "keywords": list(set(detected_keywords))},
                            f"情感: {primary_emotion.value} (强度: {round(highest_intensity, 2)})",
                            next_module="user_analysis") # 指示下一步进行用户类型分析 (Indicate next step is user type analysis)
