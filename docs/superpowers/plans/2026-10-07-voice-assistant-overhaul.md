# Voice Assistant Overhaul Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transform the BYD DiLink offline Arabic voice assistant from hardcoded logic and rigid pattern matching into an advanced, Alexa-level assistant featuring fuzzy Levenshtein + TF-IDF NLU, Arabic NER, Contextual Dialogue FSM, live Open-Meteo & DuckDuckGo APIs, strict text sanitization, and optimized Vosk STT & Piper TTS voice engines.

**Architecture:** A modular hybrid micro-pipeline dividing responsibilities between native Kotlin (continuous Vosk background listening, VAD, Piper ONNX / fallback TTS) and Chaquopy embedded Python (fuzzy Levenshtein & TF-IDF NLU, local Arabic NER, Contextual Dialogue FSM, live REST API adapters, and TextSanitizer).

**Tech Stack:** Python 3.8 (Chaquopy runtime), Kotlin, Android SDK 34, Vosk Android library, Open-Meteo API, DuckDuckGo Instant Answer API, standard library regex and JSON.

**Spec:** `docs/superpowers/specs/2026-10-07-voice-assistant-overhaul-design.md`

## Global Constraints

- Python components must use Python 3.8 standard library and zero heavy C-extensions to guarantee instant loading (<5ms) and 100% Chaquopy compatibility on car head units.
- Every string sent to TTS or UI must pass through `TextSanitizer` to eliminate markdown, HTML, URLs, emojis, and newlines (`\n`, `\r`, `\t`).
- External API calls (Open-Meteo, DuckDuckGo) must enforce a strict 4.0s timeout and gracefully degrade to local offline responses when network is unavailable.
- FSM contextual memory must support multi-turn dialogue with a 60-second inactivity timeout.
- Audio sample rate for STT is fixed at 16000Hz 16-bit Mono PCM.

## Review Focus

1. **Network Timeout / Airplane Mode:** When the car loses 4G connectivity, weather and search skills must not crash or hang; they must return informative offline fallback responses.
2. **Arabic Dialect & Diacritic Distortion:** Text containing non-standard Arabic spellings (e.g. ه / ة, أ / ا, ى / ي) and Tashkeel must be normalized before fuzzy Levenshtein and TF-IDF calculation.
3. **Dirty API Payloads:** Responses containing unescaped HTML entities (`&quot;`, `&amp;`), markdown tables, links, or multiline formatting must be strictly sanitized into clean, single-line spoken Arabic.
4. **Context Expiry in FSM:** After 60 seconds of silence, previous conversation slots (e.g. city) must reset so a new unrelated prompt is not wrongly contextualized.
5. **Missing TTS / ONNX Assets:** When Piper ONNX model files are absent on device storage, speech output must automatically fall back to the Android system `TextToSpeech` engine without silent failure.

---

### Task 1: Strict Text Sanitizer (`TextSanitizer`)

**Files:**
- Create: `app/src/main/python/ovos_android/text_sanitizer.py`
- Create: `test_text_sanitizer.py`

**Interfaces:**
- Produces: `TextSanitizer.sanitize(text: str) -> str`
- Produces: `TextSanitizer.clean_for_speech(text: str) -> str`

- [ ] **Step 1: Write the failing test**

```python
# test_text_sanitizer.py
import unittest
import sys
import os

sys.path.insert(0, os.path.abspath("app/src/main/python"))
from ovos_android.text_sanitizer import TextSanitizer

class TestTextSanitizer(unittest.TestCase):
    def test_strip_markdown(self):
        raw = "الطقس **مشمس** جداً و*دافئ* اليوم! انظر [هنا](https://weather.com)."
        clean = TextSanitizer.sanitize(raw)
        self.assertNotIn("**", clean)
        self.assertNotIn("*", clean)
        self.assertNotIn("https://", clean)
        self.assertIn("الطقس مشمس جدا و دافئ اليوم", clean)

    def test_strip_html_and_newlines(self):
        raw = "<p>درجة الحرارة <b>25</b> &amp; معتدلة</p>\n\nغداً ماطر.\r\n"
        clean = TextSanitizer.sanitize(raw)
        self.assertNotIn("<p>", clean)
        self.assertNotIn("<b>", clean)
        self.assertNotIn("\n", clean)
        self.assertNotIn("\r", clean)
        self.assertIn("&", clean)

    def test_strip_emojis_and_extra_spaces(self):
        raw = "صباح الخير ☀️🚗!   كيف    حالك؟"
        clean = TextSanitizer.sanitize(raw)
        self.assertNotIn("☀️", clean)
        self.assertNotIn("🚗", clean)
        self.assertEqual(clean, "صباح الخير! كيف حالك؟")

if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python test_text_sanitizer.py`  
Expected: ModuleNotFoundError: No module named 'ovos_android.text_sanitizer'

