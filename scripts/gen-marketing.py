#!/usr/bin/env python3
"""Generate app-store marketing images for Internet's Dream.

Outputs (into assets/store/):
  icon-512.png            Play Store icon
  feature-graphic.png     1024x500 Play feature graphic
  promo-banner.png        social share banner 1200x630
  screenshot-phone.png    styled phone-frame screenshot (uses web dash PNG)
"""

from PIL import Image, ImageDraw, ImageFont, ImageFilter
from pathlib import Path

OUT = Path(__file__).parent.parent / "assets" / "store"
OUT.mkdir(parents=True, exist_ok=True)

PURPLE = (109, 75, 216)
PINK = (232, 93, 158)
CREAM = (250, 247, 255)
DARK = (28, 26, 46)


def vgrad(size, top, bottom):
    w, h = size
    img = Image.new("RGB", size)
    px = img.load()
    for y in range(h):
        t = y / max(h - 1, 1)
        c = tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3))
        for x in range(w):
            px[x, y] = c
    return img


def font(size, bold=True):
    for path in (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold
        else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf" if bold
        else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ):
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def rounded_mask(size, radius):
    m = Image.new("L", size, 0)
    d = ImageDraw.Draw(m)
    d.rounded_rectangle([0, 0, size[0] - 1, size[1] - 1],
                        radius=radius, fill=255)
    return m


def make_icon():
    size = (512, 512)
    img = vgrad(size, PURPLE, PINK)
    mask = rounded_mask(size, 112)
    canvas = Image.new("RGBA", size, (0, 0, 0, 0))
    canvas.paste(img, (0, 0), mask)
    d = ImageDraw.Draw(canvas)
    # crescent moon
    d.ellipse([176, 96, 336, 256], fill=CREAM)
    d.ellipse([216, 76, 356, 216], fill=(109, 75, 216))
    # stars
    for (x, y, r) in [(390, 120, 7), (120, 380, 6), (400, 400, 5), (110, 130, 5)]:
        d.ellipse([x - r, y - r, x + r, y + r], fill=(255, 217, 232))
    canvas.save(OUT / "icon-512.png")


def make_feature():
    size = (1024, 500)
    img = vgrad(size, (42, 30, 80), PURPLE)
    d = ImageDraw.Draw(img)
    # soft glow circles
    for (x, y, r, col) in [(880, 80, 180, (232, 93, 158, 90)),
                           (120, 420, 160, (120, 90, 220, 70))]:
        d.ellipse([x - r, y - r, x + r, y + r], fill=col)
    d.text((64, 150), "Internet's Dream", font=font(72), fill=CREAM)
    d.text((64, 250), "Your entire digital life —\nindexed, encrypted, searchable.",
           font=font(30, bold=False), fill=(230, 224, 250), spacing=10)
    chips = ["Gmail", "Calendar", "Discord", "Telegram", "WhatsApp",
             "YouTube", "Drive", "Browser", "Files"]
    x, y = 64, 400
    for c in chips:
        f = font(22)
        w = d.textlength(c, font=f) + 36
        d.rounded_rectangle([x, y, x + w, y + 44], radius=22,
                            fill=(255, 255, 255, 45), outline=(255, 255, 255, 90))
        d.text((x + 18, y + 10), c, font=f, fill=CREAM)
        x += w + 14
        if x > 900:
            x, y = 64, 460
    img.save(OUT / "feature-graphic.png")


def make_banner():
    size = (1200, 630)
    img = vgrad(size, (42, 30, 80), (90, 55, 160))
    d = ImageDraw.Draw(img)
    d.text((80, 200), "Internet's Dream", font=font(84), fill=CREAM)
    d.text((80, 320), "A private second brain for everything\nyou've ever saved, said, or visited.",
           font=font(34, bold=False), fill=(230, 224, 250), spacing=12)
    d.rounded_rectangle([80, 500, 380, 556], radius=28,
                        fill=PURPLE, outline=(255, 255, 255, 120), width=3)
    d.text((130, 514), "Try it free →", font=font(28), fill=CREAM)
    img.save(OUT / "promo-banner.png")


if __name__ == "__main__":
    make_icon()
    make_feature()
    make_banner()
    print("store images written to", OUT)
