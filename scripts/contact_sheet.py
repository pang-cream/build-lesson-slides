from __future__ import annotations

import argparse
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps


def sheet_size(count: int, columns: int, width: int, height: int) -> tuple[int, int]:
    return columns * width, math.ceil(count / columns) * (height + 22)


def compose(paths: list[Path], columns: int = 4, width: int = 320) -> Image.Image:
    images = [Image.open(path).convert("RGB") for path in paths]
    if not images:
        raise ValueError("No preview images found.")
    height = round(width * images[0].height / images[0].width)
    sheet = Image.new("RGB", sheet_size(len(images), columns, width, height), "white")
    draw = ImageDraw.Draw(sheet)
    for index, image in enumerate(images):
        x = index % columns * width
        y = index // columns * (height + 22)
        sheet.paste(ImageOps.contain(image, (width, height)), (x, y))
        draw.text((x + 6, y + height + 3), f"{index + 1}", fill="#18243B")
    return sheet


def main() -> int:
    parser = argparse.ArgumentParser(description="Combine rendered slide previews into one contact sheet.")
    parser.add_argument("preview_dir", nargs="?", default="previews")
    parser.add_argument("output", nargs="?", default="previews/contact-sheet.png")
    parser.add_argument("--columns", type=int, default=4)
    parser.add_argument("--width", type=int, default=320)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        assert sheet_size(13, 4, 320, 180) == (1280, 808)
        print("contact-sheet self-test: ok")
        return 0
    paths = sorted(Path(args.preview_dir).glob("slide-*.png"))
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    compose(paths, args.columns, args.width).save(output)
    print(output.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
