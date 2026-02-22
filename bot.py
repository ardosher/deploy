
import os
import json
from datetime import datetime, timedelta
from typing import Dict, Any

from telegram import (
    Update,
    ReplyKeyboardMarkup,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)


TOKEN = "8496419944:AAGPafIprdEVPL0RGoO3WmXm7f3vzAcjKd0"
ADMIN_ID = int(os.environ.get("ADMIN_ID", "6920473195"))  
DB_FILE = "db.json"


CLICK_LINK = "https://my.click.uz/clickp2p/03E06568A91F7A52F863EB7445A2E756DE34D1CE1F83A8572BB5C3861A205E93"
PAYNET_LINK = "https://app.paynet.uz/?m=49156&i=1c3b0c8f-3794-43dc-8171-470dc47c8e52"
CARD_NUMBER = "9860 1701 0441 5857"
TON_ADDRESS = "UQD2G4XIHqXYPWIsagPnlwwSYJi1ob0GNXprvyrWo-zFUJps"


def load_db() -> Dict[str, Any]:
    if not os.path.exists(DB_FILE):
        base = {
            "users": {},       
            "blacklist": [],    
            "checks": {},      
            "next_check_id": 1
        }
        save_db(base)
        return base
    with open(DB_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_db(d: Dict[str, Any]):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)

db = load_db()


LANG = {
    "uz": {
        "choose_lang": "Tilni tanlang / Выберите язык",
        "welcome": "Xush kelibsiz! To'lov turini tanlang👇",
        "main_menu": "Bosh menyu:",
        "pay_window": "To'lov oynasi:",
        "check_upload": "♻️ Chekni yuboring… (rasm yoki skrinshot)",
        "check_sent": "✅ Chek adminga yuborildi. Tez orada tekshiriladi.",
        "banned_msg": "❌ Siz qora ro‘yxatga qo‘yilgansiz. Botdan foydalanish mumkin emas.",
        "admin_panel": "🛠 SUPER ADMIN PANEL — tanlang",
        "no_pending": "🔎 Hozir tekshirilishi kerak bo‘lgan chek yo‘q.",
        "accepted": "✅ To'lov Muffyaqatli Qabul qilindi",
        "declined": "❌ sizning chek Nomalum Yana qaytarilsa chetlashtirilasiz!",
        "banned_user": "🚫 Foydalanuvchi qora ro‘yxatga qo‘yildi.",
        "unbanned_user": "♻️ Foydalanuvchi qora ro‘yxatdan chiqarildi.",
        "stats_title": "📈 Statistika:",
        "new_users_title": "🆕 Oxirgi qo‘shilgan foydalanuvchilar:",
    },
    "ru": {
        "choose_lang": "Выберите язык / Tilni tanlang",
        "welcome": "Добро пожаловать! Выберите способ оплаты👇",
        "main_menu": "Главное меню:",
        "pay_window": "Окно оплаты:",
        "check_upload": "♻️ Отправьте чек… (фото или скрин)",
        "check_sent": "✅ Чек отправлен администратору. Скоро проверят.",
        "banned_msg": "❌ Вы в чёрном списке. Использование бота запрещено.",
        "admin_panel": "🛠 SUPER ADMIN PANEL — выберите",
        "no_pending": "🔎 Нет чеков на проверку.",
        "accepted": "✅ Чек принят.",
        "declined": "❌ Чек отклонён.",
        "banned_user": "🚫 Пользователь добавлен в чёрный список.",
        "unbanned_user": "♻️ Пользователь удалён из чёрного списка.",
        "stats_title": "📈 Статистика:",
        "new_users_title": "🆕 Последние добавленные пользователи:",
    }
}

# ========== Reply menyular ==========
language_menu = ReplyKeyboardMarkup([["🇺🇿 O‘zbekcha", "🇷🇺 Русский"]], resize_keyboard=True, one_time_keyboard=True)

main_menu_buttons = {
    "uz": [["CLICK AVTO", "PAYNET AVTO"], ["KARTAGA", "TON HAMYON"], ["ADMIN ORQALI", "FAQ"]],
    "ru": [["CLICK АВТО", "PAYNET АВТО"], ["НА КАРТУ", "TON КОШЕЛЁК"], ["ЧЕРЕЗ АДМИНА", "FAQ"]]
}


