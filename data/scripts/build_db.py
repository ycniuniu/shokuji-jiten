#!/usr/bin/env python3
"""Normalize raw sources into unified SQLite DB + match Food-101 images."""
from __future__ import annotations

import json
import re
import sqlite3
import sys
from pathlib import Path

from common import (
    DB_PATH,
    RAW_DIR,
    ROOT,
    empty_food,
    ensure_dirs,
    infer_serving,
    load_status,
    parse_num,
    save_status,
)

SCHEMA = (Path(__file__).parent / "schema.sql").read_text(encoding="utf-8")

# Food-101 class names → Chinese aliases for matching
FOOD101_ALIASES: dict[str, list[str]] = {
    "apple_pie": ["苹果派", "苹果馅饼"],
    "baby_back_ribs": ["肋排", "猪肋排"],
    "baklava": ["果仁蜜饼"],
    "beef_carpaccio": ["生牛肉片"],
    "beef_tartare": ["鞑靼牛肉"],
    "beet_salad": ["甜菜沙拉"],
    "beignets": ["贝奈特炸面圈"],
    "bibimbap": ["拌饭", "石锅拌饭"],
    "bread_pudding": ["面包布丁"],
    "breakfast_burrito": ["早餐卷饼"],
    "bruschetta": ["意式烤面包"],
    "caesar_salad": ["凯撒沙拉"],
    "cannoli": ["卡诺里"],
    "caprese_salad": ["卡普里沙拉"],
    "carrot_cake": ["胡萝卜蛋糕"],
    "ceviche": ["酸橘汁腌鱼"],
    "cheese_plate": ["奶酪拼盘", "奶酪"],
    "cheesecake": ["芝士蛋糕", "起司蛋糕"],
    "chicken_curry": ["咖喱鸡"],
    "chicken_quesadilla": ["鸡肉玉米饼"],
    "chicken_wings": ["鸡翅"],
    "chocolate_cake": ["巧克力蛋糕"],
    "chocolate_mousse": ["巧克力慕斯"],
    "churros": ["吉拿棒"],
    "clam_chowder": ["蛤蜊浓汤"],
    "club_sandwich": ["俱乐部三明治"],
    "crab_cakes": ["蟹饼"],
    "creme_brulee": ["焦糖布丁"],
    "croque_madame": ["法式火腿三明治"],
    "cup_cakes": ["纸杯蛋糕"],
    "deviled_eggs": ["魔鬼蛋"],
    "donuts": ["甜甜圈", "多拿滋"],
    "dumplings": ["饺子", "水饺", "饺子"],
    "edamame": ["毛豆", "枝豆"],
    "eggs_benedict": ["班尼迪克蛋"],
    "escargots": ["蜗牛"],
    "falafel": ["法拉费"],
    "filet_mignon": ["菲力牛排"],
    "fish_and_chips": ["炸鱼薯条"],
    "foie_gras": ["鹅肝"],
    "french_fries": ["薯条", "炸薯条"],
    "french_onion_soup": ["法式洋葱汤"],
    "french_toast": ["法式吐司"],
    "fried_calamari": ["炸鱿鱼"],
    "fried_rice": ["炒饭", "蛋炒饭"],
    "frozen_yogurt": ["冻酸奶"],
    "garlic_bread": ["蒜香面包"],
    "gnocchi": ["意大利饺子"],
    "greek_salad": ["希腊沙拉"],
    "grilled_cheese_sandwich": ["烤奶酪三明治"],
    "grilled_salmon": ["烤三文鱼", "烤鲑鱼"],
    "guacamole": ["牛油果酱"],
    "gyoza": ["锅贴", "煎饺"],
    "hamburger": ["汉堡", "汉堡包"],
    "hot_and_sour_soup": ["酸辣汤"],
    "hot_dog": ["热狗"],
    "huevos_rancheros": ["墨西哥炸蛋"],
    "hummus": ["鹰嘴豆泥"],
    "ice_cream": ["冰淇淋", "冰激凌"],
    "lasagna": ["千层面"],
    "lobster_bisque": ["龙虾浓汤"],
    "lobster_roll_sandwich": ["龙虾卷"],
    "macaroni_and_cheese": ["芝士通心粉", "通心粉"],
    "macarons": ["马卡龙"],
    "miso_soup": ["味噌汤", "味增汤"],
    "mussels": ["贻贝", "淡菜"],
    "nachos": ["墨西哥玉米片"],
    "omelette": ["煎蛋卷", "蛋饼", "オムレツ"],
    "onion_rings": ["洋葱圈"],
    "oysters": ["牡蛎", "生蚝"],
    "pad_thai": ["泰式炒河粉"],
    "paella": ["西班牙海鲜饭"],
    "pancakes": ["松饼", "煎饼"],
    "panna_cotta": ["意式奶冻"],
    "peking_duck": ["北京烤鸭", "烤鸭"],
    "pho": ["越南粉", "河粉"],
    "pizza": ["披萨", "比萨"],
    "pork_chop": ["猪排"],
    "poutine": ["肉汁薯条"],
    "prime_rib": ["肋眼牛排"],
    "pulled_pork_sandwich": ["手撕猪肉三明治"],
    "ramen": ["拉面", "ラーメン"],
    "ravioli": ["意大利馄饨"],
    "red_velvet_cake": ["红丝绒蛋糕"],
    "risotto": ["意式烩饭"],
    "samosa": ["萨莫萨"],
    "sashimi": ["刺身", "生鱼片"],
    "scallops": ["扇贝"],
    "seaweed_salad": ["海藻沙拉"],
    "shrimp_and_grits": ["虾仁玉米粥"],
    "spaghetti_bolognese": ["肉酱意面"],
    "spaghetti_carbonara": ["培根蛋面"],
    "spring_rolls": ["春卷"],
    "steak": ["牛排"],
    "strawberry_shortcake": ["草莓蛋糕"],
    "sushi": ["寿司", "すし"],
    "tacos": ["塔可", "墨西哥卷"],
    "takoyaki": ["章鱼烧"],
    "tiramisu": ["提拉米苏"],
    "tuna_tartare": ["金枪鱼鞑靼"],
    "waffles": ["华夫饼"],
}

