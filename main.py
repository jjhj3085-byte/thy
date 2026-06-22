"""
روليت غزاوي v2 — واجهة Premium + مميزات موسّعة
"""

import io
import logging
import re
import threading
import time
from datetime import datetime, timedelta

import telebot
from telebot import types

import database as db
import keyboards as kb
from config import BOT_TOKEN, BOT_USERNAME, QUICK_RAFFLE_LIMITS, PREMIUM_IDS, GLOBAL_FEED_CHAT_ID
from ui import navigator as nav
from ui import pages
from ui import theme as t

_settings_origin: dict[int, str] = {}
_reg_from_comp: set[int] = set()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML", use_class_middlewares=True)
db.init_db()

import admin
admin.register_handlers(bot)

SPIN_STEPS = 6
SPIN_DELAY = 0.35

from telebot.handler_backends import BaseMiddleware, CancelUpdate

class BanMiddleware(BaseMiddleware):
    def __init__(self):
        self.update_types = ['message', 'callback_query', 'inline_query']
        
    def pre_process(self, message, data):
        uid = message.from_user.id
        if db.is_user_banned(uid):
            # Ignore channel posts and admin log chat to prevent spamming the channel
            if getattr(message, 'chat', None) and str(message.chat.id) == config.ADMIN_LOG_CHAT_ID:
                return
                
            if hasattr(message, 'data'): # It's a callback query
                try:
                    bot.answer_callback_query(message.id, "⛔️ أنت محظور من استخدام البوت.", show_alert=True)
                except: pass
            elif hasattr(message, 'text'): # It's a message
                if message.chat.type == "private":
                    try:
                        bot.send_message(message.chat.id, "⛔️ <b>أنت محظور نهائياً من استخدام البوت.</b>\n\nلا يمكنك التفاعل مع البوت أو الاشتراك في أي سحب.", parse_mode="HTML")
                    except: pass
            
            return CancelUpdate()
            
    def post_process(self, message, data, exception):
        pass

bot.setup_middleware(BanMiddleware())


# ─── مساعدات ──────────────────────────────────────────────────────────────────


def ensure_user(message_or_call) -> None:
    user = message_or_call.from_user
    db.upsert_user(user.id, user.username, user.first_name)

def check_banned(user_id: int) -> bool:
    """Returns True if user is banned."""
    return db.is_user_banned(user_id)


def show_page(call_or_chat, page: str, caption: str, markup=None, *, is_call=True):
    if is_call:
        nav.edit_page(
            bot,
            call_or_chat.message.chat.id,
            call_or_chat.message.message_id,
            page,
            caption,
            markup,
        )
    else:
        nav.send_page(bot, call_or_chat, page, caption, markup)


def safe_edit_inline(inline_message_id: str, text: str, reply_markup=None) -> None:
    try:
        bot.edit_message_text(
            text,
            inline_message_id=inline_message_id,
            reply_markup=reply_markup,
            parse_mode="HTML",
        )
    except telebot.apihelper.ApiTelegramException as exc:
        if "message is not modified" not in str(exc).lower():
            logger.warning("edit_inline: %s", exc)


def safe_edit_message(chat_id, message_id, text, reply_markup=None) -> None:
    try:
        bot.edit_message_text(
            text, chat_id, message_id, reply_markup=reply_markup, parse_mode="HTML"
        )
    except telebot.apihelper.ApiTelegramException as exc:
        if "message is not modified" not in str(exc).lower():
            logger.warning("edit_message: %s", exc)


def safe_send(chat_id: int, text: str, reply_markup=None) -> None:
    try:
        bot.send_message(chat_id, text, reply_markup=reply_markup, parse_mode="HTML")
    except telebot.apihelper.ApiTelegramException as exc:
        logger.warning("send_message %s: %s", chat_id, exc)


def display_name(user) -> str:
    return user.first_name or user.username or str(user.id)


def participant_name(row) -> str:
    return row["first_name"] or row["username"] or str(row["user_id"])


def is_admin(chat_id: int, user_id: int) -> bool:
    try:
        member = bot.get_chat_member(chat_id, user_id)
        return member.status in ("creator", "administrator")
    except telebot.apihelper.ApiTelegramException:
        return False


def can_pick_winner(raffle, user_id: int) -> bool:
    if raffle["creator_id"] == user_id:
        return True
    chat_id = raffle["chat_id"]
    return bool(chat_id and is_admin(chat_id, user_id))


def post_log(creator_id: int, event: str, detail: str) -> None:
    db.log_activity(event, detail, user_id=creator_id)
    for ch in db.get_log_channels(creator_id):
        safe_send(
            ch["chat_id"],
            pages.format_log_event(event, detail),
        )


def update_raffle_message_ui(raffle_id: str) -> None:
    raffle = db.get_raffle(raffle_id)
    if not raffle or raffle["status"] != "active":
        return
    participants = db.get_participants(raffle_id)
    text = pages.format_quick_raffle_message(
        len(participants),
        raffle["limit_participants"],
        participants,
        hide_participants=bool(raffle["hide_participants"]),
        custom_message=db.get_custom_message(raffle["creator_id"])
    )
    markup = kb.quick_raffle_active(raffle_id, bool(raffle["hide_buttons"]))
    if raffle["inline_message_id"]:
        safe_edit_inline(raffle["inline_message_id"], text, markup)
    elif raffle["chat_id"] and raffle["message_id"]:
        safe_edit_message(raffle["chat_id"], raffle["message_id"], text, markup)


def _apply_winner_ui(raffle, winner_name: str, raffle_id: str) -> None:
    text = pages.format_winner_message(winner_name, raffle_id)
    markup = kb.quick_raffle_completed(raffle_id)
    if raffle["inline_message_id"]:
        safe_edit_inline(raffle["inline_message_id"], text, markup)
    elif raffle["chat_id"] and raffle["message_id"]:
        safe_edit_message(raffle["chat_id"], raffle["message_id"], text, markup)


def _run_spin_animation(raffle_id: str, winner, on_done) -> None:
    raffle = db.get_raffle(raffle_id)
    if not raffle:
        return
    count = db.count_participants(raffle_id)

    def spin():
        for step in range(SPIN_STEPS):
            spin_text = pages.format_spin_message(step, count)
            if raffle["inline_message_id"]:
                safe_edit_inline(raffle["inline_message_id"], spin_text)
            elif raffle["chat_id"] and raffle["message_id"]:
                safe_edit_message(raffle["chat_id"], raffle["message_id"], spin_text)
            time.sleep(SPIN_DELAY)
        on_done()

    threading.Thread(target=spin, daemon=True).start()


def finish_raffle_with_winner(raffle_id: str) -> None:
    raffle = db.get_raffle(raffle_id)
    if not raffle:
        return
    winner = db.pick_random_winner(raffle_id)
    if not winner:
        return
    name = participant_name(winner)

    def complete():
        db.set_raffle_status(raffle_id, "completed")
        db.record_winner(raffle_id, winner["user_id"], name)
        r = db.get_raffle(raffle_id)
        _apply_winner_ui(r, name, raffle_id)
        post_log(
            raffle["creator_id"],
            "فوز",
            f"الفائز: {name} · السحب: {raffle_id}",
        )
        if db.get_remind_on_win(winner["user_id"]):
            safe_send(
                winner["user_id"],
                pages.format_winner_message(name, raffle_id),
            )

    _run_spin_animation(raffle_id, winner, complete)


# ─── /start & أوامر ───────────────────────────────────────────────────────────


@bot.message_handler(commands=["start"])
def cmd_start(message: types.Message) -> None:
    if message.chat.type != "private":
        return
        
    is_new = db.get_user_info(message.from_user.id) is None
    ensure_user(message)
    
    if db.is_user_banned(message.from_user.id):
        bot.reply_to(message, "⛔️ أنت محظور من استخدام البوت.")
        return
        
    if is_new:
        user_tag = f"@{message.from_user.username}" if message.from_user.username else "لا يوجد"
        log_msg = (
            "➖ تم دخول شخص جديد الى البوت 👤•\n\n"
            f"➖ إسم الشخص: {message.from_user.first_name} 📝.•\n\n"
            f"➖ إلمعرف : {message.from_user.id} 🆔️•\n\n"
            f"➖ معرف حسابه : {user_tag} 📮•\n\n"
            "➖➖➖➖➖➖"
        )
        admin.admin_log(bot, log_msg)
        
    db.clear_user_state(message.from_user.id)
    
    args = message.text.split()
    if len(args) > 1:
        raffle_id = args[1]
        raffle = db.get_raffle(raffle_id)
        if raffle and raffle["status"] == "active":
            user = message.from_user
            if db.add_participant(raffle_id, user.id, user.username, user.first_name):
                name = display_name(user)
                safe_send(
                    raffle["creator_id"],
                    pages.format_new_participant_dm(name, user.id, raffle_id),
                    kb.creator_participant_actions(raffle_id, user.id),
                )
                bot.reply_to(message, f"🎰 تم انضمامك للسحب <code>{raffle_id}</code> بنجاح ✓", parse_mode="HTML")
                update_raffle_message_ui(raffle_id)
            else:
                bot.reply_to(message, "⚠ أنت مسجل بالفعل في هذا السحب.")
        else:
            bot.reply_to(message, "❌ السحب غير موجود أو منتهي.")
        return

    stats = db.get_user_stats(message.from_user.id)
    remind = db.get_remind_on_win(message.from_user.id)
    chats = db.get_registered_chats(message.from_user.id)
    nav.send_page(
        bot,
        message.chat.id,
        "main",
        pages.welcome(stats, message.from_user.full_name, message.from_user.id),
        kb.main_menu(remind, bool(chats)),
    )


@bot.message_handler(commands=["groupid"])
def cmd_groupid(message: types.Message) -> None:
    if message.chat.type in ("group", "supergroup"):
        bot.reply_to(
            message,
            f"<b>◈ آيدي القروب</b>\n<code>{message.chat.id}</code>",
            parse_mode="HTML",
        )


@bot.message_handler(commands=["quick"])
def cmd_quick(message: types.Message) -> None:
    if message.chat.type not in ("group", "supergroup"):
        bot.reply_to(message, "⚠ استخدم هذا الأمر في المجموعة.", parse_mode="HTML")
        return
    args = message.text.split()
    limit = 10
    if len(args) > 1:
        try:
            limit = max(1, min(250, int(args[1])))
        except ValueError:
            pass
    ensure_user(message)
    raffle_id = db.create_raffle(
        creator_id=message.from_user.id,
        limit_participants=limit,
        raffle_type="quick",
        chat_id=message.chat.id,
    )
    db.add_participant(raffle_id, message.from_user.id, message.from_user.username, message.from_user.first_name)
    msg = bot.send_message(
        message.chat.id,
        pages.format_quick_raffle_message(1, limit, db.get_participants(raffle_id), custom_message=db.get_custom_message(user.id)),
        reply_markup=kb.quick_raffle_active(raffle_id),
        parse_mode="HTML",
    )
    db.update_raffle_message(raffle_id, chat_id=message.chat.id, message_id=msg.message_id)


@bot.message_handler(commands=["qboard"])
def cmd_qboard(message: types.Message) -> None:
    if message.chat.type not in ("group", "supergroup"):
        bot.reply_to(message, "⚠ استخدم هذا الأمر في المجموعة.", parse_mode="HTML")
        return
    ensure_user(message)
    bot.send_message(
        message.chat.id,
        pages.quick_board_text(),
        reply_markup=kb.quick_board_markup(),
        parse_mode="HTML",
    )


@bot.message_handler(commands=["profile", "stats"])
def cmd_profile(message: types.Message) -> None:
    if message.chat.type != "private":
        return
    ensure_user(message)
    stats = db.get_user_stats(message.from_user.id)
    remind = db.get_remind_on_win(message.from_user.id)
    nav.send_page(
        bot,
        message.chat.id,
        "profile",
        pages.profile(stats, remind),
        kb.profile_menu(remind),
    )


@bot.message_handler(commands=["help"])
def cmd_help(message: types.Message) -> None:
    if message.chat.type != "private":
        return
    ensure_user(message)
    nav.send_page(
        bot,
        message.chat.id,
        "help",
        pages.help_page(),
        kb.help_menu(),
    )


@bot.message_handler(commands=["share"])
def cmd_share(message: types.Message) -> None:
    if message.chat.type != "private":
        return
    ensure_user(message)
    nav.send_page(
        bot,
        message.chat.id,
        "share",
        pages.share_bot_page(BOT_USERNAME),
        kb.share_menu(),
    )


# ─── التنقل ───────────────────────────────────────────────────────────────────


@bot.callback_query_handler(func=lambda c: c.data == "noop")
def cb_noop(call: types.CallbackQuery) -> None:
    bot.answer_callback_query(call.id)


@bot.callback_query_handler(func=lambda c: c.data == "back_main")
def cb_back_main(call: types.CallbackQuery) -> None:
    bot.answer_callback_query(call.id)
    ensure_user(call)
    db.clear_user_state(call.from_user.id)
    user_id = call.from_user.id
    remind = db.get_remind_on_win(user_id)
    chats = db.get_registered_chats(user_id)
    show_page(call, "main", pages.welcome(db.get_user_stats(user_id), call.from_user.full_name, user_id), kb.main_menu(remind, bool(chats)))


@bot.callback_query_handler(func=lambda c: c.data == "back_create")
def cb_back_create(call: types.CallbackQuery) -> None:
    bot.answer_callback_query(call.id)
    db.clear_user_state(call.from_user.id)
    chats = db.get_registered_chats(call.from_user.id)
    if chats:
        show_page(
            call,
            "create",
            pages.create_roulette(len(chats)),
            kb.roulette_group_picker(chats),
        )
    else:
        show_page(
            call,
            "create",
            pages.create_roulette(0),
            kb.create_roulette_menu(),
        )


@bot.callback_query_handler(func=lambda c: c.data == "my_raffles")
def cb_my_raffles(call: types.CallbackQuery) -> None:
    bot.answer_callback_query(call.id)
    raffles = db.get_user_active_raffles(call.from_user.id)
    show_page(
        call,
        "my_raffles",
        pages.my_raffles_header(len(raffles)),
        kb.my_raffles_list([r["raffle_id"] for r in raffles]),
    )


