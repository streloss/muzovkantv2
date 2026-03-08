import discord
from discord.ext import commands
import aiohttp
import os
import logging

logger = logging.getLogger(__name__)

class Kitty(commands.Cog, name="Котики"):
    def __init__(self, bot):
        self.bot = bot
        self.api_key = os.environ.get('CAT_API_KEY')
        self.search_url = "https://api.thecatapi.com/v1/images/search"
        
        if not self.api_key:
            logger.warning("[Kitty] no api key found")

    async def _fetch_random_cat(self):
        headers = {"Content-Type": "application/json"}
        
        if self.api_key and self.api_key != "DEMO-API-KEY":
            headers["x-api-key"] = self.api_key 
        else:
            headers["x-api-key"] = "DEMO-API-KEY" 

        params = {
            'size': 'med',
            'mime_types': 'jpg,png',
            'format': 'json',
            'has_breeds': 'true',
            'order': 'RANDOM',
            'limit': 1
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.search_url, headers=headers, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data and isinstance(data, list):
                            logger.info(f"[Kitty] API response received")
                            return data[0]
                    else:
                        logger.error(f"[Kitty] api err: {response.status}")

                        try:
                            error_text = await response.text()
                            logger.error(f"[Kitty] api error text: {error_text}")
                        except:
                            pass
        except aiohttp.ClientError as e:
            logger.error(f"[Kitty] client error when contacting api: {e}")
        except Exception as e:
            logger.error(f"[Kitty] err: {e}")
        return None

    @commands.hybrid_command(name="kitty", description="kitty")
    async def kitty(self, ctx):
        await ctx.defer()
        logger.info(f"[Kitty] kitty request from {ctx.author.name} ({ctx.author.id})")

        cat_data = await self._fetch_random_cat()

        if not cat_data:
            logger.warning("[Kitty] cat_data = null")
            await ctx.send("помоему чет поломалось. меня пингани ||not cat_data||")
            return

        image_url = cat_data.get('url')
        if not image_url:
            logger.error("[Kitty] no image url")
            await ctx.send("помоему чет поломалось. меня пингани ||no image url||")
            return

        
        breeds_info = cat_data.get('breeds')
        if breeds_info and len(breeds_info) > 0:
            breed = breeds_info[0]
            if breed.get('name'):
                caption = f"{breed['name']}"
                logger.info(f"[Kitty] Breed found: {breed['name']}")

        await ctx.send(f"random kitty of the day\n[{caption}]({image_url})")
        logger.info(f"[Kitty] succesfully send kitty to {ctx.author.name}")

async def setup(bot):
    await bot.add_cog(Kitty(bot))