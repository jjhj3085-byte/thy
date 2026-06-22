# خطة تطوير روليت سراب — Roadmap 2025–2026

> **الهدف:** تحويل البوت من أداة سحب بسيطة إلى منصة سحوبات عربية احترافية (SaaS-lite) مع واجهة Premium، توثيق، وتحليلات.

---

## الوضع الحالي (v2.0) ✅

| المجال | ما تم |
|--------|--------|
| **UI** | بانرات PNG gradient لكل صفحة + أيقونات SVG في `assets/icons/` |
| **الروليت** | شريط تقدم ▰▱، رسائل HTML غنية، دوران متحرك قبل إعلان الفائز |
| **Gamification** | XP، مستويات، لوحة الشرف |
| **إدارة** | تصدير مشاركين، إيقاف، نسخ سحب، Toggle إعدادات |
| **السجل** | توثيق في قناة السجل + سجل نشاط المستخدم |
| **الملف** | `/profile`، `/stats`، تذكير الفوز |

---

## المرحلة 1 — Polish فوري (1–2 أسابيع)

### 1.1 واجهة Telegram Premium
- [ ] رفع الأيقونات SVG كـ **Custom Emoji** (Bot API 9.3+)
- [ ] **Mini App** (WebApp) لوحة تحكم بصرية للسحوبات
- [ ] ثيمات لونية (Dark / Gold / Mint) يختارها المستخدم
- [ ] رسائل `sendAnimation` GIF للفوز بدل النص فقط

### 1.2 الروليت السريع
- [ ] **عدّاد تنازلي** قبل السحب التلقائي (3…2…1)
- [ ] صوت/اهتزاز (Haptic) عبر WebApp
- [ ] فلتر: منع حسابات بدون صورة أو username
- [ ] **Multi-winner**: 1–5 فائزين في سحب واحد
- [ ] QR Code لمشاركة السحب خارج Telegram

### 1.3 إنشاء الروليت (قنوات/قروبات)
- [ ] معالج **Wizard** خطوة بخطوة (عدد → شروط → نشر)
- [ ] جدولة السحب (تاريخ/وقت إعلان الفائز)
- [ ] اشتراك إجباري بقنوات متعددة قبل الانضمام
- [ ] Captcha بسيط anti-bot

---

## المرحلة 2 — منصة كاملة (3–6 أسابيع)

### 2.1 Backend
- [ ] ترحيل SQLite → **PostgreSQL** للإنتاج
- [ ] Redis للـ cache و rate-limit
- [ ] Webhook بدل Polling
- [ ] Docker + systemd للنشر 24/7

### 2.2 لوحة Admin
- [ ] `/admin` — إحصائيات عامة، حظر مستخدمين، إيقاف سحوبات
- [ ] تقارير CSV يومية/أسبوعية
- [ ] Broadcast للمستخدمين (مع opt-in)

### 2.3 Monetization (اختياري)
- [ ] **Sarab Pro**: سحوبات غير محدودة + بدون إعلان
- [ ] Telegram Stars / تبرعات
- [ ] White-label للقنوات الكبيرة

---

## المرحلة 3 — Quantum Leap (2–3 أشهر)

### 3.1 AI & Automation
- [ ] توليد نصوص السحب بالذكاء الاصطناعي
- [ ] كشف حسابات وهمية (heuristics + ML)
- [ ] ترجمة تلقائية EN/AR/TR

### 3.2 تكاملات
- [ ] API REST للمطورين (`POST /raffles`, webhooks)
- [ ] Zapier / Make.com
- [ ] تصدير إلى Google Sheets

### 3.3 تجربة جماعية
- [ ] **Live Roulette** — بث حي لاختيار الفائز
- [ ] غرف صوتية (Voice Chat integration hint)
- [ ] NFT/Token gating (اختياري للWeb3 channels)

---

## هيكلة الكود المستقبلية

```
sarab-roulette-bot/
├── main.py              # entry
├── config.py
├── database/
│   ├── models.py
│   └── migrations/
├── handlers/
│   ├── start.py
│   ├── raffle.py
│   └── admin.py
├── ui/
│   ├── theme.py
│   ├── pages.py
│   ├── navigator.py
│   └── assets/
├── services/
│   ├── raffle_engine.py
│   ├── spin_animation.py
│   └── log_service.py
└── tests/
```

---

## KPIs للنجاح

| المؤشر | الهدف 3 أشهر |
|--------|----------------|
| مستخدمون نشطون/شهر | 5,000+ |
| سحوبات مكتملة/يوم | 200+ |
| Uptime | 99.5% |
| زمن رد Callback | < 300ms |
| تقييم المستخدمين | 4.5/5 |

---

## أولويات التنفيذ (الأسبوع القادم)

1. **تشغيل v2** + توليد البانرات: `python tools/generate_banners.py`
2. **BotFather**: Inline Mode + Group Privacy Off
3. **اختبار** الروليت في 3 قروبات حقيقية
4. **Mini App** prototype (صفحة واحدة: إحصائياتي)
5. **PostgreSQL** migration script

---

## ملاحظات تقنية

- **SVG في Telegram**: الأزرار لا تدعم صوراً — SVG تُستخدم كبانرات (PNG) وملفات مصدر في `assets/icons/`
- **Custom Emoji**: يتطلب `@BotFather` → Upload emoji pack
- **WebApp**: React/Vue + `@twa-dev/sdk` للوحة تحكم غنية

---

*آخر تحديث: يونيو 2025 · روليت سراب v2.0*
