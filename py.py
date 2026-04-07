import requests
import json
import random

# Quick configuration - edit these values
DATABASE_URL = 'https://test-3429d-default-rtdb.europe-west1.firebasedatabase.app/messages.json'
NUMBER_OF_MESSAGES = 50

# Random message components
WORDS = ['awesome', 'cool', 'amazing', 'fantastic', 'great', 'nice', 'wonderful', 'epic', 'brilliant', 'incredible']
EMOJIS = ['🔥', '💯', '⚡', '🎉', '🚀', '✨', '💪', '🎯', '👑', '💎', '🌟', '🎊']
ACTIONS = ['testing', 'checking', 'spamming', 'flooding', 'stressing', 'benchmarking', 'validating', 'hammering']
ADJECTIVES = ['random', 'chaotic', 'wild', 'crazy', 'intense', 'rapid', 'fast', 'quick', 'automated', 'generated']

NAMES = ['Bot', 'Tester', 'Spammer', 'Flooder', 'Agent', 'Script', 'Program', 'System', 'Auto', 'Machine']

def generate_random_message():
    """Generate a random message"""
    templates = [
        f"{random.choice(EMOJIS)} {random.choice(ADJECTIVES)} {random.choice(ACTIONS)} {random.choice(EMOJIS)}",
        f"{random.choice(WORDS)} message {random.randint(1, 9999)} {random.choice(EMOJIS)}",
        f"Stress test: {random.choice(WORDS)} and {random.choice(WORDS)} {random.choice(EMOJIS)}",
        f"{random.choice(ACTIONS)} the system... {random.choice(EMOJIS)}",
        f"{random.choice(ADJECTIVES)} {random.choice(ACTIONS)} in progress {random.randint(10, 99)}%",
    ]
    return random.choice(templates)

def generate_random_name():
    """Generate a random display name"""
    return f"{random.choice(ADJECTIVES).capitalize()}{random.choice(NAMES)}{random.randint(1, 999)}"

# Send messages
print(f'Sending {NUMBER_OF_MESSAGES} random messages...')

for i in range(1, NUMBER_OF_MESSAGES + 1):
    data = {
        'message': generate_random_message(),
        'name': generate_random_name()
    }
    
    response = requests.post(DATABASE_URL, json=data)
    
    if response.status_code == 200:
        print(f'✓ Message {i} sent: "{data["message"]}" from {data["name"]}')
    else:
        print(f'✗ Message {i} failed')

print(f'\n✅ Done! Sent {NUMBER_OF_MESSAGES} random messages')