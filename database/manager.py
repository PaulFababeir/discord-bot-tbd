from .client import supabase

async def track_song_play(video_id: str, title: str) -> None:
    """Increments the play count of a song using an upsert flow."""
    try:
        # Check if the song is already tracked
        response = supabase.table("song_leaderboard").select("play_count").eq("video_id", video_id).execute()
        
        if response.data:
            # Update existing row
            new_count = response.data[0]['play_count'] + 1
            supabase.table("song_leaderboard").update({
                "play_count": new_count, 
                "title": title
            }).eq("video_id", video_id).execute()
        else:
            # Insert new track row
            supabase.table("song_leaderboard").insert({
                "video_id": video_id, 
                "title": title, 
                "play_count": 1
            }).execute()
            
    except Exception as e:
        print(f"[DB ERROR] Error syncing stats for {video_id}: {e}")

async def get_top_songs(limit: int = 10):
    """Fetches the most popular songs globally for your leaderboard command."""
    response = supabase.table("song_leaderboard").select("*").order("play_count", desc=True).limit(limit).execute()
    return response.data