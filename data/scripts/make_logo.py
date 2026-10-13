#!/usr/bin/env python3
"""Create a simple B&W + red mark logo at public/logo.png."""
from pathlib import Path

from common import ROOT

OUT = ROOT / "public" / "logo.png"


def main() -> None:
    from PIL import Image, ImageDraw, ImageFont

    size = 256
    img = Image.new("RGBA", (size, size), (255, 255, 255, 0))
    draw = ImageDraw.Draw(img)
    # Circle outline
    margin = 16
    draw.ellipse([margin, margin, size - margin, size - margin], outline=(20, 20, 20), width=10)
    # Red accent wedge
    draw.pieslice([margin + 8, margin + 8, size - margin - 8, size - margin - 8], 300, 360, fill=(196, 30, 58))
    # Center glyph "食"
    try:
        font = ImageFont.truetype("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc", 110)
    except Exception:
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 96)
        except Exception:
            font = ImageFont.load_default()
    text = "食"
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text(((size - tw) / 2, (size - th) / 2 - 8), text, fill=(20, 20, 20), font=font)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    img.save(OUT, "PNG")
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
