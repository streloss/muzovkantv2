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
        self.session: aiohttp.ClientSession | None = None

        if not self.api_key:
            logger.warning("No CAT_API_KEY found, using unauthenticated requests")

    async def cog_load(self):
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["x-api-key"] = self.api_key
        self.session = aiohttp.ClientSession(headers=headers)

    async def cog_unload(self):
        if self.session:
            await self.session.close()

    async def _fetch_random_cat(self):
        params = {
            'size': 'med',
            'mime_types': 'jpg,png',
            'format': 'json',
            'has_breeds': 'true',
            'order': 'RANDOM',
            'limit': 1,
        }
        try:
            async with self.session.get(self.search_url, params=params) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error("API error %s: %s", response.status, error_text)
                    return None

                data = await response.json()
                if not data or not isinstance(data, list):
                    logger.error("Unexpected API response format: %s", data)
                    return None

                return data[0]

        except aiohttp.ClientError as e:
            logger.error("HTTP client error: %s", e)
        except Exception as e:
            logger.error("Unexpected error fetching cat: %s", e)

        return None

    @commands.hybrid_command(name="kitty", description="kitty")
    async def kitty(self, ctx):
        await ctx.defer()
        logger.info("Kitty request from %s (%s)", ctx.author.name, ctx.author.id)

        cat_data = await self._fetch_random_cat()
        if not cat_data:
            await ctx.send("помоему чет поломалось. меня пингани ||not cat_data||")
            return

        image_url = cat_data.get('url')
        if not image_url:
            await ctx.send("помоему чет поломалось. меня пингани ||no image url||")
            return

        breeds = cat_data.get('breeds')
        breed_name = breeds[0].get('name') if breeds else None

        if breed_name:
            logger.info("Breed found: %s", breed_name)
            await ctx.send(f"random kitty of the day\n[{breed_name}]({image_url})")
        else:
            await ctx.send(f"random kitty of the day\n{image_url}")

        logger.info("Successfully sent kitty to %s", ctx.author.name)


async def setup(bot):
    await bot.add_cog(Kitty(bot))