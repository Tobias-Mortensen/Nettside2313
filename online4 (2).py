"""
Discord Online Tool
===================
Keeps all tokens online simultaneously via Discord gateway.
Custom status is read from status.txt and rotated every 3 seconds.

INSTALL:
    pip install aiohttp colorama
"""

import os, sys, glob, subprocess

def _find_python():
    candidates = [sys.executable]
    try: user = os.getlogin()
    except: user = os.environ.get("USERNAME", "User")
    for pat in [
        rf"C:\Users\{user}\AppData\Local\Programs\Python\Python*\python.exe",
        r"C:\Python*\python.exe",
        r"C:\Program Files\Python*\python.exe",
    ]:
        for p in glob.glob(pat, recursive=True):
            if p not in candidates and os.path.isfile(p):
                candidates.append(p)
    for ver in ["3.13","3.12","3.11","3.10","3.9"]:
        try:
            r = subprocess.run(["py",f"-{ver}","-c","import sys;print(sys.executable)"],
                               capture_output=True, text=True, timeout=3)
            if r.returncode == 0:
                p = r.stdout.strip()
                if p and p not in candidates: candidates.append(p)
        except: pass
    for py in candidates:
        try:
            r = subprocess.run([py,"-c","import aiohttp,colorama;print('ok')"],
                               capture_output=True, text=True, timeout=5)
            if r.returncode == 0 and "ok" in r.stdout: return py
        except: pass
    return None

try:
    import aiohttp
    from colorama import init, Fore, Style, Back
except ImportError:
    py = _find_python()
    if py and py != sys.executable:
        os.execv(py, [py] + sys.argv)
    else:
        print("Run: pip install aiohttp colorama")
        sys.exit(1)

import asyncio, json, time, threading, random

init(autoreset=True)

SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))
TOKENS_FILE = os.path.join(SCRIPT_DIR, "tokens.txt")
STATUS_FILE = os.path.join(SCRIPT_DIR, "status.txt")
GATEWAY     = "wss://gateway.discord.gg/?v=10&encoding=json"

STATUS_ROTATE_INTERVAL = 20  # seconds per status line
STATUS_EMOJI           = "💵"  # Discord :dollar: emoji

# Fake game activity
GAME_NAME        = "Exchanging on Cypto2cash.wtf"
GAME_APP_ID       = "1488138632148811807"
GAME_ASSET_KEY    = "crypto"
GAME_BUTTON_TEXT  = "Exchange now!"

STATUS        = "online"   # online / idle / dnd / invisible
CUSTOM_STATUS = ""

accounts       = {}
ws_connections = {}
lock           = threading.Lock()
running        = True
ui_paused      = False


GAME_START_TIME = None  # set at startup

def build_presence(status: str, custom_text: str = ""):
    activities = []

    # Custom status (type 4)
    if custom_text:
        activities.append({
            "type": 4,
            "name": "Custom Status",
            "state": custom_text,
            "id": "custom",
            "emoji": {"name": STATUS_EMOJI},
        })

    # Fake game activity (type 0)
    game = {
        "type": 0,
        "name": GAME_NAME,
        "application_id": GAME_APP_ID,
        "assets": {
            "large_image": GAME_ASSET_KEY,
            "large_text":  GAME_NAME,
        },
        "buttons": [GAME_BUTTON_TEXT],
    }
    if GAME_START_TIME:
        game["timestamps"] = {"start": GAME_START_TIME}
    activities.append(game)

    return {
        "op": 3,
        "d": {
            "status": status,
            "afk": False,
            "activities": activities,
            "since": 0,
        }
    }


async def update_all_presence(new_status: str = None, new_text: str = None):
    global STATUS, CUSTOM_STATUS
    if new_status is not None:
        STATUS = new_status
    if new_text is not None:
        CUSTOM_STATUS = new_text
    with lock:
        conns = dict(ws_connections)
    payload = json.dumps(build_presence(STATUS, CUSTOM_STATUS))
    for token, ws in conns.items():
        try:
            await ws.send_str(payload)
        except Exception:
            pass


def load_status_lines():
    """Read status.txt and return non-empty, non-comment lines."""
    if not os.path.exists(STATUS_FILE):
        return []
    with open(STATUS_FILE, encoding="utf-8") as f:
        return [l.strip() for l in f if l.strip() and not l.startswith("#")]


async def rotate_status():
    """Cycle through status.txt lines every STATUS_ROTATE_INTERVAL seconds.
    Re-reads the file on each full cycle so edits are picked up live."""
    index = 0
    while running:
        lines = load_status_lines()
        if lines:
            index = index % len(lines)
            await update_all_presence(new_text=lines[index])
            index += 1
        await asyncio.sleep(STATUS_ROTATE_INTERVAL)


def clear():
    os.system("cls" if os.name == "nt" else "clear")


def load_tokens():
    if not os.path.exists(TOKENS_FILE):
        print(f"{Fore.RED}tokens.txt not found in {SCRIPT_DIR}")
        sys.exit(1)
    with open(TOKENS_FILE, encoding="utf-8") as f:
        tokens = [l.strip() for l in f if l.strip() and not l.startswith("#")]
    return tokens


