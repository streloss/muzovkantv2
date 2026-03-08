import discord
from discord.ext import commands, tasks
import json
import random
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class StatusRotator(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.statuses: list[str] = []
        self.current_index = 0
        self.status_file = 'data/statuses.json'
        
    async def cog_load(self):
        await self.load_statuses()
        self.rotate_status.start()
        logger.info("[StatusRotator] status rotator initialized")
    
    async def load_statuses(self):
        try:
            with open(self.status_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.statuses = data.get('statuses', [])

                logger.info(f"[StatusRotator] loaded {len(self.statuses)} statuses")
                
        except FileNotFoundError:
            logger.error(f"[StatusRotator] file {self.status_file} notfound")
        except json.JSONDecodeError:
            logger.error(f"[StatusRotaror] err while parsing JSON")
    
    def get_random_status(self) -> str:
        return random.choice(self.statuses)
    
    def get_next_status(self) -> str:
        status = self.statuses[self.current_index]
        self.current_index = (self.current_index + 1) % len(self.statuses)
        return status
    
    async def update_status(self, status_text: Optional[str] = None):
        if status_text is None:
            status_text = self.get_random_status()
        
        activity = discord.Game(name=status_text)
        
        try:
            await self.bot.change_presence(activity=activity)
            logger.debug(f"[StatusRotator] status updated: {status_text}")
        except Exception as e:
            logger.error(f"[StatusRotator] err while updating status: {e}")
    
    @tasks.loop(minutes=1.0)
    async def rotate_status(self):
        await self.update_status()
    
    @rotate_status.before_loop
    async def before_rotate_status(self):
        await self.bot.wait_until_ready()


async def setup(bot):
    await bot.add_cog(StatusRotator(bot))