def get_user(user_id: int) -> Dict[str, Any]:
    return db["users"].get(str(user_id), {})

def set_user(user_id: int, data: Dict[str, Any]):
    db["users"][str(user_id)] = data
    save_db(db)

def is_banned(user_id: int) -> bool:
    return str(user_id) in db.get("blacklist", [])

def ensure_user_record(user_id: int):
    if str(user_id) not in db["users"]:
        db["users"][str(user_id)] = {
            "lang": None,
            "banned": False,
            "created_ts": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
            "waiting_for_check": None
        }
        save_db(db)

def create_check(user_id: int, photo_file_id: str, platform: str) -> int:
    cid = db.get("next_check_id", 1)
    db["checks"][str(cid)] = {
        "user_id": user_id,
        "photo": photo_file_id,
        "platform": platform,
        "ts": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
        "status": "pending"
    }
    db["next_check_id"] = cid + 1
    save_db(db)
    return cid

def admin_controls_for_check(check_id: int):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Qabul qilish", callback_data=f"admin_accept:{check_id}"),
            InlineKeyboardButton("❌ Rad etish", callback_data=f"admin_decline:{check_id}")
        ],
        [
            InlineKeyboardButton("🚫 Chetlashtirish", callback_data=f"admin_ban:{check_id}"),
            InlineKeyboardButton("⬅️ Ortga", callback_data="admin_back")
        ]
    ])

def build_platform_menu(platform: str, lang: str):
    if platform == "click":
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("💳 To'lov sahifasi (CLICK)", url=CLICK_LINK)],
            [InlineKeyboardButton("✅ TO'LOV QILDIM", callback_data="done_click")],
            [InlineKeyboardButton("⬅️ Ortga", callback_data="back")]
        ])
    if platform == "paynet":
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("📲 To'lov sahifasi (PAYNET)", url=PAYNET_LINK)],
            [InlineKeyboardButton("✅ TO'LOV QILDIM", callback_data="done_paynet")],
            [InlineKeyboardButton("⬅️ Ortga", callback_data="back")]
        ])
    if platform == "card":
        return InlineKeyboardMarkup([
            [InlineKeyboardButton(f"💳 Karta: {CARD_NUMBER}", callback_data="none")],
            [InlineKeyboardButton("✅ TO'LOV QILDIM", callback_data="done_card")],
            [InlineKeyboardButton("⬅️ Ortga", callback_data="back")]
        ])
    if platform == "ton":
        return InlineKeyboardMarkup([
            [InlineKeyboardButton(f"💎 TON: {TON_ADDRESS}", callback_data="none")],
            [InlineKeyboardButton("✅ TO'LOV QILDIM", callback_data="done_ton")],
            [InlineKeyboardButton("⬅️ Ortga", callback_data="back")]
        ])

# ========== HANDLER: /start ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id

    ensure_user_record(user_id)

    # Agar qora ro'yxatda bo'lsa
    if is_banned(user_id):
        lang = get_user(user_id).get("lang") or "uz"
        await update.message.reply_text(LANG[lang]["banned_msg"])
        return

    user_rec = get_user(user_id)
    lang = user_rec.get("lang")
    if not lang:
        # tilni tanlashni ko'rsatamiz (xato xabarsiz)
        await update.message.reply_text(LANG["uz"]["choose_lang"], reply_markup=language_menu)
        return

    # agar admin bo'lsa admin panel tugmasini ham ko'rsatamiz (reply keyboard)
    reply = ReplyKeyboardMarkup(main_menu_buttons[lang], resize_keyboard=True)
    await update.message.reply_text(LANG[lang]["welcome"], reply_markup=reply)

