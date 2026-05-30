import discord
from discord.ext import commands

bot = discord.Bot()

class General(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @discord.slash_command(name="hello", description="Say hello to the bot")
    async def hello(self, ctx: discord.ApplicationContext):
        await ctx.respond(f"Hey!")

def setup(bot):
    # This function is required to load the cog into the bot
    bot.add_cog(General(bot))
