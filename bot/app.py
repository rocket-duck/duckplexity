import os
import logging
import re
import html
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
    user_text = update.message.text
    logging.info("User message: %s", user_text)
    try:
        resp = await query(user_text)
        raw_content = resp["choices"][0]["message"]["content"].strip()
    except Exception as exc:
        logging.exception("Perplexity query failed")
        await update.message.reply_text("Ошибка при обращении к Perplexity: %s" % exc)
        return

    # Extract first markdown image if present and send separately so that
    # Telegram displays it as a picture with a caption.
    img_match = re.search(r"!\[[^\]]*\]\(([^)]+)\)", raw_content)
    if img_match:
        image_url = img_match.group(1)
        raw_content = re.sub(r"!\[[^\]]*\]\(([^)]+)\)", "", raw_content, count=1).strip()
        reply = _format_reply(raw_content)
        logging.info("Formatted message: %s", reply)
        logging.info("Sending image %s", image_url)
        await update.message.reply_photo(photo=image_url, caption=reply, parse_mode=ParseMode.HTML)
    else:
        reply = _format_reply(raw_content)
        logging.info("Formatted message: %s", reply)
        logging.info("Sending text message")
        await update.message.reply_text(reply, parse_mode=ParseMode.HTML)

def main() -> None:
    if not TELEGRAM_BOT_TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not set")
    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.run_polling()
