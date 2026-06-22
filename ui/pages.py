"""نصوص الصفحات الغنية — HTML + مميزات لكل قسم."""

from ui import theme as t
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import PROMO_FOOTER_RAFFLE, PROMO_FOOTER_COMP


def welcome(user_stats: dict, name: str = "", user_id: int = 0) -> str:
    user_link = f'<a href="tg://user?id={user_id}">{name}</a>' if user_id else name
    return (
        f"👋 : أهلاً بك - {user_link}\n\n"
        f"<blockquote><b> • روليت غزاوي لـ انشاء السحوبات والمسابقات والروليت السريع\n"
        f" • استمتع وابدأ الآن بالاختيار من القائمة أدناه 👇</b></blockquote>"
    )


def quick_board_text() -> str:
    return (
        f"<b>🎰 𝗥𝗢𝗨𝗟𝗘𝗧𝗧𝗘 𝗕𝗢𝗔𝗥𝗗</b>\n"
        f"{t.divider('▬', 18)}\n\n"
        f"<b>🎯 اختر عدد المشاركين:</b>\n"
        f"<blockquote>‹ اضغط على عدد للانضمام التلقائي ›</blockquote>\n\n"
        f"<i>⚡ يتم إنشاء الروليت + انضمامك فوراً</i>"
    )


def quick_roulette() -> str:
    return (
        f"<b>🎰 قسم إنشاء لعبة روليت</b>\n\n"
        f"انشاء روليت : انشاء لعبه روليت\n"
        f"الاعدادات : تحكم في اعدادة اللعبه\n\n"
        f"<blockquote>❞ • اختر ماتريد من الازرار ادناه ⇊</blockquote>"
    )

def quick_settings_page(hide_participants: bool, custom_message: str) -> str:
    visibility = "مخفي" if hide_participants else "ظاهر"
    return (
        f"<b>⚙️ الإعدادات والخصوصية</b>\n\n"
        f"اسماء المشاركين : {visibility}\n"
        f"كليشة اللعبه : {custom_message}\n\n"
        f"يمكنك التحكم في ظهور و اخفاء اسماء المشاركين في كليشه اللعبه الرسميه\n"
        f"<blockquote>❞ يمكنك اضافه كليشه للعبه 🆕</blockquote>"
    )

def custom_message_input_page(current_message: str) -> str:
    return (
        f"<b>✍️ أرسل كليشة اللعبة</b>\n\n"
        f"اكتب نص السحب الذي تريد نشره في القناة.\n"
        f"يمكنك استخدام تنسيقات تيليجرام، مثل:\n"
        f"• <b>نص عريض</b>\n"
        f"• <i>نص مائل</i>\n"
        f"- يمكنك وضع رابط داخل النص\n"
        f"<blockquote>❞ نص مقتبس</blockquote>\n\n"
        f"النص الحالي:\n"
        f"<blockquote>❞ {current_message}</blockquote>"
    )


def quick_settings(limit: int, hide_participants: bool, hide_buttons: bool, old_only: bool) -> str:
    parts = f"<b>🔧 إعدادات الروليت السريع</b>\n{t.divider('▬', 18)}\n\n"
    parts += (
        f"<b>👥 حد المشاركين:</b> <code>{limit}</code>\n"
        f"<b>🕵️ إخفاء الأسماء:</b> <code>{'مفعل ✅' if hide_participants else 'معطل ❌'}</code>\n"
        f"<b>🔘 إخفاء الأزرار:</b> <code>{'مفعل ✅' if hide_buttons else 'معطل ❌'}</code>\n"
        f"<b>👴 الأعضاء القدامى فقط:</b> <code>{'مفعل ✅' if old_only else 'معطل ❌'}</code>\n\n"
        f"{t.divider('▬', 18)}\n"
        f"<i>⚡ غيّر الإعدادات من الأزرار أدناه</i>"
    )
    return parts


def create_roulette() -> str:
    return (
        f"قسم إنشاء السحوبات 📢\n\n"
        f"اختر ما تريد:"
    )


def giveaway_select_chat() -> str:
    return (
        f"يرجى تحديد القناة أو القروب للسحب.\n\n"
        f"<blockquote>❞ تأكد أولا انك مشرف في القناة او القروب وان البوت أيضا مشرف\n"
        f"إذا لم تظهر القناة أو الجروب وتأكدت ان البوت بها كمشرف وأنت كمشرف إذا يمكنك تسجيله يدويا من الأسفل ⬇️</blockquote>"
    )


