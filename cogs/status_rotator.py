import discord
from discord.ext import commands, tasks
import json
import random
import logging
from typing import Optional
import asyncio

logger = logging.getLogger(__name__)


class StatusRotator(commands.Cog):
    def __init__(self, bot, *, status_file: str = 'data/statuses.json', interval: float = 1.0):
        self.bot = bot
        self.statuses: list[str] = []
        self.current_index = 0
        self.status_file = status_file
        self.rotate_status.change_interval(minutes=interval)

    async def cog_load(self):
        await self.load_statuses()
        logger.info("Status rotator initialized with %d statuses", len(self.statuses))
        asyncio.ensure_future(self._startup())

    async def _startup(self):
        await self.bot.wait_until_ready()
        self.rotate_status.start()

    async def cog_unload(self):
        self.rotate_status.cancel()

    async def load_statuses(self):
        try:
            with open(self.status_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self.statuses = data.get('statuses', [])
            logger.info("Loaded %d statuses", len(self.statuses))
        except FileNotFoundError:
            logger.error("Status file not found: %s", self.status_file)
        except json.JSONDecodeError:
            logger.error("Failed to parse JSON in: %s", self.status_file)

    def get_next_status(self) -> Optional[str]:
        if not self.statuses:
            return None
        status = self.statuses[self.current_index]
        self.current_index = (self.current_index + 1) % len(self.statuses)
        return status

    def get_random_status(self) -> Optional[str]:
        if not self.statuses:
            return None
        return random.choice(self.statuses)

    async def update_status(self, status_text: Optional[str] = None):
        if not self.statuses:
            logger.warning("No statuses loaded, skipping update")
            return

        if status_text is None:
            status_text = self.get_next_status()

        try:
            await self.bot.change_presence(activity=discord.Game(name=status_text))
            logger.debug("Status updated: %s", status_text)
        except Exception as e:
            logger.error("Failed to update status: %s", e)

    @tasks.loop(minutes=1.0)
    async def rotate_status(self):
        await self.update_status()

    @rotate_status.before_loop
    async def before_rotate_status(self):
        await self.bot.wait_until_ready()


async def setup(bot):
    await bot.add_cog(StatusRotator(bot))