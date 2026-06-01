import discord
from discord.commands import slash_command
from discord.ext import commands
from database.manager import get_top_songs
import re

class Leaderboard(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def clean_title(self, title: str) -> str:
        """Removes common tags like (Official Video) or [Lyric Video] from titles."""
        title = re.sub(r'(?i)\s*[\[(][^\])]*(?:official|music|lyric|audio|video|visualizer|mv|live|hd|hq|4k)[^\])]*[\])]', '', title)
        # Also remove common unbracketed tags at the end of the title
        title = re.sub(r'(?i)\s*(?:[-|]\s*)?\b(?:official\s+(?:music\s+|lyric\s+)?video|official\s+audio|lyric\s+video|music\s+video|visualizer|audio)\b.*$', '', title)
        title = re.sub(r'\s*[-|]\s*$', '', title) # Removes trailing hyphens/pipes left behind
        return title.strip()

    @slash_command(name="topsongs", description="Displays the top 10 most played songs globally.")
    async def topsongs(self, ctx: discord.ApplicationContext):
        # Defer since database queries might take a moment
        await ctx.defer()
        
        # Fetch the top 10 songs from Supabase
        top_songs = await get_top_songs(limit=10)
        
        if not top_songs:
            return await ctx.respond("No songs have been played yet! Be the first to start the party.")
            
        embed = discord.Embed(
            title="🏆 Global Most Played Songs",
            color=discord.Color.gold()
        )
        
        description = ""
        for index, song in enumerate(top_songs, start=1):
            raw_title = song.get("title", "Unknown Title")
            title = self.clean_title(raw_title)
            plays = song.get("play_count", 0)
            description += f"**{index}.** {title} — `{plays} plays`\n\n"
            
        embed.description = description
        embed.set_footer(text="Keep listening to boost your favorites!")
        
        await ctx.respond(embed=embed)

def setup(bot):
    bot.add_cog(Leaderboard(bot))
