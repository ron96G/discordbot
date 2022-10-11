import logging

from audio import TextToSpeechService, Track
from common.context import Context
from discord.ext import commands


class TextToSpeech(commands.Cog):
    log = logging.getLogger("cog")

    def __init__(
        self,
        bot: commands.Bot,
        service: TextToSpeechService,
        voiceId="Amy",
        languageCode="en-US",
        max_characters=2000,
    ):
        self.bot = bot
        self.service = service
        self.voiceId = voiceId
        self.languageCode = languageCode
        self.max_characters = max_characters

    @commands.command()
    async def say(self, ctx: Context, *, message: str):
        """Let the bot talk to you"""

        if ctx.voice_client is None:
            await self.bot.join_author(ctx)

        if len(message) > self.max_characters:
            return await ctx.reply_formatted_error(
                f"Length of message cannot exceed {self.max_characters}"
            )

        async with ctx.typing():
            id = ctx.message.guild.id

            lang_code = self.bot.config.get_config_for(
                id, key="languageCode", default=self.languageCode
            )
            voice_id = self.bot.config.get_config_for(
                id, key="voiceId", default=self.voiceId
            )

            info = self.service.synthesize_speech(id, message, lang_code, voice_id)
            info.stream = False
            track = Track(ctx, info)

            if not self.bot.queue.has(id):
                self.bot.runner.register(id)

            await self.bot.queue.put(id, track, 800)
            await ctx.tick(True)
