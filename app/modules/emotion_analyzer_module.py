# ./app/modules/emotion_analyzer_module.py
# 文件路径: ./app/modules/emotion_analyzer_module.py
from .common import ModuleOutput, EmotionType # 导入所需公共类
import re

class EmotionAnalyzerModule:
    # 情感分析模块 (增强版)
    # 关键词库保持不变
    EMOTION_KEYWORDS = {
        EmotionType.POSITIVE: ['开心', '高兴', '满意', '喜欢', '棒', '不错', '有希望', '放松', '平静', '自豪', '感恩', '安心'],
        EmotionType.NEGATIVE: ['抑郁', '低落', '难过', '悲伤', '沮丧', '没意思', '无助', '空虚', '绝望', '无价值', '自责', '疲惫', '兴趣丧失','焦虑', '担心', '害怕', '紧张', '恐惧', '恐慌', '不安', '心慌', '坐立不安', '烦躁', '压力大', '强迫','生气', '愤怒', '火大', '气死了', '不满', '怨恨', '敌意', '挫败','讨厌', '烦', '痛苦', '后悔', '内疚', '羞耻', '丢脸', '尴尬', '孤独', '失望'],
        EmotionType.AMBIVALENT: ['又爱又恨', '纠结', '矛盾', '说不清', '喜忧参半', '复杂'],
        EmotionType.CRISIS: ['绝望', '想死', '活不下去', '崩溃', '无法承受'] # 与安全模块有重叠
    }
    # 预编译正则
    EMOTION_REGEX = { etype: re.compile(r'\b(?:' + '|'.join(re.escape(k) for k in kws) + r')\b', re.IGNORECASE) for etype, kws in EMOTION_KEYWORDS.items() }

    @classmethod
    def analyze(cls, text: str) -> ModuleOutput:
        # 分析文本主要情绪
        detected_emotions = {}; highest_intensity = 0.5; primary_emotion = EmotionType.NEUTRAL; detected_keywords = []

        # 优先检查危机信号 (与安全模块协同)
        crisis_match = cls.EMOTION_REGEX[EmotionType.CRISIS].findall(text)
        if crisis_match:
            primary_emotion = EmotionType.CRISIS; highest_intensity = 1.0; detected_keywords.extend(crisis_match)
            # 注意：这里仅标记情绪，安全模块负责响应
            return ModuleOutput(True, {"emotion_type": primary_emotion, "emotion_intensity": highest_intensity, "keywords": list(set(detected_keywords))}, f"情感: {primary_emotion.value} (危机信号)", "user_analysis")

        # 检查其他情绪
        for etype, regex in cls.EMOTION_REGEX.items():
            if etype == EmotionType.CRISIS: continue
            matches = regex.findall(text)
            if matches:
                detected_emotions[etype] = len(matches); detected_keywords.extend(matches)
                intensity = 0.6 + len(matches) * 0.1
                if intensity > highest_intensity: highest_intensity = min(intensity, 1.0); primary_emotion = etype

        # 处理矛盾情绪
        has_positive = EmotionType.POSITIVE in detected_emotions
        has_negative = EmotionType.NEGATIVE in detected_emotions
        if has_positive and has_negative:
            primary_emotion = EmotionType.AMBIVALENT; highest_intensity = max(0.7, highest_intensity)
        elif not detected_emotions and primary_emotion == EmotionType.NEUTRAL:
             primary_emotion = EmotionType.UNKNOWN # 无匹配改为未知
             highest_intensity = 0.5

        # 标点调整强度
        if "！" in text or "!" in text: highest_intensity = min(1.0, highest_intensity + 0.1)
        if "..." in text or "。。。" in text: highest_intensity = max(0.3, highest_intensity - 0.1)

        return ModuleOutput(True, {"emotion_type": primary_emotion, "emotion_intensity": round(highest_intensity, 2), "keywords": list(set(detected_keywords))}, f"情感: {primary_emotion.value} ({round(highest_intensity,2)})", "user_analysis")