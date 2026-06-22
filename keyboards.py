from telebot import types

from config import BOT_USERNAME, DONATE_URL, SUPPORT_URL


def _back_button(callback: str = "back_main") -> types.InlineKeyboardButton:
    return types.InlineKeyboardButton("🔙 رجوع", callback_data=callback, style="danger")


def main_menu(remind_on: bool = False, has_chats: bool = False) -> types.InlineKeyboardMarkup:
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(
        types.InlineKeyboardButton("انشاء سحب 🐣", callback_data="create_roulette", style="primary"),
        types.InlineKeyboardButton("روليت سريع 🎡", callback_data="quick_roulette", style="primary"),
    )
    kb.add(
        types.InlineKeyboardButton("احصائياتي 📊", callback_data="statistics", style="primary"),
    )
    remind_icon = "✔️" if remind_on else "☑️"
    kb.add(
        types.InlineKeyboardButton("الشروط والأحكام 📝", callback_data="terms", style="success"),
        types.InlineKeyboardButton(f"ذكرني إذا فزت {remind_icon}", callback_data="remind_win", style="success"),
    )
    kb.add(
        types.InlineKeyboardButton("دعم البوت 🌟", url=DONATE_URL, style="success"),
        types.InlineKeyboardButton("الدعم الفني 👨‍💻", url=SUPPORT_URL, style="success"),
    )
    kb.add(
        types.InlineKeyboardButton("انشاء مسابقة 🏆", callback_data="create_competition", style="primary"),
    )
    if has_chats:
        kb.add(
            types.InlineKeyboardButton("سجل المجموعات 🗂", callback_data="manage_chats", style="danger"),
        )
    return kb


def quick_board_markup() -> types.InlineKeyboardMarkup:
    kb = types.InlineKeyboardMarkup(row_width=4)
    limits = [5, 10, 15, 20, 25, 30, 50, 70, 100, 150, 200, 250]
    row = []
    for i, lim in enumerate(limits):
        row.append(types.InlineKeyboardButton(f"🎡 {lim}", callback_data=f"qboard_l_{lim}", style="primary"))
        if len(row) == 4 or i == len(limits) - 1:
            kb.row(*row)
            row = []
    return kb


def quick_roulette_menu() -> types.InlineKeyboardMarkup:
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.add(
        types.InlineKeyboardButton("انشاء روليت 🎡", switch_inline_query="روليت", style="primary"),
    )
    kb.add(
        types.InlineKeyboardButton("الإعدادات ⚙️", callback_data="quick_settings", style="success"),
    )
    kb.add(
        types.InlineKeyboardButton("رجوع ↩️", callback_data="back_main", style="danger"),
    )
    return kb





def quick_settings_menu(hide_participants: bool = False) -> types.InlineKeyboardMarkup:
    kb = types.InlineKeyboardMarkup(row_width=2)
    visibility_text = "اسماء المشاركين : مخفي 🚷" if hide_participants else "اسماء المشاركين : ظاهر 👁️"
    kb.add(
        types.InlineKeyboardButton(visibility_text, callback_data="qset_hidep", style="primary"),
        types.InlineKeyboardButton("كليشة اللعبة 🖌", callback_data="qset_custom_msg", style="primary"),
    )
    kb.add(
        types.InlineKeyboardButton("الرجوع للافتراضي 🔄", callback_data="qset_reset_defaults", style="success"),
    )
    kb.add(
        types.InlineKeyboardButton("رجوع ↩️", callback_data="quick_roulette", style="danger"),
    )
    return kb


def qset_limit_picker(back_callback: str = "quick_settings") -> types.InlineKeyboardMarkup:
    kb = types.InlineKeyboardMarkup(row_width=4)
    for limit in [5, 10, 15, 20, 25, 30, 50, 70]:
        kb.add(
            types.InlineKeyboardButton(f"🔹 {limit}", callback_data=f"qset_limit_{limit}", style="primary")
        )
    kb.add(
        types.InlineKeyboardButton("🔹 100", callback_data="qset_limit_100", style="primary"),
        types.InlineKeyboardButton("🔹 150", callback_data="qset_limit_150", style="primary"),
        types.InlineKeyboardButton("🔹 200", callback_data="qset_limit_200", style="primary"),
        types.InlineKeyboardButton("🔹 250", callback_data="qset_limit_250", style="primary"),
    )
    kb.add(
        types.InlineKeyboardButton("🔙 رجوع", callback_data=back_callback, style="danger"),
    )
    return kb