def giveaway_input_text() -> str:
    return (
        f"أرسل كليشة السحب 📩\n\n"
        f"اكتب نص السحب الذي تريد نشره في القناة.\n"
        f"يمكنك استخدام تنسيقات تيليجرام، مثل:\n"
        f"• <b>نص عريض</b>\n"
        f"• <i>نص مائل</i>\n\n"
        f"<code>يمكنك وضع رابط داخل النص</code> 🆕\n"
        f"<blockquote>❞ نص مقتبس</blockquote>"
    )


def giveaway_input_winners() -> str:
    return (
        f"عدد الفائزين 👥\n\n"
        f"أرسل عدد الفائزين المطلوب:"
    )


def giveaway_settings_panel() -> str:
    return (
        f"اعدادات السحب 🎯\n\n"
        f"<blockquote>❞ اختر شرطًا لتحسين السحب:</blockquote>\n\n"
        f"<b>1</b> قناة شرط: الاشتراك بقناة محددة\n"
        f"<b>2</b> تعزيز القناة: تعزيز قناتك\n"
        f"<b>3</b> تصويت: التصويت لمتسابق\n"
        f"<b>4</b> مشتركين مميزين: لـ مشتركين تلجرام (المميز)\n"
        f"<b>5</b> منع الرشق: منع الرشق في السحب\n"
        f"<b>6</b> سحب تلقائي: يسحب تلقائيا عند اكتمال العدد\nالمعين أو عند انتهاء الوقت المعين\n\n"
        f"<blockquote>❞ اختر الشرط الذي تريده من الأزرار أدناه 👇</blockquote>"
    )


def giveaway_published_success() -> str:
    return "تم نشر السحب بنجاح! ✅"


def condition_channel_select() -> str:
    return (
        f"🔒 قناة الشرط\n\n"
        f"اختر نوع قناة الشرط:"
    )


def condition_channel_private() -> str:
    return (
        f"🔒 قناة الشرط الخاصة\n\n"
        f"وجه (Forward) أي رسالة من القناة الخاصة إلى هنا\n\n"
        f"<blockquote>❝ تأكد من إضافة البوت كمشرف في القناة مع صلاحية دعوة المستخدمين ❞</blockquote>"
    )


def condition_channel_public() -> str:
    return (
        f"🌐 قناة الشرط العامة\n\n"
        f"الان ارسل لي يوزر قناة الشرط\n"
        f"مثال @YYYLLY\n\n"
        f"لا تضف أي نص إضافي مع اليوزر\n\n"
        f"تأكد من إضافة البوت كمشرف في قناة الشرط مع صلاحية إدارة الأعضاء\n\n"
        f"<blockquote>❝ يمكنك إضافة قناتين كحد أقصى، ويتم إدخال الأسماء بهذا الشكل:\n"
        f"@YYYLLY\n@YY3HH ❞</blockquote>"
    )


def vote_contestant_code() -> str:
    return (
        f"🌐 كود التصويت للمتسابق\n\n"
        f"✨ أرسل كود المتسابق الخاص بك (يبدأ بـ C) ليتم التحقق من تصويتك قبل المشاركة في السحب.\n\n"
        f"🔗 مثال على الكود: <code>C12345678</code>\n\n"
        f"✅ بعد إرسال الكود، سيقوم البوت بالتحقق تلقائياً من تصويت المشاركين\n\n"
        f"<blockquote>❝ 🔗 مثال على الكود: <code>C12345678</code> ❞</blockquote>"
    )


def auto_draw_select_method() -> str:
    return (
        f"اختر طريقة انتهاء السحب\n\n"
        f"<blockquote>❝ 🔴• عدد محدد : ينتهي السحب تلقائياً عند وصول عدد المشاركين إلى الرقم الذي تحدده 🏆 ❞</blockquote>\n\n"
        f"<blockquote>❝ 🔴• وقت محدد : ينتهي السحب عند انتهاء الوقت الذي تحدده ويتم اختيار الفائزين 🏆 ❞</blockquote>"
    )


def auto_draw_count() -> str:
    return (
        f"🔴 السحب التلقائي لـ عدد محدد\n\n"
        f"أرسل عدد المشاركين المطلوب لبدء السحب تلقائياً\n\n"
        f"<blockquote>❝ مثال: إذا أردت تفعيل السحب التلقائي عند وصول عدد المشاركين إلى 100\n"
        f"أرسل الرقم 100 ❞</blockquote>"
    )


def auto_draw_time(selected: str = "غير محدد") -> str:
    return (
        f"🔴 السحب التلقائي لـ وقت محدود\n\n"
        f"الوقت المختار: {selected}\n\n"
        f"استخدم الأزرار أدناه لتحديد الوقت المطلوب لبدء السحب تلقائياً:"
    )


