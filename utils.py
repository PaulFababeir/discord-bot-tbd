"""Shared helpers used by multiple cogs (music.py, playlist.py, leaderboard.py)."""
import re
import aiohttp

# Configurations for yt-dlp to extract the stream link safely
YTDL_OPTIONS = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'quiet': True,
    'no_warnings': True,
    'source_address': '0.0.0.0', # Forces IPv4 to prevent connection timeouts
    # Restricts extraction to known music sources; blocks yt-dlp's generic
    # extractor from fetching arbitrary user-supplied URLs (SSRF risk)
    'allowed_extractors': ['youtube.*', 'soundcloud.*', 'bandcamp.*']
}

# Advanced FFmpeg arguments that ensure a smooth network stream
FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn' # Processes audio only, ignoring the heavy video channel
}


def clean_song_title(title: str) -> str:
    """Removes common YouTube video tags like (Official Video) or [Lyric Video]."""
    title = re.sub(r'(?i)\s*[\[(][^\])]*(?:official|music|lyric|audio|video|visualizer|mv|live|hd|hq|4k)[^\])]*[\])]', '', title)
    # Also remove common unbracketed tags at the end of the title
    title = re.sub(r'(?i)\s*(?:[-|]\s*)?\b(?:official\s+(?:music\s+|lyric\s+)?video|official\s+audio|lyric\s+video|music\s+video|visualizer|audio)\b.*$', '', title)
    return re.sub(r'\s*[-|]\s*$', '', title).strip()


class SpotifyResolutionError(Exception):
    """Raised when a Spotify link can't be resolved to a playable query."""


async def resolve_query(query: str) -> str:
    """Transforms a raw user query into something yt-dlp can search/extract from.

    Spotify links are resolved via oEmbed into an equivalent YouTube search
    query, since yt-dlp can't stream directly from Spotify. Plain text
    (no URL) is turned into a YouTube search query.
    """
    if "spotify.com" in query:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"https://open.spotify.com/oembed?url={query}") as resp:
                    if resp.status != 200:
                        print(f"[Spotify Error] Status {resp.status} for {query}")
                        raise SpotifyResolutionError(
                            "[❌] Could not extract track info from that Spotify link. The link may be private or invalid."
                        )

                    data = await resp.json()
                    title = data.get('title', 'Unknown Title')
                    author = data.get('author_name', '')

                    # Fallback if Spotify's oEmbed API omits the author name
                    if not author:
                        async with session.get(query) as html_resp:
                            if html_resp.status == 200:
                                html = await html_resp.text()
                                match = re.search(r'<title>(.*?)</title>', html, re.IGNORECASE)
                                if match:
                                    # Grabs e.g., "Song - song and lyrics by Artist | Spotify"
                                    title = match.group(1).replace(" | Spotify", "")

                    return f"ytsearch1:{title} {author} audio".strip()
        except SpotifyResolutionError:
            raise
        except Exception as e:
            print(f"[Spotify Error] An exception occurred: {e}")
            raise SpotifyResolutionError("[❌] An error occurred while trying to process that Spotify link.")

    if not query.startswith(('http://', 'https://')):
        return f"ytsearch1:{query}"

    return query
