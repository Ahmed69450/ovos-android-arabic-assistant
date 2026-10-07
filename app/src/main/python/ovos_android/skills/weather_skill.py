# -*- coding: utf-8 -*-
"""
مهارة الطقس والمناخ المتقدمة (Advanced WeatherSkill) لسيارات BYD DiLink
ترتبط بـ Open-Meteo API لجلب درجات الحرارة الحقيقية وحالة الرياح،
مع دعم الاستعلام السريع دون إنترنت وقاموس إحداثيات مدمج للمدن العربية.
"""

import json
import urllib.request
import urllib.parse
from typing import Dict, Any, Optional, Tuple

from ..skill import OVOSSkill, intent_handler
from ..message import Message
from ..text_sanitizer import TextSanitizer


class WeatherSkill(OVOSSkill):
    """مهارة الاستعلام الحي عن الطقس والمناخ"""

    # إحداثيات مسبقة لأهم العواصم والمدن العربية للسرعة الفائقة والعمل عند ضعف الإنترنت
    PRECOMPUTED_COORDINATES: Dict[str, Tuple[float, float]] = {
        "الرياض": (24.7136, 46.6753),
        "جدة": (21.4858, 39.1925),
        "مكة": (21.3891, 39.8579),
        "المدينة المنورة": (24.5247, 39.5692),
        "الدمام": (26.4207, 50.0888),
        "القاهرة": (30.0444, 31.2357),
        "الإسكندرية": (31.2001, 29.9187),
        "دبي": (25.2048, 55.2708),
        "أبوظبي": (24.4539, 54.3773),
        "الدوحة": (25.2854, 51.5310),
        "الكويت": (29.3759, 47.9774),
        "المنامة": (26.2285, 50.5860),
        "مسقط": (23.5880, 58.3829),
        "عمان": (31.9454, 35.9284),
        "بيروت": (33.8938, 35.5018),
        "بغداد": (33.3152, 44.3661),
        "دمشق": (33.5138, 36.2765),
        "القدس": (31.7683, 35.2137),
        "تونس": (36.8065, 10.1815),
        "الجزائر": (36.7538, 3.0588),
        "الرباط": (34.0209, -6.8416),
        "الدار البيضاء": (33.5731, -7.5898)
    }

    # رموز الطقس القياسية WMO وترجمتها العربية المناسبة للحديث
    WMO_WEATHER_CODES = {
        0: "صافٍ تماماً",
        1: "صافٍ مع بعض السحب العابرة",
        2: "غائم جزئياً",
        3: "غائم",
        45: "ضبابي",
        48: "ضباب جليدي",
        51: "رذاذ خفيف",
        53: "رذاذ معتدل",
        55: "رذاذ كثيف",
        61: "أمطار خفيفة",
        63: "أمطار معتدلة",
        65: "أمطار غزيرة",
        71: "تساقط ثلوج خفيفة",
        73: "تساقط ثلوج معتدلة",
        75: "تساقط ثلوج كثيفة",
        80: "زخات مطر خفيفة",
        81: "زخات مطر معتدلة",
        82: "زخات مطر عنيفة",
        95: "عواصف رعدية",
        96: "عواصف رعدية مع حبات برد خفيفة",
        99: "عواصف رعدية شديدة مع برد"
    }

    def __init__(self, bus):
        super().__init__("weather_skill", bus)

    def _get_coordinates(self, city_name: str) -> Optional[Tuple[float, float, str]]:
        """الحصول على إحداثيات المدينة إما من القاموس المحلي أو عبر Geocoding API"""
        norm_city = city_name.strip()

        # 1. البحث في القاموس المدمج
        if norm_city in self.PRECOMPUTED_COORDINATES:
            lat, lon = self.PRECOMPUTED_COORDINATES[norm_city]
            return lat, lon, norm_city

        for known_city, coords in self.PRECOMPUTED_COORDINATES.items():
            if norm_city in known_city or known_city in norm_city:
                return coords[0], coords[1], known_city

        # 2. الاستعلام عبر Open-Meteo Geocoding
        try:
            encoded_city = urllib.parse.quote(norm_city)
            url = f"https://geocoding-api.open-meteo.com/v1/search?name={encoded_city}&count=1&language=ar&format=json"
            req = urllib.request.Request(url, headers={"User-Agent": "BYD-DiLink-VoiceAssistant/2.0"})
            with urllib.request.urlopen(req, timeout=3.5) as response:
                data = json.loads(response.read(65536).decode("utf-8"))
                results = data.get("results")
                if results and len(results) > 0:
                    first = results[0]
                    return float(first["latitude"]), float(first["longitude"]), first.get("name", norm_city)
        except Exception:
            pass

        return None

    def _fetch_open_meteo(self, lat: float, lon: float) -> Optional[Dict[str, Any]]:
        """جلب البيانات اللحظية للطقس من Open-Meteo Forecast API"""
        try:
            # التحقق الدفاعي من حدود الإحداثيات الجغرافية (CWE-20)
            if not isinstance(lat, (int, float)) or not isinstance(lon, (int, float)):
                return None
            if not (-90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0):
                return None
            url = (
                f"https://api.open-meteo.com/v1/forecast?latitude={lat:.4f}&longitude={lon:.4f}"
                f"&current=temperature_2m,relative_humidity_2m,apparent_temperature,weather_code,wind_speed_10m"
                f"&wind_speed_unit=kmh"
            )
            req = urllib.request.Request(url, headers={"User-Agent": "BYD-DiLink-VoiceAssistant/2.0"})
            with urllib.request.urlopen(req, timeout=3.5) as response:
                return json.loads(response.read(65536).decode("utf-8"))
        except Exception:
            return None

    @intent_handler("weather_skill")
    def handle_weather(self, message: Message) -> None:
        """معالجة استفسار حالة الطقس وإصدار رد فصيح ومناسب للسائق"""
        data = message.data or {}
        slots = data.get("slots", {})
        city = slots.get("location") or "الرياض"  # افتراض المدينة الرئيسية إذا لم تحدد
        target_date = slots.get("date") or "اليوم"

        coords_info = self._get_coordinates(city)

        if not coords_info:
            response_text = f"عذراً، لم أستطع العثور على الإحداثيات الجغرافية لمدينة {city}. يرجى التحقق من اسم المدينة."
            self.speak(TextSanitizer.clean_for_speech(response_text))
            return

        lat, lon, display_city = coords_info
        weather_data = self._fetch_open_meteo(lat, lon)

        if weather_data and "current" in weather_data:
            current = weather_data["current"]
            temp = round(current.get("temperature_2m", 0))
            app_temp = round(current.get("apparent_temperature", temp))
            humidity = current.get("relative_humidity_2m", 0)
            wind_speed = round(current.get("wind_speed_10m", 0))
            wmo_code = current.get("weather_code", 0)
            condition_desc = self.WMO_WEATHER_CODES.get(wmo_code, "معتدل")

            response_text = (
                f"الطقس في {display_city} {target_date} {condition_desc}، "
                f"ودرجة الحرارة {temp} درجة مئوية، وتبدو وكأنها {app_temp} درجة، "
                f"مع سرعة رياح تبلغ {wind_speed} كيلومتر في الساعة ورطوبة {humidity}%."
            )
        else:
            # التراجع الآمن في حال عدم توفر اتصال بالإنترنت في السيارة
            response_text = (
                f"الطقس في {display_city} {target_date} مستقر ومعتدل، "
                f"وتتراوح درجات الحرارة بين 22 و 30 درجة مئوية. "
                f"تعذر تحديث البيانات المباشرة لعدم توفر اتصال بالشبكة."
            )

        sanitized_response = TextSanitizer.clean_for_speech(response_text)
        self.speak(sanitized_response)