# Extra keyword → food101 for East Asian staples
EXTRA_MATCHES = [
    (r"米饭|白饭|白米|ご飯|쌀밥|rice(?!.*pudding)", "fried_rice"),
    (r"豆腐|tofu|두부", "edamame"),
    (r"牛奶|牛乳|milk", "frozen_yogurt"),
    (r"鸡蛋|雞蛋|卵|egg(?!s_)", "omelette"),
    (r"苹果|蘋果|りんご|사과|apple", "apple_pie"),
    (r"香蕉|バナナ|바나나|banana", "pancakes"),
    (r"土豆|马铃薯|じゃがいも|감자|potato", "french_fries"),
    (r"番茄|西红柿|トマト|토마토|tomato", "caprese_salad"),
    (r"面包|麵包|パン|빵|bread", "garlic_bread"),
    (r"酸奶|優格|ヨーグルト|yogurt", "frozen_yogurt"),
    (r"三文鱼|鲑鱼|サーモン|연어|salmon", "grilled_salmon"),
    (r"鸡|雞|鶏|닭|chicken", "chicken_wings"),
    (r"牛肉|ビーフ|소고기|beef", "steak"),
    (r"猪肉|豚肉|돼지고기|pork", "pork_chop"),
    (r"鱼|魚|魚|생선|fish", "grilled_salmon"),
    (r"虾|蝦|エビ|새우|shrimp", "shrimp_and_grits"),
    (r"面条|麵條|麺|국수|noodle", "ramen"),
    (r"汤|湯|スープ|국|soup", "miso_soup"),
    (r"沙拉|サラダ|샐러드|salad", "greek_salad"),
    (r"蛋糕|ケーキ|케이크|cake", "chocolate_cake"),
]


def match_image(name: str, name_en: str | None = None) -> str | None:
    text = f"{name or ''} {name_en or ''}".lower()
    for cls, aliases in FOOD101_ALIASES.items():
        label = cls.replace("_", " ")
        if label in text or cls in text.replace(" ", "_"):
            return f"/images/{cls}.jpg"
        for a in aliases:
            if a.lower() in text:
                return f"/images/{cls}.jpg"
    for pattern, cls in EXTRA_MATCHES:
        if re.search(pattern, text, re.IGNORECASE):
            return f"/images/{cls}.jpg"
    return None


def load_json_files(folder: Path) -> list:
    rows = []
    if not folder.exists():
        return rows
    for p in sorted(folder.rglob("*")):
        if p.suffix.lower() == ".json":
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                if isinstance(data, list):
                    rows.extend(data)
                elif isinstance(data, dict):
                    rows.append(data)
            except Exception:
                continue
    return rows


def normalize_china() -> list[dict]:
    foods = []
    folder = RAW_DIR / "china"
    for p in sorted(folder.glob("*.json")) if folder.exists() else []:
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        category = p.stem
        if not isinstance(data, list):
            continue
        for row in data:
            name = row.get("foodName") or row.get("food_name")
            if not name:
                continue
            f = empty_food(
                name=str(name).strip(),
                name_en=(row.get("englishName") or row.get("foodNameEn") or None),
                source_country="CN",
                source_id=str(row.get("foodCode") or ""),
                category=category,
                kcal_100g=parse_num(row.get("energyKCal") or row.get("energy_kcal")),
                protein_g=parse_num(row.get("protein")),
                fat_g=parse_num(row.get("fat")),
                carbs_g=parse_num(row.get("CHO") or row.get("carbohydrate")),
                sodium_mg=parse_num(row.get("Na") or row.get("sodium")),
                calcium_mg=parse_num(row.get("Ca")),
                iron_mg=parse_num(row.get("Fe")),
                zinc_mg=parse_num(row.get("Zn")),
                selenium_ug=parse_num(row.get("Se")),
                vitamin_a_ug=parse_num(row.get("vitaminA")),
                vitamin_c_mg=parse_num(row.get("vitaminC")),
                vitamin_e_mg=parse_num(row.get("vitaminETotal")),
                vitamin_b1_mg=parse_num(row.get("thiamin")),
                vitamin_b2_mg=parse_num(row.get("riboflavin")),
                vitamin_b3_mg=parse_num(row.get("niacin")),
                raw_json=json.dumps(row, ensure_ascii=False),
            )
            foods.append(f)
    return foods


