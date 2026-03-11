## Improved code funchosa_parser.py by strelok and claude :D
# Удалён мёртвый build_funchosa_view()
# ensure_future → create_task
# if number → if number is not None (баг-фикс)
# Фильтрация вложений через is_image_url() с urlparse вместо .endswith()
# None-чек для last_id перед обновлением статуса
# total or 0 в funchosainfo на случай пустой БД
# Магические числа вынесены в именованные константы вверху файла

import os
import asyncio
import logging
from datetime import datetime
from typing import Optional
from urllib.parse import urlparse

import discord
from discord.ext import commands
from discord import app_commands

import config
from utils.database import FunchosaDatabase

logger = logging.getLogger(__name__)

MAX_ATTACHMENT_PREVIEW = 3
INCREMENTAL_PARSE_LIMIT = 250
LOG_EVERY_N_SAVED = 50
LOG_EVERY_N_SCANNED = 100
IMAGE_EXTENSIONS = frozenset(('.png', '.jpg', '.jpeg', '.gif', '.webp'))


def is_image_url(url: str) -> bool:
    path = urlparse(url).path
    return os.path.splitext(path)[1].lower() in IMAGE_EXTENSIONS


def build_funchosa_embed(message_data: dict) -> discord.Embed:
    embed = discord.Embed(
        description=message_data['content'] or "*[без текста]*",
        color=discord.Color.blue(),
        timestamp=datetime.fromisoformat(message_data['timestamp']),
    )
    embed.set_author(name='random фунчоза of the day')
    embed.add_field(
        name="info",
        value=(
            f"автор: <@{message_data['author_id']}>\n"
            f"дата: {message_data['timestamp'].replace('T', ' ')[:19]}\n"
            f"номер в базе: {message_data['id']}"
        ),
        inline=False,
    )

    if message_data.get('attachments'):
        links = [
            f"[вложение {i}]({att['url']})"
            for i, att in enumerate(message_data['attachments'][:MAX_ATTACHMENT_PREVIEW], 1)
        ]
        embed.add_field(name="вложения", value="\n".join(links), inline=False)

    return embed


class FunchosaView(discord.ui.View):
    def __init__(self, db: FunchosaDatabase, message_url: str):
        super().__init__(timeout=None)
        self.db = db
        self.add_item(discord.ui.Button(
            label="перейти к сообщению",
            url=message_url,
            style=discord.ButtonStyle.link,
        ))

    @discord.ui.button(label="подавай еще, раб", custom_id="another_random", style=discord.ButtonStyle.secondary)
    async def another_random(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()

        message_data = await self.db.get_random_message()
        if not message_data:
            await interaction.followup.send("помоему чет поломалось. меня пингани", ephemeral=True)
            return

        embed = build_funchosa_embed(message_data)
        view = FunchosaView(self.db, message_data['message_url'])
        await interaction.followup.send(embed=embed, view=view)


class FunchosaParser(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = FunchosaDatabase()
        self.target_channel_id = config.FUNCHOSA_CHANNEL_ID
        self.is_parsing = False
        self.parsed_count = 0

    async def cog_load(self):
        await self.db.init_db()
        logger.info("FunchosaParser initialized")
        asyncio.create_task(self._startup())

    async def _startup(self):
        await self.bot.wait_until_ready()
        await self.auto_parse_on_startup()

    async def auto_parse_on_startup(self):
        if self.is_parsing:
            logger.warning("Parsing already in progress, skipping startup parse")
            return

        channel = self.bot.get_channel(self.target_channel_id)
        if not channel:
            logger.warning("Channel with id %s not found", self.target_channel_id)
            return

        try:
            status = await self.db.get_parsing_status()
            is_first = not status['first_parse_done']
            limit = None if is_first else INCREMENTAL_PARSE_LIMIT
            logger.info("Starting %s parse", "full" if is_first else "incremental")

            count = await self._parse_history(channel, limit=limit)

            last_id = await self.db.get_last_message_in_db()
            if last_id is not None:
                await self.db.update_parsing_status(first_parse_done=True, last_parsed_message_id=last_id)

            logger.info("Parsing finished, %d new messages", count)

        except Exception as e:
            logger.error("Error during startup parse: %s", e, exc_info=True)

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return
        if self.target_channel_id and message.channel.id == self.target_channel_id:
            await self._save_message(message)

    async def _save_message(self, message):
        try:
            if await self.db.message_exists(message.id):
                return

            attachments_data = [
                {'url': a.url, 'filename': a.filename}
                for a in message.attachments
                if is_image_url(a.url)
            ]

            message_data = {
                'message_id': message.id,
                'channel_id': message.channel.id,
                'author_id': message.author.id,
                'author_name': str(message.author),
                'content': message.content,
                'timestamp': message.created_at.isoformat(),
                'message_url': message.jump_url,
                'has_attachments': bool(message.attachments),
                'attachments': attachments_data,
            }

            saved = await self.db.save_message(message_data)
            if saved:
                self.parsed_count += 1
                if self.parsed_count % LOG_EVERY_N_SAVED == 0:
                    logger.info("Saved %d messages so far", self.parsed_count)

        except Exception as e:
            logger.error("Error saving message: %s", e)

    async def _parse_history(self, channel, limit=None):
        self.is_parsing = True
        count = 0
        skipped = 0

        try:
            logger.info("Parsing history of #%s (limit=%s)", channel.name, limit)

            async for message in channel.history(limit=limit, oldest_first=True):
                if message.author.bot:
                    continue
                if await self.db.message_exists(message.id):
                    skipped += 1
                    continue

                await self._save_message(message)
                count += 1

                if (count + skipped) % LOG_EVERY_N_SCANNED == 0:
                    logger.info("Progress: +%d new, -%d skipped", count, skipped)

            logger.info("Parse done: %d new, %d skipped", count, skipped)
            return count

        except Exception as e:
            logger.error("Error parsing history: %s", e, exc_info=True)
            return 0
        finally:
            self.is_parsing = False

    @commands.hybrid_command()
    @app_commands.describe(number="номер сообщения из базы; optional")
    async def funchosarand(self, ctx, number: Optional[int] = None):
        await ctx.defer()

        if number is not None:
            message_data = await self.db.get_message_by_number(number)
            if not message_data:
                await ctx.send(f"сообщение с номером {number} не найдено в базе")
                return
        else:
            message_data = await self.db.get_random_message()
            if not message_data:
                await ctx.send("помоему чет поломалось. меня пингани")
                return

        embed = build_funchosa_embed(message_data)
        view = FunchosaView(self.db, message_data['message_url'])
        await ctx.send(embed=embed, view=view)

    @commands.hybrid_command()
    async def funchosainfo(self, ctx):
        total = await self.db.get_total_count()
        status = await self.db.get_parsing_status()

        embed = discord.Embed(title="фунчоза.статы", color=discord.Color.green())
        embed.add_field(name="сообщений в базе", value=f"**{total or 0}**", inline=True)

        if status.get('last_parsed_message_id'):
            embed.add_field(
                name="последнее сообщение",
                value=f"id: `{status['last_parsed_message_id']}`",
                inline=False,
            )

        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(FunchosaParser(bot))

