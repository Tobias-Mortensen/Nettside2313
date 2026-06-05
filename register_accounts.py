#!/usr/bin/env python3
"""
Register test accounts against snapcrest.app.

Mirrors the browser signup flow:
  1. GET  /auth/register   -> obtain the session cookie
  2. POST /auth/register   -> submit email + password (form-urlencoded)

A 302 redirect to /dashboard is treated as success.
"""

import random
import string
import sys
import time

import requests

# ---------------------------------------------------------------------------
# CONFIG -- change these
# ---------------------------------------------------------------------------
NUM_ACCOUNTS = 10                       # how many accounts to create
BASE_URL     = "https://snapcrest.app"
REGISTER_PATH = "/auth/register"
DELAY_SECONDS = 1.0                     # pause between accounts (avoid rate limits)
SAVE_FILE = "created_accounts.txt"      # where to log created credentials
# ---------------------------------------------------------------------------

BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


def random_email():
    name = "".join(random.choices(string.ascii_lowercase + string.digits, k=10))
    return f"test_{name}@example.com"


def random_password(length=14):
    # Ensure at least one upper, lower, digit, and symbol
    upper  = random.choice(string.ascii_uppercase)
    lower  = random.choice(string.ascii_lowercase)
    digit  = random.choice(string.digits)
    symbol = random.choice("!@#$%^&*")
    rest   = random.choices(string.ascii_letters + string.digits, k=length - 4)
    pwd    = list(upper + lower + digit + symbol) + rest
    random.shuffle(pwd)
    return "".join(pwd)


def register_account(email, password):
    """Returns (success: bool, status_code: int, detail: str)."""
    session = requests.Session()
    session.headers.update(BROWSER_HEADERS)

    # 1. GET the register page to pick up the session cookie / any CSRF state
    try:
        session.get(BASE_URL + REGISTER_PATH, timeout=30)
    except requests.RequestException as e:
        return False, 0, f"GET failed: {e}"

    # 2. POST the credentials. Don't auto-follow the redirect so we can see the 302.
    try:
        resp = session.post(
            BASE_URL + REGISTER_PATH,
            data={"email": email, "password": password},
            allow_redirects=False,
            timeout=30,
        )
    except requests.RequestException as e:
        return False, 0, f"POST failed: {e}"

    location = resp.headers.get("Location", "")
    # 302 -> /dashboard means success; a 2xx might too depending on the app.
    success = (resp.status_code in (301, 302) and "dashboard" in location) or (
        resp.status_code in (200, 201)
    )
    detail = f"-> {location}" if location else resp.text[:120].replace("\n", " ")
    return success, resp.status_code, detail


def main():
    n = NUM_ACCOUNTS
    if len(sys.argv) > 1:                # optional override: python register_accounts.py 5
        n = int(sys.argv[1])

    print(f"Creating {n} account(s) against {BASE_URL}{REGISTER_PATH}\n")
    created = []

    for i in range(1, n + 1):
        email = random_email()
        password = random_password()
        ok, code, detail = register_account(email, password)
        status = "OK " if ok else "FAIL"
        print(f"[{i:>2}/{n}] {status} {code}  {email}  {detail}")
        if ok:
            created.append((email, password))
        if i < n:
            time.sleep(DELAY_SECONDS)

    if created:
        with open(SAVE_FILE, "w") as f:
            f.write("email,password\n")
            for email, password in created:
                f.write(f"{email},{password}\n")
        print(f"\nSaved {len(created)} credential pair(s) to {SAVE_FILE}")

    print(f"\nDone: {len(created)}/{n} succeeded.")


if __name__ == "__main__":
    main()
