import discord
from discord.commands import slash_command, option
from discord.ext import commands, pages
import yt_dlp
import asyncio
import aiohttp
import re
from database.manager import create_playlist, get_playlists, add_song_to_playlist

YTDL_OPTIONS = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'quiet': True,
    'no_warnings': True,
    'source_address': '0.0.0.0'
}

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

    # SHOW PLAYLISTS
    @slash_command(name="showplaylists", description="Displays all playlists or those of a specific user.")
    @option("user", discord.Member, description="View a specific user's playlists", required=False)
    async def showplaylists(self, ctx: discord.ApplicationContext, user: discord.Member = None):
        await ctx.defer()
        
        owner_id = user.id if user else None
        playlists = await get_playlists(owner_id)
        
        if not playlists:
            if user:
                return await ctx.respond(f"⚠️ **{user.display_name}** does not have any playlists yet.")
            else:
                return await ctx.respond("⚠️ No playlists have been created yet.")
                
        embeds = []
        chunk_size = 10 # Display 10 playlists per page
        
        for i in range(0, len(playlists), chunk_size):
            chunk = playlists[i:i+chunk_size]
            
            title = f"🎶 Playlists ({user.display_name})" if user else "🎶 Global Playlists"
            embed = discord.Embed(title=title, color=discord.Color.purple())
            
            description = ""
            for pl in chunk:
                name = pl.get("playlist_name", "Unknown Playlist")
                pl_owner_id = pl.get("owner_id")
                songs = pl.get("songs", [])
                song_count = len(songs) if songs else 0
                
                # Using the actual database ID for stable sequential querying later
                seq_id = pl.get("id")
                description += f"**{seq_id}.** {name}\n"
                description += f"└ 👤 <@{pl_owner_id}> | 🎵 {song_count} songs\n\n"
                
            embed.description = description
            embeds.append(embed)
            
        if len(embeds) == 1:
            await ctx.respond(embed=embeds[0])
        else:
            paginator = pages.Paginator(pages=embeds, show_disabled=True, show_indicator=True)
            await paginator.respond(ctx.interaction)

    # ADD SONG TO PLAYLIST
    @slash_command(name="addsong", description="Adds a song to a specific playlist.")
    @option("playlist_id", int, description="The ID of the playlist", required=True)
    @option("query", str, description="Paste a link or type a song name to search", required=True)
    async def addsong(self, ctx: discord.ApplicationContext, playlist_id: int, query: str):
        await ctx.defer()
        
        # Spotify Bait and Switch
        if "spotify.com" in query:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(f"https://open.spotify.com/oembed?url={query}") as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            title = data.get('title', 'Unknown Title')
                            author = data.get('author_name', '')

                            if not author:
                                async with session.get(query) as html_resp:
                                    if html_resp.status == 200:
                                        html = await html_resp.text()
                                        match = re.search(r'<title>(.*?)</title>', html, re.IGNORECASE)
                                        if match:
                                            title = match.group(1).replace(" | Spotify", "")
                                            
                            query = f"ytsearch1:{title} {author} audio".strip()
                        else:
                            return await ctx.respond("[❌] Could not extract track info from that Spotify link.")
            except Exception as e:
                print(f"[Spotify Error] An exception occurred: {e}")
                return await ctx.respond(f"[❌] An error occurred while trying to process that Spotify link.")
            
        elif not query.startswith(('http://', 'https://')):
            query = f"ytsearch1:{query}"

        # Extract from Link
        with yt_dlp.YoutubeDL(YTDL_OPTIONS) as ydl:
            try:
                loop = asyncio.get_event_loop()
                info = await loop.run_in_executor(None, lambda: ydl.extract_info(query, download=False))
                
                if 'entries' in info:
                    info = info['entries'][0]
                    
                title = info.get('title', 'Unknown Title')
                resolved_url = info.get('webpage_url', query)
            except Exception as e:
                print(f"[YTDL Error] Failed to extract from '{query}'. Error: {e}")
                return await ctx.respond(f"[❌] Failed to get a playable song from that query.")

        # Insert the song into the database
        data = await add_song_to_playlist(playlist_id=playlist_id, song_link=resolved_url, song_title=title)
        
        if data:
            await ctx.respond(f"✅ Successfully added **{title}** to Playlist **#{playlist_id}**!")
        else:
            await ctx.respond(f"❌ Failed to add song. Ensure the Playlist ID **#{playlist_id}** exists.")

def setup(bot):
    bot.add_cog(Playlist(bot))
