"""هوية بصرية موحّدة — HTML + عناصر تزيينية."""

BRAND = "روليت غزاوي ✨"
TAGLINE = "Sarab Roulette"

# ألوان الهوية (للتوثيق والبانرات)
COLORS = {
    "purple": "#6C5CE7",
    "violet": "#A29BFE",
    "gold": "#FDCB6E",
    "mint": "#00CEC9",
    "rose": "#FD79A8",
    "dark": "#2D3436",
    "night": "#0F0F23",
}


def divider(char: str = "─", width: int = 22) -> str:
    return char * width


def blockquote(text: str) -> str:
    return f"<blockquote>{text}</blockquote>"


def badge(label: str, value: str) -> str:
    return f"<b>{label}</b> <code>{value}</code>"


def section(title: str, body: str) -> str:
    return f"\n{'═' * 22}\n<b>✦ {title}</b>\n{'─' * 22}\n{body}"


def progress_bar(current: int, total: int, width: int = 12) -> str:
    if total <= 0:
        return "▱" * width
    filled = min(width, max(1, round(width * current / total))) if current > 0 else 0
    pct = int(100 * current / total)
    bar = "▰" * filled + "▱" * (width - filled)
    return f"{bar} <b>{pct}%</b> ({current}/{total})"


def level_badge(xp: int) -> str:
    level = max(1, xp // 100 + 1)
    progress = xp % 100
    stars = "⭐" * min(level, 5)
    return f"المستوى {level} {stars} · XP {progress}/100"


def feature_list(items: list[str]) -> str:
    return "\n".join(f"▸ {item}" for item in items)


def spin_frame(step: int) -> str:
    frames = ["🎰", "🎲", "🎯", "🎪", "🎡", "🎰"]
    return frames[step % len(frames)]


def winner_crown(name: str) -> str:
    return (
        f"{'✦' * 22}\n"
        f"👑 <b>الفائز</b>\n"
        f"<tg-spoiler>{name}</tg-spoiler>\n"
        f"{'✦' * 22}"
    )
