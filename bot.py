"""
Discord bot:
  - /send         : send a custom embed to a chosen channel
  - /lock         : send a 'No Access' embed with donut.png thumbnail
  - /setwelcome   : choose the channel for join-pings
  - /unsetwelcome : disable join-pings
  - on_member_join: pings the new member, then deletes the ping after 0.5s

Setup:
  1. Put bot.py + donut.png + .env in the same folder
  2. .env should contain a single line:
         DISCORD_TOKEN=your_token_here
  3. Install deps in your venv:
         pip install discord.py python-dotenv
  4. Run with PM2 (see ecosystem.config.js)
"""

import asyncio
import json
import logging
import os
from pathlib import Path

# Load .env from the folder bot.py lives in (works regardless of cwd)
from dotenv import load_dotenv
load_dotenv(Path(__file__).with_name(".env"))

import discord
from discord import app_commands
from discord.ext import commands

# -------------------------------------------------------------------- logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("bot")

# -------------------------------------------------------------------- paths
CONFIG_FILE = Path(__file__).with_name("config.json")
DONUT_PATH = Path(__file__).with_name("donut.png")
PING_DELETE_DELAY = 0.5  # seconds


def load_config() -> dict:
    if CONFIG_FILE.exists():
        try:
            return json.loads(CONFIG_FILE.read_text())
        except json.JSONDecodeError:
            log.warning("config.json is corrupted, starting fresh")
    return {}


def save_config(cfg: dict) -> None:
    CONFIG_FILE.write_text(json.dumps(cfg, indent=2))


# -------------------------------------------------------------------- bot
intents = discord.Intents.default()
intents.members = True  # required for on_member_join

bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready() -> None:
    log.info("Logged in as %s (id=%s)", bot.user, bot.user.id)
    try:
        synced = await bot.tree.sync()
        log.info("Synced %d slash command(s)", len(synced))
    except Exception as exc:
        log.exception("Failed to sync slash commands: %s", exc)


# -------------------------------------------------------------------- join ping
@bot.event
async def on_member_join(member: discord.Member) -> None:
    cfg = load_config()
    guild_cfg = cfg.get(str(member.guild.id))
    if not guild_cfg:
        return
    channel_id = guild_cfg.get("welcome_channel")
    if not channel_id:
        return

    channel = member.guild.get_channel(channel_id)
    if channel is None:
        log.warning("Welcome channel %s not found in guild %s", channel_id, member.guild.id)
        return

    try:
        msg = await channel.send(member.mention)
    except discord.Forbidden:
        log.warning("Missing permission to send in #%s", channel)
        return
    except discord.HTTPException as exc:
        log.warning("Failed to send welcome ping: %s", exc)
        return

    await asyncio.sleep(PING_DELETE_DELAY)

    try:
        await msg.delete()
    except discord.NotFound:
        pass
    except discord.Forbidden:
        log.warning("Missing permission to delete in #%s", channel)
    except discord.HTTPException as exc:
        log.warning("Failed to delete welcome ping: %s", exc)


# -------------------------------------------------------------------- /send
def _parse_color(value: str | None) -> discord.Color:
    if not value:
        return discord.Color.blurple()
    value = value.strip()

    named = {
        "blurple": discord.Color.blurple(),
        "red": discord.Color.red(),
        "green": discord.Color.green(),
        "blue": discord.Color.blue(),
        "yellow": discord.Color.yellow(),
        "orange": discord.Color.orange(),
        "purple": discord.Color.purple(),
        "gold": discord.Color.gold(),
        "black": discord.Color(0x000000),
        "white": discord.Color(0xFFFFFF),
    }
    if value.lower() in named:
        return named[value.lower()]

    try:
        return discord.Color(int(value.lstrip("#"), 16))
    except ValueError as exc:
        raise ValueError(f"'{value}' isn't a valid hex color or color name") from exc


