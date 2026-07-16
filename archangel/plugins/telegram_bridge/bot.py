import logging
from telegram import Update
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
from .auth import is_authorized

logger = logging.getLogger(__name__)

def auth_required(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        if not update.effective_user:
            return
        user_id = update.effective_user.id
        if not is_authorized(user_id):
            await update.message.reply_text("Access denied.")
            return
        return await func(update, context, *args, **kwargs)
    return wrapper

@auth_required
async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Archangel Online. What do you need?")

@auth_required
async def status_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        from archangel.engine.runtime import get_status
        status = get_status()
        formatted = "📊 System Status\n"
        for k, v in status.items():
            formatted += f"• {k}: {v}\n"
        await update.message.reply_text(formatted)
    except Exception as exc:
        logger.error("Status handler failed: %s", exc)
        await update.message.reply_text(f"❌ Error getting status: {exc}")

@auth_required
async def clear_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    bridge = context.application.bot_data.get("bridge")
    if bridge:
        bridge.clear_history(user_id)
        await update.message.reply_text("✅ Chat history cleared.")
    else:
        await update.message.reply_text("❌ Bridge reference not found.")

@auth_required
async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "⚔ Archangel Bot Commands:\n\n"
        "/start - Initialize bot contact\n"
        "/status - View system runtime status\n"
        "/clear - Clear your chat history\n"
        "/scan - Trigger a one-time scan cycle\n"
        "/help - List available commands\n\n"
        "Or simply type a message to converse and run commands."
    )
    await update.message.reply_text(help_text)

@auth_required
async def scan_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔄 Initiating one-time scan...")
    try:
        import asyncio
        from archangel.engine.runtime import run_once
        summary = await asyncio.to_thread(run_once)
        formatted = "✅ Scan complete\n"
        for k, v in summary.items():
            formatted += f"• {k}: {v}\n"
        await update.message.reply_text(formatted)
    except Exception as exc:
        logger.error("Scan handler failed: %s", exc)
        await update.message.reply_text(f"❌ Scan failed: {exc}")

@auth_required
async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    text = update.message.text
    user_id = update.effective_user.id
    bridge = context.application.bot_data.get("bridge")
    if not bridge:
        await update.message.reply_text("❌ Bridge reference not found.")
        return

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    try:
        responses = await bridge.handle_message(user_id, text)
        for resp in responses:
            await update.message.reply_text(resp)
    except Exception as exc:
        logger.error("Message handler failed: %s", exc)
        await update.message.reply_text(f"❌ Error: {exc}")

def create_bot(bridge) -> Application:
    import os
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        from archangel.config.manager import load_config
        cfg = load_config()
        token = cfg.get("channels", {}).get("telegram", {}).get("bot_token")
        if token and "${" in token:
            token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise ValueError("TELEGRAM_BOT_TOKEN not found in environment or config.")

    app = ApplicationBuilder().token(token).build()
    app.bot_data["bridge"] = bridge

    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CommandHandler("status", status_handler))
    app.add_handler(CommandHandler("clear", clear_handler))
    app.add_handler(CommandHandler("help", help_handler))
    app.add_handler(CommandHandler("scan", scan_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    return app