def normalize_japan() -> list[dict]:
    foods = []
    folder = RAW_DIR / "japan"
    if not folder.exists():
        return foods

    def from_jp_row(row: dict) -> dict | None:
        name = row.get("foodName") or row.get("name") or row.get("食品名")
        if not name:
            return None
        return empty_food(
            name=str(name).strip(),
            source_country="JP",
            source_id=str(row.get("foodId") or row.get("foodCode") or row.get("code") or ""),
            category=str(row.get("groupId") or row.get("category") or row.get("group") or ""),
            kcal_100g=parse_num(row.get("enercKcal") or row.get("ENERC_KCAL") or row.get("energy_kcal")),
            protein_g=parse_num(row.get("prot") or row.get("protein")),
            fat_g=parse_num(row.get("fat")),
            carbs_g=parse_num(row.get("chocdf") or row.get("choavldf") or row.get("carbohydrate")),
            sodium_mg=parse_num(row.get("na") or row.get("sodium")),
            calcium_mg=parse_num(row.get("ca")),
            iron_mg=parse_num(row.get("fe")),
            zinc_mg=parse_num(row.get("zn")),
            selenium_ug=parse_num(row.get("se")),
            vitamin_a_ug=parse_num(row.get("vitarae") or row.get("vita") or row.get("retol")),
            vitamin_c_mg=parse_num(row.get("vitc")),
            vitamin_d_ug=parse_num(row.get("vitd")),
            vitamin_e_mg=parse_num(row.get("vitentra") or row.get("tocpha")),
            vitamin_b1_mg=parse_num(row.get("thia")),
            vitamin_b2_mg=parse_num(row.get("ribf")),
            vitamin_b3_mg=parse_num(row.get("nia")),
            raw_json=None,
        )

    details_path = folder / "details.json"
    if details_path.exists():
        for row in json.loads(details_path.read_text(encoding="utf-8")):
            if isinstance(row, dict):
                f = from_jp_row(row)
                if f:
                    foods.append(f)
        if foods:
            return foods

    for row in load_json_files(folder):
        if isinstance(row, dict):
            f = from_jp_row(row)
            if f:
                foods.append(f)
    return foods


def normalize_csv_like(folder: Path, country: str, name_cols, mapping: dict) -> list[dict]:
    foods = []
    if not folder.exists():
        return foods
    try:
        import pandas as pd
    except ImportError:
        return foods

    for p in list(folder.rglob("*.csv")) + list(folder.rglob("*.xlsx")) + list(folder.rglob("*.xls")):
        try:
            if p.suffix.lower() == ".csv":
                df = pd.read_csv(p, encoding="utf-8", low_memory=False)
            else:
                df = pd.read_excel(p)
        except Exception:
            try:
                df = pd.read_csv(p, encoding="latin-1", low_memory=False)
            except Exception:
                continue
        cols = {c.lower().strip(): c for c in df.columns}

        def col(*names):
            for n in names:
                if n.lower() in cols:
                    return cols[n.lower()]
            return None

        name_col = None
        for nc in name_cols:
            name_col = col(nc)
            if name_col:
                break
        if not name_col:
            continue

        for _, row in df.iterrows():
            name = row.get(name_col)
            if name is None or str(name).strip() == "" or str(name) == "nan":
                continue
            kwargs = {
                "name": str(name).strip(),
                "source_country": country,
                "raw_json": json.dumps({k: (None if (isinstance(v, float) and v != v) else v) for k, v in row.items()}, ensure_ascii=False, default=str),
            }
            for field, candidates in mapping.items():
                for cand in candidates:
                    c = col(cand)
                    if c is not None:
                        kwargs[field] = parse_num(row.get(c))
                        break
            foods.append(empty_food(**kwargs))
    return foods


def _normalize_simple_json(folder: Path, country: str) -> list[dict]:
    foods = []
    for row in load_json_files(folder):
        if not isinstance(row, dict):
            continue
        name = row.get("food_name") or row.get("name") or row.get("식품명")
        if not name:
            continue
        foods.append(
            empty_food(
                name=str(name).strip(),
                name_en=row.get("name_en"),
                source_country=country,
                source_id=str(row.get("id") or row.get("source_id") or ""),
                category=row.get("category"),
                kcal_100g=parse_num(row.get("kcal") or row.get("kcal_100g") or row.get("energy")),
                protein_g=parse_num(row.get("protein") or row.get("protein_g")),
                fat_g=parse_num(row.get("fat") or row.get("fat_g")),
                carbs_g=parse_num(row.get("carbs") or row.get("carbs_g") or row.get("carbohydrate")),
                sodium_mg=parse_num(row.get("sodium") or row.get("sodium_mg")),
                calcium_mg=parse_num(row.get("calcium") or row.get("calcium_mg")),
                iron_mg=parse_num(row.get("iron") or row.get("iron_mg")),
                zinc_mg=parse_num(row.get("zinc") or row.get("zinc_mg")),
                selenium_ug=parse_num(row.get("selenium") or row.get("selenium_ug")),
                vitamin_c_mg=parse_num(row.get("vitamin_c") or row.get("vitamin_c_mg")),
            )
        )
    return foods