def link_channel_group() -> str:
    return (
        f"ربط قناة أو مجموعة 📎\n\n"
        f"اختر نوع ما تريد ربطه:"
    )


def delete_channel_group() -> str:
    return (
        f"حذف قناة أو مجموعة 🗑\n\n"
        f"اضغط على 🗑 لحذف:"
    )



def competition() -> str:
    return (
        f"• <b>قسم إنشاء المسابقات</b>\n\n"
        f"اختر ما تريد:"
    )


def comp_select_chat() -> str:
    return (
        f"📢 <b>اختر المجموعة أو القناة</b>\n"
        f"{t.divider('▬', 18)}\n\n"
        f"{t.blockquote('اختر مكان نشر المسابقة من القائمة أدناه')}"
    )


def comp_input_title() -> str:
    return (
        f"📝 <b>أرسل نص المسابقة</b>\n"
        f"{t.divider('▬', 18)}\n\n"
        f"{t.blockquote('اكتب النص الذي تريد ظهوره في المسابقة')}\n\n"
        f"<b>الخطوط المتاحة:</b>\n"
        f"• <code>**عريض**</code> → <b>عريض</b>\n"
        f"• <code>__مائل__</code> → <i>مائل</i>\n"
        f"• <code>~~يتوسطه خط~~</code> → <s>يتوسطه خط</s>\n"
        f"• <code>||مخفي||</code> → <tg-spoiler>مخفي</tg-spoiler>\n"
        f"• <code>`كود`</code> → <code>كود</code>\n"
        f"• <code>```كتلة كود```</code> ← كتلة كود\n"
        f"• <code>> اقتباس</code> ← <blockquote>اقتباس</blockquote>\n"
        f"• <code>>>> اقتباس متعدد</code> ← <blockquote expandable>اقتباس متعدد</blockquote>\n"
        f"• <code>• نقطة</code> ← • نقطة\n"
        f"• <code>◦ نقطة فرعية</code> ← ◦ نقطة فرعية"
    )


def comp_input_max() -> str:
    return (
        f"👥 <b>عدد المشاركين المسموح</b>\n"
        f"{t.divider('▬', 18)}\n\n"
        f"{t.blockquote('أرسل الرقم الأقصى للمشاركين (0 = غير محدود)')}"
    )


def comp_select_end() -> str:
    return (
        f"⏰ <b>نوع إنهاء المسابقة</b>\n"
        f"{t.divider('▬', 18)}\n\n"
        f"{t.blockquote('اختر كيف تنتهي المسابقة')}"
    )


def comp_input_votes() -> str:
    return (
        f"📊 <b>عدد الأصوات المطلوب</b>\n"
        f"{t.divider('▬', 18)}\n\n"
        f"{t.blockquote('أرسل عدد الأصوات التي يحتاجها الفائز')}"
    )


def comp_input_duration() -> str:
    return (
        f"⏱ <b>اختر مدة المسابقة</b>\n"
        f"{t.divider('▬', 18)}\n\n"
        f"{t.blockquote('اختر المدة الزمنية للمسابقة من الأزرار أدناه')}\n\n"
        f"يمكنك اختيار المدة المناسبة لمسابقتك 👇"
    )


def comp_review(comp) -> str:
    end_type_txt = "⏰ وقت" if comp["end_type"] == "time" else "📊 أصوات"
    end_val_txt = (
        f"{comp['end_value']} ثانية" if comp["end_type"] == "time"
        else f"{comp['end_value']} صوت"
    )
    max_txt = str(comp["max_contestants"]) if comp["max_contestants"] > 0 else "غير محدود"
    lines = [
        f"📋 <b>مراجعة المسابقة</b>\n{t.divider('▬', 18)}",
        f"<b>النص:</b>\n{comp['title']}\n",
        f"<b>الحد الأقصى:</b> {max_txt}",
        f"<b>النهاية:</b> {end_type_txt} ({end_val_txt})",
        f"<b>تنبيه الفوز:</b> {'✅' if comp['win_notification'] else '❌'}",
        f"<b>إعلان النتائج:</b> {'✅' if comp['results_announcement'] else '❌'}",
        f"<b>موافقة المشاركات:</b> {'✅' if comp['approval_system'] else '❌'}",
        f"<b>تصويت بريميوم:</b> {'✅' if comp['premium_only'] else '❌'}",
    ]
    return "\n".join(lines)