def quick_group_picker(groups: list) -> types.InlineKeyboardMarkup:
    kb = types.InlineKeyboardMarkup(row_width=1)
    for g in groups:
        kb.add(
            types.InlineKeyboardButton(
                f"💬 {g['title'][:25]}", callback_data=f"quick_group_{g['chat_id']}", style="primary"
            )
        )
    kb.add(
        types.InlineKeyboardButton("🔙 رجوع", callback_data="quick_roulette", style="danger"),
    )
    return kb


def quick_limit_picker(chat_id: int) -> types.InlineKeyboardMarkup:
    kb = types.InlineKeyboardMarkup(row_width=4)
    for limit in [5, 10, 15, 20, 25, 30, 50, 70]:
        kb.add(
            types.InlineKeyboardButton(f"🔹 {limit}", callback_data=f"quick_make_{chat_id}_{limit}", style="primary")
        )
    kb.add(
        types.InlineKeyboardButton("🔹 100", callback_data=f"quick_make_{chat_id}_100", style="primary"),
        types.InlineKeyboardButton("🔹 150", callback_data=f"quick_make_{chat_id}_150", style="primary"),
        types.InlineKeyboardButton("🔹 200", callback_data=f"quick_make_{chat_id}_200", style="primary"),
        types.InlineKeyboardButton("🔹 250", callback_data=f"quick_make_{chat_id}_250", style="primary"),
    )
    kb.add(
        types.InlineKeyboardButton("🔙 رجوع", callback_data="quick_pick_group", style="danger"),
    )
    return kb


def create_roulette_menu() -> types.InlineKeyboardMarkup:
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(
        types.InlineKeyboardButton("انشاء سحب 🐥", callback_data="giveaway_create", style="primary"),
    )
    kb.add(
        types.InlineKeyboardButton("اضافة قناة 📢", callback_data="link_channel_group", style="success"),
        types.InlineKeyboardButton("حذف قناة 🗑", callback_data="delete_channel_group", style="danger"),
    )
    kb.add(
        types.InlineKeyboardButton("دعم البوت 🌟", url=DONATE_URL, style="success"),
        types.InlineKeyboardButton("ذكرني اذا فزت ✅", callback_data="remind_win", style="primary"),
    )
    kb.add(
        types.InlineKeyboardButton("رجوع ↩️", callback_data="back_main", style="danger"),
    )
    return kb


def link_channel_group_menu() -> types.InlineKeyboardMarkup:
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(
        types.InlineKeyboardButton("ربط جروب 👥", callback_data="register_group", style="success"),
        types.InlineKeyboardButton("ربط قناة 📢", callback_data="register_channel", style="primary"),
    )
    kb.add(
        types.InlineKeyboardButton("رجوع ↩️", callback_data="create_roulette", style="danger"),
    )
    return kb


def delete_channel_group_menu(chats: list) -> types.InlineKeyboardMarkup:
    kb = types.InlineKeyboardMarkup(row_width=2)
    for ch in chats:
        title = ch["title"] or str(ch["chat_id"])
        kb.add(
            types.InlineKeyboardButton(f"{title[:20]}", callback_data=f"noop", style="primary"),
            types.InlineKeyboardButton("🗑", callback_data=f"delchat_{ch['chat_id']}", style="danger"),
        )
    kb.add(
        types.InlineKeyboardButton("رجوع ↩️", callback_data="create_roulette", style="danger"),
    )
    return kb


