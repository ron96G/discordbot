from datetime import datetime
import logging, os
from contextlib import closing

import discord
from discord.ext import commands

from pkg.bot import Bot

## See https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/polly.html#Polly.Client.synthesize_speech

# VoiceId='Aditi'|'Amy'|'Astrid'|'Bianca'|'Brian'|'Camila'|'Carla'|'Carmen'|'Celine'|'Chantal'|'Conchita'|'Cristiano'|'Dora'|'Emma'|'Enrique'|'Ewa'|'Filiz'|'Gabrielle'|'Geraint'|'Giorgio'|'Gwyneth'|'Hans'|'Ines'|'Ivy'|'Jacek'|'Jan'|'Joanna'|'Joey'|'Justin'|'Karl'|'Kendra'|'Kevin'|'Kimberly'|'Lea'|'Liv'|'Lotte'|'Lucia'|'Lupe'|'Mads'|'Maja'|'Marlene'|'Mathieu'|'Matthew'|'Maxim'|'Mia'|'Miguel'|'Mizuki'|'Naja'|'Nicole'|'Olivia'|'Penelope'|'Raveena'|'Ricardo'|'Ruben'|'Russell'|'Salli'|'Seoyeon'|'Takumi'|'Tatyana'|'Vicki'|'Vitoria'|'Zeina'|'Zhiyu'|'Aria'|'Ayanda'
# LanguageCode='arb'|'cmn-CN'|'cy-GB'|'da-DK'|'de-DE'|'en-AU'|'en-GB'|'en-GB-WLS'|'en-IN'|'en-US'|'es-ES'|'es-MX'|'es-US'|'fr-CA'|'fr-FR'|'is-IS'|'it-IT'|'ja-JP'|'hi-IN'|'ko-KR'|'nb-NO'|'nl-NL'|'pl-PL'|'pt-BR'|'pt-PT'|'ro-RO'|'ru-RU'|'sv-SE'|'tr-TR'|'en-NZ'|'en-ZA',

ENGINE = 'standard' # 'standard'|'neural'
OUTPUT_FORMAT = 'mp3' # 'json'|'mp3'|'ogg_vorbis'|'pcm'
SAMPLE_RATE = '16000'

ffmpeg_options = {
    'options': '-vn'
}

class TextToSpeech(commands.Cog):
    def __init__(self, bot: Bot, polly_client, voiceId='Amy', languageCode='en-US', dir='./polly/', max_characters=2000):
        self.bot = bot
        self.polly = polly_client
        self.log = logging.getLogger('cog')
        self.voiceId = voiceId
        self.languageCode = languageCode
        self.dir = dir
        self.max_characters = max_characters

        if not os.path.exists(self.dir):
            os.makedirs(self.dir)


    def synthesize_speech(self, id: str, message: str, lang_code: str = None, voice_id: str = None):
        try:
            response = self.polly.synthesize_speech(
                Engine = ENGINE,
                OutputFormat = OUTPUT_FORMAT,
                SampleRate = SAMPLE_RATE,
                LanguageCode = lang_code or self.languageCode,
                Text = message,
                VoiceId = voice_id or self.voiceId
            )
        except Exception as e:
            self.log.error(e)
            raise commands.CommandError('failed to synthesize speech')

        output = os.path.join(self.dir, f'{id}.mp3')
        if "AudioStream" in response:
            with closing(response["AudioStream"]) as stream:
                
                with closing(open(output, "wb")) as file:
                    file.write(stream.read())       
        else:
            raise commands.CommandError("no audiostream found in the polly response")

        self.log.info(f'Successfully synthesized speech with id {id}')
        return discord.FFmpegOpusAudio(output, **ffmpeg_options)

    @commands.command()
    async def say(self, ctx: commands.Context, *args):
        if ctx.voice_client is None:
            await self.bot.join_author(ctx)

        message = ''
        if isinstance(args, str):
            message = args
        else:
            message = ' '.join(args)

        if len(message) > self.max_characters:
            return await ctx.send(f'Length of message cannot exceed {self.max_characters}')

        with ctx.typing():
            id = ctx.message.guild.id
            lang_code = self.bot.config.get_config_for(id, key='languageCode', default=self.languageCode)
            voice_id = self.bot.config.get_config_for(id, key='voiceId', default=self.voiceId)
            player = self.bot.loop.run_in_executor(None, lambda: self.synthesize_speech(ctx.message.id, message, lang_code, voice_id))

            if ctx.voice_client.is_playing():
                if not self.bot.queue.exists(id):
                    self.bot.queue.register(id)
                pos = await self.bot.queue.put(id, {'ctx': ctx, 'player': player, 'time': datetime.now()})

                return await ctx.message.reply(f'Queued at position {pos}')

            ctx.voice_client.play(await player, after=lambda e: print('Player error: %s' % e) if e else None)