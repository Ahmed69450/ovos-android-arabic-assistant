# -*- coding: utf-8 -*-
"""
موزع النوايا (IntentDispatcher) وفق فلسفة OpenVoiceOS
يدير دورة حياة تنفيذ المهارات:
- بث حدث بدء المعالجة (ovos.intent.handler.start)
- تنفيذ المعالج الخاص بالمهارة
- بث حدث اكتمال المعالجة (ovos.intent.handler.complete)
"""

from typing import Callable, Optional
from .message import Message
from .bus import AndroidMessageBus

class IntentDispatcher:
    """مسؤول عن استدعاء معالجات المهارات وإدارة أحداث دورة الحياة"""

    def __init__(self, bus: AndroidMessageBus):
        self.bus = bus

    def dispatch(self, skill_id: str, intent_name: str, message: Message, handler: Callable[[Message], None]) -> bool:
        """
        توجيه وتنفيذ معالج المهارة مع إدارة أحداث البدء والاكتمال
        """
        dispatch_data = {
            "skill_id": skill_id,
            "intent_name": intent_name,
            "utterance": message.data.get("utterance", "")
        }

        # 1. إرسال حدث بدء المعالج (Handler Start)
        self.bus.emit(Message("ovos.intent.handler.start", data=dispatch_data, context=message.context))

        success = True
        try:
            # 2. تنفيذ دالة المهارة المسجلة
            handler(message)
            # 3. إرسال حدث نجاح واكتمال المعالجة
            self.bus.emit(Message("ovos.intent.handler.complete", data=dispatch_data, context=message.context))
        except Exception as e:
            success = False
            error_data = dict(dispatch_data)
            error_data["error"] = str(e)
            print(f"[خطأ أثناء تشغيل مهارة {skill_id}]: {str(e)}")
            self.bus.emit(Message("ovos.intent.handler.error", data=error_data, context=message.context))

        return success