def giveaway_select_chat_menu(chats: list) -> types.InlineKeyboardMarkup:
    kb = types.InlineKeyboardMarkup(row_width=2)
    for chat in chats:
        title = chat["title"] or str(chat["chat_id"])
        kb.add(
            types.InlineKeyboardButton(
                title[:30],
                callback_data=f"giveaway_select_{chat['chat_id']}",
                style="primary",
            )
        )
    kb.add(
        types.InlineKeyboardButton("تسجيل جروب ➕", callback_data="register_group", style="primary"),
        types.InlineKeyboardButton("تسجيل قناة ➕", callback_data="register_channel", style="primary"),
    )
    kb.add(
        types.InlineKeyboardButton("رجوع ↩️", callback_data="create_roulette", style="danger"),
    )
    return kb


def giveaway_settings_menu(raffle_id: str, settings: dict) -> types.InlineKeyboardMarkup:
    kb = types.InlineKeyboardMarkup(row_width=2)

    # --- Toggle buttons (boost_channel, premium_only, anti_spam) ---
    def btn_toggle(label: str, key: str, is_on):
        is_on = bool(is_on)
        if is_on:
            display_text = f"✅ {label} : نعم"
            return types.InlineKeyboardButton(display_text, callback_data=f"giveaway_toggle_{key}_{raffle_id}", style="success")
        else:
            display_text = f"❌ {label} : لا"
            return types.InlineKeyboardButton(display_text, callback_data=f"giveaway_toggle_{key}_{raffle_id}", style="danger")

    # --- Sub-menu buttons (Blue) ---
    kb.add(
        types.InlineKeyboardButton("📢 قناة شرط", callback_data=f"gcond_menu_{raffle_id}", style="primary"),
        types.InlineKeyboardButton("❤️ تصويت متسابق", callback_data=f"gvote_menu_{raffle_id}", style="primary"),
    )
    kb.add(
        types.InlineKeyboardButton("⏰ سحب تلقائي", callback_data=f"gautodraw_menu_{raffle_id}", style="primary"),
    )

    # --- Toggle buttons (Green/Red) ---
    kb.add(
        btn_toggle("تعزيز القناة", "boost_channel", settings.get("boost_channel", 0)),
        btn_toggle("مشتركين المميز", "premium_only", settings.get("premium_only", 0)),
    )
    kb.add(
        btn_toggle("منع الرشق", "anti_spam", settings.get("anti_spam", 0)),
    )
    kb.add(
        types.InlineKeyboardButton("✅ نشر السحب", callback_data=f"giveaway_publish_{raffle_id}", style="success"),
    )
    kb.add(
        types.InlineKeyboardButton("↩ رجوع", callback_data="giveaway_create", style="danger"),
    )
    return kb


def condition_channel_type_menu(raffle_id: str) -> types.InlineKeyboardMarkup:
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(
        types.InlineKeyboardButton("قناة خاصة 🔒", callback_data=f"gcond_private_{raffle_id}", style="primary"),
        types.InlineKeyboardButton("قناة عامة 🌐", callback_data=f"gcond_public_{raffle_id}", style="primary"),
    )
    kb.add(
        types.InlineKeyboardButton("↩ رجوع للخيارات", callback_data=f"gback_settings_{raffle_id}", style="danger"),
    )
    return kb


def condition_channel_back(raffle_id: str) -> types.InlineKeyboardMarkup:
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.add(
        types.InlineKeyboardButton("↩ رجوع للخيارات", callback_data=f"gback_settings_{raffle_id}", style="danger"),
    )
    return kb


def vote_contestant_back(raffle_id: str) -> types.InlineKeyboardMarkup:
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.add(
        types.InlineKeyboardButton("↩ رجوع", callback_data=f"gback_settings_{raffle_id}", style="danger"),
    )
    return kb


def auto_draw_method_menu(raffle_id: str) -> types.InlineKeyboardMarkup:
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(
        types.InlineKeyboardButton("🏆 عدد محدد", callback_data=f"gautodraw_count_{raffle_id}", style="success"),
        types.InlineKeyboardButton("⏰ وقت محدد", callback_data=f"gautodraw_time_{raffle_id}", style="success"),
    )
    kb.add(
        types.InlineKeyboardButton("↩ رجوع للخيارات", callback_data=f"gback_settings_{raffle_id}", style="danger"),
    )
    return kb


