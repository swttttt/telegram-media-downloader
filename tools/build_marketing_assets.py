#!/usr/bin/env python3
"""Build reproducible, anonymous visual assets for the project."""

from __future__ import annotations

import math
import os
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
FONT_DIR = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts"

NAVY = "#07111f"
PANEL = "#0c1728"
PANEL_2 = "#101e33"
CYAN = "#22d3ee"
BLUE = "#3b82f6"
GREEN = "#34d399"
WHITE = "#f8fafc"
MUTED = "#94a3b8"
LINE = "#20314b"


def font(size: int, *, bold: bool = False, mono: bool = False) -> ImageFont.FreeTypeFont:
    if mono:
        candidates = ("consolab.ttf", "consola.ttf", "courbd.ttf", "cour.ttf")
    elif bold:
        candidates = ("msyhbd.ttc", "seguisb.ttf", "segoeuib.ttf", "arialbd.ttf")
    else:
        candidates = ("msyh.ttc", "segoeui.ttf", "arial.ttf")
    for name in candidates:
        path = FONT_DIR / name
        if path.exists():
            return ImageFont.truetype(str(path), size)
    return ImageFont.load_default(size=size)


def rounded_gradient(size: tuple[int, int], radius: int = 34) -> Image.Image:
    width, height = size
    image = Image.new("RGBA", size)
    pixels = image.load()
    for y in range(height):
        for x in range(width):
            mix = (x / max(width - 1, 1)) * 0.7 + (y / max(height - 1, 1)) * 0.3
            r = int(14 + 20 * mix)
            g = int(102 + 65 * mix)
            b = int(226 + 20 * mix)
            pixels[x, y] = (r, g, b, 255)
    mask = Image.new("L", size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, width - 1, height - 1), radius=radius, fill=255)
    image.putalpha(mask)
    return image


