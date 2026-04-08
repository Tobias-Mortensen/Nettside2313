import requests
import string
import itertools
import threading
import time
from queue import Queue
from colorama import Fore, Style, init
from datetime import datetime

init(autoreset=True)

class DiscordUsernameChecker:
    def __init__(self, webhook_url, length, use_numbers, threads=10, use_proxies=False):
        self.webhook_url = webhook_url
        self.length = length
        self.use_numbers = use_numbers
        self.threads = threads
        self.use_proxies = use_proxies
        
        self.proxies = []
        self.queue = Queue()
        self.checked = 0
        self.available = 0
        self.unavailable = 0
        self.errors = 0
        self.start_time = time.time()
        self.lock = threading.Lock()
        
        # Discord API endpoint
        self.api_url = "https://discord.com/api/v9/unique-username/username-attempt-unauthed"
        
        # Load proxies if enabled
        if self.use_proxies:
            self.load_proxies()
    
    def load_proxies(self):
        """Load proxies from proxies.txt"""
        try:
            with open('proxies.txt', 'r') as f:
                self.proxies = [line.strip() for line in f if line.strip() and not line.startswith('#')]
            if self.proxies:
                print(f"{Fore.GREEN}[+] Loaded {len(self.proxies)} proxies")
                print(f"{Fore.CYAN}[*] Testing first proxy...")
                
                # Show how the proxy is formatted
                parts = self.proxies[0].split(':')
                if len(parts) == 4:
                    print(f"{Fore.CYAN}[DEBUG] Proxy format: {parts[0]}:{parts[1]} with auth")
                
                if self.test_proxy(self.proxies[0]):
                    print(f"{Fore.GREEN}[✓] Proxy test successful!")
                else:
                    print(f"{Fore.RED}[✗] Proxy test failed!")
                    print(f"{Fore.YELLOW}[!] Continuing anyway, but requests may fail...")
            else:
                print(f"{Fore.YELLOW}[!] proxies.txt is empty, running proxyless")
                self.use_proxies = False
        except FileNotFoundError:
            print(f"{Fore.YELLOW}[!] proxies.txt not found, running proxyless")
            self.use_proxies = False
    
    def test_proxy(self, proxy_line):
        """Test if a proxy is working"""
        try:
            parts = proxy_line.split(':')
            
            if len(parts) == 4:
                host, port, username, password = parts
                proxy_url = f'http://{username}:{password}@{host}:{port}'
            elif len(parts) == 2:
                host, port = parts
                proxy_url = f'http://{host}:{port}'
            else:
                print(f"{Fore.RED}[DEBUG] Invalid proxy format: {proxy_line}")
                return False
            
            proxies = {
                'http': proxy_url,
                'https': proxy_url
            }
            
            # Test with a simple request
            response = requests.get('https://httpbin.org/ip', proxies=proxies, timeout=10)
            return response.status_code == 200
        except Exception as e:
            print(f"{Fore.RED}[DEBUG] Proxy test error: {type(e).__name__}: {str(e)[:150]}")
            return False
    
    def get_proxy(self):
        """Get a rotating proxy"""
        if self.use_proxies and self.proxies:
            proxy_line = self.proxies[self.checked % len(self.proxies)]
            
            # Parse proxy format: host:port:username:password or host:port
            parts = proxy_line.split(':')
            
            if len(parts) == 4:
                # Format: host:port:username:password
                host, port, username, password = parts
                proxy_url = f'http://{username}:{password}@{host}:{port}'
            elif len(parts) == 2:
                # Format: host:port (no auth)
                host, port = parts
                proxy_url = f'http://{host}:{port}'
            else:
                # Invalid format, skip this proxy
                return None
            
            return {
                'http': proxy_url,
                'https': proxy_url
            }
        return None
    
    def check_username(self, username):
        """Check if a Discord username is available"""
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        payload = {'username': username}
        
        try:
            proxy = self.get_proxy()
            response = requests.post(
                self.api_url,
                json=payload,
                headers=headers,
                proxies=proxy,
                timeout=15
            )
            
            with self.lock:
                self.checked += 1
            
            if response.status_code == 200:
                data = response.json()
                if not data.get('taken', True):
                    return True
            elif response.status_code == 429:
                # Rate limited - wait a bit
                time.sleep(3)
                return None
                
            return False
            
        except requests.exceptions.ProxyError as e:
            with self.lock:
                self.errors += 1
                # Show first few errors for debugging
                if self.errors <= 3:
                    print(f"{Fore.RED}[DEBUG] Proxy Error: {str(e)[:100]}")
            return None
        except requests.exceptions.Timeout:
            with self.lock:
                self.errors += 1
                if self.errors <= 3:
                    print(f"{Fore.RED}[DEBUG] Timeout Error")
            return None
        except Exception as e:
            with self.lock:
                self.errors += 1
                if self.errors <= 3:
                    print(f"{Fore.RED}[DEBUG] Error: {type(e).__name__}: {str(e)[:100]}")
            return None
    
    def send_to_webhook(self, username):
        """Send available username to Discord webhook"""
        embed = {
            "title": "🎯 Available Username Found!",
            "description": f"**Username:** `{username}`",
            "color": 0x00ff00,
            "timestamp": datetime.utcnow().isoformat(),
            "footer": {
                "text": f"Checked: {self.checked} | Available: {self.available}"
            }
        }
        
        payload = {
            "embeds": [embed],
            "username": "Username Checker"
        }
        
        try:
            requests.post(self.webhook_url, json=payload, timeout=5)
        except Exception as e:
            print(f"{Fore.RED}[!] Failed to send webhook: {e}")
    
    def save_to_file(self, username):
        """Save available username to file"""
        with open('available_usernames.txt', 'a') as f:
            f.write(f"{username}\n")
    
    def worker(self):
        """Worker thread to process usernames from queue"""
        while True:
            username = self.queue.get()
            if username is None:
                break
            
            result = self.check_username(username)
            
            if result is True:
                with self.lock:
                    self.available += 1
                print(f"{Fore.GREEN}[✓] AVAILABLE: {username}")
                self.send_to_webhook(username)
                self.save_to_file(username)
            elif result is False:
                with self.lock:
                    self.unavailable += 1
                print(f"{Fore.RED}[✗] Taken: {username}")
            else:
                print(f"{Fore.YELLOW}[!] Error checking: {username}")
            
            self.queue.task_done()
    
    def generate_combinations(self):
        """Generate username combinations"""
        if self.use_numbers:
            chars = string.ascii_lowercase + string.digits
            char_type = "letters + numbers"
        else:
            chars = string.ascii_lowercase
            char_type = "letters only"
        
        print(f"{Fore.CYAN}[*] Generating {self.length}-character usernames ({char_type})...")
        
        for combo in itertools.product(chars, repeat=self.length):
            username = ''.join(combo)
            self.queue.put(username)
    
    def get_stats(self):
        """Get current statistics"""
        elapsed = time.time() - self.start_time
        rps = self.checked / elapsed if elapsed > 0 else 0
        
        return (
            f"{Fore.CYAN}[Stats] "
            f"Checked: {self.checked} | "
            f"Available: {Fore.GREEN}{self.available}{Fore.CYAN} | "
            f"Taken: {self.unavailable} | "
            f"Errors: {self.errors} | "
            f"RPS: {rps:.2f}"
        )
    
    def start(self):
        """Start the username checker"""
        print(f"\n{Fore.MAGENTA}{'='*60}")
        print(f"{Fore.MAGENTA}Discord Username Checker - Starting...")
        print(f"{Fore.MAGENTA}{'='*60}\n")
        
        # Start worker threads
        threads = []
        for _ in range(self.threads):
            t = threading.Thread(target=self.worker)
            t.daemon = True
            t.start()
            threads.append(t)
        
        print(f"{Fore.GREEN}[+] Started {self.threads} worker threads")
        
        # Generate combinations in background thread
        generator = threading.Thread(target=self.generate_combinations)
        generator.daemon = True
        generator.start()
        generator.join()  # Wait for generation to complete
        
        print(f"{Fore.GREEN}[+] Generated {self.queue.qsize()} combinations to check\n")
        
        # Monitor progress
        try:
            while not self.queue.empty():
                time.sleep(5)
                print(self.get_stats())
        except KeyboardInterrupt:
            print(f"\n{Fore.YELLOW}[!] Stopping...")
        
        # Wait for queue to finish
        self.queue.join()
        
        # Stop workers
        for _ in range(self.threads):
            self.queue.put(None)
        for t in threads:
            t.join()
        
        # Final stats
        print(f"\n{Fore.MAGENTA}{'='*60}")
        print(self.get_stats())
        print(f"{Fore.MAGENTA}{'='*60}")
        if self.available > 0:
            print(f"{Fore.GREEN}[+] Found {self.available} available usernames!")
        else:
            print(f"{Fore.YELLOW}[!] No available usernames found")


