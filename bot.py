import os
import aiohttp
import discord
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
API_BASE_URL = os.getenv("API_BASE_URL")  # e.g. https://crypto2cash.vercel.app
API_KEY = os.getenv("API_KEY")

intents = discord.Intents.default()
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

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

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} slash commands.")
    except Exception as e:
        print(f"Command sync failed: {e}")

@bot.tree.command(name="howitworks", description="Learn how Crypto2Cash works")
async def how_it_works(interaction: discord.Interaction):
    embed = discord.Embed(
        title="How Crypto2Cash Works",
        description=(
            "1. Choose your crypto and amount\n"
            "2. Send the crypto to the provided address\n"
            "3. Receive your cash payout after confirmation\n\n"
            "Always double-check the network before sending."
        )
    )
    embed.set_footer(text="Security tip: Staff will never DM you first.")
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="fees", description="View fee information")
async def fees(interaction: discord.Interaction):
    try:
        data = await api_get("/api/fees")
        text = data.get("message", "Fees vary by asset, amount, and payout method.")
    except Exception:
        text = "Fees vary by asset, amount, and payout method. Use /rate for an estimate."
    await interaction.response.send_message(text, ephemeral=True)

@bot.tree.command(name="status", description="Check platform status")
async def status(interaction: discord.Interaction):
    try:
        data = await api_get("/api/status")
        status_text = data.get("status", "unknown").upper()
        message = data.get("message", "No details available.")
        embed = discord.Embed(title=f"Platform Status: {status_text}", description=message)
    except Exception:
        embed = discord.Embed(
            title="Platform Status",
            description="Unable to fetch live status right now. Please try again later."
        )
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="rate", description="Get an estimated exchange payout")
@app_commands.describe(asset="Crypto asset, e.g. BTC", amount="Amount to exchange", fiat="Fiat currency, e.g. EUR")
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

        embed = discord.Embed(title="Estimated Payout")
        embed.add_field(name="You send", value=f"{amount} {asset.upper()}", inline=True)
        embed.add_field(name="You receive", value=f'{data["payout"]} {fiat.upper()}', inline=True)
        embed.add_field(name="Fee", value=data.get("fee", "Included in estimate"), inline=True)
        embed.add_field(name="Rate", value=str(data.get("rate", "N/A")), inline=False)
        embed.set_footer(text="Estimate only. Final payout may depend on confirmations and market movement.")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    except Exception as e:
        await interaction.response.send_message(
            f"Could not fetch rate right now. Please try again later.\nError: {e}",
            ephemeral=True
        )

@bot.tree.command(name="faq", description="Common questions and answers")
async def faq(interaction: discord.Interaction):
    embed = discord.Embed(title="FAQ")
    embed.add_field(
        name="Is this the official server?",
        value="Use only links posted here and on the official website.",
        inline=False
    )
    embed.add_field(
        name="How long does it take?",
        value="Time depends on network confirmations and payout method.",
        inline=False
    )
    embed.add_field(
        name="What if I sent on the wrong network?",
        value="Contact support immediately with details. Recovery may not be possible.",
        inline=False
    )
    embed.set_footer(text="Security tip: Ignore DMs claiming to be support.")
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="support", description="Get support instructions")
async def support(interaction: discord.Interaction):
    await interaction.response.send_message(
        "For support, open a ticket in the support channel or contact the official support method listed on the website. Never share private keys or seed phrases.",
        ephemeral=True
    )

bot.run(DISCORD_TOKEN)