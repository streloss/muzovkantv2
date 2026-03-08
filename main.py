import discord
from discord.ext import commands
import config
import asyncio
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True
intents.members = True
intents.guilds = True
intents.messages = True

COGS = [
    #! cogs to load
    'cogs.role_manager',
    'cogs.status_rotator',
    'cogs.funchosa_parser',
    'cogs.uptime',
    'cogs.help',
    'cogs.kitty',
]


class Bot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix='!',
            intents=intents,
            help_command=None,
        )

    async def setup_hook(self):
        for cog in COGS:
            try:
                await self.load_extension(cog)
                logger.info("Loaded cog: %s", cog)
            except Exception as e:
                logger.error("Failed to load cog %s: %s", cog, e, exc_info=True)

        await self.tree.sync()

    async def on_ready(self):
        if not hasattr(self, '_ready'):
            self._ready = True
            logger.info("Bot ready: %s (id: %s)", self.user, self.user.id)


async def main():
    bot = Bot()
    await bot.start(config.TOKEN)


if __name__ == "__main__":
    asyncio.run(main())