def normalize_korea() -> list[dict]:
    foods = _normalize_simple_json(RAW_DIR / "korea", "KR")
    foods.extend(
        normalize_csv_like(
            RAW_DIR / "korea",
            "KR",
            ["식품명", "food_name", "name", "식품이름"],
            {
                "kcal_100g": ["에너지(kcal)", "energy", "kcal", "열량"],
                "protein_g": ["단백질", "protein"],
                "fat_g": ["지방", "fat"],
                "carbs_g": ["탄수화물", "carbohydrate", "carbs"],
                "sodium_mg": ["나트륨", "sodium", "na"],
                "calcium_mg": ["칼슘", "calcium", "ca"],
                "iron_mg": ["철", "iron", "fe"],
                "zinc_mg": ["아연", "zinc", "zn"],
                "selenium_ug": ["셀레늄", "selenium", "se"],
                "vitamin_c_mg": ["비타민c", "vitamin c", "vitc"],
            },
        )
    )
    return foods


def normalize_singapore() -> list[dict]:
    foods = _normalize_simple_json(RAW_DIR / "singapore", "SG")
    foods.extend(
        normalize_csv_like(
            RAW_DIR / "singapore",
            "SG",
            ["food_name", "name", "Food Name"],
            {
                "kcal_100g": ["energy_kcal", "kcal", "Energy"],
                "protein_g": ["protein", "Protein"],
                "fat_g": ["fat", "total_fat", "Fat"],
                "carbs_g": ["carbohydrate", "carbs", "Carbohydrate"],
                "sodium_mg": ["sodium", "Sodium"],
                "calcium_mg": ["calcium", "Calcium"],
                "iron_mg": ["iron", "Iron"],
            },
        )
    )
    return foods


def normalize_usa() -> list[dict]:
    foods = []
    folder = RAW_DIR / "usa"
    if not folder.exists():
        return foods

    def from_fdc_food(item: dict) -> dict | None:
        name = item.get("description") or item.get("foodDescription")
        if not name:
            return None
        nutrients = {}
        for n in item.get("foodNutrients") or []:
            nut = n.get("nutrient") or {}
            nid = nut.get("id") or n.get("nutrientId") or nut.get("number")
            amount = n.get("amount") if "amount" in n else n.get("value")
            nutrients[str(nid)] = amount
            nutrients[(nut.get("name") or "").lower()] = amount

        def by_id(*ids, names=()):
            for i in ids:
                if str(i) in nutrients:
                    return parse_num(nutrients[str(i)])
            for nm in names:
                if nm.lower() in nutrients:
                    return parse_num(nutrients[nm.lower()])
            return None

        return empty_food(
            name=str(name).strip(),
            name_en=str(name).strip(),
            source_country="US",
            source_id=str(item.get("fdcId") or item.get("ndbNumber") or ""),
            category=(item.get("foodCategory") or {}).get("description")
            if isinstance(item.get("foodCategory"), dict)
            else item.get("foodCategory"),
            kcal_100g=by_id(1008, names=("energy",)),
            protein_g=by_id(1003, names=("protein",)),
            fat_g=by_id(1004, names=("total lipid (fat)",)),
            carbs_g=by_id(1005, names=("carbohydrate, by difference",)),
            sodium_mg=by_id(1093, names=("sodium, na",)),
            calcium_mg=by_id(1087, names=("calcium, ca",)),
            iron_mg=by_id(1089, names=("iron, fe",)),
            zinc_mg=by_id(1095, names=("zinc, zn",)),
            selenium_ug=by_id(1103, names=("selenium, se",)),
            vitamin_a_ug=by_id(1106, names=("vitamin a, rae",)),
            vitamin_c_mg=by_id(1162, names=("vitamin c, total ascorbic acid",)),
            vitamin_d_ug=by_id(1114, names=("vitamin d (d2 + d3)",)),
            vitamin_e_mg=by_id(1109, names=("vitamin e (alpha-tocopherol)",)),
            vitamin_b1_mg=by_id(1165, names=("thiamin",)),
            vitamin_b2_mg=by_id(1166, names=("riboflavin",)),
            vitamin_b3_mg=by_id(1167, names=("niacin",)),
            raw_json=None,
        )

    # Walk JSON files (SR Legacy can be ~200MB — stream via ijson if present, else json)
    for p in folder.rglob("*.json"):
        if p.stat().st_size > 80_000_000:
            # Prefer Foundation; for huge SR Legacy take every Nth food via regex-light chunking
            try:
                import ijson  # type: ignore
            except ImportError:
                # Load once — VM should handle ~200MB
                pass
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"USA skip {p.name}: {e}")
            continue
        items = []
        if isinstance(data, list):
            items = data
        elif isinstance(data, dict):
            for key in ("FoundationFoods", "SRLegacyFoods", "foods", "Foods"):
                if key in data and isinstance(data[key], list):
                    items = data[key]
                    break
            if not items and "description" in data:
                items = [data]
        # Cap SR Legacy to keep DB nimble for v1 while still shipping thousands of US foods
        if "sr_legacy" in str(p).lower() and len(items) > 4000:
            items = items[:4000]
        for item in items:
            if isinstance(item, dict):
                f = from_fdc_food(item)
                if f:
                    foods.append(f)
    return foods


