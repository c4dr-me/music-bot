import os
import discord
import yt_dlp
import asyncio
import ctypes
import ctypes.util
import time
from discord.ext import commands, tasks
from discord import FFmpegPCMAudio
import random
from dotenv import load_dotenv
from keep_alive import keep_alive
import requests

load_dotenv()  # Load .env variables

# Disable yt-dlp bug reports
yt_dlp.utils.bug_reports_message = lambda: ''
API_TOKEN = "6NB4byix7b0IKrcBHABrIvIUOjJOEzyjUMaPdmfIx2T2QyL3P4x3qGSnwGvJxtoU"
HEADERS = {
    "Authorization": f"Bearer {API_TOKEN}",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0)"
}
# Configure opus loading
if not discord.opus.is_loaded():
    try:
        print("Attempting to load opus library...")

        # Try loading from system paths first
        opus_path = ctypes.util.find_library('opus')
        if opus_path:
            try:
                discord.opus.load_opus(opus_path)
                print(
                    f"Successfully loaded opus from system path: {opus_path}")
            except Exception as e:
                print(f"Failed to load opus from system path: {e}")

        # If not loaded, try common locations
        if not discord.opus.is_loaded():
            possible_opus_paths = [
                '/usr/lib/libopus.so.0',
                '/usr/lib/x86_64-linux-gnu/libopus.so.0',
                '/nix/store/*/libopus.so.0',
                '/home/runner/.apt/usr/lib/libopus.so.0',
                '/home/runner/.apt/lib/libopus.so.0',
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
                        except Exception as e:
                            print(f"Failed to load opus from {p}: {e}")
                            continue
                else:
                    try:
                        discord.opus.load_opus(path)
                        print(f"Successfully loaded opus from {path}")
                        break
                    except Exception as e:
                        print(f"Failed to load opus from {path}: {e}")
                        continue

        # Create a symbolic link to ffmpeg if needed
        if not os.path.exists('ffmpeg') and os.path.exists('/usr/bin/ffmpeg'):
            os.symlink('/usr/bin/ffmpeg', 'ffmpeg')
            print("Created symlink to system ffmpeg")

        # Final check
        if not discord.opus.is_loaded():
            print("WARNING: Could not load opus library automatically.")
            print("Voice functionality might not work without opus.")
    except Exception as e:
        print(f"Error during opus loading process: {e}")
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
    'extract_flat': False,
    'geo_bypass': True,
    'geo_bypass_country': 'US',
    'extractor_retries': 5,
    'http_headers': {
        'User-Agent':
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4577.63 Safari/537.36'
    },
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'opus',
    }]
}

ffmpeg_options = {
    'before_options':
    '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 10',
    'options': '-vn'
}

ytdl = yt_dlp.YoutubeDL(ytdl_format_options)
queue = []
loop = False
voice_clients = {
}  # Dictionary to store voice clients and their last activity time


# Make commands case-insensitive
def get_prefix(bot, message):
    return "!"


bot = commands.Bot(command_prefix="!", intents=discord.Intents.all(),case_insensitive=True)

# Keep track of sent messages for logging purposes
sent_messages = {}
log_channel_id = 1092519448314912863

@bot.event
async def on_message(message):
            # Ignore messages from the bot itself
            if message.author == bot.user:
                return

            # Check if the message is a DM
            if isinstance(message.channel, discord.DMChannel):
                # Log the message to the specified channel
                log_channel = bot.get_channel(log_channel_id)
                if log_channel:
                    # If it's a reply to one of the bot's messages
                    if message.reference:
                        original_message = await message.channel.fetch_message(message.reference.message_id)
                        await log_channel.send(f"User replied to bot's DM: {original_message.content}\nReply: {message.content}")
                    else:
                        # If it's a new DM, log it
                        await log_channel.send(f"New DM from {message.author}: {message.content}")

                # Handle the response or perform other actions as needed
                await message.channel.send("I received your message! I'll log it.")

            # Allow commands to still work by passing the message to the command handler
            await bot.process_commands(message)

@bot.command()
async def send_dm(ctx, member: discord.Member, *, content: str):
            """Command to send a DM to a user"""
            try:
                # Send a DM to the user
                await member.send(content)
                # Log the message sent
                print(f"Sent DM to {member}: {content}")
            except discord.errors.Forbidden:
                await ctx.send(f"Could not send DM to {member.mention}.")

# This dictionary will store the user and their annoyance task
annoyed_users = {}