# ========== HANDLER: matnli xabarlar ==========
async def messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    text = (update.message.text or "").strip()

    ensure_user_record(user_id)

    # Agar banlangan bo'lsa
    if is_banned(user_id):
        lang = get_user(user_id).get("lang") or "uz"
        await update.message.reply_text(LANG[lang]["banned_msg"])
        return

    # Til tanlash tugmasi bosildi
    if "🇺🇿" in text or "O‘zbek" in text or "O'zbek" in text:
        db["users"][str(user_id)]["lang"] = "uz"
        save_db(db)
        await update.message.reply_text(LANG["uz"]["welcome"], reply_markup=ReplyKeyboardMarkup(main_menu_buttons["uz"], resize_keyboard=True))
        return
    if "🇷🇺" in text or "Русский" in text:
        db["users"][str(user_id)]["lang"] = "ru"
        save_db(db)
        await update.message.reply_text(LANG["ru"]["welcome"], reply_markup=ReplyKeyboardMarkup(main_menu_buttons["ru"], resize_keyboard=True))
        return

    # Agar til hali yo'q bo'lsa yana taklif qilamiz (lekin Xato deb yozmaymiz)
    if not db["users"][str(user_id)].get("lang"):
        await update.message.reply_text(LANG["uz"]["choose_lang"], reply_markup=language_menu)
        return

    lang = db["users"][str(user_id)]["lang"]

    # Admin panelga kirish (reply keyboarddagi tugma)
    if text.upper() in [m.upper() for m in main_menu_buttons[lang][2]]:  # "ADMIN ORQALI" yoki shunga o'xshash
        if user_id == ADMIN_ID:
            # Super admin panel (Variant C)
            await update.message.reply_text(
                LANG[lang]["admin_panel"],
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🧾 Oxirgi cheklar (navbat)", callback_data="admin_next")],
                    [InlineKeyboardButton("📋 Barcha cheklar", callback_data="admin_list")],
                    [InlineKeyboardButton("🚫 Qora ro'yxat (ro'yxatga olish/olib tashlash)", callback_data="admin_blacklist")],
                    [InlineKeyboardButton("📈 Statistika", callback_data="admin_stats")],
                    [InlineKeyboardButton("🆕 Yangi foydalanuvchilar (so'nggi 7 kun)", callback_data="admin_newusers")],
                    [InlineKeyboardButton("⬅️ Ortga", callback_data="admin_back")]
                ])
            )
        else:
            await update.message.reply_text("❌ Bu bo‘lim faqat admin uchun.")
        return

    # To'lov tugmalari (CLICK/PAYNET) -> bevosita link va "TO'LOV QILDIM" tugmasi
    if text.upper() in [m.upper() for m in main_menu_buttons[lang][0]]:  # CLICK AVTO, PAYNET AVTO
        if "CLICK" in text.upper():
            await update.message.reply_text(LANG[lang]["pay_window"], reply_markup=build_platform_menu("click", lang))
            return
        if "PAYNET" in text.upper():
            await update.message.reply_text(LANG[lang]["pay_window"], reply_markup=build_platform_menu("paynet", lang))
            return

    # Karta va TON -> ko'rsatamiz
    if text.upper() in [m.upper() for m in main_menu_buttons[lang][1]]:
        if "KART" in text.upper() or "КАРТ" in text.upper():
            await update.message.reply_text(LANG[lang]["pay_window"], reply_markup=build_platform_menu("card", lang))
            return
        if "TON" in text.upper():
            await update.message.reply_text(LANG[lang]["pay_window"], reply_markup=build_platform_menu("ton", lang))
            return

    # Admin uchun qulay text buyruqlar (agar istasangiz)
    if user_id == ADMIN_ID:
        if text.lower().startswith("ban "):
            # format: ban <user_id>
            parts = text.split()
            if len(parts) >= 2 and parts[1].isdigit():
                target = parts[1]
                if target not in db["blacklist"]:
                    db["blacklist"].append(target)
                    db["users"].setdefault(target, {})["banned"] = True
                    save_db(db)
                    await update.message.reply_text(LANG[lang]["banned_user"])
                else:
                    await update.message.reply_text("Bu foydalanuvchi allaqachon qora ro'yxatda.")
            else:
                await update.message.reply_text("Iltimos: ban <user_id> shaklida yuboring.")
            return
        if text.lower().startswith("unban "):
            parts = text.split()
            if len(parts) >= 2 and parts[1].isdigit():
                target = parts[1]
                if target in db["blacklist"]:
                    db["blacklist"].remove(target)
                    db["users"].setdefault(target, {})["banned"] = False
                    save_db(db)
                    await update.message.reply_text(LANG[lang]["unbanned_user"])
                else:
                    await update.message.reply_text("Bu foydalanuvchi qora ro'yxatda emas.")
            else:
                await update.message.reply_text("Iltimos: unban <user_id> shaklida yuboring.")
            return

    # Boshqa matnlar — asosiy menyuni yuborish
    await update.message.reply_text(LANG[lang]["main_menu"], reply_markup=ReplyKeyboardMarkup(main_menu_buttons[lang], resize_keyboard=True))

