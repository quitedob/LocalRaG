# D:\python_code\LocalAgent\modules\user_analyzer_module.py
from .common import ModuleOutput, UserType, EmotionType
import re

class UserAnalyzerModule:
    USER_TYPE_PATTERNS = {
        UserType.EXPLORATORY: re.compile(r'我想了解|是什么|为什么|心理学|知识|概念|区别是', re.IGNORECASE),
        UserType.SEEKING_SOLUTIONS: re.compile(r'怎么办|如何解决|怎样才能|给我建议|需要方法|有办法吗', re.IGNORECASE),
        UserType.TESTING: re.compile(r'你觉得我|你认为|测试一下|你是谁|你能做什么|你的能力', re.IGNORECASE),
    }
    COGNITIVE_DISTORTION_KEYWORDS = {
        "非黑即白": ['必须', '应该', '一定', '要么...要么', '不是...就是', '永远', '从不'],
        "过度概括": ['总是', '老是', '每次都', '所有人都', '谁都', '从来没'],
        "灾难化": ['完蛋了', '没救了', '太可怕了', '世界末日', '万一...怎么办', '受不了'],
        "读心术": ['他肯定觉得', '我知道他想', '他们一定认为'],
        "标签化": ['我就是个(.*?)者', '他是个坏人', '废物', '蠢货'],
        "忽略积极面": ['只是运气', '这不算什么', '侥幸'],
        "情绪推理": ['我感觉.*所以.*'],
    }

    @classmethod
    def analyze(cls, text: str, emotion_type: EmotionType) -> ModuleOutput:
        identified_type = UserType.UNKNOWN
        detected_distortions = []

        for utype, pattern in cls.USER_TYPE_PATTERNS.items():
            if pattern.search(text):
                identified_type = utype
                break

        if identified_type == UserType.UNKNOWN:
             if emotion_type in [EmotionType.NEGATIVE, EmotionType.AMBIVALENT, EmotionType.CRISIS]:
                 identified_type = UserType.VENTING
             else:
                 identified_type = UserType.VENTING

        for distortion_name, keywords in cls.COGNITIVE_DISTORTION_KEYWORDS.items():
             if isinstance(keywords, list):
                 if any(re.search(r'\b' + re.escape(k) + r'\b', text, re.IGNORECASE) for k in keywords):
                       detected_distortions.append(distortion_name)
             elif isinstance(keywords, str):
                  if re.search(keywords, text, re.IGNORECASE):
                      detected_distortions.append(distortion_name)

        return ModuleOutput(
            success=True,
            data={
                "user_type": identified_type,
                "cognitive_distortions": list(set(detected_distortions))
            },
            message=f"用户类型: {identified_type.value}, 认知扭曲: {', '.join(detected_distortions) if detected_distortions else '无'}",
            next_module="context_update"
        )