# List of harmless messages
messages = [
    "क्या उल्लू बनाता है?", "क्या बकवास कर रहा है?", "तू बस बातें बनाता है!", "तेरी अकल पर पत्थर पड़ गया क्या?",
    "क्या फालतू बक रहा है?", "तू अपने काम से काम रख!", "तू बस बड़ी-बड़ी बातें करता है!", "तेरी बुद्धि कहाँ गुम हो गई?",
    "क्या तेरी बुद्धि सो गई है?", "तू बस बेवकूफ बनाता है!", "क्या तूने दिमाग लगाना छोड़ दिया?", "तू बस बकवास करता है!",
    "तू बस अपनी ही बातों में उलझा रहता है!", "क्या तूने दिमाग खो दिया?", "तू बस बातें बनाने में माहिर है!",
    "क्या तूने अकल पर ताला लगा रखा है?", "तू बस बड़बोला है!", "क्या तूने दिमाग घर पर छोड़ दिया?",
    "तू बस बातें बनाने में लगा रहता है!", "क्या तूने अकल को बंद कर दिया?", "तू बस बड़ी-बड़ी बातें करता है!",
    "क्या तूने दिमाग को आराम दे दिया?", "तू बस बकवास करने में मस्त है!", "क्या तूने अकल को गुम कर दिया?",
    "तू बस बातें बनाने में लगा रहता है!", "क्या तूने दिमाग को छुट्टी दे दी?", "तू बस बड़बोलेपन में मस्त है!",
    "क्या तूने अकल को सोने भेज दिया?", "तू बस बकवास करने में लगा रहता है!", "क्या तूने दिमाग को बंद कर दिया?",
    "तू बस बड़ी-बड़ी बातें करता है!", "क्या तूने अकल को गायब कर दिया?", "तू बस बकवास करने में मस्त है!",
    "क्या तूने दिमाग को छोड़ दिया?", "तू बस बड़बोलेपन में लगा रहता है!", "क्या तूने अकल को भूला दिया?",
    "तू बस बकवास करने में लगा रहता है!", "क्या तूने दिमाग को आराम दे दिया?", "तू बस बड़ी-बड़ी बातें करता है!",
    "क्या तूने अकल को गुम कर दिया?", "तू बस बकवास करने में मस्त है!", "क्या तूने दिमाग को छोड़ दिया?",
    "तू बस बड़बोलेपन में लगा रहता है!", "क्या तूने अकल को भूला दिया?", "तू बस बकवास करने में लगा रहता है!",
    "क्या तूने दिमाग को आराम दे दिया?", "तू बस बड़ी-बड़ी बातें करता है!", "क्या तूने अकल को गुम कर दिया?",
    "तू बस बकवास करने में मस्त है!", "क्या तूने दिमाग को छोड़ दिया?", "तू बस बड़बोलेपन में लगा रहता है!",
    "क्या तूने अकल को भूला दिया?", "तू बस बकवास करने में लगा रहता है!", "क्या तूने दिमाग को आराम दे दिया?",
    "तू बस बड़ी-बड़ी बातें करता है!", "क्या तूने अकल को गुम कर दिया?", "तू बस बकवास करने में मस्त है!",
    "क्या तूने दिमाग को छोड़ दिया?", "तू बस बड़बोलेपन में लगा रहता है!", "क्या तूने अकल को भूला दिया?",
    "तू बस बकवास करने में लगा रहता है!", "क्या तूने दिमाग को आराम दे दिया?", "तू बस बड़ी-बड़ी बातें करता है!",
    "क्या तूने अकल को गुम कर दिया?", "तू बस बकवास करने में मस्त है!", "क्या तूने दिमाग को छोड़ दिया?",
    "तू बस बड़बोलेपन में लगा रहता है!", "क्या तूने अकल को भूला दिया?", "तू बस बकवास करने में लगा रहता है!"
]

ALLOWED_ROLE_NAME = "Batman"

# Define the task to annoy users
@tasks.loop(minutes=1)
async def annoy_user():
    for user_id in annoyed_users:
        user = bot.get_user(user_id)
        if user:
            message = random.choice(messages)
            try:
                await user.send(message)
            except discord.errors.Forbidden:
                pass  # Ignore if DM is closed

# Helper function to check if the user has the "batman" role
def has_batman_role(ctx):
    return any(role.name.lower() == ALLOWED_ROLE_NAME.lower() for role in ctx.author.roles)

@bot.command()
async def annoy(ctx, member: discord.Member):
    """Command to annoy the user with random harmless messages."""
    if not has_batman_role(ctx):
        await ctx.send("Sorry, you don't have the required 'batman' role to annoy users.")
        return

    if member.id not in annoyed_users:
        annoyed_users[member.id] = True
        await ctx.send(f"Started annoying {member.mention} every minute!")

        # Start the loop if it's not already running
        if not annoy_user.is_running():
            annoy_user.start()
    else:
        await ctx.send(f"{member.mention} is already being annoyed!")

