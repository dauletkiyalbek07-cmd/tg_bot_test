import asyncio
import logging
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart, Command
from aiogram.fsm.storage.memory import MemoryStorage

# ==================== НАСТРОЙКИ ====================
BOT_TOKEN = "8682908255:AAGcEKUCNd0sfzQgldmI5fXYtuGeeFpZOF4"  # @BotFather дан токен

# Каналы на которые нужно подписаться (username без @)
CHANNELS = [
    {"name": "Канал 1 📺", "username": "your_channel_1", "url": "https://t.me/your_channel_1"},
    {"name": "Канал 2 🎬", "username": "your_channel_2", "url": "https://t.me/your_channel_2"},
]

# База фильмов: код -> название фильма
MOVIES = {
    "001": "🎬 Интерстеллар (2014)",
    "002": "🎬 Начало (2010)",
    "003": "🎬 Джокер (2019)",
    "004": "🎬 Мстители: Финал (2019)",
    "005": "🎬 Паразиты (2019)",
    "100": "🎬 Дюна: Часть 2 (2024)",
    "101": "🎬 Оппенгеймер (2023)",
}
# ====================================================

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())


async def check_subscriptions(user_id: int) -> list:
    """Проверяет подписку пользователя на все каналы. Возвращает список каналов без подписки."""
    not_subscribed = []
    for channel in CHANNELS:
        try:
            member = await bot.get_chat_member(f"@{channel['username']}", user_id)
            if member.status in ["left", "kicked", "restricted"]:
                not_subscribed.append(channel)
        except Exception:
            not_subscribed.append(channel)
    return not_subscribed


def subscription_keyboard(not_subscribed: list, code: str) -> InlineKeyboardMarkup:
    """Создаёт клавиатуру с кнопками подписки."""
    buttons = []
    for ch in not_subscribed:
        buttons.append([InlineKeyboardButton(text=f"✅ Подписаться на {ch['name']}", url=ch["url"])])
    buttons.append([
        InlineKeyboardButton(text="🔄 Я подписался, проверить", callback_data=f"check_{code}")
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


@dp.message(CommandStart())
async def start_handler(message: Message):
    args = message.text.split()
    code = args[1] if len(args) > 1 else None

    text = (
        "👋 Привет! Я бот для получения фильмов по коду.\n\n"
        "🎬 Отправь мне <b>код фильма</b> и я пришлю название!\n\n"
        "📌 Код обычно указан под видео в Reels / Shorts / TikTok."
    )

    if code:
        text += f"\n\n🔑 Ты пришёл с кодом: <b>{code}</b>"

    await message.answer(text, parse_mode="HTML")

    if code:
        await process_code(message, code)


@dp.message(Command("add"))
async def add_movie(message: Message):
    """Команда для добавления фильма (только для администратора)."""
    # Замени на свой Telegram ID
    ADMIN_ID = 1341838301

    if message.from_user.id != ADMIN_ID:
        await message.answer("❌ У тебя нет доступа к этой команде.")
        return

    parts = message.text.split(maxsplit=2)
    if len(parts) < 3:
        await message.answer("❗ Использование: /add КОД Название фильма\nПример: /add 006 Матрица (1999)")
        return

    code = parts[1]
    title = parts[2]
    MOVIES[code] = f"🎬 {title}"
    await message.answer(f"✅ Фильм добавлен!\nКод: <b>{code}</b>\nНазвание: <b>{title}</b>", parse_mode="HTML")


@dp.message(Command("list"))
async def list_movies(message: Message):
    """Показывает список всех кодов (только для администратора)."""
    ADMIN_ID = 123456789

    if message.from_user.id != ADMIN_ID:
        await message.answer("❌ У тебя нет доступа.")
        return

    if not MOVIES:
        await message.answer("📭 База фильмов пуста.")
        return

    text = "📋 <b>Все фильмы в базе:</b>\n\n"
    for code, title in MOVIES.items():
        text += f"<code>{code}</code> — {title}\n"

    await message.answer(text, parse_mode="HTML")


@dp.message(F.text)
async def text_handler(message: Message):
    code = message.text.strip()
    await process_code(message, code)


async def process_code(message: Message, code: str):
    """Основная логика: проверка подписки → выдача фильма."""
    code = code.strip()

    if code not in MOVIES:
        await message.answer(
            f"❌ Код <b>{code}</b> не найден.\n\n"
            "📌 Убедись что код правильный. Код указан под видео.",
            parse_mode="HTML"
        )
        return

    not_subscribed = await check_subscriptions(message.from_user.id)

    if not_subscribed:
        names = "\n".join([f"• {ch['name']}" for ch in not_subscribed])
        await message.answer(
            f"🔐 Чтобы получить фильм, подпишись на наши каналы:\n\n{names}\n\n"
            f"После подписки нажми кнопку ниже 👇",
            reply_markup=subscription_keyboard(not_subscribed, code),
            parse_mode="HTML"
        )
    else:
        film_title = MOVIES[code]
        await message.answer(
            f"✅ Вот твой фильм!\n\n{film_title}\n\n"
            f"🍿 Приятного просмотра!",
            parse_mode="HTML"
        )


@dp.callback_query(F.data.startswith("check_"))
async def check_subscription_callback(callback: CallbackQuery):
    code = callback.data.split("_", 1)[1]

    not_subscribed = await check_subscriptions(callback.from_user.id)

    if not_subscribed:
        names = "\n".join([f"• {ch['name']}" for ch in not_subscribed])
        await callback.answer("❌ Ты ещё не подписался на все каналы!", show_alert=True)
        await callback.message.edit_text(
            f"🔐 Ты ещё не подписан на:\n\n{names}\n\nПодпишись и нажми кнопку снова 👇",
            reply_markup=subscription_keyboard(not_subscribed, code),
            parse_mode="HTML"
        )
    else:
        film_title = MOVIES.get(code, "❓ Фильм не найден")
        await callback.message.edit_text(
            f"✅ Отлично! Подписка подтверждена.\n\n{film_title}\n\n"
            f"🍿 Приятного просмотра!",
            parse_mode="HTML"
        )
        await callback.answer("✅ Готово!")


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
