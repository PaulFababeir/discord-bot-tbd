from .client import supabase
from datetime import datetime, timezone

async def track_song_play(video_id: str, title: str) -> None:
    """Increments the play count of a song using an upsert flow."""
    try:
        # Defensively slice the ID to 15 chars to strictly match your VARCHAR(15) schema
        safe_video_id = video_id[:15]

        # Check if the song is already tracked
        response = supabase.table("song_leaderboard").select("play_count").eq("video_id", safe_video_id).execute()
        
        if response.data:
            # Update existing row
            new_count = response.data[0]['play_count'] + 1
            supabase.table("song_leaderboard").update({
                "play_count": new_count, 
                "title": title,
                "updated_at": datetime.now(timezone.utc).isoformat() # Manually trigger updated_at for updates
            }).eq("video_id", safe_video_id).execute()
        else:
            # Insert new track row
            supabase.table("song_leaderboard").insert({
                "video_id": safe_video_id, 
                "title": title, 
                "play_count": 1
                # updated_at defaults to NOW() automatically from your schema
            }).execute()
            
    except Exception as e:
        print(f"[DB ERROR] Error syncing stats for {video_id}: {e}")

async def get_top_songs(limit: int = 10):
    """Fetches the most popular songs globally for your leaderboard command."""
    response = supabase.table("song_leaderboard").select("*").order("play_count", desc=True).limit(limit).execute()
    return response.data

async def create_playlist(name: str, owner_id: int):
    """Creates a new playlist for a user."""
    try:
        response = supabase.table("playlist").insert({
            "playlist_name": name,
            "owner_id": owner_id
        }).execute()
        return response.data
    except Exception as e:
        print(f"[DB ERROR] Error creating playlist '{name}' for {owner_id}: {e}")
        return None