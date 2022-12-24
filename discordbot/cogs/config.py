import datetime
import logging

import discord
from common.config import ConfigValidationError
from common.context import Context
from discord.ext import commands

SESSION_DURATION = 120  # seconds


@commands.has_permissions(administrator=True)
class Config(commands.Cog):

    sessions_map = dict()

    def __init__(self, bot):
        self.log = logging.getLogger("cog")
        self.bot = bot

    async def get_session_ctx_guild_id(self, ctx: Context) -> str:
        """
        returns the guild_id of the request.
        If the request is part of an active session, return the guild_id for the session
        If the request was issued in a guild, return the id of the context
        """
        if ctx.channel.type is discord.ChannelType.private:
            session = self.sessions_map.get(ctx.author.id)
            if session is None:
                await ctx.reply_formatted_error("No config session open at this time")
                return None
            else:
                if session["until"] < datetime.datetime.now():
                    self.sessions_map.pop(ctx.author.id)
                    await ctx.reply_formatted_error("Session expired")
                    return None
                else:
                    return session["guild_id"]
        else:
            return ctx.message.guild.id

    @commands.Command
    async def set(self, ctx: Context, key: str, *, val: str):
        """Set a config parameter for your bot instance"""
        id = await self.get_session_ctx_guild_id(ctx)
        if id is None:
            return
        val = val.strip()
        try:
            if not self.bot.config.exists(id):
                self.log.info(f"{id} - Setting initial config with {key}={val}")
                self.bot.config.add_config_for(id, {key: val})
            else:
                self.log.info(f"{id} - Updating config with {key}={val}")
                self.bot.config.update_config_for(id, key, val)

        except ConfigValidationError as e:
            return await ctx.reply_formatted_error(f"{e}", error_title="Config Error")

        return await ctx.tick(True)

    @commands.Command
    async def get(self, ctx: Context, *args):
        """Get either one config parameter by the provided key
        or the entire config for your bot instance"""
        id = await self.get_session_ctx_guild_id(ctx)
        if id is None:
            return
        if self.bot.config.exists(id):
            if len(args) <= 0:
                val = self.bot.config.get_config_for(id)
                return await ctx.send(f"Current config is {val}")
            key = args[0]
            val = self.bot.config.get_config_for(id, key)
            return await ctx.send(f"Current config for {key} is {val}")

    @commands.Command
    async def reset(self, ctx: Context):
        """Reset the config to default"""
        id = ctx.message.guild.id
        if self.bot.config.exists(id):
            self.bot.config.remove_config_for(id)
            self.bot.config.set_defaults_for(id)
        return await ctx.tick(True)

    @commands.Command
    async def session(self, ctx: Context):
        """Start a session where you can set and get config parameters using direct messages to the bot"""
        await ctx.tick(True)
        await ctx.author.send(
            f"You may now access the config of {ctx.guild.name} for {SESSION_DURATION} seconds"
        )
        self.sessions_map[ctx.author.id] = {
            "guild_id": ctx.guild.id,
            "until": datetime.datetime.now() + datetime.timedelta(0, SESSION_DURATION),
        }
