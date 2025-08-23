import os
import logging
import re
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
from dotenv import load_dotenv
from bot.perplexity import query

# Configure logging to suppress noisy httpx info logs
logging.basicConfig(level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)
load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Привет! Отправь мне сообщение, и я спрошу Perplexity.")

def _format_reply(text: str) -> str:
    """Format Perplexity's markdown so that citation links appear as
    ``[1], [2]`` with commas and spaces and without a trailing list of
    sources."""
    # Drop footnote-style reference list at the end of the message.
    text = re.sub(r"\n\n\[\d+\]:.*", "", text, flags=re.DOTALL)

    # Escape brackets so that Telegram renders them literally and insert
    # a comma and space between consecutive citations.
    def _escape(match: re.Match) -> str:
        num, url = match.groups()
        url = re.sub(r"([_()])", r"\\\1", url)
        return rf"[\[{num}\]]({url})"

    text = re.sub(r"\[(\d+)\]\(([^)]+)\)", _escape, text)
    text = re.sub(r"\)\s*(?=\[\\)", "), ", text)
    text = re.sub(r"(?<!\s)(?=\[\\)", " ", text)

    # Escape Telegram MarkdownV2 special characters while preserving
    # citation links formatted above.
    placeholders: list[str] = []

    def _store(match: re.Match) -> str:
        placeholders.append(match.group(0))
        return f"PLACEHOLDER{len(placeholders) - 1}"

    text = re.sub(r"\[\\\[\d+\\\]\]\([^)]+\)", _store, text)
    text = re.sub(r"([_*\[\]()~`>#+=|{}.!])", r"\\\1", text)

    for idx, link in enumerate(placeholders):
        text = text.replace(f"PLACEHOLDER{idx}", link)

    return text.strip()

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_text = update.message.text
    logging.info("User message: %s", user_text)
    try:
        resp = await query(user_text)
        reply = _format_reply(resp["choices"][0]["message"]["content"].strip())
    except Exception as exc:
        logging.exception("Perplexity query failed")
        await update.message.reply_text("Ошибка при обращении к Perplexity: %s" % exc)
        return
    # Extract first markdown image if present and send separately so that
    # Telegram displays it as a picture with a caption.
    img_match = re.search(r"!\[[^\]]*\]\(([^)]+)\)", reply)
    if img_match:
        image_url = img_match.group(1)
        text = re.sub(r"!\[[^\]]*\]\(([^)]+)\)", "", reply, count=1).strip()
        logging.info("Sending image %s with caption: %s", image_url, text)
        await update.message.reply_photo(photo=image_url, caption=text, parse_mode=ParseMode.MARKDOWN_V2)
    else:
        logging.info("Sending text message: %s", reply)
        await update.message.reply_text(reply, parse_mode=ParseMode.MARKDOWN_V2)

def main() -> None:
    if not TELEGRAM_BOT_TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not set")
    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.run_polling()
