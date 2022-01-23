import logging

from cogs.text_to_speech import TextToSpeech
from discord.ext import commands


class Wikipedia(commands.Cog):
    def __init__(
        self,
        bot: commands.Bot,
        t2s: TextToSpeech = None,
        language="en",
        max_characters=2000,
    ):
        self.bot = bot
        self.log = logging.getLogger("cog")
        self.langugage = language
        self.max_characters = max_characters
        self.t2s = t2s

    @commands.Command
    async def explain(self, ctx: commands.Context, *, query: str):
        """Let the bot explain a topic to you"""
        import wikipedia

        id = ctx.message.guild.id
        lang = self.bot.config.get_config_for(id, "wikiLanguage", self.langugage)
        wikipedia.set_lang(lang)

        self.log.info(f'Getting suggestion for "{query}" from Wikipedia')
        try:
            suggestion = wikipedia.suggest(query)
            if suggestion is None:
                self.log.info("No good suggestion found. Using supplied query")
                suggestion = query

            self.log.info(f'Getting summary of page "{suggestion}" from Wikipedia')
            page = wikipedia.summary(suggestion)

            until_last_sentence = page[: self.max_characters].rfind(".")
            await ctx.send(f"{page[:until_last_sentence]}...")

            if self.t2s is not None:
                await self.t2s.say(ctx=ctx, message=page[:until_last_sentence])

        except wikipedia.DisambiguationError as e:
            return await ctx.send(f"{query} may refer to {e.options}")

        except Exception as e:
            self.log.error(f"failed command wikipedia.explain with: {e}")
            return await ctx.send(
                f'Currently unable to explain "{query}". Please try again later or try a different topic.'
            )
