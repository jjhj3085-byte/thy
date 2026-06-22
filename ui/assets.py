"""مسارات الأصول — SVG + بانرات PNG."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
ICONS = ASSETS / "icons"
BANNERS = ASSETS / "banners"

PAGE_BANNERS = {
    "main": BANNERS / "main.png",
    "quick": BANNERS / "quick.png",
    "create": BANNERS / "create.png",
    "my_raffles": BANNERS / "my_raffles.png",
    "channel_log": BANNERS / "channel_log.png",
    "statistics": BANNERS / "statistics.png",
    "privacy": BANNERS / "privacy.png",
    "terms": BANNERS / "terms.png",
    "competition": BANNERS / "competition.png",
    "leaderboard": BANNERS / "leaderboard.png",
    "profile": BANNERS / "profile.png",
}

PAGE_ICONS = {
    "main": ICONS / "roulette.svg",
    "quick": ICONS / "roulette.svg",
    "create": ICONS / "spark.svg",
    "my_raffles": ICONS / "trophy.svg",
    "channel_log": ICONS / "stats.svg",
    "statistics": ICONS / "stats.svg",
    "privacy": ICONS / "shield.svg",
    "terms": ICONS / "shield.svg",
    "competition": ICONS / "trophy.svg",
    "leaderboard": ICONS / "trophy.svg",
    "profile": ICONS / "spark.svg",
}


def banner_path(page: str) -> Path:
    return PAGE_BANNERS.get(page, PAGE_BANNERS["main"])


def ensure_banners() -> None:
    BANNERS.mkdir(parents=True, exist_ok=True)
    missing = [p for p in PAGE_BANNERS.values() if not p.exists()]
    if missing:
        from tools.generate_banners import generate_all

        generate_all()
