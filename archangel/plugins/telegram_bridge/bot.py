"""Telegram bot handlers with smart text routing."""

import asyncio
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

SUPPLY_PLATFORMS = [
    "fiverr.com", "upwork.com", "freelancer.com", "toptal.com",
    "guru.com", "peopleperhour.com", "99designs.com", "angelo.com",
    "contra.com", "freelancermap.com", "gun.io", "arc.dev",
    "turing.com", "andela.com", "braintrust.com", "wellfound.com",
    "yunojuno.com", "staff.com",
]


class ProgressIndicator:
    """Animated progress indicator using a live Telegram message."""

    def __init__(self, message):
        self.message = message

    async def update(self, text: str):
        try:
            await self.message.edit_text(text)
        except Exception:
            pass

    async def done(self):
        """Delete the progress message."""
        try:
            await self.message.delete()
        except Exception:
            pass

    async def error(self, text: str, delay: float = 3.0):
        """Show error text then delete after delay."""
        try:
            await self.message.edit_text(text)
            await asyncio.sleep(delay)
            await self.message.delete()
        except Exception:
            pass


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
        "  help - Show this message\n"
        "\n"
        "Discord Integration:\n"
        "  discord servers - List your Discord servers\n"
        "  discord join <id> - Join a server\n"
        "  discord leave <id> - Leave a server\n"
        "  discord monitor <id> - Monitor server for leads\n"
        "\n"
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
    """Use LLM to generate X/Twitter search queries targeting complaint language."""
    import json
    import re
    from archangel.agents.chat import LLMClient

    llm = LLMClient()
    prompt = (
        "Generate 5 X/Twitter search queries to find people COMPLAINING about a manual process.\n"
        f"Target: {raw}\n\n"
        "People who NEED help complain. They don't ask neatly.\n"
        "GOOD complaint patterns:\n"
        "- 'tired of doing X manually'\n"
        "- 'X is so frustrating'\n"
        "- 'wish there was a way to automate X'\n"
        "- 'spending hours on X every day'\n"
        "- 'X keeps breaking help'\n"
        "- 'anyone else struggle with X'\n"
        "- 'need better tool for X'\n"
        "- 'manual X is killing me'\n\n"
        "AVOID these (supply-side magnets):\n"
        "- 'anyone know how to' (attracts tutorials)\n"
        "- 'looking for developer' (attracts freelancers)\n"
        "- 'need help with' (attracts agencies)\n\n"
        'Return JSON: {"queries": ["q1","q2","q3","q4","q5"], "alternatives": ["alt1","alt2"]}'
        "\nNo subreddits needed — X/Twitter only."
    )

    response = llm.chat([{"role": "user", "content": prompt}])

    json_match = re.search(r'\{.*\}', response, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass
    return {
        "queries": [f"tired of doing {raw} manually", f"{raw} is so frustrating", f"wish there was a way to automate {raw}", f"spending hours on {raw}", f"{raw} keeps breaking"],
        "alternatives": [f"manual {raw} is killing me", f"anyone else struggle with {raw}"],
    }


SUPPLY_SIGNALS = [
    "we offer", "our services", "hire us", "contact us", "contact me",
    "dm me", "dm for", "message me", "shoot me a",
    "comment below", "check my", "link in bio", "book a call",
    "schedule a", "let's connect", "let's talk", "drop a dm",
    "i build", "i create", "i develop", "we build", "we provide", "we deliver",
    "my portfolio", "my agency", "our agency", "what we do",
    "what i offer", "services include", "we specialize",
    "available for hire", "open to work", "looking for clients",
    "freelance", "consulting", "let me know if you need",
    "follow for more", "subscribe", "join my", "free consultation",
    "limited spots", "dm for info", "price list", "starting at",
    "pricing", "get a quote", "get started", "sign up",
]


def _is_supply_side(content: str) -> bool:
    lower = content.lower()
    matches = sum(1 for signal in SUPPLY_SIGNALS if signal in lower)
    return matches >= 2


def _filter_supply(combined_content: str) -> str:
    sections = combined_content.split("---\n")
    clean = []
    for sec in sections:
        sec = sec.strip()
        if not sec:
            continue
        if _is_supply_side(sec):
            continue
        clean.append(sec)
    return "\n---\n".join(clean)


def _build_combined_content(scraper, queries, alternatives):
    """Search X/Twitter only. Runs 5 queries (3 primary + 2 alternative), dedups, returns up to 15 tweets."""
    all_urls_seen = set()
    combined = ""
    tweets = []

    for q in queries[:3]:
        results = scraper.fetch_x_search_via_ddg(q, max_results=5)
        for t in results:
            if t['url'] not in all_urls_seen:
                all_urls_seen.add(t['url'])
                tweets.append(t)

    if len(tweets) < 3 and alternatives:
        for alt_q in alternatives[:2]:
            results = scraper.fetch_x_search_via_ddg(alt_q, max_results=5)
            for t in results:
                if t['url'] not in all_urls_seen:
                    all_urls_seen.add(t['url'])
                    tweets.append(t)

    if tweets:
        combined += "=== X/TWITTER POSTS ===\n"
        for t in tweets[:15]:
            author = t['url'].split('/')[3] if '/' in t.get('url', '') else '?'
            combined += (
                f"Author: @{author}\n"
                f"Profile: https://x.com/{author}\n"
                f"URL: {t['url']}\n"
                f"{t['content'][:1000]}\n---\n"
            )

    return combined, len(tweets)


@auth_required
async def leads_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text.startswith("/"):
        text = text[1:]
    parts = text.split(None, 1)
    if len(parts) < 2:
        await update.message.reply_text(
            'Usage: leads <what you need>\n\n'
            'Examples:\n'
            '  leads ai automation help\n'
            '  leads need python developer\n'
            '  leads discord bot help\n'
            'Just describe what you want built.'
        )
        return

    raw_query = parts[1].strip().strip('"').strip("'")
    status_msg = await update.message.reply_text("🔍 Parsing your request...")

    try:
        from archangel.agents.chat import LLMClient
        from archangel.agents.scraper import SmartScraper

        await status_msg.edit_text("🧠 Understanding what you need...")
        parsed = _parse_leads_query(raw_query)
        queries = parsed.get("queries", [raw_query])
        alternatives = parsed.get("alternatives", [])

        parse_log = f"✅ Parsed: {raw_query}"
        await status_msg.edit_text(parse_log)
        await asyncio.sleep(0.5)

        scraper = SmartScraper()

        # Step 1-2: Search X/Twitter only
        await status_msg.edit_text(f"{parse_log}\n\n🔍 Searching X/Twitter...")
        combined_content, tweet_count = _build_combined_content(
            scraper, queries, alternatives
        )

        # Step 3: Supply-side pre-filter
        filtered_content = _filter_supply(combined_content)

        if not filtered_content.strip():
            filtered_content = combined_content  # Use unfiltered if filter removes everything

        total_found = f"{tweet_count} tweets"
        await status_msg.edit_text(f"{parse_log}\n\n✅ Found {total_found}")

        # Step 4: LLM extracts leads — no SKIPPED output
        await status_msg.edit_text(f"{parse_log}\n\n💡 Analyzing leads with AI...")
        llm = LLMClient()

        def _run_llm(content, query, attempt=1):
            prompt = (
                "Extract demand-side leads from these posts.\n"
                "A lead is someone SEEKING help, a developer, or automation.\n"
                "Do NOT list posts you skipped. Only list actual leads.\n\n"
                "INCLUDE if the person is:\n"
                "- Asking for help or recommendations\n"
                "- Expressing frustration with a process\n"
                "- Looking to hire or contract someone\n"
                "- Questioning how to build/automate something\n"
                "- Mentioning a budget or timeline\n\n"
                "EXCLUDE silently (do not mention in output):\n"
                "- Service providers, agencies, freelancers offering help\n"
                "- Corporate accounts, product announcements\n"
                "- Educational content, tutorials, news\n\n"
                "FOR EACH LEAD:\n"
                "- @handle or u/username\n"
                "- Profile URL\n"
                "- Post URL\n"
                "- What they need (1 sentence)\n"
                "- Date\n\n"
                "Return ONLY leads. If genuinely zero leads exist, say:\n"
                "'Try: looking for developer to build [specific thing]'\n\n"
                f"Query: {query}\n\n"
                f"{content[:8000]}"
            )
            return llm.chat([{"role": "user", "content": prompt}])

        response = _run_llm(filtered_content, raw_query)

        # Step 5: Auto-retry with broader query if zero leads
        if "1." not in response and "http" not in response.lower():
            broader = f"tired of doing {raw_query} manually"
            await status_msg.edit_text(f"{parse_log}\n\n🔍 Trying broader: '{broader}'...")
            broader_scraper = SmartScraper()
            broader_combined, _ = _build_combined_content(
                broader_scraper, [broader], []
            )
            broader_filtered = _filter_supply(broader_combined)
            if broader_filtered.strip():
                response = _run_llm(broader_filtered, broader)

        # Step 6: Post-process
        response = _ensure_profile_urls(response)

        bridge = context.application.bot_data["bridge"]
        bridge.last_leads = response
        bridge.last_leads_query = raw_query

        lead_count = response.count("1. ")
        if lead_count > 0:
            done_text = f"✅ Found {lead_count} potential leads."
        else:
            done_text = "✅ Done."
        await status_msg.edit_text(f"{parse_log}\n\n{done_text}")
        await asyncio.sleep(1)
        await status_msg.delete()

        header = f"🎯 Leads for: {raw_query}\n\n"
        full_response = header + response
        for part in bridge._split_message(full_response):
            await update.message.reply_text(part)

    except Exception as exc:
        try:
            await status_msg.edit_text(f"❌ Error: {exc}")
            await asyncio.sleep(3)
            await status_msg.delete()
        except Exception:
            pass


def _ensure_profile_urls(text: str) -> str:
    """Post-process LLM response to ensure every lead has a profile URL."""
    import re
    lines = text.split('\n')
    result = []
    for line in lines:
        if '@' in line and 'Profile' not in line and 'http' not in line:
            handle_match = re.search(r'@(\w+)', line)
            if handle_match:
                handle = handle_match.group(1)
                line += f"\nProfile: https://x.com/{handle}"
        if 'u/' in line and 'Profile' not in line and 'reddit.com' not in line:
            user_match = re.search(r'u/(\w+)', line)
            if user_match:
                username = user_match.group(1)
                line += f"\nProfile: https://reddit.com/user/{username}"
        result.append(line)
    return '\n'.join(result)


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

    status_msg = await update.message.reply_text(f"⚙️ Scraping {url}...")
    progress = ProgressIndicator(status_msg)

    try:
        from archangel.agents.scraper import SmartScraper
        scraper = SmartScraper()

        if mode == "basic":
            await progress.update("⚙️ Fetching page content...")
            raw = scraper.fetch_text(url)
            if raw.startswith("Error:"):
                await progress.error(f"❌ {raw}")
                return
            await progress.done()
            for part in bridge._split_message(raw):
                await update.message.reply_text(part)

        elif mode == "smart":
            await progress.update("⚙️ Fetching page content...")
            raw = scraper.fetch_text(url)
            if raw.startswith("Error:"):
                await progress.error(f"❌ {raw}")
                return
            await progress.update("💡 Analyzing with AI...")
            prompt = (
                "Extract and summarize the key information from this web page. "
                "Return structured data: title, main content, key points, links. "
                "Be concise but thorough.\n\n"
                f"Page content:\n{raw[:8000]}"
            )
            response = bridge.llm.chat([{"role": "user", "content": prompt}])
            await progress.done()
            for part in bridge._split_message(response):
                await update.message.reply_text(part)

        elif mode == "continuous":
            await progress.update("⚙️ Adding to watch list...")
            result = bridge.monitor.add(url)
            await progress.update(f"✅ {result}")
            await asyncio.sleep(2)
            await progress.done()

    except Exception as exc:
        await progress.error(f"❌ Scrape error: {exc}")


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


# --- Discord Command Handlers ---

@auth_required
async def discord_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle all discord subcommands."""
    text = update.message.text.strip()
    if text.startswith("/"):
        text = text[1:]
    parts = text.split()

    if len(parts) < 2 or parts[1] == "help":
        await update.message.reply_text(
            "Discord Commands:\n"
            "  discord servers - List your servers\n"
            "  discord join <id> - Join a server\n"
            "  discord leave <id> - Leave a server\n"
            "  discord monitor <id> - Monitor for leads"
        )
        return

    subcommand = parts[1].lower()

    if subcommand == "servers":
        status_msg = await update.message.reply_text("🔍 Fetching your Discord servers...")
        try:
            from archangel.agents.composio_discord import ComposioDiscord
            discord = ComposioDiscord()
            servers = discord.list_servers()

            if not servers:
                await status_msg.edit_text("❌ No servers found. Check COMPOSIO_API_KEY in .env")
                return

            lines = ["📋 Your Discord Servers:\n"]
            for i, server in enumerate(servers[:20], 1):
                name = server.get("name", "Unknown")
                gid = server.get("id", "?")
                lines.append(f"{i}. {name}\n   ID: {gid}")

            await status_msg.edit_text("\n".join(lines))
        except Exception as e:
            await status_msg.edit_text(f"❌ Error: {e}")

    elif subcommand == "join":
        if len(parts) < 3:
            await update.message.reply_text("Usage: discord join <server_id>")
            return
        guild_id = parts[2]
        status_msg = await update.message.reply_text(f"🔍 Joining server {guild_id}...")
        try:
            from archangel.agents.composio_discord import ComposioDiscord
            discord = ComposioDiscord()
            result = discord.join_server(guild_id)
            if result["success"]:
                await status_msg.edit_text("✅ Joined server!")
            else:
                await status_msg.edit_text(f"❌ Failed: {result.get('error', 'Unknown error')}")
        except Exception as e:
            await status_msg.edit_text(f"❌ Error: {e}")

    elif subcommand == "leave":
        if len(parts) < 3:
            await update.message.reply_text("Usage: discord leave <server_id>")
            return
        guild_id = parts[2]
        status_msg = await update.message.reply_text(f"🔍 Leaving server {guild_id}...")
        try:
            from archangel.agents.composio_discord import ComposioDiscord
            discord = ComposioDiscord()
            result = discord.leave_server(guild_id)
            if result["success"]:
                await status_msg.edit_text("✅ Left server!")
            else:
                await status_msg.edit_text(f"❌ Failed: {result.get('error', 'Unknown error')}")
        except Exception as e:
            await status_msg.edit_text(f"❌ Error: {e}")

    elif subcommand == "monitor":
        if len(parts) < 3:
            await update.message.reply_text("Usage: discord monitor <server_id>")
            return
        guild_id = parts[2]
        status_msg = await update.message.reply_text(f"🔍 Monitoring server {guild_id}...")
        try:
            from archangel.agents.composio_discord import ComposioDiscord
            from archangel.agents.chat import LLMClient
            import asyncio
            import re

            discord = ComposioDiscord()
            channels = discord.get_channels(guild_id)
            text_channels = [c for c in channels if c.get("type") == 0]

            if not text_channels:
                await status_msg.edit_text("❌ No text channels found.")
                return

            all_messages = []
            for ch in text_channels[:5]:
                ch_id = ch.get("id")
                ch_name = ch.get("name", "?")
                msgs = discord.get_messages(ch_id, limit=20)
                for m in msgs:
                    m["channel_name"] = ch_name
                all_messages.extend(msgs)

            if not all_messages:
                await status_msg.edit_text("❌ No messages found.")
                return

            await status_msg.edit_text(f"✅ Fetched {len(all_messages)} messages.\n💡 Analyzing for leads...")

            llm = LLMClient()
            messages_text = "\n\n".join([
                f"#{m.get('channel_name', '?')} | u/{m.get('author', {}).get('username', '?')}: {m.get('content', '')[:200]}"
                for m in all_messages[:50]
            ])

            prompt = (
                "Extract demand-side leads from these Discord messages.\n"
                "Only include people SEEKING help, not offering services.\n"
                "Skip bots, moderators, corporate accounts.\n"
                "Only last 5 days.\n\n"
                "For each lead: username, channel, what they need, why good lead.\n\n"
                f"Messages:\n{messages_text}"
            )
            response = llm.chat([{"role": "user", "content": prompt}])

            bridge = context.application.bot_data["bridge"]
            bridge.last_leads = response
            bridge.last_leads_query = f"Discord server {guild_id}"

            lead_count = len(re.findall(r'\d+\.\s', response))
            await status_msg.edit_text(f"✅ Done! Found ~{lead_count} leads.")
            await asyncio.sleep(1)
            await status_msg.delete()

            for part in bridge._split_message(f"🎯 Discord Leads from {guild_id}\n\n{response}"):
                await update.message.reply_text(part)
        except Exception as e:
            await status_msg.edit_text(f"❌ Error: {e}")


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

    # Discord commands (unified handler)
    if lower.startswith("discord"):
        return await discord_handler(update, context)

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
