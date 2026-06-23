from fastapi import FastAPI
from supabase import create_client
from  dotenv import load_dotenv
import os

load_dotenv()


app = FastAPI()

supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        
)

@app.get("/")
def root():
    return {"message": "Backend running"}