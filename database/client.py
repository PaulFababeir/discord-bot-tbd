import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

url: str = os.getenv("SUPABASE_URL")
key: str = os.getenv("SUPABASE_KEY")

# One clean, reusable client instance
if not url or not key:
    raise ValueError("Missing Supabase credentials in environment variables.")

supabase: Client = create_client(url, key)