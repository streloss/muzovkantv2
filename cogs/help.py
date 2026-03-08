import logging
from discord.ext import commands
import config

logger = logging.getLogger(__name__)


class HelpCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="help")
    async def help(self, ctx):
        await ctx.send(config.HELP_TEXT)
        logger.debug("Help requested by %s", ctx.author.name)


async def setup(bot):
    await bot.add_cog(HelpCog(bot))