"""توليد بانرات PNG احترافية من هوية SVG."""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
BANNERS = ROOT / "assets" / "banners"

THEMES = {
    "main": {"bg1": "#0F0F23", "bg2": "#6C5CE7", "accent": "#FDCB6E", "title": "روليت غزاوي"},
    "quick": {"bg1": "#1A1A2E", "bg2": "#00CEC9", "accent": "#FDCB6E", "title": "الروليت السريع"},
    "create": {"bg1": "#162447", "bg2": "#A29BFE", "accent": "#FD79A8", "title": "إنشاء روليت"},
    "my_raffles": {"bg1": "#1B1464", "bg2": "#FD79A8", "accent": "#FDCB6E", "title": "سحوباتي"},
    "channel_log": {"bg1": "#0B5345", "bg2": "#00CEC9", "accent": "#FDCB6E", "title": "سجل القناة"},
    "statistics": {"bg1": "#0C2461", "bg2": "#0984E3", "accent": "#00CEC9", "title": "الإحصائيات"},
    "privacy": {"bg1": "#2D3436", "bg2": "#636E72", "accent": "#74B9FF", "title": "الخصوصية"},
    "terms": {"bg1": "#2D3436", "bg2": "#6C5CE7", "accent": "#FDCB6E", "title": "الشروط"},
    "competition": {"bg1": "#4A148C", "bg2": "#E17055", "accent": "#FDCB6E", "title": "مسابقة"},
    "leaderboard": {"bg1": "#1A237E", "bg2": "#FDCB6E", "accent": "#FD79A8", "title": "لوحة الشرف"},
    "profile": {"bg1": "#311B92", "bg2": "#00CEC9", "accent": "#FDCB6E", "title": "ملفي"},
}


def _hex(c: str) -> tuple:
    c = c.lstrip("#")
    return tuple(int(c[i : i + 2], 16) for i in (0, 2, 4))


def _gradient(size, c1, c2):
    w, h = size
    base = Image.new("RGB", size, c1)
    top = Image.new("RGB", size, c2)
    mask = Image.new("L", size)
    draw = ImageDraw.Draw(mask)
    for y in range(h):
        draw.line([(0, y), (w, y)], fill=int(255 * y / h))
    return Image.composite(top, base, mask)


def _draw_roulette_icon(draw, cx, cy, r, accent):
    draw.ellipse((cx - r, cy - r, cx + r, cy + r), outline=accent, width=4)
    draw.ellipse((cx - 8, cy - 8, cx + 8, cy + 8), fill=accent)
    for i, (dx, dy) in enumerate([(0, -r + 6), (r - 6, 0), (0, r - 6), (-r + 6, 0)]):
        colors = ["#FD79A8", "#00CEC9", "#FDCB6E", "#74B9FF"]
        draw.polygon(
            [(cx, cy), (cx + dx, cy + dy), (cx + dx // 2, cy + dy // 2)],
            fill=colors[i % 4],
        )


def generate_banner(name: str, theme: dict, out: Path) -> None:
    w, h = 800, 280
    img = _gradient((w, h), _hex(theme["bg1"]), _hex(theme["bg2"]))
    draw = ImageDraw.Draw(img)

    # زخرفة دائرية
    draw.ellipse((520, -40, 780, 200), fill=_hex(theme["accent"]))
    draw.ellipse((600, 80, 760, 240), outline=_hex(theme["accent"]), width=2)

    _draw_roulette_icon(draw, 680, 120, 56, _hex(theme["accent"]))

    try:
        font_title = ImageFont.truetype("arial.ttf", 52)
        font_sub = ImageFont.truetype("arial.ttf", 22)
    except OSError:
        font_title = ImageFont.load_default()
        font_sub = ImageFont.load_default()

    draw.text((40, 70), theme["title"], fill=(255, 255, 255), font=font_title)
    draw.text((44, 150), "Sarab Roulette · Premium UI", fill=_hex(theme["accent"]), font=font_sub)
    draw.rounded_rectangle((40, 200, 220, 238), radius=14, fill=_hex(theme["accent"]))
    draw.text((58, 208), "v2.0", fill=(20, 20, 40), font=font_sub)

    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out, "PNG", optimize=True)


def generate_all() -> None:
    for key, theme in THEMES.items():
        generate_banner(key, theme, BANNERS / f"{key}.png")
    print(f"Generated {len(THEMES)} banners in {BANNERS}")


if __name__ == "__main__":
    generate_all()
