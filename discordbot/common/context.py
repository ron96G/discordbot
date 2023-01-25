import discord
from discord.ext import commands


class Context(commands.Context):
    async def tick(self, value):
        emoji = "\N{WHITE HEAVY CHECK MARK}" if value else "\N{CROSS MARK}"
        try:
            await self.message.add_reaction(emoji)
        except discord.HTTPException:
            pass

    async def reply_formatted_error(
        self,
        error_msg: str,
        error_title: str = "Error occurred",
        thumbnail_url: str = None,
    ) -> discord.Message:
        embed = discord.Embed(
            title=error_title, description=error_msg, color=discord.Color.red()
        )
        embed.set_author(name=self.author.name, icon_url=self.author.avatar.url)
        if thumbnail_url:
            embed.set_thumbnail(url=thumbnail_url)

        return await self.send(embed=embed)

    async def reply_formatted_msg(
        self, msg: str, title: str = "Bottich Audio Player", thumbnail_url: str = None
    ) -> discord.Message:
        embed = discord.Embed(
            title=title, description=msg, color=discord.Color.dark_gold()
        )
        embed.set_author(name=self.author.display_name, icon_url=self.author.avatar.url)
        if thumbnail_url:
            embed.set_thumbnail(url=thumbnail_url)

        return await self.send(embed=embed)