def comp_manage_title(count: int) -> str:
    icon = "🆕" if count > 0 else "📭"
    return (
        f"{icon} <b>المسابقات الحديثة</b>\n"
        f"{t.divider('▬', 18)}\n\n"
        f"{t.badge('نشطة', str(count))}\n"
        f"{t.blockquote('اختر مسابقة للتحكم بها من القائمة أدناه')}"
    )


def comp_manage_contest(comp, participants_count: int, chat_name: str = "") -> str:
    chat_name = chat_name or str(comp["chat_id"])
    status_icon = "🟢" if comp["status"] == "active" else "🔴"
    max_txt = str(comp["max_contestants"]) if comp["max_contestants"] > 0 else "غير محدود"
    chat_id_positive = abs(comp["chat_id"])
    has_link = comp["message_id"] is not None
    lines = [
        f"<b>لوحة التحكم</b>\n{t.divider('▬', 18)}",
        f"<blockquote>",
        f"<b>العنوان:</b> {comp['title']}",
        f"<b>القناة:</b> {chat_name}",
    ]
    if has_link:
        post_link = f"https://t.me/c/{chat_id_positive}/{comp['message_id']}"
        lines.append(f"<b>الرابط:</b> <a href='{post_link}'>فتح المنشور</a>")
    else:
        lines.append("<b>الرابط:</b> —")
    lines += [
        f"<b>الحالة:</b> {status_icon} {comp['status']}",
        f"<b>المشاركون:</b> {participants_count}/{max_txt}",
        f"</blockquote>",
        f"\n<b>⚙️ الإعدادات:</b>",
        f"• <b>تنبيه الفوز:</b> {'✅' if comp['win_notification'] else '❌'}",
        f"• <b>إعلان النتائج:</b> {'✅' if comp['results_announcement'] else '❌'}",
        f"• <b>موافقة المشاركات:</b> {'✅' if comp['approval_system'] else '❌'}",
        f"• <b>تصويت بريميوم:</b> {'✅' if comp['premium_only'] else '❌'}",
    ]
    return "\n".join(lines)


def comp_confirm_message(contest_title: str, user_display: str) -> str:
    return (
        f"🎯 <b>تأكيد المشاركة في المسابقة</b>\n"
        f"{t.divider('▬', 18)}\n\n"
        f"تريد المشاركة في المسابقة <b>{contest_title}</b>\n"
        f"باسم: <b>{user_display}</b>\n\n"
        f"هل أنت متأكد؟"
    )


def comp_pending_message() -> str:
    return (
        f"⏳ <b>طلبك قيد المراجعة</b>\n"
        f"{t.divider('▬', 18)}\n\n"
        f"{t.blockquote('طلبك قيد المراجعة حالياً من قبل الإدارة. سيتم إشعارك فور قبول مشاركتك.')}"
    )


def comp_approved_message(contest_title: str) -> str:
    return (
        f"✅ <b>تم قبول مشاركتك!</b>\n"
        f"{t.divider('▬', 18)}\n\n"
        f"{t.blockquote(f'تم قبولك في المسابقة: {contest_title}')}"
        f"\n\n<i>تم إنشاء بطاقة التصويت الخاصة بك في القناة ✅</i>"
    )


def comp_rejected_message(contest_title: str) -> str:
    return (
        f"❌ <b>عذراً، تم رفض طلبك</b>\n"
        f"{t.divider('▬', 18)}\n\n"
        f"{t.blockquote(f'لم يتم قبولك في المسابقة: {contest_title}')}"
        f"\n\n<i>يمكنك التقديم لمسابقة أخرى من القائمة الرئيسية</i>"
    )


def comp_voting_card_text(display_name: str, premium_only: bool = False) -> str:
    lines = [
        f"🏅 <b>بطاقة متسابق</b>\n{t.divider('▬', 18)}\n",
        f"<b>المتسابق:</b> {display_name}\n",
        f"<b>الحالة:</b> 🟢 نشط\n",
    ]
    if premium_only:
        lines.append(f"\n{t.blockquote('💎 التصويت متاح فقط للمشتركين المميزين')}\n")
    lines.append(f"\n{t.blockquote(f'❤️ اضغط على زر التصويت للتصويت لهذا المتسابق')}")
    return "".join(lines)