@bot.tree.command(name="send", description="Send an embedded message to a channel.")
@app_commands.describe(
    channel="Channel to post the embed in",
    title="Embed title",
    description="Embed body. Use \\n for line breaks.",
    color="Hex like #5865F2 or a name like 'red'. Optional.",
    footer="Footer text. Optional.",
    image_url="Large image URL. Optional.",
    thumbnail_url="Small thumbnail image URL. Optional.",
)
@app_commands.default_permissions(manage_messages=True)
async def send(
    interaction: discord.Interaction,
    channel: discord.TextChannel,
    title: str,
    description: str,
    color: str | None = None,
    footer: str | None = None,
    image_url: str | None = None,
    thumbnail_url: str | None = None,
) -> None:
    if not interaction.user.guild_permissions.manage_messages:
        await interaction.response.send_message(
            "You need the **Manage Messages** permission to use this.", ephemeral=True
        )
        return

    try:
        embed_color = _parse_color(color)
    except ValueError as exc:
        await interaction.response.send_message(str(exc), ephemeral=True)
        return

    description = description.replace("\\n", "\n")

    embed = discord.Embed(title=title, description=description, color=embed_color)
    if footer:
        embed.set_footer(text=footer)
    if image_url:
        embed.set_image(url=image_url)
    if thumbnail_url:
        embed.set_thumbnail(url=thumbnail_url)

    try:
        await channel.send(embed=embed)
    except discord.Forbidden:
        await interaction.response.send_message(
            f"I don't have permission to post in {channel.mention}.", ephemeral=True
        )
        return
    except discord.HTTPException as exc:
        await interaction.response.send_message(f"Discord rejected the embed: {exc}", ephemeral=True)
        return

    await interaction.response.send_message(f"Embed sent in {channel.mention}.", ephemeral=True)


# -------------------------------------------------------------------- /lock
@bot.tree.command(name="lock", description="Send a 'No Access' embed with the donut thumbnail.")
@app_commands.describe(
    channel="Channel to post the lock message in",
    role="Role required to access the locked area",
    verification_channel="Channel where users complete verification",
)
@app_commands.default_permissions(manage_messages=True)
async def lock(
    interaction: discord.Interaction,
    channel: discord.TextChannel,
    role: discord.Role,
    verification_channel: discord.TextChannel,
) -> None:
    if not interaction.user.guild_permissions.manage_messages:
        await interaction.response.send_message(
            "You need the **Manage Messages** permission to use this.", ephemeral=True
        )
        return

    if not DONUT_PATH.exists():
        await interaction.response.send_message(
            f"`donut.png` not found at `{DONUT_PATH}`. Drop the file next to bot.py and try again.",
            ephemeral=True,
        )
        return

    embed = discord.Embed(
        title="🔒  No Access",
        description=(
            f"You must be {role.mention} to access this channel.\n\n"
            f"Please complete verification in {verification_channel.mention}."
        ),
        color=discord.Color(0xF1A03A),  # warm gold/orange like the mockup
    )
    embed.set_thumbnail(url="attachment://donut.png")

    file = discord.File(DONUT_PATH, filename="donut.png")

    try:
        await channel.send(
            embed=embed,
            file=file,
            allowed_mentions=discord.AllowedMentions(roles=False, everyone=False, users=False),
        )
    except discord.Forbidden:
        await interaction.response.send_message(
            f"I can't post (or attach files) in {channel.mention}.", ephemeral=True
        )
        return
    except discord.HTTPException as exc:
        await interaction.response.send_message(f"Discord rejected the message: {exc}", ephemeral=True)
        return

    await interaction.response.send_message(f"Lock message sent in {channel.mention}.", ephemeral=True)


# -------------------------------------------------------------------- /setwelcome
@bot.tree.command(name="setwelcome", description="Set the channel where new members get pinged.")
@app_commands.describe(channel="Channel to ping joiners in")
@app_commands.default_permissions(manage_guild=True)
async def setwelcome(interaction: discord.Interaction, channel: discord.TextChannel) -> None:
    if not interaction.user.guild_permissions.manage_guild:
        await interaction.response.send_message(
            "You need the **Manage Server** permission to use this.", ephemeral=True
        )
        return

    cfg = load_config()
    cfg.setdefault(str(interaction.guild.id), {})["welcome_channel"] = channel.id
    save_config(cfg)

    await interaction.response.send_message(
        f"Welcome pings will be sent in {channel.mention} and deleted after "
        f"{PING_DELETE_DELAY:g}s.",
        ephemeral=True,
    )


# -------------------------------------------------------------------- /unsetwelcome
@bot.tree.command(name="unsetwelcome", description="Stop pinging new members.")
@app_commands.default_permissions(manage_guild=True)
async def unsetwelcome(interaction: discord.Interaction) -> None:
    if not interaction.user.guild_permissions.manage_guild:
        await interaction.response.send_message(
            "You need the **Manage Server** permission to use this.", ephemeral=True
        )
        return

    cfg = load_config()
    guild_cfg = cfg.get(str(interaction.guild.id), {})
    if guild_cfg.pop("welcome_channel", None) is None:
        await interaction.response.send_message("Welcome pings weren't enabled.", ephemeral=True)
        return
    save_config(cfg)
    await interaction.response.send_message("Welcome pings disabled.", ephemeral=True)


# -------------------------------------------------------------------- run
if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        raise SystemExit(
            "DISCORD_TOKEN not found. Make sure .env exists in the same folder as bot.py "
            "and contains a line like:  DISCORD_TOKEN=your_token_here"
        )
    bot.run(token)
