yt_dlp.utils.bug_reports_message = lambda: ''

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

queue: list[str] = []

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = data.get('url')
        self.views = data.get('view_count')
        self.likes = data.get('like_count')
        self.thumbnail = data.get('thumbnail')
        self.date = data.get('upload_date')
        self.duration = parse_duration(int(data.get('duration')))
        self.raw_duration = int(data.get('duration'))
        self.uploader = data.get('uploader')

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
                #print("FFmpeg will try to play:", data['url'])
                return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)
        except IndexError:
            await ctx.send('neradau')
            return None

            async def next_song(ctx, search=None):
    ctx.voice_client.stop() 
    await asyncio.sleep(1)

    if loop:
        await search_song(ctx, search=search)
    else:
        if len(queue) == 0:
            return
        else:
            if ctx.voice_client.is_playing():
                ctx.voice_client.stop()
            await search_song(ctx, search=queue.pop(0))                                                                         

loop: bool = False

class Controls(discord.ui.View):
    def __init__(self, ctx, artist, song):
        super().__init__(timeout=None)
        self.ctx = ctx
        self.song = song
        self.artist = artist

    @discord.ui.button(label='Resume', style=discord.ButtonStyle.green)
    async def resume_button(self, interaction: discord.Interaction, button: discord.Button):
        self.ctx.voice_client.resume()
        await interaction.response.send_message('Resumed', ephemeral=True)

    @discord.ui.button(label='Pause', style=discord.ButtonStyle.primary)
    async def pause_button(self, interaction: discord.Interaction, button: discord.Button):
        self.ctx.voice_client.pause()
        await interaction.response.send_message('Paused', ephemeral=True)

    @discord.ui.button(label='Stop', style=discord.ButtonStyle.red)
    async def stop_button(self, interaction: discord.Interaction, button: discord.Button):
        self.ctx.voice_client.stop()
        global loop
        if loop:
            loop = not loop
        await interaction.response.send_message('Stopped, loop disabled', ephemeral=True)

    @discord.ui.button(label='Skip', style=discord.ButtonStyle.secondary)
    async def skip_button(self, interaction: discord.Interaction, button: discord.Button):
        await interaction.response.send_message('Skipped', ephemeral=True)

        if self.ctx.voice_client and self.ctx.voice_client.is_playing():
            self.ctx.voice_client.stop()

        bot.loop.create_task(next_song(self.ctx))

    @discord.ui.button(label='Lyrics', style=discord.ButtonStyle.primary)
    async def lyrics_button(self, interaction: discord.Interaction, button:discord.Button):
        await interaction.response.defer()
        await get_lyrics(self.ctx, self.artist, self.song)

    @discord.ui.button(label='Loop', style=discord.ButtonStyle.green, row=1)
    async def loop_button(self, interaction: discord.Interaction, button: discord.Button):
        global loop
        loop = not loop
        if loop:
            await interaction.response.send_message("Loop enabled", ephemeral=False)
        else:
            await interaction.response.send_message("Loop disabled", ephemeral=False)


            @bot.command(name='play')
async def search_song(ctx, *, search:str=None):
    
    if search is None:
        await ctx.send('ivesk dainos pavadinima arba linka')
        return

    if ctx.voice_client and ctx.voice_client.is_playing():
        queue.append(search)
        await ctx.send(f'"{search}" ideta i queue')
        return
    
    if not ctx.author.voice:
        await ctx.send('neprijungtas prie vc')
        return 
  
    if ctx.voice_client is None:
        vc = await ctx.author.voice.channel.connect()
    else:
        vc = ctx.voice_client

    if 'https://' in search:
        await ctx.send(f'ieskau "<{search}>"')
    else:
        await ctx.send(f'ieskau "{search}"')
    player = await YTDLSource.search(search, loop=bot.loop, ctx=ctx)
    if player is None:
        await ctx.send('neradau')
        return

    date_padaryta = player.date[:4] + '-' + player.date[4:6] + '-' + player.date[6:]

    embed = discord.Embed(title=player.title, color=discord.Color.pink())
    embed.add_field(name='Views', value=player.views, inline=False)
    embed.add_field(name='Likes', value=player.likes, inline=False)
    embed.add_field(name='Uploaded', value=date_padaryta, inline=False)
    embed.add_field(name='Duration', value=player.duration, inline=True)
    embed.set_thumbnail(url=player.thumbnail)

    message = await ctx.send(embed=embed)
    
    ctx.voice_client.play(player, after=lambda e: bot.loop.create_task(next_song(ctx, search)))

    ctx.bot.controls = Controls(ctx, player.uploader, search)
    
    await ctx.send(view=ctx.bot.controls)
    
    total_duration = player.raw_duration
    elapsed = 0
    bar_length = 20

    while elapsed < total_duration and ctx.voice_client.is_playing():
        await asyncio.sleep(10)
        elapsed += 10

        percentage = min(elapsed / total_duration, 1)
        filled_blocks = int(percentage * bar_length)
        empty_blocks = int(bar_length - filled_blocks)
        progress_bar = "█" * filled_blocks + "░" * empty_blocks

        embed.set_field_at(3, name='Duration', value=f'{parse_duration(elapsed)} {progress_bar} {player.duration}', inline=True)
        await message.edit(embed=embed)