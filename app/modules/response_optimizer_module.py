# D:\python_code\LocalAgent\modules\response_optimizer_module.py
# 文件路径: ./app/modules/response_optimizer_module.py
from .common import ModuleOutput, DialogueState
import re

class ResponseOptimizerModule:
    # 回复优化模块
    COT_REGEX = re.compile(r"\s*\[思考\](.*?)\[/思考\]\s*", re.DOTALL | re.IGNORECASE) # 思考标签正则
    RESPONSE_START_TAG_REGEX = re.compile(r"^\s*\[回应\]\s*", re.IGNORECASE) # 开始回应标签
    RESPONSE_END_TAG_REGEX = re.compile(r"\s*\[/回应\]\s*$", re.IGNORECASE) # 结束回应标签

    @classmethod
    def optimize(cls, raw_response: str, state: DialogueState) -> ModuleOutput:
        # 优化原始LLM回复
        thought_content = ""; optimized_response = raw_response.strip()

        # 1. 提取并移除思考块
        match = cls.COT_REGEX.search(optimized_response)
        if match:
            thought_content = match.group(1).strip() # 提取思考内容
            optimized_response = cls.COT_REGEX.sub('', optimized_response).strip() # 移除思考块
        # else: print("[优化] 未找到思考标记")

        # 2. 移除回应标签
        optimized_response = cls.RESPONSE_START_TAG_REGEX.sub('', optimized_response).strip()
        optimized_response = cls.RESPONSE_END_TAG_REGEX.sub('', optimized_response).strip()

        # 3. 格式化 (换行转<br>)
        final_reply = optimized_response.replace("\n", "<br>").strip()

        # 4. 检查是否为空
        if not final_reply and not thought_content: final_reply = "抱歉，未能生成有效回复。" # 都为空则提示

        return ModuleOutput(
            success=True,
            data={"optimized_response": final_reply, "thought_content": thought_content},
            message="优化完成" + (", 提取到思考" if thought_content else ", 未找到思考"),
            next_module="finalize_response" # 结束标志
        )
