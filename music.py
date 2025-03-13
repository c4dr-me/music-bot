import os
import discord
import yt_dlp
import asyncio
import ctypes
import ctypes.util
from discord.ext import commands
from discord import FFmpegPCMAudio
from dotenv import load_dotenv
from keep_alive import keep_alive

load_dotenv()  # Load .env variables

# Load opus library for voice
if not discord.opus.is_loaded():
    try:
        discord.opus.load_opus('libopus.so.0')
    except OSError:
        try:
            opus_path = ctypes.util.find_library('opus')
            if opus_path:
                discord.opus.load_opus(opus_path)
            else:
                # If it still fails, try installing libopus
                os.system('apt-get update && apt-get install -y libopus0')
                discord.opus.load_opus('libopus.so.0')
        except Exception as e:
            print(f"Could not load opus library: {e}")
            print("Voice functionality might not work.")

ytdl_format_options = {
    'format': 'bestaudio/best',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0',
}

ffmpeg_options = {
    'before_options':
    '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 10',
    'options': '-vn'
    # Let discord.py find ffmpeg in the system path
}

ytdl = yt_dlp.YoutubeDL(ytdl_format_options)
queue = []

# Make commands case-insensitive
def get_prefix(bot, message):
    return "!"

bot = commands.Bot(command_prefix=get_prefix, 
                  intents=discord.Intents.all(),
                  case_insensitive=True)  # Add case insensitivity


class YTDLSource(discord.PCMVolumeTransformer):

    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = data.get('url')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(
            None, lambda: ytdl.extract_info(url, download=not stream))
        
        if 'entries' in data:
            # Take the first item from a playlist
            data = data['entries'][0]
            
        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options),
                   data=data)


@bot.command(name="play")
async def play(ctx, *, search: str):
    """Plays a song from a YouTube search"""
    if not ctx.author.voice:
        await ctx.send("❌ You must be in a voice channel to use this command!")
        return

    if ctx.voice_client is None:
        await ctx.author.voice.channel.connect()

    player = await YTDLSource.from_url(search, loop=bot.loop, stream=True)
    ctx.voice_client.play(player,
                          after=lambda e: bot.loop.create_task(next_song(ctx)))

    await ctx.send(f"🎶 Now playing: **{player.title}**")


@bot.command(name="stop")
async def stop(ctx):
    """Stops the current song"""
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        await ctx.send("⏹️ Stopped playing music.")


if __name__ == "__main__":
    keep_alive()  # Keep the bot alive
    bot.run(os.getenv("DISCORD_TOKEN"))

