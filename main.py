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

intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True
intents.members = True
intents.guilds = True
intents.messages = True
intents.voice_states = True

class Bot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix='!',
            intents=intents,
            help_command=None,
        )
    
    async def setup_hook(self):
        # ! load cogs
        await self.load_extension('cogs.role_manager')
        await self.load_extension('cogs.status_rotator')
        await self.load_extension('cogs.funchosa_parser')
        await self.load_extension('cogs.uptime')
        await self.load_extension('cogs.help')
        await self.load_extension('cogs.kitty')
        #await self.load_extension('cogs.muter') # ass
        # adding new modules:
        # await self.load_extension('cogs.whyrureadingts')
        
        await self.tree.sync()
    
    async def on_ready(self):
        print(f"bot initialized succesfully with user '{self.user}'")
        print(f"user.id: '{self.user.id}'")
        print('initialization (probably) complete; further is logs.')
        print('\n*------*\n')

async def main():
    bot = Bot()
    await bot.start(config.TOKEN)

if __name__ == "__main__":
    asyncio.run(main())