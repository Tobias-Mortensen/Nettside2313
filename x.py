import discord
from discord.ext import commands
import asyncio
import os

# === CONFIG ===
TOKEN = "YOUR_USER_TOKEN_HERE"  # Get from Discord developer tools or browser local storage
CHANNEL_ID = 1493999175422054590  # ID of the channel where you want to spam/delete
MESSAGES = [
    "First message here",
    "Second message here",
    "Third message - whatever you want",
    # Add more as needed
]

bot = commands.Bot(command_prefix="!", self_bot=True, intents=discord.Intents.all())

@bot.event
async def on_ready():
    print(f"Selfbot logged in as {bot.user}")
    channel = bot.get_channel(CHANNEL_ID)
    if not channel:
        print("Channel not found!")
        return
    
    print("Starting message cycle...")
    while True:
        for msg_content in MESSAGES:
            try:
                # Send message
                sent_msg = await channel.send(msg_content)
                print(f"Sent: {msg_content}")
                
                # Wait 5 seconds
                await asyncio.sleep(5)
                
                # Delete it
                await sent_msg.delete()
                print(f"Deleted message")
                
            except Exception as e:
                print(f"Error: {e}")
            
            # Optional small delay between cycles
            await asyncio.sleep(1)

bot.run(TOKEN)