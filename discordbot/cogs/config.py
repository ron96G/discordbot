import logging

from cogs.func import Context
from discord.ext import commands


class Config(commands.Cog):
    def __init__(self, bot):
        self.log = logging.getLogger("cog")
        self.bot = bot

    @commands.Command
    async def set(self, ctx: Context, key: str, val: str):
        """Set a config parameter for your bot instance"""
        id = ctx.message.guild.id
        if not self.bot.config.exists(id):
            self.log.info(f"{id} - Setting initial config with {key}={val}")
            self.bot.config.add_config_for(id, {key: val})
        else:
            self.log.info(f"{id} - Updating config with {key}={val}")
            self.bot.config.update_config_for(id, key, val)

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