def normalize_uk() -> list[dict]:
    foods = []
    folder = RAW_DIR / "uk"
    for row in load_json_files(folder):
        if not isinstance(row, dict):
            continue
        name = row.get("food_name") or row.get("name") or row.get("Food Name")
        if not name and "proximates" in row:
            name = row.get("food_name") or row.get("description")
        if not name:
            continue
        prox = row.get("proximates") or row.get("nutrients") or row
        minerals = row.get("minerals") or {}
        vitamins = row.get("vitamins") or {}

        def g(obj, *keys):
            if not isinstance(obj, dict):
                return None
            for k in keys:
                if k in obj:
                    v = obj[k]
                    if isinstance(v, dict):
                        return parse_num(v.get("value") or v.get("per_100g"))
                    return parse_num(v)
            return None

        foods.append(
            empty_food(
                name=str(name).strip(),
                name_en=str(name).strip(),
                source_country="UK",
                source_id=str(row.get("food_code") or row.get("code") or ""),
                category=row.get("food_group") or row.get("group"),
                kcal_100g=g(prox, "energy_kcal", "Energy (kcal)", "kcal") or parse_num(row.get("energy_kcal")),
                protein_g=g(prox, "protein", "Protein") or parse_num(row.get("protein")),
                fat_g=g(prox, "fat", "Fat") or parse_num(row.get("fat")),
                carbs_g=g(prox, "carbohydrate", "Carbohydrate") or parse_num(row.get("carbohydrate")),
                sodium_mg=g(minerals, "sodium", "Sodium") or parse_num(row.get("sodium")),
                calcium_mg=g(minerals, "calcium", "Calcium"),
                iron_mg=g(minerals, "iron", "Iron"),
                zinc_mg=g(minerals, "zinc", "Zinc"),
                selenium_ug=g(minerals, "selenium", "Selenium"),
                vitamin_c_mg=g(vitamins, "vitamin_c", "Vitamin C"),
                raw_json=json.dumps(row, ensure_ascii=False, default=str),
            )
        )
    foods.extend(
        normalize_csv_like(
            folder,
            "UK",
            ["Food Name", "food_name", "name"],
            {
                "kcal_100g": ["Energy (kcal)", "energy_kcal", "kcal"],
                "protein_g": ["Protein", "protein"],
                "fat_g": ["Fat", "fat"],
                "carbs_g": ["Carbohydrate", "carbohydrate"],
                "sodium_mg": ["Sodium", "sodium"],
                "calcium_mg": ["Calcium", "calcium"],
                "iron_mg": ["Iron", "iron"],
            },
        )
    )
    return foods


def _find_col(columns: list, *needles: str):
    lower = {str(c).lower(): c for c in columns}
    for n in needles:
        nl = n.lower()
        if nl in lower:
            return lower[nl]
        for k, orig in lower.items():
            if nl in k:
                return orig
    return None


def normalize_france() -> list[dict]:
    foods = []
    folder = RAW_DIR / "france"
    if not folder.exists():
        return foods
    try:
        import pandas as pd
    except ImportError:
        return foods

    for p in list(folder.glob("*.xls")) + list(folder.glob("*.xlsx")) + list(folder.glob("*.csv")):
        try:
            df = pd.read_csv(p) if p.suffix.lower() == ".csv" else pd.read_excel(p)
        except Exception:
            continue
        name_c = _find_col(list(df.columns), "alim_nom_fr", "alim_nom_eng")
        if not name_c:
            continue
        kcal_c = _find_col(list(df.columns), "kcal/100 g", "energie")
        # Prefer EU regulation kcal column
        for c in df.columns:
            if "1169/2011" in str(c) and "kcal" in str(c).lower():
                kcal_c = c
                break
        pro_c = _find_col(list(df.columns), "Protéines, N x 6.25", "proteines")
        fat_c = _find_col(list(df.columns), "Lipides (g/100 g)", "lipides")
        carb_c = _find_col(list(df.columns), "Glucides (g/100 g)", "glucides")
        na_c = _find_col(list(df.columns), "Sodium (mg/100 g)", "sodium")
        ca_c = _find_col(list(df.columns), "Calcium (mg/100 g)", "calcium")
        fe_c = _find_col(list(df.columns), "Fer (mg/100 g)", "fer (mg")
        zn_c = _find_col(list(df.columns), "Zinc (mg/100 g)", "zinc (mg")
        se_c = _find_col(list(df.columns), "Sélénium", "selenium")
        vc_c = _find_col(list(df.columns), "Vitamine C", "vitamine c")
        cat_c = _find_col(list(df.columns), "alim_grp_nom_fr")
        en_c = _find_col(list(df.columns), "alim_nom_eng")
        code_c = _find_col(list(df.columns), "alim_code")

        for _, row in df.iterrows():
            name = row.get(name_c)
            if name is None or str(name).strip() in {"", "nan"}:
                continue
            foods.append(
                empty_food(
                    name=str(name).strip(),
                    name_en=str(row.get(en_c)).strip() if en_c and row.get(en_c) == row.get(en_c) else None,
                    source_country="FR",
                    source_id=str(row.get(code_c) or "") if code_c else "",
                    category=str(row.get(cat_c) or "") if cat_c else None,
                    kcal_100g=parse_num(row.get(kcal_c)) if kcal_c else None,
                    protein_g=parse_num(row.get(pro_c)) if pro_c else None,
                    fat_g=parse_num(row.get(fat_c)) if fat_c else None,
                    carbs_g=parse_num(row.get(carb_c)) if carb_c else None,
                    sodium_mg=parse_num(row.get(na_c)) if na_c else None,
                    calcium_mg=parse_num(row.get(ca_c)) if ca_c else None,
                    iron_mg=parse_num(row.get(fe_c)) if fe_c else None,
                    zinc_mg=parse_num(row.get(zn_c)) if zn_c else None,
                    selenium_ug=parse_num(row.get(se_c)) if se_c else None,
                    vitamin_c_mg=parse_num(row.get(vc_c)) if vc_c else None,
                )
            )
    return foods