# ========== CALLBACKS: admin opsiyalar va platform callbacks ==========
async def callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user = query.from_user
    user_id = user.id

    # agar foydalanuvchi banlangan bo'lsa
    if is_banned(user_id):
        lang = get_user(user_id).get("lang") or "uz"
        await query.edit_message_text(LANG[lang]["banned_msg"])
        return

    # Platforma "TO'LOV QILDIM" tugmasi bosildi -> waiting_for_check belgilanadi va foydalanuvchidan rasm so'raymiz
    if data.startswith("done_"):
        platform = data.replace("done_", "")
        ensure_user_record(user_id)
        db["users"][str(user_id)]["waiting_for_check"] = platform
        save_db(db)
        lang = get_user(user_id).get("lang") or "uz"
        await query.edit_message_text(LANG[lang]["check_upload"])
        return

    # Oddiy back tugma
    if data == "back":
        lang = get_user(user_id).get("lang") or "uz"
        await query.edit_message_text(LANG[lang]["main_menu"])
        return

    # ========== ADMIN CALLBACKS (faqat ADMIN_ID) ==========
    if data == "admin_next" and user_id == ADMIN_ID:
        # birinchi pending chekni tanlab admin chatga yuborish
        pending = {k: v for k, v in db["checks"].items() if v["status"] == "pending"}
        if not pending:
            lang = get_user(user_id).get("lang") or "uz"
            await query.edit_message_text(LANG[lang]["no_pending"])
            return
        first_id = sorted(int(k) for k in pending.keys())[0]
        check = db["checks"][str(first_id)]
        caption = (
            f"🆔 Check ID: {first_id}\n"
            f"👤 Foydalanuvchi: {check['user_id']}\n"
            f"💠 Platforma: {check['platform']}\n"
            f"⏱ Vaqt (UTC): {check['ts']}\n"
            f"Status: {check['status']}"
        )
        # Admin chatiga rasm bilan yuboramiz va inline tugmalar beramiz
        try:
            await context.bot.send_photo(chat_id=ADMIN_ID, photo=check["photo"], caption=caption, reply_markup=admin_controls_for_check(first_id))
        except:
            pass
        await query.edit_message_text("🔎 Navbatdagi chek admin chatiga yuborildi.")
        return

    if data == "admin_list" and user_id == ADMIN_ID:
        lines = []
        for cid, info in db["checks"].items():
            lines.append(f"#{cid} — {info['platform']} — {info['status']} — {info['user_id']}")
        text = "\n".join(lines) if lines else "Hech qanday chek yo'q."
        await query.edit_message_text("📋 Barcha cheklar:\n" + text)
        return

    if data == "admin_blacklist" and user_id == ADMIN_ID:
        bl = db.get("blacklist", [])
        text = "\n".join(bl) if bl else "Qora ro'yxat bo'sh."
        await query.edit_message_text("🚫 Qora ro'yxat:\n" + text)
        return

    if data == "admin_stats" and user_id == ADMIN_ID:
        total_users = len(db["users"])
        total_checks = len(db["checks"])
        pending = sum(1 for v in db["checks"].values() if v["status"] == "pending")
        accepted = sum(1 for v in db["checks"].values() if v["status"] == "accepted")
        declined = sum(1 for v in db["checks"].values() if v["status"] == "declined")
        msg = (
            f"{LANG['uz']['stats_title']}\n"
            f"Foydalanuvchilar: {total_users}\n"
            f"Jami cheklar: {total_checks}\n"
            f"Pending: {pending}\n"
            f"Accepted: {accepted}\n"
            f"Declined: {declined}"
        )
        await query.edit_message_text(msg)
        return

    if data == "admin_newusers" and user_id == ADMIN_ID:
        # oxirgi 7 kun ichida qo'shilganlardan 20tasini ko'rsatish
        cutoff = datetime.utcnow() - timedelta(days=7)
        recent = []
        for uid, info in db["users"].items():
            ts = info.get("created_ts")
            try:
                t = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")
            except:
                continue
            if t >= cutoff:
                recent.append((t, uid))
        recent.sort(reverse=True)
        lines = [f"{uid} — {t.strftime('%Y-%m-%d')}" for t, uid in recent[:20]]
        text = "\n".join(lines) if lines else "So'nggi 7 kun ichida yangi foydalanuvchi yo'q."
        await query.edit_message_text(f"{LANG['uz']['new_users_title']}\n" + text)
        return

    if data.startswith("admin_accept:") and user_id == ADMIN_ID:
        cid = data.split(":", 1)[1]
        if cid in db["checks"]:
            db["checks"][cid]["status"] = "accepted"
            save_db(db)
            target = db["checks"][cid]["user_id"]
            try:
                # foydalanuvchiga xabar yuborish
                lang = get_user(int(target)).get("lang") or "uz"
                await context.bot.send_message(chat_id=int(target), text=LANG[lang]["accepted"])
            except:
                pass
            await query.edit_message_text("✅ Chek qabul qilindi.")
        else:
            await query.edit_message_text("Chek topilmadi.")
        return

    if data.startswith("admin_decline:") and user_id == ADMIN_ID:
        cid = data.split(":", 1)[1]
        if cid in db["checks"]:
            db["checks"][cid]["status"] = "declined"
            save_db(db)
            target = db["checks"][cid]["user_id"]
            try:
                lang = get_user(int(target)).get("lang") or "uz"
                await context.bot.send_message(chat_id=int(target), text=LANG[lang]["declined"])
            except:
                pass
            await query.edit_message_text("❌ Chek rad etildi.")
        else:
            await query.edit_message_text("Chek topilmadi.")
        return

    if data.startswith("admin_ban:") and user_id == ADMIN_ID:
        cid = data.split(":", 1)[1]
        if cid in db["checks"]:
            target = str(db["checks"][cid]["user_id"])
            if target not in db["blacklist"]:
                db["blacklist"].append(target)
                db["users"].setdefault(target, {})["banned"] = True
                save_db(db)
            try:
                lang = get_user(int(target)).get("lang") or "uz"
                await context.bot.send_message(chat_id=int(target), text=LANG[lang]["banned_msg"])
            except:
                pass
            await query.edit_message_text("🚫 Foydalanuvchi qora ro'yxatga olindi.")
        else:
            await query.edit_message_text("Chek topilmadi.")
        return

    if data == "admin_back":
        lang = get_user(user_id).get("lang") or "uz"
        await query.edit_message_text(LANG[lang]["admin_panel"])
        return

