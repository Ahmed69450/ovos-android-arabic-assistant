# -*- coding: utf-8 -*-
"""
حزمة OVOS المخصصة لنظام أندرويد (OpenVoiceOS Android Adaptation)
توفر نواة معالجة النوايا والموجه والمهارات المحلية باللغة العربية
"""

from .message import Message
from .bus import AndroidMessageBus
from .skill import OVOSSkill, intent_handler
from .nlu_engine import ArabicNLUEngine
from .dispatcher import IntentDispatcher
from .intent_service import IntentService
from .skill_router import SkillRouter

__all__ = [
    "Message",
    "AndroidMessageBus",
    "OVOSSkill",
    "intent_handler",
    "ArabicNLUEngine",
    "IntentDispatcher",
    "IntentService",
    "SkillRouter",
]
