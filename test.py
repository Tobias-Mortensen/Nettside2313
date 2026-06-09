import requests
import json
import os
import time

SUPABASE_URL = "https://guewgygcpcmrcoppihzx.supabase.co"
ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imd1ZXdneWdjcGNtcmNvcHBpaHp4Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzI2Njk2NTMsImV4cCI6MjA4ODI0NTY1M30.V5Jw7wJgiMpSQPa2mt0ftjyye5ynG1qLlam00yPVNJY"   # ← Paste real key

headers = {
    "apikey": ANON_KEY,
    "Authorization": f"Bearer {ANON_KEY}",
    "Content-Type": "application/json"
}

def probe():
    print("[*] Probing what the anon key can actually do...\n")
    
    # 1. Try to get schema / list tables
    print("1. Trying to list all tables...")
    r = requests.get(f"{SUPABASE_URL}/rest/v1/", headers=headers)
    print(f"   Status: {r.status_code}")
    
    # 2. Test common tables
    tables = ["users", "profiles", "projects", "api_keys", "conversations", "messages", 
              "credits", "subscriptions", "payments", "settings"]
    
    print("\n2. Testing readable tables:")
    readable = []
    for table in tables:
        r = requests.get(f"{SUPABASE_URL}/rest/v1/{table}?limit=3", headers=headers)
        status = r.status_code
        size = len(r.text)
        print(f"   {table:15} → {status} ({size} bytes)")
        if status == 200 and size > 10:
            try:
                data = r.json()
                if isinstance(data, list) and len(data) > 0:
                    readable.append((table, len(data)))
                    print(f"      → SUCCESS! Sample keys: {list(data[0].keys()) if data else None}")
            except:
                pass
        time.sleep(0.5)

    # 3. Auth endpoints
    print("\n3. Auth capabilities:")
    print("   Can create accounts: Likely YES")
    
    # 4. Save results
    result = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "readable_tables": readable,
        "tested_tables": tables
    }
    
    with open("anon_key_capabilities.json", "w") as f:
        json.dump(result, f, indent=2)
    
    print(f"\n[+] Probe finished. Results saved to anon_key_capabilities.json")

if __name__ == "__main__":
    probe()