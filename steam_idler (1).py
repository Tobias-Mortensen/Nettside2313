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

ACCOUNTS_FILE = Path("accounts.json")
GAME_IDS = [730]

def load_accounts():
    if ACCOUNTS_FILE.exists():
        with open(ACCOUNTS_FILE) as f:
            return json.load(f)
    print("No accounts.json found.")
    sys.exit(1)

class AccountIdler:
    def __init__(self, account):
        self.account = account
        self.client = SteamClient()
        self.running = True
        self.tag = account["username"]
        self.client.on("logged_on", self._on_logged_on)
        self.client.on("disconnected", self._on_disconnected)
        self.client.on("error", self._on_error)

    def log(self, msg):
        print(f"[{self.tag}] {msg}")

    def _on_logged_on(self):
        self.log("Logged on")
        self.client.games_played(GAME_IDS)

    def _on_disconnected(self):
        self.log("Disconnected")

    def _on_error(self, result):
        self.log(f"Error: {result}")

    async def run(self):
        u = self.account["username"]
        p = self.account["password"]
        if not u or not p:
            self.log("Missing credentials, skipping.")
            return
        self.log("Logging in...")
        result = self.client.cli_login(u, p)
        if result != EResult.OK:
            self.log(f"Login failed: {result}")
            return
        self.log("Idling...")
        while self.running:
            try:
                await asyncio.sleep(5)
                self.client.sleep(0)
                if not self.client.connected and self.running:
                    self.log("Reconnecting...")
                    await asyncio.sleep(10)
                    result = self.client.cli_login(u, p)
                    if result == EResult.OK:
                        self.log("Reconnected.")
                    else:
                        self.log(f"Reconnect failed: {result}")
                        await asyncio.sleep(30)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.log(f"Error: {e}")
                await asyncio.sleep(10)
        self.shutdown()

    def shutdown(self):
        try:
            self.client.games_played([])
            self.client.logout()
        except:
            pass

    def stop(self):
        self.running = False

async def main():
    accounts = load_accounts()
    valid = [a for a in accounts if a.get("username") and a.get("password")]
    print(f"Starting {len(valid)} account(s)...\n")
    idlers = [AccountIdler(a) for a in valid]
    loop = asyncio.get_event_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, lambda: [i.stop() for i in idlers])
        except NotImplementedError:
            pass
    await asyncio.gather(*(i.run() for i in idlers))
    print("\nAll accounts stopped.")

if __name__ == "__main__":
    asyncio.run(main())
