
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

# Disable yt-dlp bug reports
yt_dlp.utils.bug_reports_message = lambda: ''

# Configure opus loading
if not discord.opus.is_loaded():
    try:
        # Check common locations for the Opus library on Replit
        possible_opus_paths = [
            '/usr/lib/libopus.so.0',
            '/usr/lib/x86_64-linux-gnu/libopus.so.0',
            '/nix/store/*/libopus.so.0',
            '/home/runner/.apt/usr/lib/libopus.so.0',
            '/home/runner/workspace/.pythonlibs/lib/python3.11/site-packages/discord/libopus.so.0'
        ]
        
        # Try each possible path
        for path in possible_opus_paths:
            import glob
            if "*" in path:
                paths = glob.glob(path)
                for p in paths:
                    try:
                        discord.opus.load_opus(p)
                        print(f"Successfully loaded opus from {p}")
                        break
                    except Exception:
                        continue
            else:
                try:
                    discord.opus.load_opus(path)
                    print(f"Successfully loaded opus from {path}")
                    break
                except Exception:
                    continue
                    
        # If still not loaded, try the system path
        if not discord.opus.is_loaded():
            opus_path = ctypes.util.find_library('opus')
            if opus_path:
                discord.opus.load_opus(opus_path)
                print(f"Successfully loaded opus from {opus_path}")
    except Exception as e:
        print(f"Could not load opus library: {e}")
        print("Voice functionality might not work properly.")

# Configure download options
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
    'outtmpl': 'downloads/%(id)s.%(ext)s',
}

ffmpeg_options = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 10',
    'options': '-vn'
}

ytdl = yt_dlp.YoutubeDL(ytdl_format_options)
queue = []
loop = False

# Make commands case-insensitive
def get_prefix(bot, message):
    return "!"

bot = commands.Bot(command_prefix=get_prefix, 
                  intents=discord.Intents.all(),
                  case_insensitive=True)

def parse_duration(duration_seconds):
    """Convert duration in seconds to a formatted string."""
    minutes, seconds = divmod(duration_seconds, 60)
    hours, minutes = divmod(minutes, 60)
    
    if hours > 0:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    else:
        return f"{minutes}:{seconds:02d}"

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = data.get('url')
        self.views = data.get('view_count')
        self.likes = data.get('like_count')
        self.thumbnail = data.get('thumbnail')
        self.date = data.get('upload_date', '00000000')
        self.duration = parse_duration(int(data.get('duration', 0)))
        self.raw_duration = int(data.get('duration', 0))
        self.uploader = data.get('uploader', 'Unknown')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False, ctx=None):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))
        if 'entries' in data:
            data = data['entries'][0]
        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)
        
    @classmethod
    async def search(cls, search: str, *, loop=None, stream=False, ctx=None):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(f'ytsearch:{search}', download=False))
        try:
            if 'entries' in data:
                data = data['entries'][0]
                filename = data['url']
                return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)
        except IndexError:
            if ctx:
                await ctx.send('Song not found!')
            return None

class Controls(discord.ui.View):
    def __init__(self, ctx, artist, song):
        super().__init__(timeout=None)
        self.ctx = ctx
        self.song = song
        self.artist = artist

    @discord.ui.button(label='Resume', style=discord.ButtonStyle.green)
    async def resume_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.ctx.voice_client.resume()
        await interaction.response.send_message('▶️ Resumed playback', ephemeral=True)

    @discord.ui.button(label='Pause', style=discord.ButtonStyle.primary)
    async def pause_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.ctx.voice_client.pause()
        await interaction.response.send_message('⏸️ Paused playback', ephemeral=True)

    @discord.ui.button(label='Stop', style=discord.ButtonStyle.red)
    async def stop_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.ctx.voice_client.stop()
        global loop
        if loop:
            loop = False
        await interaction.response.send_message('⏹️ Stopped playback, loop disabled', ephemeral=True)

    @discord.ui.button(label='Skip', style=discord.ButtonStyle.secondary)
    async def skip_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message('⏭️ Skipped to next song', ephemeral=True)

        if self.ctx.voice_client and self.ctx.voice_client.is_playing():
            self.ctx.voice_client.stop()

        bot.loop.create_task(next_song(self.ctx))

    @discord.ui.button(label='Loop', style=discord.ButtonStyle.green, row=1)
    async def loop_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        global loop
        loop = not loop
        if loop:
            await interaction.response.send_message("🔁 Loop enabled", ephemeral=False)
        else:
            await interaction.response.send_message("➡️ Loop disabled", ephemeral=False)

async def next_song(ctx, search=None):
    if ctx.voice_client:
        ctx.voice_client.stop()
    await asyncio.sleep(1)

    if loop and search:
        await search_song(ctx, search=search)
    else:
        if len(queue) == 0:
            await ctx.send("📭 Queue is empty. Add more songs with !play")
            return
        else:
            if ctx.voice_client and ctx.voice_client.is_playing():
                ctx.voice_client.stop()
            next_search = queue.pop(0)
            await ctx.send(f"⏭️ Playing next song: {next_search}")
            await search_song(ctx, search=next_search)