- [ ] **Step 3: Write minimal implementation**

```python
# app/src/main/python/ovos_android/text_sanitizer.py
# -*- coding: utf-8 -*-
import re
import html

class TextSanitizer:
    """أداة تنقية وتجريد النصوص من الماركداون والوسوم والأسطر قبل الإخراج الصوتي والمرئي"""

    URL_PATTERN = re.compile(r'https?://\S+|www\.\S+')
    HTML_TAG_PATTERN = re.compile(r'<[^>]+>')
    MARKDOWN_LINK_PATTERN = re.compile(r'\[([^\]]+)\]\([^\)]+\)')
    MARKDOWN_FORMAT_PATTERN = re.compile(r'[*_~`#>]')
    EMOJI_PATTERN = re.compile(
        r'[\U00010000-\U0010ffff]'
        r'|[\u2600-\u27BF]'
        r'|[\uD83C-\uDBFF\uDC00-\uDFFF]',
        flags=re.UNICODE
    )

    @classmethod
    def sanitize(cls, text: str) -> str:
        if not text or not isinstance(text, str):
            return ""

        # 1. Unescape HTML entities
        text = html.unescape(text)

        # 2. Extract markdown link anchor text
        text = cls.MARKDOWN_LINK_PATTERN.sub(r'\1', text)

        # 3. Strip URLs
        text = cls.URL_PATTERN.sub('', text)

        # 4. Strip HTML tags
        text = cls.HTML_TAG_PATTERN.sub(' ', text)

        # 5. Strip Markdown formatting symbols
        text = cls.MARKDOWN_FORMAT_PATTERN.sub(' ', text)

        # 6. Strip Emojis
        text = cls.EMOJI_PATTERN.sub('', text)

        # 7. Replace all newlines and tabs with single space
        text = text.replace('\n', ' ').replace('\r', ' ').replace('\t', ' ')

        # 8. Collapse consecutive spaces
        text = re.sub(r'\s+', ' ', text).strip()

        return text

    @classmethod
    def clean_for_speech(cls, text: str) -> str:
        cleaned = cls.sanitize(text)
        # Remove quotes and brackets that sound unnatural when read out loud
        cleaned = re.sub(r'["\'\(\)\{\}\[\]]', '', cleaned)
        return cleaned.strip()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python test_text_sanitizer.py`  
Expected: Ran 3 tests, OK

- [ ] **Step 5: Commit**

```bash
git add app/src/main/python/ovos_android/text_sanitizer.py test_text_sanitizer.py
git commit -m "feat(nlu): add strict TextSanitizer utility for UI and speech"
```

---

### Task 2: Arabic Named Entity Recognition (NER) & Slot Extractor

**Files:**
- Create: `app/src/main/python/ovos_android/ner_extractor.py`
- Create: `test_ner_extractor.py`

**Interfaces:**
- Consumes: Raw normalized user utterances
- Produces: `ArabicNERExtractor.extract_slots(utterance: str) -> Dict[str, Any]` (`location`, `date`, `number`)

- [ ] **Step 1: Write the failing test**

```python
# test_ner_extractor.py
import unittest
import sys
import os

sys.path.insert(0, os.path.abspath("app/src/main/python"))
from ovos_android.ner_extractor import ArabicNERExtractor

