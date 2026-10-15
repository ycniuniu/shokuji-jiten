#!/usr/bin/env python3
"""Fetch real food photos for public/images/ from Wikimedia Commons.

For every Food-101 class we search Commons, keep only freely licensed files
(CC0 / Public Domain / CC BY / CC BY-SA, never NC or ND), crop to 640x480,
and record author / license / source page in public/images/credits.json.
Classes without a usable photo keep a labeled placeholder (CJK font).

Usage:
  python3 fetch_images.py            # fill in only missing classes
  python3 fetch_images.py --force    # re-fetch every class
  python3 fetch_images.py --only pho,sushi --force
"""
from __future__ import annotations

import html
import io
import json
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "public" / "images"
CREDITS = OUT / "credits.json"
API = "https://commons.wikimedia.org/w/api.php"
UA = "shokuji-jiten/1.0 (https://github.com/ycniuniu/shokuji-jiten; image credits fetcher)"
SIZE = (640, 480)

# Commons search terms where the class name alone is ambiguous.
QUERY = {
    "cup_cakes": "cupcakes",
    "donuts": "doughnuts",
    "pho": "pho noodle soup",
    "steak": "beef steak plate",
    "mussels": "mussels dish",
    "oysters": "oysters plate",
    "scallops": "seared scallops",
    "escargots": "escargots de Bourgogne",
    "sashimi": "sashimi plate",
    "edamame": "edamame bowl",
    "ice_cream": "ice cream scoops",
    "pizza": "pizza margherita",
    "sushi": "sushi plate",
    "waffles": "waffles plate",
    "hamburger": "hamburger sandwich",
    "tacos": "tacos plate",
    "ramen": "ramen bowl",
    "omelette": "omelette plate",
    "dumplings": "jiaozi dumplings",
    "lobster_roll_sandwich": "lobster roll",
    "pulled_pork_sandwich": "pulled pork sandwich",
    "cheese_plate": "cheese platter",
    "beignets": "beignets powdered sugar",
    "churros": "churros",
}

# Hand-picked Commons files that override the search result (after review).
OVERRIDE: dict[str, str] = {
    "apple_pie": "File:Slice of apple pie 2.jpg",
    "nachos": "File:Nachos-cheese.jpg",
    "caprese_salad": "File:Insalata caprese.jpg",
    "hot_dog": "File:Hot dog 3.jpg",
    "paella": "File:Paella Valenciana tradicional.jpg",
    "pork_chop": "File:Three grilled pork chops.jpg",
    "edamame": "File:Edamame beans.jpg",
    "french_fries": "File:French fries 3.jpg",
    "carrot_cake": "File:Slice of gluten-free carrot cake, April 2005.jpg",
    "strawberry_shortcake": "File:Strawberry shortcake with whipcream.jpg",
}

ALLOWED = re.compile(r"^(cc0|cc[- ]?zero|public domain|pd\b|pd-|cc[- ]by(-sa)?[- ]?\d|cc[- ]by(-sa)?$)", re.I)


def clean(s: str | None) -> str:
    s = re.sub(r"<[^>]+>", "", s or "")
    return re.sub(r"\s+", " ", html.unescape(s)).strip()


def license_ok(short: str) -> bool:
    s = short.strip()
    if re.search(r"\bNC\b|\bND\b|non-?commercial|no ?deriv", s, re.I):
        return False
    return bool(ALLOWED.match(s))


def session():
    import requests

    s = requests.Session()
    s.headers["User-Agent"] = UA
    return s


def candidates(s, query: str, limit: int = 20) -> list[dict]:
    params = {
        "action": "query", "format": "json", "generator": "search",
        "gsrnamespace": 6, "gsrsearch": f"{query} filetype:bitmap", "gsrlimit": limit,
        "prop": "imageinfo", "iiprop": "url|extmetadata|mime|size", "iiurlwidth": 800,
    }
    r = s.get(API, params=params, timeout=30)
    r.raise_for_status()
    pages = (r.json().get("query") or {}).get("pages") or {}
    return sorted(pages.values(), key=lambda p: p.get("index", 0))


def by_title(s, title: str) -> list[dict]:
    params = {
        "action": "query", "format": "json", "titles": title,
        "prop": "imageinfo", "iiprop": "url|extmetadata|mime|size", "iiurlwidth": 800,
    }
    r = s.get(API, params=params, timeout=30)
    r.raise_for_status()
    return list(((r.json().get("query") or {}).get("pages") or {}).values())