@bot.inline_handler(func=lambda query: True)
def inline_quick_limits(query: types.InlineQuery) -> None:
    try:
        if check_banned(query.from_user.id):
            return
        results = []
        for limit in QUICK_RAFFLE_LIMITS:
            placeholder = f"P_{limit}_{query.from_user.id}"
            results.append(
                types.InlineQueryResultArticle(
                    id=f"q{limit}",
                    title=f"🎰 روليت {limit}",
                    description=f"انضمام تلقائي · سحب عند {limit}",
                    input_message_content=types.InputTextMessageContent(
                        message_text=pages.format_quick_raffle_message(0, limit, [], custom_message=db.get_custom_message(query.from_user.id)),
                        parse_mode="HTML",
                    ),
                    reply_markup=kb.quick_raffle_active(placeholder),
                )
            )
        bot.answer_inline_query(query.id, results, cache_time=1)
    except Exception as exc:
        logger.error("inline error: %s", exc)


@bot.chosen_inline_handler(func=lambda c: c.result_id.startswith("q") and c.result_id[1:].isdigit())
def chosen_inline_quick(chosen: types.ChosenInlineResult) -> None:
    try:
        limit = int(chosen.result_id[1:])
        creator_id = chosen.from_user.id
        s = db.get_quick_settings(creator_id)
        raffle_id = db.create_raffle(
            creator_id=creator_id,
            limit_participants=limit,
            raffle_type="quick",
            hide_participants=s["hide_participants"],
            hide_buttons=s["hide_buttons"],
            old_members_only=s["old_members_only"],
        )
        db.add_participant(raffle_id, creator_id, chosen.from_user.username, chosen.from_user.first_name)
        count = db.count_participants(raffle_id)
        participants = db.get_participants(raffle_id)
        if chosen.inline_message_id:
            db.update_raffle_message(raffle_id, inline_message_id=chosen.inline_message_id)
            safe_edit_inline(
                chosen.inline_message_id,
                pages.format_quick_raffle_message(count, limit, participants, hide_participants=s["hide_participants"], custom_message=db.get_custom_message(user.id)),
                kb.quick_raffle_active(raffle_id, hide_buttons=s["hide_buttons"]),
            )
    except Exception as exc:
        logger.error("chosen_inline error: %s", exc, exc_info=True)
        try:
            bot.send_message(chosen.from_user.id, f"⚠ choseinline: {exc}", parse_mode="HTML")
        except Exception:
            pass


@bot.callback_query_handler(func=lambda c: c.data == "quick_roulette")
def cb_quick_roulette(call: types.CallbackQuery) -> None:
    bot.answer_callback_query(call.id)
    show_page(
        call,
        "quick",
        pages.quick_roulette(),
        kb.quick_roulette_menu(),
    )


@bot.callback_query_handler(func=lambda c: c.data and c.data.startswith("qmake_"))
def cb_qmake(call: types.CallbackQuery) -> None:
    bot.answer_callback_query(call.id)
    limit = int(call.data.split("_", 1)[1])
    user = call.from_user
    chat_type = call.message.chat.type
    if chat_type in ("group", "supergroup"):
        raffle_id = db.create_raffle(
            creator_id=user.id,
            limit_participants=limit,
            raffle_type="quick",
            chat_id=call.message.chat.id,
        )
        db.add_participant(raffle_id, user.id, user.username, user.first_name)
        msg = bot.send_message(
            call.message.chat.id,
            pages.format_quick_raffle_message(1, limit, db.get_participants(raffle_id), custom_message=db.get_custom_message(user.id)),
            reply_markup=kb.quick_raffle_active(raffle_id),
            parse_mode="HTML",
        )
        db.update_raffle_message(raffle_id, chat_id=call.message.chat.id, message_id=msg.message_id)
    else:
        text = (
            f"<b>🎯 لإنشاء روليت سريع:</b>\n{t.divider('▬', 18)}\n\n"
            f"استخدم الأمر <code>/quick {limit}</code> في المجموعة\n"
            f"أو اضغط (📤 نشر في المجموعة) من القائمة أعلاه\n\n"
            f"<i>⚡ سيتم إنشاء الروليت مع انضمام تلقائي</i>"
        )
        bot.send_message(call.message.chat.id, text, parse_mode="HTML")


@bot.callback_query_handler(func=lambda c: c.data == "quick_publish")
def cb_quick_publish(call: types.CallbackQuery) -> None:
    bot.answer_callback_query(call.id)
    user = call.from_user
    chats = db.get_registered_chats(user.id)
    if not chats:
        bot.send_message(
            call.message.chat.id,
            f"<b>⚠ لا توجد مجموعات مسجلة</b>\n{t.divider('▬', 18)}\n\n"
            f"سجل مجموعة أولاً من القائمة الرئيسية ← <b>تسجيل قروب</b>",
            parse_mode="HTML",
        )
        return
    text = f"<b>📤 اختر المجموعة:</b>\n{i}سيتم إرسال لوحة الأعداد"
    markup = types.InlineKeyboardMarkup(row_width=1)
    for c in chats:
        markup.add(types.InlineKeyboardButton(
            f"🏠 {c.get('title', c.get('chat_id', ''))}",
            callback_data=f"qboard_pub_{c['chat_id']}"
        ))
    markup.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="quick_roulette", style="danger"))
    bot.send_message(call.message.chat.id, text, reply_markup=markup, parse_mode="HTML")


@bot.callback_query_handler(func=lambda c: c.data and c.data.startswith("qboard_pub_"))
def cb_qboard_pub(call: types.CallbackQuery) -> None:
    bot.answer_callback_query(call.id)
    try:
        chat_id = int(call.data.split("_", 2)[2])
    except (ValueError, IndexError):
        return
    try:
        chat = bot.get_chat(chat_id)
        title = chat.title or str(chat_id)
    except Exception:
        title = str(chat_id)
    bot.send_message(
        chat_id,
        pages.quick_board_text(),
        reply_markup=kb.quick_board_markup(),
        parse_mode="HTML",
    )
    bot.send_message(
        call.message.chat.id,
        f"<b>✅ تم النشر في</b> {title}",
        parse_mode="HTML",
    )


@bot.callback_query_handler(func=lambda c: c.data and c.data.startswith("qboard_l_"))
def cb_qboard_limit(call: types.CallbackQuery) -> None:
    bot.answer_callback_query(call.id)
    try:
        limit = int(call.data.split("_", 2)[2])
    except (ValueError, IndexError):
        return
    user = call.from_user
    if call.message.chat.type not in ("group", "supergroup"):
        bot.send_message(call.message.chat.id, "⚠ استخدم هذا الزر في المجموعة.", parse_mode="HTML")
        return
    raffle_id = db.create_raffle(
        creator_id=user.id,
        limit_participants=limit,
        raffle_type="quick",
        chat_id=call.message.chat.id,
    )
    db.add_participant(raffle_id, user.id, user.username, user.first_name)
    msg = bot.send_message(
        call.message.chat.id,
        pages.format_quick_raffle_message(1, limit, db.get_participants(raffle_id), custom_message=db.get_custom_message(user.id)),
        reply_markup=kb.quick_raffle_active(raffle_id),
        parse_mode="HTML",
    )
    db.update_raffle_message(raffle_id, chat_id=call.message.chat.id, message_id=msg.message_id)


@bot.callback_query_handler(func=lambda c: c.data == "quick_settings")
def cb_quick_settings(call: types.CallbackQuery) -> None:
    bot.answer_callback_query(call.id)
    s = db.get_quick_settings(call.from_user.id)
    show_page(
        call,
        "quick",
        pages.quick_settings_page(s["hide_participants"], s["custom_message"]),
        kb.quick_settings_menu(s["hide_participants"]),
    )


@bot.callback_query_handler(func=lambda c: c.data == "qset_hidep")
def cb_qset_toggle_hide(call: types.CallbackQuery) -> None:
    bot.answer_callback_query(call.id)
    s = db.get_quick_settings(call.from_user.id)
    new_val = 0 if s["hide_participants"] else 1
    db.set_quick_setting(call.from_user.id, "hide_participants", new_val)
    s = db.get_quick_settings(call.from_user.id)
    show_page(
        call,
        "quick",
        pages.quick_settings_page(s["hide_participants"], s["custom_message"]),
        kb.quick_settings_menu(s["hide_participants"]),
    )


@bot.callback_query_handler(func=lambda c: c.data == "qset_custom_msg")
def cb_qset_custom_msg(call: types.CallbackQuery) -> None:
    bot.answer_callback_query(call.id)
    current_msg = db.get_custom_message(call.from_user.id)
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("رجوع ↩️", callback_data="quick_settings", style="danger"))
    show_page(
        call,
        "quick",
        pages.custom_message_input_page(current_msg),
        markup,
    )
    db.set_user_state(call.from_user.id, "qset_custom_msg_input")


@bot.callback_query_handler(func=lambda c: c.data == "qset_reset_defaults")
def cb_qset_reset_defaults(call: types.CallbackQuery) -> None:
    bot.answer_callback_query(call.id, "✅ تم إعادة الإعدادات للافتراضي")
    db.reset_quick_settings(call.from_user.id)
    s = db.get_quick_settings(call.from_user.id)
    show_page(
        call,
        "quick",
        pages.quick_settings_page(s["hide_participants"], s["custom_message"]),
        kb.quick_settings_menu(s["hide_participants"]),
    )



@bot.callback_query_handler(func=lambda c: c.data == "manage_chats")
def cb_manage_chats(call: types.CallbackQuery) -> None:
    bot.answer_callback_query(call.id)
    chats = db.get_registered_chats(call.from_user.id)
    if not chats:
        bot.send_message(
            call.message.chat.id,
            "⚠ <b>لا يوجد مجموعات أو قنوات مسجلة</b>",
            parse_mode="HTML",
        )
        return
    origin = _settings_origin.get(call.from_user.id, "quick_settings")
    text = f"<b>🗂 إدارة المجموعات والقنوات</b>\n{t.divider('▬', 18)}\n\nاختر ما تريد حذفه:"
    bot.send_message(
        call.message.chat.id,
        text,
        reply_markup=kb.manage_chats_menu(chats, origin),
        parse_mode="HTML",
    )


@bot.callback_query_handler(func=lambda c: c.data and c.data.startswith("delchat_"))
def cb_delchat(call: types.CallbackQuery) -> None:
    bot.answer_callback_query(call.id)
    chat_id = int(call.data.split("_", 1)[1])
    ok = db.unregister_chat(chat_id, call.from_user.id)
    if ok:
        bot.send_message(
            call.message.chat.id,
            f"<b>✅ تم الحذف بنجاح</b>\n{t.divider('▬', 18)}\n\n<code>{chat_id}</code>",
            parse_mode="HTML",
        )
    else:
        bot.send_message(
            call.message.chat.id,
            "❌ لم يتم الحذف. تأكد من أنك مسجّل هذه المجموعة.",
        )


@bot.callback_query_handler(func=lambda c: c.data == "create_roulette")
def cb_create_roulette(call: types.CallbackQuery) -> None:
    bot.answer_callback_query(call.id)
    show_page(call, "create", pages.create_roulette(), kb.create_roulette_menu())


@bot.callback_query_handler(func=lambda c: c.data == "link_channel_group")
def cb_link_channel_group(call: types.CallbackQuery) -> None:
    bot.answer_callback_query(call.id)
    show_page(call, "create", pages.link_channel_group(), kb.link_channel_group_menu())


@bot.callback_query_handler(func=lambda c: c.data == "delete_channel_group")
def cb_delete_channel_group(call: types.CallbackQuery) -> None:
    bot.answer_callback_query(call.id)
    chats = db.get_registered_chats(call.from_user.id)
    show_page(call, "create", pages.delete_channel_group(), kb.delete_channel_group_menu(chats))


@bot.callback_query_handler(func=lambda c: c.data == "giveaway_create")
def cb_giveaway_create(call: types.CallbackQuery) -> None:
    bot.answer_callback_query(call.id)
    chats = db.get_registered_chats(call.from_user.id)
    show_page(
        call,
        "create",
        pages.giveaway_select_chat(),
        kb.giveaway_select_chat_menu(chats),
    )


@bot.callback_query_handler(func=lambda c: c.data and c.data.startswith("giveaway_select_"))
def cb_giveaway_select(call: types.CallbackQuery) -> None:
    chat_id = int(call.data.split("_", 2)[2])
    bot.answer_callback_query(call.id)
    
    # Create the raffle entry first
    raffle_id = db.create_raffle(
        creator_id=call.from_user.id,
        limit_participants=0,
        raffle_type="advanced",
        chat_id=chat_id,
    )
    db.set_user_state(call.from_user.id, "giveaway_input_text", raffle_id)
    
    bot.edit_message_text(
        pages.giveaway_input_text(),
        call.message.chat.id,
        call.message.message_id,
        reply_markup=kb.register_back_menu("giveaway_create"),
        parse_mode="HTML",
    )


@bot.callback_query_handler(func=lambda c: c.data and c.data.startswith("giveaway_toggle_"))
def cb_giveaway_toggle(call: types.CallbackQuery) -> None:
    parts = call.data.split("_")
    key = "_".join(parts[2:-1])
    raffle_id = parts[-1]
    
    raffle_row = db.get_raffle(raffle_id)
    if not raffle_row:
        bot.answer_callback_query(call.id, "❌ خطأ في السحب")
        return
        
    raffle = dict(raffle_row)
    current_val = raffle.get(key, 0)
    new_val = 0 if current_val else 1
    db.update_raffle(raffle_id, **{key: new_val})
    
    bot.answer_callback_query(call.id)
    updated_raffle = db.get_raffle(raffle_id)
    bot.edit_message_reply_markup(
        call.message.chat.id,
        call.message.message_id,
        reply_markup=kb.giveaway_settings_menu(raffle_id, dict(updated_raffle)),
    )



# ─── قناة الشرط Sub-Flow ───────────────────────────────────────────────────

@bot.callback_query_handler(func=lambda c: c.data and c.data.startswith("gcond_menu_"))
def cb_gcond_menu(call: types.CallbackQuery) -> None:
    raffle_id = call.data.split("_")[-1]
    bot.answer_callback_query(call.id)
    bot.edit_message_text(
        pages.condition_channel_select(),
        call.message.chat.id,
        call.message.message_id,
        reply_markup=kb.condition_channel_type_menu(raffle_id),
        parse_mode="HTML",
    )


