"""
AnyIP Proxy Generator
Generates unique session-based proxies for AnyIP residential network
"""

import random
import string

# ============================================================
# EDIT THESE WITH YOUR ANYIP CREDENTIALS
# ============================================================
PROXY_SERVER = "portal.anyip.io"
PORT = "1080"
USER_ID = "user_201fba"  # Your unique user ID
PASSWORD = "xz"       # Your password
PROXY_TYPE = "residential"  # or "mobile"

# How many proxies to generate
NUM_PROXIES = 10000
# ============================================================


def generate_session_id(length=10):
    """Generate a random session ID"""
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))


def main():
    print(f"Generating {NUM_PROXIES} AnyIP proxies...")
    
    with open('proxies.txt', 'w') as f:
        for i in range(NUM_PROXIES):
            # Generate unique session ID for each proxy
            session_id = generate_session_id(10)
            
            # Format: server:port:username:password
            # Username includes type and session
            username = f"{USER_ID},type_{PROXY_TYPE},session_{session_id}"
            
            proxy_line = f"{PROXY_SERVER}:{PORT}:{username}:{PASSWORD}"
            f.write(proxy_line + "\n")
    
    print(f"✅ Generated {NUM_PROXIES} unique proxies in proxies.txt")
    print(f"📍 Server: {PROXY_SERVER}:{PORT}")
    print(f"🔑 Each proxy has a unique session ID = unique IP")
    print(f"\nReady to run your Discord username checker!")


if __name__ == "__main__":
    main()
