# -*- coding: utf-8 -*-
"""
خدمة النوايا المركزية (IntentService) المتوافقة مع ovos-core
تستمع لعبارات المستخدم، وتستدعي محرك NLU لتحديد النية، وتوجه الطلب للمهارة الفائزة
"""

from typing import Dict, Any, Optional
from .message import Message
from .bus import AndroidMessageBus
from .nlu_engine import ArabicNLUEngine
from .dispatcher import IntentDispatcher

class IntentService:
    """المنسق المركزي لتحليل النوايا وتوجيهها للمهارات"""

    def __init__(self, bus: AndroidMessageBus, nlu_engine: ArabicNLUEngine, min_confidence: float = 0.30):
        self.bus = bus
        self.nlu_engine = nlu_engine
        self.min_confidence = min_confidence
        self.dispatcher = IntentDispatcher(bus)
        self._skills_registry: Dict[str, Any] = {}
        self._register_bus_listeners()

    def _register_bus_listeners(self) -> None:
        """الاستماع للأحداث الصوتية من واجهة أندرويد"""
        # الحدث القياسي في OVOS لوصول نص منطوق جديد
        self.bus.on("recognizer_loop:utterance", self._handle_utterance)

    def register_skill(self, skill: Any) -> None:
        """تسجيل مهارة جديدة في سجل المهارات"""
        self._skills_registry[skill.skill_id] = skill

    def _handle_utterance(self, message: Message) -> None:
        """معالجة حدث العبارة المنطوقة القادمة من الهاتف"""
        utterance = message.data.get("utterances", [""])[0] if "utterances" in message.data else message.data.get("utterance", "")
        if not utterance:
            return

        # 1. مطابقة النية عبر محرك NLU
        match_result = self.nlu_engine.parse_intent(utterance)
        matched_intent = match_result["intent"]
        confidence = match_result["confidence"]

        # 2. التحقق من عتبة الثقة المعتمدة
        is_confident = confidence >= self.min_confidence

        if is_confident and matched_intent:
            # بث حدث مطابقة النية بنجاح
            self.bus.emit(Message("ovos.intent.matched", data={
                "intent_name": matched_intent,
                "confidence": confidence,
                "utterance": utterance
            }))

            # إيجاد المهارة التي سجلت هذا المعالج
            dispatched = False
            for skill_id, skill in self._skills_registry.items():
                handler = skill._intent_handlers.get(matched_intent)
                if handler:
                    intent_msg = Message(
                        f"{skill_id}:{matched_intent}",
                        data={"utterance": utterance, "confidence": confidence, "intent": matched_intent},
                        context=message.context
                    )
                    self.dispatcher.dispatch(skill_id, matched_intent, intent_msg, handler)
                    dispatched = True
                    break

            if not dispatched:
                self._trigger_fallback(utterance, message)
        else:
            # عند عدم توفر درجة ثقة كافية يتم التراجع للمهارة الاحتياطية (Fallback)
            self._trigger_fallback(utterance, message)

        # بث حدث اكتمال معالجة الجملة المنطوقة
        self.bus.emit(Message("ovos.utterance.handled", data={"utterance": utterance}))

    def _trigger_fallback(self, utterance: str, original_message: Message) -> None:
        """تفعيل مهارة التراجع عند عدم فهم النية بدقة"""
        fallback_skill = self._skills_registry.get("fallback_skill")
        if fallback_skill and hasattr(fallback_skill, "handle_fallback"):
            fallback_msg = Message(
                "fallback_skill:handle_fallback",
                data={"utterance": utterance},
                context=original_message.context
            )
            self.dispatcher.dispatch("fallback_skill", "handle_fallback", fallback_msg, fallback_skill.handle_fallback)
        else:
            self.bus.emit(Message("speak", data={"utterance": "عذراً، لم أستطع فهم طلبك بدقة، هل يمكنك التوضيح أكثر؟"}))
