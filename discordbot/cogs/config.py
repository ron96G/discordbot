import logging

from common.config import ConfigValidationError
from common.context import Context
from discord.ext import commands


class Config(commands.Cog):
    def __init__(self, bot):
        self.log = logging.getLogger("cog")
        self.bot = bot

    @commands.Command
    async def set(self, ctx: Context, key: str, *, val: str):
        """Set a config parameter for your bot instance"""
        id = ctx.message.guild.id
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
        id = ctx.message.guild.id
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
