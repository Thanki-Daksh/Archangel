"""Telegram bot handlers with smart text routing."""

import logging
from telegram import Update
from telegram.ext import (
    Application,
    ApplicationBuilder,
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
        if not is_authorized(update.effective_user.id):
            await update.message.reply_text("Access denied.")
            return
        return await func(update, context, *args, **kwargs)
    return wrapper


# --- Command Handlers ---

@auth_required
async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Archangle Online.\n\n"
        "Commands:\n"
        "  status - System status\n"
        "  search <query> - Search the web\n"
        "  leads <query> [site:<platform>] - Find leads on any platform\n"
        "  save - Save last leads to file\n"
        "  mode [basic|smart|continuous] - Toggle scraping mode\n"
        "  scrape <url> - Scrape a URL\n"
        "  watch <url> - Monitor a URL for changes\n"
        "  unwatch <url> - Stop monitoring\n"
        "  watches - List monitored URLs\n"
        "  clear - Clear chat history\n"
        "  help - Show this message\n\n"
        "Or just type anything to chat with Archangel AI."
    )


@auth_required
async def status_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        from archangel.engine.runtime import get_status
        status = get_status()
        lines = ["📊 System Status"]
        for k, v in status.items():
            lines.append(f"• {k}: {v}")
        await update.message.reply_text("\n".join(lines))
    except Exception as exc:
        await update.message.reply_text(f"❌ Error: {exc}")


@auth_required
async def clear_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bridge = context.application.bot_data.get("bridge")
    if bridge:
        bridge.clear_history(update.effective_user.id)
        await update.message.reply_text("✅ Chat history cleared.")
    else:
        await update.message.reply_text("❌ Bridge not initialized.")


@auth_required
async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start_handler(update, context)


@auth_required
async def scan_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔄 Initiating scan...")
    try:
        import asyncio
        from archangel.engine.runtime import run_once
        summary = await asyncio.to_thread(run_once)
        lines = ["✅ Scan complete"]
        for k, v in summary.items():
            lines.append(f"• {k}: {v}")
        await update.message.reply_text("\n".join(lines))
    except Exception as exc:
        await update.message.reply_text(f"❌ Scan failed: {exc}")


@auth_required
async def search_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text.startswith("/"):
        text = text[1:]
    parts = text.split(None, 1)
    if len(parts) < 2:
        await update.message.reply_text("Usage: search <query>")
        return

    query = parts[1].strip()
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    try:
        from archangel.agents.chat import WebSearch
        results = WebSearch().search(query, max_results=5)
        bridge = context.application.bot_data.get("bridge")
        if bridge:
            for part in bridge._split_message(results):
                await update.message.reply_text(part)
        else:
            await update.message.reply_text(results)
    except Exception as exc:
        await update.message.reply_text(f"❌ Search failed: {exc}")


SITE_SHORTCUTS = {
    "linkedin": "linkedin.com",
    "reddit": "reddit.com",
    "discord": "discord.com",
    "x": "x.com",
    "twitter": "x.com",
    "github": "github.com",
    "stackoverflow": "stackoverflow.com",
    "quora": "quora.com",
    "medium": "medium.com",
    "producthunt": "producthunt.com",
    "indiehackers": "indiehackers.com",
    "hackernews": "news.ycombinator.com",
    "facebook": "facebook.com",
    "instagram": "instagram.com",
    "youtube": "youtube.com",
}


def _parse_site_filter(query: str):
    """Extract site: parameter from query. Returns (cleaned_query, site_filter_or_None)."""
    import re
    # Check known shortcuts first
    lower = query.lower()
    for key, domain in SITE_SHORTCUTS.items():
        pattern = f"site:{key}"
        if pattern in lower:
            idx = lower.index(pattern)
            cleaned = (query[:idx] + query[idx + len(pattern):]).strip()
            return cleaned, f"site:{domain}"
    # Check raw domain (e.g., site:customsite.com)
    match = re.search(r'site:(\S+)', query, re.IGNORECASE)
    if match:
        domain = match.group(1)
        cleaned = (query[:match.start()] + query[match.end():]).strip()
        return cleaned, f"site:{domain}"
    return query, None