def comp_admin_notify(user_display: str, uid: int, comp_title: str, comp_id: str) -> str:
    return (
        f"📩 <b>طلب انضمام جديد</b>\n{t.divider('▬', 18)}\n\n"
        f"{t.blockquote(f'يوجد طلب انضمام للمسابقة، يرجى المراجعة')}\n\n"
        f"👤 <b>المستخدم:</b> {user_display}\n"
        f"🆔 <b>الآيدي:</b> <code>{uid}</code>\n"
        f"🏆 <b>المسابقة:</b> {comp_title}\n"
        f"🔖 <b>الرمز:</b> <code>{comp_id}</code>\n\n"
        f"{t.divider('▬', 18)}\n"
        f"<i>اختر قبول أو رفض من الأزرار أدناه 👇</i>"
    )


def comp_results_text(comp_title: str, scored: list, winner_votes: int) -> str:
    lines = [
        f"🏁 <b>انتهت المسابقة!</b>\n{t.divider('▬', 18)}\n",
        f"{comp_title}\n",
        f"{t.blockquote('النتائج النهائية للمسابقة 👇')}\n",
    ]
    for c, v in scored:
        name = c["first_name"] or c["username"] or str(c["user_id"])
        crown = "👑 " if v == winner_votes and v > 0 else ""
        vote_display = f"{v} صوت" if v != 1 else "1 صوت"
        if v == winner_votes and v > 0:
            lines.append(f"{crown}<b>{name}</b> — 🗳 {vote_display} 🏆")
        else:
            lines.append(f"{crown}<b>{name}</b> — 🗳 {vote_display}")
    lines.append(f"\n{t.divider('▬', 14)}\n<i>شكراً لجميع المشاركين</i>")
    return "\n".join(lines)


def comp_winner_text(comp_title: str, winner_votes: int) -> str:
    return (
        f"🎉 <b>مبروك! أنت الفائز!</b>\n{t.divider('▬', 18)}\n\n"
        f"{t.blockquote(f'لقد فزت في المسابقة:')}\n\n"
        f"🏆 <b>المسابقة:</b> {comp_title}\n"
        f"🗳 <b>الأصوات:</b> {winner_votes}\n\n"
        f"تهانينا! 🎊"
    )


def comp_ended_message(comp_title: str, count: int) -> str:
    return (
        f"🏁 <b>انتهت المسابقة</b>\n{t.divider('▬', 18)}\n\n"
        f"{t.blockquote(comp_title)}\n\n"
        f"👥 <b>عدد المشاركين:</b> {count}\n"
        f"📊 <b>الحالة:</b> منتهية ✅\n\n"
        f"<i>شكراً لجميع المشاركين</i>"
    )


def _format_timer(seconds: int) -> str:
    if seconds <= 0:
        return ""
    days = seconds // 86400
    hours = (seconds % 86400) // 3600
    mins = (seconds % 3600) // 60
    secs = seconds % 60
    if days > 0:
        return f"⏳ {days}ي {hours:02d}:{mins:02d}:{secs:02d}"
    if hours > 0:
        return f"⏳ {hours:02d}:{mins:02d}:{secs:02d}"
    return f"⏳ {mins:02d}:{secs:02d}"


def format_competition_message(comp, participants: list, count: int, remaining: int | None = None) -> str:
    max_txt = str(comp["max_contestants"]) if comp["max_contestants"] > 0 else "غير محدود"
    status_icon = "🟢" if comp["status"] == "active" else "🔴"
    status_txt = "نشطة" if comp["status"] == "active" else ("موقفة" if comp["status"] == "paused" else "منتهية")
    lines = [
        f"🏆 <b>مسابقة جديدة!</b>\n{t.divider('▬', 18)}\n",
        f"{t.blockquote(comp['title'])}\n",
    ]
    if remaining is not None and remaining > 0 and comp["end_type"] == "time":
        lines.append(f"⏳ <b>الوقت المتبقي:</b> {_format_timer(remaining)}\n")
    elif comp["end_type"] == "votes":
        lines.append(f"📊 <b>النهاية عند:</b> {comp['end_value']} صوت\n")
    lines.append(f"👥 <b>المقاعد:</b> {count}/{max_txt}")
    lines.append(f"\n📌 <b>الحالة:</b> {status_icon} {status_txt}")
    lines.append(f"\n\n<blockquote>{PROMO_FOOTER_COMP}</blockquote>")
    return "\n".join(lines)


def my_raffles_header(count: int) -> str:
    features = t.feature_list([
        "إيقاف السحب فوراً",
        "تصدير قائمة المشاركين",
        "نسخ السحب بإعدادات جديدة",
        "Toggle لكل خيار بضغطة",
    ])
    return (
        f"📋 <b>سحوباتي</b>\n"
        f"{t.badge('نشطة', str(count))}\n"
        f"{t.blockquote('اختر سحباً للتحكم الكامل بإعداداته.')}\n"
        f"{t.section('مميزات اللوحة', features)}"
    )