@bot.callback_query_handler(func=lambda c: c.data and c.data.startswith("gcond_private_"))
def cb_gcond_private(call: types.CallbackQuery) -> None:
    raffle_id = call.data.split("_")[-1]
    bot.answer_callback_query(call.id)
    db.set_user_state(call.from_user.id, "gcond_private_fwd", raffle_id)
    db.update_raffle(raffle_id, condition_channel=1, condition_channel_type="private")
    bot.edit_message_text(
        pages.condition_channel_private(),
        call.message.chat.id,
        call.message.message_id,
        reply_markup=kb.condition_channel_back(raffle_id),
        parse_mode="HTML",
    )


@bot.callback_query_handler(func=lambda c: c.data and c.data.startswith("gcond_public_"))
def cb_gcond_public(call: types.CallbackQuery) -> None:
    raffle_id = call.data.split("_")[-1]
    bot.answer_callback_query(call.id)
    db.set_user_state(call.from_user.id, "gcond_public_username", raffle_id)
    db.update_raffle(raffle_id, condition_channel=1, condition_channel_type="public")
    bot.edit_message_text(
        pages.condition_channel_public(),
        call.message.chat.id,
        call.message.message_id,
        reply_markup=kb.condition_channel_back(raffle_id),
        parse_mode="HTML",
    )


# ─── تصويت متسابق Sub-Flow ─────────────────────────────────────────────────

@bot.callback_query_handler(func=lambda c: c.data and c.data.startswith("gvote_menu_"))
def cb_gvote_menu(call: types.CallbackQuery) -> None:
    raffle_id = call.data.split("_")[-1]
    bot.answer_callback_query(call.id)
    db.set_user_state(call.from_user.id, "gvote_code_input", raffle_id)
    bot.edit_message_text(
        pages.vote_contestant_code(),
        call.message.chat.id,
        call.message.message_id,
        reply_markup=kb.vote_contestant_back(raffle_id),
        parse_mode="HTML",
    )


# ─── سحب تلقائي Sub-Flow ───────────────────────────────────────────────────

@bot.callback_query_handler(func=lambda c: c.data and c.data.startswith("gautodraw_menu_"))
def cb_gautodraw_menu(call: types.CallbackQuery) -> None:
    raffle_id = call.data.split("_")[-1]
    bot.answer_callback_query(call.id)
    bot.edit_message_text(
        pages.auto_draw_select_method(),
        call.message.chat.id,
        call.message.message_id,
        reply_markup=kb.auto_draw_method_menu(raffle_id),
        parse_mode="HTML",
    )


@bot.callback_query_handler(func=lambda c: c.data and c.data.startswith("gautodraw_count_"))
def cb_gautodraw_count(call: types.CallbackQuery) -> None:
    raffle_id = call.data.split("_")[-1]
    bot.answer_callback_query(call.id)
    db.set_user_state(call.from_user.id, "gautodraw_count_input", raffle_id)
    db.update_raffle(raffle_id, auto_draw=1, auto_draw_type="count")
    bot.edit_message_text(
        pages.auto_draw_count(),
        call.message.chat.id,
        call.message.message_id,
        reply_markup=kb.auto_draw_count_back(raffle_id),
        parse_mode="HTML",
    )


@bot.callback_query_handler(func=lambda c: c.data and c.data.startswith("gautodraw_time_"))
def cb_gautodraw_time(call: types.CallbackQuery) -> None:
    raffle_id = call.data.split("_")[-1]
    bot.answer_callback_query(call.id)
    db.update_raffle(raffle_id, auto_draw=1, auto_draw_type="time")
    bot.edit_message_text(
        pages.auto_draw_time(),
        call.message.chat.id,
        call.message.message_id,
        reply_markup=kb.auto_draw_time_picker(raffle_id),
        parse_mode="HTML",
    )


@bot.callback_query_handler(func=lambda c: c.data and c.data.startswith("gautodraw_tval_"))
def cb_gautodraw_tval(call: types.CallbackQuery) -> None:
    parts = call.data.split("_")
    minutes = int(parts[2])
    raffle_id = parts[-1]
    bot.answer_callback_query(call.id, f"تم تحديد الوقت: {minutes} دقيقة ✅")
    db.update_raffle(raffle_id, auto_draw=1, auto_draw_type="time", auto_draw_value=minutes)
    # Return to settings panel
    raffle = db.get_raffle(raffle_id)
    bot.edit_message_text(
        pages.giveaway_settings_panel(),
        call.message.chat.id,
        call.message.message_id,
        reply_markup=kb.giveaway_settings_menu(raffle_id, dict(raffle)),
        parse_mode="HTML",
    )


@bot.callback_query_handler(func=lambda c: c.data and c.data.startswith("gautodraw_custom_"))
def cb_gautodraw_custom(call: types.CallbackQuery) -> None:
    raffle_id = call.data.split("_")[-1]
    bot.answer_callback_query(call.id)
    db.set_user_state(call.from_user.id, "gautodraw_custom_input", raffle_id)
    db.update_raffle(raffle_id, auto_draw=1, auto_draw_type="time")
    bot.edit_message_text(
        "⏲ أرسل الوقت المخصص بالدقائق:\n\nمثال: 90 (ساعة ونصف)",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=kb.auto_draw_count_back(raffle_id),
        parse_mode="HTML",
    )


@bot.callback_query_handler(func=lambda c: c.data and c.data.startswith("gautodraw_adjust_"))
def cb_gautodraw_adjust(call: types.CallbackQuery) -> None:
    raffle_id = call.data.split("_")[-1]
    bot.answer_callback_query(call.id, "📞 قريباً...")


# ─── رجوع للإعدادات ─────────────────────────────────────────────────────────

@bot.callback_query_handler(func=lambda c: c.data and c.data.startswith("gback_settings_"))
def cb_gback_settings(call: types.CallbackQuery) -> None:
    raffle_id = call.data.split("_")[-1]
    bot.answer_callback_query(call.id)
    db.clear_user_state(call.from_user.id)
    raffle = db.get_raffle(raffle_id)
    if raffle:
        bot.edit_message_text(
            pages.giveaway_settings_panel(),
            call.message.chat.id,
            call.message.message_id,
            reply_markup=kb.giveaway_settings_menu(raffle_id, dict(raffle)),
            parse_mode="HTML",
        )


@bot.callback_query_handler(func=lambda c: c.data and c.data.startswith("giveaway_publish_"))
def cb_giveaway_publish(call: types.CallbackQuery) -> None:
    raffle_id = call.data.split("_")[-1]
    bot.answer_callback_query(call.id, "جاري النشر...")
    raffle_row = db.get_raffle(raffle_id)
    if not raffle_row:
        return
    raffle = dict(raffle_row)
        
    # Set end_time if auto_draw_time is enabled
    if raffle.get("auto_draw") and raffle.get("auto_draw_type") == "time":
        import time
        minutes = raffle.get("auto_draw_value", 0)
        end_time = int(time.time()) + (minutes * 60)
        db.update_raffle(raffle_id, end_time=end_time)
        raffle["end_time"] = end_time
        
    # Format the text nicely
    text = pages.format_giveaway_text(raffle)
    
    count = db.count_participants(raffle_id)
    chat_id = raffle["chat_id"]
    
    try:
        msg = bot.send_message(
            chat_id,
            text,
            reply_markup=kb.giveaway_active_keyboard(raffle_id, count),
            parse_mode="HTML",
        )
        db.update_raffle_message(raffle_id, chat_id=chat_id, message_id=msg.message_id)
        
        try:
            # Build link to the actual group message
            raw_id = str(chat_id).replace("-100", "")
            group_url = f"https://t.me/c/{raw_id}/{msg.message_id}"
            feed_text = (
                f"<blockquote>❝ 🎉 سحب جديد >> <a href='{group_url}'>هــــنــــا</a> ❞</blockquote>\n"
                f"<blockquote>❝ 🏆 عدد الفائزين: {raffle.get('winners_count', 1)} ❞</blockquote>"
            )
            kb_feed = types.InlineKeyboardMarkup()
            kb_feed.add(types.InlineKeyboardButton("🎯 رؤية السحب", url=group_url))
            bot.send_message(GLOBAL_FEED_CHAT_ID, feed_text, reply_markup=kb_feed, parse_mode="HTML", disable_web_page_preview=True)
        except Exception as e:
            logger.error("Failed to post giveaway to global feed: %s", e)
            
        try:
            admin_kb = types.InlineKeyboardMarkup()
            admin_kb.add(types.InlineKeyboardButton("👥 رؤية المشاركين", callback_data=f"admin_viewparticipants_raffle_{raffle_id}"))
            admin_kb.add(types.InlineKeyboardButton("الذهاب للسحب ↗", url=group_url))
            user_tag = f"@{call.from_user.username}" if call.from_user.username else "بدون يوزر"
            admin.admin_log(bot, f"🎉 <b>إنشاء سحب جديد:</b>\n🆔 السحب: <code>{raffle_id}</code>\n👤 من: {call.from_user.first_name} ({user_tag})\n🎁 الجائزة: {raffle.get('prize', 'غير محدد')}", reply_markup=admin_kb)
        except Exception as e:
            pass

        bot.edit_message_text(
            pages.giveaway_published_success(),
            call.message.chat.id,
            call.message.message_id,
            reply_markup=kb.back_only("create_roulette"),
            parse_mode="HTML",
        )
    except Exception as exc:
        logger.error("giveaway publish error: %s", exc, exc_info=True)
        try:
            bot.send_message(call.from_user.id, f"⚠ خطأ: {exc}", parse_mode="HTML")
        except Exception:
            pass


@bot.callback_query_handler(func=lambda c: c.data and c.data.startswith("gjoin_"))
def cb_giveaway_join(call: types.CallbackQuery) -> None:
    raffle_id = call.data.split("_")[-1]
    
    raffle_row = db.get_raffle(raffle_id)
    if not raffle_row or raffle_row["status"] != "active":
        bot.answer_callback_query(call.id, "❌ السحب غير متاح أو منتهي.", show_alert=True)
        return
    raffle = dict(raffle_row)
        
    user = call.from_user
    
    # 1. Premium Check
    if raffle.get("premium_only") and not getattr(user, "is_premium", False):
        bot.answer_callback_query(call.id, "❌ هذا السحب للمشتركين المميزين (Premium) فقط.", show_alert=True)
        return
        
    # 2. Condition Channel Check
    if raffle.get("condition_channel"):
        channel_ids_str = raffle.get("condition_channel_ids")
        if channel_ids_str:
            channel_ids = [ch.strip() for ch in str(channel_ids_str).split("\n") if ch.strip()]
            for ch_id in channel_ids:
                try:
                    member = bot.get_chat_member(ch_id, user.id)
                    if member.status in ["left", "kicked"]:
                        bot.answer_callback_query(call.id, f"❌ يجب عليك الاشتراك في القناة أولاً:\n{ch_id}", show_alert=True)
                        return
                except Exception as e:
                    logger.error(f"Failed to check member in {ch_id}: {e}")
                    # If we can't check, we let it pass or fail? Usually let it pass or warn creator.
                    pass

    # Add participant
    ensure_user(call)
    if not db.add_participant(raffle_id, user.id, user.username, user.first_name):
        bot.answer_callback_query(call.id, "⚠️ لقد انضممت لهذا السحب مسبقاً!", show_alert=True)
        return
        
    bot.answer_callback_query(call.id, "✅ تم انضمامك للسحب بنجاح!", show_alert=True)
    count = db.count_participants(raffle_id)
    
    # Update keyboard
    try:
        bot.edit_message_reply_markup(
            call.message.chat.id,
            call.message.message_id,
            reply_markup=kb.giveaway_active_keyboard(raffle_id, count)
        )
    except Exception:
        pass

    # 3. Auto Draw (Count)
    if raffle.get("auto_draw") and raffle.get("auto_draw_type") == "count":
        target = raffle.get("auto_draw_value", 0)
        if count >= target:
            # Trigger auto draw!
            db.update_raffle(raffle_id, status="completed")
            winners_count = raffle.get("winners_count", 1)
            participants = db.get_participants(raffle_id)
            if participants:
                import random
                winners = random.sample(participants, min(winners_count, len(participants)))
                winners_text = "\n".join([f"🏆 <a href='tg://user?id={w['user_id']}'>{w['first_name']}</a>" for w in winners])
                text = f"<b>انتهى السحب! (عدد مكتمل)</b>\n\nالفائزون:\n{winners_text}"
                try:
                    bot.edit_message_text(
                        text,
                        call.message.chat.id,
                        call.message.message_id,
                        parse_mode="HTML"
                    )
                except Exception:
                    pass


@bot.callback_query_handler(func=lambda c: c.data and c.data.startswith("gstop_"))
def cb_giveaway_stop(call: types.CallbackQuery) -> None:
    raffle_id = call.data.split("_")[-1]
    bot.answer_callback_query(call.id)
    raffle_row = db.get_raffle(raffle_id)
    if not raffle_row or raffle_row["creator_id"] != call.from_user.id:
        return
    raffle = dict(raffle_row)
        
    db.update_raffle(raffle_id, status="completed")
    winners_count = raffle.get("winners_count", 1)
    participants = db.get_participants(raffle_id)
    
    if not participants:
        bot.send_message(call.message.chat.id, "انتهى السحب. لا يوجد مشاركين.")
        return
        
    import random
    winners = random.sample(participants, min(winners_count, len(participants)))
    winners_text = "\n".join([f"🏆 <a href='tg://user?id={w['user_id']}'>{w['first_name']}</a>" for w in winners])
    text = f"<b>انتهى السحب!</b>\n\nالفائزون:\n{winners_text}"
    
    bot.edit_message_text(
        text,
        call.message.chat.id,
        call.message.message_id,
        parse_mode="HTML"
    )


@bot.callback_query_handler(func=lambda c: c.data and c.data.startswith("grepublish_"))
def cb_giveaway_republish(call: types.CallbackQuery) -> None:
    raffle_id = call.data.split("_")[-1]
    bot.answer_callback_query(call.id)
    raffle_row = db.get_raffle(raffle_id)
    if not raffle_row or raffle_row["creator_id"] != call.from_user.id:
        return
    raffle = dict(raffle_row)
        
    count = db.count_participants(raffle_id)
    text = pages.format_giveaway_text(raffle)
    
    try:
        msg = bot.send_message(
            call.message.chat.id,
            text,
            reply_markup=kb.giveaway_active_keyboard(raffle_id, count),
            parse_mode="HTML"
        )
        db.update_raffle_message(raffle_id, chat_id=call.message.chat.id, message_id=msg.message_id)
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except Exception:
            bot.edit_message_text(
                "تم إعادة نشر هذا السحب في الأسفل 👇",
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=None
            )
    except Exception:
        pass
