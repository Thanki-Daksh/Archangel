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
        "  leads <query> [site:<platform>] - Find leads (describe naturally)\n"
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


def _parse_leads_query(raw: str) -> dict:
    """Use LLM to parse user's raw message into structured search fields."""
    import json
    import re
    from archangel.agents.chat import LLMClient

    llm = LLMClient()
    prompt = (
        "Parse this user message into structured fields for a web search. Return ONLY valid JSON.\n\n"
        "Fields:\n"
        "- query: search terms that will find REAL USER POSTS (not blogs, not directories, not marketing)\n"
        "- site: the domain to search on (e.g. linkedin.com, reddit.com, x.com, discord.com) or null\n"
        "- instructions: extra requirements (budget, timing, comment count, post age, etc.) or null\n\n"
        "CRITICAL RULES for query:\n"
        "- Query must target REAL PEOPLE asking for help or expressing need\n"
        "- Good: 'looking for discord bot developer', 'need automation help', 'frustrated with manual process'\n"
        "- Bad: 'easy discord bots' (returns bot directories), 'AI automation' (returns blog posts)\n"
        "- Think: what would someone ACTUALLY TYPE when they need this service?\n"
        "- Use action words: 'looking for', 'need', 'help with', 'want to hire', 'frustrated with'\n"
        "- Keep query SHORT (3-6 words max)\n\n"
        "Site mapping:\n"
        "- X/Twitter → x.com\n"
        "- Reddit → reddit.com\n"
        "- Discord → discord.com\n"
        "- LinkedIn → linkedin.com\n"
        "- GitHub → github.com\n"
        "- Or any raw domain\n\n"
        f"User message: {raw}\n\n"
        'Return JSON: {"query": "...", "site": "...", "instructions": "..."}'
    )

    response = llm.chat([{"role": "user", "content": prompt}])

    json_match = re.search(r'\{.*\}', response, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass
    return {"query": raw, "site": None, "instructions": None}


@auth_required
async def leads_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text.startswith("/"):
        text = text[1:]
    parts = text.split(None, 1)
    if len(parts) < 2:
        await update.message.reply_text(
            'Usage: leads <query> [site:<platform>]\n\n'
            'Just describe what you want naturally:\n'
            '  leads "AI automation" site:discord\n'
            '  leads easy discord bots site: X budget 300-1000$, early posts, zero comments\n'
            '  leads python freelance work\n\n'
            'Supported sites: linkedin, reddit, discord, x, github, stackoverflow, medium\n'
            'Or use any domain: site:customsite.com'
        )
        return

    raw_query = parts[1].strip().strip('"').strip("'")

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    try:
        from archangel.agents.chat import WebSearch, LLMClient
        from archangel.agents.scraper import SmartScraper
        import re

        # Step 1: LLM parses the raw message
        parsed = _parse_leads_query(raw_query)
        search_terms = parsed.get("query", raw_query)
        site_domain = parsed.get("site")
        instructions = parsed.get("instructions")

        # Step 2: Build clean search query
        if site_domain:
            search_query = f'{search_terms} site:{site_domain}'
        else:
            search_query = search_terms

        # Step 3: Search
        results = WebSearch().search(search_query, max_results=5)
        urls = re.findall(r'URL:\s*(https?://[^\s]+)', results)

        if not urls:
            await update.message.reply_text("No results found.")
            return

        # Step 4: Scrape URLs
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

        # Step 5: Context hint based on site
        if site_domain:
            if "discord" in site_domain:
                context_hint = "Look for people asking for help, seeking automation services, or discussing pain points in Discord servers."
            elif "reddit" in site_domain:
                context_hint = "Look for Reddit threads where people are asking for recommendations, expressing frustration, or seeking automation solutions."
            elif "linkedin" in site_domain:
                context_hint = "Look for LinkedIn posts or articles where companies express AI automation needs or executives discuss digital transformation."
            elif "x.com" in site_domain or "twitter" in site_domain:
                context_hint = "Look for tweets expressing pain points, asking for recommendations, or discussing automation needs."
            elif "github" in site_domain:
                context_hint = "Look for GitHub issues, discussions, or repos where people need automation help."
            elif "stackoverflow" in site_domain:
                context_hint = "Look for StackOverflow questions where people struggle with automation or repetitive tasks."
            else:
                context_hint = f"Look for people or companies on {site_domain} showing interest in or need for AI automation services."
        else:
            context_hint = "Find people or companies showing interest in or need for AI automation services."

        # Step 6: LLM extracts leads
        llm = LLMClient()
        combined_pages = "\n\n---\n\n".join(pages)
        combined_links = "\n\n".join(all_links) if all_links else "No additional links found."

        prompt = (
            f"Analyze these search results and extract potential leads for an AI automation service.\n"
            f"{context_hint}\n\n"
        )
        if instructions:
            prompt += f"User's specific requirements: {instructions}\n\n"

        prompt += (
            "For EACH lead, extract:\n"
            "- Company/Person name\n"
            "- Profile URL (linkedin.com/in/, discord handle, reddit username, twitter handle, etc.)\n"
            "- Post/Content URL\n"
            "- What they need (pain point)\n"
            "- Why they're a good lead\n"
            "- Contact signal (named person, handle, email, etc.)\n\n"
            "Numbered list. Be concise. Only genuine leads showing real interest or need.\n"
            "Skip irrelevant results (blog posts, directories, marketing content).\n\n"
            f"Search: {search_query}\n\n"
            f"=== PAGES ===\n{combined_pages}\n\n"
            f"=== LINKS ===\n{combined_links}"
        )
        response = llm.chat([{"role": "user", "content": prompt}])

        # Step 7: Store for save command
        bridge = context.application.bot_data["bridge"]
        bridge.last_leads = response
        bridge.last_leads_query = raw_query

        # Step 8: Send to Telegram
        site_label = f" on {site_domain}" if site_domain else ""
        header = f"🎯 Leads for: {search_terms}{site_label}\n\n"
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