def raffle_control(raffle_id: str, count: int, limit: int) -> str:
    actions = t.feature_list([
        "إعادة نشر · إخفاء العدد · إخفاء الأزرار",
        "قفل الأعضاء القدامى · تصدير · إيقاف",
    ])
    return (
        f"🎛 <b>لوحة تحكم السحب</b>\n"
        f"{t.badge('الكود', raffle_id)}\n"
        f"{t.progress_bar(count, limit)}\n"
        f"{t.section('إجراءات سريعة', actions)}"
    )


def channel_log(count: int) -> str:
    features = t.feature_list([
        "كود فريد لكل قناة",
        "سجل زمني للعمليات",
        "ربط متعدد للقنوات",
        "تنبيهات للمالك فقط",
    ])
    return (
        f"📂 <b>قناة السجل</b>\n"
        f"{t.badge('قنوات مربوطة', str(count))}\n"
        f"{t.blockquote('توثيق تلقائي: إنشاء · إيقاف · فوز · استبعاد')}\n"
        f"{t.section('مميزات', features)}"
    )


def statistics(stats: dict, top_channels: list) -> str:
    medals = ["🥇", "🥈", "🥉", "🏅", "🏅"]
    channel_lines = []
    for i, ch in enumerate(top_channels[:5], 1):
        title = ch["title"] or "قناة"
        total = ch["total"]
        medal = medals[i - 1] if i <= 5 else "🏅"
        channel_lines.append(f"{medal} <b>{title}</b> — {total} مشاركة")
    top_block = "\n".join(channel_lines) if channel_lines else "لا توجد بيانات بعد."
    return (
        f"📊 <b>إحصائياتي في {t.BRAND}</b>\n"
        f"{t.divider('▬', 18)}\n"
        f"<blockquote>🎯 سحوبات أنشأتها: <b>{stats.get('created', 0)}</b>\n"
        f"✍️ مشاركاتي: <b>{stats.get('joined', 0)}</b>\n"
        f"🏆 مرات الفوز: <b>{stats.get('wins', 0)}</b>\n"
        f"⚡ XP: <b>{stats.get('xp', 0)}</b> · {t.level_badge(stats.get('xp', 0))}</blockquote>\n"
        f"{t.divider('▬', 18)}\n"
        f"<b>🌟 أعلى القنوات نشاطاً</b>\n"
        f"{top_block}"
    )


def privacy() -> str:
    data = t.feature_list([
        "نخزن المعرف واسم العرض فقط",
        "لا نبيع أو نشارك بياناتك",
        "يمكنك طلب حذف بياناتك من الدعم",
    ])
    rules = t.feature_list([
        "1. احترام خصوصيتك أولوية",
        "2. لا جمع لرسائلك الخاصة",
        "3. تخزين محلي آمن",
        "4. إيقاف الخدمة = حذف تلقائي دوري",
        "5. cookies غير مستخدمة",
        "6. تواصل: الدعم الفني",
    ])
    return (
        f"🔒 <b>سياسة الخصوصية</b>\n"
        f"{t.section('البيانات', data)}"
        f"\n{t.section('البنود', rules)}"
    )


def terms() -> str:
    return (
        f"<b>📜 : سياسة الاستخدام والخصوصية</b>\n\n"
        f"ثقتكم هي أولويتنا\n\n"
        f"<b>✅ : المسموح به:</b>\n"
        f"├ تنظيم سحوبات حقيقية وواضحة\n"
        f"├ تقديم جوائز حقيقية وموثوقة\n"
        f"└ احترام جميع المشاركين\n\n"
        f"<b>❌ : الممنوع:</b>\n"
        f"├ سحوبات وهمية أو مضللة\n"
        f"├ خداع المستخدمين\n"
        f"└ التلاعب بالنتائج\n\n"
        f"<blockquote>❞ 🚨 : أي مخالفة = حظر دائم\n"
        f"ثقتكم هي أولويتنا</blockquote>"
    )


def leaderboard(rows: list) -> str:
    lines = []
    medals = ["🥇", "🥈", "🥉"]
    for i, row in enumerate(rows[:15], 1):
        medal = medals[i - 1] if i <= 3 else f"{i}."
        name = row["first_name"] or row["username"] or str(row["user_id"])
        lines.append(f"{medal} {name} — <b>{row['wins']}</b> فوز · XP {row['xp']}")
    body = "\n".join(lines) if lines else "لا يوجد متصدرون بعد."
    return (
        f"🏅 <b>لوحة الشرف</b>\n"
        f"{t.blockquote('أكثر الفائزين في روليت غزاوي')}\n"
        f"{t.section('Top 15', body)}"
    )