def auto_draw_count_back(raffle_id: str) -> types.InlineKeyboardMarkup:
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.add(
        types.InlineKeyboardButton("↩ رجوع للخيارات", callback_data=f"gback_settings_{raffle_id}", style="danger"),
    )
    return kb


def auto_draw_time_picker(raffle_id: str) -> types.InlineKeyboardMarkup:
    kb = types.InlineKeyboardMarkup(row_width=2)
    time_options = [
        ("⏰ بعد 1 دقيقة", 1),
        ("⏰ بعد 5 دقايق", 5),
        ("⏰ بعد 30 دقيقة", 30),
        ("⏰ بعد 1 ساعة", 60),
        ("⏰ بعد 2 ساعات", 120),
        ("⏰ بعد 3 ساعات", 180),
        ("⏰ بعد 4 ساعات", 240),
        ("⏰ بعد 5 ساعات", 300),
        ("⏰ بعد 6 ساعات", 360),
        ("⏰ بعد 12 ساعات", 720),
        ("⏰ بعد 24 ساعة", 1440),
        ("⏰ بعد 48 ساعات", 2880),
        ("⏰ بعد 3 ايام", 4320),
        ("⏰ بعد 1 اسبوع", 10080),
    ]
    for label, minutes in time_options:
        kb.add(
            types.InlineKeyboardButton(label, callback_data=f"gautodraw_tval_{minutes}_{raffle_id}", style="primary"),
        )
    kb.add(
        types.InlineKeyboardButton("⏲ وقت مخصص رقم", callback_data=f"gautodraw_custom_{raffle_id}", style="primary"),
        types.InlineKeyboardButton("📞 زيادة تنقيص", callback_data=f"gautodraw_adjust_{raffle_id}", style="primary"),
    )
    kb.add(
        types.InlineKeyboardButton("↩ رجوع", callback_data=f"gautodraw_menu_{raffle_id}", style="danger"),
    )
    return kb


def regular_limit_picker(chat_id: int) -> types.InlineKeyboardMarkup:
    kb = types.InlineKeyboardMarkup(row_width=4)
    for limit in [5, 10, 15, 20, 25, 30, 50, 70]:
        kb.add(
            types.InlineKeyboardButton(f"🔹 {limit}", callback_data=f"regular_make_{chat_id}_{limit}", style="primary")
        )
    kb.add(
        types.InlineKeyboardButton("🔹 100", callback_data=f"regular_make_{chat_id}_100", style="primary"),
        types.InlineKeyboardButton("🔹 150", callback_data=f"regular_make_{chat_id}_150", style="primary"),
        types.InlineKeyboardButton("🔹 200", callback_data=f"regular_make_{chat_id}_200", style="primary"),
        types.InlineKeyboardButton("🔹 250", callback_data=f"regular_make_{chat_id}_250", style="primary"),
    )
    kb.add(
        types.InlineKeyboardButton("🔙 رجوع", callback_data="create_roulette", style="danger"),
    )
    return kb


def register_back_menu(back_callback: str = "back_create") -> types.InlineKeyboardMarkup:
    kb = types.InlineKeyboardMarkup()
    kb.add(_back_button(back_callback))
    return kb


def back_only(callback: str = "back_main") -> types.InlineKeyboardMarkup:
    kb = types.InlineKeyboardMarkup()
    kb.add(_back_button(callback))
    return kb


def my_raffles_list(raffle_ids: list[str]) -> types.InlineKeyboardMarkup:
    kb = types.InlineKeyboardMarkup(row_width=2)
    for rid in raffle_ids:
        kb.add(types.InlineKeyboardButton(f"🎲 {rid}", callback_data=f"raffle_{rid}", style="primary"))
    kb.add(
        types.InlineKeyboardButton("🆕 إنشاء جديد", callback_data="create_roulette", style="success"),
        types.InlineKeyboardButton("🏅 المتصدرون", callback_data="leaderboard", style="primary"),
    )
    kb.add(_back_button())
    return kb