class TestArabicNERExtractor(unittest.TestCase):
    def setUp(self):
        self.extractor = ArabicNERExtractor()

    def test_extract_location_exact(self):
        slots = self.extractor.extract_slots("ما هي حالة الطقس في الرياض")
        self.assertEqual(slots.get("location"), "الرياض")

    def test_extract_location_fuzzy(self):
        slots = self.extractor.extract_slots("كيف الجو في اسكندريه اليوم")
        self.assertEqual(slots.get("location"), "الإسكندرية")
        self.assertEqual(slots.get("date"), "اليوم")

    def test_extract_date_relative(self):
        slots = self.extractor.extract_slots("هل ستمطر غدا في دبي")
        self.assertEqual(slots.get("location"), "دبي")
        self.assertEqual(slots.get("date"), "غداً")

    def test_extract_numbers(self):
        slots = self.extractor.extract_slots("اضبط المكيف على 22 درجة")
        self.assertEqual(slots.get("number"), 22)

if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python test_ner_extractor.py`  
Expected: ModuleNotFoundError: No module named 'ovos_android.ner_extractor'

- [ ] **Step 3: Write minimal implementation**

```python
# app/src/main/python/ovos_android/ner_extractor.py
# -*- coding: utf-8 -*-
import re
from typing import Dict, Any, Optional

def levenshtein_similarity(s1: str, s2: str) -> float:
    if not s1 or not s2:
        return 0.0
    m, n = len(s1), len(s2)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(m + 1):
        dp[i][0] = i
    for j in range(n + 1):
        dp[0][j] = j
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            cost = 0 if s1[i - 1] == s2[j - 1] else 1
            dp[i][j] = min(dp[i - 1][j] + 1, dp[i][j - 1] + 1, dp[i - 1][j - 1] + cost)
    max_len = max(m, n)
    return 1.0 - (dp[m][n] / max_len)

class ArabicNERExtractor:
    """مستخرج الكيانات المسمى باللغة العربية (NER) خفيف وسريع بزمن استدلال < 2ms"""

    CITIES_GAZETTEER = {
        "الرياض": ["الرياض", "رياض"],
        "جدة": ["جدة", "جده"],
        "مكة": ["مكة", "مكه", "مكة المكرمة"],
        "المدينة المنورة": ["المدينة", "المدينه", "المدينة المنورة"],
        "الدمام": ["الدمام", "دمام"],
        "القاهرة": ["القاهرة", "القاهره", "قاهرة", "مصر"],
        "الإسكندرية": ["الإسكندرية", "الاسكندرية", "الاسكندريه", "اسكندرية", "اسكندريه"],
        "دبي": ["دبي", "دبى"],
        "أبوظبي": ["أبوظبي", "ابوظبي", "أبو ظبي", "ابو ظبي"],
        "الدوحة": ["الدوحة", "الدوحه", "دوحة"],
        "الكويت": ["الكويت", "كويت"],
        "المنامة": ["المنامة", "المنامه", "بحرين", "البحرين"],
        "مسقط": ["مسقط", "عمان"],
        "بيروت": ["بيروت", "لبنان"],
        "عمان": ["عمان", "الاردن", "عمّان"],
        "بغداد": ["بغداد", "العراق"],
        "دمشق": ["دمشق", "سوريا"],
        "القدس": ["القدس", "فلسطين"],
        "طرابلس": ["طرابلس", "ليبيا"],
        "تونس": ["تونس"],
        "الجزائر": ["الجزائر"],
        "الرباط": ["الرباط", "المغرب"],
        "الدار البيضاء": ["الدار البيضاء", "كازابلانكا", "كازا"]
    }

    DATE_PATTERNS = {
        "اليوم": ["اليوم", "هذا اليوم", "الآن", "الان"],
        "غداً": ["غدا", "غداً", "بكرة", "باكر"],
        "بعد غد": ["بعد غد", "بعد غدا", "بعد بكرة"],
        "أمس": ["امس", "أمس", "البارحة", "البارحه"],
        "الأسبوع القادم": ["الاسبوع القادم", "الأسبوع القادم", "الاسبوع الجاي"]
    }

    @staticmethod
    def _normalize(text: str) -> str:
        text = re.sub(r'[\u064B-\u065F\u0670\u0640]', '', text)
        text = re.sub(r'[إأآا]', 'ا', text)
        text = re.sub(r'[يى]', 'ي', text)
        text = re.sub(r'ة', 'ه', text)
        return text.strip()

    def extract_slots(self, utterance: str) -> Dict[str, Any]:
        slots: Dict[str, Any] = {}
        if not utterance:
            return slots

        norm_utt = self._normalize(utterance)
        words = norm_utt.split()

        # 1. Location Extraction
        for standard_city, variations in self.CITIES_GAZETTEER.items():
            matched = False
            for var in variations:
                norm_var = self._normalize(var)
                if norm_var in norm_utt:
                    slots["location"] = standard_city
                    matched = True
                    break
            if matched:
                break

        # Fuzzy Location fallback if no direct match
        if "location" not in slots:
            best_city = None
            best_sim = 0.0
            for word in words:
                if len(word) < 3:
                    continue
                for standard_city, variations in self.CITIES_GAZETTEER.items():
                    for var in variations:
                        sim = levenshtein_similarity(word, self._normalize(var))
                        if sim > best_sim and sim >= 0.75:
                            best_sim = sim
                            best_city = standard_city
            if best_city:
                slots["location"] = best_city

        # 2. Date / Time Extraction
        for standard_date, variations in self.DATE_PATTERNS.items():
            for var in variations:
                norm_var = self._normalize(var)
                if norm_var in norm_utt:
                    slots["date"] = standard_date
                    break
            if "date" in slots:
                break

        # 3. Number Extraction
        num_match = re.search(r'\b\d+\b', utterance)
        if num_match:
            slots["number"] = int(num_match.group(0))

        return slots
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python test_ner_extractor.py`  
Expected: Ran 4 tests, OK

- [ ] **Step 5: Commit**

```bash
git add app/src/main/python/ovos_android/ner_extractor.py test_ner_extractor.py
git commit -m "feat(nlu): add ArabicNERExtractor with gazetteers and fuzzy slot matching"
```

---

### Task 3: Contextual Dialogue Finite State Machine (FSM)

**Files:**
- Create: `app/src/main/python/ovos_android/dialogue_fsm.py`
- Create: `test_dialogue_fsm.py`

**Interfaces:**
- Produces: `DialogueFSM.update_turn(intent: str, slots: Dict[str, Any]) -> DialogueContext`
- Produces: `DialogueFSM.get_context() -> DialogueContext`
- Produces: `DialogueFSM.reset()`

- [ ] **Step 1: Write the failing test**

```python
# test_dialogue_fsm.py
import unittest
import sys
import os
import time