def profile(stats: dict, remind: bool) -> str:
    remind_txt = "مفعّل ✅" if remind else "معطّل ❌"
    achievements = t.feature_list([
        f"XP: <b>{stats['xp']}</b> · {t.level_badge(stats['xp'])}",
        f"🏆 فوز: <b>{stats['wins']}</b>",
        f"🎯 أنشأت: <b>{stats['created']}</b> سحب",
        f"✍️ مشاركات: <b>{stats['joined']}</b>",
    ])
    settings = t.feature_list([f"تذكير الفوز: <b>{remind_txt}</b>"])
    return (
        f"👤 <b>ملفي الشخصي</b>\n"
        f"{t.section('الإنجازات', achievements)}"
        f"\n{t.section('الإعدادات', settings)}"
    )


def register_group(bot_username: str) -> str:
    return (
        f"ربط جروب 👥\n\n"
        f"لـ اضافة جروب اتبع الخطوات التالية:\n\n"
        f"❶ أضف البوت @GazawiRbot كمشرف في الجروب الخاص بك.\n\n"
        f"❷ إذهب للجروب الخاص بك بعد إضافة البوت و اكتب ⇐ تفعيل روليت"
    )


def register_channel(bot_username: str) -> str:
    return (
        f"ربط قناة 🌐\n\n"
        f"لـ اضافة قناة اتبع الخطوات التالية:\n\n"
        f"❶ أضف البوت @{bot_username} كمشرف في قناتك.\n\n"
        f"❷ قم بإعادة توجيه أي رسالة من قناتك إلى البوت\n\n"
        f"ملاحظة: 📌\n"
        f"<blockquote>❞ جميع المشرفين الآخرين في القناة سيتمكنون أيضًا من استخدام البوت بعد إضافته.</blockquote>"
    )





def format_quick_raffle_message(
    count: int, limit: int, participants: list, hide_participants: bool = False, custom_message: str = "• مرحبا بكم في لعبه روليت 👑"
) -> str:
    bar = t.progress_bar(count, limit, width=14)
    lines = [
        f"{custom_message}",
        f"\n👥 {bar}",
    ]
    if not hide_participants and participants:
        names = []
        for i, p in enumerate(participants[:20], 1):
            name = p["first_name"] or p["username"] or str(p["user_id"])
            names.append(f"{i}. {name}")
        extra = len(participants) - 20
        if extra > 0:
            names.append(f"<i>+{extra} آخرين</i>")
        lines.append("<b>المشاركون:</b>\n" + "\n".join(names))
    lines.append("\n<blockquote>❞ 🔗 بواسطة: <a href=\"https://t.me/GazawiRbot\">روليت غزاوي</a></blockquote>")
    return "\n".join(lines)


def format_spin_message(step: int, count: int) -> str:
    frame = t.spin_frame(step)
    return (
        f"<b>{frame} جاري دوران الروليت...</b>\n\n"
        f"👥 مشاركون: <b>{count}</b>\n"
        f"<i>حظاً موفقاً للجميع!</i>"
    )


def format_winner_message(winner_name: str, raffle_id: str = "") -> str:
    extra = f"\n<code>{raffle_id}</code>" if raffle_id else ""
    return (
        f"🎉 <b>تم اكتمال السحب!</b>\n\n"
        f"{t.winner_crown(winner_name)}"
        f"\n<i>بواسطة {t.BRAND}</i>{extra}"
    )


def format_new_participant_dm(name: str, user_id: int, raffle_id: str) -> str:
    return (
        f"🆕 <b>مشاركة جديدة في سحبك</b>\n"
        f"{t.badge('السحب', raffle_id)}\n"
        f"👤 <b>{name}</b>\n"
        f"🆔 <code>{user_id}</code>"
    )


def format_log_event(event: str, detail: str) -> str:
    return f"📋 <b>سجل</b> · {event}\n{detail}\n<i>{t.BRAND}</i>"


# ─── مميزات إضافية ─────────────────────────────────────────────────────────────


