import discord
from discord.ext import commands

class HelpCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.command(name="help")
    async def help(self, ctx):
        help_text = """
комманды:

```
uptime : сколько времени прошло с запуска бота
funchosarand <id> : рандомная пикча из фунчозы либо по айдишнику в базе
funchosainfo : фунчоза.статы
kitty : рандомная пикча кошечки из [thecatapi](https://thecatapi.com/)
```

префикс: `!`
в лс отпишите по предложениям че в бота докинуть
        """
        
        await ctx.send(help_text)

async def setup(bot):
    await bot.add_cog(HelpCog(bot))