import aiohttp
import asyncio
import json
import string
import time
import random
import ssl
from colorama import Fore, init
from datetime import datetime

init(autoreset=True)


class Discord4LetterChecker:
    def __init__(self, webhook_url, concurrency=50, use_proxies=False):
        self.webhook_url = webhook_url
        self.concurrency = concurrency
        self.use_proxies = use_proxies

        self.proxies = []
        self.checked = 0
        self.available = 0
        self.unavailable = 0
        self.errors = 0
        self.rate_limits = 0
        self.start_time = time.time()
        
        # Error warning feature
        self.error_warning_sent = False
        self.error_threshold = 13.0

        self.proxy_times = {}
        self.no_proxy_lock = asyncio.Lock() if not use_proxies else None
        self.no_proxy_last = 0.0

        self.webhook_queue = asyncio.Queue()

        self.checked_file = 'checked_4letter.txt'
        self.checked_set = self._load_checked()

        # Build all 4-letter combos not yet checked
        self.remaining = []
        for a in string.ascii_lowercase:
            for b in string.ascii_lowercase:
                for c in string.ascii_lowercase:
                    for d in string.ascii_lowercase:
                        name = a + b + c + d
                        if name not in self.checked_set:
                            self.remaining.append(name)
        random.shuffle(self.remaining)

        self.api_url = "https://discord.com/api/v9/unique-username/username-attempt-unauthed"
        self.ssl_ctx = ssl.create_default_context()
        self.ssl_ctx.check_hostname = False
        self.ssl_ctx.verify_mode = ssl.CERT_NONE

        if self.use_proxies:
            self.load_proxies()

    def _load_checked(self):
        try:
            with open(self.checked_file, 'r') as f:
                loaded = set(line.strip() for line in f if line.strip())
            print(f"{Fore.GREEN}[+] Loaded {len(loaded)} already-checked usernames")
            return loaded
        except FileNotFoundError:
            return set()

    def _save_checked(self, username):
        self.checked_set.add(username)
        with open(self.checked_file, 'a') as f:
            f.write(f"{username}\n")

    def load_proxies(self):
        try:
            with open('proxies.txt', 'r', encoding='utf-8') as f:
                self.proxies = [line.strip() for line in f if line.strip() and not line.startswith('#')]
            if self.proxies:
                print(f"{Fore.GREEN}[+] Loaded {len(self.proxies)} proxies")
                for i in range(len(self.proxies)):
                    self.proxy_times[i] = 0.0
            else:
                print(f"{Fore.YELLOW}[!] proxies.txt is empty, running proxyless")
                self.use_proxies = False
        except FileNotFoundError:
            print(f"{Fore.YELLOW}[!] proxies.txt not found, running proxyless")
            self.use_proxies = False

    def format_proxy(self, proxy_line):
        """Format proxy string to URL - supports multiple formats"""
        # Remove http:// prefix if present
        if proxy_line.startswith('http://'):
            proxy_line = proxy_line[7:]
        elif proxy_line.startswith('https://'):
            proxy_line = proxy_line[8:]
        
        parts = proxy_line.split(':')
        if len(parts) == 4:
            # Format: host:port:username:password
            host, port, username, password = parts
            return f'http://{username}:{password}@{host}:{port}'
        elif len(parts) > 4:
            # Format: host:port:username__cr.countries:password (or other multi-colon formats)
            host = parts[0]
            port = parts[1]
            username = parts[2]
            password = ':'.join(parts[3:])  # Join remaining parts
            return f'http://{username}:{password}@{host}:{port}'
        elif len(parts) == 2:
            return f'http://{parts[0]}:{parts[1]}'
        return None

    async def check_username(self, session, username, proxy_idx=None):
        if self.use_proxies and proxy_idx is not None:
            now = time.monotonic()
            last = self.proxy_times.get(proxy_idx, 0.0)
            wait = 0.3 - (now - last)
            if wait > 0:
                await asyncio.sleep(wait)
            self.proxy_times[proxy_idx] = time.monotonic()
        elif not self.use_proxies:
            async with self.no_proxy_lock:
                now = time.monotonic()
                wait = 0.5 - (now - self.no_proxy_last)
                if wait > 0:
                    await asyncio.sleep(wait)
                self.no_proxy_last = time.monotonic()

        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        payload = {'username': username}

        proxy_url = None
        if self.use_proxies and proxy_idx is not None:
            proxy_url = self.format_proxy(self.proxies[proxy_idx])

        try:
            async with session.post(
                self.api_url,
                json=payload,
                headers=headers,
                proxy=proxy_url,
                timeout=aiohttp.ClientTimeout(total=10),
                ssl=self.ssl_ctx
            ) as resp:
                self.checked += 1

                if resp.status == 200:
                    data = await resp.json()
                    self._save_checked(username)
                    if not data.get('taken', True):
                        return True
                    return False
                elif resp.status == 429:
                    self.rate_limits += 1
                    if self.rate_limits % 50 == 0:
                        print(f"{Fore.YELLOW}[!] Rate limiting ({self.rate_limits} total)")
                    await asyncio.sleep(random.uniform(2, 5))
                    return None
                elif resp.status in [403, 401]:
                    self.errors += 1
                    if self.errors <= 3:
                        print(f"{Fore.RED}[!] Blocked ({resp.status})")
                    return None
                else:
                    self.errors += 1
                    return False

        except (aiohttp.ClientProxyConnectionError, aiohttp.ClientHttpProxyError):
            self.errors += 1
            return None
        except asyncio.TimeoutError:
            self.errors += 1
            return None
        except Exception:
            self.errors += 1
            return None

    async def queue_webhook(self, username):
        embed = {
            "title": "4-Letter Username Available!",
            "description": f"**Username:** `{username}`",
            "color": 0xffd700,
            "timestamp": datetime.utcnow().isoformat(),
            "footer": {"text": f"Checked: {self.checked} | Available: {self.available}"}
        }
        payload = {"embeds": [embed], "username": "4-Letter Checker"}
        await self.webhook_queue.put((self.webhook_url, payload))

    async def send_error_warning(self):
        """Send one-time warning if error rate exceeds threshold"""
        if self.error_warning_sent:
            return
        
        total_attempts = self.checked + self.errors
        error_rate = (self.errors / total_attempts * 100) if total_attempts > 0 else 0
        
        if error_rate > self.error_threshold and total_attempts > 100:
            self.error_warning_sent = True
            
            embed = {
                "title": "⚠️ High Error Rate Warning",
                "description": f"Error rate has exceeded {self.error_threshold}%!",
                "color": 0xff0000,
                "fields": [
                    {"name": "Current Error Rate", "value": f"{error_rate:.1f}%", "inline": True},
                    {"name": "Total Errors", "value": f"{self.errors:,}", "inline": True},
                    {"name": "Successful Checks", "value": f"{self.checked:,}", "inline": True},
                    {"name": "Recommendation", "value": "Check your proxies or reduce concurrency", "inline": False}
                ],
                "timestamp": datetime.utcnow().isoformat()
            }
            payload = {"embeds": [embed], "username": "4-Letter Checker - Alert"}
            await self.webhook_queue.put((self.webhook_url, payload))

    async def webhook_sender(self, session):
        while True:
            url, payload = await self.webhook_queue.get()
            for attempt in range(3):
                try:
                    async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                        if resp.status == 429:
                            data = await resp.json()
                            retry_after = data.get('retry_after', 2)
                            await asyncio.sleep(retry_after)
                            continue
                        if resp.status in (200, 204):
                            break
                except Exception:
                    await asyncio.sleep(1)
            await asyncio.sleep(2.5)
            self.webhook_queue.task_done()

    def save_to_file(self, username):
        with open('available_4letter.txt', 'a') as f:
            f.write(f"{username}\n")
        with open('special_usernames.txt', 'a') as f:
            f.write(f"{username}\n")

    async def worker(self, session, sem, username, proxy_idx):
        async with sem:
            result = await self.check_username(session, username, proxy_idx)

            if result is True:
                self.available += 1
                print(f"{Fore.YELLOW}[★] AVAILABLE: {username}")
                await self.queue_webhook(username)
                self.save_to_file(username)
            elif result is False:
                self.unavailable += 1
                print(f"{Fore.RED}[-] Taken: {username}")

    def get_stats(self):
        elapsed = time.time() - self.start_time
        rps = self.checked / elapsed if elapsed > 0 else 0
        remaining = len(self.remaining)
        total = 26 ** 4
        done = total - remaining
        pct = done / total * 100
        
        # Fixed error rate calculation
        total_attempts = self.checked + self.errors
        error_rate = (self.errors / total_attempts * 100) if total_attempts > 0 else 0
        
        return (
            f"{Fore.CYAN}[Stats] "
            f"Checked: {self.checked} | "
            f"Available: {Fore.YELLOW}{self.available}{Fore.CYAN} | "
            f"Taken: {self.unavailable} | "
            f"Errors: {Fore.RED}{self.errors} ({error_rate:.1f}%){Fore.CYAN} | "
            f"Rate Limits: {self.rate_limits} | "
            f"RPS: {rps:.2f} | "
            f"Remaining: {remaining}/{total} ({pct:.1f}% done)"
        )

    async def stats_printer(self):
        while True:
            await asyncio.sleep(5)
            print(self.get_stats())
            # Check and send error warning if needed
            await self.send_error_warning()

    async def start(self):
        print(f"\n{Fore.MAGENTA}{'='*70}")
        print(f"{Fore.MAGENTA}Discord 4-Letter Username Checker (aaaa-zzzz)")
        print(f"{Fore.MAGENTA}{'='*70}\n")

        total = 26 ** 4
        print(f"{Fore.CYAN}[*] Total: {total:,} (aaaa-zzzz)")
        print(f"{Fore.CYAN}[*] Already checked: {total - len(self.remaining):,}")
        print(f"{Fore.CYAN}[*] Remaining: {len(self.remaining):,}\n")

        if not self.remaining:
            print(f"{Fore.GREEN}[+] All 4-letter usernames have been checked!")
            return

        num_proxies = len(self.proxies) if self.use_proxies else 1
        effective_concurrency = min(self.concurrency, num_proxies * 3) if self.use_proxies else 5

        sem = asyncio.Semaphore(effective_concurrency)
        connector = aiohttp.TCPConnector(limit=effective_concurrency * 2, ssl=self.ssl_ctx)

        if not self.use_proxies:
            self.no_proxy_lock = asyncio.Lock()

        print(f"{Fore.GREEN}[+] Concurrency: {effective_concurrency}")
        print(f"{Fore.GREEN}[+] Proxies: {num_proxies if self.use_proxies else 'none'}")
        print(f"{Fore.CYAN}[*] Press Ctrl+C to stop\n")

        stats_task = asyncio.create_task(self.stats_printer())

        try:
            async with aiohttp.ClientSession(connector=connector) as session:
                wh_tasks = [asyncio.create_task(self.webhook_sender(session)) for _ in range(2)]

                while self.remaining:
                    batch_size = min(effective_concurrency * 5, len(self.remaining))
                    batch = [self.remaining.pop() for _ in range(batch_size)]
                    tasks = []
                    for i, username in enumerate(batch):
                        proxy_idx = i % num_proxies if self.use_proxies else None
                        tasks.append(self.worker(session, sem, username, proxy_idx))
                    await asyncio.gather(*tasks)

                print(f"\n{Fore.GREEN}[+] All 4-letter usernames checked!")

        except (KeyboardInterrupt, asyncio.CancelledError):
            print(f"\n{Fore.YELLOW}[!] Stopping... ({len(self.remaining):,} remaining)")
            if not self.webhook_queue.empty():
                print(f"{Fore.YELLOW}[!] Sending {self.webhook_queue.qsize()} queued webhooks...")
                await self.webhook_queue.join()
        finally:
            for t in wh_tasks:
                t.cancel()
            stats_task.cancel()

        print(f"\n{Fore.MAGENTA}{'='*70}")
        print(self.get_stats())
        print(f"{Fore.MAGENTA}{'='*70}")
        if self.available > 0:
            print(f"{Fore.YELLOW}[+] Found {self.available} available 4-letter usernames!")