@bot.command()
async def unannoy(ctx, member: discord.Member):
    """Command to stop annoying the user."""
    if not has_batman_role(ctx):
        await ctx.send("Sorry, you don't have the required 'batman' role to stop annoying users.")
        return

    if member.id in annoyed_users:
        del annoyed_users[member.id]
        await ctx.send(f"Stopped annoying {member.mention}.")

        # If there are no users left to annoy, stop the loop
        if not annoyed_users:
            annoy_user.stop()
    else:
        await ctx.send(f"{member.mention} is not currently being annoyed.")

@bot.command()
async def stop_annoy(ctx, member: discord.Member):
    """Command to stop annoying the user."""
    if not has_batman_role(ctx):
        await ctx.send("Sorry, you don't have the required 'batman' role to stop annoying users.")
        return

    await unannoy(ctx, member)  # Reuse unannoy command to handle stopping.

# Global variable to store currently playing song
current_song = {"artist": None, "title": None}

async def get_lyrics(ctx, artist: str, song: str):        

        query = f'{song} {artist}'
        search_url = f"https://api.genius.com/search?q={query}"
        
        response = requests.get(search_url, headers=HEADERS)
        
        if not response.status_code == 200:
            await ctx.send(f"erroras {response.status_code} nxj")
            return
        
        search_data = response.json()
        try:
            song_url = search_data['response']['hits'][0]['result']['url']
            song_name = search_data['response']['hits'][0]['result']['title']
            song_artist = search_data['response']['hits'][0]['result']['primary_artist']['name']
            song_thumbnail = search_data['response']['hits'][0]['result']["song_art_image_thumbnail_url"]
            date = search_data['response']['hits'][0]['result']["release_date_for_display"]
        except IndexError:
            await ctx.send("neradau lyricsu")
            return
        
        embed = discord.Embed(title=song_name, url=song_url, color=discord.Color.pink())
        embed.set_author(name=song_artist)
        embed.set_thumbnail(url=song_thumbnail)
        embed.add_field(name='Released', value=date)
        
        await ctx.send(embed=embed, ephemeral=False)




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
        data = await loop.run_in_executor(
            None, lambda: ytdl.extract_info(url, download=not stream))
        if 'entries' in data:
            data = data['entries'][0]
        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options),
                   data=data)

    @classmethod
    async def search(cls, search: str, *, loop=None, stream=False, ctx=None):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(
            None,
            lambda: ytdl.extract_info(f'ytsearch:{search}', download=False))
        try:
            if 'entries' in data:
                data = data['entries'][0]
                filename = data['url']
                return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options),
                           data=data)
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
    async def resume_button(self, interaction: discord.Interaction,
                            button: discord.ui.Button):
        self.ctx.voice_client.resume()
        await interaction.response.send_message('▶️ Resumed playback',
                                                ephemeral=True)

    @discord.ui.button(label='Pause', style=discord.ButtonStyle.primary)
    async def pause_button(self, interaction: discord.Interaction,
                           button: discord.ui.Button):
        self.ctx.voice_client.pause()
        await interaction.response.send_message('⏸️ Paused playback',
                                                ephemeral=True)

    @discord.ui.button(label='Stop', style=discord.ButtonStyle.red)
    async def stop_button(self, interaction: discord.Interaction,
                          button: discord.ui.Button):
        self.ctx.voice_client.stop()
        global loop
        if loop:
            loop = False
        await interaction.response.send_message(
            '⏹️ Stopped playback, loop disabled', ephemeral=True)

    @discord.ui.button(label='Skip', style=discord.ButtonStyle.secondary)
    async def skip_button(self, interaction: discord.Interaction,
                          button: discord.ui.Button):
        await interaction.response.send_message('⏭️ Skipped to next song',
                                                ephemeral=True)

        if self.ctx.voice_client and self.ctx.voice_client.is_playing():
            self.ctx.voice_client.stop()

        bot.loop.create_task(next_song(self.ctx))

    @discord.ui.button(label='Lyrics', style=discord.ButtonStyle.blurple)
    async def lyrics_button(self, interaction: discord.Interaction,
                                button: discord.ui.Button):
        """Button to fetch and display lyrics"""        
        await interaction.response.defer()  # Acknowledge the interaction        
        await get_lyrics(self.ctx, self.artist, self.song)

    @discord.ui.button(label='Loop', style=discord.ButtonStyle.green, row=1)
    async def loop_button(self, interaction: discord.Interaction,
                          button: discord.ui.Button):
        global loop
        loop = not loop
        if loop:
            await interaction.response.send_message("🔁 Loop enabled",
                                                    ephemeral=False)
        else:
            await interaction.response.send_message("➡️ Loop disabled",
                                                    ephemeral=False)


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
        player = await YTDLSource.from_url(search,
                                           loop=bot.loop,
                                           stream=True,
                                           ctx=ctx)
    else:
        await ctx.send(f'🔍 Searching for "{search}"')
        player = await YTDLSource.search(search,
                                         loop=bot.loop,
                                         stream=True,
                                         ctx=ctx)

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
    embed.add_field(name='👁️ Views',
                    value=player.views or "Unknown",
                    inline=True)
    embed.add_field(name='👍 Likes',
                    value=player.likes or "Unknown",
                    inline=True)
    embed.add_field(name='📅 Uploaded', value=date_formatted, inline=True)
    embed.add_field(name='⏱️ Duration', value=player.duration, inline=True)

    if player.thumbnail:
        embed.set_thumbnail(url=player.thumbnail)

    embed.set_footer(text=f"Requested by {ctx.author.display_name}")

    # Create controls
    ctx.bot.controls = Controls(ctx, player.uploader, search)

    # Send embed with controls
    message = await ctx.send(embed=embed, view=ctx.bot.controls)

    # Play the song and update bot status
    ctx.voice_client.play(
        player, after=lambda e: bot.loop.create_task(next_song(ctx, search)))
    await bot.change_presence(activity=discord.Activity(
        type=discord.ActivityType.listening,
        name=f"{player.title[:100]} | discord.gg/dZygWejWv8"))

    # Update last activity time
    voice_clients[ctx.guild.id] = time.time()

    # Progress bar updates
    total_duration = player.raw_duration
    elapsed = 0
    bar_length = 20

    while elapsed < total_duration and ctx.voice_client and ctx.voice_client.is_playing(
    ):
        await asyncio.sleep(10)
        elapsed += 10

        if not ctx.voice_client or not ctx.voice_client.is_playing():
            break

        percentage = min(elapsed / total_duration, 1)
        filled_blocks = int(percentage * bar_length)
        empty_blocks = bar_length - filled_blocks
        progress_bar = "█" * filled_blocks + "░" * empty_blocks

        embed.set_field_at(
            3,
            name='⏱️ Duration',
            value=f'{parse_duration(elapsed)} {progress_bar} {player.duration}',
            inline=True)
        try:
            await message.edit(embed=embed)
        except discord.errors.NotFound:
            break


