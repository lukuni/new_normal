"""Proposal classification: topic, sentiment, urgency.

Two classifiers share one interface:
  * RuleClassifier  - Mongolian stem matching (works offline, default).
  * LLMClassifier   - large language model via the Anthropic API, used when
                      ANTHROPIC_API_KEY is set; falls back to rules on error.

Mongolian is agglutinative ("сургууль" -> "сургуулийн", "оюутан" -> "оюутнууд"),
so rules match word *prefixes* (stems) on whole tokens rather than substrings.
This avoids false hits such as "ус" (water) inside "автобус".
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, asdict

import httpx

from .config import settings

CATEGORIES = [
    "Боловсрол",
    "Ажлын байр",
    "Орон сууц",
    "Агаар, байгаль орчин",
    "Эрүүл мэнд",
    "Тээвэр, түгжрэл",
    "Цахим засаглал",
    "Бусад",
]
SENTIMENTS = ["Сөрөг", "Төвийг сахисан", "Эерэг"]
URGENCIES = ["Өндөр", "Дунд", "Бага"]

# Stems are matched against the start of each token (after folding ө->о, ү->у).
CATEGORY_STEMS: dict[str, list[str]] = {
    "Боловсрол": ["сургуул", "сургал", "багш", "оюут", "боловсрол", "тэтгэлэг", "хичээл",
                  "цэцэрлэг", "их сургуул", "дотуур байр", "диплом", "шалгалт"],
    "Ажлын байр": ["ажлын байр", "ажилгүй", "ажил", "цалин", "хөдөлмөр", "дадлага", "стартап",
                   "бизнес", "ур чадвар", "үйлдвэрлэл", "мэргэжил"],
    "Орон сууц": ["орон сууц", "ипотек", "түрээс", "зээл", "урьдчилгаа", "гэр хороол", "байрны үнэ"],
    "Агаар, байгаль орчин": ["агаар", "утаа", "бохирд", "хог", "нуур", "голын", "байгал",
                             "халаагуур", "цэвэр ус", "мод тари", "уур амьсгал"],
    "Эрүүл мэнд": ["эмнэлг", "эрүүл", "сэтгэл зүй", "эмч", "даатгал", "спорт"],
    "Тээвэр, түгжрэл": ["түгжрэл", "автобус", "зам", "тээвэр", "метро", "дугуй", "явган"],
    "Цахим засаглал": ["цахим", "онлайн", "апп", "программ", "интернэт", "e-mongolia", "өгөгдөл",
                       "ил тод", "авлиг", "платформ", "төсөв"],
}
NEGATIVE = ["хүрэлцэхгүй", "хүнд", "муу", "бохир", "асуудал", "өндөр", "ажилгүй", "түгжрэл",
            "удаан", "хангалтгүй", "дутагдал", "авлиг", "үнэтэй", "хүртээмжгүй", "саад", "бага",
            "шийдэгдэхгүй", "гомдол", "хэцүү", "дутуу"]
POSITIVE = ["сайн", "дэмжи", "талархаж", "сайшаа", "амжилт", "үр дүнтэй", "таалагд",
            "сайжирсан", "баярла"]
URGENT = ["яаралтай", "маш", "аюул", "эрсдэл", "хүнд", "шууд", "нэн даруй", "амь", "осол"]

_LATIN2CYR = [("sh", "ш"), ("ch", "ч"), ("ts", "ц"), ("kh", "х"), ("ya", "я"), ("yu", "ю"),
              ("yo", "ё"), ("ye", "е"), ("a", "а"), ("b", "б"), ("v", "в"), ("w", "в"), ("g", "г"),
              ("d", "д"), ("e", "э"), ("j", "ж"), ("z", "з"), ("i", "и"), ("k", "к"), ("l", "л"),
              ("m", "м"), ("n", "н"), ("o", "о"), ("q", "ө"), ("p", "п"), ("r", "р"), ("s", "с"),
              ("t", "т"), ("u", "у"), ("f", "ф"), ("h", "х"), ("c", "ц"), ("y", "ы"), ("x", "х")]

_PII_PATTERNS = [
    (re.compile(r"\b[А-ЯӨҮа-яөү]{2}\d{8}\b"), "[РД]"),               # national register number
    (re.compile(r"\b(?:\+?976[\s-]?)?\d{4}[\s-]?\d{4}\b"), "[УТАС]"),  # phone numbers
    (re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+"), "[И-МЭЙЛ]"),
]


def scrub_pii(text: str) -> str:
    """Remove register numbers, phone numbers and e-mails before storage."""
    for pat, repl in _PII_PATTERNS:
        text = pat.sub(repl, text)
    return text


def latin_to_cyrillic(text: str) -> str:
    """Convert Mongolian written in Latin letters ("galig") to Cyrillic, best effort."""
    out, i, low = [], 0, text.lower()
    while i < len(low):
        for lat, cyr in _LATIN2CYR:
            if low.startswith(lat, i):
                out.append(cyr)
                i += len(lat)
                break
        else:
            out.append(low[i])
            i += 1
    return "".join(out)


def normalize(text: str) -> str:
    """Lower-case, convert galig to Cyrillic, fold ө/ү so stems match both spellings."""
    t = text.strip()
    letters = re.findall(r"[A-Za-zА-Яа-яӨөҮүЁё]", t)
    latin = sum(1 for ch in letters if ch.isascii())
    if letters and latin / len(letters) > 0.6 and "e-mongolia" not in t.lower():
        t = latin_to_cyrillic(t)
    t = t.lower()
    return _fold(t)


def _fold(s: str) -> str:
    return s.replace("ө", "о").replace("ү", "у").replace("ё", "е")


def _hits(norm_text: str, tokens: list[str], stems: list[str]) -> int:
    n = 0
    for stem in stems:
        s = _fold(stem.lower())
        if " " in s.strip():  # multi-word phrase: match as text
            if re.search(r"(^|[^а-яa-z])" + re.escape(s), norm_text):
                n += 1
        elif any(tok.startswith(s.strip()) for tok in tokens):
            n += 1
    return n


@dataclass
class Classification:
    category: str
    sentiment: str
    urgency: str
    confidence: float
    classifier: str
    scores: dict[str, int]

    def as_dict(self) -> dict:
        return asdict(self)


class RuleClassifier:
    name = "rules"

    def classify(self, text: str) -> Classification:
        norm = normalize(text)
        tokens = re.findall(r"[a-zа-яе-]+", norm)
        scores = {c: _hits(norm, tokens, stems) for c, stems in CATEGORY_STEMS.items()}
        best = max(scores, key=lambda c: scores[c])
        top = scores[best]
        category = best if top > 0 else "Бусад"
        neg = _hits(norm, tokens, NEGATIVE)
        pos = _hits(norm, tokens, POSITIVE)
        sentiment = "Сөрөг" if neg > pos else "Эерэг" if pos > neg else "Төвийг сахисан"
        u = _hits(norm, tokens, URGENT) + (1 if neg >= 2 else 0)
        urgency = "Өндөр" if u >= 2 else "Дунд" if u == 1 else "Бага"
        runner_up = sorted(scores.values(), reverse=True)[1] if len(scores) > 1 else 0
        # Confidence rises with keyword evidence and falls when two topics tie.
        conf = 0.45 + 0.12 * top + 0.03 * (neg + pos) - (0.15 if top and runner_up == top else 0)
        return Classification(category, sentiment, urgency, round(max(0.3, min(conf, 0.97)), 2),
                              self.name, scores)


LLM_PROMPT = """Та Монгол залуучуудын бодлогын саналыг ангилдаг туслах.
Дараах саналыг уншаад ЗӨВХӨН JSON буцаа:
{{"category": <{cats}>, "sentiment": <{sents}>, "urgency": <{urgs}>, "confidence": 0..1}}