def pick(pages: list[dict], words: list[str]) -> dict | None:
    best, best_score = None, -1
    for p in pages:
        ii = (p.get("imageinfo") or [{}])[0]
        if ii.get("mime") not in ("image/jpeg", "image/png"):
            continue
        if (ii.get("width") or 0) < 640 or (ii.get("height") or 0) < 400:
            continue
        meta = ii.get("extmetadata") or {}
        lic = clean((meta.get("LicenseShortName") or {}).get("value"))
        if not license_ok(lic):
            continue
        title = p.get("title", "").lower()
        score = sum(w in title for w in words) * 10 - p.get("index", 0)
        if score > best_score:
            best, best_score = p, score
    return best


def credit_of(p: dict) -> dict:
    ii = p["imageinfo"][0]
    meta = ii.get("extmetadata") or {}
    v = lambda k: clean((meta.get(k) or {}).get("value"))
    author = v("Artist") or v("Credit") or "Unknown"
    if len(author) > 80:
        author = author[:77] + "…"
    return {
        "title": p["title"],
        "author": author,
        "license": v("LicenseShortName"),
        "license_url": v("LicenseUrl") or None,
        "page_url": ii.get("descriptionurl"),
    }


def save_photo(s, url: str, dest: Path) -> None:
    from PIL import Image, ImageOps

    r = s.get(url, timeout=60)
    r.raise_for_status()
    img = ImageOps.exif_transpose(Image.open(io.BytesIO(r.content))).convert("RGB")
    img = ImageOps.fit(img, SIZE, Image.LANCZOS)
    img.save(dest, "JPEG", quality=80, optimize=True, progressive=True)


FONT_CANDIDATES = [
    "/System/Library/Fonts/Hiragino Sans GB.ttc",
    "/System/Library/Fonts/STHeiti Medium.ttc",
    "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]


def make_placeholder(cls: str, dest: Path) -> None:
    from PIL import Image, ImageDraw, ImageFont

    img = Image.new("RGB", SIZE, (245, 245, 245))
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, 640, 8], fill=(196, 30, 58))
    font = small = None
    for path in FONT_CANDIDATES:
        try:
            font, small = ImageFont.truetype(path, 28), ImageFont.truetype(path, 16)
            break
        except Exception:
            continue
    if font is None:
        font = small = ImageFont.load_default()
    draw.text((40, 200), cls.replace("_", " ").title(), fill=(20, 20, 20), font=font)
    draw.text((40, 250), "食事事典 · Food-101", fill=(120, 120, 120), font=small)
    img.save(dest, "JPEG", quality=85)


def classes() -> list[str]:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from build_db import FOOD101_ALIASES

    return list(FOOD101_ALIASES)


def main() -> int:
    force = "--force" in sys.argv
    only = None
    if "--only" in sys.argv:
        only = set(sys.argv[sys.argv.index("--only") + 1].split(","))
    OUT.mkdir(parents=True, exist_ok=True)
    credits = json.loads(CREDITS.read_text("utf-8")) if CREDITS.exists() else {}
    s = session()
    missing = []
    for cls in classes():
        if only and cls not in only:
            continue
        dest = OUT / f"{cls}.jpg"
        if not force and cls in credits and dest.exists():
            continue
        try:
            if cls in OVERRIDE:
                pages = by_title(s, OVERRIDE[cls])
                p = pick(pages, [])
            else:
                q = QUERY.get(cls, cls.replace("_", " "))
                p = pick(candidates(s, q), q.lower().split())
            if p is None:
                raise LookupError("no freely licensed photo")
            save_photo(s, p["imageinfo"][0].get("thumburl") or p["imageinfo"][0]["url"], dest)
            credits[cls] = credit_of(p)
            print(f"ok   {cls}: {p['title']} [{credits[cls]['license']}]")
        except Exception as e:  # keep the placeholder
            credits.pop(cls, None)
            if force or not dest.exists():
                make_placeholder(cls, dest)
            missing.append(cls)
            print(f"miss {cls}: {e}")
        time.sleep(0.3)
    CREDITS.write_text(json.dumps(dict(sorted(credits.items())), ensure_ascii=False, indent=2) + "\n", "utf-8")
    print(f"photos: {len(credits)}  placeholders: {len(missing)} {missing}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