def help_page() -> str:
    """صفحة المساعدة الشاملة."""
    commands = t.feature_list([
        "/start — بدء البوت والقائمة الرئيسية",
        "/profile — ملفك الشخصي وإحصائياتك",
        "/stats — عرض إحصائياتك",
        "/groupid — معرفة آيدي القروب",
    ])
    features = t.feature_list([
        "🎡 روليت سريع — سحب فوري عبر الإنلاين",
        "🐥 إنشاء سحب — سحب مخصص بإعدادات كاملة",
        "🏆 مسابقات — قوالب جاهزة للمسابقات",
        "📂 قناة السجل — توثيق تلقائي لكل العمليات",
        "📊 إحصائيات — تتبع نشاطك ومراتبك",
        "✅ تذكير الفوز — إشعار فوري عند الفوز",
        "⬇ تصدير — تنزيل قائمة المشاركين",
        "⎘ نسخ السحب — استنساخ بإعدادات جديدة",
    ])
    return (
        f"❓ <b>المساعدة والإرشادات</b>\n"
        f"{t.section('الأوامر المتاحة', commands)}"
        f"\n{t.section('مميزات البوت', features)}"
    )


def broadcast_confirm(count: int) -> str:
    """تأكيد إرسال رسالة جماعية (للمالك فقط)."""
    return (
        f"📢 <b>بث جماعي</b>\n\n"
        f"سيتم الإرسال إلى <b>{count}</b> مستخدم.\n"
        f"{t.blockquote('اكتب الرسالة التي تريد إرسالها للجميع.')}"
    )


def user_banned_page(reason: str = "") -> str:
    """صفحة حظر المستخدم."""
    reason_text = f"\nالسبب: <i>{reason}</i>" if reason else ""
    return (
        f"🚫 <b>تم حظرك من استخدام البوت</b>{reason_text}\n\n"
        f"{t.blockquote('إذا كنت تعتقد أن هذا خطأ، تواصل مع الدعم الفني.')}"
    )


def raffle_expired_page(raffle_id: str) -> str:
    """صفحة انتهاء صلاحية السحب."""
    return (
        f"⏰ <b>انتهت صلاحية السحب</b>\n"
        f"{t.badge('الكود', raffle_id)}\n\n"
        f"{t.blockquote('هذا السحب لم يعد نشطاً. أنشئ سحباً جديداً من القائمة الرئيسية.')}"
    )


def share_bot_page(bot_username: str) -> str:
    """صفحة مشاركة البوت."""
    return (
        f"📤 <b>شارك البوت مع أصدقائك!</b>\n\n"
        f"🔗 الرابط: https://t.me/{bot_username}\n\n"
        f"{t.blockquote('انشر البوت واحصل على XP إضافي مع كل مستخدم جديد!')}"
    )

import time

def format_giveaway_text(raffle: dict) -> str:
    """Formats the active giveaway text to include the active conditions nicely."""
    text = raffle.get("giveaway_text", "سحب جديد!")
    
    conditions = []
    
    # Auto draw condition
    if raffle.get("auto_draw"):
        if raffle.get("auto_draw_type") == "count":
            val = raffle.get("auto_draw_value", 0)
            conditions.append(f"🎯 <b>انتهاء تلقائي عند اكتمال العدد:</b> {val} مشارك")
        elif raffle.get("auto_draw_type") == "time":
            end_time = raffle.get("end_time")
            if end_time:
                # Format time nicely: "2026-06-22 14:30" (or similar relative/absolute string)
                import datetime
                dt = datetime.datetime.fromtimestamp(end_time)
                dt_str = dt.strftime("%Y-%m-%d %I:%M %p")
                conditions.append(f"⏱ <b>وقت الانتهاء التلقائي:</b> {dt_str}")

    # Condition channels
    if raffle.get("condition_channel"):
        ch_ids = raffle.get("condition_channel_ids", "")
        if ch_ids:
            channels = [ch.strip() for ch in str(ch_ids).split("\n") if ch.strip()]
            if channels:
                ch_list_str = " | ".join(channels)
                conditions.append(f"📢 <b>شرط الاشتراك:</b> {ch_list_str}")

    # Vote contestant
    if raffle.get("vote_contestant"):
        code = raffle.get("vote_code", "C...")
        conditions.append(f"🎟 <b>كود التصويت المطلوب:</b> <code>{code}</code>")

    # Premium only
    if raffle.get("premium_only"):
        conditions.append("💎 <b>للمشتركين المميزين (Premium) فقط</b>")



    # Winners count
    winners = raffle.get("winners_count", 1)
    conditions.append(f"🏆 <b>عدد الفائزين:</b> {winners}")

    if conditions:
        divider = "▬" * 15
        cond_text = "\n".join(conditions)
        res = f"{text}\n\n{divider}\n<b>شروط وتفاصيل السحب:</b>\n{cond_text}"
    else:
        res = text
        
    return f"{res}\n\n<blockquote>{PROMO_FOOTER_RAFFLE}</blockquote>"
