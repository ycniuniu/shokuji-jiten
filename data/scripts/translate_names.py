#!/usr/bin/env python3
"""Translate non-Chinese food names into foods.name_zh.

Original text is copied to name_original and left in name.
Chinese rows (source_country = CN, or no foreign script) are copied as-is.

Uses deep-translator's GoogleTranslator. Its HTML endpoint currently returns
429, so batches go through Google's gtx client after that failure.
"""

from __future__ import annotations

import json
import sqlite3
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import requests
from deep_translator import GoogleTranslator
from deep_translator.exceptions import TooManyRequests

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "food.db"
CACHE_PATH = ROOT / "name_zh_cache.json"

LANG_BY_COUNTRY = {
    "JP": "ja",
    "KR": "ko",
    "FR": "fr",
    "DE": "de",
    "US": "en",
    "UK": "en",
    "SG": "en",
}

ENDPOINTS = (
    (
        "https://clients5.google.com/translate_a/t",
        {"client": "dict-chrome-ex"},
    ),
    (
        "https://translate.googleapis.com/translate_a/single",
        {"client": "gtx", "dt": "t"},
    ),
)
HEADERS = {"User-Agent": "Mozilla/5.0"}
MAX_CHARS = 3800
WORKERS = 1


def source_lang(country: str, name: str) -> str | None:
    if country == "CN":
        return None
    if any("\uac00" <= ch <= "\ud7af" for ch in name):
        return "ko"
    if any("\u3040" <= ch <= "\u30ff" for ch in name):
        return "ja"
    if any("\u4e00" <= ch <= "\u9fff" for ch in name):
        if country == "JP":
            return "ja"
        if country == "KR":
            return "ko"
        return None
    if any(ch.isascii() and ch.isalpha() for ch in name):
        return LANG_BY_COUNTRY.get(country, "en")
    return LANG_BY_COUNTRY.get(country)


def ensure_columns(conn: sqlite3.Connection) -> None:
    cols = {row[1] for row in conn.execute("PRAGMA table_info(foods)")}
    if "name_original" not in cols:
        conn.execute("ALTER TABLE foods ADD COLUMN name_original TEXT")
    if "name_zh" not in cols:
        conn.execute("ALTER TABLE foods ADD COLUMN name_zh TEXT")
    conn.execute(
        "UPDATE foods SET name_original = name "
        "WHERE name_original IS NULL OR name_original = ''"
    )
    conn.commit()


def load_cache() -> dict[str, str]:
    if CACHE_PATH.exists():
        return json.loads(CACHE_PATH.read_text(encoding="utf-8"))
    return {}


def save_cache(cache: dict[str, str]) -> None:
    tmp = CACHE_PATH.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
    tmp.replace(CACHE_PATH)


def probe_library() -> str:
    """One call through deep-translator. Returns 'library' or 'gtx'."""
    try:
        text = GoogleTranslator(source="en", target="zh-CN").translate("milk")
        print(f"deep-translator GoogleTranslator ok: milk -> {text}")
        return "library"
    except TooManyRequests:
        print("deep-translator GoogleTranslator returned 429; using Google gtx batches")
        return "gtx"
    except Exception as exc:
        print(f"deep-translator GoogleTranslator failed ({exc}); using Google gtx batches")
        return "gtx"


def _translated_text(data: object) -> str:
    if isinstance(data, list) and data and isinstance(data[0], str):
        return data[0]
    if isinstance(data, list) and data and isinstance(data[0], list):
        return str(data[0][0][0])
    raise ValueError(f"unexpected translate payload: {data!r}"[:200])


def gtx_translate(source: str, text: str) -> str:
    last_error: Exception | None = None
    for attempt in range(6):
        for url, extra in ENDPOINTS:
            try:
                response = requests.get(
                    url,
                    params={"sl": source, "tl": "zh-CN", "q": text, **extra},
                    headers=HEADERS,
                    timeout=30,
                )
                if response.status_code == 429:
                    continue
                response.raise_for_status()
                translated = _translated_text(response.json())
                time.sleep(0.25)
                return translated
            except Exception as exc:
                last_error = exc
        time.sleep(3 * (attempt + 1))
    raise RuntimeError(f"translate failed: {last_error}")


def library_translate(source: str, text: str) -> str:
    last_error: Exception | None = None
    for attempt in range(4):
        try:
            return GoogleTranslator(source=source, target="zh-CN").translate(text)
        except Exception as exc:
            last_error = exc
            time.sleep(1.2 * (attempt + 1))
    raise RuntimeError(f"library translate failed: {last_error}")


