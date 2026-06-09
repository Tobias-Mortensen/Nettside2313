import requests
import random
import time
import os
from datetime import datetime

# ========================= CONFIG =========================
URL = "https://api.web3forms.com/submit"

ACCESS_KEY = "460b8135-0bf3-4091-9e14-794027910920"

PROXIES_FILE = "proxies.txt"
NUM_REQUESTS = 10                    # How many times to send

# Optional: Randomize data
RANDOMIZE = True
# =========================================================

def load_proxies():
    if not os.path.exists(PROXIES_FILE):
        print("[-] proxies.txt not found. Running without proxies.")
        return [None]
    with open(PROXIES_FILE, "r", encoding="utf-8") as f:
        proxies = [line.strip() for line in f if line.strip() and not line.startswith("#")]
    print(f"[+] Loaded {len(proxies)} proxies")
    return proxies

def get_random_proxy(proxies):
    if not proxies or proxies == [None]:
        return None
    proxy = random.choice(proxies)
    return {"http": f"http://{proxy}", "https": f"http://{proxy}"}

def send_form(proxy_dict=None):
    if RANDOMIZE:
        name = f"User{random.randint(1000,999999)}"
        email = f"test{random.randint(10000,999999)}@gmail.com"
        message = random.choice(["Hello", "Test message", "Hi there", "Working?", "Spam test"])
    else:
        name = "vczxxc"
        email = "cxfebzcxz@gmail.com"
        message = "hi"

    payload = {
        "access_key": ACCESS_KEY,
        "name": name,
        "email": email,
        "message": message,
        "subject": "New Contact Form Submission"
    }

    try:
        r = requests.post(URL, json=payload, proxies=proxy_dict, timeout=15)
        
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        if r.status_code == 200:
            print(f"[{timestamp}] ✅ SUCCESS | {email} | {r.json().get('message', 'OK')}")
            return True
        else:
            print(f"[{timestamp}] ❌ Failed ({r.status_code}) | {r.text[:150]}")
            return False

    except Exception as e:
        print(f"[{timestamp}] ❌ Error: {e}")
        return False


if __name__ == "__main__":
    print("[*] Web3Forms Submitter Started")
    proxies = load_proxies()

    success = 0
    for i in range(NUM_REQUESTS):
        print(f"\n--- Request {i+1}/{NUM_REQUESTS} ---")
        proxy_dict = get_random_proxy(proxies)
        if proxy_dict:
            print(f"   Using proxy: {list(proxy_dict.values())[0]}")
        
        if send_form(proxy_dict):
            success += 1
        
        time.sleep(random.uniform(2, 6))  # Be respectful / avoid rate limits

    print(f"\n[+] Finished! Success: {success}/{NUM_REQUESTS}")