@bot.callback_query_handler(func=lambda c: c.data == "roulette_settings")
def cb_roulette_settings(call: types.CallbackQuery) -> None:
    bot.answer_callback_query(call.id)
    s = db.get_quick_settings(call.from_user.id)
    show_page(
        call,
        "create",
        pages.quick_settings_page(s["hide_participants"], s["custom_message"]),
        kb.quick_settings_menu(s["hide_participants"]),
    )


@bot.callback_query_handler(func=lambda c: c.data == "register_group")
def cb_register_group(call: types.CallbackQuery) -> None:
    bot.answer_callback_query(call.id)
    db.set_user_state(call.from_user.id, "waiting_group_id")
    show_page(
        call,
        "create",
        pages.register_group(BOT_USERNAME),
        kb.register_back_menu(),
    )


@bot.callback_query_handler(func=lambda c: c.data == "register_channel")
def cb_register_channel(call: types.CallbackQuery) -> None:
    bot.answer_callback_query(call.id)
    db.set_user_state(call.from_user.id, "waiting_channel_id")
    show_page(
        call,
        "create",
        pages.register_channel(BOT_USERNAME),
        kb.register_back_menu(),
    )


@bot.callback_query_handler(func=lambda c: c.data == "comp_reg_group")
def cb_comp_reg_group(call: types.CallbackQuery) -> None:
    bot.answer_callback_query(call.id)
    _reg_from_comp.add(call.from_user.id)
    db.set_user_state(call.from_user.id, "waiting_group_id")
    show_page(call, "create", pages.register_group(BOT_USERNAME), kb.register_back_menu("create_competition"))


@bot.callback_query_handler(func=lambda c: c.data == "comp_reg_channel")
def cb_comp_reg_channel(call: types.CallbackQuery) -> None:
    bot.answer_callback_query(call.id)
    _reg_from_comp.add(call.from_user.id)
    db.set_user_state(call.from_user.id, "waiting_channel_id")
    show_page(call, "create", pages.register_channel(BOT_USERNAME), kb.register_back_menu("create_competition"))


@bot.callback_query_handler(func=lambda c: c.data == "channel_log")
def cb_channel_log(call: types.CallbackQuery) -> None:
    bot.answer_callback_query(call.id)
    channels = db.get_log_channels(call.from_user.id)
    show_page(
        call,
        "channel_log",
        pages.channel_log(len(channels)),
        kb.channel_log_menu(channels),
    )


@bot.callback_query_handler(func=lambda c: c.data == "statistics")
def cb_statistics(call: types.CallbackQuery) -> None:
    bot.answer_callback_query(call.id)
    stats = db.get_user_stats(call.from_user.id)
    show_page(
        call,
        "statistics",
        pages.statistics(stats, db.get_top_channels(10)),
        kb.back_only(),
    )


@bot.callback_query_handler(func=lambda c: c.data == "privacy")
def cb_privacy(call: types.CallbackQuery) -> None:
    bot.answer_callback_query(call.id)
    show_page(call, "privacy", pages.privacy(), kb.back_only())


@bot.callback_query_handler(func=lambda c: c.data == "terms")
def cb_terms(call: types.CallbackQuery) -> None:
    bot.answer_callback_query(call.id)
    show_page(call, "terms", pages.terms(), kb.back_only())


@bot.callback_query_handler(func=lambda c: c.data == "profile")
def cb_profile(call: types.CallbackQuery) -> None:
    bot.answer_callback_query(call.id)
    stats = db.get_user_stats(call.from_user.id)
    remind = db.get_remind_on_win(call.from_user.id)
    show_page(call, "profile", pages.profile(stats, remind), kb.profile_menu(remind))


@bot.callback_query_handler(func=lambda c: c.data == "leaderboard")
def cb_leaderboard(call: types.CallbackQuery) -> None:
    bot.answer_callback_query(call.id)
    show_page(
        call,
        "leaderboard",
        pages.leaderboard(db.get_leaderboard()),
        kb.back_only(),
    )


@bot.callback_query_handler(func=lambda c: c.data == "remind_win")
def cb_remind_win(call: types.CallbackQuery) -> None:
    val = db.toggle_remind_on_win(call.from_user.id)
    status = "مفعل" if val else "معطل"
    bot.answer_callback_query(call.id, f"تذكير الفوز: {status}", show_alert=True)
    msg_text = call.message.text or call.message.caption or ""
    if "ملفي" in msg_text:
        stats = db.get_user_stats(call.from_user.id)
        show_page(call, "profile", pages.profile(stats, bool(val)), kb.profile_menu(bool(val)))
    elif "أهلاً بك" in msg_text or "رويلت" in msg_text or "روليت" in msg_text:
        stats = db.get_user_stats(call.from_user.id)
        chats = db.get_registered_chats(call.from_user.id)
        nav.edit_page(
            bot,
            call.message.chat.id,
            call.message.message_id,
            "main",
            pages.welcome(stats, call.from_user.full_name, call.from_user.id),
            kb.main_menu(bool(val), bool(chats)),
        )


@bot.callback_query_handler(func=lambda c: c.data == "create_competition")
def cb_create_competition(call: types.CallbackQuery) -> None:
    bot.answer_callback_query(call.id)
    show_page(call, "competition", pages.competition(), kb.competition_menu())


@bot.callback_query_handler(func=lambda c: c.data == "share_bot")
def cb_share_bot(call: types.CallbackQuery) -> None:
    bot.answer_callback_query(call.id)
    show_page(call, "share", pages.share_bot_page(BOT_USERNAME), kb.share_menu())


@bot.callback_query_handler(func=lambda c: c.data == "help_page")
def cb_help_page(call: types.CallbackQuery) -> None:
    bot.answer_callback_query(call.id)
    show_page(call, "help", pages.help_page(), kb.help_menu())


@bot.callback_query_handler(func=lambda c: c.data and c.data.startswith("tpl_"))
def cb_template(call: types.CallbackQuery) -> None:
    limits = {"tpl_weekly": 50, "tpl_flash": 10, "tpl_mega": 200}
    limit = limits.get(call.data, 10)
    bot.answer_callback_query(
        call.id,
        f"قالب {limit} مشارك — استخدم @{BOT_USERNAME} في محادثتك",
        show_alert=True,
    )


# ─── المسابقات ─────────────────────────────────────────────────────────────────


# ─── حالة المستخدم للمسابقات ────────────────────────────────────────────────

COMP_STATE_CHAT = "comp_chat"
COMP_STATE_TITLE = "comp_title"
COMP_STATE_MAX = "comp_max"
COMP_STATE_VOTES = "comp_votes"

# تخزين مؤقت للمسابقة قيد الإنشاء
_comp_wip: dict[int, dict] = {}


def _get_wip(user_id: int) -> dict:
    data = _comp_wip.get(user_id, {})
    if "comp_id" not in data:
        data["comp_id"] = db.generate_comp_id()
        data["creator_id"] = user_id
        data["win_notification"] = True
        data["results_announcement"] = True
        data["approval_system"] = False
        data["premium_only"] = False
        data["max_contestants"] = 0
        data["end_type"] = "time"
        data["end_value"] = 3600
        _comp_wip[user_id] = data
    return data


def _clear_wip(user_id: int) -> None:
    _comp_wip.pop(user_id, None)
    db.clear_user_state(user_id)


@bot.callback_query_handler(func=lambda c: c.data == "comp_start")
def cb_comp_start(call: types.CallbackQuery) -> None:
    bot.answer_callback_query(call.id)
    uid = call.from_user.id
    chats = db.get_registered_chats(uid)
    _comp_wip.pop(uid, None)
    _get_wip(uid)
    bot.edit_message_text(
        pages.comp_select_chat(),
        call.message.chat.id,
        call.message.message_id,
        reply_markup=kb.comp_chat_picker(chats),
        parse_mode="HTML",
    )


@bot.callback_query_handler(func=lambda c: c.data and c.data.startswith("comp_chat_"))
def cb_comp_chat(call: types.CallbackQuery) -> None:
    bot.answer_callback_query(call.id)
    uid = call.from_user.id
    chat_id = int(call.data.split("_")[2])
    wip = _get_wip(uid)
    wip["chat_id"] = chat_id
    _comp_wip[uid] = wip
    db.set_user_state(uid, COMP_STATE_TITLE, str(chat_id))
    bot.edit_message_text(
        pages.comp_input_title(),
        call.message.chat.id,
        call.message.message_id,
        reply_markup=kb.back_only("comp_start"),
        parse_mode="HTML",
    )


@bot.callback_query_handler(func=lambda c: c.data and c.data.startswith("comp_end_time"))
def cb_comp_end_time(call: types.CallbackQuery) -> None:
    bot.answer_callback_query(call.id)
    uid = call.from_user.id
    wip = _get_wip(uid)
    wip["end_type"] = "time"
    _comp_wip[uid] = wip
    bot.edit_message_text(
        pages.comp_input_duration(),
        call.message.chat.id,
        call.message.message_id,
        reply_markup=kb.comp_duration_picker(),
        parse_mode="HTML",
    )


@bot.callback_query_handler(func=lambda c: c.data and c.data.startswith("comp_end_votes"))
def cb_comp_end_votes(call: types.CallbackQuery) -> None:
    bot.answer_callback_query(call.id)
    uid = call.from_user.id
    wip = _get_wip(uid)
    wip["end_type"] = "votes"
    _comp_wip[uid] = wip
    db.set_user_state(uid, COMP_STATE_VOTES, wip.get("comp_id", ""))
    bot.edit_message_text(
        pages.comp_input_votes(),
        call.message.chat.id,
        call.message.message_id,
        reply_markup=kb.back_only("comp_show_end_types"),
        parse_mode="HTML",
    )


@bot.callback_query_handler(func=lambda c: c.data == "comp_show_end_types")
def cb_comp_show_end_types(call: types.CallbackQuery) -> None:
    bot.answer_callback_query(call.id)
    bot.edit_message_text(
        pages.comp_select_end(),
        call.message.chat.id,
        call.message.message_id,
        reply_markup=kb.comp_end_type_picker(),
        parse_mode="HTML",
    )


@bot.callback_query_handler(func=lambda c: c.data and c.data.startswith("comp_dur_"))
def cb_comp_dur(call: types.CallbackQuery) -> None:
    bot.answer_callback_query(call.id)
    uid = call.from_user.id
    secs = int(call.data.split("_")[2])
    wip = _get_wip(uid)
    wip["end_value"] = secs
    wip["end_type"] = "time"
    _comp_wip[uid] = wip
    # إظهار لوحة المراجعة
    bot.edit_message_text(
        pages.comp_review(wip),
        call.message.chat.id,
        call.message.message_id,
        reply_markup=kb.comp_toggle_panel(
            wip["comp_id"],
            wip.get("win_notification", True),
            wip.get("results_announcement", True),
            wip.get("approval_system", False),
            wip.get("premium_only", False),
        ),
        parse_mode="HTML",
    )


@bot.callback_query_handler(func=lambda c: c.data and c.data.startswith("comp_toggle_"))
def cb_comp_toggle(call: types.CallbackQuery) -> None:
    bot.answer_callback_query(call.id)
    uid = call.from_user.id
    parts = call.data.split("_", 3)
    key_raw = parts[2]
    comp_id = parts[3] if len(parts) > 3 else None
    key_map = {"notif": "win_notification", "results": "results_announcement", "approve": "approval_system", "premium": "premium_only"}
    key = key_map.get(key_raw)
    if not key or not comp_id:
        return
    # تحقق: هل المسابقة موجودة في قاعدة البيانات أم جديدة؟
    existing = db.get_competition(comp_id)
    if existing and existing["creator_id"] == uid:
        # موجودة → نحدث في DB مباشرة
        new_val = 0 if existing[key] else 1
        db.update_competition(comp_id, **{key: new_val})
        # تحديث بطاقات التصويت إذا تغير premium_only
        if key == "premium_only":
            apps = db.get_approved_contestants(comp_id)
            for app in apps:
                if not app["vote_msg_id"]:
                    continue
                display = f"@{app['username']}" if app["username"] else (app["first_name"] or str(app["user_id"]))
                new_card_text = pages.comp_voting_card_text(display, bool(new_val))
                votes = db.get_vote_count(comp_id, app["user_id"])
                try:
                    bot.edit_message_text(
                        new_card_text,
                        existing["chat_id"],
                        app["vote_msg_id"],
                        reply_markup=kb.comp_voting_card(comp_id, app["user_id"], votes, bool(new_val)),
                        parse_mode="HTML",
                    )
                except telebot.apihelper.ApiTelegramException:
                    pass
        existing = db.get_competition(comp_id)
        chat_name = db.get_chat_title(existing["chat_id"]) or str(existing["chat_id"])
        count = db.count_comp_participants(comp_id)
        bot.edit_message_text(
            pages.comp_review(existing),
            call.message.chat.id,
            call.message.message_id,
            reply_markup=kb.comp_settings_panel(
                comp_id,
                existing["win_notification"],
                existing["results_announcement"],
                existing["approval_system"],
                existing["premium_only"],
            ),
            parse_mode="HTML",
        )
    else:
        # جديدة → نستخدم WIP
        wip = _get_wip(uid)
        wip[key] = not wip.get(key, False)
        _comp_wip[uid] = wip
        bot.edit_message_text(
            pages.comp_review(wip),
            call.message.chat.id,
            call.message.message_id,
            reply_markup=kb.comp_toggle_panel(
                wip["comp_id"],
                wip.get("win_notification", True),
                wip.get("results_announcement", True),
                wip.get("approval_system", False),
                wip.get("premium_only", False),
            ),
            parse_mode="HTML",
        )