sys.path.insert(0, os.path.abspath("app/src/main/python"))
from ovos_android.dialogue_fsm import DialogueFSM, DialogueState

class TestDialogueFSM(unittest.TestCase):
    def setUp(self):
        self.fsm = DialogueFSM(session_timeout_seconds=2)

    def test_initial_state(self):
        self.assertEqual(self.fsm.current_state, DialogueState.IDLE)
        self.assertEqual(self.fsm.last_intent, "")
        self.assertEqual(self.fsm.slots, {})

    def test_single_turn(self):
        ctx = self.fsm.update_turn(intent="weather_skill", slots={"location": "الرياض", "date": "اليوم"})
        self.assertEqual(self.fsm.current_state, DialogueState.ACTIVE_SESSION)
        self.assertEqual(ctx.last_intent, "weather_skill")
        self.assertEqual(ctx.slots["location"], "الرياض")

    def test_multi_turn_followup(self):
        self.fsm.update_turn(intent="weather_skill", slots={"location": "الرياض", "date": "اليوم"})
        # Follow-up: User only mentions date
        ctx = self.fsm.update_turn(intent="weather_skill", slots={"date": "غداً"})
        # Location from previous turn must be preserved
        self.assertEqual(ctx.slots["location"], "الرياض")
        self.assertEqual(ctx.slots["date"], "غداً")

    def test_session_timeout(self):
        self.fsm.update_turn(intent="weather_skill", slots={"location": "الرياض"})
        time.sleep(2.1)
        # Timeout expired, should reset
        ctx = self.fsm.get_context()
        self.assertEqual(ctx.state, DialogueState.IDLE)
        self.assertEqual(ctx.slots, {})

