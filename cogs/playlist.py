import discord
from discord.commands import slash_command, option
from discord.ext import commands, pages
import yt_dlp
import asyncio
from database.manager import create_playlist, get_playlists, get_playlist, add_song_to_playlist, remove_song_from_playlist, get_songs_in_playlist, clear_playlist, delete_playlist, get_song
from utils import YTDL_OPTIONS, resolve_query, SpotifyResolutionError

class Playlist(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def _require_owner(self, ctx: discord.ApplicationContext, playlist_id: int):
        """Fetches a playlist and verifies the caller owns it. Responds and returns None on failure."""
        playlist = await get_playlist(playlist_id)
        if not playlist:
            await ctx.respond(f"❌ Playlist **#{playlist_id}** does not exist.")
            return None
        if playlist.get("owner_id") != ctx.author.id:
            await ctx.respond(f"❌ Only the owner of Playlist **#{playlist_id}** can do that.")
            return None
        return playlist

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
        
        # Resolves Spotify links to a YouTube search query, or wraps plain text as one
        try:
            query = await resolve_query(query)
        except SpotifyResolutionError as e:
            return await ctx.respond(str(e))

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

    # REMOVE SONG FROM PLAYLIST
    @slash_command(name="removesong", description="Removes a song from a playlist.")
    @option("song_id", int, description="The ID of the song to remove", required=True)
    async def removesong(self, ctx: discord.ApplicationContext, song_id: int):
        await ctx.defer()

        song = await get_song(song_id)
        if not song:
            return await ctx.respond(f"❌ Song **#{song_id}** does not exist.")

        if not await self._require_owner(ctx, song.get("playlist_id")):
            return

        # Delete the song from the database using its unique song_id
        data = await remove_song_from_playlist(song_id=song_id)

        if data:
            await ctx.respond(f"✅ Successfully removed song **#{song_id}** from the playlist!")
        else:
            await ctx.respond(f"❌ Failed to remove song. Ensure the Song ID **#{song_id}** exists.")

    # CLEAR PLAYLIST
    @slash_command(name="clearplaylist", description="Removes all songs from a specific playlist.")
    @option("playlist_id", int, description="The ID of the playlist to clear", required=True)
    async def clearplaylist(self, ctx: discord.ApplicationContext, playlist_id: int):
        await ctx.defer()

        if not await self._require_owner(ctx, playlist_id):
            return

        songs = await get_songs_in_playlist(playlist_id=playlist_id)
        if songs is None:
            return await ctx.respond(f"❌ Failed to fetch songs for Playlist **#{playlist_id}**.")
            
        if not songs:
            return await ctx.respond(f"⚠️ Playlist **#{playlist_id}** is already empty.")
            
        data = await clear_playlist(playlist_id=playlist_id)
        
        if data is not None:
            await ctx.respond(f"✅ Successfully removed **{len(songs)}** songs from Playlist **#{playlist_id}**!")
        else:
            await ctx.respond(f"❌ Failed to clear Playlist **#{playlist_id}**.")

    # DELETE PLAYLIST
    @slash_command(name="deleteplaylist", description="Deletes an empty playlist.")
    @option("playlist_id", int, description="The ID of the playlist to delete", required=True)
    async def deleteplaylist(self, ctx: discord.ApplicationContext, playlist_id: int):
        await ctx.defer()

        if not await self._require_owner(ctx, playlist_id):
            return

        songs = await get_songs_in_playlist(playlist_id=playlist_id)
        if songs is None:
            return await ctx.respond(f"❌ Failed to check Playlist **#{playlist_id}**. Ensure it exists.")
            
        if len(songs) > 0:
            return await ctx.respond(f"⚠️ Playlist **#{playlist_id}** is not empty! Please use `/clearplaylist` first.")
            
        data = await delete_playlist(playlist_id=playlist_id)
        
        if data:
            await ctx.respond(f"✅ Successfully deleted Playlist **#{playlist_id}**!")
        else:
            await ctx.respond(f"❌ Failed to delete playlist. Ensure the Playlist ID **#{playlist_id}** exists.")

    # SHOW PLAYLIST SONGS
    @slash_command(name="songs", description="Displays the songs inside a specific playlist.")
    @option("playlist_id", int, description="The ID of the playlist to view", required=True)
    async def songs(self, ctx: discord.ApplicationContext, playlist_id: int):
        await ctx.defer()
        
        songs = await get_songs_in_playlist(playlist_id=playlist_id)
        
        if songs is None:
            return await ctx.respond(f"❌ Failed to fetch songs for Playlist **#{playlist_id}**.")
            
        if not songs:
            return await ctx.respond(f"⚠️ Playlist **#{playlist_id}** is currently empty or does not exist.")
            
        embeds = []
        chunk_size = 10 # Display 10 songs per page
        
        for i in range(0, len(songs), chunk_size):
            chunk = songs[i:i+chunk_size]
            
            embed = discord.Embed(title=f"🎶 Playlist #{playlist_id} Songs", color=discord.Color.purple())
            
            description = ""
            for song in chunk:
                song_id = song.get("song_id")
                title = song.get("song_title", "Unknown Title")
                url = song.get("song_link", "")
                
                description += f"**ID: {song_id}** - [{title}]({url})\n\n"
                
            embed.description = description
            embeds.append(embed)
            
        if len(embeds) == 1:
            await ctx.respond(embed=embeds[0])
        else:
            paginator = pages.Paginator(pages=embeds, show_disabled=True, show_indicator=True)
            await paginator.respond(ctx.interaction)

    # PLAY PLAYLIST
    @slash_command(name="playplaylist", description="Queues and plays all songs from a specific playlist.")
    @option("playlist_id", int, description="The ID of the playlist to play", required=True)
    async def playplaylist(self, ctx: discord.ApplicationContext, playlist_id: int):
        await ctx.defer()
        
        songs = await get_songs_in_playlist(playlist_id=playlist_id)
        
        if songs is None:
            return await ctx.respond(f"❌ Failed to fetch songs for Playlist **#{playlist_id}**.")
            
        if not songs:
            return await ctx.respond(f"⚠️ Playlist **#{playlist_id}** is currently empty or does not exist.")
            
        # User must be in a Voice Channel
        if not getattr(ctx.author, "voice", None):
            return await ctx.respond("[❌] You must be inside a voice channel to use this command!")
            
        user_voice_channel = ctx.author.voice.channel
        
        # Connect to VC if not already connected
        if ctx.voice_client is None:
            vc = await user_voice_channel.connect()
        else:
            vc = ctx.voice_client
            
        # Retrieve the Music cog to interact with its queue and methods
        music_cog = self.bot.get_cog("Music")
        if not music_cog:
            return await ctx.respond("[❌] The Music module is currently unavailable.")
            
        if ctx.guild.id not in music_cog.queues:
            music_cog.queues[ctx.guild.id] = []
            
        is_idle = not (vc.is_playing() or vc.is_paused())
        
        if is_idle:
            first_song = songs.pop(0)
            
            # Add the rest to the queue
            music_cog.queues[ctx.guild.id].extend([
                {'url': s.get("song_link"), 'title': s.get("song_title"), 'thumbnail': None}
                for s in songs
            ])
            
            await ctx.respond(f"✅ Queued **{len(songs) + 1}** songs from Playlist **#{playlist_id}**! Starting playback...")
            
            # Start playing the first song directly
            await music_cog.play_next_song(ctx, first_song.get("song_link"))
        else:
            # Just add all to the queue
            music_cog.queues[ctx.guild.id].extend([
                {'url': s.get("song_link"), 'title': s.get("song_title"), 'thumbnail': None}
                for s in songs
            ])
            
            await ctx.respond(f"✅ Added **{len(songs)}** songs from Playlist **#{playlist_id}** to the queue!")

def setup(bot):
    bot.add_cog(Playlist(bot))