@bot.callback_query_handler(func=lambda c: c.data and c.data.startswith("comp_publish_"))
def cb_comp_publish(call: types.CallbackQuery) -> None:
    bot.answer_callback_query(call.id)
    uid = call.from_user.id
    wip = _get_wip(uid)
    required = ["chat_id", "title"]
    for r in required:
        if r not in wip or not wip.get(r):
            bot.answer_callback_query(call.id, f"⚠ خطأ: البيانات غير مكتملة ({r})", show_alert=True)
            return
    comp_id = db.create_competition(
        creator_id=uid,
        chat_id=wip["chat_id"],
        title=wip["title"],
        max_contestants=wip.get("max_contestants", 0),
        end_type=wip.get("end_type", "time"),
        end_value=wip.get("end_value", 3600),
        win_notification=wip.get("win_notification", True),
        results_announcement=wip.get("results_announcement", True),
        approval_system=wip.get("approval_system", False),
        premium_only=wip.get("premium_only", False),
    )
    wip["comp_id"] = comp_id
    _comp_wip[uid] = wip

    participants = []
    count = 0
    comp_row = db.get_competition(comp_id)
    remaining = _comp_remaining_seconds(comp_row) if comp_row else None
    msg_text = pages.format_competition_message(comp_row or wip, participants, count, remaining)

    try:
        sent = bot.send_message(
            wip["chat_id"],
            msg_text,
            reply_markup=kb.comp_channel_join_button(comp_id, full=_is_comp_full(comp_row) if comp_row else False),
            parse_mode="HTML",
        )
        db.update_competition_message(comp_id, sent.message_id)
        
        try:
            max_cont = comp_row.get("max_contestants") if comp_row else wip.get("max_contestants", 0)
            cont_str = str(max_cont) if max_cont > 0 else "مفتوح"
            # Build link to the actual group message
            raw_id = str(wip["chat_id"]).replace("-100", "")
            group_url = f"https://t.me/c/{raw_id}/{sent.message_id}"
            feed_text = (
                f"<blockquote>❝ 🏁 مسابقة جديدة >> <a href='{group_url}'>هــــنــــا</a> ❞</blockquote>\n"
                f"<blockquote>❝ 👥 عدد المشاركين: {cont_str} ❞</blockquote>"
            )
            kb_feed = types.InlineKeyboardMarkup()
            kb_feed.add(types.InlineKeyboardButton("🏆 رؤية المسابقة", url=group_url))
            bot.send_message(GLOBAL_FEED_CHAT_ID, feed_text, reply_markup=kb_feed, parse_mode="HTML", disable_web_page_preview=True)
        except Exception as e:
            logger.error("Failed to post comp to global feed: %s", e)
            
        try:
            admin_kb = types.InlineKeyboardMarkup()
            admin_kb.add(types.InlineKeyboardButton("👥 رؤية المشاركين", callback_data=f"admin_viewparticipants_comp_{comp_id}"))
            admin_kb.add(types.InlineKeyboardButton("الذهاب للمسابقة ↗", url=group_url))
            user_tag = f"@{call.from_user.username}" if call.from_user.username else "بدون يوزر"
            comp_title = wip.get('title', 'غير محدد')
            admin.admin_log(bot, f"🏁 <b>إنشاء مسابقة جديدة:</b>\n🆔 المسابقة: <code>{comp_id}</code>\n👤 من: {call.from_user.first_name} ({user_tag})\nالعنوان: {comp_title}\nالمقاعد: {cont_str}", reply_markup=admin_kb)
        except Exception as e:
            pass
    except telebot.apihelper.ApiTelegramException as e:
        bot.answer_callback_query(call.id, f"❌ فشل النشر: {e}", show_alert=True)
        return

    _clear_wip(uid)
    bot.edit_message_text(
        f"✅ <b>تم نشر المسابقة!</b>\n{t.divider('▬', 18)}\n\n"
        f"رقم المسابقة: <code>{comp_id}</code>\n"
        f"تم النشر في القروب/القناة بنجاح.",
        call.message.chat.id,
        call.message.message_id,
        parse_mode="HTML",
    )


# ─── إدارة المسابقات الحديثة ────────────────────────────────────────────────


@bot.callback_query_handler(func=lambda c: c.data == "comp_recent")
def cb_comp_recent(call: types.CallbackQuery) -> None:
    bot.answer_callback_query(call.id)
    uid = call.from_user.id
    comps = db.get_user_active_competitions(uid)
    if not comps:
        bot.edit_message_text(
            pages.comp_manage_title(0),
            call.message.chat.id,
            call.message.message_id,
            reply_markup=kb.comp_recent_list([]),
            parse_mode="HTML",
        )
        return
    bot.edit_message_text(
        pages.comp_manage_title(len(comps)),
        call.message.chat.id,
        call.message.message_id,
        reply_markup=kb.comp_recent_list(comps),
        parse_mode="HTML",
    )


@bot.callback_query_handler(func=lambda c: c.data and c.data.startswith("comp_manage_"))
def cb_comp_manage(call: types.CallbackQuery) -> None:
    bot.answer_callback_query(call.id)
    comp_id = call.data.split("_", 2)[2]
    comp = db.get_competition(comp_id)
    if not comp:
        bot.answer_callback_query(call.id, "❌ المسابقة غير موجودة", show_alert=True)
        return
    uid = call.from_user.id
    if comp["creator_id"] != uid:
        bot.answer_callback_query(call.id, "غير مسموح.", show_alert=True)
        return
    participants_count = db.count_comp_participants(comp_id)
    chat_name = db.get_chat_title(comp["chat_id"]) or str(comp["chat_id"])
    bot.edit_message_text(
        pages.comp_manage_contest(comp, participants_count, chat_name),
        call.message.chat.id,
        call.message.message_id,
        reply_markup=kb.comp_manage_dashboard(comp_id),
        parse_mode="HTML",
    )


@bot.callback_query_handler(func=lambda c: c.data and c.data.startswith("comp_chmax_"))
def cb_comp_chmax(call: types.CallbackQuery) -> None:
    bot.answer_callback_query(call.id)
    comp_id = call.data.split("_", 2)[2]
    comp = db.get_competition(comp_id)
    if not comp or comp["creator_id"] != call.from_user.id:
        return
    db.set_user_state(call.from_user.id, "comp_chmax", comp_id)
    current = comp['max_contestants']
    current_txt = str(current) if current > 0 else "غير محدود"
    bot.edit_message_text(
        f"📊 <b>تغيير عدد المقاعد</b>\n{t.divider('▬', 18)}\n\n"
        f"{t.blockquote('أرسل الرقم الجديد (0 = غير محدود)')}\n\n"
        f"📌 <b>العدد الحالي:</b> <code>{current_txt}</code>",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=kb.back_only(f"comp_manage_{comp_id}"),
        parse_mode="HTML",
    )


@bot.callback_query_handler(func=lambda c: c.data and c.data.startswith("comp_pause_"))
def cb_comp_pause(call: types.CallbackQuery) -> None:
    bot.answer_callback_query(call.id)
    comp_id = call.data.split("_", 2)[2]
    comp = db.get_competition(comp_id)
    if not comp or comp["creator_id"] != call.from_user.id:
        bot.answer_callback_query(call.id, "غير مسموح.", show_alert=True)
        return
    new_status = "paused" if comp["status"] == "active" else "active"
    db.set_competition_status(comp_id, new_status)
    # تحديث المنشور في القناة
    participants = db.get_comp_participants(comp_id)
    count = db.count_comp_participants(comp_id)
    comp = db.get_competition(comp_id)
    chat_name = db.get_chat_title(comp["chat_id"]) or str(comp["chat_id"])
    remaining = _comp_remaining_seconds(comp)
    try:
        msg_text = pages.format_competition_message(comp, participants, count, remaining)
        bot.edit_message_text(msg_text, comp["chat_id"], comp["message_id"], reply_markup=kb.comp_channel_join_button(comp_id, full=_is_comp_full(comp)), parse_mode="HTML")
    except telebot.apihelper.ApiTelegramException:
        pass
    bot.edit_message_text(
        pages.comp_manage_contest(comp, count, chat_name),
        call.message.chat.id,
        call.message.message_id,
        reply_markup=kb.comp_manage_dashboard(comp_id),
        parse_mode="HTML",
    )


@bot.callback_query_handler(func=lambda c: c.data and c.data.startswith("comp_cset_"))
def cb_comp_cset(call: types.CallbackQuery) -> None:
    bot.answer_callback_query(call.id)
    comp_id = call.data.split("_", 2)[2]
    comp = db.get_competition(comp_id)
    if not comp or comp["creator_id"] != call.from_user.id:
        return
    bot.edit_message_text(
        pages.comp_review(comp),
        call.message.chat.id,
        call.message.message_id,
        reply_markup=kb.comp_settings_panel(
            comp_id,
            comp["win_notification"],
            comp["results_announcement"],
            comp["approval_system"],
            comp["premium_only"],
        ),
        parse_mode="HTML",
    )


@bot.callback_query_handler(func=lambda c: c.data and c.data.startswith("comp_rmpart_"))
def cb_comp_rmpart(call: types.CallbackQuery) -> None:
    bot.answer_callback_query(call.id)
    comp_id = call.data.split("_", 2)[2]
    comp = db.get_competition(comp_id)
    if not comp or comp["creator_id"] != call.from_user.id:
        return
    db.set_user_state(call.from_user.id, "comp_rmpart", comp_id)
    participants = db.get_comp_participants(comp_id)
    if not participants:
        bot.answer_callback_query(call.id, "⚠ لا يوجد مشاركون", show_alert=True)
        return
    lines = [f"🧾 <b>قائمة المشاركين</b>\n{t.divider('▬', 18)}\n"]
    for p in participants:
        name = p["first_name"] or p["username"] or str(p["user_id"])
        votes = p.get("votes", 0)
        lines.append(f"• <code>{p['user_id']}</code> — {name} (🗳 {votes})")
    lines.append(f"\n{t.blockquote('أرسل آيدي المستخدم (الرقم) لإزالته من المسابقة')}")
    bot.edit_message_text(
        "\n".join(lines),
        call.message.chat.id,
        call.message.message_id,
        reply_markup=kb.back_only(f"comp_manage_{comp_id}"),
        parse_mode="HTML",
    )


@bot.callback_query_handler(func=lambda c: c.data and c.data.startswith("comp_delete_"))
def cb_comp_delete(call: types.CallbackQuery) -> None:
    bot.answer_callback_query(call.id)
    comp_id = call.data.split("_", 2)[2]
    comp = db.get_competition(comp_id)
    if not comp or comp["creator_id"] != call.from_user.id:
        bot.answer_callback_query(call.id, "غير مسموح.", show_alert=True)
        return
    # حذف المنشور من القناة
    if comp["chat_id"] and comp["message_id"]:
        try:
            bot.delete_message(comp["chat_id"], comp["message_id"])
        except telebot.apihelper.ApiTelegramException:
            pass
    db.delete_competition(comp_id)
    bot.answer_callback_query(call.id, "✅ تم حذف المسابقة", show_alert=True)
    # الرجوع للقائمة
    uid = call.from_user.id
    comps = db.get_user_active_competitions(uid)
    bot.edit_message_text(
        pages.comp_manage_title(len(comps)),
        call.message.chat.id,
        call.message.message_id,
        reply_markup=kb.comp_recent_list(comps),
        parse_mode="HTML",
    )


# ─── الرد على نصوص المسابقات (ضمن handler النصوص الرئيسي) ────────────────────


@bot.callback_query_handler(func=lambda c: c.data and c.data.startswith("comp_join_"))
def cb_comp_join(call: types.CallbackQuery) -> None:
    if check_banned(call.from_user.id):
        bot.answer_callback_query(call.id, "⛔️ أنت محظور من استخدام البوت.", show_alert=True)
        return
    bot.answer_callback_query(call.id)
    comp_id = call.data[len("comp_join_"):]
    comp = db.get_competition(comp_id)
    if not comp:
        bot.answer_callback_query(call.id, "❌ المسابقة غير موجودة", show_alert=True)
        return
    if comp["status"] != "active":
        bot.answer_callback_query(call.id, "❌ المسابقة منتهية", show_alert=True)
        return
    uid = call.from_user.id
    # التحقق من العدد الأقصى
    max_c = comp["max_contestants"]
    if max_c > 0:
        cur_count = len(db.get_approved_contestants(comp_id))
        if cur_count >= max_c:
            bot.answer_callback_query(call.id, "❌ المسابقة ممتلئة", show_alert=True)
            return
    # التحقق من وجود طلب سابق
    existing = db.get_application(comp_id, uid)
    if existing:
        if existing["status"] == "pending":
            bot.answer_callback_query(call.id, "⏳ طلبك قيد المراجعة", show_alert=True)
        elif existing["status"] == "approved":
            bot.answer_callback_query(call.id, "✅ أنت مشترك بالفعل", show_alert=True)
        else:
            bot.answer_callback_query(call.id, "❌ تم رفض طلبك سابقاً", show_alert=True)
        return
    # إرسال رسالة التأكيد في الخاص
    user = call.from_user
    user_display = user.first_name or user.username or str(user.id)
    try:
        bot.send_message(
            uid,
            pages.comp_confirm_message(comp["title"], user_display),
            reply_markup=kb.comp_confirm_join(comp_id),
            parse_mode="HTML",
        )
        bot.answer_callback_query(call.id, "✅ تم إرسال التأكيد في الخاص", show_alert=True)
    except telebot.apihelper.ApiTelegramException:
        bot.answer_callback_query(call.id, "❌ أرسل رسالة للبوت أولاً", show_alert=True)