if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python test_dialogue_fsm.py`  
Expected: ModuleNotFoundError: No module named 'ovos_android.dialogue_fsm'

- [ ] **Step 3: Write minimal implementation**

```python
# app/src/main/python/ovos_android/dialogue_fsm.py
# -*- coding: utf-8 -*-
import time
from enum import Enum
from typing import Dict, Any, Optional

class DialogueState(Enum):
    IDLE = "IDLE"
    ACTIVE_SESSION = "ACTIVE_SESSION"
    AWAITING_SLOT = "AWAITING_SLOT"

class DialogueContext:
    def __init__(self, state: DialogueState, last_intent: str, slots: Dict[str, Any], awaiting_slot: Optional[str] = None):
        self.state = state
        self.last_intent = last_intent
        self.slots = slots
        self.awaiting_slot = awaiting_slot

class DialogueFSM:
    """آلة حالات منتهية (FSM) لإدارة وتتبع سياق الحوار بين جولات الحديث في السيارة"""

    def __init__(self, session_timeout_seconds: float = 60.0):
        self.session_timeout = session_timeout_seconds
        self.current_state = DialogueState.IDLE
        self.last_intent = ""
        self.slots: Dict[str, Any] = {}
        self.awaiting_slot: Optional[str] = None
        self.last_interaction_timestamp = 0.0

    def _check_and_expire(self) -> None:
        if self.current_state != DialogueState.IDLE:
            if time.time() - self.last_interaction_timestamp > self.session_timeout:
                self.reset()

    def update_turn(self, intent: str, slots: Dict[str, Any], awaiting_slot: Optional[str] = None) -> DialogueContext:
        self._check_and_expire()
        self.last_interaction_timestamp = time.time()

        if intent and intent != "fallback_skill":
            self.last_intent = intent

        # Merge slots (preserve existing slots if not explicitly overridden)
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
        self._check_and_expire()
        return DialogueContext(
            state=self.current_state,
            last_intent=self.last_intent,
            slots=dict(self.slots),
            awaiting_slot=self.awaiting_slot
        )

    def reset(self) -> None:
        self.current_state = DialogueState.IDLE
        self.last_intent = ""
        self.slots.clear()
        self.awaiting_slot = None
        self.last_interaction_timestamp = 0.0
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python test_dialogue_fsm.py`  
Expected: Ran 4 tests, OK

- [ ] **Step 5: Commit**

```bash
git add app/src/main/python/ovos_android/dialogue_fsm.py test_dialogue_fsm.py
git commit -m "feat(nlu): implement DialogueFSM for contextual multi-turn memory"
```

---

### Task 4: Hybrid Fuzzy Levenshtein + TF-IDF NLU Engine

**Files:**
- Modify: `app/src/main/python/ovos_android/nlu_engine.py`
- Create: `test_nlu_hybrid.py`

**Interfaces:**
- Consumes: `intents.json`, `model_weights.json`
- Produces: `ArabicNLUEngine.parse_intent(utterance: str, context: Optional[DialogueContext] = None) -> Dict[str, Any]`

- [ ] **Step 1: Write the failing test**

```python
# test_nlu_hybrid.py
import unittest
import sys
import os

sys.path.insert(0, os.path.abspath("app/src/main/python"))
from ovos_android.nlu_engine import ArabicNLUEngine

class TestHybridNLUEngine(unittest.TestCase):
    def setUp(self):
        weights_path = os.path.abspath("app/src/main/assets/model_weights.json")
        intents_path = os.path.abspath("app/src/main/assets/intents.json")
        self.engine = ArabicNLUEngine(weights_source=weights_path, intents_data_path=intents_path)

    def test_fuzzy_intent_with_typo(self):
        # Typo: "الطقث" instead of "الطقس"
        result = self.engine.parse_intent("كيف الطقث في الرياض")
        self.assertEqual(result["intent"], "weather_skill")
        self.assertGreaterEqual(result["confidence"], 0.70)

    def test_fuzzy_intent_greeting_typo(self):
        # Typo: "مرجبا" instead of "مرحبا"
        result = self.engine.parse_intent("مرجبا يا صديقي")
        self.assertEqual(result["intent"], "greeting_skill")

    def test_stop_command_fuzzy(self):
        # Typo: "توغف" instead of "توقف"
        result = self.engine.parse_intent("توغف عن الكلام")
        self.assertEqual(result["intent"], "stop_skill")

