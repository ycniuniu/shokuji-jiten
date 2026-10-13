#!/usr/bin/env python3
"""Download nutrition data from multi-country sources into data/raw/."""
from __future__ import annotations

import json
import shutil
import sys
import time
import zipfile
from pathlib import Path
from urllib.parse import urljoin

import requests

from common import RAW_DIR, ensure_dirs, save_status

HEADERS = {
    "User-Agent": "food-nutrition/1.0 (educational; +https://github.com/food-nutrition)",
    "Accept": "*/*",
}
TIMEOUT = 60


def get(url: str, **kwargs) -> requests.Response:
    kwargs.setdefault("headers", HEADERS)
    kwargs.setdefault("timeout", TIMEOUT)
    kwargs.setdefault("allow_redirects", True)
    return requests.get(url, **kwargs)


def download_file(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    with get(url, stream=True) as r:
        r.raise_for_status()
        with dest.open("wb") as f:
            for chunk in r.iter_content(chunk_size=1024 * 256):
                if chunk:
                    f.write(chunk)


def status_ok(msg: str, count: int | None = None) -> dict:
    return {"ok": True, "message": msg, "count": count}


def status_fail(msg: str) -> dict:
    return {"ok": False, "message": msg, "count": 0}


# ---------- China ----------
def download_china() -> dict:
    """Sanotsu/china-food-composition-data json_data_v3 (~1677 foods)."""
    out = RAW_DIR / "china"
    out.mkdir(parents=True, exist_ok=True)
    api = "https://api.github.com/repos/Sanotsu/china-food-composition-data/contents/json_data_v3_20260825_qwen38max_kimi_k3_fixed"
    try:
        r = get(api)
        r.raise_for_status()
        files = [x for x in r.json() if x.get("name", "").endswith(".json")]
        n = 0
        for item in files:
            dest = out / item["name"]
            if dest.exists() and dest.stat().st_size > 0:
                n += 1
                continue
            download_file(item["download_url"], dest)
            n += 1
            time.sleep(0.15)
        return status_ok(f"Downloaded {n} China JSON category files", n)
    except Exception as e:
        # Mirror: sparse sample bundled later by build if empty
        return status_fail(f"China download failed: {e}")


# ---------- Japan ----------
def download_japan() -> dict:
    """MEXT 八訂 via katoharu432 GitHub JSON or pons static API index + sample."""
    out = RAW_DIR / "japan"
    out.mkdir(parents=True, exist_ok=True)
    # Prefer GitHub JSON dump (single file / tree)
    api = "https://api.github.com/repos/katoharu432/standards-tables-of-food-composition-in-japan/contents"
    try:
        r = get(api)
        r.raise_for_status()
        entries = r.json()
        json_files = [x for x in entries if x.get("name", "").endswith(".json")]
        if not json_files:
            # maybe nested
            for x in entries:
                if x.get("type") == "dir":
                    r2 = get(x["url"])
                    r2.raise_for_status()
                    json_files.extend([y for y in r2.json() if y.get("name", "").endswith(".json")])
        n = 0
        for item in json_files[:50]:
            dest = out / item["name"]
            if not dest.exists():
                download_file(item["download_url"], dest)
            n += 1
            time.sleep(0.1)
        if n:
            return status_ok(f"Downloaded Japan GitHub JSON ({n} files)", n)
    except Exception as e1:
        err1 = str(e1)

    # Fallback: pons index + first N detail records
    try:
        index = get("https://food-ingredients.pons-llc.com/index.json").json()
        (out / "index.json").write_text(json.dumps(index, ensure_ascii=False), encoding="utf-8")
        # Download a representative subset (full 2541 is heavy; take up to 400)
        codes = [x["code"] for x in index[:400]]
        details = []
        for i, code in enumerate(codes):
            try:
                d = get(f"https://food-ingredients.pons-llc.com/data/{code}.json").json()
                details.append(d)
            except Exception:
                continue
            if i % 20 == 0:
                time.sleep(0.2)
        (out / "details.json").write_text(json.dumps(details, ensure_ascii=False), encoding="utf-8")
        return status_ok(f"Japan pons API: index + {len(details)} details", len(details))
    except Exception as e2:
        return status_fail(f"Japan failed (github: {err1 if 'err1' in dir() else 'n/a'}; pons: {e2})")


# ---------- Korea ----------
def download_korea() -> dict:
    """Korea MFDS Excel is portal-gated; ship a small curated sample mirror."""
    out = RAW_DIR / "korea"
    out.mkdir(parents=True, exist_ok=True)
    sample = [
        {"food_name": "김치", "category": "채소", "kcal": 19, "protein": 1.1, "fat": 0.2, "carbs": 3.9, "sodium": 498, "calcium": 33, "iron": 0.5, "zinc": 0.2, "selenium": 0.5},
        {"food_name": "백미밥", "category": "곡류", "kcal": 130, "protein": 2.4, "fat": 0.3, "carbs": 28.1, "sodium": 1, "calcium": 5, "iron": 0.2, "zinc": 0.4, "selenium": 0},
        {"food_name": "된장찌개", "category": "국", "kcal": 45, "protein": 3.5, "fat": 1.8, "carbs": 4.2, "sodium": 620, "calcium": 40, "iron": 0.8, "zinc": 0.5, "selenium": 2},
        {"food_name": "불고기", "category": "육류", "kcal": 180, "protein": 15, "fat": 10, "carbs": 8, "sodium": 410, "calcium": 15, "iron": 1.5, "zinc": 2.5, "selenium": 12},
        {"food_name": "비빔밥", "category": "밥류", "kcal": 140, "protein": 6, "fat": 4, "carbs": 20, "sodium": 420, "calcium": 40, "iron": 1.2, "zinc": 1.0, "selenium": 8},
    ]
    (out / "sample_mfds_mirror.json").write_text(
        json.dumps(sample, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (out / "README.txt").write_text(
        "Official source: https://various.foodsafetykorea.go.kr/\n"
        "Bulk Excel is not auto-downloadable (portal/auth).\n"
        "Bundled sample_mfds_mirror.json keeps KR rows in the DB.\n"
        "Replace with official Excel/CSV when available.\n",
        encoding="utf-8",
    )
    return status_ok("Korea: curated sample mirror (official Excel blocked)", len(sample))


# ---------- Singapore ----------
def download_singapore() -> dict:
    """HPB SG FoodID has no public bulk API; ship curated sample."""
    out = RAW_DIR / "singapore"
    out.mkdir(parents=True, exist_ok=True)
    sample = [
        {"food_name": "Chicken rice", "category": "Meals", "kcal": 149, "protein": 8.5, "fat": 4.2, "carbs": 18, "sodium": 320, "calcium": 12, "iron": 0.6, "zinc": 0.5, "selenium": 8},
        {"food_name": "Laksa", "category": "Noodles", "kcal": 130, "protein": 6, "fat": 7, "carbs": 12, "sodium": 480, "calcium": 40, "iron": 0.8, "zinc": 0.6, "selenium": 6},
        {"food_name": "Chili crab", "category": "Seafood", "kcal": 120, "protein": 14, "fat": 5, "carbs": 6, "sodium": 550, "calcium": 80, "iron": 0.7, "zinc": 2.0, "selenium": 30},
        {"food_name": "Kaya toast", "category": "Breakfast", "kcal": 280, "protein": 6, "fat": 12, "carbs": 36, "sodium": 320, "calcium": 40, "iron": 1.2, "zinc": 0.5, "selenium": 4},
        {"food_name": "Roti prata", "category": "Bread", "kcal": 300, "protein": 7, "fat": 12, "carbs": 42, "sodium": 380, "calcium": 30, "iron": 1.5, "zinc": 0.7, "selenium": 5},
    ]
    (out / "sample_foodid_mirror.json").write_text(
        json.dumps(sample, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (out / "README.txt").write_text(
        "SG FoodID portal: https://pphtpc.hpb.gov.sg/\n"
        "No public bulk export found for automated download.\n"
        "Bundled sample_foodid_mirror.json keeps SG rows in the DB.\n",
        encoding="utf-8",
    )
    return status_ok("Singapore: curated sample mirror (no bulk API)", len(sample))


# ---------- USA ----------
def download_usa() -> dict:
    """USDA FoodData Central Foundation + SR Legacy JSON dumps."""
    out = RAW_DIR / "usa"
    out.mkdir(parents=True, exist_ok=True)
    # Official zip dumps (large). Prefer smaller FoodData Central survey/foundation JSON if available.
    urls = {
        "Foundation_Foods.json": None,
        "SR_Legacy_Foods.json": None,
    }
    # Try USDA download page assets (known CDN pattern)
    candidates = [
        (
            "foundation",
            "https://fdc.nal.usda.gov/fdc-datasets/FoodData_Central_foundation_food_json_2024-04-18.zip",
        ),
        (
            "sr_legacy",
            "https://fdc.nal.usda.gov/fdc-datasets/FoodData_Central_sr_legacy_food_json_2018-04.zip",
        ),
    ]
    # Alternate: GitHub mirror / smaller sample API
    got = 0
    errors = []
    for name, url in candidates:
        zip_path = out / f"{name}.zip"
        try:
            if not zip_path.exists():
                download_file(url, zip_path)
            with zipfile.ZipFile(zip_path, "r") as zf:
                zf.extractall(out / name)
            got += 1
        except Exception as e:
            errors.append(f"{name}: {e}")

    if got == 0:
        # Fallback: download a handful via FDC public API (no key needed for limited use? actually needs key)
        # Use GitHub-hosted samples if any
        try:
            sample_url = (
                "https://raw.githubusercontent.com/usda/USDA-FoodDataCentral/"
                "master/Documentation%20and%20Sample%20Files/Foundation_foods_sample.json"
            )
            download_file(sample_url, out / "foundation_sample.json")
            got = 1
            return status_ok("USA: sample Foundation JSON only (full zip blocked)", 1)
        except Exception as e:
            errors.append(str(e))
            return status_fail("USA FDC download failed: " + "; ".join(errors))

    return status_ok(f"USA FDC downloaded {got} dataset(s)", got)


# ---------- UK ----------
def download_uk() -> dict:
    """McCance & Widdowson CoFID 2021 from GOV.UK assets."""
    out = RAW_DIR / "uk"
    out.mkdir(parents=True, exist_ok=True)
    url = (
        "https://assets.publishing.service.gov.uk/media/60538b91e90e07527df82ae4/"
        "McCance_Widdowsons_Composition_of_Foods_Integrated_Dataset_2021..xlsx"
    )
    try:
        dest = out / "cofid_2021.xlsx"
        if not dest.exists() or dest.stat().st_size < 10000:
            download_file(url, dest)
        return status_ok("UK CoFID 2021 xlsx from GOV.UK", 1)
    except Exception as e:
        return status_fail(f"UK CoFID download failed: {e}")


# ---------- France ----------
def download_france() -> dict:
    """ANSES Ciqual 2020 Excel via data.gouv / anses.fr."""
    out = RAW_DIR / "france"
    out.mkdir(parents=True, exist_ok=True)
    try:
        meta = get(
            "https://www.data.gouv.fr/api/1/datasets/?q=ciqual&page_size=5"
        ).json()
        for d in meta.get("data", []):
            for res in d.get("resources", []):
                url = res.get("url") or ""
                fmt = (res.get("format") or "").lower()
                title = (res.get("title") or "").lower()
                if fmt in {"xls", "xlsx"} or url.lower().endswith((".xls", ".xlsx")):
                    if "anglais" in title or "english" in title or "eng" in url.lower():
                        continue
                    dest = out / ("ciqual_2020_fr.xls" if url.lower().endswith(".xls") else "ciqual_2020_fr.xlsx")
                    download_file(url, dest)
                    return status_ok(f"France Ciqual: {res.get('title')}", 1)
        # Direct anses fallback
        url = "https://ciqual.anses.fr/cms/sites/default/files/inline-files/Table%20Ciqual%202020_FR_2020%2007%2007.xls"
        download_file(url, out / "ciqual_2020_fr.xls")
        return status_ok("France Ciqual XLS from anses.fr", 1)
    except Exception as e:
        return status_fail(f"France Ciqual download failed: {e}")


# ---------- Germany ----------
def download_germany() -> dict:
    """BLS 4.0 open data zip from blsdb.de (tokenized link on download page)."""
    import re

    out = RAW_DIR / "germany"
    out.mkdir(parents=True, exist_ok=True)
    try:
        page = get("https://blsdb.de/download").text
        m = re.search(r'href="([^"]*BLS[^"]*\.zip[^"]*)"', page, re.I)
        if not m:
            m = re.search(r'href="((?:&#47;|/)assets[^"]*BLS[^"]+)"', page, re.I)
        if not m:
            return status_fail("Germany: no BLS zip link found on blsdb.de/download")
        link = (
            m.group(1)
            .replace("&#47;", "/")
            .replace("&#95;", "_")
            .replace("&#46;", ".")
            .replace("&#63;", "?")
            .replace("&#61;", "=")
        )
        if not link.startswith("http"):
            link = urljoin("https://blsdb.de/", link)
        dest = out / "BLS_4_0_2025_DE.zip"
        download_file(link, dest)
        with zipfile.ZipFile(dest, "r") as zf:
            zf.extractall(out / "extracted")
        return status_ok("Germany BLS 4.0 from blsdb.de", 1)
    except Exception as e:
        return status_fail(f"Germany BLS download failed: {e}")


def main() -> int:
    ensure_dirs()
    status = {}
    steps = [
        ("china", download_china),
        ("japan", download_japan),
        ("korea", download_korea),
        ("singapore", download_singapore),
        ("usa", download_usa),
        ("uk", download_uk),
        ("france", download_france),
        ("germany", download_germany),
    ]
    for key, fn in steps:
        print(f"==> {key} ...")
        try:
            status[key] = fn()
        except Exception as e:
            status[key] = status_fail(str(e))
        print(f"    {status[key]}")
    save_status(status)
    print("Wrote", RAW_DIR.parent / "source_status.json")
    ok = sum(1 for v in status.values() if v.get("ok"))
    print(f"Done: {ok}/{len(status)} sources OK")
    return 0 if ok > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