def raffle_control(
    raffle_id: str,
    hide_participants: int,
    hide_buttons: int,
    old_members_only: int,
) -> types.InlineKeyboardMarkup:
    kb = types.InlineKeyboardMarkup(row_width=1)

    def toggle_icon(val: int) -> str:
        return "ON" if val else "OFF"

    kb.add(
        types.InlineKeyboardButton(
            f"🔄 إعادة نشر [{toggle_icon(1)}]", callback_data=f"republish_{raffle_id}", style="primary"
        ),
        types.InlineKeyboardButton(
            f"👁 إخفاء العدد [{toggle_icon(hide_participants)}]", callback_data=f"toggle_hidep_{raffle_id}", style="primary"
        ),
    )
    kb.add(
        types.InlineKeyboardButton(
            f"🔘 إخفاء الأزرار [{toggle_icon(hide_buttons)}]", callback_data=f"toggle_hideb_{raffle_id}", style="primary"
        ),
        types.InlineKeyboardButton(
            f"🔒 قفل القدامى [{toggle_icon(old_members_only)}]", callback_data=f"toggle_oldm_{raffle_id}", style="primary"
        ),
    )
    kb.add(
        types.InlineKeyboardButton("📥 تصدير المشاركين", callback_data=f"export_{raffle_id}", style="success"),
        types.InlineKeyboardButton("⏹ إيقاف السحب", callback_data=f"stop_{raffle_id}", style="danger"),
    )
    kb.add(
        types.InlineKeyboardButton("📋 نسخ السحب", callback_data=f"duplicate_{raffle_id}", style="success"),
        _back_button("my_raffles"),
    )
    return kb

def giveaway_active_keyboard(raffle_id: str, count: int) -> types.InlineKeyboardMarkup:
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(
        types.InlineKeyboardButton(f"اضغط لـ المشاركة ({count})", callback_data=f"gjoin_{raffle_id}", style="primary")
    )
    kb.add(
        types.InlineKeyboardButton("مشاركة السحب ↗", url=f"https://t.me/share/url?url=https://t.me/{BOT_USERNAME}?start={raffle_id}", style="primary"),
        types.InlineKeyboardButton("إعادة نشر ↻", callback_data=f"grepublish_{raffle_id}", style="primary"),
    )
    kb.add(
        types.InlineKeyboardButton("ذكرني اذا فزت ↗", callback_data="remind_win", style="success"),
        types.InlineKeyboardButton("ايقاف وسحب", callback_data=f"gstop_{raffle_id}", style="danger"),
    )
    return kb


def channel_log_menu(log_channels: list) -> types.InlineKeyboardMarkup:
    kb = types.InlineKeyboardMarkup(row_width=1)
    for ch in log_channels:
        label = f"{ch['code']} · {ch['title'] or 'قناة'}"[:60]
        kb.add(
            types.InlineKeyboardButton(f"📂 {label}", callback_data=f"logch_{ch['chat_id']}", style="primary")
        )
    kb.add(
        types.InlineKeyboardButton("➕ تسجيل قروب", callback_data="register_group", style="success"),
        types.InlineKeyboardButton("➕ تسجيل قناة", callback_data="register_channel", style="success"),
    )
    kb.add(
        types.InlineKeyboardButton("📜 سجل نشاطي", callback_data="my_activity", style="primary"),
        _back_button(),
    )
    return kb


def manage_chats_menu(chats: list, back_callback: str = "quick_settings") -> types.InlineKeyboardMarkup:
    kb = types.InlineKeyboardMarkup(row_width=2)
    for ch in chats:
        label = f"{ch['title'] or ch['type']}"[:20]
        kb.add(
            types.InlineKeyboardButton(f"🎲 {label}", callback_data=f"create_group_{ch['chat_id']}", style="primary"),
            types.InlineKeyboardButton(f"🗑 حذف", callback_data=f"delchat_{ch['chat_id']}", style="danger"),
        )
    kb.add(
        types.InlineKeyboardButton("🔙 رجوع", callback_data=back_callback, style="danger"),
    )
    return kb


