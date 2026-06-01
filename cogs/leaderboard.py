import discord
from discord.commands import slash_command
from discord.ext import commands
from database.manager import get_top_songs

class Leaderboard(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @slash_command(name="leaderboard", description="Displays the top 10 most played songs globally.")
    async def leaderboard(self, ctx: discord.ApplicationContext):
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
            title = song.get("title", "Unknown Title")
            plays = song.get("play_count", 0)
            description += f"**{index}.** {title} — `{plays} plays`\n\n"
            
        embed.description = description
        embed.set_footer(text="Keep listening to boost your favorites!")
        
        await ctx.respond(embed=embed)

def setup(bot):
    bot.add_cog(Leaderboard(bot))
