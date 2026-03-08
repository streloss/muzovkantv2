import discord
from discord.ext import commands
from discord import app_commands
import config
from utils.data_manager import save_message_id, load_message_id
import logging

# Создаем логгер для этого модуля
logger = logging.getLogger(__name__)

class RoleManager(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.role_message_id = None
        self.CHANNEL_ID = config.CHANNEL_ID
        self.REACTION_ROLES = config.REACTION_ROLES
        self._ready = False
        
    async def cog_load(self):
        self.role_message_id = load_message_id()
        if self.role_message_id:
            logger.info(f"[RoleManager] initialized role msg with id: '{self.role_message_id}'")
        else:
            logger.info('[RoleManager] no role msg found')
    
    @commands.Cog.listener()
    async def on_ready(self):
        if not self._ready and self.role_message_id:
            await self.check_and_sync_roles()
            self._ready = True
    
    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        await self.handle_reaction(payload, add_role=True)
    
    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        await self.handle_reaction(payload, add_role=False)
    
    async def handle_reaction(self, payload, add_role=True):
        if payload.message_id != self.role_message_id:
            return
        
        emoji = str(payload.emoji)
        if emoji not in self.REACTION_ROLES:
            return
        
        guild = self.bot.get_guild(payload.guild_id)
        if not guild:
            return
        
        member = guild.get_member(payload.user_id)
        if not member or member.bot:
            return
        
        role_id = self.REACTION_ROLES[emoji]
        role = guild.get_role(role_id)
        
        if not role:
            logger.warning(f"[RoleManager] role with id '{role_id}' not found")
            return
        
        try:
            if add_role:
                await member.add_roles(role)
                logger.info(f"[RoleManager] gave role '{role.name}' to '{member.name}'")
            else:
                await member.remove_roles(role)
                logger.info(f"[RoleManager] removed role '{role.name}' from user '{member.name}'")
        except discord.Forbidden:
            logger.error(f"[RoleManager] not enough rights to give role '{role.name}'")
        except Exception as e:
            logger.error(f"[RoleManager] err: '{e}'")
    
    async def check_and_sync_roles(self):
        if not self.role_message_id:
            return
        
        try:
            channel = await self.bot.fetch_channel(self.CHANNEL_ID)
            if not channel:
                logger.warning(f"[RoleManager] channel with id '{self.CHANNEL_ID}' not found")
                return
            
            message = await channel.fetch_message(self.role_message_id)
            
            for reaction in message.reactions:
                emoji = str(reaction.emoji)
                
                if emoji in self.REACTION_ROLES:
                    role_id = self.REACTION_ROLES[emoji]
                    role = message.guild.get_role(role_id)
                    
                    if not role:
                        logger.warning(f"[RoleManager] role with id '{role_id}' not found")
                        continue
                    
                    async for user in reaction.users():
                        if user.bot:
                            continue
                        
                        member = message.guild.get_member(user.id)
                        if member and role not in member.roles:
                            await member.add_roles(role)
                            logger.info(f"[RoleManager] gave role '{role.name}' to user '{member.name}'")
            
        except discord.NotFound:
            logger.warning("[RoleManager] role msg not found")
        except discord.Forbidden:
            logger.error("[RoleManager] no rights to get channel or message")
        except Exception as e:
            logger.error(f"[RoleManager] sync err: '{e}'")
    
    @commands.hybrid_command()
    @commands.has_permissions(administrator=True)
    async def create_role_message(self, ctx):
        embed = discord.Embed(
            title="ле",
            description="пикните там роли снизу по реактам,\nшоб если куда то шли играть с фаршем >3 человек то сразу можно было ее пингануть\n\n"
            "react_index = {\n"
            "    '💩': гревдиггер\n"
            "    '🤙': бара наверн хз\n"
            "    '🤕': пох ваще за любой движ\n"
            "    '🇺🇦': мтк\n"
            "}\n\n"
            "естессно кто будет спамить пингом ролей тот будет опущен и закинут в таймаут\n"
            "если бот в оффе роли выдадутся когда я врублю его снова",
            color=0x00ff00
        )
        
        message = await ctx.send(embed=embed)
        
        for emoji in self.REACTION_ROLES.keys():
            await message.add_reaction(emoji)
        
        self.role_message_id = message.id
        save_message_id(message.id)
        logger.info(f"[RoleManager] created new role message with id: '{message.id}'")
    
    @commands.hybrid_command()
    @commands.has_permissions(administrator=True)
    async def sync_roles(self, ctx):
        await self.check_and_sync_roles()
        logger.info("[RoleManager] manual sync triggered by admin")

async def setup(bot):
    await bot.add_cog(RoleManager(bot))