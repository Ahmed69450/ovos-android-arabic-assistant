# -*- coding: utf-8 -*-
"""
ناقل الرسائل الخفيف المتوافق مع OpenVoiceOS لنظام أندرويد (AndroidMessageBus)
يوفر نمط الناشر/المشترك (Pub/Sub) المعتمد في OVOS بدون الحاجة لمخدمات ويب-سوكت خارجية
"""

import threading
from typing import Callable, Dict, List
from .message import Message

class AndroidMessageBus:
    """ناقل رسائل محلي خفيف الوزن ومناسب لبيئة أندرويد المدمجة"""

    def __init__(self):
        self._handlers: Dict[str, List[Callable[[Message], None]]] = {}
        self._lock = threading.RLock()

    def on(self, event_type: str, handler: Callable[[Message], None]) -> None:
        """تسجيل دالة استماع لحدث معين"""
        with self._lock:
            if event_type not in self._handlers:
                self._handlers[event_type] = []
            if handler not in self._handlers[event_type]:
                self._handlers[event_type].append(handler)

    def once(self, event_type: str, handler: Callable[[Message], None]) -> None:
        """تسجيل دالة استماع لمرة واحدة فقط ثم يتم إلغاؤها تلقائياً"""
        def _wrapper(msg: Message):
            self.remove(event_type, _wrapper)
            handler(msg)
        self.on(event_type, _wrapper)

    def remove(self, event_type: str, handler: Callable[[Message], None]) -> None:
        """إلغاء تسجيل دالة استماع"""
        with self._lock:
            if event_type in self._handlers and handler in self._handlers[event_type]:
                self._handlers[event_type].remove(handler)

    def emit(self, message: Message) -> None:
        """بث رسالة لجميع المهارات والخدمات المشتركة في هذا الحدث"""
        with self._lock:
            handlers = list(self._handlers.get(message.msg_type, []))
            # دعم الاستماع العام للأحداث (Wildcard)
            wildcard_handlers = list(self._handlers.get("*", []))
            
        for handler in handlers + wildcard_handlers:
            try:
                handler(message)
            except Exception as e:
                print(f"[خطأ في معالج الحدث {message.msg_type}]: {str(e)}")
