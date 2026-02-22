import asyncio
import random
import time
import openai
from aiogram import Bot, Dispatcher, types, executor
from aiogram.contrib.fsm_storage.memory import MemoryContextStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup

# --- KONFIGURATSIYA ---
API_TOKEN = '8570450962:AAF3mJoChGNeefoUPuokdLuIrvS1wmieyTw'
ADMIN_ID = 7009426983 # O'z ID raqamingiz
OPENAI_API_KEY = 'OPENAI_KEY_BU_YERGA' # AI xohlamasangiz bo'sh qoldiring

openai.api_key = OPENAI_API_KEY
bot = Bot(token=API_TOKEN, parse_mode="HTML")
storage = MemoryContextStorage()
dp = Dispatcher(bot, storage=storage)

class NexoriumStates(StatesGroup):
    REPLY_MODE = State()
    AI_MODE = State()

# RAM-dagi ma'lumotlar
sessions = {} # Foydalanuvchi va operator suhbati uchun
ai_active = True # Avtomatik AI javobi yoqilgan

# --- AI JAVOB FUNKSIYASI ---
async def get_ai_response(user_text):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Sen Nexorium IT kompaniyasining aqlli yordamchisisan. Foydalanuvchilarga professional, xushmuomala va qisqa javob ber."},
                {"role": "user", "content": user_text}
            ]
        )
        return response.choices[0].message.content
    except:
        return "Hozirda operatorlarimiz band, birozdan so'ng javob berishadi."

# --- USER QISMI ---
@dp.message_handler(commands=['start'])
async def cmd_start(message: types.Message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("👨‍💻 Mutaxassis bilan bog'lanish")
    await message.answer(
        f"🚀 <b>Nexorium IT Solutions</b> botiga xush kelibsiz!\n\n"
        f"Bizning AI-yordamchimiz yoki operatorlarimiz sizga yordam berishga tayyor.",
        reply_markup=markup
    )

@dp.message_handler(lambda m: m.from_user.id != ADMIN_ID)
async def handle_messages(message: types.Message):
    # Operatorga xabar yuborish dizayni
    ticket_id = f"NX-{random.randint(100, 999)}"
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("⚡️ Javob berish", callback_data=f"ans_{message.from_user.id}"))
    
    # Operatorga bildirishnoma
    await bot.send_message(
        ADMIN_ID,
        f"📬 <b>Yangi Ticket: {ticket_id}</b>\n"
        f"👤 Foydalanuvchi: {message.from_user.full_name}\n"
        f"💬 Xabar: <i>{message.text}</i>",
        reply_markup=markup
    )

    # Agar AI yoqilgan bo'lsa, mijozga srazu AI javob beradi
    if ai_active:
        wait_msg = await message.answer("🤖 <i>Nexorium AI fikrlamoqda...</i>")
        ai_text = await get_ai_response(message.text)
        await wait_msg.edit_text(f"🤖 <b>AI Yordamchi:</b>\n\n{ai_text}\n\n<i>(Operator ham tez orada ulanadi)</i>")
    else:
        await message.answer("✅ Xabaringiz operatorga yetkazildi. Iltimos, kuting.")

# --- ADMIN PANEL (EXKLYUZIV) ---
@dp.callback_query_handler(lambda c: c.data.startswith('ans_'), user_id=ADMIN_ID)
async def admin_reply_start(call: types.CallbackQuery, state: FSMContext):
    user_id = call.data.split("_")[1]
    await NexoriumStates.REPLY_MODE.set()
    await state.update_data(target_id=user_id)
    await bot.send_message(ADMIN_ID, f"⌨️ <b>ID: {user_id}</b> uchun javobingizni yozing:")
    await call.answer()

@dp.message_handler(state=NexoriumStates.REPLY_MODE, user_id=ADMIN_ID)
async def admin_reply_send(message: types.Message, state: FSMContext):
    data = await state.get_data()
    uid = data.get("target_id")
    
    try:
        # Mijozga yuborish
        await bot.send_message(uid, f"👨‍💻 <b>Nexorium Mutaxassisi:</b>\n\n{message.text}")
        await message.answer("✅ Muvaffaqiyatli yuborildi.")
    except:
        await message.answer("❌ Xatolik: Foydalanuvchi botni to'xtatgan.")
    
    await state.finish()

# Admin uchun boshqaruv paneli
@dp.message_handler(commands=['panel'], user_id=ADMIN_ID)
async def admin_settings(message: types.Message):
    global ai_active
    status = "✅ YOQILGAN" if ai_active else "❌ O'CHIRILGAN"
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton(f"AI Holati: {status}", callback_data="toggle_ai"))
    
    await message.answer("🛠 <b>Nexorium Control Panel</b>\nAI-yordamchini boshqarish:", reply_markup=markup)

@dp.callback_query_handler(text="toggle_ai", user_id=ADMIN_ID)
async def toggle_ai_handler(call: types.CallbackQuery):
    global ai_active
    ai_active = not ai_active
    await call.answer("AI holati o'zgardi!")
    await admin_settings(call.message)
    await call.message.delete()

if __name__ == '__main__':
    print("Nexorium AI Bot is running...")
    executor.start_polling(dp, skip_updates=True)
