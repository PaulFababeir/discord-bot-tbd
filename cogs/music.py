import discord
from discord.commands import slash_command, option
from discord.ext import commands
import yt_dlp
import asyncio

# Configurations for yt-dlp to extract the stream link safely
YTDL_OPTIONS = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'quiet': True,
    'source_address': '0.0.0.0' # Forces IPv4 to prevent connection timeouts
}

# Advanced FFmpeg arguments that ensure a smooth network stream
FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn' # Processes audio only, ignoring the heavy video channel
}

class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.queues = {} # Maps guild IDs to a list of queued songs

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
            stream_url = info['url']
            title = info.get('title', 'Unknown Title')

        audio_source = discord.FFmpegPCMAudio(stream_url, **FFMPEG_OPTIONS)
        
        # Pass check_queue back into 'after' to keep the loop going!
        vc.play(audio_source, after=lambda e: self.check_queue(ctx))
        
        # Use ctx.send (instead of ctx.respond) because the initial interaction is already over
        await ctx.send(f"🎶 Now Streaming from Queue: **{title}**")

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

        # 4. Extract the direct audio stream from the link using yt-dlp
        with yt_dlp.YoutubeDL(YTDL_OPTIONS) as ydl:
            try:
                # Extract metadata without downloading the actual file to your machine.
                # We use a background thread to prevent the synchronous yt-dlp library from freezing the bot.
                loop = asyncio.get_event_loop()
                info = await loop.run_in_executor(None, lambda: ydl.extract_info(url, download=False))
                stream_url = info['url']
                title = info.get('title', 'Unknown Title')
            except Exception as e:
                return await ctx.respond(f"[❌] Failed to extract audio stream from that link. Error: {e}")

        # 5. Check if we should queue the song or play it immediately
        if vc.is_playing() or vc.is_paused():
            # Initialize the server's queue if it doesn't exist yet
            if ctx.guild.id not in self.queues:
                self.queues[ctx.guild.id] = []
            
            # Add the URL and Title to the queue
            self.queues[ctx.guild.id].append({'url': url, 'title': title})
            return await ctx.respond(f"✅ Added to queue: **{title}**")

        # 6. Stream the raw audio directly into the voice channel using FFmpeg
        audio_source = discord.FFmpegPCMAudio(stream_url, **FFMPEG_OPTIONS)
        
        # IMPORTANT: Add the after callback here!
        vc.play(audio_source, after=lambda e: self.check_queue(ctx))

        await ctx.respond(f"🎶 Now Streaming: **{title}**")

    # QUEUE COMMAND
    @slash_command(description="Displays the current music queue.")
    async def queue(self, ctx: discord.ApplicationContext):
        if ctx.guild.id not in self.queues or not self.queues[ctx.guild.id]:
            return await ctx.respond("[⚠️] The queue is currently empty.")
            
        queue_list = "\n".join([f"{i+1}. {song['title']}" for i, song in enumerate(self.queues[ctx.guild.id])])
        await ctx.respond(f"**Current Queue:**\n{queue_list}")

    # DISCONNECT COMMAND
    @slash_command(description="Disconnects the bot from the voice channel.")
    async def disconnect(self, ctx: discord.ApplicationContext):
        if ctx.voice_client:
            await ctx.voice_client.disconnect()
            await ctx.respond("[👋] Left the voice channel.")
        elif ctx.guild and ctx.guild.me.voice:
            # Handles the edge case where the bot lost its local voice state but is physically still in the VC
            await ctx.guild.me.edit(voice_channel=None)
            await ctx.respond("[👋] Forcefully left the voice channel after a restart.")
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
            await ctx.respond("[▶️] Resumed the track.")
        else:
            await ctx.respond("[⚠️] The audio is not paused.")

def setup(bot):
    bot.add_cog(Music(bot))