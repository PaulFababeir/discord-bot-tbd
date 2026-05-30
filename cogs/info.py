import discord
from discord.ext import commands

class Info(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @discord.slash_command(name="info", description="Displays information about the bot")
    async def info(self, ctx: discord.ApplicationContext):
        embed = discord.Embed(
            title="Bot Information",
            description="I am a scalable, modular Discord bot!",
            color=discord.Color.blue()
        )
        embed.add_field(name="Latency", value=f"{round(self.bot.latency * 1000)}ms")
        
        await ctx.respond(embed=embed)

def setup(bot):
    bot.add_cog(Info(bot))
