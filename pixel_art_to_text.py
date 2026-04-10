#!/usr/bin/env python3
"""
Convert pixel art images into a reusable text-based format.

Output format is plain text and includes:
1) metadata (width, height, mode)
2) a palette that maps short symbols to exact RGBA colors
3) a row-by-row pixel grid using palette symbols

This is lossless for exact pixel colors and is easy to parse later.

Usage:
  python pixel_art_to_text.py input.png
  python pixel_art_to_text.py input.png -o sprite.txt
  python pixel_art_to_text.py input.png --transparent-as-dot
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from PIL import Image

Color = Tuple[int, int, int, int]


def index_to_symbol(index: int) -> str:
    """Create compact palette symbols: A..Z, AA..AZ, BA..ZZ, AAA..."""
    alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    # 0 -> A, 25 -> Z, 26 -> AA (Excel-style column naming)
    n = index + 1
    chars: List[str] = []
    while n > 0:
        n -= 1
        chars.append(alphabet[n % 26])
        n //= 26
    return "".join(reversed(chars))


def image_to_palette_grid(image_path: Path, transparent_as_dot: bool) -> Tuple[Dict[Color, str], List[List[str]], int, int]:
    img = Image.open(image_path).convert("RGBA")
    width, height = img.size
    pixels = list(img.getdata())

    palette: Dict[Color, str] = {}
    next_idx = 0

    grid: List[List[str]] = []
    for y in range(height):
        row: List[str] = []
        for x in range(width):
            c = pixels[y * width + x]

            if transparent_as_dot and c[3] == 0:
                row.append(".")
                continue

            if c not in palette:
                palette[c] = index_to_symbol(next_idx)
                next_idx += 1

            row.append(palette[c])
        grid.append(row)

    return palette, grid, width, height


def preprocess_image(
    image_path: Path,
    force_size: Optional[Tuple[int, int]],
    max_colors: Optional[int],
) -> Image.Image:
    img = Image.open(image_path).convert("RGBA")

    return preprocess_pil_image(img, force_size=force_size, max_colors=max_colors)


def preprocess_pil_image(
    img: Image.Image,
    force_size: Optional[Tuple[int, int]],
    max_colors: Optional[int],
) -> Image.Image:
    img = img.convert("RGBA")

    # Preserve hard edges when recovering pixel art from upscaled images.
    if force_size is not None:
        img = img.resize(force_size, resample=Image.NEAREST)

    # Reduce colors deterministically to the requested palette size.
    if max_colors is not None:
        quantized = img.convert("P", palette=Image.ADAPTIVE, colors=max_colors)
        img = quantized.convert("RGBA")

    return img


def infer_grid_candidates(
    img: Image.Image,
    min_size: Tuple[int, int],
    max_size: Tuple[int, int],
    top_k: int,
) -> List[Tuple[float, int, int]]:
    """Return best candidate grids as (score, width, height), lower score is better."""
    img = img.convert("RGBA")
    src_w, src_h = img.size

    min_w, min_h = min_size
    max_w, max_h = max_size

    if min_w > max_w or min_h > max_h:
        raise ValueError("infer min size must be <= infer max size")

    max_w = min(max_w, src_w)
    max_h = min(max_h, src_h)

    candidates: List[Tuple[float, int, int]] = []
    src_pixels = list(img.getdata())
    max_delta = 4 * 255

    for gw in range(min_w, max_w + 1):
        for gh in range(min_h, max_h + 1):
            down = img.resize((gw, gh), resample=Image.NEAREST)
            up = down.resize((src_w, src_h), resample=Image.NEAREST)
            up_pixels = list(up.getdata())

            total_delta = 0
            for a, b in zip(src_pixels, up_pixels):
                total_delta += (
                    abs(a[0] - b[0])
                    + abs(a[1] - b[1])
                    + abs(a[2] - b[2])
                    + abs(a[3] - b[3])
                )

            mean_delta = total_delta / (len(src_pixels) * max_delta)
            candidates.append((mean_delta, gw, gh))

    candidates.sort(key=lambda item: item[0])
    return candidates[:top_k]


def pil_image_to_palette_grid(img: Image.Image, transparent_as_dot: bool) -> Tuple[Dict[Color, str], List[List[str]], int, int]:
    width, height = img.size
    pixels = list(img.getdata())

    palette: Dict[Color, str] = {}
    next_idx = 0

    grid: List[List[str]] = []
    for y in range(height):
        row: List[str] = []
        for x in range(width):
            c = pixels[y * width + x]

            if transparent_as_dot and c[3] == 0:
                row.append(".")
                continue

            if c not in palette:
                palette[c] = index_to_symbol(next_idx)
                next_idx += 1

            row.append(palette[c])
        grid.append(row)

    return palette, grid, width, height


def render_text(
    palette: Dict[Color, str],
    grid: List[List[str]],
    width: int,
    height: int,
    image_name: str,
    transparent_as_dot: bool,
) -> str:
    lines: List[str] = []

    lines.append("# PIXEL_ART_TEXT v1")
    lines.append(f"image: {image_name}")
    lines.append(f"width: {width}")
    lines.append(f"height: {height}")
    lines.append("mode: RGBA")
    lines.append(f"transparent_as_dot: {str(transparent_as_dot).lower()}")
    lines.append("")

    lines.append("[PALETTE]")
    if transparent_as_dot:
        lines.append(". = (0,0,0,0)  # transparent")

    for color, symbol in sorted(palette.items(), key=lambda item: item[1]):
        r, g, b, a = color
        lines.append(f"{symbol} = ({r},{g},{b},{a})")

    lines.append("")
    lines.append("[PIXELS]")
    for row in grid:
        lines.append(" ".join(row))

    return "\n".join(lines) + "\n"


def default_output_path(image_path: Path) -> Path:
    return image_path.with_suffix(".pixel.txt")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Convert a pixel art image into text format.")
    parser.add_argument("input", type=Path, help="Path to image file (png/jpg/etc.)")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Output text file (default: <input>.pixel.txt)",
    )
    parser.add_argument(
        "--transparent-as-dot",
        action="store_true",
        help="Represent fully transparent pixels with '.'",
    )
    parser.add_argument(
        "--size",
        type=str,
        default=None,
        help="Force image size before export, e.g. 10x10 (uses nearest-neighbor)",
    )
    parser.add_argument(
        "--max-colors",
        type=int,
        default=None,
        help="Reduce palette to this number of colors before export",
    )
    parser.add_argument(
        "--infer-grid",
        action="store_true",
        help="Test candidate grid sizes and print best matches",
    )
    parser.add_argument(
        "--infer-min-size",
        type=str,
        default="4x4",
        help="Minimum candidate size for --infer-grid, e.g. 4x4",
    )
    parser.add_argument(
        "--infer-max-size",
        type=str,
        default="64x64",
        help="Maximum candidate size for --infer-grid, e.g. 64x64",
    )
    parser.add_argument(
        "--infer-top-k",
        type=int,
        default=5,
        help="How many top inferred grid sizes to print",
    )
    parser.add_argument(
        "--use-inferred-size",
        action="store_true",
        help="When using --infer-grid, convert using best inferred size",
    )
    return parser.parse_args()


def parse_size(size_str: Optional[str]) -> Optional[Tuple[int, int]]:
    if size_str is None:
        return None

    parts = size_str.lower().split("x")
    if len(parts) != 2:
        raise ValueError("--size must be formatted as <width>x<height>, e.g. 10x10")

    w, h = int(parts[0]), int(parts[1])
    if w <= 0 or h <= 0:
        raise ValueError("--size values must be positive integers")

    return w, h


def main() -> None:
    args = parse_args()

    if not args.input.exists():
        raise FileNotFoundError(f"Input image not found: {args.input}")

    output_path = args.output if args.output else default_output_path(args.input)

    force_size = parse_size(args.size)
    infer_min_size = parse_size(args.infer_min_size)
    infer_max_size = parse_size(args.infer_max_size)
    if infer_min_size is None or infer_max_size is None:
        raise ValueError("infer size bounds must be provided")

    if args.max_colors is not None and args.max_colors <= 0:
        raise ValueError("--max-colors must be a positive integer")
    if args.infer_top_k <= 0:
        raise ValueError("--infer-top-k must be a positive integer")
    if args.use_inferred_size and not args.infer_grid:
        raise ValueError("--use-inferred-size requires --infer-grid")

    src_img = Image.open(args.input).convert("RGBA")

    if args.infer_grid:
        top_candidates = infer_grid_candidates(
            src_img,
            min_size=infer_min_size,
            max_size=infer_max_size,
            top_k=args.infer_top_k,
        )

        print("Inferred grid candidates (lower score is better):")
        for score, w, h in top_candidates:
            print(f"  {w}x{h}  score={score:.6f}")

        if args.use_inferred_size and top_candidates:
            _, best_w, best_h = top_candidates[0]
            force_size = (best_w, best_h)
            print(f"Using inferred best size: {best_w}x{best_h}")

    preprocessed = preprocess_pil_image(
        src_img,
        force_size=force_size,
        max_colors=args.max_colors,
    )

    palette, grid, width, height = pil_image_to_palette_grid(
        preprocessed,
        transparent_as_dot=args.transparent_as_dot,
    )

    text_output = render_text(
        palette=palette,
        grid=grid,
        width=width,
        height=height,
        image_name=args.input.name,
        transparent_as_dot=args.transparent_as_dot,
    )

    output_path.write_text(text_output, encoding="utf-8")
    print(f"Saved text pixel art to: {output_path}")
    print(f"Palette colors: {len(palette)}")
    if force_size is not None:
        print(f"Forced size: {force_size[0]}x{force_size[1]}")
    if args.max_colors is not None:
        print(f"Forced max colors: {args.max_colors}")


if __name__ == "__main__":
    main()