def draw_ui():
    while running:
        if ui_paused:
            time.sleep(0.2)
            continue
        with lock:
            snap = dict(accounts)

        clear()
        total      = len(snap)
        online     = sum(1 for a in snap.values() if a["state"] == "online")
        connecting = sum(1 for a in snap.values() if a["state"] == "connecting")
        dead       = sum(1 for a in snap.values() if a["state"] == "dead")
        error      = sum(1 for a in snap.values() if a["state"] == "error")

        print(f"{Fore.CYAN}{Style.BRIGHT}╔{'═'*68}╗")
        print(f"║{'  Discord Online Tool':^68}║")
        print(f"╠{'═'*68}╣")
        print(f"║  {Fore.GREEN}Online: {online:<6}{Fore.YELLOW}Connecting: {connecting:<6}{Fore.RED}Dead: {dead:<6}{Fore.MAGENTA}Error: {error:<6}{Fore.CYAN}         ║")
        print(f"║  {Fore.WHITE}Total: {total:<62}  ║")
        print(f"╠{'═'*68}╣")
        print(f"║  {'Username':<20} {'State':<12} {'Last Error / ID':<32}  ║")
        print(f"╠{'═'*68}╣")

        for token, info in list(snap.items()):
            state      = info.get("state", "connecting")
            username   = info.get("username", "...")[:18]
            uid        = info.get("id", "")
            last_error = info.get("last_error", "")

            right = uid[:30] if state == "online" else (last_error[:30] if last_error else "")

            if state == "online":
                color = Fore.GREEN
                icon  = "● ONLINE"
            elif state == "connecting":
                color = Fore.YELLOW
                icon  = "○ CONNECTING"
            elif state == "dead":
                color = Fore.RED
                icon  = "✖ DEAD"
            else:
                color = Fore.MAGENTA
                icon  = "! ERROR"

            print(f"║  {color}{username:<20} {icon:<12} {right:<32}{Fore.CYAN}  ║")

        print(f"╠{'═'*68}╣")
        cs = CUSTOM_STATUS[:44] if CUSTOM_STATUS else "none"
        status_src = "status.txt" if os.path.exists(STATUS_FILE) else "no status.txt"
        print(f"║  {Fore.WHITE}[1] Online  [2] Idle  [3] DND  [4] Invisible  [Q] Quit{Fore.CYAN}       ║")
        print(f"║  {Fore.WHITE}Status: {Fore.GREEN}{STATUS:<10}{Fore.WHITE} Rotating from: {Fore.CYAN}{status_src:<20}{Fore.CYAN}║")
        print(f"║  {Fore.WHITE}Current: {Fore.CYAN}{cs:<58}║")
        print(f"╚{'═'*68}╝")

        time.sleep(1)


async def keep_online(token: str, session: aiohttp.ClientSession, startup_delay: float = 0):
    short = token[:20] + "..."

    with lock:
        accounts[token] = {"state": "connecting", "username": short, "id": "", "last_error": ""}

    if startup_delay > 0:
        await asyncio.sleep(startup_delay)

    while running:
        try:
            async with session.ws_connect(GATEWAY, max_msg_size=0, timeout=aiohttp.ClientTimeout(total=30)) as ws:
                with lock:
                    ws_connections[token] = ws
                    accounts[token]["last_error"] = ""

                heartbeat_interval = None
                heartbeat_task     = None
                missed_acks        = [0]

                async def send_heartbeat():
                    while True:
                        await asyncio.sleep(heartbeat_interval / 1000)
                        if missed_acks[0] >= 2:
                            await ws.close()
                            return
                        missed_acks[0] += 1
                        await ws.send_str(json.dumps({"op": 1, "d": None}))

                async for msg in ws:
                    if not running:
                        return

                    if msg.type == aiohttp.WSMsgType.TEXT:
                        data = json.loads(msg.data)
                        op   = data.get("op")
                        t    = data.get("t")
                        d    = data.get("d") or {}

                        if op == 10:
                            heartbeat_interval = d["heartbeat_interval"]

                            await ws.send_str(json.dumps({"op": 1, "d": None}))

                            await ws.send_str(json.dumps({
                                "op": 2,
                                "d": {
                                    "token": token,
                                    "capabilities": 16381,
                                    "properties": {
                                        "os": "Windows",
                                        "browser": "Chrome",
                                        "device": "",
                                        "system_locale": "en-US",
                                        "browser_user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                                        "browser_version": "120.0.0.0",
                                        "os_version": "10",
                                        "referrer": "",
                                        "referring_domain": "",
                                        "referrer_current": "",
                                        "referring_domain_current": "",
                                        "release_channel": "stable",
                                        "client_build_number": 269902,
                                        "client_event_source": None,
                                    },
                                    "presence": build_presence(STATUS, CUSTOM_STATUS)["d"],
                                    "compress": False,
                                    "client_state": {
                                        "guild_versions": {},
                                        "highest_last_message_id": "0",
                                        "read_state_version": 0,
                                        "user_guild_settings_version": -1,
                                        "user_settings_version": -1,
                                        "private_channels_version": "0",
                                        "api_code_version": 0,
                                    }
                                }
                            }))

                            heartbeat_task = asyncio.create_task(send_heartbeat())

                        elif op == 11:
                            missed_acks[0] = 0

                        elif t == "READY":
                            user  = d.get("user", {})
                            uname = user.get("global_name") or user.get("username", short)
                            uid   = str(user.get("id", ""))
                            with lock:
                                accounts[token] = {
                                    "state":      "online",
                                    "username":   uname,
                                    "id":         uid,
                                    "last_error": "",
                                }

                        elif op == 9:
                            with lock:
                                accounts[token]["state"]      = "dead"
                                accounts[token]["username"]   = "INVALID SESSION"
                                accounts[token]["last_error"] = "op9 invalid session"
                            if heartbeat_task:
                                heartbeat_task.cancel()
                            return

                    elif msg.type == aiohttp.WSMsgType.CLOSED:
                        with lock:
                            accounts[token]["last_error"] = f"ws closed: {msg.data}"
                        break

                    elif msg.type == aiohttp.WSMsgType.ERROR:
                        with lock:
                            accounts[token]["last_error"] = f"ws error: {str(msg.data)[:25]}"
                        break

                if heartbeat_task:
                    heartbeat_task.cancel()

                with lock:
                    ws_connections.pop(token, None)

        except asyncio.TimeoutError:
            with lock:
                accounts[token]["state"]      = "error"
                accounts[token]["last_error"] = "timeout connecting to gateway"
        except aiohttp.ClientConnectorError as e:
            with lock:
                accounts[token]["state"]      = "error"
                accounts[token]["last_error"] = f"conn refused: {str(e)[:25]}"
        except Exception as e:
            err = str(e)
            if "4004" in err or "401" in err:
                with lock:
                    accounts[token]["state"]      = "dead"
                    accounts[token]["username"]   = "BAD TOKEN"
                    accounts[token]["last_error"] = err[:32]
                return
            with lock:
                accounts[token]["state"]      = "error"
                accounts[token]["last_error"] = err[:32]

        if not running:
            return

        with lock:
            if accounts[token]["state"] != "dead":
                accounts[token]["state"] = "connecting"
        await asyncio.sleep(5)


