import asyncio
import json
import signal
import sys
from pathlib import Path

try:
    from steam.client import SteamClient
    from steam.enums import EResult
except ImportError:
    print("Install steam package: pip install steam[client]")
    sys.exit(1)


CONFIG_FILE = Path("idler_config.json")

DEFAULT_CONFIG = {
    "accounts": [
        {
            "username": "",
            "password": "",
            "game_ids": [730],
        },
    ],
}


def load_config() -> dict:
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE) as f:
            return json.load(f)
    with open(CONFIG_FILE, "w") as f:
        json.dump(DEFAULT_CONFIG, f, indent=2)
    print(f"Created {CONFIG_FILE} — fill in your accounts and run again.")
    sys.exit(0)


class AccountIdler:
    def __init__(self, account: dict):
        self.account = account
        self.client = SteamClient()
        self.running = True
        self.tag = account["username"] or "unknown"
        self.connected = False

        self.client.on("logged_on", self._on_logged_on)
        self.client.on("disconnected", self._on_disconnected)
        self.client.on("error", self._on_error)

    def log(self, msg: str):
        print(f"[{self.tag}] {msg}")

    def _on_logged_on(self):
        self.connected = True
        self.log("Logged on")
        game_ids = self.account["game_ids"]
        self.log(f"Idling {len(game_ids)} game(s): {game_ids}")
        self.client.games_played(game_ids)

    def _on_disconnected(self):
        self.connected = False
        self.log("Disconnected")

    def _on_error(self, result):
        self.log(f"Error: {result}")

    async def run(self):
        username = self.account["username"]
        password = self.account["password"]

        if not username or not password:
            self.log("Missing credentials — skipping.")
            return

        self.log("Logging in...")
        result = self.client.cli_login(username, password)

        if result != EResult.OK:
            self.log(f"Login failed: {result}")
            return

        self.log("Idling...")

        while self.running:
            try:
                await asyncio.sleep(5)
                self.client.sleep(0)

                # reconnect if dropped
                if not self.client.connected and self.running:
                    self.log("Connection lost, reconnecting...")
                    await asyncio.sleep(10)
                    result = self.client.cli_login(username, password)
                    if result == EResult.OK:
                        self.log("Reconnected.")
                    else:
                        self.log(f"Reconnect failed: {result}")
                        await asyncio.sleep(30)

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.log(f"Error in idle loop: {e}")
                await asyncio.sleep(10)

        self.shutdown()

    def shutdown(self):
        self.log("Shutting down...")
        try:
            self.client.games_played([])
            self.client.logout()
        except Exception:
            pass

    def stop(self):
        self.running = False


async def main():
    config = load_config()
    accounts = config.get("accounts", [])

    if not accounts:
        print("[!] No accounts in config.")
        return

    print(f"[*] Starting {len(accounts)} account(s)...\n")

    idlers = [AccountIdler(acc) for acc in accounts]

    loop = asyncio.get_event_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, lambda: [i.stop() for i in idlers])
        except NotImplementedError:
            pass

    await asyncio.gather(*(idler.run() for idler in idlers))
    print("\n[*] All accounts stopped.")


if __name__ == "__main__":
    asyncio.run(main())