if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python test_nlu_hybrid.py`  
Expected: AssertionError or KeyError

- [ ] **Step 3: Modify `nlu_engine.py` to add Levenshtein and fuzzy pattern matching**

Update `app/src/main/python/ovos_android/nlu_engine.py`:
1. In `__init__`, accept `intents_data_path` and load pattern templates into `self.intent_patterns: Dict[str, List[str]]`.
2. Implement `_fuzzy_match_patterns(cleaned_text: str) -> Optional[Tuple[str, float]]` using token-based and sentence-based Levenshtein similarity.
3. Replace rigid `_fast_rules` with fuzzy matcher, and blend fuzzy confidence with TF-IDF probability.
4. Support contextual intent biasing when `context` is provided (e.g. follow-up query inherits previous intent if query is short and slot-focused).

- [ ] **Step 4: Run test to verify it passes**

Run: `python test_nlu_hybrid.py`  
Expected: Ran 3 tests, OK

- [ ] **Step 5: Commit**

```bash
git add app/src/main/python/ovos_android/nlu_engine.py test_nlu_hybrid.py
git commit -m "feat(nlu): integrate Levenshtein fuzzy matching and contextual intent resolution"
```

---

### Task 5: Live Weather Service with Open-Meteo API

**Files:**
- Modify: `app/src/main/python/ovos_android/skills/weather_skill.py`
- Create: `test_weather_skill.py`

**Interfaces:**
- Consumes: `Message` with `slots` (`location`, `date`), `TextSanitizer`
- Produces: `WeatherSkill.handle_weather(message: Message)` -> emits `speak` event with dynamic, real-time Arabic weather text.

- [ ] **Step 1: Write the failing test**

```python
# test_weather_skill.py
import unittest
import sys
import os

sys.path.insert(0, os.path.abspath("app/src/main/python"))
from ovos_android.bus import AndroidMessageBus
from ovos_android.message import Message
from ovos_android.skills.weather_skill import WeatherSkill

class TestWeatherSkill(unittest.TestCase):
    def setUp(self):
        self.bus = AndroidMessageBus()
        self.skill = WeatherSkill(self.bus)
        self.skill.initialize()
        self.spoken = []
        self.bus.on("speak", lambda msg: self.spoken.append(msg.data.get("utterance", "")))

    def test_fetch_real_weather(self):
        msg = Message("weather_skill", data={"utterance": "ما حالة الطقس في الرياض", "slots": {"location": "الرياض"}})
        self.skill.handle_weather(msg)
        self.assertTrue(len(self.spoken) > 0)
        resp = self.spoken[0]
        self.assertIn("الرياض", resp)
        self.assertTrue("درجة" in resp or "الطقس" in resp)
        self.assertNotIn("\n", resp)

    def test_offline_fallback_on_invalid_location(self):
        msg = Message("weather_skill", data={"utterance": "الطقس في مكانغيرموجود123", "slots": {"location": "مكانغيرموجود123"}})
        self.skill.handle_weather(msg)
        self.assertTrue(len(self.spoken) > 0)

if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python test_weather_skill.py`  
Expected: Fails or returns old static dialog.

- [ ] **Step 3: Refactor `weather_skill.py`**

Implement real HTTP geocoding and forecasting via `urllib.request` against Open-Meteo:
1. `get_coordinates(city: str) -> Tuple[float, float]` via `https://geocoding-api.open-meteo.com/v1/search?name={city}&count=1&language=ar&format=json`
2. `get_forecast(lat: float, lon: float) -> Dict[str, Any]` via `https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m,apparent_temperature,weather_code,wind_speed_10m`
3. Translate WMO weather code to natural Arabic string (0 -> "صافٍ", 1-3 -> "غائم جزئياً", 51-67 -> "ممطر", etc.).
4. Format clean natural sentence and sanitize via `TextSanitizer.clean_for_speech`.
5. Graceful fallback on network timeout (timeout=4.0s).

- [ ] **Step 4: Run test to verify it passes**

Run: `python test_weather_skill.py`  
Expected: Ran 2 tests, OK

- [ ] **Step 5: Commit**

