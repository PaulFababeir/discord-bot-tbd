import discord
import os # default module
from dotenv import load_dotenv

load_dotenv() # load all the variables from the env file

# Load testing guild IDs from the .env file (supports comma-separated IDs)
raw_guild_ids = os.getenv('GUILD_ID')
debug_guilds = [int(g_id.strip()) for g_id in raw_guild_ids.split(',')] if raw_guild_ids else None

bot = discord.Bot()

# List of cogs to load
cogs_list = [
    'cogs.general',
    'cogs.info',
    'cogs.music',
    'cogs.leaderboard',
]

for cog in cogs_list:
    bot.load_extension(cog)

@bot.event
async def on_ready():
    print(f"{bot.user} is ready and online!")

bot.run(os.getenv('TOKEN')) # run the bot with the token