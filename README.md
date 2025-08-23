# Duckplexity

Telegram bot that forwards user messages to Perplexity AI.

## Usage
1. Copy `.env.example` to `.env` and fill in `TELEGRAM_BOT_TOKEN`, `PERPLEXITY_API_KEY` and `ADMIN_CHAT_ID`.
2. Build and run using Docker Compose:
   ```bash
   docker compose up --build
   ```
3. User access state is stored in `data/access.json` and persisted on the host via a volume mount.