def quick_raffle_active(
    raffle_id: str,
    hide_buttons: bool = False,
) -> types.InlineKeyboardMarkup:
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(
        types.InlineKeyboardButton(
            "✅ انضم للسحب", callback_data=f"join_{raffle_id}", style="success"
        )
    )
    if not hide_buttons:
        kb.add(
            types.InlineKeyboardButton(
                "🎯 اختيار الفائز", callback_data=f"pick_{raffle_id}", style="primary"
            )
        )
    return kb


def quick_raffle_completed(raffle_id: str) -> types.InlineKeyboardMarkup:
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(
        types.InlineKeyboardButton(
            "🔄 فائز آخر", callback_data=f"pickagain_{raffle_id}", style="primary"
        ),
        types.InlineKeyboardButton(
            "🔁 العب مجدداً", callback_data=f"replay_{raffle_id}", style="success"
        ),
    )
    return kb


def creator_participant_actions(raffle_id: str, user_id: int) -> types.InlineKeyboardMarkup:
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(
        types.InlineKeyboardButton("👤 الملف الشخصي", url=f"tg://user?id={user_id}", style="primary"),
        types.InlineKeyboardButton(
            "🚫 استبعاد", callback_data=f"exclude_{raffle_id}_{user_id}", style="danger"
        ),
    )
    return kb


def profile_menu(remind_on: bool) -> types.InlineKeyboardMarkup:
    kb = types.InlineKeyboardMarkup(row_width=2)
    status = "مفعل ✅" if remind_on else "معطل ❌"
    kb.add(
        types.InlineKeyboardButton(
            f"🔔 تذكير الفوز {status}", callback_data="remind_win", style="primary"
        ),
        types.InlineKeyboardButton("🏅 لوحة الشرف", callback_data="leaderboard", style="success"),
    )
    kb.add(
        types.InlineKeyboardButton("📊 إحصائياتي", callback_data="statistics", style="primary"),
        types.InlineKeyboardButton("🔙 رجوع", callback_data="back_main", style="danger"),
    )
    return kb


def competition_menu() -> types.InlineKeyboardMarkup:
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(
        types.InlineKeyboardButton("انشاء مسابقة 🏆", callback_data="comp_start", style="success"),
    )
    kb.add(
        types.InlineKeyboardButton("➕ تسجيل قناة", callback_data="comp_reg_channel", style="primary"),
        types.InlineKeyboardButton("➕ تسجيل قروب", callback_data="comp_reg_group", style="primary"),
    )
    kb.add(
        types.InlineKeyboardButton("المسابقات الحديثة 🆕", callback_data="comp_recent", style="primary"),
    )
    kb.add(
        types.InlineKeyboardButton("↩️ رجوع", callback_data="back_main", style="danger"),
    )
    return kb


def comp_chat_picker(chats: list) -> types.InlineKeyboardMarkup:
    kb = types.InlineKeyboardMarkup(row_width=1)
    for chat in chats:
        title = chat["title"] or str(chat["chat_id"])
        kb.add(
            types.InlineKeyboardButton(f"💬 {title[:30]}", callback_data=f"comp_chat_{chat['chat_id']}", style="primary"),
        )
    kb.add(
        types.InlineKeyboardButton("➕ تسجيل قروب", callback_data="comp_reg_group", style="success"),
        types.InlineKeyboardButton("➕ تسجيل قناة", callback_data="comp_reg_channel", style="success"),
    )
    kb.add(
        types.InlineKeyboardButton("🔙 رجوع", callback_data="create_competition", style="danger"),
    )
    return kb


def comp_end_type_picker() -> types.InlineKeyboardMarkup:
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(
        types.InlineKeyboardButton("⏰ وقت محدد", callback_data="comp_end_time", style="primary"),
        types.InlineKeyboardButton("📊 عدد أصوات", callback_data="comp_end_votes", style="success"),
    )
    kb.add(
        types.InlineKeyboardButton("🔙 رجوع", callback_data="comp_start", style="danger"),
    )
    return kb


