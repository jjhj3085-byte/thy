import telebot
from telebot import types
import database as db
import config
import threading
import io

# حالة لوحة التحكم في القناة الإدارية
ADMIN_STATE = None
DASHBOARD_MSG_ID = None

def admin_log(bot: telebot.TeleBot, text: str, reply_markup=None):
    if not config.ADMIN_LOG_CHAT_ID:
        return
    try:
        bot.send_message(config.ADMIN_LOG_CHAT_ID, text, reply_markup=reply_markup, parse_mode="HTML")
    except Exception as e:
        print(f"Admin log error: {e}")

def get_main_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("📊 الإحصائيات", callback_data="adm_stats"),
        types.InlineKeyboardButton("🔍 بحث مستخدم", callback_data="adm_search")
    )
    markup.add(
        types.InlineKeyboardButton("🎰 السحوبات النشطة", callback_data="adm_raffles"),
        types.InlineKeyboardButton("🏁 المسابقات النشطة", callback_data="adm_comps")
    )
    markup.add(
        types.InlineKeyboardButton("🔔 إذاعة رسالة", callback_data="adm_bcast"),
        types.InlineKeyboardButton("⛔️ المحظورين", callback_data="adm_banned")
    )
    markup.add(
        types.InlineKeyboardButton("🗑 تنظيف البيانات", callback_data="adm_cleanup"),
        types.InlineKeyboardButton("🗃 تصدير البيانات", callback_data="adm_export")
    )
    markup.add(
        types.InlineKeyboardButton("🏆 آخر الفائزين", callback_data="adm_winners"),
        types.InlineKeyboardButton("👥 آخر المشتركين", callback_data="adm_recent")
    )
    markup.add(
        types.InlineKeyboardButton("🥇 الأكثر فوزاً", callback_data="adm_top"),
        types.InlineKeyboardButton("📜 سجل الأحداث", callback_data="adm_log")
    )
    return markup

def _edit(bot, chat_id, msg_id, text, markup=None):
    try:
        bot.edit_message_text(text, chat_id, msg_id, reply_markup=markup, parse_mode="HTML")
    except Exception:
        pass

def _back_btn():
    return types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("🔙 الرئيسية", callback_data="adm_main"))

