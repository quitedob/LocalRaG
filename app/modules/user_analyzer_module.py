# D:\python_code\LocalAgent\modules\user_analyzer_module.py
# 文件路径: ./app/modules/user_analyzer_module.py
# --- 修正导入：确保导入了所有需要的类型 ---
from .common import ModuleOutput, UserType, EmotionType # 使用相对导入，并确保导入 EmotionType
import re

class UserAnalyzerModule:
    # 用户意图/认知分析
    USER_TYPE_PATTERNS = { # 意图正则
        UserType.EXPLORATORY: re.compile(r'我想了解|是什么|为什么|心理学|知识|概念|区别是', re.IGNORECASE),
        UserType.SEEKING_SOLUTIONS: re.compile(r'怎么办|如何解决|怎样才能|给我建议|需要方法|有办法吗', re.IGNORECASE),
        UserType.TESTING: re.compile(r'你觉得我|你认为|测试一下|你是谁|你能做什么|你的能力', re.IGNORECASE),
    }
    COGNITIVE_DISTORTION_KEYWORDS = { # 认知扭曲关键词
        "非黑即白": ['必须', '应该', '一定', '要么...要么', '不是...就是', '永远', '从不'],
        "过度概括": ['总是', '老是', '每次都', '所有人都', '谁都', '从来没'],
        "灾难化": ['完蛋了', '没救了', '太可怕了', '世界末日', '万一...怎么办', '受不了'],
        "读心术": ['他肯定觉得', '我知道他想', '他们一定认为'],
        "标签化": ['我就是个(.*?)者', '他是个坏人', '废物', '蠢货'], # 使用简单正则匹配
        "忽略积极面": ['只是运气', '这不算什么', '侥幸'],
        "情绪推理": ['我感觉.*所以.*'], # 使用简单正则匹配
    }

    @classmethod
    def analyze(cls, text: str, emotion_type: EmotionType) -> ModuleOutput:
        # 分析用户意图与认知扭曲
        identified_type = UserType.UNKNOWN; detected_distortions = []

        # 1. 匹配特定意图
        for utype, pattern in cls.USER_TYPE_PATTERNS.items():
            if pattern.search(text): identified_type = utype; break

        # 2. 根据情感判断倾诉 (若无特定意图)
        if identified_type == UserType.UNKNOWN:
             if emotion_type in [EmotionType.NEGATIVE, EmotionType.AMBIVALENT, EmotionType.CRISIS]: identified_type = UserType.VENTING # 负面->倾诉
             else: identified_type = UserType.VENTING # 其他暂定为倾诉

        # 3. 识别认知扭曲
        for name, kws in cls.COGNITIVE_DISTORTION_KEYWORDS.items():
            if isinstance(kws, list): # 关键词列表
                if any(re.search(r'\b' + re.escape(k) + r'\b', text, re.IGNORECASE) for k in kws): detected_distortions.append(name)
            elif isinstance(kws, str): # 正则表达式
                 if re.search(kws, text, re.IGNORECASE): detected_distortions.append(name)

        return ModuleOutput(
            success=True,
            data={"user_type": identified_type, "cognitive_distortions": list(set(detected_distortions))}, # 去重
            message=f"类型:{identified_type.value}, 扭曲:{', '.join(detected_distortions) or '无'}",
            next_module=None # Pipeline 决定下一步
        )
