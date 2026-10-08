# -*- coding: utf-8 -*-
"""
موجه المهارات المركزي (SkillRouter) لسيارات BYD DiLink
ينظم ويشغل دورة حياة المساعد الصوتي بالكامل:
- إنشاء ناقل الرسائل (MessageBus)
- تحميل محرك NLU العربي الهجين (TF-IDF + Levenshtein)
- تفعيل آلة حالات الحوار (DialogueFSM) ومستخرج الكيانات (ArabicNERExtractor)
- تهيئة وتسجيل جميع المهارات العربية
- تنقية الردود الصوتية بصرامة عبر TextSanitizer
"""

import os
import json
import threading
from typing import Dict, Any, Optional

from .bus import AndroidMessageBus
from .message import Message
from .nlu_engine import ArabicNLUEngine
from .intent_service import IntentService
from .dialogue_fsm import DialogueFSM
from .ner_extractor import ArabicNERExtractor
from .text_sanitizer import TextSanitizer
from .skills import (
    GreetingSkill,
    AssistantInfoSkill,
    TimeDateSkill,
    StopSkill,
    WeatherSkill,
    HealthWellnessSkill,
    ScienceTechSkill,
    HistoryGeographySkill,
    MathLogicSkill,
    LanguageTranslationSkill,
    CreativeWritingSkill,
    DailyAssistantSkill,
    GeneralKnowledgeSkill,
    FallbackSkill,
)


class SkillRouter:
    """موجه ومنسق مهارات OpenVoiceOS لنظام أندرويد"""

    def __init__(self, model_weights_path: str, intents_data_path: Optional[str] = None):
        self.bus = AndroidMessageBus()
        self.fsm = DialogueFSM(session_timeout_seconds=60.0)
        self.ner = ArabicNERExtractor()
        self.nlu_engine = ArabicNLUEngine(
            weights_source=model_weights_path,
            intents_data_path=intents_data_path
        )
        self.intent_service = IntentService(
            bus=self.bus,
            nlu_engine=self.nlu_engine,
            fsm=self.fsm,
            ner=self.ner,
            min_confidence=0.65
        )
        self.skills: Dict[str, Any] = {}
        self.last_speech_output: str = ""
        self.last_matched_intent: str = ""
        self.last_confidence: float = 0.0
        self._lock = threading.RLock()

        # الاستماع للردود الصوتية الصادرة من المهارات ومطابقة النوايا
        self.bus.on("speak", self._on_speak_event)
        self.bus.on("ovos.intent.matched", self._on_intent_matched)

        # تحميل البيانات وتهيئة المهارات
        self._load_and_initialize_skills(intents_data_path)

    def _on_speak_event(self, message: Message) -> None:
        """التقاط وتنقية الرد الصوتي الصادر من المهارة النشطة"""
        raw_text = message.data.get("utterance", "")
        # ضمان خلو الرد التام من الماركداون والوسوم والأسطر
        self.last_speech_output = TextSanitizer.clean_for_speech(raw_text)

    def _on_intent_matched(self, message: Message) -> None:
        """تسجيل النية المطابقة ودرجة ثقتها"""
        self.last_matched_intent = message.data.get("intent_name", "")
        self.last_confidence = message.data.get("confidence", 0.0)

    def _load_and_initialize_skills(self, intents_data_path: Optional[str]) -> None:
        """تحميل وتغذية المهارات ببيانات الردود والأزواج المعرفية"""
        intents_dict = {}
        qa_pairs = []

        if intents_data_path and os.path.exists(intents_data_path):
            try:
                with open(intents_data_path, "r", encoding="utf-8") as f:
                    raw_data = json.load(f)
                    for item in raw_data.get("intents", []):
                        intents_dict[item["tag"]] = item.get("responses", [])
                    qa_pairs = raw_data.get("qa_pairs", [])
            except Exception as e:
                print(f"[SkillRouter] Error reading intents JSON: {e}")

        # تجميع أزواج السؤال والجواب حسب كل نية
        qa_by_intent = {}
        for pair in qa_pairs:
            cat = pair.get("intent")
            if cat not in qa_by_intent:
                qa_by_intent[cat] = []
            qa_by_intent[cat].append(pair)

        # 1. المهارات النظامية والحوارية
        self._register(GreetingSkill(self.bus))
        self._register(AssistantInfoSkill(self.bus))
        self._register(TimeDateSkill(self.bus))
        self._register(StopSkill(self.bus))
        self._register(WeatherSkill(self.bus))

        # 2. مهارات المعرفة والعلوم والمهام
        self._register(HealthWellnessSkill(self.bus, qa_by_intent.get("health_wellness_skill", []), intents_dict.get("health_wellness_skill", [])))
        self._register(ScienceTechSkill(self.bus, qa_by_intent.get("science_tech_skill", []), intents_dict.get("science_tech_skill", [])))
        self._register(HistoryGeographySkill(self.bus, qa_by_intent.get("history_geography_skill", []), intents_dict.get("history_geography_skill", [])))
        self._register(MathLogicSkill(self.bus, qa_by_intent.get("math_logic_skill", []), intents_dict.get("math_logic_skill", [])))
        self._register(LanguageTranslationSkill(self.bus, qa_by_intent.get("language_translation_skill", []), intents_dict.get("language_translation_skill", [])))
        self._register(CreativeWritingSkill(self.bus, qa_by_intent.get("creative_writing_skill", []), intents_dict.get("creative_writing_skill", [])))
        self._register(DailyAssistantSkill(self.bus, qa_by_intent.get("daily_assistant_skill", []), intents_dict.get("daily_assistant_skill", [])))
        self._register(GeneralKnowledgeSkill(self.bus, qa_by_intent.get("general_knowledge_skill", []), intents_dict.get("general_knowledge_skill", [])))

        # 3. مهارة التراجع
        self._register(FallbackSkill(self.bus, qa_pairs))

    def _register(self, skill: Any) -> None:
        """تسجيل المهارة في موجه النوايا والناقل"""
        skill.initialize()
        self.skills[skill.skill_id] = skill
        self.intent_service.register_skill(skill)

    def process_utterance(
        self,
        utterance: str,
        external_intent: Optional[str] = None,
        external_confidence: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        معالجة جملة المستخدم وتوجيهها للمهارة المناسبة وإرجاع الرد المنقى
        مع سياق الكيانات وحالة الذاكرة ودعم التوجيه الدلالي المسبق
        """
        if utterance and len(utterance) > 256:
            utterance = utterance[:256]

        with self._lock:
            self.last_speech_output = ""
            self.last_matched_intent = ""
            self.last_confidence = 0.0

            # بث الحدث القياسي في OVOS مع حقن النية الدلالية الخارجية إن وجدت
            msg_data: Dict[str, Any] = {"utterances": [utterance]}
            if external_intent:
                msg_data["external_intent"] = external_intent
                msg_data["external_confidence"] = external_confidence or 0.0

            msg = Message("recognizer_loop:utterance", data=msg_data)
            self.bus.emit(msg)

            ctx = self.fsm.get_context()
            return {
                "response": self.last_speech_output,
                "intent": self.last_matched_intent,
                "confidence": self.last_confidence,
                "utterance": utterance,
                "slots": ctx.slots,
                "context_state": ctx.state.value
            }