CONFIG_FILE = 'config_4letter.json'

DEFAULT_CONFIG = {
    "webhook": "",
    "use_proxies": False,
    "concurrency": 50
}


def load_config():
    try:
        with open(CONFIG_FILE, 'r') as f:
            cfg = json.load(f)
        print(f"{Fore.GREEN}[+] Loaded settings from {CONFIG_FILE}")
        return {**DEFAULT_CONFIG, **cfg}
    except FileNotFoundError:
        return None
    except json.JSONDecodeError:
        print(f"{Fore.RED}[!] {CONFIG_FILE} is invalid JSON, ignoring")
        return None


def save_config(cfg):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(cfg, f, indent=2)
    print(f"{Fore.GREEN}[+] Settings saved to {CONFIG_FILE}")


def prompt_settings():
    webhook = input(f"{Fore.CYAN}[?] Webhook URL: {Fore.WHITE}").strip()
    if not webhook:
        print(f"{Fore.RED}[!] Webhook URL required!")
        exit(1)

    while True:
        up = input(f"{Fore.CYAN}[?] Use proxies? (y/n): {Fore.WHITE}").strip().lower()
        if up in ('y', 'yes', 'n', 'no'):
            use_proxies = up in ('y', 'yes')
            break

    if use_proxies:
        try:
            with open('proxies.txt', 'r') as f:
                pc = len([l for l in f if l.strip() and not l.startswith('#')])
            rec = min(pc * 3, 500)
            print(f"{Fore.YELLOW}[!] {pc} proxies -> recommended concurrency: {rec}")
            ci = input(f"{Fore.CYAN}[?] Concurrency (default {rec}): {Fore.WHITE}").strip()
            concurrency = int(ci) if ci else rec
        except Exception:
            concurrency = int(input(f"{Fore.CYAN}[?] Concurrency (default 50): {Fore.WHITE}").strip() or "50")
    else:
        concurrency = int(input(f"{Fore.CYAN}[?] Concurrency (default 5): {Fore.WHITE}").strip() or "5")

    return {
        "webhook": webhook,
        "use_proxies": use_proxies,
        "concurrency": concurrency
    }


