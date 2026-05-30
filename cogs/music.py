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

    @slash_command(description="Plays audio directly from a provided YouTube or web link.")
    @option("url", str, description="Paste the direct music link here (e.g., YouTube URL)", required=True)
    async def play_link(
        self, 
        ctx: discord.ApplicationContext, 
        url: str
    ):
        # 1. Defer the response because pulling metadata from YouTube takes 1–3 seconds
        await ctx.defer()

        # 2. Safety Check: Verify if the user is currently inside a Voice Channel
        if not getattr(ctx.author, "voice", None):
            return await ctx.respond("❌ You must be inside a voice channel to use this command!")

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
                return await ctx.respond(f"❌ Failed to extract audio stream from that link. Error: {e}")

        # 5. Stop playback if a song is already running to avoid messy audio overlap
        if vc.is_playing():
            vc.stop()

        # 6. Stream the raw audio directly into the voice channel using FFmpeg
        audio_source = discord.FFmpegPCMAudio(stream_url, **FFMPEG_OPTIONS)
        vc.play(audio_source)

        await ctx.respond(f"🎶 Now Streaming: **{title}**")

    @slash_command(description="Disconnects the bot from the voice channel.")
    async def leave(self, ctx: discord.ApplicationContext):
        if ctx.voice_client:
            await ctx.voice_client.disconnect()
            await ctx.respond("👋 Left the voice channel.")
        else:
            await ctx.respond("❌ I am not connected to any voice channel.")

def setup(bot):
    bot.add_cog(Music(bot))