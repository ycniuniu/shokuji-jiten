"""Shared helpers for nutrition data pipeline."""
from __future__ import annotations

import json
import math
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "data" / "raw"
DB_PATH = ROOT / "data" / "food.db"
SOURCE_STATUS_PATH = ROOT / "data" / "source_status.json"

# Default 常见份量 references (grams) by rough category keywords
SERVING_DEFAULTS = [
    (r"米|饭|粥|麺|面|饭|rice|noodle|pasta", "一碗约 150 g"),
    (r"面包|吐司|bread|bagel", "一片约 30 g"),
    (r"蛋|egg", "一枚约 50 g"),
    (r"奶|乳|milk|yogurt|牛乳", "一杯约 200 ml / 200 g"),
    (r"苹果|香蕉|橙|果|apple|banana|orange|fruit", "一个约 150 g"),
    (r"菜|蔬|vegetable|salad", "一小碟约 100 g"),
    (r"肉|鸡|猪|牛|鱼|meat|chicken|pork|beef|fish", "一份约 80 g"),
    (r"油|oil|butter", "一汤匙约 10 g"),
    (r"坚果|nut|seed", "一小把约 20 g"),
]


def ensure_dirs() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    (ROOT / "public" / "images").mkdir(parents=True, exist_ok=True)
    (ROOT / "data").mkdir(parents=True, exist_ok=True)


def parse_num(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
            return None
        return float(value)
    s = str(value).strip()
    if not s or s in {"-", "—", "–", "Tr", "tr", "Trace", "NA", "N", "nil", "*", "n.d.", "ND"}:
        return None
    s = s.replace(",", ".")
    m = re.search(r"-?\d+(?:\.\d+)?", s)
    if not m:
        return None
    try:
        return float(m.group(0))
    except ValueError:
        return None


def infer_serving(name: str, category: str | None = None) -> str:
    text = f"{name or ''} {category or ''}"
    for pattern, serving in SERVING_DEFAULTS:
        if re.search(pattern, text, re.IGNORECASE):
            return serving
    return "常见份量约 100 g（按每 100 g 换算）"


def empty_food(**kwargs: Any) -> dict[str, Any]:
    base = {
        "name": None,
        "name_en": None,
        "source_country": None,
        "source_id": None,
        "category": None,
        "kcal_100g": None,
        "protein_g": None,
        "fat_g": None,
        "carbs_g": None,
        "sodium_mg": None,
        "calcium_mg": None,
        "iron_mg": None,
        "zinc_mg": None,
        "selenium_ug": None,
        "vitamin_a_ug": None,
        "vitamin_c_mg": None,
        "vitamin_d_ug": None,
        "vitamin_e_mg": None,
        "vitamin_b1_mg": None,
        "vitamin_b2_mg": None,
        "vitamin_b3_mg": None,
        "serving_ref": None,
        "image_path": None,
        "raw_json": None,
    }
    base.update(kwargs)
    if not base.get("serving_ref"):
        base["serving_ref"] = infer_serving(base.get("name") or "", base.get("category"))
    return base


def save_status(status: dict[str, Any]) -> None:
    SOURCE_STATUS_PATH.write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8")


def load_status() -> dict[str, Any]:
    if SOURCE_STATUS_PATH.exists():
        return json.loads(SOURCE_STATUS_PATH.read_text(encoding="utf-8"))
    return {}
