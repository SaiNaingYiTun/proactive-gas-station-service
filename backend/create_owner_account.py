import getpass
import sys

from dotenv import load_dotenv
from supabase import create_client
import os

from auth import hash_password

load_dotenv()


def main():
    supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_ROLE_KEY"))

    existing = supabase.table("staff_accounts").select("id").eq("is_owner", True).limit(1).execute().data
    if existing:
        print("An owner account already exists. Refusing to create a second one.")
        print("To replace it, edit or delete that row in Supabase directly, then re-run this.")
        sys.exit(1)

    print("Creating the owner account for the staff dashboard.")
    username = input("Owner username: ").strip()
    if not username:
        print("Username cannot be empty.")
        sys.exit(1)
    display_name = input("Owner display name [Owner]: ").strip() or "Owner"
    password = getpass.getpass("Owner password: ")
    confirm = getpass.getpass("Confirm password: ")
    if password != confirm:
        print("Passwords did not match.")
        sys.exit(1)
    if len(password) < 8:
        print("Use at least 8 characters.")
        sys.exit(1)

    supabase.table("staff_accounts").insert({
        "username": username,
        "password_hash": hash_password(password),
        "display_name": display_name,
        "is_owner": True,
    }).execute()
    print(f"Owner account '{username}' created. Log in at the dashboard's /login page.")


if __name__ == "__main__":
    main()