@bot.callback_query_handler(func=lambda c: c.data and c.data.startswith("comp_confirm_yes_"))
def cb_comp_confirm_yes(call: types.CallbackQuery) -> None:
    bot.answer_callback_query(call.id)
    uid = call.from_user.id
    parts = call.data.split("_", 3)
    comp_id = parts[3]
    comp = db.get_competition(comp_id)
    if not comp or comp["status"] != "active":
        bot.answer_callback_query(call.id, "❌ المسابقة غير نشطة", show_alert=True)
        return
    max_c = comp["max_contestants"]
    if max_c > 0:
        cur_count = len(db.get_approved_contestants(comp_id))
        if cur_count >= max_c:
            bot.edit_message_text("❌ المسابقة ممتلئة.", call.message.chat.id, call.message.message_id, parse_mode="HTML")
            return
    user = call.from_user
    result = db.apply_competition(comp_id, uid, user.username, user.first_name)
    if result in ("exists", "error"):
        bot.edit_message_text("⚠ حدث خطأ أو أنك مشترك بالفعل.", call.message.chat.id, call.message.message_id, parse_mode="HTML")
        return
    if result == "pending":
        # يحتاج موافقة المشرف
        bot.edit_message_text(
            pages.comp_pending_message(),
            call.message.chat.id,
            call.message.message_id,
            reply_markup=kb.comp_pending_notify(comp["creator_id"]),
            parse_mode="HTML",
        )
        # إرسال إشعار للمشرف
        try:
            user_display = f"@{user.username}" if user.username else (user.first_name or str(user.id))
            bot.send_message(
                comp["creator_id"],
                pages.comp_admin_notify(user_display, uid, comp["title"], comp_id),
                reply_markup=kb.comp_admin_approve_reject(comp_id, uid),
                parse_mode="HTML",
            )
        except telebot.apihelper.ApiTelegramException:
            pass
    else:  # approved مباشرة
        bot.edit_message_text(
            pages.comp_approved_message(comp["title"]),
            call.message.chat.id,
            call.message.message_id,
            parse_mode="HTML",
        )
        # إنشاء بطاقة التصويت
        approved = db.get_approved_contestants(comp_id)
        votes = db.get_vote_count(comp_id, uid)
        display = f"@{user.username}" if user.username else (user.first_name or str(user.id))
        card_text = pages.comp_voting_card_text(display, bool(comp["premium_only"]))
        try:
            sent = bot.send_message(
                comp["chat_id"],
                card_text,
                reply_markup=kb.comp_voting_card(comp_id, uid, votes, bool(comp["premium_only"])),
                parse_mode="HTML",
            )
            db.set_vote_msg_id(comp_id, uid, sent.message_id)
        except telebot.apihelper.ApiTelegramException:
            pass
        # تحديث العداد في رسالة القناة
        count = len(approved)
        remaining = _comp_remaining_seconds(comp)
        comp_row = db.get_competition(comp_id)
        try:
            bot.edit_message_text(
                pages.format_competition_message(comp_row or comp, [], count, remaining),
                comp["chat_id"],
                comp["message_id"],
                reply_markup=kb.comp_channel_join_button(comp_id, full=_is_comp_full(comp_row or comp)),
                parse_mode="HTML",
            )
        except telebot.apihelper.ApiTelegramException:
            pass


@bot.callback_query_handler(func=lambda c: c.data and c.data.startswith("comp_confirm_no_"))
def cb_comp_confirm_no(call: types.CallbackQuery) -> None:
    bot.answer_callback_query(call.id)
    bot.edit_message_text(
        f"❌ <b>تم إلغاء المشاركة</b>\n{t.divider('▬', 18)}\n\n"
        f"{t.blockquote('تم إلغاء طلب المشاركة بنجاح')}",
        call.message.chat.id,
        call.message.message_id,
        parse_mode="HTML",
    )


@bot.callback_query_handler(func=lambda c: c.data and c.data.startswith("comp_admapp_"))
def cb_comp_admapp(call: types.CallbackQuery) -> None:
    bot.answer_callback_query(call.id)
    parts = call.data.split("_", 2)
    rest = parts[2]
    comp_id, target_uid = rest.rsplit("_", 1)
    target_uid = int(target_uid)
    comp = db.get_competition(comp_id)
    if not comp or comp["creator_id"] != call.from_user.id:
        bot.answer_callback_query(call.id, "غير مسموح.", show_alert=True)
        return
    ok = db.set_application_status(comp_id, target_uid, "approved")
    if not ok:
        bot.answer_callback_query(call.id, "⚠ فشل", show_alert=True)
        return
    # إشعار المستخدم
    try:
        bot.send_message(
            target_uid,
            pages.comp_approved_message(comp["title"]),
            parse_mode="HTML",
        )
    except telebot.apihelper.ApiTelegramException:
        pass
    # إنشاء بطاقة التصويت
    votes = db.get_vote_count(comp_id, target_uid)
    app = db.get_application(comp_id, target_uid)
    display = f"@{app['username']}" if app and app["username"] else (app["first_name"] or str(target_uid) if app else str(target_uid))
    card_text = pages.comp_voting_card_text(display, bool(comp["premium_only"]))
    try:
        sent = bot.send_message(
            comp["chat_id"],
            card_text,
            reply_markup=kb.comp_voting_card(comp_id, target_uid, votes, bool(comp["premium_only"])),
            parse_mode="HTML",
        )
        db.set_vote_msg_id(comp_id, target_uid, sent.message_id)
    except telebot.apihelper.ApiTelegramException:
        pass
    # تحديث العداد في رسالة القناة
    approved = db.get_approved_contestants(comp_id)
    count = len(approved)
    remaining = _comp_remaining_seconds(comp)
    comp = db.get_competition(comp_id)
    try:
        bot.edit_message_text(
            pages.format_competition_message(comp, [], count, remaining),
            comp["chat_id"],
            comp["message_id"],
            reply_markup=kb.comp_channel_join_button(comp_id, full=_is_comp_full(comp)),
            parse_mode="HTML",
        )
    except telebot.apihelper.ApiTelegramException:
        pass
    # تحديث رسالة الإشعار للإدارة
    bot.edit_message_text(
        f"✅ <b>تمت الموافقة ✓</b>\n{t.divider('▬', 18)}\n\n"
        f"{t.blockquote(f'تم قبول المستخدم في المسابقة')}\n\n"
        f"👤 <b>المستخدم:</b> <code>{target_uid}</code>\n"
        f"🏆 <b>المسابقة:</b> {comp['title']}",
        call.message.chat.id,
        call.message.message_id,
        parse_mode="HTML",
    )


@bot.callback_query_handler(func=lambda c: c.data and c.data.startswith("comp_admrej_"))
def cb_comp_admrej(call: types.CallbackQuery) -> None:
    bot.answer_callback_query(call.id)
    parts = call.data.split("_", 2)
    rest = parts[2]
    comp_id, target_uid = rest.rsplit("_", 1)
    target_uid = int(target_uid)
    comp = db.get_competition(comp_id)
    if not comp or comp["creator_id"] != call.from_user.id:
        bot.answer_callback_query(call.id, "غير مسموح.", show_alert=True)
        return
    ok = db.set_application_status(comp_id, target_uid, "rejected")
    if not ok:
        bot.answer_callback_query(call.id, "⚠ فشل", show_alert=True)
        return
    try:
        title = comp["title"]
        bot.send_message(
            target_uid,
            pages.comp_rejected_message(title),
            parse_mode="HTML",
        )
    except telebot.apihelper.ApiTelegramException:
        pass
    bot.edit_message_text(
        f"❌ <b>تم الرفض ✗</b>\n{t.divider('▬', 18)}\n\n"
        f"{t.blockquote(f'تم رفض المستخدم من المسابقة')}\n\n"
        f"👤 <b>المستخدم:</b> <code>{target_uid}</code>\n"
        f"🏆 <b>المسابقة:</b> {comp['title']}",
        call.message.chat.id,
        call.message.message_id,
        parse_mode="HTML",
    )


@bot.callback_query_handler(func=lambda c: c.data and c.data.startswith("comp_votecard_"))
def cb_comp_votecard(call: types.CallbackQuery) -> None:
    bot.answer_callback_query(call.id)
    parts = call.data.split("_", 3)
    contest_id = parts[2]
    contestant_id = int(parts[3])
    comp = db.get_competition(contest_id)
    if not comp or comp["status"] != "active":
        bot.answer_callback_query(call.id, "❌ المسابقة غير نشطة", show_alert=True)
        return
    voter_id = call.from_user.id
    if voter_id == contestant_id:
        bot.answer_callback_query(call.id, "⚠ لا يمكنك التصويت لنفسك", show_alert=True)
        return
    # تحقق من بريميوم إذا مطلوب
    if comp["premium_only"]:
        from config import PREMIUM_IDS
        if voter_id not in PREMIUM_IDS:
            bot.answer_callback_query(call.id, "💎 فقط المشتركين المميزين", show_alert=True)
            return
    result = db.vote_contestant(contest_id, contestant_id, voter_id)
    if result == "duplicate":
        bot.answer_callback_query(call.id, "⚠ لقد صوتّ مسبقاً", show_alert=True)
        return
    # تحديث عداد البطاقة
    new_votes = db.get_vote_count(contest_id, contestant_id)
    try:
        bot.edit_message_reply_markup(
            call.message.chat.id,
            call.message.message_id,
            reply_markup=kb.comp_voting_card(contest_id, contestant_id, new_votes, bool(comp["premium_only"])),
        )
    except telebot.apihelper.ApiTelegramException:
        pass
    # إنهاء المسابقة إذا وصل المتسابق للعدد المطلوب من الأصوات
    if comp["end_type"] == "votes" and new_votes >= comp["end_value"]:
        finalize_competition(contest_id)
    bot.answer_callback_query(call.id, f"✅ تم التصويت! العدد: {new_votes}", show_alert=False)


@bot.callback_query_handler(func=lambda c: c.data and c.data.startswith("comp_copycode_"))
def cb_comp_copycode(call: types.CallbackQuery) -> None:
    bot.answer_callback_query(call.id)
    parts = call.data.split("_", 3)
    contest_id = parts[2]
    contestant_id = int(parts[3])
    bot.answer_callback_query(
        call.id,
        f"🎖 كود المتسابق: {contest_id}:{contestant_id}",
        show_alert=True,
    )


@bot.callback_query_handler(func=lambda c: c.data and c.data.startswith("comp_leave_"))
def cb_comp_leave(call: types.CallbackQuery) -> None:
    bot.answer_callback_query(call.id)
    comp_id = call.data.split("_", 2)[2]
    uid = call.from_user.id
    ok = db.set_application_status(comp_id, uid, "rejected")
    if ok:
        # حذف بطاقة التصويت
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except telebot.apihelper.ApiTelegramException:
            pass
        bot.answer_callback_query(call.id, "✅ تمت المغادرة", show_alert=True)
    else:
        bot.answer_callback_query(call.id, "⚠ حدث خطأ", show_alert=True)


@bot.callback_query_handler(func=lambda c: c.data == "my_activity")
def cb_my_activity(call: types.CallbackQuery) -> None:
    bot.answer_callback_query(call.id)
    rows = db.get_user_activity(call.from_user.id, 12)
    if not rows:
        body = "لا يوجد نشاط مسجّل بعد."
    else:
        body = "\n".join(
            f"• {r['event']}: {r['detail'] or '—'}" for r in rows
        )
    show_page(
        call,
        "channel_log",
        pages.channel_log(len(db.get_log_channels(call.from_user.id)))
        + f"\n\n<b>آخر نشاطك:</b>\n{body}",
        kb.channel_log_menu(db.get_log_channels(call.from_user.id)),
    )


# ─── إدارة السحوبات ───────────────────────────────────────────────────────────


@bot.callback_query_handler(func=lambda c: c.data and c.data.startswith("raffle_"))
def cb_raffle_control(call: types.CallbackQuery) -> None:
    bot.answer_callback_query(call.id)
    raffle_id = call.data.replace("raffle_", "", 1)
    raffle = db.get_raffle(raffle_id)
    if not raffle or raffle["creator_id"] != call.from_user.id:
        bot.answer_callback_query(call.id, "السحب غير موجود.", show_alert=True)
        return
    count = db.count_participants(raffle_id)
    show_page(
        call,
        "my_raffles",
        pages.raffle_control(raffle_id, count, raffle["limit_participants"]),
        kb.raffle_control(
            raffle_id,
            raffle["hide_participants"],
            raffle["hide_buttons"],
            raffle["old_members_only"],
        ),
    )


@bot.callback_query_handler(func=lambda c: c.data and c.data.startswith("toggle_"))
def cb_toggle_raffle(call: types.CallbackQuery) -> None:
    bot.answer_callback_query(call.id)
    field_map = {
        "toggle_hidep_": "hide_participants",
        "toggle_hideb_": "hide_buttons",
        "toggle_oldm_": "old_members_only",
    }
    field, raffle_id = None, None
    for prefix, fname in field_map.items():
        if call.data.startswith(prefix):
            field, raffle_id = fname, call.data[len(prefix):]
            break
    if not field:
        return
    raffle = db.get_raffle(raffle_id)
    if not raffle or raffle["creator_id"] != call.from_user.id:
        return
    db.toggle_raffle_field(raffle_id, field)
    raffle = db.get_raffle(raffle_id)
    count = db.count_participants(raffle_id)
    show_page(
        call,
        "my_raffles",
        pages.raffle_control(raffle_id, count, raffle["limit_participants"]),
        kb.raffle_control(
            raffle_id,
            raffle["hide_participants"],
            raffle["hide_buttons"],
            raffle["old_members_only"],
        ),
    )
    update_raffle_message_ui(raffle_id)


@bot.callback_query_handler(func=lambda c: c.data and c.data.startswith("republish_"))
def cb_republish(call: types.CallbackQuery) -> None:
    bot.answer_callback_query(call.id, "تم إعادة النشر ✓")
    raffle_id = call.data.replace("republish_", "", 1)
    raffle = db.get_raffle(raffle_id)
    if raffle and raffle["creator_id"] == call.from_user.id:
        update_raffle_message_ui(raffle_id)


@bot.callback_query_handler(func=lambda c: c.data and c.data.startswith("stop_"))
def cb_stop_raffle(call: types.CallbackQuery) -> None:
    raffle_id = call.data.replace("stop_", "", 1)
    raffle = db.get_raffle(raffle_id)
    if not raffle or raffle["creator_id"] != call.from_user.id:
        bot.answer_callback_query(call.id, "غير مسموح.", show_alert=True)
        return
    db.stop_raffle(raffle_id)
    post_log(call.from_user.id, "إيقاف", f"أوقف السحب {raffle_id}")
    bot.answer_callback_query(call.id, "تم إيقاف السحب.", show_alert=True)
    raffles = db.get_user_active_raffles(call.from_user.id)
    show_page(
        call,
        "my_raffles",
        pages.my_raffles_header(len(raffles)),
        kb.my_raffles_list([r["raffle_id"] for r in raffles]),
    )


@bot.callback_query_handler(func=lambda c: c.data and c.data.startswith("duplicate_"))
def cb_duplicate(call: types.CallbackQuery) -> None:
    raffle_id = call.data.replace("duplicate_", "", 1)
    raffle = db.get_raffle(raffle_id)
    if not raffle or raffle["creator_id"] != call.from_user.id:
        bot.answer_callback_query(call.id, "غير مسموح.", show_alert=True)
        return
    new_id = db.duplicate_raffle(raffle_id)
    bot.answer_callback_query(call.id, f"نسخة جديدة: {new_id}", show_alert=True)


