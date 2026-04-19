#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image, ImageOps


INFERRED_PALETTE = {
    "#ffeb3b": "yellow",
    "#ff5466": "red",
    "#a768ff": "purple",
    "#78d63d": "green",
    "#4b97ff": "blue",
}


def clamp_u8(v: float) -> int:
    return max(0, min(255, int(round(v))))


def hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    s = hex_color.strip().lstrip("#")
    if len(s) != 6:
        raise ValueError(f"Invalid hex color: {hex_color}")
    return int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16)


def mix_rgb(a: tuple[int, int, int], b: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    return (
        clamp_u8(a[0] + (b[0] - a[0]) * t),
        clamp_u8(a[1] + (b[1] - a[1]) * t),
        clamp_u8(a[2] + (b[2] - a[2]) * t),
    )


def tight_crop(image: Image.Image, alpha_threshold: int = 8) -> Image.Image:
    rgba = image.convert("RGBA")
    alpha = rgba.getchannel("A")
    bbox = alpha.point(lambda p: 255 if p > alpha_threshold else 0).getbbox()
    if not bbox:
        return rgba
    return rgba.crop(bbox)


def split_head_and_body(source_arrow: Image.Image) -> tuple[Image.Image, Image.Image]:
    src = tight_crop(source_arrow)
    w, h = src.size
    head_cut_x = int(w * 0.63)
    body = src.crop((0, 0, head_cut_x, h))
    head = src.crop((int(w * 0.47), 0, w, h))

    body = tight_crop(body)
    head = tight_crop(head)

    # Extract a clean shaft strip from center rows of the body for repeatable texture.
    bw, bh = body.size
    strip_h = max(14, int(bh * 0.46))
    strip_y = (bh - strip_h) // 2
    strip = body.crop((0, strip_y, bw, strip_y + strip_h))
    strip = tight_crop(strip)

    return head, strip


def tint_preserve_shading(base_rgba: Image.Image, target_hex: str) -> Image.Image:
    base = base_rgba.convert("RGBA")
    alpha = base.getchannel("A")
    gray = ImageOps.grayscale(base)

    target = hex_to_rgb(target_hex)
    dark = mix_rgb(target, (0, 0, 0), 0.46)
    mid = mix_rgb(target, (255, 255, 255), 0.06)
    light = mix_rgb(target, (255, 255, 255), 0.58)

    colored = ImageOps.colorize(gray, black=dark, mid=mid, white=light)
    colored.putalpha(alpha)
    return colored


def build_sheet(base_img: Image.Image, colors: list[str], cell_size: int) -> Image.Image:
    out = Image.new("RGBA", (cell_size * len(colors), cell_size), (0, 0, 0, 0))
    for i, color in enumerate(colors):
        tinted = tint_preserve_shading(base_img, color)
        fitted = ImageOps.contain(tinted, (cell_size, cell_size), method=Image.Resampling.LANCZOS)
        x = i * cell_size + (cell_size - fitted.width) // 2
        y = (cell_size - fitted.height) // 2
        out.alpha_composite(fitted, (x, y))
    return out


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Infer bottom-arrow assets from screenshot-derived source arrow")
    parser.add_argument("--source", default="assets/forwardarrow.png", help="Path to right-facing source arrow PNG")
    parser.add_argument("--out-dir", default="assets/experiment", help="Output asset directory")
    parser.add_argument("--cell", type=int, default=128, help="Sprite sheet cell size")
    args = parser.parse_args()

    source_path = Path(args.source)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    source = Image.open(source_path).convert("RGBA")
    head, strip = split_head_and_body(source)

    head_base_path = out_dir / "bottom_arrow_head_inferred_base.png"
    strip_base_path = out_dir / "bottom_arrow_body_inferred_base.png"
    head_sheet_path = out_dir / "bottom_arrow_heads_sheet_inferred.png"
    strip_sheet_path = out_dir / "bottom_arrow_body_sheet_inferred.png"
    meta_path = out_dir / "bottom_arrow_inferred_palette.json"

    head.save(head_base_path)
    strip.save(strip_base_path)

    colors = list(INFERRED_PALETTE.keys())
    head_sheet = build_sheet(head, colors, args.cell)
    strip_sheet = build_sheet(strip, colors, args.cell)
    head_sheet.save(head_sheet_path)
    strip_sheet.save(strip_sheet_path)

    write_json(
        meta_path,
        {
            "source": str(source_path).replace('\\\\', '/'),
            "cell": args.cell,
            "colors": [
                {"hex": c, "name": INFERRED_PALETTE[c], "index": i}
                for i, c in enumerate(colors)
            ],
            "outputs": {
                "headBase": str(head_base_path).replace('\\\\', '/'),
                "bodyBase": str(strip_base_path).replace('\\\\', '/'),
                "headSheet": str(head_sheet_path).replace('\\\\', '/'),
                "bodySheet": str(strip_sheet_path).replace('\\\\', '/'),
            },
        },
    )

    print(f"Generated inferred arrow assets in {out_dir}")


if __name__ == "__main__":
    main()