async def main():
    global running, STATUS, GAME_START_TIME
    GAME_START_TIME = int(time.time() * 1000)  # milliseconds, resets each run

    tokens = load_tokens()
    if not tokens:
        print(f"{Fore.RED}No tokens found in tokens.txt")
        return

    clear()
    print(f"{Fore.CYAN}{Style.BRIGHT}")
    print("╔══════════════════════════════════════╗")
    print("║      Discord Online Tool             ║")
    print("╠══════════════════════════════════════╣")
    print(f"║  Tokens loaded: {len(tokens):<21}║")

    status_lines = load_status_lines()
    if status_lines:
        print(f"║  Status lines:  {len(status_lines):<21}║")
    else:
        print(f"║  {Fore.YELLOW}No status.txt found — no custom status{Fore.CYAN}  ║")

    print(f"╠══════════════════════════════════════╣")
    print("║  [1] Online                          ║")
    print("║  [2] Idle                            ║")
    print("║  [3] Do Not Disturb                  ║")
    print("║  [4] Invisible                       ║")
    print("╚══════════════════════════════════════╝")
    print(f"\n{Fore.YELLOW}Choose status (or Enter for Online): ", end="")

    choice = input().strip()
    if choice == "2":
        STATUS = "idle"
    elif choice == "3":
        STATUS = "dnd"
    elif choice == "4":
        STATUS = "invisible"
    else:
        STATUS = "online"

    print(f"\n{Fore.GREEN}Starting {len(tokens)} connections as {STATUS.upper()}...\n")
    await asyncio.sleep(1)

    ui_thread = threading.Thread(target=draw_ui, daemon=True)
    ui_thread.start()

    connector = aiohttp.TCPConnector(limit=0, ssl=False)
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = [
            asyncio.create_task(keep_online(t, session, startup_delay=i * 2.0))
            for i, t in enumerate(tokens)
        ]

        # Start the status rotation task
        rotate_task = asyncio.create_task(rotate_status())

        loop = asyncio.get_running_loop()
        def input_loop():
            global running, STATUS, ui_paused
            while running:
                try:
                    cmd = input().strip().lower()
                    if cmd == "q":
                        running = False
                        for task in tasks:
                            task.cancel()
                        rotate_task.cancel()
                    elif cmd in ("1", "2", "3", "4"):
                        status_map = {"1": "online", "2": "idle", "3": "dnd", "4": "invisible"}
                        asyncio.run_coroutine_threadsafe(
                            update_all_presence(new_status=status_map[cmd]), loop
                        )
                except Exception:
                    pass

        input_thread = threading.Thread(target=input_loop, daemon=True)
        input_thread.start()

        try:
            await asyncio.gather(*tasks, rotate_task, return_exceptions=True)
        except asyncio.CancelledError:
            pass

    running = False
    clear()
    print(f"{Fore.GREEN}Disconnected all accounts. Goodbye.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        running = False
        clear()
        print(f"{Fore.YELLOW}Stopped.")
