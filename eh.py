import requests
import random
import time
import os
from datetime import datetime

# ========================= CONFIG =========================
URL = "https://api.web3forms.com/submit"
ACCESS_KEY = "460b8135-0bf3-4091-9e14-794027910920"

PROXIES_FILE = "proxies.txt"
BATCH_SIZE = 3                    # Send 3 requests per proxy
NUM_BATCHES = 10                  # Total batches (adjust as needed)

RANDOMIZE = True                  # Randomize name/email/message
# =========================================================

def load_proxies():
    if not os.path.exists(PROXIES_FILE):
        print("[-] proxies.txt not found!")
        return []
    with open(PROXIES_FILE, "r", encoding="utf-8") as f:
        proxies = [line.strip() for line in f if line.strip() and not line.startswith("#")]
    print(f"[+] Loaded {len(proxies)} proxies")
    return proxies

def get_proxy_dict(proxy_str):
    """Convert proxy string to requests format"""
    return {
        "http": f"http://{proxy_str}",
        "https": f"http://{proxy_str}"
    }

def send_request(proxy_dict, name, email, message):
    payload = {
        "access_key": ACCESS_KEY,
        "name": name,
        "email": email,
        "message": message,
        "subject": "New Contact Form Submission"
    }

    try:
        r = requests.post(URL, json=payload, proxies=proxy_dict, timeout=20)
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        if r.status_code == 200:
            print(f"[{timestamp}] ✅ SUCCESS | {email}")
            return True
        else:
            print(f"[{timestamp}] ❌ Failed ({r.status_code}) | {r.text[:100]}")
            return False
    except Exception as e:
        print(f"[{timestamp}] ❌ Error: {e}")
        return False


if __name__ == "__main__":
    print("[*] Web3Forms Spammer - 3 per Proxy Rotation")
    proxies = load_proxies()
    
    if not proxies:
        print("No proxies available. Exiting.")
        exit()

    success_count = 0
    proxy_index = 0

    for batch in range(NUM_BATCHES):
        proxy_str = proxies[proxy_index % len(proxies)]
        proxy_dict = get_proxy_dict(proxy_str)
        
        print(f"\n{'='*60}")
        print(f"BATCH {batch+1} | Using Proxy: {proxy_str[:50]}...")
        print(f"{'='*60}")

        for i in range(BATCH_SIZE):
            if RANDOMIZE:
                name = f"User{random.randint(1000,999999)}"
                email = f"test{random.randint(100000,999999999)}@gmail.com"
                message = random.choice(["Hello there", "Test message", "Hi", "Working good?", "Spam test 123"])
            else:
                name = "vczxxc"
                email = "cxfebzcxz@gmail.com"
                message = "hi"

            if send_request(proxy_dict, name, email, message):
                success_count += 1

            time.sleep(random.uniform(1.5, 4))  # Small delay between requests in same batch

        proxy_index += 1  # Rotate proxy after 3 requests
        time.sleep(random.uniform(3, 8))  # Delay before next batch

    print(f"\n[+] Finished! Total Successful: {success_count}/{NUM_BATCHES * BATCH_SIZE}")