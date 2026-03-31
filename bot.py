import os
import aiohttp
import discord
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
API_BASE_URL = os.getenv("API_BASE_URL")
API_KEY = os.getenv("API_KEY")

# ✅ No privileged intents needed
intents = discord.Intents.default()

bot = commands.Bot(command_prefix="!", intents=intents)

# ---------------- API HELPER ---------------- #
async def api_get(path: str, params: dict | None = None):
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Accept": "application/json",
        "User-Agent": "crypto2cash-discord-bot/1.0"
    }
    url = f"{API_BASE_URL}{path}"

    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.get(url, params=params, timeout=15) as resp:
            resp.raise_for_status()
            return await resp.json()

# ---------------- READY EVENT ---------------- #
@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"✅ Synced {len(synced)} slash commands")
    except Exception as e:
        print(f"❌ Sync failed: {e}")

# ---------------- COMMANDS ---------------- #

@bot.tree.command(name="howitworks", description="Learn how Crypto2Cash works")
async def how_it_works(interaction: discord.Interaction):
    embed = discord.Embed(
        title="How Crypto2Cash Works",
        description=(
            "1️⃣ Choose crypto & amount\n"
            "2️⃣ Send crypto to the address\n"
            "3️⃣ Receive your cash payout\n\n"
            "⚠️ Always double-check the network before sending."
        ),
        color=0x00ffcc
    )
    embed.set_footer(text="Security: Staff will NEVER DM you first.")
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="status", description="Check platform status")
async def status(interaction: discord.Interaction):
    try:
        data = await api_get("/api/status")
        embed = discord.Embed(
            title=f"Status: {data.get('status', 'UNKNOWN').upper()}",
            description=data.get("message", "No details."),
            color=0x00ff00
        )
    except Exception:
        embed = discord.Embed(
            title="Status",
            description="⚠️ Could not fetch status right now.",
            color=0xff0000
        )
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="rate", description="Get estimated payout")
@app_commands.describe(asset="Crypto (BTC, ETH)", amount="Amount", fiat="Currency (EUR, USD)")
async def rate(interaction: discord.Interaction, asset: str, amount: float, fiat: str = "EUR"):
    if amount <= 0:
        await interaction.response.send_message("Amount must be greater than 0.", ephemeral=True)
        return

    try:
        data = await api_get("/api/rate", {
            "asset": asset.upper(),
            "amount": amount,
            "fiat": fiat.upper()
        })

        embed = discord.Embed(title="💱 Estimated Payout", color=0x0099ff)
        embed.add_field(name="You send", value=f"{amount} {asset.upper()}", inline=True)
        embed.add_field(name="You receive", value=f'{data["payout"]} {fiat.upper()}', inline=True)
        embed.add_field(name="Fee", value=data.get("fee", "Included"), inline=True)
        embed.set_footer(text="Estimate only. Final payout may vary.")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    except Exception as e:
        await interaction.response.send_message(
            f"⚠️ Could not fetch rate.\nError: {e}",
            ephemeral=True
        )

@bot.tree.command(name="faq", description="Common questions")
async def faq(interaction: discord.Interaction):
    embed = discord.Embed(title="FAQ", color=0xcccccc)
    embed.add_field(
        name="Is this safe?",
        value="Only use official links. We never DM first.",
        inline=False
    )
    embed.add_field(
        name="How long does it take?",
        value="Depends on blockchain confirmations.",
        inline=False
    )
    embed.add_field(
        name="Wrong network?",
        value="Contact support immediately.",
        inline=False
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="support", description="Get help")
async def support(interaction: discord.Interaction):
    await interaction.response.send_message(
        "🛟 Open a ticket in the support channel or use official website support.\n⚠️ Never share private keys.",
        ephemeral=True
    )

# ---------------- RUN ---------------- #
bot.run(DISCORD_TOKEN)