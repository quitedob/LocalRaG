# D:\python_code\LocalAgent\modules\safety_module.py
from flask import current_app
from modules.common import ModuleOutput
import re

class SafetyModule:
    CRISIS_KEYWORDS = [
        '自杀', '想死', '活不下去了?', '活不了', '不想活', '没意思', '解脱', '结束生命',
        '自残', '割腕', '伤害自己?', '了断', '自我了断', '报复社会', '伤害别人', '杀了他', '弄死他',
        '同归于尽', '绝望', '没希望了?', '崩溃', '无法承受', '救命', '紧急', '帮帮我'
    ]
    CRISIS_REGEX = re.compile(r'\b(?:' + '|'.join(re.escape(k.replace('?', '')) for k in CRISIS_KEYWORDS) + r')\b', re.IGNORECASE)

    @classmethod
    def check(cls, text: str) -> ModuleOutput:
        match = cls.CRISIS_REGEX.search(text)
        if match:
            detected_keyword = match.group(0)
            print(f"[安全模块] 检测到危机关键词: {detected_keyword}")

            try:
                hotline_info = current_app.config.get('CRISIS_HOTLINE_INFO', "未配置危机热线信息")
            except RuntimeError:
                 hotline_info = "无法获取危机热线信息 (无应用上下文)"
                 print("[警告] SafetyModule.check 在没有 Flask 应用上下文的情况下被调用。")

            crisis_response_template = f"""
⚠️ **安全警示**：我注意到您提到了可能与伤害自己或他人相关的想法或内容。我现在非常担心您的安全。

作为一个AI助手，我无法提供实时的紧急救助，但请知道您不是一个人在面对这些困难。**您的安全是最重要的。**

**如果您正处于危机中或需要立即获得支持，请务必联系专业的危机干预资源。** 以下是一些您可以联系的途径：
{hotline_info}

**请不要独自承受，立刻寻求帮助。** 如果您身边有信任的家人、朋友或专业人士（如医生、老师），也请告诉他们您现在的情况。他们会支持您的。
"""
            return ModuleOutput(
                success=False,
                data={"crisis": True, "response": crisis_response_template.strip(), "detected_keyword": detected_keyword},
                message=f"检测到危机关键词: {detected_keyword}",
                next_module="end_conversation"
            )
        else:
            return ModuleOutput(
                success=True,
                data={"crisis": False},
                message="安全检查通过",
                next_module="preprocess"
            )