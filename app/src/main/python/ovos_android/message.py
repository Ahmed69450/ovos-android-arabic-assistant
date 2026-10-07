# -*- coding: utf-8 -*-
"""
تمثيل كائن الرسالة (Message) وفق معايير OpenVoiceOS
يُستخدم لتبادل الأحداث والبيانات بين موجه النوايا والمهارات عبر ناقل الرسائل
"""

import json
from typing import Any, Dict, Optional

class Message:
    """كائن الرسالة المتوافق مع ovos_bus_client.message.Message"""

    def __init__(self, msg_type: str, data: Optional[Dict[str, Any]] = None, context: Optional[Dict[str, Any]] = None):
        self.msg_type = msg_type
        self.data = data or {}
        self.context = context or {}

    def reply(self, msg_type: str, data: Optional[Dict[str, Any]] = None, context: Optional[Dict[str, Any]] = None) -> "Message":
        """إنشاء رسالة رد مع توريث سياق المحادثة الجارية"""
        new_context = dict(self.context)
        if context:
            new_context.update(context)
        return Message(msg_type, data or {}, new_context)

    def serialize(self) -> str:
        """تحويل الرسالة إلى نص بتنسيق JSON للتسجيل أو الإرسال"""
        return json.dumps({
            "type": self.msg_type,
            "data": self.data,
            "context": self.context
        }, ensure_ascii=False)

    @classmethod
    def deserialize(cls, json_str: str) -> "Message":
        """استعادة كائن الرسالة من نص JSON"""
        parsed = json.loads(json_str)
        return cls(parsed.get("type", ""), parsed.get("data", {}), parsed.get("context", {}))

    def __repr__(self) -> str:
        return f"<OVOS Message: type='{self.msg_type}', data_keys={list(self.data.keys())}>"