```bash
git add app/src/main/python/ovos_android/skills/weather_skill.py test_weather_skill.py
git commit -m "feat(skills): refactor WeatherSkill with Open-Meteo live API and robust offline fallback"
```

---

### Task 6: General Knowledge & Fallback Skill with DuckDuckGo / Wolfram Alpha

**Files:**
- Modify: `app/src/main/python/ovos_android/skills/knowledge_skills.py`
- Modify: `app/src/main/python/ovos_android/skills/fallback_skill.py`
- Create: `test_knowledge_skills.py`

**Interfaces:**
- Consumes: DuckDuckGo Instant Answer API, `TextSanitizer`
- Produces: Sanitized knowledge answers with local QA pair fallback.

- [ ] **Step 1: Write the failing test**

```python
# test_knowledge_skills.py
import unittest
import sys
import os

sys.path.insert(0, os.path.abspath("app/src/main/python"))
from ovos_android.bus import AndroidMessageBus
from ovos_android.message import Message
from ovos_android.skills.fallback_skill import FallbackSkill

class TestKnowledgeSkills(unittest.TestCase):
    def setUp(self):
        self.bus = AndroidMessageBus()
        self.skill = FallbackSkill(self.bus, qa_pairs=[])
        self.skill.initialize()
        self.spoken = []
        self.bus.on("speak", lambda msg: self.spoken.append(msg.data.get("utterance", "")))

    def test_duckduckgo_query(self):
        msg = Message("fallback_skill:handle_fallback", data={"utterance": "ما هي الأهرامات"})
        self.skill.handle_fallback(msg)
        self.assertTrue(len(self.spoken) > 0)
        resp = self.spoken[0]
        self.assertNotIn("\n", resp)
        self.assertNotIn("<p>", resp)

if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python test_knowledge_skills.py`  
Expected: Fails or returns static fallback dialog without online search.

- [ ] **Step 3: Modify `fallback_skill.py` and `knowledge_skills.py`**

1. Add DuckDuckGo Instant Answer API query via `https://api.duckduckgo.com/?q={query}&format=json&no_html=1&skip_disambig=1`.
2. Add support for Wolfram Alpha Spoken API query if `WOLFRAM_APP_ID` is set: `https://api.wolframalpha.com/v1/spoken?appid={app_id}&i={query}`.
3. Pass all results through `TextSanitizer.clean_for_speech`.
4. If network error occurs or answer is empty, fall back to local `qa_pairs` fuzzy matching.

- [ ] **Step 4: Run test to verify it passes**

Run: `python test_knowledge_skills.py`  
Expected: Ran 1 test, OK

- [ ] **Step 5: Commit**

```bash
git add app/src/main/python/ovos_android/skills/knowledge_skills.py app/src/main/python/ovos_android/skills/fallback_skill.py test_knowledge_skills.py
git commit -m "feat(skills): integrate DuckDuckGo knowledge API with sanitization and QA fallback"
```

---

### Task 7: Intent Service & Skill Router Integration with FSM & Sanitizer

**Files:**
- Modify: `app/src/main/python/ovos_android/intent_service.py`
- Modify: `app/src/main/python/ovos_android/skill_router.py`
- Modify: `app/src/main/python/ovos_bridge.py`
- Create: `test_full_integrated_pipeline.py`

**Interfaces:**
- Produces: Fully integrated `ovos_bridge.process_utterance(utterance: str) -> str` supporting multi-turn memory, slots, and sanitized responses.

- [ ] **Step 1: Write the failing test**

```python
# test_full_integrated_pipeline.py
import unittest
import sys
import os
import json

sys.path.insert(0, os.path.abspath("app/src/main/python"))
import ovos_bridge

class TestFullIntegratedPipeline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        m_path = os.path.abspath("app/src/main/assets/model_weights.json")
        i_path = os.path.abspath("app/src/main/assets/intents.json")
        ovos_bridge.initialize(m_path, i_path)

    def test_pipeline_turn1_and_turn2_context(self):
        # Turn 1: Weather in Riyadh
        r1 = json.loads(ovos_bridge.process_utterance("ما هو الطقس في الرياض اليوم"))
        self.assertEqual(r1["intent"], "weather_skill")
        self.assertIn("الرياض", r1["response"])
        self.assertNotIn("\n", r1["response"])

        # Turn 2: Follow-up question relying on previous location
        r2 = json.loads(ovos_bridge.process_utterance("وغداً؟"))
        self.assertEqual(r2["intent"], "weather_skill")
        self.assertIn("الرياض", r2["response"])

if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python test_full_integrated_pipeline.py`  
Expected: Turn 2 fails to retain Riyadh or fails intent matching.