@bot.callback_query_handler(func=lambda c: c.data and c.data.startswith("export_"))
def cb_export(call: types.CallbackQuery) -> None:
    raffle_id = call.data.replace("export_", "", 1)
    raffle = db.get_raffle(raffle_id)
    if not raffle or raffle["creator_id"] != call.from_user.id:
        bot.answer_callback_query(call.id, "غير مسموح.", show_alert=True)
        return
    participants = db.get_participants(raffle_id)
    lines = [f"سحب {raffle_id}", "─" * 20]
    for i, p in enumerate(participants, 1):
        name = participant_name(p)
        lines.append(f"{i}. {name} ({p['user_id']})")
    content = "\n".join(lines).encode("utf-8")
    bot.send_document(
        call.message.chat.id,
        ("participants.txt", io.BytesIO(content)),
        caption=f"◈ مشاركو {raffle_id} ({len(participants)})",
    )
    bot.answer_callback_query(call.id, "تم التصدير ✓")


# ─── Inline Query ───────────────────────────────────────────────────────────────





# ─── انضمام / فائز ────────────────────────────────────────────────────────────


@bot.callback_query_handler(func=lambda c: c.data and c.data.startswith("join_"))
def cb_join_raffle(call: types.CallbackQuery) -> None:
    try:
        if check_banned(call.from_user.id):
            bot.answer_callback_query(call.id, "⛔️ أنت محظور من استخدام البوت.", show_alert=True)
            return
        raffle_id = call.data.replace("join_", "", 1)
        if raffle_id.startswith("P_"):
            parts = raffle_id.split("_")
            limit = int(parts[1])
            bot.answer_callback_query(call.id, "✅ جاري التجهيز...")
            s = db.get_quick_settings(call.from_user.id)
            real_id = db.create_raffle(
                creator_id=call.from_user.id,
                limit_participants=limit,
                raffle_type="quick",
                hide_participants=s["hide_participants"],
                hide_buttons=s["hide_buttons"],
                old_members_only=s["old_members_only"],
            )
            
            # Log to admin channel
            admin_kb = types.InlineKeyboardMarkup()
            admin_kb.add(types.InlineKeyboardButton("👥 رؤية المشاركين", callback_data=f"admin_viewparticipants_raffle_{real_id}"))
            user_tag = f"@{call.from_user.username}" if call.from_user.username else "بدون يوزر"
            admin.admin_log(bot, f"🎰 <b>إنشاء روليت سريع:</b>\n🆔 السحب: <code>{real_id}</code>\n👤 من: {call.from_user.first_name} ({user_tag})\n👥 العدد المطلوب: {limit}", reply_markup=admin_kb)
            
            db.add_participant(real_id, call.from_user.id, call.from_user.username, call.from_user.first_name)
            if call.inline_message_id:
                safe_edit_inline(
                    call.inline_message_id,
                    pages.format_quick_raffle_message(1, limit, db.get_participants(real_id), hide_participants=s["hide_participants"], custom_message=db.get_custom_message(call.from_user.id)),
                    kb.quick_raffle_active(real_id, hide_buttons=s["hide_buttons"]),
                )
                db.update_raffle_message(real_id, inline_message_id=call.inline_message_id)
            elif call.message:
                msg = bot.send_message(
                    call.message.chat.id,
                    pages.format_quick_raffle_message(1, limit, db.get_participants(real_id), hide_participants=s["hide_participants"], custom_message=db.get_custom_message(call.from_user.id)),
                    reply_markup=kb.quick_raffle_active(real_id, hide_buttons=s["hide_buttons"]),
                    parse_mode="HTML",
                )
                db.update_raffle_message(real_id, chat_id=call.message.chat.id, message_id=msg.message_id)
                try:
                    bot.delete_message(call.message.chat.id, call.message.message_id)
                except Exception:
                    pass
            return
        bot.answer_callback_query(call.id, "✅ جاري الانضمام...")
        raffle = db.get_raffle(raffle_id)
        if not raffle:
            return
        if raffle["status"] != "active":
            return
        user = call.from_user
        if not db.add_participant(raffle_id, user.id, user.username, user.first_name):
            return
        ensure_user(call)
        name = display_name(user)
        safe_send(
            raffle["creator_id"],
            pages.format_new_participant_dm(name, user.id, raffle_id),
            kb.creator_participant_actions(raffle_id, user.id),
        )
        safe_send(user.id, f"🎰 تم انضمامك للسحب <code>{raffle_id}</code> بنجاح ✓")
        update_raffle_message_ui(raffle_id)
        if db.count_participants(raffle_id) >= raffle["limit_participants"]:
            finish_raffle_with_winner(raffle_id)
    except Exception as exc:
        logger.error("join error: %s", exc, exc_info=True)
        try:
            bot.send_message(call.from_user.id, f"⚠ خطأ: {exc}", parse_mode="HTML")
        except Exception:
            pass


@bot.callback_query_handler(func=lambda c: c.data and c.data.startswith("pick_"))
def cb_pick_winner(call: types.CallbackQuery) -> None:
    raffle_id = call.data.replace("pick_", "", 1)
    if raffle_id.startswith("P_"):
        bot.answer_callback_query(call.id, "⚠ لم يبدأ السحب، اضغط انضم أولاً.", show_alert=True)
        return
    raffle = db.get_raffle(raffle_id)
    if not raffle:
        bot.answer_callback_query(call.id, "غير موجود.", show_alert=True)
        return
    if not can_pick_winner(raffle, call.from_user.id):
        bot.answer_callback_query(call.id, "للمنشئ/المشرفين فقط.", show_alert=True)
        return
    if db.count_participants(raffle_id) == 0:
        bot.answer_callback_query(call.id, "لا مشاركين.", show_alert=True)
        return
    bot.answer_callback_query(call.id)
    finish_raffle_with_winner(raffle_id)


@bot.callback_query_handler(func=lambda c: c.data and c.data.startswith("pickagain_"))
def cb_pick_again(call: types.CallbackQuery) -> None:
    raffle_id = call.data.replace("pickagain_", "", 1)
    raffle = db.get_raffle(raffle_id)
    if not raffle or not can_pick_winner(raffle, call.from_user.id):
        bot.answer_callback_query(call.id, "غير مسموح.", show_alert=True)
        return
    winner = db.pick_random_winner(raffle_id)
    if not winner:
        bot.answer_callback_query(call.id, "لا مشاركين.", show_alert=True)
        return
    bot.answer_callback_query(call.id)

    def done():
        name = participant_name(winner)
        db.record_winner(raffle_id, winner["user_id"], name)
        _apply_winner_ui(db.get_raffle(raffle_id), name, raffle_id)

    _run_spin_animation(raffle_id, winner, done)


@bot.callback_query_handler(func=lambda c: c.data and c.data.startswith("replay_"))
def cb_replay(call: types.CallbackQuery) -> None:
    old_id = call.data.replace("replay_", "", 1)
    old = db.get_raffle(old_id)
    if not old or not can_pick_winner(old, call.from_user.id):
        bot.answer_callback_query(call.id, "غير مسموح.", show_alert=True)
        return
    bot.answer_callback_query(call.id)
    new_id = db.create_raffle(
        creator_id=old["creator_id"],
        limit_participants=old["limit_participants"],
        raffle_type="quick",
        chat_id=old["chat_id"],
        message_id=old["message_id"],
        inline_message_id=old["inline_message_id"],
    )
    text = pages.format_quick_raffle_message(0, old["limit_participants"], [], custom_message=db.get_custom_message(call.from_user.id))
    markup = kb.quick_raffle_active(new_id)
    if old["inline_message_id"]:
        db.update_raffle_message(new_id, inline_message_id=old["inline_message_id"])
        safe_edit_inline(old["inline_message_id"], text, markup)
    elif old["chat_id"] and old["message_id"]:
        db.update_raffle_message(new_id, chat_id=old["chat_id"], message_id=old["message_id"])
        safe_edit_message(old["chat_id"], old["message_id"], text, markup)


@bot.callback_query_handler(func=lambda c: c.data and c.data.startswith("exclude_"))
def cb_exclude(call: types.CallbackQuery) -> None:
    parts = call.data.split("_")
    if len(parts) < 3:
        return
    raffle_id, user_id = parts[1], int(parts[2])
    raffle = db.get_raffle(raffle_id)
    if not raffle or raffle["creator_id"] != call.from_user.id:
        bot.answer_callback_query(call.id, "غير مسموح.", show_alert=True)
        return
    db.remove_participant(raffle_id, user_id)
    bot.answer_callback_query(call.id, "✅ تم الاستبعاد وحذف الإشعار", show_alert=True)
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except Exception:
        pass
    post_log(call.from_user.id, "استبعاد", f"مستخدم {user_id} من {raffle_id}")


# ─── تسجيل القروبات ───────────────────────────────────────────────────────────


@bot.message_handler(func=lambda m: m.chat.type in ("group", "supergroup") and m.text and m.text.strip() == "تفعيل روليت")
def group_text_handler(message: types.Message) -> None:
    try:
        user_status = bot.get_chat_member(message.chat.id, message.from_user.id).status
        if user_status not in ("creator", "administrator"):
            bot.reply_to(message, "❌ عذراً، هذا الأمر مخصص لمشرفي المجموعة فقط.")
            return
            
        db.register_chat(message.from_user.id, message.chat.id, message.chat.title)
        
        # Verify bot permissions
        bot_member = bot.get_chat_member(message.chat.id, bot.get_me().id)
        if bot_member.status != "administrator":
            bot.reply_to(message, "✅ تم تسجيل الجروب بنجاح!\n\n⚠ لكن يرجى رفع البوت كمشرف (Admin) لضمان عمل الروليت بدون مشاكل.")
            return
            
        bot.reply_to(message, "✅ تم تفعيل الروليت في هذا الجروب بنجاح!\n\nيمكنك الآن الذهاب للبوت لإنشاء السحوبات.")
    except Exception as e:
        logger.error(f"Error registering group: {e}")
        bot.reply_to(message, "❌ حدث خطأ أثناء تفعيل الجروب. تأكد من إعطاء البوت الصلاحيات المطلوبة.")