def register_handlers(bot: telebot.TeleBot):
    global ADMIN_STATE, DASHBOARD_MSG_ID

    # ─── channel posts (commands + text input) ────────────────────────
    @bot.channel_post_handler(func=lambda m: True)
    def handle_channel_post(message: types.Message):
        global ADMIN_STATE, DASHBOARD_MSG_ID

        if str(message.chat.id) != config.ADMIN_LOG_CHAT_ID:
            return

        if message.text and message.text.strip() in ['/ادارة', '/روليت']:
            text = ("👑 <b>لوحة تحكم الإدارة الشاملة</b>\n"
                    "▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬" + "\n"
                    "مرحباً بك في مركز التحكم المباشر.\n"
                    "اختر القسم المطلوب:")
            try: bot.delete_message(message.chat.id, message.message_id)
            except: pass
            msg = bot.send_message(message.chat.id, text, reply_markup=get_main_keyboard(), parse_mode="HTML")
            DASHBOARD_MSG_ID = msg.message_id
            ADMIN_STATE = None
            return

        # حالة الإدخال
        if ADMIN_STATE and message.text:
            txt = message.text.strip()
            state = ADMIN_STATE
            ADMIN_STATE = None
            try: bot.delete_message(message.chat.id, message.message_id)
            except: pass

            if state == "search":
                # بحث بالآيدي أو اليوزر
                info = None
                if txt.isdigit():
                    info = db.get_user_info(int(txt))
                else:
                    info = db.search_user_by_username(txt)
                if not info:
                    _edit(bot, message.chat.id, DASHBOARD_MSG_ID,
                          "❌ <b>لم يتم العثور على المستخدم.</b>\nتأكد من الآيدي أو اليوزر.", _back_btn())
                    return
                _show_user_profile(bot, message.chat.id, DASHBOARD_MSG_ID, info)

            elif state == "ban":
                info = None
                if txt.isdigit():
                    info = db.get_user_info(int(txt))
                    if info:
                        db.set_user_ban(info['user_id'], 1)
                else:
                    uid = db.set_user_ban_by_username(txt, 1)
                    if uid:
                        info = db.get_user_info(uid)
                if info:
                    _edit(bot, message.chat.id, DASHBOARD_MSG_ID,
                          f"⛔️ <b>تم حظر المستخدم بنجاح!</b>\n👤 {info['first_name']}\n🆔 <code>{info['user_id']}</code>", _back_btn())
                else:
                    _edit(bot, message.chat.id, DASHBOARD_MSG_ID,
                          "❌ <b>المستخدم غير موجود.</b>", _back_btn())

            elif state == "unban":
                info = None
                if txt.isdigit():
                    info = db.get_user_info(int(txt))
                    if info:
                        db.set_user_ban(info['user_id'], 0)
                else:
                    uid = db.set_user_ban_by_username(txt, 0)
                    if uid:
                        info = db.get_user_info(uid)
                if info:
                    _edit(bot, message.chat.id, DASHBOARD_MSG_ID,
                          f"✅ <b>تم فك حظر المستخدم!</b>\n👤 {info['first_name']}\n🆔 <code>{info['user_id']}</code>", _back_btn())
                else:
                    _edit(bot, message.chat.id, DASHBOARD_MSG_ID,
                          "❌ <b>المستخدم غير موجود.</b>", _back_btn())

            elif state == "broadcast":
                _edit(bot, message.chat.id, DASHBOARD_MSG_ID,
                      "⏳ <b>جاري الإذاعة...</b>\nقد يستغرق هذا بعض الوقت.", types.InlineKeyboardMarkup())
                def do_bcast(msg_txt, cid, mid):
                    with db.get_connection() as conn:
                        rows = conn.execute("SELECT user_id FROM users WHERE is_banned = 0").fetchall()
                    ok = 0
                    fail = 0
                    for r in rows:
                        try:
                            bot.send_message(r["user_id"], msg_txt)
                            ok += 1
                        except:
                            fail += 1
                    _edit(bot, cid, mid,
                          f"✅ <b>تمت الإذاعة بنجاح!</b>\n📨 وصلت لـ: <b>{ok}</b>\n❌ فشلت: <b>{fail}</b>", _back_btn())
                threading.Thread(target=do_bcast, args=(txt, message.chat.id, DASHBOARD_MSG_ID), daemon=True).start()

    def _show_user_profile(bot, chat_id, msg_id, info):
        uid = info['user_id']
        stats = db.get_user_stats(uid)
        banned = info.get('is_banned', 0)
        res = (
            f"👤 <b>ملف المستخدم</b>\n"
            f"▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬" + "\n"
            f"📛 الاسم: <b>{info['first_name']}</b>\n"
            f"🏷 اليوزر: @{info.get('username', 'لا يوجد')}\n"
            f"🆔 الآيدي: <code>{uid}</code>\n"
            f"📅 تاريخ الانضمام: {info['joined_date']}\n"
            f"▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬" + "\n"
            f"🏆 مرات الفوز: <b>{stats.get('wins', 0)}</b>\n"
            f"🎮 المشاركات: <b>{stats.get('joined', 0)}</b>\n"
            f"🎰 سحوبات أنشأها: <b>{stats.get('created', 0)}</b>\n"
            f"⚡️ النقاط (XP): <b>{stats.get('xp', 0)}</b>\n"
            f"▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬" + "\n"
            f"الحالة: {'⛔️ <b>محظور</b>' if banned else '✅ <b>نشط</b>'}"
        )
        kb = types.InlineKeyboardMarkup(row_width=1)
        if banned:
            kb.add(types.InlineKeyboardButton("✅ فك الحظر", callback_data=f"adm_ub_{uid}"))
        else:
            kb.add(types.InlineKeyboardButton("⛔️ حظر المستخدم", callback_data=f"adm_bn_{uid}"))
        kb.add(types.InlineKeyboardButton("🔙 الرئيسية", callback_data="adm_main"))
        _edit(bot, chat_id, msg_id, res, kb)

    # ─── callback queries ─────────────────────────────────────────────
    @bot.callback_query_handler(func=lambda c: c.data and c.data.startswith("adm_"))
    def cb_admin(call: types.CallbackQuery):
        global ADMIN_STATE, DASHBOARD_MSG_ID
        if str(call.message.chat.id) != config.ADMIN_LOG_CHAT_ID:
            bot.answer_callback_query(call.id, "غير مصرح لك", show_alert=True)
            return

        DASHBOARD_MSG_ID = call.message.message_id
        cid = call.message.chat.id
        mid = call.message.message_id
        action = call.data.replace("adm_", "")

        # ── الرئيسية ──────────────────────────────────────────────
        if action == "main":
            ADMIN_STATE = None
            text = ("👑 <b>لوحة تحكم الإدارة الشاملة</b>\n"
                    "▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬" + "\n"
                    "مرحباً بك في مركز التحكم المباشر.\n"
                    "اختر القسم المطلوب:")
            _edit(bot, cid, mid, text, get_main_keyboard())
            bot.answer_callback_query(call.id)

        # ── الإحصائيات ────────────────────────────────────────────
        elif action == "stats":
            try:
                users = db.get_total_users()
                raffles = db.get_total_active_raffles()
                comps = db.get_total_active_competitions()
                banned = len(db.get_banned_users())
                text = (
                    "📊 <b>الإحصائيات الشاملة</b>\n"
                    "▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬" + "\n\n"
                    f"👥 إجمالي المستخدمين: <b>{users}</b>\n"
                    f"⛔️ المحظورين: <b>{banned}</b>\n"
                    f"🎰 السحوبات النشطة: <b>{raffles}</b>\n"
                    f"🏁 المسابقات النشطة: <b>{comps}</b>\n"
                )
                _edit(bot, cid, mid, text, _back_btn())
            except Exception as e:
                _edit(bot, cid, mid, f"❌ خطأ: {e}", _back_btn())
            bot.answer_callback_query(call.id)

        # ── البحث ─────────────────────────────────────────────────
        elif action == "search":
            ADMIN_STATE = "search"
            text = ("🔍 <b>بحث عن مستخدم</b>\n"
                    "▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬" + "\n\n"
                    "أرسل الآن <b>اليوزر</b> (مثل: @username)\n"
                    "أو <b>الآيدي</b> (مثل: 123456)\n\n"
                    "كرسالة هنا في القناة 🔽")
            _edit(bot, cid, mid, text, _back_btn())
            bot.answer_callback_query(call.id)

        # ── السحوبات النشطة ───────────────────────────────────────
        elif action == "raffles":
            try:
                r_list = db.get_active_raffles(10)
                kb = types.InlineKeyboardMarkup(row_width=1)
                if not r_list:
                    text = ("🎰 <b>السحوبات النشطة</b>\n"
                            "▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬" + "\n\n"
                            "لا توجد سحوبات نشطة حالياً.")
                else:
                    text = (f"🎰 <b>السحوبات النشطة ({len(r_list)}):</b>\n"
                            "▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬" + "\n\n"
                            "اختر السحب للتحكم به:")
                    for r in r_list:
                        prize = r.get('giveaway_text', r.get('prize', ''))
                        prize_short = (prize[:12] + '..') if prize and len(prize) > 12 else (prize or 'بدون جائزة')
                        cnt = db.count_participants(r['raffle_id'])
                        kb.add(types.InlineKeyboardButton(
                            f"🎁 {r['raffle_id']} | {prize_short} | 👥{cnt}",
                            callback_data=f"adm_mr_{r['raffle_id']}"))
                kb.add(types.InlineKeyboardButton("🔙 الرئيسية", callback_data="adm_main"))
                _edit(bot, cid, mid, text, kb)
            except Exception as e:
                _edit(bot, cid, mid, f"❌ خطأ: {e}", _back_btn())
            bot.answer_callback_query(call.id)

        # ── إدارة سحب معين ────────────────────────────────────────
        elif action.startswith("mr_"):
            rid = action[3:]
            raffle = db.get_raffle(rid)
            cnt = db.count_participants(rid)
            if raffle:
                text = (
                    f"⚙️ <b>إدارة السحب</b>\n"
                    f"▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬" + "\n\n"
                    f"🆔 الآيدي: <code>{rid}</code>\n"
                    f"👤 المنشئ: <code>{raffle['creator_id']}</code>\n"
                    f"👥 المشاركين: <b>{cnt}</b>\n"
                    f"📅 أنشئ: {raffle.get('created_at', '—')}\n"
                )
            else:
                text = f"⚙️ <b>إدارة السحب:</b> <code>{rid}</code>"
            kb = types.InlineKeyboardMarkup(row_width=1)
            kb.add(types.InlineKeyboardButton("👥 رؤية المشاركين", callback_data=f"adm_vpr_{rid}"))
            kb.add(types.InlineKeyboardButton("🗑 حذف السحب نهائياً", callback_data=f"adm_dr_{rid}"))
            kb.add(types.InlineKeyboardButton("🔙 السحوبات", callback_data="adm_raffles"))
            _edit(bot, cid, mid, text, kb)
            bot.answer_callback_query(call.id)

        # ── رؤية مشاركين سحب ──────────────────────────────────────
        elif action.startswith("vpr_"):
            rid = action[4:]
            p_list = db.get_participants(rid)
            if not p_list:
                _edit(bot, cid, mid, f"لا يوجد مشاركين في السحب <code>{rid}</code>.",
                      types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("🔙 رجوع", callback_data=f"adm_mr_{rid}")))
            else:
                text = f"👥 <b>مشاركين السحب ({rid}) — {len(p_list)} مشارك:</b>\n\n"
                for i, p in enumerate(p_list, 1):
                    tag = f"@{p['username']}" if p.get('username') else "بدون يوزر"
                    text += f"{i}. {p['first_name']} ({tag})\n"
                if len(text) > 4000:
                    text = text[:3900] + "\n... القائمة طويلة"
                _edit(bot, cid, mid, text,
                      types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("🔙 رجوع", callback_data=f"adm_mr_{rid}")))
            bot.answer_callback_query(call.id)

        # ── حذف سحب ───────────────────────────────────────────────
        elif action.startswith("dr_"):
            rid = action[3:]
            db.force_delete_raffle(rid)
            _edit(bot, cid, mid, f"✅ تم حذف السحب <code>{rid}</code> نهائياً.", _back_btn())
            bot.answer_callback_query(call.id, "تم الحذف")

        # ── المسابقات النشطة ──────────────────────────────────────
        elif action == "comps":
            try:
                c_list = db.get_active_competitions(10)
                kb = types.InlineKeyboardMarkup(row_width=1)
                if not c_list:
                    text = ("🏁 <b>المسابقات النشطة</b>\n"
                            "▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬" + "\n\n"
                            "لا توجد مسابقات نشطة حالياً.")
                else:
                    text = (f"🏁 <b>المسابقات النشطة ({len(c_list)}):</b>\n"
                            "▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬" + "\n\n"
                            "اختر المسابقة للتحكم بها:")
                    for c in c_list:
                        kb.add(types.InlineKeyboardButton(
                            f"🏁 {c['comp_id']} | {c['title'][:15]}",
                            callback_data=f"adm_mc_{c['comp_id']}"))
                kb.add(types.InlineKeyboardButton("🔙 الرئيسية", callback_data="adm_main"))
                _edit(bot, cid, mid, text, kb)
            except Exception as e:
                _edit(bot, cid, mid, f"❌ خطأ: {e}", _back_btn())
            bot.answer_callback_query(call.id)

        # ── إدارة مسابقة معينة ────────────────────────────────────
        elif action.startswith("mc_"):
            comp_id = action[3:]
            kb = types.InlineKeyboardMarkup(row_width=1)
            kb.add(types.InlineKeyboardButton("👥 رؤية المشاركين", callback_data=f"adm_vpc_{comp_id}"))
            kb.add(types.InlineKeyboardButton("🗑 حذف المسابقة نهائياً", callback_data=f"adm_dc_{comp_id}"))
            kb.add(types.InlineKeyboardButton("🔙 المسابقات", callback_data="adm_comps"))
            _edit(bot, cid, mid, f"⚙️ <b>إدارة المسابقة:</b> <code>{comp_id}</code>\nاختر الإجراء:", kb)
            bot.answer_callback_query(call.id)

        # ── رؤية مشاركين مسابقة ────────────────────────────────────
        elif action.startswith("vpc_"):
            comp_id = action[4:]
            p_list = db.get_comp_participants(comp_id)
            if not p_list:
                _edit(bot, cid, mid, f"لا يوجد مشاركين في المسابقة <code>{comp_id}</code>.",
                      types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("🔙 رجوع", callback_data=f"adm_mc_{comp_id}")))
            else:
                text = f"👥 <b>مشاركين المسابقة ({comp_id}) — {len(p_list)} مشارك:</b>\n\n"
                for i, p in enumerate(p_list, 1):
                    tag = f"@{p['username']}" if p.get('username') else "بدون يوزر"
                    text += f"{i}. {p['first_name']} ({tag})\n"
                if len(text) > 4000:
                    text = text[:3900] + "\n... القائمة طويلة"
                _edit(bot, cid, mid, text,
                      types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("🔙 رجوع", callback_data=f"adm_mc_{comp_id}")))
            bot.answer_callback_query(call.id)

        # ── حذف مسابقة ────────────────────────────────────────────
        elif action.startswith("dc_"):
            comp_id = action[3:]
            db.force_delete_competition(comp_id)
            _edit(bot, cid, mid, f"✅ تم حذف المسابقة <code>{comp_id}</code> نهائياً.", _back_btn())
            bot.answer_callback_query(call.id, "تم الحذف")

        # ── الإذاعة ───────────────────────────────────────────────
        elif action == "bcast":
            ADMIN_STATE = "broadcast"
            text = ("🔔 <b>إذاعة رسالة لجميع المشتركين</b>\n"
                    "▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬" + "\n\n"
                    "أرسل الآن <b>نص الرسالة</b> التي تود إرسالها\n"
                    "لجميع المستخدمين كرسالة هنا في القناة 🔽\n\n"
                    "<i>ملاحظة: لن يتم إرسالها للمحظورين.</i>")
            _edit(bot, cid, mid, text, _back_btn())
            bot.answer_callback_query(call.id)

        # ── المحظورين ─────────────────────────────────────────────
        elif action == "banned":
            b_list = db.get_banned_users()
            kb = types.InlineKeyboardMarkup(row_width=1)
            if not b_list:
                text = ("⛔️ <b>قائمة المحظورين</b>\n"
                        "▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬" + "\n\n"
                        "لا يوجد مستخدمين محظورين حالياً.")
            else:
                text = (f"⛔️ <b>المحظورين ({len(b_list)}):</b>\n"
                        "▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬" + "\n\n")
                for b in b_list:
                    tag = f"@{b['username']}" if b.get('username') else 'بدون يوزر'
                    text += f"• {b['first_name']} ({tag})\n"
                    kb.add(types.InlineKeyboardButton(
                        f"✅ فك حظر: {b['first_name']}",
                        callback_data=f"adm_ub_{b['user_id']}"))

            kb.add(types.InlineKeyboardButton("➕ حظر مستخدم جديد", callback_data="adm_banadd"))
            kb.add(types.InlineKeyboardButton("🔙 الرئيسية", callback_data="adm_main"))
            _edit(bot, cid, mid, text, kb)
            bot.answer_callback_query(call.id)

        # ── حظر مستخدم جديد ───────────────────────────────────────
        elif action == "banadd":
            ADMIN_STATE = "ban"
            text = ("⛔️ <b>حظر مستخدم</b>\n"
                    "▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬" + "\n\n"
                    "أرسل <b>اليوزر</b> (مثل: @username)\n"
                    "أو <b>الآيدي</b> (مثل: 123456)\n\n"
                    "كرسالة هنا في القناة 🔽")
            _edit(bot, cid, mid, text, _back_btn())
            bot.answer_callback_query(call.id)

        # ── حظر مباشر ─────────────────────────────────────────────
        elif action.startswith("bn_"):
            uid = int(action[3:])
            db.set_user_ban(uid, 1)
            _edit(bot, cid, mid, f"⛔️ تم حظر المستخدم <code>{uid}</code> بنجاح.", _back_btn())
            bot.answer_callback_query(call.id, "تم الحظر")

        # ── فك حظر مباشر ──────────────────────────────────────────
        elif action.startswith("ub_"):
            uid = int(action[3:])
            db.set_user_ban(uid, 0)
            _edit(bot, cid, mid, f"✅ تم فك حظر المستخدم <code>{uid}</code>.", _back_btn())
            bot.answer_callback_query(call.id, "تم فك الحظر")

        # ── تنظيف البيانات ─────────────────────────────────────────
        elif action == "cleanup":
            kb = types.InlineKeyboardMarkup(row_width=2)
            kb.add(
                types.InlineKeyboardButton("⚠️ نعم، نظّف", callback_data="adm_doclean"),
                types.InlineKeyboardButton("🔙 تراجع", callback_data="adm_main")
            )
            _edit(bot, cid, mid,
                  "🗑 <b>تنظيف البيانات</b>\n"
                  "▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬" + "\n\n"
                  "هل تريد حذف جميع السحوبات المنتهية\n"
                  "ومشاركيها لتسريع البوت؟\n\n"
                  "⚠️ <i>هذا الإجراء لا يمكن التراجع عنه!</i>", kb)
            bot.answer_callback_query(call.id)

        elif action == "doclean":
            c = db.cleanup_old_data()
            _edit(bot, cid, mid, f"✅ <b>تم التنظيف!</b>\nتم حذف <b>{c}</b> سحب منتهي.", _back_btn())
            bot.answer_callback_query(call.id)

        # ── تصدير البيانات ─────────────────────────────────────────
        elif action == "export":
            bot.answer_callback_query(call.id, "جاري الاستخراج...")
            try:
                with db.get_connection() as conn:
                    rows = conn.execute("SELECT user_id, username, first_name FROM users").fetchall()
                if not rows:
                    _edit(bot, cid, mid, "قاعدة البيانات فارغة.", _back_btn())
                    return
                lines = ["user_id,username,first_name"]
                for r in rows:
                    lines.append(f"{r['user_id']},{r['username'] or ''},{r['first_name'] or ''}")
                data = "\n".join(lines).encode("utf-8")
                bot.send_document(cid, ("users_export.csv", io.BytesIO(data)),
                                  caption=f"🗃 بيانات المستخدمين — العدد: {len(rows)}")
                _edit(bot, cid, mid, "✅ تم إرسال ملف البيانات بنجاح.", _back_btn())
            except Exception as e:
                _edit(bot, cid, mid, f"❌ خطأ: {e}", _back_btn())

        # ── آخر الفائزين ──────────────────────────────────────────
        elif action == "winners":
            try:
                w_list = db.get_recent_winners(15)
                if not w_list:
                    text = ("🏆 <b>آخر الفائزين</b>\n"
                            "▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬" + "\n\n"
                            "لا يوجد فائزين بعد.")
                else:
                    text = (f"🏆 <b>آخر {len(w_list)} فائز:</b>\n"
                            "▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬" + "\n\n")
                    for i, w in enumerate(w_list, 1):
                        text += f"{i}. 🎁 {w['winner_name']} — سحب: <code>{w['raffle_id']}</code>\n"
                _edit(bot, cid, mid, text, _back_btn())
            except Exception as e:
                _edit(bot, cid, mid, f"❌ خطأ: {e}", _back_btn())
            bot.answer_callback_query(call.id)

        # ── آخر المشتركين الجدد ───────────────────────────────────
        elif action == "recent":
            try:
                u_list = db.get_recent_users(20)
                if not u_list:
                    text = ("👥 <b>آخر المشتركين</b>\n"
                            "▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬" + "\n\n"
                            "لا يوجد مشتركين.")
                else:
                    text = (f"👥 <b>آخر {len(u_list)} مشترك:</b>\n"
                            "▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬" + "\n\n")
                    for i, u in enumerate(u_list, 1):
                        tag = f"@{u['username']}" if u.get('username') else '—'
                        text += f"{i}. {u['first_name']} ({tag}) — {u['joined_date']}\n"
                    if len(text) > 4000:
                        text = text[:3900] + "\n..."
                _edit(bot, cid, mid, text, _back_btn())
            except Exception as e:
                _edit(bot, cid, mid, f"❌ خطأ: {e}", _back_btn())
            bot.answer_callback_query(call.id)

        # ── الأكثر فوزاً (الترتيب) ───────────────────────────────
        elif action == "top":
            try:
                t_list = db.get_top_users(10)
                if not t_list:
                    text = ("🥇 <b>الأكثر فوزاً</b>\n"
                            "▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬" + "\n\n"
                            "لا يوجد بيانات بعد.")
                else:
                    medals = ['🥇', '🥈', '🥉'] + ['🏅'] * 7
                    text = ("🥇 <b>ترتيب الأكثر فوزاً:</b>\n"
                            "▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬" + "\n\n")
                    for i, u in enumerate(t_list):
                        tag = f"@{u['username']}" if u.get('username') else '—'
                        text += f"{medals[i]} {u['first_name']} ({tag})\n"
                        text += f"    🏆 فوز: {u['wins']} | ⚡️ XP: {u['xp']}\n\n"
                _edit(bot, cid, mid, text, _back_btn())
            except Exception as e:
                _edit(bot, cid, mid, f"❌ خطأ: {e}", _back_btn())
            bot.answer_callback_query(call.id)

        # ── سجل الأحداث ──────────────────────────────────────────
        elif action == "log":
            try:
                logs = db.get_activity_log(15)
                if not logs:
                    text = ("📜 <b>سجل الأحداث</b>\n"
                            "▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬" + "\n\n"
                            "لا يوجد أحداث مسجلة بعد.")
                else:
                    text = (f"📜 <b>آخر {len(logs)} حدث:</b>\n"
                            "▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬" + "\n\n")
                    for l in logs:
                        text += f"• [{l.get('created_at', '—')}] {l.get('event', '—')}\n"
                    if len(text) > 4000:
                        text = text[:3900] + "\n..."
                _edit(bot, cid, mid, text, _back_btn())
            except Exception as e:
                _edit(bot, cid, mid, f"❌ خطأ: {e}", _back_btn())
            bot.answer_callback_query(call.id)

        # ── رؤية المشاركين (من اللوق) ─────────────────────────────
        elif action.startswith("viewparticipants_"):
            parts = action.split("_")
            kind = parts[1]
            item_id = parts[2]
            bot.answer_callback_query(call.id)
            p_list = db.get_participants(item_id) if kind == "raffle" else db.get_comp_participants(item_id)
            if not p_list:
                _edit(bot, cid, mid, f"لا يوجد مشاركين في {item_id}.", _back_btn())
                return
            text = f"👥 <b>المشاركين ({item_id}) — {len(p_list)}:</b>\n\n"
            for i, p in enumerate(p_list, 1):
                tag = f"@{p['username']}" if p.get('username') else "بدون يوزر"
                text += f"{i}. {p['first_name']} ({tag})\n"
            if len(text) > 4000:
                text = text[:3900] + "\n..."
            _edit(bot, cid, mid, text, _back_btn())
