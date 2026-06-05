#!/usr/bin/env python3
"""
Register test accounts against snapcrest.app with proxy support.
"""

import random
import re
import string
import sys
import time

import requests
from requests.exceptions import RequestException, ProxyError, ConnectionError

# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------
NUM_ACCOUNTS = 10
BASE_URL     = "https://snapcrest.app"
REGISTER_PATH = "/auth/register"
DELAY_SECONDS = 2.0                     # Increased delay
SAVE_FILE = "created_accounts.txt"
FIXED_PASSWORD = "hello998"

# Your Nettify proxy
PROXY_STRING = "awny02gupdzj:i1ill526hww6@eu.nettify.xyz:8080"
PROXIES_LIST = [f"http://{PROXY_STRING}"]
PROXY_ROTATE_EVERY = 3
# ---------------------------------------------------------------------------

BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


def test_proxy(proxy_dict):
    """Quick test if proxy is working."""
    try:
        test_session = requests.Session()
        test_session.proxies.update(proxy_dict)
        r = test_session.get("https://httpbin.org/ip", timeout=15)
        return r.status_code == 200
    except Exception as e:
        print(f"   Proxy test failed: {type(e).__name__} - {e}")
        return False


def get_proxy_for_account(account_index: int):
    if not PROXIES_LIST:
        return None
    proxy_idx = (account_index // PROXY_ROTATE_EVERY) % len(PROXIES_LIST)
    proxy_url = PROXIES_LIST[proxy_idx]
    return {"http": proxy_url, "https": proxy_url}


def register_account(email, password, proxy_dict=None):
    session = requests.Session()
    session.headers.update(BROWSER_HEADERS)
    
    if proxy_dict:
        session.proxies.update(proxy_dict)

    try:
        page = session.get(BASE_URL + REGISTER_PATH, timeout=40)
    except RequestException as e:
        err_type = type(e).__name__
        return False, 0, f"GET failed [{err_type}]: {str(e)[:100]}"

    # Extract CSRF token
    m = re.search(r'csrf_token:\s*"([^"]+)"', page.text)
    if not m:
        return False, page.status_code, "CSRF token not found"

    csrf_token = m.group(1)

    try:
        resp = session.post(
            BASE_URL + REGISTER_PATH,
            data={"email": email, "password": password, "csrf_token": csrf_token},
            headers={
                "X-CSRFToken": csrf_token,
                "Referer": BASE_URL + REGISTER_PATH,
                "Origin": BASE_URL,
            },
            allow_redirects=False,
            timeout=40,
        )
    except RequestException as e:
        return False, 0, f"POST failed: {type(e).__name__} - {e}"

    location = resp.headers.get("Location", "")
    success = (resp.status_code in (301, 302) and "dashboard" in location.lower()) or (
        resp.status_code in (200, 201)
    )
    
    detail = f"-> {location}" if location else resp.text[:120].replace("\n", " ")
    return success, resp.status_code, detail


def main():
    n = NUM_ACCOUNTS
    if len(sys.argv) > 1:
        n = int(sys.argv[1])

    print(f"Using proxy: {PROXY_STRING}")
    print(f"Creating {n} account(s)...\n")

    # Test proxy first
    print("Testing proxy...")
    proxy_dict = get_proxy_for_account(0)
    if proxy_dict and not test_proxy(proxy_dict):
        print("⚠️  Proxy test failed! Continuing anyway...\n")

    created = []

    for i in range(1, n + 1):
        email = random_email()
        password = FIXED_PASSWORD if FIXED_PASSWORD else random_password()
        
        proxy_dict = get_proxy_for_account(i-1)
        ok, code, detail = register_account(email, password, proxy_dict)
        
        status = "✅ OK" if ok else "❌ FAIL"
        proxy_num = (i-1) // PROXY_ROTATE_EVERY
        print(f"[{i:>2}/{n}] {status} {code} (proxy {proxy_num}) {email} | {detail[:80]}")

        if ok:
            created.append((email, password))

        if i < n:
            time.sleep(DELAY_SECONDS)

    if created:
        with open(SAVE_FILE, "w") as f:
            f.write("email,password\n")
            for email, password in created:
                f.write(f"{email},{password}\n")
        print(f"\n✅ Saved {len(created)} accounts to {SAVE_FILE}")

    print(f"\nDone: {len(created)}/{n} succeeded.")


def random_email():
    name = "".join(random.choices(string.ascii_lowercase + string.digits, k=10))
    return f"test_{name}@example.com"


def random_password(length=14):
    upper = random.choice(string.ascii_uppercase)
    lower = random.choice(string.ascii_lowercase)
    digit = random.choice(string.digits)
    symbol = random.choice("!@#$%^&*")
    rest = random.choices(string.ascii_letters + string.digits, k=length - 4)
    pwd = list(upper + lower + digit + symbol) + rest
    random.shuffle(pwd)
    return "".join(pwd)


if __name__ == "__main__":
    main()