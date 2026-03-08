import discord
from discord.ext import commands
import config
from utils.data_manager import save_message_id, load_message_id
import logging

logger = logging.getLogger(__name__)


class RoleManager(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.role_message_id = None
        self.CHANNEL_ID = config.CHANNEL_ID
        self.REACTION_ROLES = config.REACTION_ROLES

    async def cog_load(self):
        self.role_message_id = load_message_id()
        if self.role_message_id:
            logger.info("Initialized role message with id: %s", self.role_message_id)
        else:
            logger.info("No role message found")

        await self.bot.wait_until_ready()
        if self.role_message_id:
            await self.check_and_sync_roles()

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
            logger.warning("Role with id %s not found", role_id)
            return

        try:
            if add_role:
                await member.add_roles(role)
                logger.info("Gave role '%s' to '%s'", role.name, member.name)
            else:
                await member.remove_roles(role)
                logger.info("Removed role '%s' from '%s'", role.name, member.name)
        except discord.Forbidden:
            logger.error("Missing permissions to manage role '%s'", role.name)
        except Exception as e:
            logger.error("Unexpected error in handle_reaction: %s", e)

    async def check_and_sync_roles(self):
        if not self.role_message_id:
            return

        try:
            channel = await self.bot.fetch_channel(self.CHANNEL_ID)
            message = await channel.fetch_message(self.role_message_id)

            for reaction in message.reactions:
                emoji = str(reaction.emoji)
                if emoji not in self.REACTION_ROLES:
                    continue

                role = message.guild.get_role(self.REACTION_ROLES[emoji])
                if not role:
                    logger.warning("Role with id %s not found during sync", self.REACTION_ROLES[emoji])
                    continue

                async for user in reaction.users():
                    if user.bot:
                        continue
                    member = message.guild.get_member(user.id)
                    if member and role not in member.roles:
                        await member.add_roles(role)
                        logger.info("Sync gave role '%s' to '%s'", role.name, member.name)

        except discord.NotFound:
            logger.warning("Role message not found during sync")
        except discord.Forbidden:
            logger.error("Missing permissions to fetch channel or message")
        except Exception as e:
            logger.error("Unexpected sync error: %s", e)

    @commands.hybrid_command()
    @commands.has_permissions(administrator=True)
    async def create_role_message(self, ctx):
        message = await ctx.send(config.ROLE_MESSAGE_TEXT)
        for emoji in self.REACTION_ROLES:
            await message.add_reaction(emoji)

        self.role_message_id = message.id
        save_message_id(message.id)
        logger.info("Created new role message with id: %s", message.id)

    @commands.hybrid_command()
    @commands.has_permissions(administrator=True)
    async def update_role_message(self, ctx):
        if not self.role_message_id:
            return

        try:
            channel = await self.bot.fetch_channel(self.CHANNEL_ID)
            message = await channel.fetch_message(self.role_message_id)

            await message.edit(content=config.ROLE_MESSAGE_TEXT)

            existing = [str(r.emoji) for r in message.reactions]
            for emoji in self.REACTION_ROLES:
                if emoji not in existing:
                    await message.add_reaction(emoji)

            logger.info("Role message updated by %s", ctx.author.name)

        except discord.NotFound:
            logger.warning("Role message not found during update")
        except discord.Forbidden:
            logger.error("Missing permissions to edit role message")


async def setup(bot):
    await bot.add_cog(RoleManager(bot))