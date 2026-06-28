from supabase import create_client
from dotenv import load_dotenv
import os

load_dotenv()

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

print("URL:", url)
print("KEY EXISTS:", bool(key))

supabase = create_client(url, key)

result = supabase.table("cameras").select("*").execute()

print(result.data)