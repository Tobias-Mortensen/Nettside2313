"""
Discord Online Tool
===================
Keeps all tokens online simultaneously via Discord gateway.

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

import asyncio, json, time, threading

init(autoreset=True)

SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))
TOKENS_FILE = os.path.join(SCRIPT_DIR, "tokens.txt")
GATEWAY     = "wss://gateway.discord.gg/?v=10&encoding=json"

STATUS        = "online"   # online / idle / dnd / invisible
CUSTOM_STATUS = ""         # custom status text e.g. "nothing stays forever"

accounts       = {}
ws_connections = {}
lock           = threading.Lock()
running        = True
ui_paused      = False


def build_presence(status: str, custom_text: str = ""):
    activities = []
    if custom_text:
        activities = [{
            "type": 4,
            "name": "Custom Status",
            "state": custom_text,
            "id": "custom",
        }]
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
        total   = len(snap)
        online  = sum(1 for a in snap.values() if a["state"] == "online")
        connecting = sum(1 for a in snap.values() if a["state"] == "connecting")
        dead    = sum(1 for a in snap.values() if a["state"] == "dead")
        error   = sum(1 for a in snap.values() if a["state"] == "error")

        print(f"{Fore.CYAN}{Style.BRIGHT}╔{'═'*60}╗")
        print(f"║{'  Discord Online Tool':^60}║")
        print(f"╠{'═'*60}╣")
        print(f"║  {Fore.GREEN}Online: {online:<6}{Fore.YELLOW}Connecting: {connecting:<6}{Fore.RED}Dead: {dead:<6}{Fore.MAGENTA}Error: {error:<6}{Fore.CYAN}  ║")
        print(f"║  {Fore.WHITE}Total: {total:<54}  ║")
        print(f"╠{'═'*60}╣")
        print(f"║  {'Username':<22} {'Status':<14} {'ID':<22}  ║")
        print(f"╠{'═'*60}╣")

        for token, info in list(snap.items()):
            state    = info.get("state", "connecting")
            username = info.get("username", "...")[:20]
            uid      = info.get("id", "")[:20]

            if state == "online":
                color  = Fore.GREEN
                icon   = "● ONLINE"
            elif state == "connecting":
                color  = Fore.YELLOW
                icon   = "○ CONNECTING"
            elif state == "dead":
                color  = Fore.RED
                icon   = "✖ DEAD"
            else:
                color  = Fore.MAGENTA
                icon   = "! ERROR"

            print(f"║  {color}{username:<22} {icon:<14} {uid:<22}{Fore.CYAN}  ║")

        print(f"╠{'═'*60}╣")
        cs = CUSTOM_STATUS[:30] if CUSTOM_STATUS else "none"
        print(f"║  {Fore.WHITE}[1] Online [2] Idle [3] DND [4] Invisible [Q] Quit{Fore.CYAN}     ║")
        print(f"║  {Fore.WHITE}[C] Set custom status text{Fore.CYAN}                              ║")
        print(f"║  {Fore.WHITE}Status: {Fore.GREEN}{STATUS:<12}{Fore.WHITE} Custom: {Fore.CYAN}{cs:<22}{Fore.CYAN}║")
        print(f"╚{'═'*60}╝")

        time.sleep(1)


async def keep_online(token: str, session: aiohttp.ClientSession):
    short = token[:20] + "..."

    with lock:
        accounts[token] = {"state": "connecting", "username": short, "id": ""}

    while running:
        try:
            async with session.ws_connect(GATEWAY) as ws:
                with lock:
                    ws_connections[token] = ws
                heartbeat_interval = None
                heartbeat_task     = None

                async def send_heartbeat():
                    while True:
                        await asyncio.sleep(heartbeat_interval / 1000)
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

                            # Send initial heartbeat
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

                        elif t == "READY":
                            user = d.get("user", {})
                            uname = user.get("global_name") or user.get("username", short)
                            uid   = str(user.get("id", ""))
                            with lock:
                                accounts[token] = {
                                    "state":    "online",
                                    "username": uname,
                                    "id":       uid,
                                }

                        elif op == 9:
                            with lock:
                                accounts[token]["state"] = "dead"
                                accounts[token]["username"] = "INVALID SESSION"
                            if heartbeat_task:
                                heartbeat_task.cancel()
                            return

                    elif msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
                        break

                if heartbeat_task:
                    heartbeat_task.cancel()

                with lock:
                    ws_connections.pop(token, None)

        except Exception as e:
            err = str(e)
            if "4004" in err or "401" in err:
                with lock:
                    accounts[token]["state"] = "dead"
                    accounts[token]["username"] = f"DEAD: {err[:30]}"
                return
            with lock:
                accounts[token]["state"] = "error"
                accounts[token]["username"] = f"ERR: {err[:30]}"

        if not running:
            return

        # Reconnect after 3s
        with lock:
            if accounts[token]["state"] != "dead":
                accounts[token]["state"] = "connecting"
        await asyncio.sleep(3)


async def fetch_status(token: str, session: aiohttp.ClientSession):
    try:
        async with session.get(
            "https://discord.com/api/v9/users/@me",
            headers={"Authorization": token}
        ) as r:
            if r.status == 200:
                d = await r.json()
                return d.get("global_name") or d.get("username"), str(d.get("id",""))
    except Exception:
        pass
    return None, None


async def main():
    global running, STATUS

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
    print(f"║  Status: {STATUS:<28}║")
    print("╠══════════════════════════════════════╣")
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

    # Start UI thread
    ui_thread = threading.Thread(target=draw_ui, daemon=True)
    ui_thread.start()

    connector = aiohttp.TCPConnector(limit=0, ssl=False)
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = [asyncio.create_task(keep_online(t, session)) for t in tokens]

        # Input loop for quit/commands
        loop = asyncio.get_running_loop()
        def input_loop():
            global running, STATUS, CUSTOM_STATUS, ui_paused
            while running:
                try:
                    cmd = input().strip().lower()
                    if cmd == "q":
                        running = False
                        for task in tasks:
                            task.cancel()
                    elif cmd in ("1", "2", "3", "4"):
                        status_map = {"1": "online", "2": "idle", "3": "dnd", "4": "invisible"}
                        new_status = status_map[cmd]
                        asyncio.run_coroutine_threadsafe(
                            update_all_presence(new_status=new_status), loop
                        )
                    elif cmd == "c":
                        global ui_paused
                        ui_paused = True
                        time.sleep(0.3)
                        clear()
                        print(f"{Fore.YELLOW}Enter custom status text (blank to clear): ", end="", flush=True)
                        text = input().strip()
                        ui_paused = False
                        asyncio.run_coroutine_threadsafe(
                            update_all_presence(new_text=text), loop
                        )
                except Exception:
                    pass

        input_thread = threading.Thread(target=input_loop, daemon=True)
        input_thread.start()

        try:
            await asyncio.gather(*tasks, return_exceptions=True)
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
