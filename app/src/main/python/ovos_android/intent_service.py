# -*- coding: utf-8 -*-
"""
خدمة النوايا المركزية (IntentService) المتوافقة مع ovos-core
تستمع لعبارات المستخدم، تستخرج الكيانات، تستدعي محرك NLU بالاقتران مع سياق FSM،
وتوجه الطلب مع الكيانات والسياق للمهارة الفائزة
"""

import re
from typing import Dict, Any, Optional
from .message import Message
from .bus import AndroidMessageBus
from .nlu_engine import ArabicNLUEngine
from .dispatcher import IntentDispatcher
from .dialogue_fsm import DialogueFSM
from .ner_extractor import ArabicNERExtractor


class IntentService:
    """المنسق المركزي لتحليل النوايا وتوجيهها للمهارات مع ذاكرة السياق"""

    def __init__(
        self,
        bus: AndroidMessageBus,
        nlu_engine: ArabicNLUEngine,
        fsm: Optional[DialogueFSM] = None,
        ner: Optional[ArabicNERExtractor] = None,
        min_confidence: float = 0.65
    ):
        self.bus = bus
        self.nlu_engine = nlu_engine
        self.fsm = fsm
        self.ner = ner
        self.min_confidence = min_confidence
        self.dispatcher = IntentDispatcher(bus)
        self._skills_registry: Dict[str, Any] = {}
        self._register_bus_listeners()

    def _register_bus_listeners(self) -> None:
        """الاستماع للأحداث الصوتية من واجهة أندرويد"""
        self.bus.on("recognizer_loop:utterance", self._handle_utterance)

    def register_skill(self, skill: Any) -> None:
        """تسجيل مهارة جديدة في سجل المهارات"""
        self._skills_registry[skill.skill_id] = skill

    def _handle_utterance(self, message: Message) -> None:
        """معالجة حدث العبارة المنطوقة القادمة من الهاتف مع حقن الكيانات والسياق"""
        utterance = message.data.get("utterances", [""])[0] if "utterances" in message.data else message.data.get("utterance", "")
        if not utterance:
            return

        # 1. استخراج الكيانات اللحظية (NER)
        current_slots = self.ner.extract_slots(utterance) if self.ner else {}

        # 2. الحصول على سياق الجلسة السابقة
        current_context = self.fsm.get_context() if self.fsm else None

        # 3. فحص سياق الحوار التتابعي لردود الدردشة (Chitchat State Followup)
        # إذا كانت الجولة السابقة تحية أو سؤال عن الحال، والرد هو حالة المستخدم (مثل "اني زين", "الحمد لله", "بخير")
        clean_utt = re.sub(r'[^\w\s]', ' ', utterance).strip()
        utt_words = clean_utt.split()
        chitchat_phrases = [
            "اني زين", "انا زين", "الحمد لله", "الحمدلله", "زين الحمد لله",
            "زين الحمدلله", "بخير الحمد لله", "تمام الحمد لله", "الحمد لله بخير",
            "بخير وانت", "تمام وانت", "وانت كيفك", "وانت شخبارك", "كلو تمام",
            "كله تمام", "بصحة جيدة", "على ما يرام", "ماشي الحال"
        ]
        chitchat_single_words = {"زين", "بخير", "تمام", "عايشين", "كويس"}
        has_chitchat_phrase = any(phrase in clean_utt for phrase in chitchat_phrases)
        has_chitchat_word = len(utt_words) <= 3 and any(w in chitchat_single_words for w in utt_words)
        is_chitchat = has_chitchat_phrase or has_chitchat_word

        ext_intent = message.data.get("external_intent")
        ext_conf = float(message.data.get("external_confidence", 0.0))

        if ext_intent and ext_intent != "unknown":
            matched_intent = ext_intent
            confidence = ext_conf
        elif current_context and current_context.last_intent == "greeting_skill" and is_chitchat:
            matched_intent = "greeting_skill"
            confidence = 0.99
            match_result = {
                "intent": "greeting_skill",
                "confidence": 0.99,
                "utterance": utterance,
                "match_type": "chitchat_followup"
            }
        elif is_chitchat and len(utt_words) <= 3:
            # حتى لو كانت الجولة الأولى، ردود الحالة الشخصية تصنف كدردشة حوارية ودودة
            matched_intent = "greeting_skill"
            confidence = 0.98
            match_result = {
                "intent": "greeting_skill",
                "confidence": 0.98,
                "utterance": utterance,
                "match_type": "chitchat_followup"
            }
        else:
            match_result = self.nlu_engine.parse_intent(utterance, context=current_context)
            matched_intent = match_result.get("intent", "")
            confidence = match_result.get("confidence", 0.0)

        # 4. التحقق من عتبة الثقة المعتمدة (65% حد أدنى لمنع التوجيه العشوائي)
        is_confident = confidence >= self.min_confidence

        if is_confident and matched_intent and matched_intent != "fallback_skill":
            # تحديث آلة حالات الحوار بالنية والكيانات المكتشفة
            if self.fsm:
                updated_ctx = self.fsm.update_turn(matched_intent, current_slots)
                merged_slots = updated_ctx.slots
            else:
                merged_slots = current_slots

            # بث حدث مطابقة النية بنجاح
            self.bus.emit(Message("ovos.intent.matched", data={
                "intent_name": matched_intent,
                "confidence": confidence,
                "utterance": utterance,
                "slots": merged_slots
            }))

            # إيجاد المهارة التي سجلت هذا المعالج
            dispatched = False
            for skill_id, skill in self._skills_registry.items():
                handler = skill._intent_handlers.get(matched_intent)
                if handler:
                    intent_msg = Message(
                        f"{skill_id}:{matched_intent}",
                        data={
                            "utterance": utterance,
                            "confidence": confidence,
                            "intent": matched_intent,
                            "slots": merged_slots
                        },
                        context=message.context
                    )
                    self.dispatcher.dispatch(skill_id, matched_intent, intent_msg, handler)
                    dispatched = True
                    break

            if not dispatched:
                self._trigger_fallback(utterance, message, slots=merged_slots)
        else:
            # عند عدم توفر درجة ثقة كافية يتم التراجع للمهارة الاحتياطية (Fallback)
            self._trigger_fallback(utterance, message, slots=current_slots)

        # بث حدث اكتمال معالجة الجملة المنطوقة
        self.bus.emit(Message("ovos.utterance.handled", data={"utterance": utterance}))

    def _trigger_fallback(self, utterance: str, original_message: Message, slots: Optional[Dict[str, Any]] = None) -> None:
        """تفعيل مهارة التراجع عند عدم فهم النية بدقة مع تمرير الكيانات"""
        fallback_skill = self._skills_registry.get("fallback_skill")
        if fallback_skill and hasattr(fallback_skill, "handle_fallback"):
            fallback_msg = Message(
                "fallback_skill:handle_fallback",
                data={"utterance": utterance, "slots": slots or {}},
                context=original_message.context
            )
            self.dispatcher.dispatch("fallback_skill", "handle_fallback", fallback_msg, fallback_skill.handle_fallback)
        else:
            self.bus.emit(Message("speak", data={"utterance": "عذراً، لم أستطع فهم طلبك بدقة، هل يمكنك التوضيح أكثر؟"}))
