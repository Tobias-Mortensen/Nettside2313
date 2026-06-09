import requests
import json
import os
import time
import random
from datetime import datetime

# ========================= CONFIG =========================
SUPABASE_URL = "https://guewgygcpcmrcoppihzx.supabase.co"
ANON_KEY = "YOUR_ANON_KEY_HERE"   # ← Make sure this is correct

USE_PROXIES = False
PROXIES_FILE = "proxies.txt"
DUMP_FOLDER = "supabase_dump_v2"
# =========================================================

headers = {
    "apikey": ANON_KEY,
    "Authorization": f"Bearer {ANON_KEY}",
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

def get_request(url, params=None):
    proxy = None
    if USE_PROXIES:
        # load proxy logic here if needed
        pass
    
    try:
        r = requests.get(url, headers=headers, params=params, timeout=20)
        print(f"    Status: {r.status_code} | Size: {len(r.text)} bytes")
        if r.status_code != 200:
            print(f"    Response: {r.text[:500]}")
        return r
    except Exception as e:
        print(f"    Request error: {e}")
        return None

def dump_table(table_name):
    print(f"[*] Dumping table: {table_name}")
    all_data = []
    limit = 500   # Smaller limit to avoid restrictions
    offset = 0
    max_attempts = 10

    for attempt in range(max_attempts):
        params = {
            "select": "*",
            "limit": limit,
            "offset": offset
        }
        
        resp = get_request(f"{SUPABASE_URL}/rest/v1/{table_name}", params=params)
        
        if not resp:
            break
        if resp.status_code != 200:
            print(f"    [-] Failed after {attempt+1} attempts")
            break
        
        data = resp.json()
        if not isinstance(data, list):
            print(f"    [-] Unexpected response format")
            break
            
        all_data.extend(data)
        print(f"    → Fetched {len(data)} rows (Total: {len(all_data)})")
        
        if len(data) < limit:
            break
            
        offset += limit
        time.sleep(0.8)

    return all_data

def main():
    os.makedirs(DUMP_FOLDER, exist_ok=True)
    print(f"[*] Starting Improved Supabase Dump → {DUMP_FOLDER}/")

    # Tables we know exist
    tables = ["projects", "api_keys"]

    summary = {
        "dumped_at": datetime.now().isoformat(),
        "tables": {}
    }

    for table in tables:
        data = dump_table(table)
        if data:
            filepath = os.path.join(DUMP_FOLDER, f"{table}.json")
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            summary["tables"][table] = len(data)
            print(f"[+] Successfully saved {len(data)} rows from {table}\n")
        else:
            print(f"[-] No data retrieved from {table}\n")
        time.sleep(1)

    with open(os.path.join(DUMP_FOLDER, "SUMMARY.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print(f"\n[+] Dump finished! Check folder: {DUMP_FOLDER}/")

if __name__ == "__main__":
    main()