import discord
from discord.commands import slash_command, option
from discord.ext import commands, pages
import yt_dlp
import asyncio
import time
import aiohttp
import re

# Configurations for yt-dlp to extract the stream link safely
YTDL_OPTIONS = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'quiet': True,
    'no_warnings': True,
    'source_address': '0.0.0.0' # Forces IPv4 to prevent connection timeouts
}

# Advanced FFmpeg arguments that ensure a smooth network stream
FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn' # Processes audio only, ignoring the heavy video channel
}

def create_progress_bar(current_sec, total_sec, length=20):
    """Generates a text-based progress bar."""
    if not total_sec:
        return "🔘" + "▬" * (length - 1) + " `Live / Unknown Duration`"
    
    progress = int(length * current_sec / total_sec)
    progress = max(0, min(length - 1, progress)) # Keep index in bounds
    
    bar = "▬" * progress + "🔘" + "▬" * (length - progress - 1)
    
    curr_str = time.strftime('%H:%M:%S' if total_sec >= 3600 else '%M:%S', time.gmtime(current_sec))
    tot_str = time.strftime('%H:%M:%S' if total_sec >= 3600 else '%M:%S', time.gmtime(total_sec))
    
    return f"{bar} `{curr_str} / {tot_str}`"

class MusicController(discord.ui.View):
    """Interactive buttons attached to the 'Now Playing' message."""
    def __init__(self, cog, ctx):
        super().__init__(timeout=None)
        self.cog = cog
        self.ctx = ctx

    def get_progress_embed(self):
        guild_id = self.ctx.guild.id
        track = self.cog.current_track.get(guild_id)
        if not track:
            return discord.Embed(description="No track is currently playing.", color=discord.Color.red())
        
        # Calculate current time based on whether it is actively playing or paused
        if track['is_paused']:
            current_time = track['accumulated_time']
        else:
            current_time = track['accumulated_time'] + (time.time() - track['start_time'])
        
        bar = create_progress_bar(current_time, track['duration'])
        
        embed = discord.Embed(
            title=f"🎶 Now Playing: {track['title']}",
            url=track['url'],
            color=discord.Color.blue()
        )
        embed.description = bar
        if track['thumbnail']:
            embed.set_image(url=track['thumbnail'])
        return embed

    @discord.ui.button(label="Pause / Resume", style=discord.ButtonStyle.primary, emoji="⏯️")
    async def toggle_pause(self, button: discord.ui.Button, interaction: discord.Interaction):
        vc = self.ctx.voice_client
        if not vc: return await interaction.response.send_message("Not connected to a voice channel.", ephemeral=True)
        
        # Triggers your cog's existing commands via the view!
        if vc.is_playing():
            await self.cog.pause(self.ctx)
        elif vc.is_paused():
            await self.cog.resume(self.ctx)
        await interaction.response.edit_message(embed=self.get_progress_embed())

    @discord.ui.button(label="Skip", style=discord.ButtonStyle.danger, emoji="⏭️")
    async def skip_track(self, button: discord.ui.Button, interaction: discord.Interaction):
        await self.cog.skip(self.ctx)
        for child in self.children: child.disabled = True
        await interaction.response.edit_message(view=self)

    @discord.ui.button(label="Refresh", style=discord.ButtonStyle.secondary, emoji="🔄")
    async def refresh(self, button: discord.ui.Button, interaction: discord.Interaction):
        if not self.ctx.voice_client or (not self.ctx.voice_client.is_playing() and not self.ctx.voice_client.is_paused()):
            for child in self.children: child.disabled = True
            return await interaction.response.edit_message(content="**Track ended.**", embed=self.get_progress_embed(), view=self)
        await interaction.response.edit_message(embed=self.get_progress_embed())

