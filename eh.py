import cloudscraper
import random
import time
import os
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

# ========================= CONFIG =========================
URL = "https://api.web3forms.com/submit"
ACCESS_KEY = "460b8135-0bf3-4091-9e14-794027910920"

PROXIES_FILE = "proxies.txt"
BATCH_SIZE = 3                    # Send 3 at the same time
NUM_BATCHES = 30                  # Total number of batches (adjust)
# =========================================================

def load_proxies():
    if not os.path.exists(PROXIES_FILE):
        print("[-] proxies.txt not found!")
        return []
    with open(PROXIES_FILE, "r") as f:
        return [line.strip() for line in f if line.strip()]

def send_single(scraper, name, email, message):
    payload = {
        "access_key": ACCESS_KEY,
        "name": name,
        "email": email,
        "message": message,
        "subject": "Contact Form Submission"
    }

    try:
        r = scraper.post(URL, json=payload, timeout=20)
        timestamp = datetime.now().strftime("%H:%M:%S")
        if r.status_code == 200:
            print(f"[{timestamp}] ✅ SUCCESS | {email}")
            return True
        else:
            print(f"[{timestamp}] ❌ Failed ({r.status_code})")
            return False
    except Exception as e:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ Error: {e}")
        return False

if __name__ == "__main__":
    print("[*] Web3Forms Spammer - 3 Concurrent Requests per Proxy")
    proxies = load_proxies()
    if not proxies:
        print("No proxies!")
        exit()

    success = 0
    proxy_index = 0

    for batch in range(NUM_BATCHES):
        proxy_str = proxies[proxy_index % len(proxies)]
        
        # Create scraper for this proxy
        scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows'})
        scraper.proxies = {"http": f"http://{proxy_str}", "https": f"http://{proxy_str}"}

        print(f"\n{'='*75}")
        print(f"BATCH {batch+1}/{NUM_BATCHES} | Using Proxy: {proxy_str[:55]}...")
        print(f"{'='*75}")

        # Prepare 3 concurrent tasks
        with ThreadPoolExecutor(max_workers=BATCH_SIZE) as executor:
            futures = []
            for _ in range(BATCH_SIZE):
                name = f"User{random.randint(10000,999999)}"
                email = f"test{random.randint(100000000,999999999)}@gmail.com"
                message = "Automated concurrent test submission."

                future = executor.submit(send_single, scraper, name, email, message)
                futures.append(future)

            # Wait for all 3 to finish
            for future in as_completed(futures):
                if future.result():
                    success += 1

        proxy_index += 1
        time.sleep(random.uniform(4, 9))  # Delay before switching proxy

    print(f"\n[+] All done! Total Successful Submissions: {success}")