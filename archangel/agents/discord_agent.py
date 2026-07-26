"""Discord Bot Lead Monitor for Archangel using official discord.py API."""

import os
import logging
import discord
from archangel.storage import StorageBackend
from archangel.models import RawPost, LeadAnalysis, LeadScore
from archangel.agents.scraper import SmartScraper

logger = logging.getLogger(__name__)


class DiscordLeadMonitor(discord.Client):
    """Listens for live job/gig opportunities in configured Discord channels."""

    def __init__(self, target_channel_ids: list[int] = None, *args, **kwargs):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(intents=intents, *args, **kwargs)

        self.target_channel_ids = set(target_channel_ids or [])
        self.storage = StorageBackend.get_instance()
        self.scraper = SmartScraper()
        self.channel_names = ("hiring", "gigs", "freelance", "jobs", "paid-work", "job-board", "opportunities")

    async def on_ready(self):
        logger.info("Discord Lead Monitor logged in as %s (ID: %s)", self.user.name, self.user.id)
        print(f"🤖 Discord Lead Monitor online as: {self.user.name}")
        print(f"📡 Monitoring {len(self.guilds)} server(s) for client leads...")

    async def on_message(self, message: discord.Message):
        # Ignore bot's own messages or other bots
        if message.author.bot:
            return

        # Check if message is in a monitored channel ID or matching channel name
        ch_name = getattr(message.channel, "name", "").lower()
        is_target = (
            message.channel.id in self.target_channel_ids
            or any(target in ch_name for target in self.channel_names)
        )

        if not is_target:
            return

        title = message.content.split("\n")[0][:100]
        body = message.content

        # Filter supply-side promos and enforce buyer intent
        if self.scraper._is_supply_side(title):
            return

        if not self.scraper._has_buyer_intent(title, body):
            return

        guild_name = message.guild.name if message.guild else "Direct"
        post_url = message.jump_url

        logger.info("Discovered live Discord lead in #%s (%s): %s", ch_name, guild_name, title)
        print(f"\n🎯 [DISCORD LEAD] #{ch_name} ({guild_name}): {title}")
        print(f"   🔗 {post_url}")
        print(f"   👤 Author: {message.author.name}")

        # Store lead into Archangel DB
        try:
            raw_post = RawPost(
                source="discord",
                channel=f"{guild_name}/#{ch_name}",
                author=f"{message.author.name}",
                content=f"{title}\n{body}",
                timestamp=message.created_at.timestamp(),
                url=post_url,
                metadata={"channel_id": message.channel.id, "guild_id": message.guild.id if message.guild else None},
            )
            raw_id = self.storage.store_raw_post(raw_post)
            if raw_id:
                analysis = LeadAnalysis(
                    raw_post_id=raw_id,
                    is_lead=True,
                    confidence=0.90,
                    estimated_budget="Variable",
                    urgency="High",
                    category="discord-job",
                    reasoning="Live Discord message in job channel",
                )
                analysis_id = self.storage.store_analysis(analysis)
                if analysis_id:
                    score = LeadScore(analysis_id=analysis_id, score=90.0, confidence_score=0.90)
                    self.storage.store_score(score)
        except Exception as exc:
            logger.error("Failed to store Discord lead: %s", exc)


def start_discord_monitor(token: str | None = None, channel_ids: list[int] = None):
    """Start Discord bot monitor event loop."""
    bot_token = token or os.getenv("DISCORD_BOT_TOKEN")
    if not bot_token:
        raise ValueError("DISCORD_BOT_TOKEN environment variable or token parameter is required.")

    monitor = DiscordLeadMonitor(target_channel_ids=channel_ids)
    monitor.run(bot_token)