class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.queues = {} # Maps guild IDs to a list of queued songs
        self.current_track = {} # Maps guild IDs to current track info

    # CLEAR VC STATE
    @commands.Cog.listener()
    async def on_ready(self):
        for guild in self.bot.guilds:
            if guild.me.voice:
                await guild.me.edit(voice_channel=None)

    def check_queue(self, ctx: discord.ApplicationContext):
        """Called automatically when a song finishes playing."""
        if ctx.guild.id in self.queues and len(self.queues[ctx.guild.id]) > 0:
            # Pop the next song from the queue
            next_song = self.queues[ctx.guild.id].pop(0)
            
            # The 'after' callback is synchronous, so we must schedule 
            # the async playback onto the bot's event loop
            coro = self.play_next_song(ctx, next_song['url'])
            asyncio.run_coroutine_threadsafe(coro, self.bot.loop)

    async def play_next_song(self, ctx: discord.ApplicationContext, original_url: str):
        """Helper to safely fetch and play the next song in the background."""
        vc = ctx.voice_client
        if not vc:
            return

        # Re-extract the stream to prevent "HTTP 403 Forbidden" expiration errors
        with yt_dlp.YoutubeDL(YTDL_OPTIONS) as ydl:
            loop = asyncio.get_event_loop()
            info = await loop.run_in_executor(None, lambda: ydl.extract_info(original_url, download=False))
            
            # Extract the actual track info if a search query/playlist was provided
            if 'entries' in info:
                info = info['entries'][0]
                
            stream_url = info['url']
            title = info.get('title', 'Unknown Title')
            duration = info.get('duration', 0)
            thumbnail = info.get('thumbnail')

        raw_audio = discord.FFmpegPCMAudio(stream_url, **FFMPEG_OPTIONS)
        audio_source = discord.PCMVolumeTransformer(raw_audio, volume=0.30) # Sets volume to 50%
        
        self.current_track[ctx.guild.id] = {
            'title': title,
            'url': original_url,
            'duration': duration,
            'thumbnail': thumbnail,
            'start_time': time.time(),
            'is_paused': False,
            'accumulated_time': 0
        }
        
        # Pass check_queue back into 'after' to keep the loop going!
        vc.play(audio_source, after=lambda e: self.check_queue(ctx))
        
        view = MusicController(self, ctx)
        await ctx.send(embed=view.get_progress_embed(), view=view)

    # PLAY COMMAND
    @slash_command(description="Plays audio directly from a provided YouTube or web link.")
    @option("url", str, description="Paste the direct music link here (e.g., YouTube URL)", required=True)
    async def play(
        self, 
        ctx: discord.ApplicationContext, 
        url: str
    ):
        # 1. Defer the response because pulling metadata from YouTube takes 1–3 seconds
        await ctx.defer()

        # 2. Safety Check: Verify if the user is currently inside a Voice Channel
        if not getattr(ctx.author, "voice", None):
            return await ctx.respond("[❌] You must be inside a voice channel to use this command!")

        user_voice_channel = ctx.author.voice.channel

        # 3. Connect to the Voice Channel if the bot isn't already there
        if ctx.voice_client is None:
            vc = await user_voice_channel.connect()
        else:
            vc = ctx.voice_client

        # Spotify Bait and Switch
        if "spotify.com" in url:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(f"https://open.spotify.com/oembed?url={url}") as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            # Overwrite the URL with a YouTube search query for the top result
                            title = data.get('title', 'Unknown Title')
                            author = data.get('author_name', '')

                            # Fallback if Spotify's Oembed API omits the author name
                            if not author:
                                async with session.get(url) as html_resp:
                                    if html_resp.status == 200:
                                        html = await html_resp.text()
                                        match = re.search(r'<title>(.*?)</title>', html, re.IGNORECASE)
                                        if match:
                                            # Grabs e.g., "Song - song and lyrics by Artist | Spotify"
                                            title = match.group(1).replace(" | Spotify", "")
                                            
                            url = f"ytsearch1:{title} {author} audio".strip()
                        else:
                            return await ctx.respond("[❌] Could not extract track info from that Spotify link.")
            except Exception as e:
                return await ctx.respond(f"[❌] Error connecting to Spotify: {e}")

        # 4. Extract the direct audio stream from the link using yt-dlp
        with yt_dlp.YoutubeDL(YTDL_OPTIONS) as ydl:
            try:
                # Extract metadata without downloading the actual file to your machine.
                # We use a background thread to prevent the synchronous yt-dlp library from freezing the bot.
                loop = asyncio.get_event_loop()
                info = await loop.run_in_executor(None, lambda: ydl.extract_info(url, download=False))
                
                # Extract the first result if it's a search result
                if 'entries' in info:
                    info = info['entries'][0]
                    
                stream_url = info['url']
                title = info.get('title', 'Unknown Title')
                duration = info.get('duration', 0)
                thumbnail = info.get('thumbnail')
                # Store the direct YouTube link so the background queue player doesn't have to search again
                resolved_url = info.get('webpage_url', url)
            except Exception as e:
                return await ctx.respond(f"[❌] Failed to extract audio stream from that link. Error: {e}")

        # 5. Check if we should queue the song or play it immediately
        if vc.is_playing() or vc.is_paused():
            # Initialize the server's queue if it doesn't exist yet
            if ctx.guild.id not in self.queues:
                self.queues[ctx.guild.id] = []
            
            # Add the URL, Title, and Thumbnail to the queue
            self.queues[ctx.guild.id].append({'url': resolved_url, 'title': title, 'thumbnail': thumbnail})
            return await ctx.respond(f"✅ Added to queue: **{title}**")

        # 6. Stream the raw audio directly into the voice channel using FFmpeg
        raw_audio = discord.FFmpegPCMAudio(stream_url, **FFMPEG_OPTIONS)
        audio_source = discord.PCMVolumeTransformer(raw_audio, volume=0.30) # Sets volume to 50%
        
        self.current_track[ctx.guild.id] = {
            'title': title,
            'url': resolved_url,
            'duration': duration,
            'thumbnail': thumbnail,
            'start_time': time.time(),
            'is_paused': False,
            'accumulated_time': 0
        }
        
        # IMPORTANT: Add the after callback here!
        vc.play(audio_source, after=lambda e: self.check_queue(ctx))

        view = MusicController(self, ctx)
        await ctx.respond(embed=view.get_progress_embed(), view=view)

    # QUEUE COMMAND
    @slash_command(description="Displays the current music queue.")
    async def queue(self, ctx: discord.ApplicationContext):
        if ctx.guild.id not in self.queues or not self.queues[ctx.guild.id]:
            return await ctx.respond("[⚠️] The queue is currently empty.")
            
        queue_list = self.queues[ctx.guild.id]
        embeds = []
        chunk_size = 10 # Display 5 songs per page
        
        for i in range(0, len(queue_list), chunk_size):
            chunk = queue_list[i:i+chunk_size]
            embed = discord.Embed(
                title="🎶 Current Music Queue",
                color=discord.Color.blue()
            )
            
            description = ""
            for j, song in enumerate(chunk):
                description += f"**{i + j + 1}.** [{song['title']}]({song['url']})\n\n"
                
            embed.description = description
            
            # Set the thumbnail to the first song in this page's chunk
            if chunk[0].get('thumbnail'):
                embed.set_thumbnail(url=chunk[0]['thumbnail'])
                
            embeds.append(embed)
            
        # If there's only 1 page, just send the embed on its own
        if len(embeds) == 1:
            await ctx.respond(embed=embeds[0])
        else:
            paginator = pages.Paginator(pages=embeds, show_disabled=True, show_indicator=True)
            await paginator.respond(ctx.interaction)

    # DISCONNECT COMMAND
    @slash_command(description="Disconnects the bot from the voice channel.")
    async def disconnect(self, ctx: discord.ApplicationContext):
        if ctx.voice_client:
            await ctx.voice_client.disconnect()
            await ctx.respond("[👋] Left the voice channel.")
        elif ctx.guild and ctx.guild.me.voice:
            # Handles the edge case where the bot lost its local voice state but is physically still in the VC
            await ctx.guild.me.edit(voice_channel=None)
            await ctx.respond("[👋] Left the voice channel.")
        else:
            await ctx.respond("[❌] I am not connected to any voice channel.")
    
    # PAUSE COMMAND
    @slash_command(description="Pauses the currently playing track.")
    async def pause(self, ctx: discord.ApplicationContext):
        vc = ctx.voice_client

        if not vc:
            return await ctx.respond("[❌] I am not connected to a voice channel.")
        
        if vc.is_playing():
            vc.pause()
            track = self.current_track.get(ctx.guild.id)
            if track:
                track['accumulated_time'] += time.time() - track['start_time']
                track['is_paused'] = True
            await ctx.respond("[⏸️] Paused the current track.")
        else:
            await ctx.respond("[⚠️] No audio is currently playing.")

    # RESUME COMMAND
    @slash_command(description="Resumes a paused track.")
    async def resume(self, ctx: discord.ApplicationContext):
        vc = ctx.voice_client

        if not vc:
            return await ctx.respond("[❌] I am not connected to a voice channel.")
        
        if vc.is_paused():
            vc.resume()
            track = self.current_track.get(ctx.guild.id)
            if track:
                track['start_time'] = time.time()
                track['is_paused'] = False
            await ctx.respond("[▶️] Resumed the track.")
        else:
            await ctx.respond("[⚠️] The audio is not paused.")

    # SKIP COMMAND
    @slash_command(description="Skips the currently playing song.")
    async def skip(self, ctx: discord.ApplicationContext):
        vc = ctx.voice_client

        if not vc:
            return await ctx.respond("[❌] I am not connected to a voice channel.")
        
        if vc.is_playing() or vc.is_paused():
            vc.stop() # This automatically triggers the 'after' callback to play the next song!
            await ctx.respond("[⏭️] Skipped the current track.")
        else:
            await ctx.respond("[⚠️] No audio is currently playing to skip.")

    # REMOVE COMMAND
    @slash_command(description="Removes a specific song from the queue.")
    @option("index", int, description="The queue number of the song to remove", required=True)
    async def remove(self, ctx: discord.ApplicationContext, index: int):
        if ctx.guild.id not in self.queues or not self.queues[ctx.guild.id]:
            return await ctx.respond("[⚠️] The queue is currently empty.")
            
        queue_list = self.queues[ctx.guild.id]
        
        if index < 1 or index > len(queue_list):
            return await ctx.respond(f"[❌] Invalid number! Please provide a number between 1 and {len(queue_list)}.")
            
        removed_song = queue_list.pop(index - 1)
        await ctx.respond(f"🗑️ Removed from queue: **{removed_song['title']}**")

    # NOW PLAYING COMMAND
    @slash_command(description="Displays the currently playing song and its progress.")
    async def nowplaying(self, ctx: discord.ApplicationContext):
        vc = ctx.voice_client
        if not vc or not (vc.is_playing() or vc.is_paused()):
            return await ctx.respond("[⚠️] No audio is currently playing.")
            
        view = MusicController(self, ctx)
        await ctx.respond(embed=view.get_progress_embed(), view=view)

def setup(bot):
    bot.add_cog(Music(bot))