Санал: \"\"\"{text}\"\"\""""


class LLMClassifier:
    name = "llm"

    def __init__(self, fallback: RuleClassifier):
        self.fallback = fallback

    def classify(self, text: str) -> Classification:
        rules = self.fallback.classify(text)
        try:
            prompt = LLM_PROMPT.format(cats=" | ".join(CATEGORIES), sents=" | ".join(SENTIMENTS),
                                       urgs=" | ".join(URGENCIES), text=text[:4000])
            r = httpx.post(
                "https://api.anthropic.com/v1/messages",
                headers={"x-api-key": settings.anthropic_api_key,
                         "anthropic-version": "2023-06-01", "content-type": "application/json"},
                json={"model": settings.llm_model, "max_tokens": 200,
                      "messages": [{"role": "user", "content": prompt}]},
                timeout=settings.llm_timeout_s,
            )
            r.raise_for_status()
            raw = "".join(b.get("text", "") for b in r.json().get("content", []))
            data = json.loads(raw[raw.index("{"): raw.rindex("}") + 1])
            if data["category"] not in CATEGORIES or data["sentiment"] not in SENTIMENTS \
                    or data["urgency"] not in URGENCIES:
                raise ValueError("label outside schema")
            return Classification(data["category"], data["sentiment"], data["urgency"],
                                  round(float(data.get("confidence", 0.8)), 2), self.name, rules.scores)
        except Exception:
            return rules  # never lose a proposal because the LLM is unavailable


_rules = RuleClassifier()


def get_classifier():
    return LLMClassifier(_rules) if settings.anthropic_api_key else _rules
