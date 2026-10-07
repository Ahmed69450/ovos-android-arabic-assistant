# -*- coding: utf-8 -*-
"""
صنف الأساس للمهارات (OVOSSkill) ومزخرف النوايا (intent_handler)
مبني وفق معايير OpenVoiceOS لتسهيل بناء مهارات صوتية عربية قابلة للتوسع
"""

import functools
from typing import Any, Callable, Dict, List, Optional
from .message import Message
from .bus import AndroidMessageBus

def intent_handler(intent_name: str):
    """
    مزخرف (Decorator) لربط دوال المهارة بنية معينة
    مثال:
        @intent_handler('greeting_skill')
        def handle_greeting(self, message):
            self.speak("أهلاً وسهلاً بك!")
    """
    def decorator(func: Callable):
        setattr(func, "_ovos_intent_name", intent_name)
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        setattr(wrapper, "_ovos_intent_name", intent_name)
        return wrapper
    return decorator


class OVOSSkill:
    """صنف المهارة الأساسي المتوافق مع OpenVoiceOS Workshop لنظام أندرويد"""

    def __init__(self, skill_id: str, bus: AndroidMessageBus):
        self.skill_id = skill_id
        self.bus = bus
        self._intent_handlers: Dict[str, Callable[[Message], None]] = {}
        self._last_spoken_response: Optional[str] = None
        self._bind_decorated_handlers()

    def _bind_decorated_handlers(self) -> None:
        """اكتشاف تلقائي للدوال المزخرفة بـ @intent_handler وتسجيلها"""
        for attr_name in dir(self):
            attr_val = getattr(self, attr_name)
            if callable(attr_val) and hasattr(attr_val, "_ovos_intent_name"):
                intent_name = getattr(attr_val, "_ovos_intent_name")
                self.register_intent(intent_name, attr_val)

    def register_intent(self, intent_name: str, handler: Callable[[Message], None]) -> None:
        """تسجيل معالج لنية محددة في المهارة وربطه بناقل الرسائل"""
        self._intent_handlers[intent_name] = handler
        # حدث تشغيل المعالج الخاص بهذه المهارة وفق معايير OVOS: <skill_id>:<intent_name>
        event_name = f"{self.skill_id}:{intent_name}"
        self.bus.on(event_name, handler)

    def speak(self, utterance: str, data: Optional[Dict[str, Any]] = None) -> None:
        """
        إرسال النص إلى محرك تحويل النص إلى كلام (TTS) في أندرويد
        يقوم ببث حدث 'speak' عبر ناقل الرسائل
        """
        self._last_spoken_response = utterance
        msg = Message("speak", data={"utterance": utterance, "skill_id": self.skill_id})
        self.bus.emit(msg)

    def get_last_response(self) -> Optional[str]:
        """الحصول على آخر رد نصي تم توليده بواسطة هذه المهارة"""
        return self._last_spoken_response

    def initialize(self) -> None:
        """دورة حياة المهارة: تهيئة الموارد عند التشغيل (يتم تجاوزه عند الحاجة)"""
        pass

    def shutdown(self) -> None:
        """دورة حياة المهارة: تحرير الموارد عند إغلاق التطبيق"""
        pass