def translate_batch(mode: str, source: str, texts: list[str]) -> list[str]:
    if not texts:
        return []
    if len(texts) == 1:
        fn = library_translate if mode == "library" else gtx_translate
        return [fn(source, texts[0])]
    joined = "\n".join(texts)
    fn = library_translate if mode == "library" else gtx_translate
    try:
        out = fn(source, joined)
    except Exception:
        if len(texts) == 1:
            raise
        mid = max(1, len(texts) // 2)
        return translate_batch(mode, source, texts[:mid]) + translate_batch(
            mode, source, texts[mid:]
        )
    parts = out.split("\n")
    if len(parts) != len(texts):
        mid = max(1, len(texts) // 2)
        return translate_batch(mode, source, texts[:mid]) + translate_batch(
            mode, source, texts[mid:]
        )
    return [part.strip() for part in parts]


def chunks(items: list[str]) -> list[list[str]]:
    batches: list[list[str]] = []
    current: list[str] = []
    size = 0
    for item in items:
        extra = len(item) + 1
        if current and size + extra > MAX_CHARS:
            batches.append(current)
            current = []
            size = 0
        current.append(item)
        size += extra
    if current:
        batches.append(current)
    return batches


def main() -> None:
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    ensure_columns(conn)

    pending: dict[tuple[str, str], list[int]] = {}
    copied = 0
    for row_id, country, name, name_zh in conn.execute(
        "SELECT id, source_country, name, name_zh FROM foods"
    ):
        if name_zh:
            continue
        lang = source_lang(country, name)
        if lang is None:
            conn.execute("UPDATE foods SET name_zh = ? WHERE id = ?", (name, row_id))
            copied += 1
            continue
        pending.setdefault((lang, name), []).append(row_id)
    conn.commit()
    print(f"copied already-Chinese rows: {copied}")
    print(f"unique names to translate: {len(pending)}")

    cache = load_cache()
    cache_lock = threading.Lock()
    mode = probe_library()

    by_lang: dict[str, list[str]] = {}
    for lang, name in pending:
        key = f"{lang}\t{name}"
        if key in cache and cache[key]:
            continue
        by_lang.setdefault(lang, []).append(name)

    jobs: list[tuple[str, list[str]]] = []
    for lang, names in by_lang.items():
        for batch in chunks(names):
            jobs.append((lang, batch))
    print(f"batches: {len(jobs)} via {mode}")

    done = 0
    done_lock = threading.Lock()

    def run_job(lang: str, batch: list[str]) -> tuple[str, list[str], list[str]]:
        translated = translate_batch(mode, lang, batch)
        return lang, batch, translated

    update = conn.cursor()
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futures = [pool.submit(run_job, lang, batch) for lang, batch in jobs]
        for future in as_completed(futures):
            lang, batch, translated = future.result()
            with cache_lock:
                for src, dst in zip(batch, translated):
                    if not dst:
                        continue
                    cache[f"{lang}\t{src}"] = dst
                    for row_id in pending[(lang, src)]:
                        update.execute(
                            "UPDATE foods SET name_zh = ? WHERE id = ?",
                            (dst, row_id),
                        )
                conn.commit()
                save_cache(cache)
            with done_lock:
                done += len(batch)
                print(f"translated {done}/{sum(len(v) for v in by_lang.values())} {lang}", flush=True)

    # Apply cache hits that were already known before this run.
    applied = 0
    for (lang, name), ids in pending.items():
        dst = cache.get(f"{lang}\t{name}")
        if not dst:
            continue
        for row_id in ids:
            update.execute(
                "UPDATE foods SET name_zh = ? WHERE id = ? AND (name_zh IS NULL OR name_zh = '')",
                (dst, row_id),
            )
            applied += update.rowcount
    conn.commit()

    missing = conn.execute(
        "SELECT COUNT(*) FROM foods WHERE name_zh IS NULL OR name_zh = ''"
    ).fetchone()[0]
    print(f"cache reapplied rows: {applied}")
    print(f"still missing name_zh: {missing}")

    print("--- spot check ---")
    for country in ("JP", "KR", "FR", "DE", "US", "UK"):
        rows = conn.execute(
            """
            SELECT name_original, name_zh FROM foods
            WHERE source_country = ? AND name_zh IS NOT NULL AND name_zh != name_original
            ORDER BY id LIMIT 4
            """,
            (country,),
        ).fetchall()
        for original, zh in rows:
            print(f"{country}\t{original}\t{zh}")
    conn.close()


if __name__ == "__main__":
    main()
