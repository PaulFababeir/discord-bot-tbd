A Discord music bot with playlists and a global leaderboard, built on Pycord and yt-dlp.

<p>
  <img src="https://img.shields.io/badge/Python-3.12-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python 3.12">
  <img src="https://img.shields.io/badge/Pycord-2.8-5865F2?style=for-the-badge&logo=discord&logoColor=white" alt="Pycord 2.8">
  <img src="https://img.shields.io/badge/Supabase-3FCF8E?style=for-the-badge&logo=supabase&logoColor=white" alt="Supabase">
  <img src="https://img.shields.io/badge/yt--dlp-FF0000?style=for-the-badge&logo=youtube&logoColor=white" alt="yt-dlp">
  <img src="https://img.shields.io/badge/FFmpeg-007808?style=for-the-badge&logo=ffmpeg&logoColor=white" alt="FFmpeg">
</p>

## Features

### 🎵 Music
- Play audio from a YouTube link, search query, or Spotify track link (auto-resolved to a matching YouTube source)
- Queue system with add, view (paginated), and remove-by-index
- Pause / resume / skip
- Interactive "Now Playing" message with buttons (⏯️ pause-resume, ⏭️ skip, 🔄 refresh) and a live progress bar

### 🗂️ Playlists
- Create and delete custom playlists
- Add or remove songs from a playlist
- View all playlists (globally or per user) and the songs inside one
- Queue an entire playlist in one command

### 🏆 Leaderboard
- Tracks how many times each song has been played, backed by Supabase
- `/topsongs` shows the 10 most-played tracks server-wide

### ⚙️ General & Info
- Auto-generated `/commands` list, grouped by category
- `/info` shows bot stats: server count, user count, latency, Python/Pycord version

## Commands

| Command | Description |
|---|---|
| `/play <query>` | Play a link/search/Spotify link, or add it to the queue |
| `/queue` | Show the current queue |
| `/nowplaying` | Show the current track with progress and controls |
| `/pause` / `/resume` | Pause or resume playback |
| `/skip` | Skip the current track |
| `/remove <index>` | Remove a song from the queue |
| `/clearqueue` | Clear the entire queue |
| `/disconnect` | Leave the voice channel |
| `/createplaylist <name>` | Create a new playlist |
| `/showplaylists [user]` | List playlists (all or by user) |
| `/songs <playlist_id>` | List songs in a playlist |
| `/addsong <playlist_id> <query>` | Add a song to a playlist |
| `/removesong <song_id>` | Remove a song from a playlist |
| `/clearplaylist <playlist_id>` | Remove all songs from a playlist |
| `/deleteplaylist <playlist_id>` | Delete an empty playlist |
| `/playplaylist <playlist_id>` | Queue/play an entire playlist |
| `/topsongs` | Show the top 10 most-played songs globally |
| `/info` | Bot stats and info |
| `/commands` | List all available commands |
| `/hello`, `/hi` | Say hi to the bot |

## Tech Stack

- **[Pycord](https://pycord.dev/)** — Discord API wrapper (slash commands, voice)
- **[yt-dlp](https://github.com/yt-dlp/yt-dlp)** — audio extraction from YouTube/search queries
- **FFmpeg** — audio streaming/transcoding
- **[Supabase](https://supabase.com/)** — Postgres database for playlists and the play-count leaderboard
- **aiohttp** — Spotify oEmbed lookups for link resolution

## Setup

### Prerequisites
- Python 3.12+
- [FFmpeg](https://ffmpeg.org/download.html) installed and available on your `PATH`
- A Discord bot application and token ([Discord Developer Portal](https://discord.com/developers/applications))
- A [Supabase](https://supabase.com/) project (URL + API key)

### Installation

```bash
# Clone the repo
git clone <repo-url>
cd discord-bot-tbd

# Create and activate a virtual environment
python -m venv venv
venv\Scripts\activate      # Windows
source venv/bin/activate   # macOS/Linux

# Install dependencies
pip install -r requirements.txt
```

### Configuration

Create a `.env` file in the project root:

```env
TOKEN=your_discord_bot_token
GUILD_ID=your_test_guild_id      # optional, comma-separated for multiple guilds
SUPABASE_URL=your_supabase_project_url
SUPABASE_KEY=your_supabase_api_key
```

Leaving `GUILD_ID` unset makes slash commands sync globally instead of instantly to a test server.

### Database

Run [`database/schema.sql`](database/schema.sql) in your Supabase project's **SQL Editor** to create the three required tables (`playlist`, `songs`, `song_leaderboard`) with the correct types, primary keys, and foreign key.

Note: Supabase free-tier projects auto-pause after a period of inactivity — if the bot's DB-backed commands (`/topsongs`, playlist commands) suddenly stop working, check your project's dashboard for a paused state before assuming it's a code issue.

### Run

```bash
python main.py
```

## Project Structure

```
├── main.py               # Bot entrypoint, loads cogs
├── cogs/
│   ├── general.py        # /hello, /hi, /commands
│   ├── info.py            # /info
│   ├── music.py           # Playback and queue
│   ├── playlist.py        # Custom playlists
│   └── leaderboard.py     # /topsongs
└── database/
    ├── client.py          # Supabase client
    └── manager.py          # Database queries
```