import asyncio
import json
import os
import signal
import sys
from pathlib import Path

try:
    from steam.client import Client
    from steam.enums import EResult
except ImportError:
    print("Install steam package: pip install steam[client]")
    sys.exit(1)


CONFIG_FILE = Path("idler_config.json")

DEFAULT_CONFIG = {
    "username": "",
    "password": "",
    "game_ids": [730, 570, 440],  # CS2, Dota 2, TF2
    "reconnect_delay": 30,
    "status_message": "",
}


def load_config() -> dict:
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE) as f:
            return json.load(f)
    with open(CONFIG_FILE, "w") as f:
        json.dump(DEFAULT_CONFIG, f, indent=2)
    print(f"Created {CONFIG_FILE} — fill in your credentials and run again.")
    sys.exit(0)


class SteamIdler:
    def __init__(self, config: dict):
        self.config = config
        self.client = Client()
        self.running = True

        self.client.on("logged_on", self._on_logged_on)
        self.client.on("disconnected", self._on_disconnected)
        self.client.on("error", self._on_error)

    def _on_logged_on(self):
        username = self.client.user.name or self.config["username"]
        print(f"[+] Logged in as {username}")
        game_ids = self.config["game_ids"]
        print(f"[+] Idling {len(game_ids)} game(s): {game_ids}")
        self.client.games_played(game_ids)

    def _on_disconnected(self):
        print("[!] Disconnected from Steam")

    def _on_error(self, result):
        print(f"[!] Error: {result}")
        if result == EResult.InvalidPassword:
            print("[!] Invalid credentials. Check your config.")
            self.running = False
        elif result == EResult.RateLimitExceeded:
            print("[!] Rate limited. Waiting longer before retry...")

    async def run(self):
        username = self.config["username"]
        password = self.config["password"]

        if not username or not password:
            print("[!] Set username and password in config.")
            return

        while self.running:
            print(f"[*] Logging in as {username}...")
            result = self.client.login(username, password)

            if result == EResult.OK:
                print("[+] Connected. Idling... (Ctrl+C to stop)")
                try:
                    while self.running and self.client.connected:
                        await asyncio.sleep(1)
                        self.client.sleep(0)  # pump callbacks
                except asyncio.CancelledError:
                    break
            elif result == EResult.TwoFactorCodeRequired:
                code = input("[?] Enter Steam Guard Mobile code: ")
                result = self.client.login(username, password, two_factor_code=code)
                if result == EResult.OK:
                    print("[+] Connected with 2FA. Idling...")
                    try:
                        while self.running and self.client.connected:
                            await asyncio.sleep(1)
                            self.client.sleep(0)
                    except asyncio.CancelledError:
                        break
                else:
                    print(f"[!] 2FA login failed: {result}")
            elif result == EResult.AccountLoginDeniedNeedTwoFactor:
                code = input("[?] Enter email auth code: ")
                result = self.client.login(username, password, auth_code=code)
                if result == EResult.OK:
                    print("[+] Connected with email code. Idling...")
                    try:
                        while self.running and self.client.connected:
                            await asyncio.sleep(1)
                            self.client.sleep(0)
                    except asyncio.CancelledError:
                        break
                else:
                    print(f"[!] Email auth login failed: {result}")
            else:
                print(f"[!] Login failed: {result}")

            if not self.running:
                break

            delay = self.config["reconnect_delay"]
            print(f"[*] Reconnecting in {delay}s...")
            try:
                await asyncio.sleep(delay)
            except asyncio.CancelledError:
                break

        self.shutdown()

    def shutdown(self):
        print("[*] Shutting down...")
        try:
            self.client.games_played([])
            self.client.logout()
        except Exception:
            pass
        print("[*] Done.")


async def main():
    config = load_config()
    idler = SteamIdler(config)

    loop = asyncio.get_event_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, lambda: setattr(idler, "running", False))
        except NotImplementedError:
            pass  # windows

    await idler.run()


if __name__ == "__main__":
    asyncio.run(main())