@bot.message_handler(func=lambda m: m.chat.type == "private", content_types=["text", "photo", "video", "document", "audio", "voice", "animation"])
def private_text_handler(message: types.Message) -> None:
    ensure_user(message)
    uid = message.from_user.id
    state_row = db.get_user_state(uid)
    if not state_row:
        return
    state = state_row["state"]
    text = (message.text or "").strip()

    # ── حالات المسابقات ──────────────────────────────────────────────────────
    # ── حالات السحوبات (Giveaways) ──────────────────────────────────────────

    if state == "qset_custom_msg_input":
        new_msg = text if text else (message.caption or "").strip()
        if new_msg:
            db.set_custom_message(uid, new_msg)
            db.clear_user_state(uid)
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("رجوع للإعدادات ↩️", callback_data="quick_settings", style="danger"))
            bot.send_message(
                message.chat.id,
                "✅ تم تحديث نص الترحيب في كليشة اللعبة بنجاح.",
                reply_markup=markup,
                parse_mode="HTML",
            )
        else:
            bot.send_message(message.chat.id, "❌ يرجى إرسال نص صحيح.")
        return

    if state == "gcond_private_fwd":
        raffle_id = state_row["data"]
        if message.forward_from_chat:
            db.update_raffle(raffle_id, condition_channel_ids=str(message.forward_from_chat.id))
            db.clear_user_state(message.from_user.id)
            raffle = db.get_raffle(raffle_id)
            bot.send_message(
                message.chat.id,
                pages.giveaway_settings_panel(),
                reply_markup=kb.giveaway_settings_menu(raffle_id, dict(raffle)),
                parse_mode="HTML"
            )
        else:
            bot.send_message(message.chat.id, "❌ يرجى توجيه رسالة صحيحة من القناة.")
        return

    if state == "gcond_public_username":
        raffle_id = state_row["data"]
        usernames = "\n".join([u for u in message.text.split() if u.startswith("@")])
        if usernames:
            db.update_raffle(raffle_id, condition_channel_ids=usernames)
            db.clear_user_state(message.from_user.id)
            raffle = db.get_raffle(raffle_id)
            bot.send_message(
                message.chat.id,
                pages.giveaway_settings_panel(),
                reply_markup=kb.giveaway_settings_menu(raffle_id, dict(raffle)),
                parse_mode="HTML"
            )
        else:
            bot.send_message(message.chat.id, "❌ يرجى إرسال يوزر قناة صحيح يبدأ بـ @.")
        return

    if state == "gvote_code_input":
        raffle_id = state_row["data"]
        code = text
        if code.startswith("C"):
            db.update_raffle(raffle_id, vote_contestant=1, vote_code=code)
            db.clear_user_state(message.from_user.id)
            raffle = db.get_raffle(raffle_id)
            bot.send_message(
                message.chat.id,
                pages.giveaway_settings_panel(),
                reply_markup=kb.giveaway_settings_menu(raffle_id, dict(raffle)),
                parse_mode="HTML"
            )
        else:
            bot.send_message(message.chat.id, "❌ الكود يجب أن يبدأ بحرف C.")
        return

    if state == "gautodraw_count_input":
        raffle_id = state_row["data"]
        if not text:
            bot.send_message(message.chat.id, "❌ يرجى إرسال رقم صحيح.")
            return
        if text.isdigit():
            count = int(text)
            if count <= 0:
                bot.send_message(message.chat.id, "❌ يجب أن يكون العدد أكبر من 0.")
                return
            db.update_raffle(raffle_id, auto_draw=1, auto_draw_type="count", auto_draw_value=count)
            db.clear_user_state(message.from_user.id)
            raffle = db.get_raffle(raffle_id)
            bot.send_message(
                message.chat.id,
                f"✅ تم تحديد العدد: {count} مشارك\n\n" + pages.giveaway_settings_panel(),
                reply_markup=kb.giveaway_settings_menu(raffle_id, dict(raffle)),
                parse_mode="HTML"
            )
        else:
            bot.send_message(message.chat.id, "❌ يرجى إرسال رقم صحيح.")
        return

    if state == "gautodraw_custom_input":
        raffle_id = state_row["data"]
        if not text:
            bot.send_message(message.chat.id, "❌ يرجى إرسال رقم صحيح بالدقائق.")
            return
        if text.isdigit():
            minutes = int(text)
            if minutes <= 0:
                bot.send_message(message.chat.id, "❌ يجب أن يكون الرقم أكبر من 0.")
                return
            db.update_raffle(raffle_id, auto_draw=1, auto_draw_type="time", auto_draw_value=minutes)
            db.clear_user_state(message.from_user.id)
            raffle = db.get_raffle(raffle_id)
            bot.send_message(
                message.chat.id,
                f"✅ تم تحديد الوقت: {minutes} دقيقة\n\n" + pages.giveaway_settings_panel(),
                reply_markup=kb.giveaway_settings_menu(raffle_id, dict(raffle)),
                parse_mode="HTML"
            )
        else:
            bot.send_message(message.chat.id, "❌ يرجى إرسال رقم صحيح بالدقائق.")
        return

    if state == "giveaway_input_text":
        raffle_id = state_row["data"]
        if not text:
            bot.reply_to(message, "⚠ أرسل نص السحب.")
            return
        db.update_raffle(raffle_id, giveaway_text=text)
        db.set_user_state(uid, "giveaway_input_winners", raffle_id)
        bot.reply_to(
            message,
            pages.giveaway_input_winners(),
            reply_markup=kb.register_back_menu("giveaway_create"),
            parse_mode="HTML",
        )
        return

    if state == "giveaway_input_winners":
        raffle_id = state_row["data"]
        if not text:
            bot.reply_to(message, "⚠ أرسل رقماً صحيحاً.")
            return
        try:
            winners_count = int(text)
            if winners_count <= 0:
                raise ValueError
        except ValueError:
            bot.reply_to(message, "⚠ أرسل رقماً صحيحاً أكبر من 0.")
            return
        db.update_raffle(raffle_id, winners_count=winners_count)
        db.clear_user_state(uid)
        raffle = db.get_raffle(raffle_id)
        bot.reply_to(
            message,
            pages.giveaway_settings_panel(),
            reply_markup=kb.giveaway_settings_menu(raffle_id, dict(raffle)),
            parse_mode="HTML",
        )
        return

    if state == COMP_STATE_TITLE:
        if not text:
            bot.reply_to(message, "⚠ أرسل نص المسابقة.")
            return
        wip = _get_wip(uid)
        wip["title"] = text
        _comp_wip[uid] = wip
        db.set_user_state(uid, COMP_STATE_MAX, wip.get("comp_id", ""))
        bot.reply_to(
            message,
            pages.comp_input_max(),
            reply_markup=kb.back_only("comp_start"),
            parse_mode="HTML",
        )
        return

    if state == COMP_STATE_MAX:
        if not text:
            return
        try:
            max_val = int(text)
            if max_val < 0:
                raise ValueError
        except ValueError:
            bot.reply_to(message, "⚠ أرسل رقماً صحيحاً (0 = غير محدود).")
            return
        wip = _get_wip(uid)
        wip["max_contestants"] = max_val
        _comp_wip[uid] = wip
        db.clear_user_state(uid)
        bot.reply_to(
            message,
            pages.comp_select_end(),
            reply_markup=kb.comp_end_type_picker(),
            parse_mode="HTML",
        )
        return

    if state == COMP_STATE_VOTES:
        if not text:
            return
        try:
            votes_val = int(text)
            if votes_val <= 0:
                raise ValueError
        except ValueError:
            bot.reply_to(message, "⚠ أرسل رقماً صحيحاً أكبر من 0.")
            return
        wip = _get_wip(uid)
        wip["end_value"] = votes_val
        wip["end_type"] = "votes"
        _comp_wip[uid] = wip
        db.clear_user_state(uid)
        bot.reply_to(
            message,
            pages.comp_review(wip),
            reply_markup=kb.comp_toggle_panel(
                wip["comp_id"],
                wip.get("win_notification", True),
                wip.get("results_announcement", True),
                wip.get("approval_system", False),
                wip.get("premium_only", False),
            ),
            parse_mode="HTML",
        )
        return

    # ── حالات إدارة المسابقات ────────────────────────────────────────────────
    if state == "comp_chmax":
        if not text:
            return
        try:
            max_val = int(text)
            if max_val < 0:
                raise ValueError
        except ValueError:
            bot.reply_to(message, "⚠ أرسل رقماً صحيحاً (0 = غير محدود).")
            return
        comp_id = state_row["data"]
        comp = db.get_competition(comp_id)
        if comp and comp["creator_id"] == uid:
            db.update_competition(comp_id, max_contestants=max_val)
            # تحديث منشور القناة
            participants = []
            count = 0
            comp = db.get_competition(comp_id)
            remaining = _comp_remaining_seconds(comp)
            try:
                msg_text = pages.format_competition_message(comp, participants, count, remaining)
                bot.edit_message_text(msg_text, comp["chat_id"], comp["message_id"], reply_markup=kb.comp_channel_join_button(comp_id, full=_is_comp_full(comp)), parse_mode="HTML")
            except telebot.apihelper.ApiTelegramException:
                pass
        db.clear_user_state(uid)
        bot.reply_to(
            message,
            f"✅ <b>تم تحديث عدد المقاعد</b>\n{t.divider('▬', 18)}\n\n"
            f"{t.blockquote(f'العدد الجديد: {max_val}')}",
            parse_mode="HTML",
        )
        return

    if state == "comp_rmpart":
        if not text:
            return
        try:
            target_id = int(text.strip())
        except ValueError:
            bot.reply_to(message, "⚠ أرسل آيدي المستخدم الرقمي.")
            return
        comp_id = state_row["data"]
        comp = db.get_competition(comp_id)
        if comp and comp["creator_id"] == uid:
            ok = db.remove_comp_participant(comp_id, target_id)
            ok2 = db.set_application_status(comp_id, target_id, "rejected")
            if ok:
                # تحديث منشور القناة
                participants = []
                count = 0
                comp = db.get_competition(comp_id)
                remaining = _comp_remaining_seconds(comp)
                try:
                    msg_text = pages.format_competition_message(comp, participants, count, remaining)
                    bot.edit_message_text(msg_text, comp["chat_id"], comp["message_id"], reply_markup=kb.comp_channel_join_button(comp_id, full=_is_comp_full(comp)), parse_mode="HTML")
                except telebot.apihelper.ApiTelegramException:
                    pass
                bot.reply_to(
                    message,
                    f"✅ <b>تم إزالة المستخدم</b>\n{t.divider('▬', 18)}\n\n"
                    f"{t.blockquote(f'المستخدم {target_id} تمت إزالته من المسابقة')}",
                    parse_mode="HTML",
                )
            else:
                bot.reply_to(
                    message,
                    f"⚠ <b>لم يتم العثور على المستخدم</b>\n{t.divider('▬', 18)}\n\n"
                    f"{t.blockquote(f'لا يوجد مستخدم بالآيدي {target_id} في المسابقة')}",
                    parse_mode="HTML",
                )
        db.clear_user_state(uid)
        return

    # ── حالات تسجيل القروبات ─────────────────────────────────────────────────
    if state not in ("waiting_group_id", "waiting_channel_id"):
        return

    chat_id = None
    if message.forward_from_chat:
        chat_id = message.forward_from_chat.id
    else:
        m = re.search(r"-?\d{6,}", text)
        if m:
            chat_id = int(m.group())
    if not chat_id:
        bot.reply_to(message, "⚠ لم أجد آيدي صالح. أرسل الآيدي (رقم) أو أعد توجيه رسالة من القروب/القناة.")
        return

    try:
        chat = bot.get_chat(chat_id)
    except telebot.apihelper.ApiTelegramException:
        bot.reply_to(message, "❌ تعذّر الوصول. أضف البوت مشرفاً في القروب أولاً.")
        return

    if state == "waiting_group_id" and chat.type not in ("group", "supergroup"):
        bot.reply_to(message, "❌ هذا ليس قروباً.")
        return
    if state == "waiting_channel_id" and chat.type != "channel":
        bot.reply_to(message, "❌ هذا ليس قناة.")
        return
    if not is_admin(chat_id, message.from_user.id):
        bot.reply_to(message, "❌ يجب أن تكون مشرفاً في القروب.")
        return
    try:
        bot_me = bot.get_me()
        bot_member = bot.get_chat_member(chat_id, bot_me.id)
        if bot_member.status not in ("administrator", "creator"):
            bot.reply_to(message, "❌ ارفع البوت مشرفاً في القروب وصلاحياته كاملة.")
            return
    except telebot.apihelper.ApiTelegramException:
        bot.reply_to(message, "❌ تعذّر التحقق. تأكد من صلاحيات البوت في القروب.")
        return

    db.register_chat(chat_id, chat.title or str(chat_id), chat.type, message.from_user.id)
    db.clear_user_state(message.from_user.id)
    uid = message.from_user.id
    if uid in _reg_from_comp:
        _reg_from_comp.discard(uid)
        chats = db.get_registered_chats(uid)
        bot.reply_to(
            message,
            f"✅ <b>تم تسجيل القروب/القناة!</b>\n\n{pages.comp_select_chat()}",
            reply_markup=kb.comp_chat_picker(chats),
            parse_mode="HTML",
        )
    elif state == "waiting_channel_id":
        code = db.register_log_channel(uid, chat_id, chat.title or str(chat_id))
        bot.reply_to(
            message,
            f"✅ <b>تم التسجيل</b>\n📂 كود السجل: <code>{code}</code>",
            parse_mode="HTML",
        )
    else:
        bot.reply_to(
            message,
            f"✅ <b>تم تسجيل القروب!</b>\n{t.divider('▬', 18)}\n\nاختر عدد المشاركين لبدء السحب:",
            reply_markup=kb.regular_limit_picker(chat_id),
            parse_mode="HTML",
        )
    post_log(uid, "تسجيل", f"{chat.type}: {chat.title}")


def _is_comp_full(comp) -> bool:
    max_c = comp["max_contestants"]
    if max_c <= 0:
        return False
    cur = len(db.get_approved_contestants(comp["comp_id"]))
    return cur >= max_c


def _comp_remaining_seconds(comp) -> int:
    if comp["end_type"] != "time" or comp["status"] != "active":
        return 0
    created = datetime.strptime(comp["created_at"], "%Y-%m-%d %H:%M:%S")
    end_time = created + timedelta(seconds=comp["end_value"])
    remaining = int((end_time - datetime.utcnow()).total_seconds())
    return max(0, remaining)


def finalize_competition(comp_id: str) -> None:
    comp = db.get_competition(comp_id)
    if not comp or comp["status"] != "active":
        return
    db.set_competition_status(comp_id, "ended")
    contestants = db.get_approved_contestants(comp_id)
    comp_title = comp["title"]

    count = len(contestants) if contestants else 0

    if contestants:
        scored = [(c, db.get_vote_count(comp_id, c["user_id"])) for c in contestants]
        scored.sort(key=lambda x: x[1], reverse=True)
        winner, winner_votes = scored[0]

        if comp["results_announcement"]:
            try:
                bot.send_message(
                    comp["chat_id"],
                    pages.comp_results_text(comp_title, scored, winner_votes),
                    parse_mode="HTML",
                )
            except telebot.apihelper.ApiTelegramException:
                pass

        if comp["win_notification"] and winner_votes > 0:
            try:
                bot.send_message(
                    winner["user_id"],
                    pages.comp_winner_text(comp_title, winner_votes),
                    parse_mode="HTML",
                )
            except telebot.apihelper.ApiTelegramException:
                pass

    try:
        bot.edit_message_text(
            pages.comp_ended_message(comp_title, count),
            comp["chat_id"],
            comp["message_id"],
            parse_mode="HTML",
        )
    except telebot.apihelper.ApiTelegramException:
        pass


def competition_timer_loop() -> None:
    while True:
        try:
            comps = db.get_all_active_competitions()
            for comp in comps:
                if comp["end_type"] == "time":
                    remaining = _comp_remaining_seconds(comp)
                    if remaining <= 0:
                        finalize_competition(comp["comp_id"])
                    else:
                        count = db.count_comp_participants(comp["comp_id"])
                        msg = pages.format_competition_message(comp, [], count, remaining)
                        try:
                            bot.edit_message_text(msg, comp["chat_id"], comp["message_id"], reply_markup=kb.comp_channel_join_button(comp["comp_id"], full=_is_comp_full(comp)), parse_mode="HTML")
                        except telebot.apihelper.ApiTelegramException:
                            pass
        except Exception:
            pass
        time.sleep(5)



def giveaway_timer_loop() -> None:
    while True:
        try:
            raffles = db.get_all_active_raffles()
            import time
            now = int(time.time())
            for r in raffles:
                raffle = dict(r)
                if raffle.get("auto_draw") and raffle.get("auto_draw_type") == "time":
                    end_time = raffle.get("end_time")
                    if end_time and now >= end_time:
                        raffle_id = raffle["raffle_id"]
                        
                        # Stop raffle and draw winners
                        db.update_raffle(raffle_id, status="completed")
                        winners_count = raffle.get("winners_count", 1)
                        participants = db.get_participants(raffle_id)
                        
                        if participants:
                            import random
                            winners = random.sample(participants, min(winners_count, len(participants)))
                            winners_text = "\n".join([f"🏆 <a href='tg://user?id={w['user_id']}'>{w['first_name']}</a>" for w in winners])
                            text = f"<b>انتهى السحب! (الوقت انتهى)</b>\n\nالفائزون:\n{winners_text}"
                        else:
                            text = "<b>انتهى السحب! (الوقت انتهى)</b>\n\nلا يوجد مشاركين."
                            
                        try:
                            bot.edit_message_text(
                                text,
                                raffle["chat_id"],
                                raffle["message_id"],
                                parse_mode="HTML"
                            )
                        except telebot.apihelper.ApiTelegramException:
                            pass
        except Exception as e:
            logger.error(f"Error in giveaway_timer_loop: {e}")
            pass
        time.sleep(10)


def run_polling() -> None:
    logger.info("روليت غزاوي v2 يعمل...")
    bot.infinity_polling(
        skip_pending=True,
        timeout=60,
        long_polling_timeout=60,
        allowed_updates=["message", "callback_query", "inline_query", "chosen_inline_result", "channel_post"],
    )


def start_dummy_server():
    import os
    import http.server
    import socketserver
    port = int(os.environ.get("PORT", 8080))
    Handler = http.server.SimpleHTTPRequestHandler
    try:
        with socketserver.TCPServer(("", port), Handler) as httpd:
            logger.info(f"Dummy server serving at port {port}")
            httpd.serve_forever()
    except Exception as e:
        logger.error(f"Dummy server error: {e}")

if __name__ == "__main__":
    if BOT_TOKEN == "ضع_توكن_البوت_هنا":
        print("⚠ ضع التوكن في config.py")
    
    # Start dummy web server for Render / Heroku to keep the bot alive
    threading.Thread(target=start_dummy_server, daemon=True).start()
    
    threading.Thread(target=competition_timer_loop, daemon=True).start()
    threading.Thread(target=giveaway_timer_loop, daemon=True).start()

    run_polling()