@bot.command(name='play')
async def search_song(ctx, *, search: str = None):
    """Play a song by name or URL"""
    if search is None:
        await ctx.send('❓ Please enter a song name or URL')
        return

    # If already playing, add to queue
    if ctx.voice_client and ctx.voice_client.is_playing():
        queue.append(search)
        await ctx.send(f'📋 "{search}" added to queue')
        return
    
    # Check if user is in voice channel
    if not ctx.author.voice:
        await ctx.send('❌ You must be in a voice channel to use this command!')
        return 
  
    # Connect to voice channel if not already connected
    if ctx.voice_client is None:
        vc = await ctx.author.voice.channel.connect()
    else:
        vc = ctx.voice_client

    # Search for song
    if 'https://' in search:
        await ctx.send(f'🔍 Searching for "<{search}>"')
        player = await YTDLSource.from_url(search, loop=bot.loop, stream=True, ctx=ctx)
    else:
        await ctx.send(f'🔍 Searching for "{search}"')
        player = await YTDLSource.search(search, loop=bot.loop, stream=True, ctx=ctx)
    
    if player is None:
        await ctx.send('❌ Could not find the song')
        return

    # Format upload date if available
    try:
        date_formatted = f"{player.date[:4]}-{player.date[4:6]}-{player.date[6:]}"
    except (IndexError, TypeError):
        date_formatted = "Unknown date"

    # Create embed with song info
    embed = discord.Embed(title=player.title, color=discord.Color.blue())
    embed.add_field(name='👁️ Views', value=player.views or "Unknown", inline=True)
    embed.add_field(name='👍 Likes', value=player.likes or "Unknown", inline=True)
    embed.add_field(name='📅 Uploaded', value=date_formatted, inline=True)
    embed.add_field(name='⏱️ Duration', value=player.duration, inline=True)
    
    if player.thumbnail:
        embed.set_thumbnail(url=player.thumbnail)
    
    embed.set_footer(text=f"Requested by {ctx.author.display_name}")
    
    message = await ctx.send(embed=embed)
    
    # Play the song
    ctx.voice_client.play(player, after=lambda e: bot.loop.create_task(next_song(ctx, search)))

    # Create controls
    ctx.bot.controls = Controls(ctx, player.uploader, search)
    await ctx.send("🎮 Music Controls:", view=ctx.bot.controls)
    
    # Progress bar updates
    total_duration = player.raw_duration
    elapsed = 0
    bar_length = 20

    while elapsed < total_duration and ctx.voice_client and ctx.voice_client.is_playing():
        await asyncio.sleep(10)
        elapsed += 10

        if not ctx.voice_client or not ctx.voice_client.is_playing():
            break

        percentage = min(elapsed / total_duration, 1)
        filled_blocks = int(percentage * bar_length)
        empty_blocks = bar_length - filled_blocks
        progress_bar = "█" * filled_blocks + "░" * empty_blocks

        embed.set_field_at(3, name='⏱️ Duration', value=f'{parse_duration(elapsed)} {progress_bar} {player.duration}', inline=True)
        try:
            await message.edit(embed=embed)
        except discord.errors.NotFound:
            break

@bot.command(name='skip')
async def skip(ctx):
    """Skip the current song"""
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.stop()
        await ctx.send("⏭️ Skipped song")
        await next_song(ctx)
    else:
        await ctx.send("❌ Nothing playing to skip")

@bot.command(name='stop')
async def stop(ctx):
    """Stop playback and clear the queue"""
    global queue, loop
    queue = []
    loop = False
    
    if ctx.voice_client:
        ctx.voice_client.stop()
        await ctx.voice_client.disconnect()
        await ctx.send("⏹️ Stopped playing music and cleared queue")
    else:
        await ctx.send("❌ Not connected to a voice channel")

@bot.command(name='pause')
async def pause(ctx):
    """Pause the current song"""
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.pause()
        await ctx.send("⏸️ Paused")
    else:
        await ctx.send("❌ Nothing playing to pause")

@bot.command(name='resume')
async def resume(ctx):
    """Resume the paused song"""
    if ctx.voice_client and ctx.voice_client.is_paused():
        ctx.voice_client.resume()
        await ctx.send("▶️ Resumed")
    else:
        await ctx.send("❌ Nothing paused to resume")

@bot.command(name='queue', aliases=['q'])
async def show_queue(ctx):
    """Show the current queue"""
    if not queue:
        await ctx.send("📭 Queue is empty")
        return
        
    embed = discord.Embed(title="🎵 Music Queue", color=discord.Color.blue())
    for i, song in enumerate(queue, start=1):
        embed.add_field(name=f"{i}. {song}", value="\u200b", inline=False)
    
    await ctx.send(embed=embed)

@bot.command(name='loop')
async def toggle_loop(ctx):
    """Toggle song looping"""
    global loop
    loop = not loop
    if loop:
        await ctx.send("🔁 Loop enabled")
    else:
        await ctx.send("➡️ Loop disabled")

@bot.command(name='clear')
async def clear_queue(ctx):
    """Clear the song queue"""
    global queue
    queue = []
    await ctx.send("🧹 Queue cleared")

@bot.event
async def on_ready():
    """When the bot is ready"""
    activity = discord.Activity(type=discord.ActivityType.listening, name="!play [song]")
    await bot.change_presence(activity=activity)
    print(f'Logged in as {bot.user.name}')
    print('------')

if __name__ == "__main__":
    keep_alive()  # Keep the bot alive
    bot.run(os.getenv("DISCORD_TOKEN"))
