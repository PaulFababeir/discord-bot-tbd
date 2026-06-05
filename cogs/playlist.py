import discord
from discord.commands import slash_command, option
from discord.ext import commands
from database.manager import create_playlist

class Playlist(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # CREATE PLAYLIST
    @slash_command(name="createplaylist", description="Creates a new custom playlist.")
    @option("name", str, description="The name of your new playlist", required=True)
    async def createplaylist(self, ctx: discord.ApplicationContext, name: str):
        await ctx.defer()
        
        # Insert the new playlist into the database using the author's ID
        data = await create_playlist(name=name, owner_id=ctx.author.id)
        
        if data:
            await ctx.respond(f"✅ Successfully created playlist: **{name}**!")
        else:
            await ctx.respond(f"❌ Failed to create playlist: **{name}**. Please try again later.")

def setup(bot):
    bot.add_cog(Playlist(bot))
