import discord
from discord.ext import commands


def pluralize(n: int, one: str, few: str, many: str) -> str:
    if 11 <= n % 100 <= 14:
        return f"{n} {many}"
    r = n % 10
    if r == 1:
        return f"{n} {one}"
    if 2 <= r <= 4:
        return f"{n} {few}"
    return f"{n} {many}"


class UptimeSimple(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.start_time = discord.utils.utcnow()

    @commands.command(name="uptime")
    async def uptime(self, ctx):
        delta = discord.utils.utcnow() - self.start_time
        seconds = int(delta.total_seconds())
        minutes, secs = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)
        days, hours = divmod(hours, 24)

        parts = []
        if days:
            parts.append(pluralize(days, "день", "дня", "дней"))
        if hours:
            parts.append(pluralize(hours, "час", "часа", "часов"))
        if minutes:
            parts.append(pluralize(minutes, "минуту", "минуты", "минут"))
        if secs or not parts:
            parts.append(pluralize(secs, "секунду", "секунды", "секунд"))

        embed = discord.Embed(
            description="бот работает уже: " + " ".join(parts),
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(UptimeSimple(bot))