if __name__ == "__main__":
    print(f"{Fore.CYAN}{'='*55}")
    print(f"{Fore.CYAN}  Discord 4-Letter Username Checker (aaaa-zzzz)")
    print(f"{Fore.CYAN}{'='*55}\n")

    cfg = load_config()

    if cfg and cfg.get("webhook"):
        print(f"{Fore.CYAN}  Webhook:     {cfg['webhook'][:40]}...")
        print(f"{Fore.CYAN}  Proxies:     {'yes' if cfg['use_proxies'] else 'no'}")
        print(f"{Fore.CYAN}  Concurrency: {cfg['concurrency']}\n")

        choice = input(f"{Fore.CYAN}[?] Use these settings? (y/n): {Fore.WHITE}").strip().lower()
        if choice not in ('y', 'yes', ''):
            cfg = prompt_settings()
            save_config(cfg)
    else:
        cfg = prompt_settings()
        save = input(f"{Fore.CYAN}[?] Save settings for next time? (y/n): {Fore.WHITE}").strip().lower()
        if save in ('y', 'yes', ''):
            save_config(cfg)

    checker = Discord4LetterChecker(
        webhook_url=cfg['webhook'],
        concurrency=cfg['concurrency'],
        use_proxies=cfg['use_proxies']
    )

    try:
        asyncio.run(checker.start())
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}[!] Stopped.")