@auth_required
async def leads_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text.startswith("/"):
        text = text[1:]
    parts = text.split(None, 1)
    if len(parts) < 2:
        await update.message.reply_text(
            'Usage: leads <query> [site:<platform>]\n\n'
            'Sites: linkedin, reddit, discord, x, github, medium, producthunt\n'
            'Or use any domain: site:customsite.com\n\n'
            'Examples:\n'
            '  leads "AI automation" site:discord\n'
            '  leads "chatbot" site:linkedin\n'
            '  leads "python freelance" site:customsite.com'
        )
        return

    raw_query = parts[1].strip().strip('"').strip("'")
    query, site_filter = _parse_site_filter(raw_query)

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    try:
        from archangel.agents.chat import WebSearch, LLMClient
        from archangel.agents.scraper import SmartScraper
        import re

        # Build search query
        if site_filter:
            search_query = f'{query} {site_filter}'
        else:
            search_query = query

        results = WebSearch().search(search_query, max_results=5)
        urls = re.findall(r'URL:\s*(https?://[^\s]+)', results)

        if not urls:
            await update.message.reply_text("No results found.")
            return

        # Scrape each URL
        scraper = SmartScraper()
        pages = []
        all_links = []
        for url in urls[:3]:
            content = scraper.fetch_text(url, timeout=20)
            if not content.startswith("Error:"):
                pages.append(f"URL: {url}\n\n{content[:3000]}")
                links_output = scraper.fetch_links(url, timeout=20)
                if links_output and not links_output.startswith("Error:"):
                    all_links.append(f"Links from {url}:\n{links_output[:2000]}")

        if not pages:
            await update.message.reply_text("Could not scrape any pages.")
            return

        # Build context-aware prompt based on site
        if site_filter and "discord" in site_filter:
            context_hint = "Look for people asking for help, seeking automation services, or discussing pain points in Discord servers."
        elif site_filter and "reddit" in site_filter:
            context_hint = "Look for Reddit threads where people are asking for recommendations, expressing frustration, or seeking automation solutions."
        elif site_filter and "linkedin" in site_filter:
            context_hint = "Look for LinkedIn posts or articles where companies express AI automation needs or executives discuss digital transformation."
        elif site_filter and ("x.com" in site_filter or "twitter" in site_filter):
            context_hint = "Look for tweets expressing pain points, asking for recommendations, or discussing automation needs."
        elif site_filter and "github" in site_filter:
            context_hint = "Look for GitHub issues, discussions, or repos where people need automation help or are building related tools."
        elif site_filter and "stackoverflow" in site_filter:
            context_hint = "Look for StackOverflow questions where people struggle with automation, AI integration, or repetitive tasks."
        else:
            context_hint = "Find people or companies showing interest in or need for AI automation services."

        llm = LLMClient()
        combined_pages = "\n\n---\n\n".join(pages)
        combined_links = "\n\n".join(all_links) if all_links else "No additional links found."
        prompt = (
            f"Analyze these search results and extract potential leads for an AI automation service.\n"
            f"{context_hint}\n\n"
            "For EACH lead, extract:\n"
            "- Company/Person name\n"
            "- Profile URL (if available — look for linkedin.com/in/, discord handles, reddit usernames, twitter handles)\n"
            "- Post/Content URL\n"
            "- What they need (pain point)\n"
            "- Why they're a good lead\n"
            "- Contact signal (named person, handle, email, etc.)\n\n"
            "Numbered list. Be concise. Only genuine leads.\n\n"
            f"Search: {search_query}\n\n"
            f"=== PAGES ===\n{combined_pages}\n\n"
            f"=== LINKS ===\n{combined_links}"
        )
        response = llm.chat([{"role": "user", "content": prompt}])

        # Store in memory for save command
        bridge = context.application.bot_data["bridge"]
        bridge.last_leads = response
        bridge.last_leads_query = raw_query

        site_label = f" on {site_filter}" if site_filter else ""
        header = f"🎯 Leads for: {query}{site_label}\n\n"
        full_response = header + response
        for part in bridge._split_message(full_response):
            await update.message.reply_text(part)

    except Exception as exc:
        await update.message.reply_text(f"❌ Leads search failed: {exc}")


@auth_required
async def save_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bridge = context.application.bot_data.get("bridge")
    if not bridge or not bridge.last_leads:
        await update.message.reply_text("No leads to save. Run a leads search first.")
        return

    try:
        from pathlib import Path
        from datetime import datetime
        import re

        leads_dir = Path(__file__).resolve().parents[2] / "data" / "leads"
        leads_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_query = re.sub(r'[^\w\s-]', '', bridge.last_leads_query)[:30].strip().replace(' ', '_')
        filename = f"leads_{safe_query}_{timestamp}.txt"
        filepath = leads_dir / filename

        content = (
            f"Query: {bridge.last_leads_query}\n"
            f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"{'='*60}\n\n"
            f"{bridge.last_leads}\n"
        )
        filepath.write_text(content, encoding="utf-8")
        await update.message.reply_text(f"✅ Leads saved to {filepath.name}")
    except Exception as exc:
        await update.message.reply_text(f"❌ Save failed: {exc}")



@auth_required
async def mode_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip().lower()
    # If text has leading slash, strip it
    if text.startswith("/"):
        text = text[1:]
    parts = text.split()
    bridge = context.application.bot_data["bridge"]
    user_id = update.effective_user.id

    if len(parts) == 1:
        mode = bridge.get_mode(user_id)
        await update.message.reply_text(f"Current mode: {mode}\n\nModes:\n  basic - Fetch raw text\n  smart - LLM extracts structured data\n  continuous - Auto-monitor for changes")
    elif len(parts) >= 2:
        new_mode = parts[1]
        if new_mode in ("basic", "smart", "continuous"):
            bridge.set_mode(user_id, new_mode)
            await update.message.reply_text(f"✅ Switched to {new_mode} mode")
        else:
            await update.message.reply_text("Invalid mode. Use: basic, smart, or continuous")


