#!/usr/bin/python3.8

import logging
import os

from bot import Bot
from common import ConfigMap, ConfigStore, install
from discord.ext import commands

CONFIG_VERSION = os.environ.get("CONFIG_VERSION", None)
CONFIG_TYPE = os.environ.get("CONFIG_TYPE", "s3")
if CONFIG_TYPE == "s3":
    config = ConfigStore.s3(CONFIG_VERSION)
elif CONFIG_TYPE == "env_file":
    config = ConfigStore.env_file(".env")
else:
    config = ConfigStore()

config.set_in_env()

TOKEN = config.get("DISCORD_SECRET_TOKEN")
FFMPEG_VERSION = config.get("FFMPEG_VERSION", fallback="5.1.1")

if __name__ == "__main__":
    logging.basicConfig(
        filename=config.get_env_first("FILENAME", None),
        level=config.get_env_first("LOGLEVEL", "INFO"),
        format="[%(asctime)s] [%(pathname)s:%(lineno)d] %(levelname)s - %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )

    install(FFMPEG_VERSION, force=False)

    configmap = ConfigMap.from_file(
        config.get_env_first("CONFIGFILE", "discordbot_config.json")
    )

    bot = Bot(
        command_prefix=commands.when_mentioned_or("!"),
        description="Bottich",
        configmap=configmap,
        configstore=config,
    )

    bot.run(TOKEN)