@bot.command(name='skip')
async def skip(ctx):
    """Skip the current song"""
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.stop()
        # Update activity time
        voice_clients[ctx.guild.id] = time.time()
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
        # Update activity time
        voice_clients[ctx.guild.id] = time.time()
        await ctx.send("⏸️ Paused")
    else:
        await ctx.send("❌ Nothing playing to pause")


@bot.command(name='resume')
async def resume(ctx):
    """Resume the paused song"""
    if ctx.voice_client and ctx.voice_client.is_paused():
        ctx.voice_client.resume()
        # Update activity time
        voice_clients[ctx.guild.id] = time.time()
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




async def check_voice_timeout():
    """Check for voice channel inactivity and disconnect if inactive for 5 minutes"""
    await bot.wait_until_ready()
    while not bot.is_closed():
        current_time = time.time()
        for guild_id, last_activity in list(voice_clients.items()):
            # If inactive for 5 minutes (300 seconds)
            if current_time - last_activity > 300:
                guild = bot.get_guild(guild_id)
                if guild and guild.voice_client:
                    await guild.voice_client.disconnect()
                    print(f"Disconnected from {guild.name} due to inactivity")
                    # Remove from tracking dictionary
                    if guild_id in voice_clients:
                        del voice_clients[guild_id]

        # Check every 30 seconds
        await asyncio.sleep(30)


@bot.event
async def on_ready():
    """When the bot is ready"""
    activity = discord.Activity(type=discord.ActivityType.listening,
                                name="!play | discord.gg/dZygWejWv8")
    await bot.change_presence(activity=activity)
    print(f'Logged in as {bot.user.name}')
    print('------')

    # Start the inactivity check task
    bot.loop.create_task(check_voice_timeout())


if __name__ == "__main__":
    keep_alive()  # Keep the bot alive
    bot.run(os.getenv("DISCORD_TOKEN"))
