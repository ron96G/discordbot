import logging

from discord.ext import commands

from pkg.bot import Bot
from pkg.cogs.text_to_speech import TextToSpeech


class Wikipedia(commands.Cog):

    def __init__(self, bot: Bot, t2s: TextToSpeech = None, language='en', max_characters=2000):
        self.bot = bot
        self.log = logging.getLogger('cog')
        self.langugage = language
        self.max_characters = max_characters
        self.t2s = t2s

    @commands.Command
    async def explain(self, ctx: commands.Context,  *args):

        with ctx.typing():
            import wikipedia
            id = ctx.message.guild.id
            lang = self.bot.config.get_config_for(id, 'wikiLanguage', self.langugage)
            wikipedia.set_lang(lang)

            title = ''.join(args)
            try:
                search_result = wikipedia.search(title, results=1)

                page = wikipedia.summary(search_result)

                until_last_sentence = page[:self.max_characters].rfind('.')
                await ctx.send(f'{page[:until_last_sentence]}...')

                if self.t2s is not None:
                    await self.t2s.say(ctx, page[:until_last_sentence])

            except wikipedia.DisambiguationError as e:
                return await ctx.send(f'{title} may refer to {e.options}')
                
            except KeyError:
                return await ctx.send(f'Unable to find the requested page with title "{title}"')
            

