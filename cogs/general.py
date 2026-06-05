import discord
from discord.commands import slash_command
from discord.ext import commands

class General(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @slash_command(name="hello", description="Say hello to the bot")
    async def hello(self, ctx: discord.ApplicationContext):
        await ctx.respond(f"Hey!")

    @slash_command(name="hi", description="Say hi to the bot")
    async def hi(self, ctx: discord.ApplicationContext):
        await ctx.respond(f"Ho!")    

    @slash_command(name="commands", description="Displays all available commands organized by category.")
    async def show_commands(self, ctx: discord.ApplicationContext):
        embed = discord.Embed(
            title="📚 Available Commands",
            description="Here is a list of all commands you can use:",
            color=discord.Color.blurple()
        )

        # Dynamically iterate through all registered cogs
        for cog_name, cog in self.bot.cogs.items():
            cog_commands = cog.get_commands()
            if not cog_commands:
                continue
            
            command_list = ""
            for cmd in cog_commands:
                description = getattr(cmd, 'description', 'No description provided.')
                command_list += f"**/{cmd.name}** - {description}\n"
            
            if command_list:
                embed.add_field(name=f"✨ {cog_name.upper()}", value=command_list + "\u200b", inline=False)
        
        # Footer
        embed.set_footer(text=f"Requested by {ctx.author.display_name}", icon_url=ctx.author.display_avatar.url)

        await ctx.respond(embed=embed)

def setup(bot):
    # This function is required to load the cog into the bot
    bot.add_cog(General(bot))