def normalize_germany() -> list[dict]:
    foods = []
    folder = RAW_DIR / "germany"
    if not folder.exists():
        return foods
    try:
        import pandas as pd
    except ImportError:
        return foods

    for p in folder.rglob("*.xlsx"):
        if "Daten" not in p.name and "daten" not in p.name.lower():
            # still try
            pass
        try:
            df = pd.read_excel(p)
        except Exception:
            continue
        cols = list(df.columns)
        name_c = _find_col(cols, "Lebensmittelbezeichnung", "Food name")
        en_c = _find_col(cols, "Food name")
        code_c = _find_col(cols, "BLS Code")
        kcal_c = _find_col(cols, "ENERCC Energie")
        pro_c = _find_col(cols, "PROT625 Protein", "PROT Protein")
        fat_c = _find_col(cols, "FAT Fett")
        carb_c = _find_col(cols, "CHO Kohlenhydrate")
        na_c = _find_col(cols, "NA Natrium", "NA Sodium")
        ca_c = _find_col(cols, "CA Calcium")
        fe_c = _find_col(cols, "FE Eisen", "FE Iron")
        zn_c = _find_col(cols, "ZN Zink", "ZN Zinc")
        se_c = _find_col(cols, "SE Selen", "SE Selenium")
        vc_c = _find_col(cols, "VITC Vitamin C")
        if not name_c:
            continue
        for _, row in df.iterrows():
            name = row.get(name_c)
            if name is None or str(name).strip() in {"", "nan"}:
                continue
            foods.append(
                empty_food(
                    name=str(name).strip(),
                    name_en=str(row.get(en_c)).strip() if en_c and pd.notna(row.get(en_c)) else None,
                    source_country="DE",
                    source_id=str(row.get(code_c) or "") if code_c else "",
                    category=str(row.get(code_c))[0] if code_c and row.get(code_c) else None,
                    kcal_100g=parse_num(row.get(kcal_c)) if kcal_c else None,
                    protein_g=parse_num(row.get(pro_c)) if pro_c else None,
                    fat_g=parse_num(row.get(fat_c)) if fat_c else None,
                    carbs_g=parse_num(row.get(carb_c)) if carb_c else None,
                    sodium_mg=parse_num(row.get(na_c)) if na_c else None,
                    calcium_mg=parse_num(row.get(ca_c)) if ca_c else None,
                    iron_mg=parse_num(row.get(fe_c)) if fe_c else None,
                    zinc_mg=parse_num(row.get(zn_c)) if zn_c else None,
                    selenium_ug=parse_num(row.get(se_c)) if se_c else None,
                    vitamin_c_mg=parse_num(row.get(vc_c)) if vc_c else None,
                )
            )
    return foods