def comp_duration_picker() -> types.InlineKeyboardMarkup:
    kb = types.InlineKeyboardMarkup(row_width=3)
    durations = [
        ("1 دقيقة", 60), ("5 دقائق", 300), ("15 دقيقة", 900),
        ("30 دقيقة", 1800), ("1 ساعة", 3600), ("2 ساعات", 7200),
        ("6 ساعات", 21600), ("12 ساعة", 43200), ("24 ساعة", 86400),
        ("3 أيام", 259200), ("7 أيام", 604800),
    ]
    for i in range(0, len(durations), 3):
        kb.row(*[
            types.InlineKeyboardButton(f"⏱ {label}", callback_data=f"comp_dur_{secs}", style="primary")
            for label, secs in durations[i:i+3]
        ])
    kb.add(
        types.InlineKeyboardButton("🔙 رجوع", callback_data="comp_show_end_types", style="danger"),
    )
    return kb


def comp_toggle_panel(comp_id: str, win_notif: bool, results_ann: bool, approval: bool, premium: bool) -> types.InlineKeyboardMarkup:
    kb = types.InlineKeyboardMarkup(row_width=2)
    def btn(label: str, key: str, on: bool) -> types.InlineKeyboardButton:
        icon = "✅" if on else "❌"
        stl = "success" if on else "danger"
        return types.InlineKeyboardButton(f"{icon} {label}", callback_data=f"comp_toggle_{key}_{comp_id}", style=stl)
    kb.add(
        btn("تنبيه الفوز", "notif", win_notif),
        btn("اعلان النتائج", "results", results_ann),
    )
    kb.add(
        btn("موافقة المشاركات", "approve", approval),
        btn("تصويت بريميوم", "premium", premium),
    )
    kb.add(
        types.InlineKeyboardButton("🚀 نشر المسابقة", callback_data=f"comp_publish_{comp_id}", style="success"),
    )
    kb.add(
        types.InlineKeyboardButton("🔙 رجوع", callback_data="comp_start", style="danger"),
    )
    return kb


def comp_settings_panel(comp_id: str, win_notif, results_ann, approval, premium) -> types.InlineKeyboardMarkup:
    kb = types.InlineKeyboardMarkup(row_width=2)
    def btn(label: str, key: str, on) -> types.InlineKeyboardButton:
        icon = "✅" if on else "❌"
        stl = "success" if on else "danger"
        return types.InlineKeyboardButton(f"{icon} {label}", callback_data=f"comp_toggle_{key}_{comp_id}", style=stl)
    kb.add(
        btn("تنبيه الفوز", "notif", win_notif),
        btn("اعلان النتائج", "results", results_ann),
    )
    kb.add(
        btn("موافقة المشاركات", "approve", approval),
        btn("تصويت بريميوم", "premium", premium),
    )
    kb.add(
        types.InlineKeyboardButton("🔙 رجوع", callback_data=f"comp_manage_{comp_id}", style="danger"),
    )
    return kb


def help_menu() -> types.InlineKeyboardMarkup:
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(
        types.InlineKeyboardButton("✨ روليت سريع 🎡", callback_data="quick_roulette", style="primary"),
        types.InlineKeyboardButton("✨ انشاء سحب 🐥", callback_data="create_roulette", style="primary"),
    )
    kb.add(
        types.InlineKeyboardButton("✨ شارك البوت 📤", callback_data="share_bot", style="success"),
    )
    kb.add(_back_button("back_main"))
    return kb


def share_menu() -> types.InlineKeyboardMarkup:
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.add(
        types.InlineKeyboardButton(
            "📤 شارك البوت", switch_inline_query="", style="success"
        ),
    )
    kb.add(_back_button("back_main"))
    return kb


# ─── إدارة المسابقات الحديثة ────────────────────────────────────────────────

