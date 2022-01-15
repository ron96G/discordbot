#!/usr/bin/python3

import logging
import os

import boto3
import spotipy
from discord.ext import commands
from googleapiclient.discovery import build
from spotipy.oauth2 import SpotifyClientCredentials

from utils import ConfigMap
from bot import Bot
from music_utils import Spotify, Youtube
from cogs import Config, Func, Music, TextToSpeech, Wikipedia

TOKEN = os.environ.get("DISCORD_SECRET_TOKEN", None)
ACCESS_KEY = os.environ.get("AWS_ACCESS_KEY_ID", None)
SECRET_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY", None)

YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY", None)

SPOTIFY_CLIENT_ID = os.environ.get("SPOTIFY_CLIENT_ID", None)
SPOTIFY_CLIENT_SECRET = os.environ.get("SPOTIFY_CLIENT_SECRET", None)


def main():
    configmap = ConfigMap.from_file(
        os.environ.get("CONFIGFILE", "discordbot_config.json")
    )

    bot = Bot(
        command_prefix=commands.when_mentioned_or("!"),
        description="Bot example",
        configmap=configmap,
    )

    bot.add_cog(Config(bot))
    bot.add_cog(Func(bot))

    t2s = TextToSpeech(
        bot,
        boto3.client(
            "polly",
            aws_access_key_id=ACCESS_KEY,
            aws_secret_access_key=SECRET_KEY,
            region_name="eu-central-1",
        ),
    )
    bot.add_cog(t2s)

    bot.add_cog(Wikipedia(bot, t2s))

    spotify = None
    if SPOTIFY_CLIENT_ID is not None and SPOTIFY_CLIENT_SECRET is not None:
        s = spotipy.Spotify(
            client_credentials_manager=SpotifyClientCredentials(
                client_id=SPOTIFY_CLIENT_ID, client_secret=SPOTIFY_CLIENT_SECRET
            )
        )
        spotify = Spotify(s)

    youtube = None
    if YOUTUBE_API_KEY is not None:
        service = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)
        youtube = Youtube(service)

    bot.add_cog(Music(bot, youtube, spotify))
    bot.run(TOKEN)

    del spotify
    del youtube


if __name__ == "__main__":
    logging.basicConfig(
        filename=os.environ.get("FILENAME", None),
        level=os.environ.get("LOGLEVEL", "INFO"),
        format="[%(asctime)s] [%(pathname)s:%(lineno)d] %(levelname)s - %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )
    
    main()
