# D:\python_code\LocalAgent\modules\emotion_analyzer_module.py
# 文件路径: ./app/modules/emotion_analyzer_module.py
from .common import ModuleOutput, EmotionType # 确保导入 EmotionType
import re

class EmotionAnalyzerModule:
    # 情感分析模块
    EMOTION_KEYWORDS = { # 情感关键词库
        EmotionType.POSITIVE: ['开心', '高兴', '满意', '喜欢', '棒', '不错', '有希望', '放松', '平静', '自豪', '感恩', '安心'],
        EmotionType.NEGATIVE: [
            '抑郁', '低落', '难过', '悲伤', '沮丧', '没意思', '无助', '空虚', '绝望', '无价值', '自责', '疲惫', '兴趣丧失',
            '焦虑', '担心', '害怕', '紧张', '恐惧', '恐慌', '不安', '心慌', '坐立不安', '烦躁', '压力大', '强迫',
            '生气', '愤怒', '火大', '气死了', '不满', '怨恨', '敌意', '挫败',
            '讨厌', '烦', '痛苦', '后悔', '内疚', '羞耻', '丢脸', '尴尬', '孤独', '失望'
        ],
        EmotionType.AMBIVALENT: ['又爱又恨', '纠结', '矛盾', '说不清', '喜忧参半', '复杂'],
        EmotionType.CRISIS: ['绝望', '想死', '活不下去', '崩溃', '无法承受'] # 与安全模块有重叠
    }
    EMOTION_REGEX = { etype: re.compile(r'\b(?:' + '|'.join(re.escape(k) for k in kws) + r')\b', re.IGNORECASE) for etype, kws in EMOTION_KEYWORDS.items() }

    @classmethod
    def analyze(cls, text: str) -> ModuleOutput:
        # 分析文本主要情绪
        detected_emotions = {}; highest_intensity = 0.5; primary_emotion = EmotionType.NEUTRAL; detected_keywords = []
        crisis_match = cls.EMOTION_REGEX[EmotionType.CRISIS].findall(text)
        if crisis_match: # 优先检查危机
            primary_emotion = EmotionType.CRISIS; highest_intensity = 1.0; detected_keywords.extend(crisis_match)
            return ModuleOutput(True, {"emotion_type": primary_emotion, "emotion_intensity": highest_intensity, "keywords": list(set(detected_keywords))}, f"情感: {primary_emotion.value} (危机信号)", "user_analysis")

        for etype, regex in cls.EMOTION_REGEX.items(): # 查找其他情绪
            if etype == EmotionType.CRISIS: continue
            matches = regex.findall(text)
            if matches:
                detected_emotions[etype] = len(matches); detected_keywords.extend(matches)
                intensity = 0.6 + len(matches) * 0.1
                if intensity > highest_intensity: highest_intensity = min(intensity, 1.0); primary_emotion = etype

        if EmotionType.POSITIVE in detected_emotions and EmotionType.NEGATIVE in detected_emotions: # 处理矛盾情绪
            primary_emotion = EmotionType.AMBIVALENT; highest_intensity = max(0.7, highest_intensity)
        elif not detected_emotions and primary_emotion == EmotionType.NEUTRAL: # 未检测到则未知
             primary_emotion = EmotionType.UNKNOWN; highest_intensity = 0.5

        # 标点调整强度 (可选)
        if "！" in text or "!" in text: highest_intensity = min(1.0, highest_intensity + 0.1)
        if "..." in text or "。。。" in text: highest_intensity = max(0.3, highest_intensity - 0.1)

        # if primary_emotion == EmotionType.NEUTRAL and not detected_emotions: primary_emotion = EmotionType.UNKNOWN # 再次确认

        return ModuleOutput(True, {"emotion_type": primary_emotion, "emotion_intensity": round(highest_intensity, 2), "keywords": list(set(detected_keywords))}, f"情感: {primary_emotion.value} (强度: {round(highest_intensity, 2)})", "user_analysis")