- [ ] **Step 3: Modify `skill_router.py` and `intent_service.py`**

1. Instantiate `ArabicNERExtractor` and `DialogueFSM` in `SkillRouter` and pass to `IntentService`.
2. Extract slots on incoming utterance and inject into message context and FSM.
3. Sanitize speech outputs centrally in `SkillRouter._on_speak_event` using `TextSanitizer.clean_for_speech`.
4. Return enriched JSON in `process_utterance` including `slots` and `context_state`.

- [ ] **Step 4: Run test to verify it passes**

Run: `python test_full_integrated_pipeline.py`  
Expected: Ran 1 test, OK

- [ ] **Step 5: Commit**

```bash
git add app/src/main/python/ovos_android/intent_service.py app/src/main/python/ovos_android/skill_router.py app/src/main/python/ovos_bridge.py test_full_integrated_pipeline.py
git commit -m "feat(core): connect DialogueFSM and NER extractor into central SkillRouter pipeline"
```

---

### Task 8: Android Platform & Voice Engine Optimization (Vosk STT & Piper TTS Architecture)

**Files:**
- Modify: `app/build.gradle`
- Modify: `app/src/main/AndroidManifest.xml`
- Create: `app/src/main/java/com/ovos/arabicassistant/voice/VoskSpeechService.kt`
- Create: `app/src/main/java/com/ovos/arabicassistant/voice/PiperTtsManager.kt`
- Modify: `app/src/main/java/com/ovos/arabicassistant/MainActivity.kt`

**Interfaces:**
- Produces: `VoskSpeechService` for background continuous listening.
- Produces: `PiperTtsManager` for high-fidelity speech with `length_scale = 1.15` and system TTS fallback.

- [ ] **Step 1: Update `AndroidManifest.xml` with required permissions**

Add:
```xml
<uses-permission android:name="android.permission.INTERNET" />
<uses-permission android:name="android.permission.ACCESS_NETWORK_STATE" />
<uses-permission android:name="android.permission.FOREGROUND_SERVICE" />
<uses-permission android:name="android.permission.FOREGROUND_SERVICE_MICROPHONE" />
```

- [ ] **Step 2: Update `app/build.gradle` with Vosk library and dependencies**

Add Vosk and OkHttp dependencies:
```groovy
implementation 'com.alphacephei:vosk-android:0.3.47'
implementation 'com.squareup.okhttp3:okhttp:4.12.0'
```

- [ ] **Step 3: Implement `PiperTtsManager.kt`**

Create `app/src/main/java/com/ovos/arabicassistant/voice/PiperTtsManager.kt`:
Handles speech synthesis, configures `length_scale = 1.15`, sanitizes inputs, and delegates to Android `TextToSpeech` as a reliable fallback.

- [ ] **Step 4: Implement `VoskSpeechService.kt`**

Create `app/src/main/java/com/ovos/arabicassistant/voice/VoskSpeechService.kt`:
Configures 16000Hz continuous listening with Energy-based Voice Activity Detection (VAD) and feeds speech recognition results to `MainActivity` or `OvosAssistantEngine`.

- [ ] **Step 5: Update `MainActivity.kt` to integrate the optimized voice managers**

Connect `PiperTtsManager` and `VoskSpeechService` to UI with clean visual indicators and audio focus handling.

- [ ] **Step 6: Verify Gradle and Android project build**

Run: `gradle assembleDebug --dry-run` or check Gradle configuration.  
Expected: BUILD SUCCESSFUL

- [ ] **Step 7: Commit**

```bash
git add app/build.gradle app/src/main/AndroidManifest.xml app/src/main/java/com/ovos/arabicassistant/voice/ app/src/main/java/com/ovos/arabicassistant/MainActivity.kt
git commit -m "feat(android): add VoskSpeechService, PiperTtsManager, and network permissions"
```
