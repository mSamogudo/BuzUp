"""Generate ticket decoration PNG assets (bus + skyline + bridge).

Run with:
    .venv/bin/python scripts/generate_ticket_assets.py
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter


ASSETS_DIR = Path(__file__).resolve().parent.parent / "static" / "assets" / "ticket"
ASSETS_DIR.mkdir(parents=True, exist_ok=True)

WIDTH = 1200
HEADER_HEIGHT = 600
FOOTER_HEIGHT = 220


def _draw_buildings(draw: ImageDraw.ImageDraw, color, opacity: int, baseline: int, x_offset: int = 0):
    rgba = color + (opacity,)
    blocks = [
        (60, 110, 70, 220),
        (140, 90, 90, 240),
        (240, 130, 95, 200),
        (340, 70, 110, 260),
        (460, 110, 80, 230),
        (550, 95, 100, 245),
        (660, 140, 80, 200),
        (750, 80, 95, 250),
        (855, 120, 90, 220),
        (955, 95, 110, 245),
        (1075, 110, 90, 230),
    ]
    for x, h, w, _max in blocks:
        x += x_offset
        draw.rectangle((x, baseline - h, x + w, baseline), fill=rgba)
        for win_y in range(baseline - h + 15, baseline - 10, 22):
            for win_x in range(x + 10, x + w - 10, 16):
                draw.rectangle((win_x, win_y, win_x + 6, win_y + 10), fill=color + (max(opacity - 20, 30),))


def _draw_bridge(draw: ImageDraw.ImageDraw, color, opacity: int, baseline: int):
    rgba = color + (opacity,)
    pylon_left_x = 720
    pylon_right_x = 1020
    pylon_top_y = baseline - 320
    deck_y = baseline - 70

    draw.line((550, deck_y, 1170, deck_y), fill=rgba, width=4)

    draw.rectangle((pylon_left_x - 8, pylon_top_y, pylon_left_x + 8, deck_y), fill=rgba)
    draw.rectangle((pylon_right_x - 8, pylon_top_y, pylon_right_x + 8, deck_y), fill=rgba)
    draw.line((pylon_left_x - 28, pylon_top_y - 10, pylon_left_x + 28, pylon_top_y - 10), fill=rgba, width=3)
    draw.line((pylon_right_x - 28, pylon_top_y - 10, pylon_right_x + 28, pylon_top_y - 10), fill=rgba, width=3)

    for k in range(6):
        offset = k * 24
        draw.line((pylon_left_x, pylon_top_y, pylon_left_x - 90 + offset, deck_y), fill=rgba, width=2)
        draw.line((pylon_left_x, pylon_top_y, pylon_left_x + 60 + offset, deck_y), fill=rgba, width=2)
        draw.line((pylon_right_x, pylon_top_y, pylon_right_x - 60 - offset, deck_y), fill=rgba, width=2)
        draw.line((pylon_right_x, pylon_top_y, pylon_right_x + 60 + offset, deck_y), fill=rgba, width=2)


def _draw_bus(canvas: Image.Image, color, opacity: int, center_x: int, baseline: int):
    bus = Image.new("RGBA", (560, 240), (0, 0, 0, 0))
    bd = ImageDraw.Draw(bus)
    rgba = color + (opacity,)
    fill_dark = color + (max(opacity - 40, 30),)

    bd.rounded_rectangle((20, 40, 540, 200), radius=24, outline=rgba, width=5, fill=fill_dark)
    bd.rounded_rectangle((40, 30, 510, 80), radius=22, outline=rgba, width=5, fill=fill_dark)

    window_y0 = 70
    window_y1 = 130
    win_x_start = 60
    win_x_end = 510
    win_width = 56
    gap = 18
    x = win_x_start
    while x + win_width < win_x_end:
        bd.rounded_rectangle((x, window_y0, x + win_width, window_y1), radius=8, fill=rgba)
        x += win_width + gap

    bd.rectangle((win_x_end - 90, 145, win_x_end - 30, 195), outline=rgba, width=4)
    bd.line((win_x_end - 90, 170, win_x_end - 30, 170), fill=rgba, width=2)

    bd.line((40, 165, 500, 165), fill=rgba, width=3)

    for cx in (140, 420):
        bd.ellipse((cx - 32, 180, cx + 32, 244), fill=color + (255,), outline=rgba, width=2)
        bd.ellipse((cx - 16, 196, cx + 16, 228), fill=(0, 0, 0, 0), outline=rgba, width=2)

    bd.rectangle((40, 90, 80, 130), fill=rgba)

    canvas.alpha_composite(bus, dest=(center_x - bus.width // 2, baseline - bus.height + 24))


def build_header_image(width: int = WIDTH, height: int = HEADER_HEIGHT) -> Image.Image:
    img = Image.new("RGBA", (width, height), (7, 30, 73, 255))
    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))

    for y in range(height):
        factor = y / height
        c = int(10 + factor * 8)
        ImageDraw.Draw(img).line((0, y, width, y), fill=(c, 26 + int(factor * 10), 73 + int(factor * 14), 255))

    draw = ImageDraw.Draw(overlay)
    for y in range(0, 90, 6):
        for x in range(0, width, 14):
            if (x + y) % 28 == 0:
                draw.ellipse((x, y, x + 2, y + 2), fill=(255, 255, 255, 40))

    skyline_baseline = height - 30
    _draw_bridge(draw, (255, 255, 255), 70, skyline_baseline)
    _draw_buildings(draw, (255, 255, 255), 55, skyline_baseline)
    _draw_buildings(draw, (255, 255, 255), 35, skyline_baseline + 6, x_offset=40)

    _draw_bus(overlay, (255, 255, 255), 230, center_x=int(width * 0.62), baseline=skyline_baseline - 4)

    overlay = overlay.filter(ImageFilter.GaussianBlur(radius=0.4))
    img.alpha_composite(overlay)

    return img


def build_footer_image(width: int = WIDTH, height: int = FOOTER_HEIGHT) -> Image.Image:
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    baseline = height - 10
    _draw_buildings(draw, (148, 163, 184), 75, baseline)
    _draw_buildings(draw, (148, 163, 184), 50, baseline + 6, x_offset=60)

    overlay = overlay.filter(ImageFilter.GaussianBlur(radius=0.8))
    img.alpha_composite(overlay)
    return img


def main():
    header = build_header_image()
    footer = build_footer_image()
    header.save(ASSETS_DIR / "header_decoration.png", "PNG")
    footer.save(ASSETS_DIR / "footer_skyline.png", "PNG")
    print(f"Wrote: {ASSETS_DIR / 'header_decoration.png'}")
    print(f"Wrote: {ASSETS_DIR / 'footer_skyline.png'}")


if __name__ == "__main__":
    main()
