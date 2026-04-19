#!/usr/bin/env python3

import argparse
import base64
import collections
import json
import pathlib
import sys
import urllib.request
from urllib.error import HTTPError, URLError
from typing import Optional

from PIL import Image, ImageChops, ImageColor, ImageOps


DEFAULT_PROMPT = (
    "A premium mobile game asset: a single glossy arrow point icon pointing right, "
    "clean isolated sprite on transparent background, candy-like polished 2D style, "
    "bright yellow-orange gradient, subtle highlight, bold outline, simple readable "
    "shape, centered composition, no text, no scene"
)

DEFAULT_PALETTE = [
    ("gold", "#ffb703"),
    ("yellow", "#ffeb3b"),
    ("red", "#ff5466"),
    ("purple", "#8f55ff"),
    ("green", "#6fe64e"),
    ("blue", "#4ea4ff"),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate transparent OpenAI images and optional tinted sprite sheets."
    )
    parser.add_argument("--env-file", default=".env")
    parser.add_argument("--env-key", default="openai-arturov-apikey")
    parser.add_argument("--model", default="gpt-image-1")
    parser.add_argument("--prompt", default=DEFAULT_PROMPT)
    parser.add_argument("--size", default="1024x1024")
    parser.add_argument("--background", default="transparent")
    parser.add_argument("--output-format", default="png")
    parser.add_argument("--output", type=pathlib.Path)
    parser.add_argument("--base-image", type=pathlib.Path)
    parser.add_argument("--sprite-sheet-output", type=pathlib.Path)
    parser.add_argument("--metadata-output", type=pathlib.Path)
    parser.add_argument("--cell-size", type=int, default=128)
    parser.add_argument("--padding", type=int, default=12)
    parser.add_argument(
        "--extract-center-component",
        action="store_true",
        default=True,
        help="Extract only the alpha-connected component nearest image center (default on)",
    )
    parser.add_argument(
        "--no-extract-center-component",
        dest="extract_center_component",
        action="store_false",
        help="Disable center-component extraction",
    )
    parser.add_argument(
        "--palette",
        nargs="*",
        default=[f"{name}={color}" for name, color in DEFAULT_PALETTE],
        help="Space-separated name=#RRGGBB entries",
    )
    return parser.parse_args()


def load_api_key(env_file: pathlib.Path, env_key: str) -> str:
    for raw_line in env_file.read_text().splitlines():
      line = raw_line.strip()
      if not line or line.startswith("#") or "=" not in line:
          continue
      key, value = line.split("=", 1)
      if key.strip() == env_key:
          return value.strip()
    raise RuntimeError(f"Key '{env_key}' not found in {env_file}")


