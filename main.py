import os, sys, logging, boto3
from discord.ext import commands

from googleapiclient.discovery import build

from pkg.bot import Bot, Func
from pkg.music import Music, Youtube;
from pkg.text_to_speech import TextToSpeech 


TOKEN = os.environ.get('DISCORD_SECRET_TOKEN', None)
ACCESS_KEY = os.environ.get('AWS_ACCESS_KEY_ID', None)
SECRET_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY', None)
YOUTUBE_API_KEY = os.environ.get('YOUTUBE_API_KEY', None)

if __name__ == '__main__':
    logging.basicConfig(
        filename = os.environ.get('FILENAME', None),
        level = os.environ.get('LOGLEVEL', 'INFO'),
        format = '[%(asctime)s] [%(pathname)s:%(lineno)d] %(levelname)s - %(message)s',
        datefmt = '%Y-%m-%dT%H:%M:%S'
    )
    
    bot = Bot(command_prefix=commands.when_mentioned_or("!"), description='Bot example')

    bot.add_cog(Func(bot))
    bot.add_cog(TextToSpeech(bot, boto3.client('polly', 
        aws_access_key_id=ACCESS_KEY,
        aws_secret_access_key=SECRET_KEY,
        region_name='eu-central-1')
    ))

    with build('youtube', 'v3', developerKey = YOUTUBE_API_KEY) as service:
        youtube = Youtube(service)

        bot.add_cog(Music(bot, youtube))
        bot.run(TOKEN)
        
    sys.exit(0)