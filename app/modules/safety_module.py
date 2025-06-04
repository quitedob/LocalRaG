# 文件路径: D:\python_code\LocalAgent\modules\safety_module.py
from flask import current_app  # 通过 Flask 应用上下文获取配置
from modules.common import ModuleOutput  # 导出统一的模块输出格式
import re  # 正则表达式库，用于匹配危机关键词

class SafetyModule:
    """
    安全检测模块，优先检测用户输入的危机信号。
    """
    # 危机关键词列表，支持多种表达
    CRISIS_KEYWORDS = [
        '自杀', '想死', '活不下去了', '活不了', '不想活', '没意思', '解脱', '结束生命',
        '自残', '割腕', '伤害自己', '了断', '自我了断',
        '绝望', '没希望了', '彻底完了', '放弃了', '撑不住了', '熬不下去了',
        '报复社会', '伤害别人', '杀了他', '弄死他', '同归于尽',
        '救命', '紧急', '帮帮我', '我需要帮助', '危机'
    ]
    # 编译正则表达式，提高匹配效率
    CRISIS_REGEX = re.compile(
        r"\b(?:" + "|".join(re.escape(k) for k in CRISIS_KEYWORDS) + r")\b",
        re.IGNORECASE
    )

    @classmethod
    def check(cls, text: str) -> ModuleOutput:
        """
        检查输入文本是否包含危机关键词。
        如果检测到危机，返回带 hotline 信息的响应；否则，标记通过。
        """
        match = cls.CRISIS_REGEX.search(text)
        if match:
            kw = match.group(0)
            # 从 Flask 配置中获取危机热线信息
            hotline_info = current_app.config.get(
                'CRISIS_HOTLINE_INFO',
                "未配置危机热线信息"
            )
            # 生成标准的危机响应
            crisis_response = f"""
⚠️ **安全警示**：检测到危机词“{kw}”，我非常担心您的安全。

作为 AI 助手，我无法提供实时紧急救助，但您并不孤单。
**紧急时请联系专业人士或使用以下危机热线：**
{hotline_info}

**请不要独自承受，立即寻求帮助。**
""".strip()
            return ModuleOutput(
                success=False,
                data={
                    "crisis": True,
                    "response": crisis_response,
                    "detected_keyword": kw
                },
                message=f"检测到危机词: {kw}",
                next_module="end_conversation"
            )
        # 没有危机关键词，正常通过
        return ModuleOutput(
            success=True,
            data={"crisis": False},
            message="安全检查通过",
            next_module="preprocess"
        )
