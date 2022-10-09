#!/usr/bin/python3

import logging
import os

import boto3
import spotipy
from bot import Bot
from cogs import Config, Debugging, Func, Music, TextToSpeech, Wikipedia
from discord.ext import commands
from googleapiclient.discovery import build
from music_utils import Spotify, Twitch, Youtube
from spotipy.oauth2 import SpotifyClientCredentials
from twitchAPI.twitch import Twitch as TwitchAPI
from utils import ConfigMap, ConfigStore, install

CONFIG_VERSION = os.environ.get("CONFIG_VERSION", None)
CONFIG_TYPE = os.environ.get("CONFIG_TYPE", "s3")
if CONFIG_TYPE == "s3":
    config = ConfigStore.s3(CONFIG_VERSION)
elif CONFIG_TYPE == "env_file":
    config = ConfigStore.env_file(".env")
else:
    config = ConfigStore()

config.set_in_env()

DEBUG = config.get("DEBUG") in ["true", "True"]
TOKEN = config.get("DISCORD_SECRET_TOKEN")

FFMPEG_VERSION = config.get("FFMPEG_VERSION", fallback="5.1.1")

ACCESS_KEY = config.get("AWS_ACCESS_KEY_ID")
SECRET_KEY = config.get("AWS_SECRET_ACCESS_KEY")

YOUTUBE_API_KEY = config.get("YOUTUBE_API_KEY")

SPOTIFY_CLIENT_ID = config.get("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = config.get("SPOTIFY_CLIENT_SECRET")

TWITCH_CLIENT_ID = config.get("TWITCH_CLIENT_ID")
TWITCH_CLIENT_SECRET = config.get("TWITCH_CLIENT_SECRET")


def main():
    configmap = ConfigMap.from_file(
        os.environ.get("CONFIGFILE", "discordbot_config.json")
    )

    bot = Bot(
        command_prefix=commands.when_mentioned_or("!"),
        description="Bottich",
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

    # Twitch
    # TwitchAPI is only used to fetch meta information like Twitch thumbnail and title
    ## Therefore, it is not required to stream
    twitch = Twitch(TwitchAPI(TWITCH_CLIENT_ID, TWITCH_CLIENT_SECRET))

    bot.add_cog(Music(bot, youtube, spotify, twitch))

    if DEBUG:
        bot.add_cog(Debugging(bot, youtube, spotify, twitch))

    bot.run(TOKEN)

    del spotify
    del youtube
    del twitch


if __name__ == "__main__":
    logging.basicConfig(
        filename=os.environ.get("FILENAME", None),
        level=os.environ.get("LOGLEVEL", "INFO"),
        format="[%(asctime)s] [%(pathname)s:%(lineno)d] %(levelname)s - %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )

    install(FFMPEG_VERSION, force=False)
    main()