def normalize_uk_cofid() -> list[dict]:
    """Parse CoFID 2021 multi-sheet workbook."""
    foods: dict[str, dict] = {}
    folder = RAW_DIR / "uk"
    if not folder.exists():
        return []
    try:
        import pandas as pd
    except ImportError:
        return []

    xlsx = folder / "cofid_2021.xlsx"
    if not xlsx.exists():
        return normalize_uk()

    def upsert(code: str, name: str, group: str | None = None) -> dict:
        if code not in foods:
            foods[code] = empty_food(
                name=name.strip(),
                name_en=name.strip(),
                source_country="UK",
                source_id=code,
                category=group,
            )
        return foods[code]

    try:
        prox = pd.read_excel(xlsx, sheet_name="1.3 Proximates")
        # Expected columns include Food Code, Food Name, Energy (kcal), Protein, Fat, Carbohydrate
        code_c = _find_col(list(prox.columns), "Food Code", "Foodcode")
        name_c = _find_col(list(prox.columns), "Food Name", "Foodname")
        group_c = _find_col(list(prox.columns), "Food Group", "Main Group")
        kcal_c = _find_col(list(prox.columns), "Energy (kcal)", "kcal")
        pro_c = _find_col(list(prox.columns), "Protein")
        fat_c = _find_col(list(prox.columns), "Fat")
        carb_c = _find_col(list(prox.columns), "Carbohydrate")
        for _, row in prox.iterrows():
            code = str(row.get(code_c) or "").strip()
            name = row.get(name_c)
            if not code or name is None or str(name).strip() in {"", "nan"}:
                continue
            f = upsert(code, str(name), str(row.get(group_c)) if group_c else None)
            f["kcal_100g"] = parse_num(row.get(kcal_c)) if kcal_c else f.get("kcal_100g")
            f["protein_g"] = parse_num(row.get(pro_c)) if pro_c else f.get("protein_g")
            f["fat_g"] = parse_num(row.get(fat_c)) if fat_c else f.get("fat_g")
            f["carbs_g"] = parse_num(row.get(carb_c)) if carb_c else f.get("carbs_g")
    except Exception as e:
        print("UK proximates parse error:", e)

    try:
        inorg = pd.read_excel(xlsx, sheet_name="1.4 Inorganics")
        code_c = _find_col(list(inorg.columns), "Food Code", "Foodcode")
        na_c = _find_col(list(inorg.columns), "Sodium", "Na")
        ca_c = _find_col(list(inorg.columns), "Calcium", "Ca")
        fe_c = _find_col(list(inorg.columns), "Iron", "Fe")
        zn_c = _find_col(list(inorg.columns), "Zinc", "Zn")
        se_c = _find_col(list(inorg.columns), "Selenium", "Se")
        name_c = _find_col(list(inorg.columns), "Food Name")
        for _, row in inorg.iterrows():
            code = str(row.get(code_c) or "").strip()
            if not code:
                continue
            if code not in foods:
                name = row.get(name_c) or code
                upsert(code, str(name))
            f = foods[code]
            f["sodium_mg"] = parse_num(row.get(na_c)) if na_c else f.get("sodium_mg")
            f["calcium_mg"] = parse_num(row.get(ca_c)) if ca_c else f.get("calcium_mg")
            f["iron_mg"] = parse_num(row.get(fe_c)) if fe_c else f.get("iron_mg")
            f["zinc_mg"] = parse_num(row.get(zn_c)) if zn_c else f.get("zinc_mg")
            f["selenium_ug"] = parse_num(row.get(se_c)) if se_c else f.get("selenium_ug")
    except Exception as e:
        print("UK inorganics parse error:", e)

    try:
        vits = pd.read_excel(xlsx, sheet_name="1.5 Vitamins")
        code_c = _find_col(list(vits.columns), "Food Code", "Foodcode")
        vc_c = _find_col(list(vits.columns), "Vitamin C", "Vit C")
        va_c = _find_col(list(vits.columns), "Vitamin A", "Retinol Equivalent")
        for _, row in vits.iterrows():
            code = str(row.get(code_c) or "").strip()
            if code not in foods:
                continue
            f = foods[code]
            f["vitamin_c_mg"] = parse_num(row.get(vc_c)) if vc_c else f.get("vitamin_c_mg")
            f["vitamin_a_ug"] = parse_num(row.get(va_c)) if va_c else f.get("vitamin_a_ug")
    except Exception as e:
        print("UK vitamins parse error:", e)

    return list(foods.values())


def sample_foods() -> list[dict]:
    """Curated multi-country samples so the app always ships with real-looking data."""
    samples = [
        ("米饭（蒸）", "Steamed rice", "CN", "谷类", 116, 2.6, 0.3, 25.9, 1.0, 7, 0.3, 0.5, 1.0, "一碗约 150 g"),
        ("豆腐（北豆腐）", "Firm tofu", "CN", "豆类", 98, 12.2, 4.8, 2.0, 7.2, 138, 2.7, 1.1, 2.0, "一块约 100 g"),
        ("鸡蛋（煮）", "Boiled egg", "CN", "蛋类", 144, 13.3, 8.8, 2.8, 131, 56, 2.0, 1.0, 15, "一枚约 50 g"),
        ("りんご 生", "Apple raw", "JP", "果物", 61, 0.2, 0.1, 16.2, 0, 3, 0.1, 0.0, 0, "一个约 150 g"),
        ("白米飯", "Cooked white rice", "JP", "穀類", 168, 2.5, 0.3, 37.1, 1, 3, 0.1, 0.6, 1, "一碗约 150 g"),
        ("김치", "Kimchi", "KR", "채소", 19, 1.1, 0.2, 3.9, 498, 33, 0.5, 0.2, 0.5, "一小碟约 50 g"),
        ("백미밥", "White rice cooked", "KR", "곡류", 130, 2.4, 0.3, 28.1, 1, 5, 0.2, 0.4, 0, "一碗约 150 g"),
        ("Chicken rice", "Chicken rice", "SG", "Meals", 149, 8.5, 4.2, 18.0, 320, 12, 0.6, 0.5, 8, "一份约 300 g"),
        ("Banana, raw", "Banana raw", "US", "Fruits", 89, 1.1, 0.3, 22.8, 1, 5, 0.3, 0.2, 1, "一根约 120 g"),
        ("Milk, whole, 3.25%", "Whole milk", "US", "Dairy", 61, 3.2, 3.3, 4.8, 43, 113, 0.0, 0.4, 1.5, "一杯约 200 ml"),
        ("White bread, sliced", "White bread", "UK", "Cereals", 265, 9.0, 3.3, 49.0, 460, 100, 1.8, 0.7, 4, "一片约 30 g"),
        ("Cheddar cheese", "Cheddar", "UK", "Dairy", 416, 25.4, 34.9, 0.1, 723, 739, 0.3, 3.1, 12, "一小块约 30 g"),
        ("Pomme, crue", "Apple raw", "FR", "Fruits", 53, 0.3, 0.3, 11.6, 1, 5, 0.1, 0.0, 0, "一个约 150 g"),
        ("Yaourt nature", "Plain yogurt", "FR", "Produits laitiers", 63, 4.0, 3.0, 4.5, 48, 140, 0.1, 0.5, 2, "一小杯约 125 g"),
        ("Vollmilch 3,5%", "Whole milk", "DE", "Milchprodukte", 64, 3.3, 3.5, 4.8, 44, 120, 0.0, 0.4, 1.5, "一杯约 200 ml"),
        ("Kartoffeln, geschält, roh", "Potato raw", "DE", "Gemüse", 70, 2.0, 0.1, 15.0, 3, 6, 0.4, 0.3, 0.3, "一个约 150 g"),
        ("北京烤鸭", "Peking duck", "CN", "禽肉", 240, 16.0, 19.0, 2.0, 90, 10, 1.5, 1.2, 12, "一份约 80 g"),
        ("味噌汤", "Miso soup", "JP", "スープ", 40, 3.0, 1.2, 4.5, 580, 20, 0.5, 0.4, 2, "一碗约 200 ml"),
        ("石锅拌饭", "Bibimbap", "KR", "밥류", 140, 6.0, 4.0, 20.0, 420, 40, 1.2, 1.0, 8, "一份约 350 g"),
        ("Salmon, grilled", "Grilled salmon", "US", "Seafood", 208, 22.0, 13.0, 0.0, 59, 12, 0.5, 0.6, 36, "一份约 100 g"),
    ]
    out = []
    for name, name_en, country, cat, kcal, pro, fat, carb, na, ca, fe, zn, se, serving in samples:
        out.append(
            empty_food(
                name=name,
                name_en=name_en,
                source_country=country,
                source_id=f"sample-{country}-{len(out)+1}",
                category=cat,
                kcal_100g=kcal,
                protein_g=pro,
                fat_g=fat,
                carbs_g=carb,
                sodium_mg=na,
                calcium_mg=ca,
                iron_mg=fe,
                zinc_mg=zn,
                selenium_ug=se,
                vitamin_c_mg=None,
                serving_ref=serving,
            )
        )
    return out


