from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RequestIntent:
    output_type: str
    grounding: str | None
    confidence: str
    reason: str


_OUTPUT_MARKERS: dict[str, tuple[str, ...]] = {
    "embedding": ("embedding", "vector", "متجه", "تمثيل متجهي", "تشابه دلالي", "semantic similarity"),
    "live": ("live", "real time", "realtime", "websocket", "محادثة مباشرة", "محادثة صوتية", "صوتية مباشرة", "وقت حقيقي", "مكالمة صوتية"),
    "audio": ("text to speech", "tts", "voice", "audio output", "صوت", "صوتي", "اقرأ بصوت", "تحويل النص إلى كلام"),
    "video_generation": ("generate video", "create a video", "video generation", "توليد فيديو", "إنشاء فيديو"),
    "video_analysis": ("analyze video", "summarize video", "video understanding", "حلل الفيديو", "لخص الفيديو", "فهم الفيديو"),
    "image": ("generate image", "create an image", "draw", "image generation", "صورة", "صور", "ارسم", "توليد صورة", "إنشاء صورة"),
}

_GROUNDING_MARKERS: dict[str, tuple[str, ...]] = {
    "maps": ("google maps", "maps grounding", "map grounding", "near me", "nearby", "بالقرب مني", "موقعي", "مطاعم قريبة", "خرائط"),
    "search": ("grounding", "google search", "web search", "search grounding", "ابحث", "مصادر حديثة", "الويب", "آخر الأخبار", "حاليًا", "الآن"),
}


def detect_intent(user_prompt: str, *, output_type: str = "auto", grounding: str | None = None) -> RequestIntent:
    prompt = str(user_prompt or "").strip().lower()
    if output_type and output_type != "auto":
        resolved_output = output_type
        confidence = "explicit"
        reason = "output_type supplied by caller"
    else:
        resolved_output = "text"
        confidence = "default"
        reason = "no specialized output marker found"
        for candidate, markers in _OUTPUT_MARKERS.items():
            if any(marker in prompt for marker in markers):
                resolved_output = candidate
                confidence = "heuristic"
                reason = f"matched {candidate} marker"
                break

    if grounding and grounding != "auto":
        resolved_grounding = grounding
    else:
        resolved_grounding = None
        for candidate, markers in _GROUNDING_MARKERS.items():
            if any(marker in prompt for marker in markers):
                resolved_grounding = candidate
                break
    return RequestIntent(resolved_output, resolved_grounding, confidence, reason)
