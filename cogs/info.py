import discord
from discord.commands import slash_command
from discord.ext import commands
import platform

class Info(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @slash_command(name="info", description="Displays detailed information about the bot")
    async def info(self, ctx: discord.ApplicationContext):
        embed = discord.Embed(
            title="🤖 hiiii >////<",
            description="A music bot side project by Fabi",
            color=discord.Color.dark_green()
        )
        
        # Top Right Thumbnail
        if self.bot.user.display_avatar:
            embed.set_thumbnail(url=self.bot.user.display_avatar.url)
            
        # Bottom Image
        # embed.set_image(url="https://images.unsplash.com/photo-1550745165-9bc0b252726f?q=80&w=1024&auto=format&fit=crop")
        
        # Calculate the total number of users across all servers the bot is in
        total_users = sum([guild.member_count for guild in self.bot.guilds if guild.member_count])
        
        # Informational Fields
        embed.add_field(name="👨‍💻 Developer", value="**Fabi**", inline=True)
        embed.add_field(name="📊 Servers", value=f"{len(self.bot.guilds)}", inline=True)
        embed.add_field(name="👥 Total Users", value=f"{total_users}", inline=True)
        
        embed.add_field(name="⚙️ Python Version", value=platform.python_version(), inline=True)
        embed.add_field(name="📚 Library", value=f"Pycord {discord.__version__}", inline=True)
        embed.add_field(name="📡 Latency", value=f"{round(self.bot.latency * 1000)}ms", inline=True)
        
        # Footer
        embed.set_footer(text=f"Requested by {ctx.author.display_name}", icon_url=ctx.author.display_avatar.url)

        await ctx.respond(embed=embed)

def setup(bot):
    bot.add_cog(Info(bot))
