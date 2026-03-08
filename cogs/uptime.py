import discord
from discord.ext import commands
import datetime

class UptimeSimple(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.start_time = None
    
    @commands.Cog.listener()
    async def on_ready(self):
        if self.start_time is None:
            self.start_time = datetime.datetime.now(datetime.timezone.utc)
    
    @commands.command(name="uptime")
    async def uptime(self, ctx):
        if self.start_time is None:
            await ctx.send("ебать у тебя тайминги кнш")
            return
        
        current_time = datetime.datetime.now(datetime.timezone.utc)
        uptime = current_time - self.start_time
        seconds = int(uptime.total_seconds())
        
        days = seconds // 86400
        hours = (seconds % 86400) // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        
        result = "бот работает уже: "
        parts = []
        
        if days > 0:
            parts.append(f"{days} дня")
        if hours > 0:
            parts.append(f"{hours} часа")
        if minutes > 0:
            parts.append(f"{minutes} минут")
        if secs > 0 or not parts:
            parts.append(f"{secs} секунд")
        
        result += " ".join(parts)
        await ctx.send(result)

async def setup(bot):
    await bot.add_cog(UptimeSimple(bot))