def draw_logo(image: Image.Image, box: tuple[int, int, int, int]) -> None:
    left, top, right, bottom = box
    width, height = right - left, bottom - top
    logo = rounded_gradient((width, height), max(14, width // 5))
    image.alpha_composite(logo, (left, top))
    draw = ImageDraw.Draw(image)
    plane = [
        (left + int(width * 0.18), top + int(height * 0.47)),
        (left + int(width * 0.82), top + int(height * 0.20)),
        (left + int(width * 0.66), top + int(height * 0.78)),
        (left + int(width * 0.47), top + int(height * 0.59)),
        (left + int(width * 0.35), top + int(height * 0.72)),
        (left + int(width * 0.36), top + int(height * 0.54)),
    ]
    draw.polygon(plane, fill=WHITE)
    draw.line(
        (
            left + int(width * 0.36),
            top + int(height * 0.54),
            left + int(width * 0.70),
            top + int(height * 0.31),
        ),
        fill="#bfdbfe",
        width=max(2, width // 32),
    )


def draw_chip(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    label: str,
    *,
    accent: str = CYAN,
) -> int:
    x, y = xy
    label_font = font(22, bold=True)
    bbox = draw.textbbox((0, 0), label, font=label_font)
    width = bbox[2] - bbox[0] + 52
    draw.rounded_rectangle((x, y, x + width, y + 48), radius=24, fill=PANEL_2, outline=LINE, width=2)
    draw.ellipse((x + 18, y + 19, x + 28, y + 29), fill=accent)
    draw.text((x + 38, y + 10), label, font=label_font, fill="#dbeafe")
    return width


def build_social_preview() -> None:
    width, height = 1280, 640
    image = Image.new("RGBA", (width, height), NAVY)
    draw = ImageDraw.Draw(image)

    for y in range(height):
        t = y / height
        draw.line((0, y, width, y), fill=(7, int(17 + 12 * t), int(31 + 18 * t), 255))
    for x, y, radius, color in (
        (1125, 90, 270, (17, 116, 150, 48)),
        (1040, 540, 330, (30, 64, 175, 42)),
        (120, 600, 240, (16, 185, 129, 28)),
    ):
        glow = Image.new("RGBA", image.size, (0, 0, 0, 0))
        glow_draw = ImageDraw.Draw(glow)
        glow_draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=color)
        image = Image.alpha_composite(image, glow)

    draw = ImageDraw.Draw(image)
    draw_logo(image, (92, 86, 220, 214))
    draw.text((254, 91), "TELEGRAM MEDIA", font=font(22, bold=True), fill=CYAN)
    draw.text((254, 126), "DOWNLOADER", font=font(54, bold=True), fill=WHITE)
    draw.text(
        (94, 260),
        "One link. Every original-quality file.",
        font=font(39, bold=True),
        fill=WHITE,
    )
    draw.text(
        (96, 322),
        "一条链接，完整保存原画质图片与视频",
        font=font(30, bold=True),
        fill="#cbd5e1",
    )

    x = 96
    for label, accent in (
        ("Full albums", CYAN),
        ("Discussion media", GREEN),
        ("Fast & reliable", "#fbbf24"),
    ):
        x += draw_chip(draw, (x, 412), label, accent=accent) + 16

    draw.rounded_rectangle((96, 510, 1184, 548), radius=19, fill="#0b1830", outline=LINE, width=2)
    draw.rounded_rectangle((98, 512, 880, 546), radius=17, fill=CYAN)
    draw.text((1090, 510), "73%", font=font(24, bold=True, mono=True), fill=WHITE)
    draw.text(
        (96, 575),
        "Windows portable  •  中文 / English  •  Open source",
        font=font(20, bold=True),
        fill=MUTED,
    )

    output = ASSETS / "social-preview.png"
    image.convert("RGB").save(output, optimize=True)


def terminal_frame(progress: int, stage: int) -> Image.Image:
    width, height = 960, 540
    image = Image.new("RGBA", (width, height), NAVY)
    draw = ImageDraw.Draw(image)

    draw.rounded_rectangle((24, 24, width - 24, height - 24), radius=28, fill=PANEL, outline=LINE, width=2)
    draw.ellipse((54, 51, 68, 65), fill="#fb7185")
    draw.ellipse((78, 51, 92, 65), fill="#fbbf24")
    draw.ellipse((102, 51, 116, 65), fill=GREEN)
    draw.text((352, 43), "Telegram Media Downloader", font=font(18, bold=True), fill=MUTED)

    draw_logo(image, (62, 96, 126, 160))
    draw.text((148, 96), "ORIGINAL-QUALITY MEDIA", font=font(18, bold=True), fill=CYAN)
    draw.text((148, 124), "FAST  •  RELIABLE  •  BILINGUAL", font=font(23, bold=True), fill=WHITE)

    steps = [
        ("✓", "Link accepted securely / 已安全读取链接"),
        ("✓", "Telegram login ready / Telegram 登录就绪"),
        ("✓", "Media parsed: 8 items / 已解析 8 项媒体"),
    ]
    for index, (icon, label) in enumerate(steps):
        y = 205 + index * 46
        active = stage > index
        draw.text((70, y), icon if active else "·", font=font(22, bold=True, mono=True), fill=GREEN if active else MUTED)
        draw.text((106, y), label, font=font(20, bold=active), fill=WHITE if active else MUTED)

    bar_left, bar_top, bar_right, bar_bottom = 70, 375, 800, 405
    draw.rounded_rectangle((bar_left, bar_top, bar_right, bar_bottom), radius=15, fill="#1a2940")
    filled = bar_left + int((bar_right - bar_left) * progress / 100)
    if progress:
        draw.rounded_rectangle((bar_left, bar_top, max(bar_left + 30, filled), bar_bottom), radius=15, fill=CYAN)
    draw.text((826, 373), f"{progress:>3}%", font=font(22, bold=True, mono=True), fill=WHITE)

    item_count = min(8, math.floor(progress * 8 / 100))
    status = (
        "Download complete / 下载完成"
        if progress == 100
        else f"Downloading original media  {item_count}/8"
    )
    draw.text((70, 435), status, font=font(21, bold=True), fill=GREEN if progress == 100 else "#dbeafe")
    draw.text(
        (70, 476),
        "No screenshots  •  No recompression  •  Integrity checked",
        font=font(17, bold=True),
        fill=MUTED,
    )
    return image.convert("P", palette=Image.Palette.ADAPTIVE, colors=128)


def build_demo() -> None:
    frames: list[Image.Image] = []
    durations: list[int] = []
    sequence = [
        (0, 0, 800),
        (0, 1, 650),
        (0, 2, 650),
        (0, 3, 500),
        (18, 3, 380),
        (41, 3, 380),
        (73, 3, 420),
        (100, 3, 1200),
    ]
    for progress, stage, duration in sequence:
        frames.append(terminal_frame(progress, stage))
        durations.append(duration)
    frames[0].save(
        ASSETS / "demo.gif",
        save_all=True,
        append_images=frames[1:],
        duration=durations,
        loop=0,
        optimize=True,
        disposal=2,
    )


def build_icon() -> None:
    master = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
    draw_logo(master, (8, 8, 248, 248))
    master.save(
        ASSETS / "app.ico",
        format="ICO",
        sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
    )


def main() -> None:
    ASSETS.mkdir(parents=True, exist_ok=True)
    build_social_preview()
    build_demo()
    build_icon()
    for name in ("social-preview.png", "demo.gif", "app.ico"):
        path = ASSETS / name
        print(f"built {path.relative_to(ROOT)} ({path.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
