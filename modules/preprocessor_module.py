# modules/preprocessor_module.py
import re  # 正则表达式
import jieba  # 中文分词
from modules.common import ModuleOutput

class PreprocessorModule:
    # 文本预处理模块
    @classmethod
    def process(cls, text: str) -> ModuleOutput:
        try:
            cleaned = re.sub(r'[^\w\s]', '', text.lower())  # 清除标点并转小写
        except re.error as e:
            return ModuleOutput(False, {}, f"正则错误: {e}", ["fallback"])
        try:
            words = list(jieba.cut(cleaned))  # 分词
        except Exception as e:
            return ModuleOutput(False, {}, f"分词错误: {e}", ["fallback"])
        entities = cls._extract_entities(words)
        keywords = cls._extract_keywords(words)
        return ModuleOutput(True, {"cleaned_text": cleaned, "words": words,
                                   "entities": entities, "keywords": keywords},
                            "预处理完成", ["emotion_analysis"])

    @staticmethod
    def _extract_entities(words):
        return [w for w in words if len(w) > 1]  # 简单实体：长度大于1

    @staticmethod
    def _extract_keywords(words):
        stopwords = {"的", "了", "和", "是", "我"}
        return [w for w in words if w not in stopwords]  # 过滤停用词
