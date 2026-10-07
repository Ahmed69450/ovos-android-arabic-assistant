# -*- coding: utf-8 -*-
"""
آلة حالات الحوار المنتهية (Contextual Dialogue FSM)
تتتبع سياق الحوار بين جولات الحديث، وتحفظ آخر نية والكيانات المستخرجة (مثل المدينة والتاريخ)،
وتدير مؤقت انتهاء الجلسة لحماية الخصوصية وملاءمة القيادة في سيارات BYD DiLink.
"""

import time
from enum import Enum
from typing import Dict, Any, Optional


class DialogueState(Enum):
    IDLE = "IDLE"
    ACTIVE_SESSION = "ACTIVE_SESSION"
    AWAITING_SLOT = "AWAITING_SLOT"


class DialogueContext:
    """كائن يحمل سياق الجلسة الحالية ومحتوى الذاكرة اللحظية"""

    def __init__(
        self,
        state: DialogueState,
        last_intent: str,
        slots: Dict[str, Any],
        awaiting_slot: Optional[str] = None
    ):
        self.state = state
        self.last_intent = last_intent
        self.slots = slots
        self.awaiting_slot = awaiting_slot

    def to_dict(self) -> Dict[str, Any]:
        return {
            "state": self.state.value,
            "last_intent": self.last_intent,
            "slots": self.slots,
            "awaiting_slot": self.awaiting_slot
        }

    def __repr__(self) -> str:
        return f"<DialogueContext state={self.state.value} intent='{self.last_intent}' slots={self.slots}>"


class DialogueFSM:
    """آلة حالات منتهية (FSM) لإدارة وتتبع سياق الحوار بين جولات الحديث"""

    def __init__(self, session_timeout_seconds: float = 60.0):
        self.session_timeout = session_timeout_seconds
        self.current_state = DialogueState.IDLE
        self.last_intent = ""
        self.slots: Dict[str, Any] = {}
        self.awaiting_slot: Optional[str] = None
        self.last_interaction_timestamp = 0.0

    def _check_and_expire(self) -> None:
        """التحقق من انتهاء مهلة الجلسة وإعادتها لحالة السكون عند الصمت الطويل"""
        if self.current_state != DialogueState.IDLE:
            if time.time() - self.last_interaction_timestamp > self.session_timeout:
                self.reset()

    def update_turn(
        self,
        intent: Optional[str],
        slots: Optional[Dict[str, Any]] = None,
        awaiting_slot: Optional[str] = None
    ) -> DialogueContext:
        """
        تحديث حالة الحوار بعد كل جملة من المستخدم:
        - دمج الكيانات الجديدة مع الحفاظ على الكيانات السابقة
        - تحديث حالة الجلسة
        - تجديد مؤقت الجلسة
        """
        self._check_and_expire()
        self.last_interaction_timestamp = time.time()

        if intent and intent not in ("fallback_skill", "unknown", "error"):
            self.last_intent = intent

        # دمج الكيانات الجديدة
        if slots:
            for k, v in slots.items():
                if v is not None:
                    self.slots[k] = v

        if awaiting_slot:
            self.current_state = DialogueState.AWAITING_SLOT
            self.awaiting_slot = awaiting_slot
        else:
            self.current_state = DialogueState.ACTIVE_SESSION
            self.awaiting_slot = None

        return self.get_context()

    def get_context(self) -> DialogueContext:
        """استرجاع السياق الحالي مع التحقق من صلاحية المهلة"""
        self._check_and_expire()
        return DialogueContext(
            state=self.current_state,
            last_intent=self.last_intent,
            slots=dict(self.slots),
            awaiting_slot=self.awaiting_slot
        )

    def reset(self) -> None:
        """إعادة تعيين كاملة لحالة السكون ومسح الذاكرة اللحظية"""
        self.current_state = DialogueState.IDLE
        self.last_intent = ""
        self.slots.clear()
        self.awaiting_slot = None
        self.last_interaction_timestamp = 0.0
