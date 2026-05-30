import discord
from discord.ext import commands

class General(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @discord.slash_command(name="hello", description="Say hello to the bot")
    async def hello(self, ctx: discord.ApplicationContext):
        await ctx.respond(f"Hey!")

    @discord.slash_command(name="hi", description="Say hi to the bot")
    async def hello(self, ctx: discord.ApplicationContext):
        await ctx.respond(f"Hey!")    

def setup(bot):
    # This function is required to load the cog into the bot
    bot.add_cog(General(bot))