def ensure_parent(path: pathlib.Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def request_image(args: argparse.Namespace, api_key: str, output_path: pathlib.Path) -> pathlib.Path:
    payload = {
        "model": args.model,
        "size": args.size,
        "background": args.background,
        "output_format": args.output_format,
        "prompt": args.prompt,
    }
    request = urllib.request.Request(
        "https://api.openai.com/v1/images/generations",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            body = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        details = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code}: {details[:2000]}") from exc
    except URLError as exc:
        raise RuntimeError(f"Network error: {exc}") from exc

    images = body.get("data") or []
    if not images or not images[0].get("b64_json"):
        raise RuntimeError(f"Unexpected image response: {json.dumps(body)[:2000]}")

    ensure_parent(output_path)
    output_path.write_bytes(base64.b64decode(images[0]["b64_json"]))
    return output_path


def parse_palette(entries: list[str]) -> list[tuple[str, str]]:
    parsed: list[tuple[str, str]] = []
    for entry in entries:
        if "=" not in entry:
            raise ValueError(f"Invalid palette entry '{entry}'. Expected name=#RRGGBB")
        name, color = entry.split("=", 1)
        parsed.append((name.strip(), color.strip()))
    if not parsed:
        raise ValueError("Palette must contain at least one entry")
    return parsed


def shift_color(color: str, factor: float) -> str:
    red, green, blue = ImageColor.getrgb(color)
    red = max(0, min(255, round(red * factor)))
    green = max(0, min(255, round(green * factor)))
    blue = max(0, min(255, round(blue * factor)))
    return f"#{red:02x}{green:02x}{blue:02x}"


def tinted_variant(base_image: Image.Image, color: str) -> Image.Image:
    rgba = base_image.convert("RGBA")
    alpha = rgba.getchannel("A")
    grayscale = ImageOps.grayscale(rgba)
    tinted = ImageOps.colorize(
        grayscale,
        black=shift_color(color, 0.48),
        mid=color,
        white=shift_color(color, 1.35),
    ).convert("RGBA")
    tinted.putalpha(alpha)

    shadow = Image.new("RGBA", rgba.size, (0, 0, 0, 0))
    shadow_alpha = ImageChops.multiply(alpha, Image.new("L", rgba.size, 105))
    shadow.putalpha(shadow_alpha)
    shadow = shadow.transform(rgba.size, Image.AFFINE, (1, 0, 8, 0, 1, 8))

    composed = Image.new("RGBA", rgba.size, (0, 0, 0, 0))
    composed.alpha_composite(shadow)
    composed.alpha_composite(tinted)
    return composed


def nearest_opaque_pixel(alpha: Image.Image) -> Optional[tuple[int, int]]:
    width, height = alpha.size
    cx = width // 2
    cy = height // 2
    pixels = alpha.load()
    if pixels[cx, cy] > 0:
        return (cx, cy)

    best = None
    best_dist = float("inf")
    for y in range(height):
        for x in range(width):
            if pixels[x, y] == 0:
                continue
            dx = x - cx
            dy = y - cy
            dist = dx * dx + dy * dy
            if dist < best_dist:
                best_dist = dist
                best = (x, y)
    return best


def extract_center_component(image: Image.Image) -> Image.Image:
    rgba = image.convert("RGBA")
    alpha = rgba.getchannel("A")
    seed = nearest_opaque_pixel(alpha)
    if seed is None:
        return rgba

    width, height = alpha.size
    pixels = alpha.load()
    visited = set()
    queue = collections.deque([seed])
    visited.add(seed)

    min_x = seed[0]
    min_y = seed[1]
    max_x = seed[0]
    max_y = seed[1]

    while queue:
        x, y = queue.popleft()
        if x < min_x:
            min_x = x
        if y < min_y:
            min_y = y
        if x > max_x:
            max_x = x
        if y > max_y:
            max_y = y

        for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
            if nx < 0 or ny < 0 or nx >= width or ny >= height:
                continue
            if (nx, ny) in visited:
                continue
            if pixels[nx, ny] == 0:
                continue
            visited.add((nx, ny))
            queue.append((nx, ny))

    cropped = rgba.crop((min_x, min_y, max_x + 1, max_y + 1))
    if cropped.width < 2 or cropped.height < 2:
        return rgba
    return cropped


def build_sprite_sheet(
    base_image_path: pathlib.Path,
    sprite_sheet_output: pathlib.Path,
    metadata_output: Optional[pathlib.Path],
    palette: list[tuple[str, str]],
    cell_size: int,
    padding: int,
    extract_center_component_enabled: bool,
) -> pathlib.Path:
    base_image = Image.open(base_image_path).convert("RGBA")
    if extract_center_component_enabled:
        base_image = extract_center_component(base_image)
    sheet = Image.new("RGBA", (cell_size * len(palette), cell_size), (0, 0, 0, 0))
    metadata = {"cellSize": cell_size, "sprites": []}

    for index, (name, color) in enumerate(palette):
        sprite = tinted_variant(base_image, color)
        sprite.thumbnail((cell_size - padding * 2, cell_size - padding * 2), Image.LANCZOS)
        x = index * cell_size + (cell_size - sprite.width) // 2
        y = (cell_size - sprite.height) // 2
        sheet.alpha_composite(sprite, (x, y))
        metadata["sprites"].append({"name": name, "color": color, "x": index * cell_size, "y": 0})

    ensure_parent(sprite_sheet_output)
    sheet.save(sprite_sheet_output)
    if metadata_output:
        ensure_parent(metadata_output)
        metadata_output.write_text(json.dumps(metadata, indent=2))
    return sprite_sheet_output


def main() -> int:
    args = parse_args()
    palette = parse_palette(args.palette)

    base_image_path = args.base_image
    if args.output:
        api_key = load_api_key(pathlib.Path(args.env_file), args.env_key)
        base_image_path = request_image(args, api_key, args.output)
        print(f"Generated image: {base_image_path}")

    if args.sprite_sheet_output:
        if not base_image_path:
            raise RuntimeError("Provide --output or --base-image when building a sprite sheet")
        sprite_path = build_sprite_sheet(
            base_image_path=base_image_path,
            sprite_sheet_output=args.sprite_sheet_output,
            metadata_output=args.metadata_output,
            palette=palette,
            cell_size=args.cell_size,
            padding=args.padding,
            extract_center_component_enabled=args.extract_center_component,
        )
        print(f"Generated sprite sheet: {sprite_path}")

    if not args.output and not args.sprite_sheet_output:
        raise RuntimeError("Nothing to do. Provide --output and/or --sprite-sheet-output")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)