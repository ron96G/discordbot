import logging
from discord.ext import commands

from pkg.cogs.func import Context
from pkg.bot import Bot

class Config(commands.Cog):

    def __init__(self, bot: Bot):
        self.log = logging.getLogger('cog')
        self.bot = bot

    @commands.Command
    async def set(self, ctx: Context, key: str, val: str):
        id = ctx.message.guild.id
        if not self.bot.config.exists(id):
            self.log.info(f'{id} - Setting initial config with {key}={val}')
            self.bot.config.add_config_for(id, {key: val})
        else:
            self.log.info(f'{id} - Updating config with {key}={val}')
            self.bot.config.update_config_for(id, key, val)

        return await ctx.tick(True)

    @commands.Command
    async def get(self, ctx: Context, *args):
        id = ctx.message.guild.id
        if self.bot.config.exists(id):
            if len(args) <= 0:
                val = self.bot.config.get_config_for(id)
                return await ctx.send(f'Current config is {val}')
            key = args[0]
            val = self.bot.config.get_config_for(id, key)
            return await ctx.send(f'Current config for {key} is {val}')