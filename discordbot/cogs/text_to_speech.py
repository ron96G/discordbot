import logging
import os
from contextlib import closing
from datetime import datetime
from typing import Any, Union

import discord
from botocore.exceptions import BotoCoreError, ClientError, ValidationError
from common.context import Context
from discord.ext import commands

## See https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/polly.html#Polly.Client.synthesize_speech

# VoiceId='Aditi'|'Amy'|'Astrid'|'Bianca'|'Brian'|'Camila'|'Carla'|'Carmen'|'Celine'|'Chantal'|'Conchita'|'Cristiano'|'Dora'|'Emma'|'Enrique'|'Ewa'|'Filiz'|'Gabrielle'|'Geraint'|'Giorgio'|'Gwyneth'|'Hans'|'Ines'|'Ivy'|'Jacek'|'Jan'|'Joanna'|'Joey'|'Justin'|'Karl'|'Kendra'|'Kevin'|'Kimberly'|'Lea'|'Liv'|'Lotte'|'Lucia'|'Lupe'|'Mads'|'Maja'|'Marlene'|'Mathieu'|'Matthew'|'Maxim'|'Mia'|'Miguel'|'Mizuki'|'Naja'|'Nicole'|'Olivia'|'Penelope'|'Raveena'|'Ricardo'|'Ruben'|'Russell'|'Salli'|'Seoyeon'|'Takumi'|'Tatyana'|'Vicki'|'Vitoria'|'Zeina'|'Zhiyu'|'Aria'|'Ayanda'
# LanguageCode='arb'|'cmn-CN'|'cy-GB'|'da-DK'|'de-DE'|'en-AU'|'en-GB'|'en-GB-WLS'|'en-IN'|'en-US'|'es-ES'|'es-MX'|'es-US'|'fr-CA'|'fr-FR'|'is-IS'|'it-IT'|'ja-JP'|'hi-IN'|'ko-KR'|'nb-NO'|'nl-NL'|'pl-PL'|'pt-BR'|'pt-PT'|'ro-RO'|'ru-RU'|'sv-SE'|'tr-TR'|'en-NZ'|'en-ZA',
# https://docs.aws.amazon.com/de_de/polly/latest/dg/voicelist.html

ENGINE = "standard"  # 'standard'|'neural'
OUTPUT_FORMAT = "mp3"  # 'json'|'mp3'|'ogg_vorbis'|'pcm'
SAMPLE_RATE = "16000"

ffmpeg_options = {"options": "-vn"}


class SynthesizeSpeechSource(discord.PCMVolumeTransformer):
    """Required as a wrapper to make the audio source complied to the required interface in the queue"""

    title: str
    error: Union[Any, str, None]

    def __init__(self, source, volume=0.5, title="SynthesizeSpeech", error=None):
        self.title = title
        if error is None:
            self.error = None
            super().__init__(source, volume)
            logging.info(f"Successfully constructed audiosource for synthesized speech")
        else:
            self.error = error


class TextToSpeech(commands.Cog):
    def __init__(
        self,
        bot: commands.Bot,
        polly_client,
        voiceId="Amy",
        languageCode="en-US",
        dir="./polly/",
        max_characters=2000,
    ):
        self.bot = bot
        self.polly = polly_client
        self.log = logging.getLogger("cog")
        self.voiceId = voiceId
        self.languageCode = languageCode
        self.dir = dir
        self.max_characters = max_characters

        if not os.path.exists(self.dir):
            os.makedirs(self.dir)

    def synthesize_speech(
        self, id: str, message: str, lang_code: str = None, voice_id: str = None
    ):
        try:
            response = self.polly.synthesize_speech(
                Engine=ENGINE,
                OutputFormat=OUTPUT_FORMAT,
                SampleRate=SAMPLE_RATE,
                LanguageCode=lang_code or self.languageCode,
                Text=message,
                VoiceId=voice_id or self.voiceId,
            )

        except ClientError as e:
            raise commands.CommandError(f"failed to synthesize speech: {e}")
        except (BotoCoreError, ValidationError) as e:
            raise commands.CommandError(f"failed to synthesize speech: {e.fmt}")

        output = os.path.join(self.dir, f"{id}.mp3")
        if "AudioStream" in response:
            with closing(response["AudioStream"]) as stream:

                with closing(open(output, "wb")) as file:
                    file.write(stream.read())
        else:
            raise commands.CommandError("no audiostream found in the polly response")

        self.log.info(f"Successfully synthesized speech with id {id}")
        return SynthesizeSpeechSource(discord.FFmpegPCMAudio(output, **ffmpeg_options))

    @commands.command()
    async def say(self, ctx: Context, *, message: str):
        """Let the bot talk to you"""
        if ctx.voice_client is None:
            await self.bot.join_author(ctx)

        if len(message) > self.max_characters:
            return await ctx.reply_formatted_error(
                f"Length of message cannot exceed {self.max_characters}"
            )

        with ctx.typing():
            id = ctx.message.guild.id
            lang_code = self.bot.config.get_config_for(
                id, key="languageCode", default=self.languageCode
            )
            voice_id = self.bot.config.get_config_for(
                id, key="voiceId", default=self.voiceId
            )
            player = self.bot.loop.run_in_executor(
                None,
                lambda: self.synthesize_speech(
                    ctx.message.id, message, lang_code, voice_id
                ),
            )

            if not self.bot.queue.exists(id):
                await self.bot.queue.register(id)
            pos = await self.bot.queue.put(
                id, {"ctx": ctx, "player": player, "time": datetime.now()}
            )

            await ctx.tick(True)
            if pos > 1:
                await ctx.message.reply(f"Queued at position {pos}")