@auth_required
async def scrape_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text.startswith("/"):
        text = text[1:]
    parts = text.split(None, 1)
    if len(parts) < 2:
        await update.message.reply_text("Usage: scrape <url>")
        return

    url = parts[1].strip()
    bridge = context.application.bot_data["bridge"]
    user_id = update.effective_user.id
    mode = bridge.get_mode(user_id)

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    try:
        from archangel.agents.scraper import SmartScraper
        scraper = SmartScraper()

        if mode == "basic":
            raw = scraper.fetch_text(url)
            if raw.startswith("Error:"):
                await update.message.reply_text(f"❌ {raw}")
                return
            for part in bridge._split_message(raw):
                await update.message.reply_text(part)

        elif mode == "smart":
            raw = scraper.fetch_text(url)
            if raw.startswith("Error:"):
                await update.message.reply_text(f"❌ {raw}")
                return
            prompt = (
                "Extract and summarize the key information from this web page. "
                "Return structured data: title, main content, key points, links. "
                "Be concise but thorough.\n\n"
                f"Page content:\n{raw[:8000]}"
            )
            response = bridge.llm.chat([{"role": "user", "content": prompt}])
            for part in bridge._split_message(response):
                await update.message.reply_text(part)

        elif mode == "continuous":
            result = bridge.monitor.add(url)
            await update.message.reply_text(result)

    except Exception as exc:
        await update.message.reply_text(f"❌ Scrape error: {exc}")


@auth_required
async def watch_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text.startswith("/"):
        text = text[1:]
    parts = text.split(None, 1)
    if len(parts) < 2:
        await update.message.reply_text("Usage: watch <url>")
        return
    bridge = context.application.bot_data["bridge"]
    result = bridge.monitor.add(parts[1].strip())
    await update.message.reply_text(result)


@auth_required
async def unwatch_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text.startswith("/"):
        text = text[1:]
    parts = text.split(None, 1)
    if len(parts) < 2:
        await update.message.reply_text("Usage: unwatch <url>")
        return
    bridge = context.application.bot_data["bridge"]
    result = bridge.monitor.remove(parts[1].strip())
    await update.message.reply_text(result)


@auth_required
async def watches_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bridge = context.application.bot_data["bridge"]
    watchers = bridge.monitor.watchers
    if not watchers:
        await update.message.reply_text("No URLs being watched.")
        return
    lines = ["👀 Watched URLs:"]
    for url in watchers:
        lines.append(f"• {url}")
    await update.message.reply_text("\n".join(lines))


# --- Smart Router ---

@auth_required
async def smart_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Route plain text messages to the right handler. No / prefix required."""
    if not update.message or not update.message.text:
        return

    text = update.message.text.strip()

    # Strip leading / if present
    if text.startswith("/"):
        text = text[1:]

    lower = text.lower()

    # Command dispatch
    if lower == "start" or lower.startswith("start "):
        return await start_handler(update, context)
    if lower == "status" or lower.startswith("status "):
        return await status_handler(update, context)
    if lower == "clear" or lower.startswith("clear "):
        return await clear_handler(update, context)
    if lower == "help" or lower.startswith("help "):
        return await help_handler(update, context)
    if lower == "scan" or lower.startswith("scan "):
        return await scan_handler(update, context)
    if lower.startswith("search "):
        return await search_handler(update, context)
    if lower.startswith("leads "):
        return await leads_handler(update, context)
    if lower == "save":
        return await save_handler(update, context)
    if lower.startswith("mode"):
        return await mode_handler(update, context)
    if lower.startswith("scrape "):
        return await scrape_handler(update, context)
    if lower.startswith("watch "):
        return await watch_handler(update, context)
    if lower.startswith("unwatch "):
        return await unwatch_handler(update, context)
    if lower == "watches":
        return await watches_handler(update, context)

    # Default: chat with AI
    if not update.message or not update.message.text:
        return
    bridge = context.application.bot_data.get("bridge")
    if not bridge:
        await update.message.reply_text("❌ Bridge not initialized.")
        return

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    try:
        responses = await bridge.handle_message(update.effective_user.id, update.message.text)
        for resp in responses:
            await update.message.reply_text(resp)
    except Exception as exc:
        logger.error("Message handler failed: %s", exc)
        await update.message.reply_text(f"❌ Error: {exc}")


# --- Bot Builder ---

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

    # Single handler — smart router handles everything
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, smart_router))
    # Also catch /commands through the same router
    app.add_handler(MessageHandler(filters.COMMAND, smart_router))

    return app
