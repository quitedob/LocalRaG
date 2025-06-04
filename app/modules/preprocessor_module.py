# modules/preprocessor_module.py
# 文件路径: ./app/modules/preprocessor_module.py
import re  # 正则表达式
import jieba  # 中文分词
from .common import ModuleOutput # 相对导入

class PreprocessorModule:
    # 文本预处理模块
    @classmethod
    def process(cls, text: str) -> ModuleOutput:
        # 执行文本预处理
        try:
            # 清理：移除特殊字符（保留字母、数字、空格、中文字符），转小写，去首尾空格
            cleaned = re.sub(r'[^\w\s\u4e00-\u9fff]', '', text.lower()).strip()
        except re.error as e:
            print(f"[预处理] 正则清理错误: {e}")
            return ModuleOutput(False, {}, f"正则错误: {e}")
        except Exception as e_clean:
             print(f"[预处理] 清理时发生未知错误: {e_clean}")
             cleaned = text # 保留原始文本

        try:
            words = list(jieba.cut(cleaned))  # 分词
        except Exception as e:
            print(f"[预处理] 分词错误: {e}")
            words = [cleaned] # 分词失败用清理后文本

        # entities = cls._extract_entities(words) # 可选实体提取
        # keywords = cls._extract_keywords(words) # 可选关键词提取

        return ModuleOutput(
            success=True,
            data={"cleaned_text": cleaned, "words": words}, #, "entities": entities, "keywords": keywords},
            message="预处理完成",
            next_module="emotion_analysis" # 下一步情感分析
        )

    # @staticmethod
    # def _extract_entities(words):
    #     # 简单实体提取示例：长度大于1的词
    #     return [w for w in words if len(w) > 1]

    # @staticmethod
    # def _extract_keywords(words):
    #     # 简单关键词提取示例：过滤停用词
    #     stopwords = {"的", "了", "和", "是", "我", "你", "他", "她", "它", "们", "这", "那", "在", "吗", "呢", "吧"}
    #     return [w for w in words if w not in stopwords and len(w) > 0]