# ========== PHOTO handler: foydalanuvchidan chek qabul qilish ==========
async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    user_id = user.id

    if is_banned(user_id):
        lang = get_user(user_id).get("lang") or "uz"
        await update.message.reply_text(LANG[lang]["banned_msg"])
        return

    ensure_user_record(user_id)
    user_rec = get_user(user_id)
    waiting = user_rec.get("waiting_for_check")
    if not waiting:
        # foydalanuvchiga avval qaysi platformada to'lov qildingiz (TO'LOV QILDIM) tugmasini bosishi kerakligini aytamiz
        await update.message.reply_text("Iltimos: avval to'lov platformani tanlang va 'TO'LOV QILDIM' tugmasini bosing.")
        return

    photo = update.message.photo[-1].file_id
    cid = create_check(user_id, photo, waiting)

    caption = (
        f"🧾 YANGI TO'LOV CHEKI\n"
        f"👤 Foydalanuvchi: @{user.username if user.username else user.full_name}\n"
        f"🆔 Telegram ID: {user_id}\n"
        f"💠 Platforma: {waiting.upper()}\n"
        f"⏱ Vaqt (UTC): {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"Check ID: {cid}"
    )
    # adminga yuboramiz
    try:
        await context.bot.send_photo(chat_id=ADMIN_ID, photo=photo, caption=caption, reply_markup=admin_controls_for_check(cid))
    except:
        pass

    lang = get_user(user_id).get("lang") or "uz"
    await update.message.reply_text(LANG[lang]["check_sent"])
    
    db["users"][str(user_id)].pop("waiting_for_check", None)
    save_db(db)


def main():
    
    try:
        from keep_alive import keep_alive
        keep_alive()
    except:
        pass

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(callbacks))
    app.add_handler(MessageHandler(filters.PHOTO, photo_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, messages))

    print("Bot ishga tushdi…")
    app.run_polling()

if __name__ == "__main__":
    main()
