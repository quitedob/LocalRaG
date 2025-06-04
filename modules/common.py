# D:\python_code\LocalAgent\modules\common.py
from dataclasses import dataclass, field # 导入数据类和字段工厂 (Import dataclass and field factory)
from enum import Enum  # 枚举类型 (Enum type)
from typing import List, Dict, Any # 类型注解 (Type hints)

# --- 用户类型枚举 (User Type Enum) ---
class UserType(Enum):
    """ 标识用户的对话意图或状态 (Identifies the user's dialogue intent or state) """
    EXPLORATORY = "探索型"        # 用户想了解知识或自我探索 (User wants to learn or self-explore)
    VENTING = "倾诉型"            # 用户主要表达情绪和经历 (User is mainly expressing emotions/experiences)
    SEEKING_SOLUTIONS = "求助型"  # 用户明确寻求建议或方法 (User is explicitly seeking advice/solutions)
    TESTING = "测试型"            # 用户在试探AI能力或边界 (User is testing the AI's capabilities/boundaries)
    CRISIS = "危机型"            # 用户表达了危机信号 (User expressed crisis signals)
    UNKNOWN = "未知类型"          # 未能明确识别用户类型 (Could not clearly identify user type)

# --- 情感类型枚举 (Emotion Type Enum - 保持简单，具体分析在模块中) ---
class EmotionType(Enum):
    """ 标识用户的主要情感基调 (Identifies the user's main emotional tone) """
    POSITIVE = "积极"      # Positive
    NEGATIVE = "消极"      # Negative
    NEUTRAL = "中性"       # Neutral
    AMBIVALENT = "矛盾"    # Ambivalent / Mixed
    CRISIS = "危机情绪"    # Crisis Emotion (linked to safety)
    UNKNOWN = "未知情绪"   # Unknown

# --- (旧的 DialogueStage 已移除) ---

# --- 对话状态数据类 (Dialogue State Dataclass) ---
@dataclass
class DialogueState:
    """ 存储当前对话的关键状态信息 (Stores key state information for the current dialogue) """
    user_type: UserType = UserType.UNKNOWN            # 当前识别的用户类型 (Currently identified user type)
    user_emotion: EmotionType = EmotionType.UNKNOWN   # 当前识别的用户主要情绪 (Currently identified user's main emotion)
    emotion_intensity: float = 0.5                  # 情绪强度 (0-1) (Emotion intensity)
    detected_keywords: List[str] = field(default_factory=list) # 本轮检测到的重要关键词 (Important keywords detected this turn)
    cognitive_distortions: List[str] = field(default_factory=list) # 本轮识别到的认知扭曲 (Cognitive distortions identified this turn)
    is_crisis: bool = False                           # 当前是否处于危机状态 (Is currently in crisis state)
    session_turn_count: int = 0                       # 当前会话的轮次计数 (Turn count for the current session)
    # context_tokens: int = 0                         # (如果需要精确控制Token数，可以保留) (Keep if precise token control is needed)
    dialogue_goals: List[str] = field(default_factory=list) # (可以用于追踪咨询目标，暂时保留) (Can be used to track consultation goals, kept for now)

# --- 模块输出数据类 (Module Output Dataclass) ---
@dataclass
class ModuleOutput:
    """ 定义模块处理结果的标准结构 (Defines the standard structure for module processing results) """
    success: bool                     # 处理是否成功 (Whether processing was successful)
    data: Dict[str, Any] = field(default_factory=dict) # 处理返回的数据 (Data returned from processing)
    message: str = ""                 # 调试或用户提示信息 (Debug or user-facing message)
    next_module: str | None = None    # 建议的下一个处理模块 (Suggested next processing module) - 用于更灵活的流程控制 (for more flexible flow control)
