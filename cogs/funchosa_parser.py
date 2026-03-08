import discord
from discord.ext import commands, tasks
from discord import app_commands
import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional
import config
from utils.database import FunchosaDatabase

logger = logging.getLogger(__name__)

class FunchosaParser(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = FunchosaDatabase()
        
        self.target_channel_id = config.FUNCHOSA_CHANNEL_ID
        self.is_parsing = False
        self.parsed_count = 0
        self.rate_limit_delay = 0.5
        
    async def cog_load(self):
        await self.db.init_db()
        logger.info("[FunchosaParser] cog initialized")
        
    @commands.Cog.listener()
    async def on_ready(self):
        await asyncio.sleep(10)
        
        if not self.is_parsing:
            await self.auto_parse_on_startup()
    
    async def auto_parse_on_startup(self):
        try:
            if not self.target_channel_id:
                logger.warning("[FunchosaParser] no id channel ")
                return
            
            channel = self.bot.get_channel(self.target_channel_id)
            if not channel:
                logger.warning(f"[FunchosaParser] no channel with id {self.target_channel_id} found")
                return
            
            status = await self.db.get_parsing_status()
            logger.info(f"[FunchosaParser] parsing status; firsttry = {not status['first_parse_done']}")
            
            if self.is_parsing:
                logger.warning("[FunchosaParser] parsing already in progress")
                return
            
            logger.info("[FunchosaParser] starting to parse")
            
            if not status['first_parse_done']:
                logger.info("[FunchosaParser] first try, parse all")
                count = await self._parse_history(channel, limit=None)
                
                last_message_id = await self.db.get_last_message_in_db()
                await self.db.update_parsing_status(
                    first_parse_done=True,
                    last_parsed_message_id=last_message_id
                )
                
                logger.info(f"[FunchosaParser] parsing finished, total msg count: {count}")
            else:
                logger.info("[FunchosaParser] NOTfirst try, parse first 250")
                count = await self._parse_history(channel, limit=250)
                
                if count > 0:
                    new_last_message_id = await self.db.get_last_message_in_db()
                    await self.db.update_parsing_status(
                        first_parse_done=True,
                        last_parsed_message_id=new_last_message_id
                    )
                
                logger.info(f"[FunchosaParser] parsing finished, total msg count: {count}")
                
        except Exception as e:
            logger.error(f"[FunchosaParser] err when parsing: {e}", exc_info=True)
    
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
            
            attachments_data = []
            attachment_urls = []
            
            for attachment in message.attachments:
                if attachment.url.lower().endswith(('png', 'jpg', 'jpeg', 'gif', 'webp')):
                    attachments_data.append({
                        'url': attachment.url,
                        'filename': attachment.filename
                    })
                    attachment_urls.append(attachment.url)
            
            message_data = {
                'message_id': message.id,
                'channel_id': message.channel.id,
                'author_id': message.author.id,
                'author_name': str(message.author),
                'content': message.content,
                'timestamp': message.created_at.isoformat(),
                'message_url': message.jump_url,
                'has_attachments': len(message.attachments) > 0,
                'attachment_urls': ','.join(attachment_urls),
                'attachments': attachments_data
            }
            
            saved = await self.db.save_message(message_data)
            if saved:
                self.parsed_count += 1
                if self.parsed_count % 50 == 0:
                    logger.info(f"[FunchosaParser] saved messages total: {self.parsed_count}")
            
        except Exception as e:
            logger.error(f"[FunchosaParser] err when saving msg: {e}")
    
    async def _parse_history(self, channel, limit=None, after_message=None):
        try:
            self.is_parsing = True
            count = 0
            skipped = 0
            batch_size = 0
            
            logger.info(f"[FunchosaParser] starting to parse {channel.name}")
            
            oldest_first = not limit or limit < 0
            
            parse_kwargs = {
                'limit': abs(limit) if limit else None,
                'oldest_first': oldest_first,
            }
            
            if after_message:
                parse_kwargs['after'] = after_message

            async for message in channel.history(**parse_kwargs):
                if message.author.bot:
                    continue
                
                if await self.db.message_exists(message.id):
                    skipped += 1
                    batch_size += 1
                    
                    if batch_size >= 100:
                        logger.info(f"[FunchosaParser] batch: +{count} новых, -{skipped} skipped")
                        batch_size = 0
                    
                    continue
                
                await self._save_message(message)
                count += 1
                batch_size += 1
               
                await asyncio.sleep(self.rate_limit_delay)
                
                if batch_size >= 100:
                    logger.info(f"[FunchosaParser] batch: +{count} новых, -{skipped} skipped")
                    batch_size = 0
            
            logger.info(f"[FunchosaParser] parsing done. total new: {count}, total skipped: {skipped}")
            return count
            
        except Exception as e:
            logger.error(f"[FunchosaParser] err when parsing history: {e}", exc_info=True)
            return 0
        finally:
            self.is_parsing = False
    
    @commands.hybrid_command()
    @app_commands.describe(
        number="номер сообщения из базы; optional"
    )
    async def funchosarand(self, ctx, number: Optional[int] = None):
        await ctx.defer()
        
        if number:
            message_data = await self.db.get_message_by_number(number)
            if not message_data:
                await ctx.send(f"сообщение с номером {number} не найдено в базе ||соси черт||")
                return
        else:
            message_data = await self.db.get_random_message()
            if not message_data:
                await ctx.send("помоему чет поломалось. меня пингани")
                return

        embed = discord.Embed(
            description=message_data['content'] or "*[без текста]*",
            color=discord.Color.blue(),
            timestamp=datetime.fromisoformat(message_data['timestamp'])
        )
        
        embed.set_author(
            name='random фунчоза of the day'
        )
        
        
        attachments_text = []
        if message_data.get('attachments'):
            for i, att in enumerate(message_data['attachments'][:3], 1):
                attachments_text.append(f"[вложение {i}]({att['url']})")
        
        embed.add_field(
            name="info",
            value=(
                f"автор: <@{message_data['author_id']}>\n"
                f"дата: {message_data['timestamp'].replace('T', ' ')[:19]}\n"
                f"номер в базе: {message_data['id']}"
            ),
            inline=False
        )
        
        if attachments_text:
            embed.add_field(
                name="вложения",
                value="\n".join(attachments_text),
                inline=False
            )
        
        view = discord.ui.View()
        view.add_item(
            discord.ui.Button(
                label="перейти к сообщению",
                url=message_data['message_url'],
                style=discord.ButtonStyle.link
            )
        )
        
        view.add_item(
            discord.ui.Button(
                label="подавай еще, раб",
                custom_id="another_random",
                style=discord.ButtonStyle.secondary
            )
        )
        
        await ctx.send(embed=embed, view=view)
    
    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if not interaction.data or 'custom_id' not in interaction.data:
            return
        
        if interaction.data['custom_id'] == "another_random":
            await interaction.response.defer()
            
            message_data = await self.db.get_random_message()
            if not message_data:
                await interaction.followup.send("помоему чет поломалось. меня пингани", ephemeral=True)
                return
            
            embed = discord.Embed(
                description=message_data['content'] or "*[без текста]*",
                color=discord.Color.blue(),
                timestamp=datetime.fromisoformat(message_data['timestamp'])
            )
            
            embed.set_author(
                name='random фунчоза of the day'
            )
            
            embed.add_field(
                name="info",
                value=(
                    f"автор: <@{message_data['author_id']}>\n"
                    f"дата: {message_data['timestamp'].replace('T', ' ')[:19]}\n"
                    f"номер в базе: {message_data['id']}"
                ),
                inline=False
            )
            
            view = discord.ui.View()
            view.add_item(
                discord.ui.Button(
                    label="перейти к сообщению",
                    url=message_data['message_url'],
                    style=discord.ButtonStyle.link
                )
            )
            view.add_item(
                discord.ui.Button(
                    label="подавай еще, раб",
                    custom_id="another_random",
                    style=discord.ButtonStyle.secondary
                )
            )
            
            await interaction.followup.send(embed=embed, view=view)
    
    @commands.hybrid_command()
    async def funchosainfo(self, ctx):
        total = await self.db.get_total_count()
        status = await self.db.get_parsing_status()
        
        embed = discord.Embed(
            title="фунчоза.статы",
            color=discord.Color.green()
        )
        
        embed.add_field(name="сообщений в базе", value=f"**{total}**", inline=True)
        
        if status['last_parsed_message_id']:
            embed.add_field(
                name="последнее сообщение", 
                value=f"id: `{status['last_parsed_message_id']}`", 
                inline=False
            )
        
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(FunchosaParser(bot))