def comp_recent_list(competitions: list) -> types.InlineKeyboardMarkup:
    kb = types.InlineKeyboardMarkup(row_width=1)
    for comp in competitions:
        title = comp["title"][:25]
        status = "🟢" if comp["status"] == "active" else "🔴"
        kb.add(
            types.InlineKeyboardButton(
                f"{status} {title}",
                callback_data=f"comp_manage_{comp['comp_id']}",
                style="primary",
            ),
        )
    kb.add(
        types.InlineKeyboardButton("🔙 رجوع", callback_data="create_competition", style="danger"),
    )
    return kb


def comp_manage_dashboard(comp_id: str) -> types.InlineKeyboardMarkup:
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.add(
        types.InlineKeyboardButton("📊 تغيير عدد المقاعد", callback_data=f"comp_chmax_{comp_id}", style="primary"),
    )
    kb.add(
        types.InlineKeyboardButton("⏸️ إيقاف المسابقة 🎟️", callback_data=f"comp_pause_{comp_id}", style="danger"),
    )
    kb.add(
        types.InlineKeyboardButton("🔄 تغيير إعدادات المسابقة", callback_data=f"comp_cset_{comp_id}", style="primary"),
    )
    kb.add(
        types.InlineKeyboardButton("🗑️ إزالة متسابق", callback_data=f"comp_rmpart_{comp_id}", style="danger"),
    )
    kb.add(
        types.InlineKeyboardButton("🗑️ حذف المسابقة بالكامل", callback_data=f"comp_delete_{comp_id}", style="danger"),
    )
    kb.add(
        types.InlineKeyboardButton("🔙 رجوع", callback_data="comp_recent", style="danger"),
    )
    return kb


# ─── أزرار المسابقات (نظام الموافقة وبطاقات التصويت) ───────────────────────

def comp_channel_join_button(contest_id: str, is_approved: bool = False, full: bool = False) -> types.InlineKeyboardMarkup:
    kb = types.InlineKeyboardMarkup(row_width=1)
    if full:
        kb.add(
            types.InlineKeyboardButton("❌ المقاعد ممتلئة", callback_data="noop", style="danger"),
        )
    elif is_approved:
        kb.add(
            types.InlineKeyboardButton("🚪 مغادرة المسابقة", callback_data=f"comp_leave_{contest_id}", style="danger"),
        )
    else:
        kb.add(
            types.InlineKeyboardButton("↗️ المشاركة في المسابقة ✅", callback_data=f"comp_join_{contest_id}", style="success"),
        )
    return kb


def comp_confirm_join(contest_id: str) -> types.InlineKeyboardMarkup:
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(
        types.InlineKeyboardButton("✅ قبول", callback_data=f"comp_confirm_yes_{contest_id}", style="success"),
        types.InlineKeyboardButton("❌ رفض", callback_data=f"comp_confirm_no_{contest_id}", style="danger"),
    )
    return kb


def comp_pending_notify(admin_id: int) -> types.InlineKeyboardMarkup:
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.add(
        types.InlineKeyboardButton("📞 الدعم الفني", url="https://t.me/ziad_sh123", style="primary"),
    )
    return kb


def comp_admin_approve_reject(contest_id: str, user_id: int) -> types.InlineKeyboardMarkup:
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(
        types.InlineKeyboardButton("موافقة ✅", callback_data=f"comp_admapp_{contest_id}_{user_id}", style="success"),
        types.InlineKeyboardButton("رفض ❌", callback_data=f"comp_admrej_{contest_id}_{user_id}", style="danger"),
    )
    return kb


def comp_voting_card(contest_id: str, contestant_id: int, votes: int, premium_only: bool = False) -> types.InlineKeyboardMarkup:
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(
        types.InlineKeyboardButton("👤 رؤية حساب المتسابق", url=f"tg://user?id={contestant_id}", style="primary"),
        types.InlineKeyboardButton(f"♡ {votes}", callback_data=f"comp_votecard_{contest_id}_{contestant_id}", style="success"),
    )
    return kb

