import logging
import os
from contextlib import closing

import discord
from discord.ext import commands

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
    def __init__(self, bot: commands.Bot, polly_client, voiceId='Cristiano', languageCode='en-US', dir='./polly/'):
        self.bot = bot
        self.polly = polly_client
        self.log = logging.getLogger('cog')
        self.voiceId = voiceId
        self.languageCode = languageCode
        self.dir = dir

        if not os.path.exists(self.dir):
            os.makedirs(self.dir)

    @commands.command()
    async def say(self, ctx: commands.Context, *args):
        if ctx.voice_client is None:
            await self.bot.join_author(ctx)

        message = ''.join(args)

        response = self.polly.synthesize_speech(
            Engine = ENGINE,
            OutputFormat = OUTPUT_FORMAT,
            SampleRate = SAMPLE_RATE,
            LanguageCode = self.languageCode,
            Text = message,
            VoiceId = self.voiceId
        )

        if "AudioStream" in response:
            with closing(response["AudioStream"]) as stream:
                output = os.path.join(self.dir, f'{ctx.message.id}.mp3')
                with closing(open(output, "wb")) as file:
                    file.write(stream.read())
                player = discord.FFmpegOpusAudio(output, **ffmpeg_options)
                ctx.voice_client.play(player, after=lambda e: print('Player error: %s' % e) if e else None)
        else:
            raise commands.CommandError("no audiostream found in the polly response")
            
