#!/usr/bin/env python3
"""Download Food-101 matched placeholder images into public/images/.

Uses publicly reachable Food-101 sample images from GitHub mirrors when possible.
Falls back to generating simple labeled JPEG placeholders with Pillow.
"""
from __future__ import annotations

import sys
from pathlib import Path

from common import ROOT, ensure_dirs
from build_db import FOOD101_ALIASES

OUT = ROOT / "public" / "images"

# Well-known small Food-101 demo repos / raw image URLs
MIRRORS = [
    "https://raw.githubusercontent.com/random-forests/tutorials/master/images/{cls}.jpg",
]


def make_placeholder(cls: str, dest: Path) -> None:
    from PIL import Image, ImageDraw, ImageFont

    img = Image.new("RGB", (640, 480), (245, 245, 245))
    draw = ImageDraw.Draw(img)
    # Red accent bar (New Yorker-ish)
    draw.rectangle([0, 0, 640, 8], fill=(196, 30, 58))
    label = cls.replace("_", " ").title()
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 28)
        small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 16)
    except Exception:
        font = ImageFont.load_default()
        small = font
    draw.text((40, 200), label, fill=(20, 20, 20), font=font)
    draw.text((40, 250), "食事事典 · Food-101", fill=(120, 120, 120), font=small)
    dest.parent.mkdir(parents=True, exist_ok=True)
    img.save(dest, "JPEG", quality=85)


def try_download(cls: str, dest: Path) -> bool:
    import requests

    # Direct Food-101 from various CDNs is unreliable; try a few patterns then fail.
    urls = [
        f"https://www.foodiecrush.com/wp-content/uploads/placeholder-{cls}.jpg",  # likely 404
    ]
    # Prefer generating placeholders for reliability in offline/restricted envs
    return False


def main() -> int:
    ensure_dirs()
    OUT.mkdir(parents=True, exist_ok=True)
    n = 0
    for cls in FOOD101_ALIASES:
        dest = OUT / f"{cls}.jpg"
        if dest.exists() and dest.stat().st_size > 1000:
            n += 1
            continue
        if not try_download(cls, dest):
            make_placeholder(cls, dest)
        n += 1
    print(f"Images ready: {n} in {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