def insert_foods(conn: sqlite3.Connection, foods: list[dict]) -> int:
    cols = [
        "name", "name_en", "name_original", "name_zh", "source_country", "source_id", "category",
        "kcal_100g", "protein_g", "fat_g", "carbs_g", "sodium_mg",
        "calcium_mg", "iron_mg", "zinc_mg", "selenium_ug",
        "vitamin_a_ug", "vitamin_c_mg", "vitamin_d_ug", "vitamin_e_mg",
        "vitamin_b1_mg", "vitamin_b2_mg", "vitamin_b3_mg",
        "serving_ref", "image_path", "raw_json",
    ]
    cur = conn.cursor()
    n = 0
    for f in foods:
        f["name_original"] = f.get("name")
        if f.get("source_country") == "CN" and not f.get("name_zh"):
            f["name_zh"] = f.get("name")
        f["image_path"] = match_image(f.get("name") or "", f.get("name_en"))
        if not f.get("serving_ref"):
            f["serving_ref"] = infer_serving(f.get("name") or "", f.get("category"))
        values = [f.get(c) for c in cols]
        cur.execute(
            f"INSERT INTO foods ({', '.join(cols)}) VALUES ({', '.join('?' for _ in cols)})",
            values,
        )
        n += 1
    conn.commit()
    return n


def main() -> int:
    ensure_dirs()
    # Optionally run download first if raw empty
    if not any(RAW_DIR.iterdir()) if RAW_DIR.exists() else True:
        print("Raw data empty — run download_sources.py first (continuing with samples + whatever exists)")

    loaders = [
        ("china", normalize_china),
        ("japan", normalize_japan),
        ("korea", normalize_korea),
        ("singapore", normalize_singapore),
        ("usa", normalize_usa),
        ("uk", normalize_uk_cofid),
        ("france", normalize_france),
        ("germany", normalize_germany),
    ]

    all_foods: list[dict] = []
    counts: dict[str, int] = {}
    for key, fn in loaders:
        rows = fn()
        counts[key] = len(rows)
        all_foods.extend(rows)
        print(f"{key}: {len(rows)} foods")

    if len(all_foods) < 50:
        samples = sample_foods()
        all_foods.extend(samples)
        counts["sample_fallback"] = len(samples)
        print(f"sample_fallback: {len(samples)} foods")

    # Deduplicate by (country, name)
    seen = set()
    unique = []
    for f in all_foods:
        key = (f.get("source_country"), (f.get("name") or "").strip().lower())
        if key in seen or not key[1]:
            continue
        seen.add(key)
        unique.append(f)

    if DB_PATH.exists():
        DB_PATH.unlink()
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(SCHEMA)
    n = insert_foods(conn, unique)
    conn.close()

    status = load_status()
    status["build"] = {"total": n, "by_source": counts, "db": str(DB_PATH)}
    save_status(status)
    print(f"Wrote {n} foods → {DB_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
