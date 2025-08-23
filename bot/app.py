import os
import logging
import re
import html
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from dotenv import load_dotenv
from bot.perplexity import query
from bot.auth import load_access, save_access

# Configure logging to suppress noisy httpx info logs
logging.basicConfig(level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)
load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    user_id = str(user.id)
    access = load_access()
    status = access.get(user_id)

    if status == "banned":
        await update.message.reply_text("Доступ отклонен")
        return
    if status == "allowed":
        await update.message.reply_text("Доступ уже предоставлен")
        return

    access[user_id] = "pending"
    save_access(access)
    await update.message.reply_text("Ожидайте выдачи доступа")

    if ADMIN_CHAT_ID:
        keyboard = [
            [
                InlineKeyboardButton("Разрешить", callback_data=f"allow:{user_id}"),
                InlineKeyboardButton("Отклонить", callback_data=f"deny:{user_id}"),
                InlineKeyboardButton("Бан", callback_data=f"ban:{user_id}"),
            ]
        ]
        username = user.username or user.full_name
        text = f'Пользователь "{username}" хочет получить доступ к duckplexity'
        await context.bot.send_message(
            chat_id=int(ADMIN_CHAT_ID),
            text=text,
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

def _format_reply(text: str) -> str:
    """Format Perplexity's markdown so citation numbers become hyperlinks
    and the trailing footnote list is removed."""
    # Extract footnote links: lines like `[1]: url`.
    footnotes = dict(re.findall(r"\[(\d+)\]:\s*(\S+)", text))
    # Drop footnote definitions from the message.
    text = re.sub(r"\n\[(\d+)\]:\s*\S+", "", text)

    # Escape all HTML special characters.
    text = html.escape(text)

    # Replace `[n]` with hyperlink if URL is known.
    def _replace(match: re.Match) -> str:
        num = match.group(1)
        url = footnotes.get(num)
        if url:
            return f'<a href="{html.escape(url, quote=True)}">[{num}]</a>'
        return match.group(0)

    text = re.sub(r"\[(\d+)\]", _replace, text)

    # Insert commas and spaces between consecutive citations
    text = re.sub(r"(</a>)\s*(?=<a)", r"\1, ", text)
    text = re.sub(r"(?<!\s)(?=<a)", " ", text)

    # Bold formatting: convert **text** to <b>text</b>
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)

    return text.strip()

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    user_id = str(user.id)
    access = load_access()
    status = access.get(user_id)

    if status == "allowed":
        user_text = update.message.text
        logging.info("User message: %s", user_text)
        try:
            resp = await query(user_text)
            raw_content = resp["choices"][0]["message"]["content"].strip()
        except Exception as exc:
            logging.exception("Perplexity query failed")
            await update.message.reply_text("Ошибка при обращении к Perplexity: %s" % exc)
            return

        img_match = re.search(r"!\[[^\]]*\]\(([^)]+)\)", raw_content)
        if img_match:
            image_url = img_match.group(1)
            raw_content = re.sub(r"!\[[^\]]*\]\(([^)]+)\)", "", raw_content, count=1).strip()
            reply = _format_reply(raw_content)
            logging.info("Formatted message: %s", reply)
            logging.info("Sending image %s", image_url)
            await update.message.reply_photo(
                photo=image_url, caption=reply, parse_mode=ParseMode.HTML
            )
        else:
            reply = _format_reply(raw_content)
            logging.info("Formatted message: %s", reply)
            logging.info("Sending text message")
            await update.message.reply_text(reply, parse_mode=ParseMode.HTML)
        return

    if status == "pending" or status is None:
        await update.message.reply_text("У вас нет доступа")
    elif status == "denied":
        await update.message.reply_text("вам отказано в доступе")
    elif status == "banned":
        await update.message.reply_text("Доступ отклонен")

async def handle_decision(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if ADMIN_CHAT_ID and query.from_user.id != int(ADMIN_CHAT_ID):
        await query.answer("Недостаточно прав", show_alert=True)
        return

    action, user_id = query.data.split(":", 1)
    access = load_access()
    if action == "allow":
        access[user_id] = "allowed"
        await context.bot.send_message(chat_id=int(user_id), text="Доступ предоставлен")
    elif action == "deny":
        access[user_id] = "denied"
        await context.bot.send_message(chat_id=int(user_id), text="Доступ отклонен")
    elif action == "ban":
        access[user_id] = "banned"
        await context.bot.send_message(chat_id=int(user_id), text="Доступ отклонен")
    save_access(access)
    await query.edit_message_reply_markup(reply_markup=None)

def main() -> None:
    if not TELEGRAM_BOT_TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not set")
    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(handle_decision))
    application.run_polling()