if __name__ == "__main__":
    print(f"{Fore.CYAN}╔════════════════════════════════════════════════════╗")
    print(f"{Fore.CYAN}║     Discord Username Checker - Webhook Edition    ║")
    print(f"{Fore.CYAN}╚════════════════════════════════════════════════════╝\n")
    
    # Get webhook URL
    webhook = input(f"{Fore.CYAN}[?] Enter Discord webhook URL: {Fore.WHITE}").strip()
    if not webhook:
        print(f"{Fore.RED}[!] Webhook URL is required!")
        exit(1)
    
    # Get character length
    while True:
        try:
            length = int(input(f"{Fore.CYAN}[?] How many characters? (3-5 recommended): {Fore.WHITE}").strip())
            if length < 1:
                print(f"{Fore.RED}[!] Length must be at least 1")
                continue
            if length > 6:
                print(f"{Fore.YELLOW}[!] Warning: {length} characters will take a very long time!")
                confirm = input(f"{Fore.YELLOW}[?] Continue? (y/n): {Fore.WHITE}").strip().lower()
                if confirm != 'y':
                    continue
            break
        except ValueError:
            print(f"{Fore.RED}[!] Please enter a valid number")
    
    # Get character type
    while True:
        char_type = input(f"{Fore.CYAN}[?] Character type? (1=letters only, 2=letters+numbers): {Fore.WHITE}").strip()
        if char_type == '1':
            use_numbers = False
            break
        elif char_type == '2':
            use_numbers = True
            break
        else:
            print(f"{Fore.RED}[!] Please enter 1 or 2")
    
    # Get threads
    try:
        threads = int(input(f"{Fore.CYAN}[?] Number of threads (default 10): {Fore.WHITE}").strip() or "10")
    except ValueError:
        threads = 10
        print(f"{Fore.YELLOW}[!] Using default: 10 threads")
    
    # Ask about proxies
    while True:
        use_proxy = input(f"{Fore.CYAN}[?] Use proxies? (y/n): {Fore.WHITE}").strip().lower()
        if use_proxy in ['y', 'yes']:
            use_proxies = True
            break
        elif use_proxy in ['n', 'no']:
            use_proxies = False
            break
        else:
            print(f"{Fore.RED}[!] Please enter y or n")
    
    # Create and start checker
    checker = DiscordUsernameChecker(
        webhook_url=webhook,
        length=length,
        use_numbers=use_numbers,
        threads=threads,
        use_proxies=use_proxies
    )
    
    checker.start()
