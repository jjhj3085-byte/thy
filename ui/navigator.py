"""عرض الصفحات نصوص فقط — بدون بانرات."""

import logging

import telebot
from telebot import types

logger = logging.getLogger(__name__)


def send_page(
    bot: telebot.TeleBot,
    chat_id: int,
    page: str,
    caption: str,
    markup: types.InlineKeyboardMarkup | None = None,
) -> types.Message:
    return bot.send_message(
        chat_id,
        caption,
        reply_markup=markup,
        parse_mode="HTML",
        disable_web_page_preview=True,
    )


def edit_page(
    bot: telebot.TeleBot,
    chat_id: int,
    message_id: int,
    page: str,
    caption: str,
    markup: types.InlineKeyboardMarkup | None = None,
) -> None:
    # أولاً: نحاول تعديل كرسالة نصية
    try:
        bot.edit_message_text(
            caption,
            chat_id,
            message_id,
            reply_markup=markup,
            parse_mode="HTML",
            disable_web_page_preview=True,
        )
        return  # نجحت — خلص
    except telebot.apihelper.ApiTelegramException as exc:
        msg = str(exc).lower()
        if "message is not modified" in msg:
            return  # نفس المحتوى — تجاهل

    # إذا فشلت (الرسالة القديمة كانت صورة)، نحاول تعديل الكابشن
    try:
        bot.edit_message_caption(
            caption,
            chat_id,
            message_id,
            reply_markup=markup,
            parse_mode="HTML",
        )
        return  # نجحت
    except telebot.apihelper.ApiTelegramException as exc:
        msg = str(exc).lower()
        if "message is not modified" in msg:
            return

    # كل المحاولات فشلت — نحذف الرسالة القديمة ونرسل جديدة
    try:
        bot.delete_message(chat_id, message_id)
    except Exception:
        pass  # حتى لو فشل الحذف، نرسل رسالة جديدة
    try:
        bot.send_message(
            chat_id,
            caption,
            reply_markup=markup,
            parse_mode="HTML",
            disable_web_page_preview=True,
        )
    except Exception as e:
        logger.error("edit_page: failed to send fallback message: %s", e)
