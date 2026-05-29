import asyncio
import os
import discord
from discord.ext import commands

from database import setup_database
from config import GUILD_ID

TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()

bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    setup_database()

    guild = discord.Object(id=GUILD_ID)

    synced = await bot.tree.sync(guild=guild)

    print(f"Logged in as {bot.user}")
    print(f"Synced {len(synced)} commands to guild {GUILD_ID}")


async def main():
    async with bot:
        await bot.load_extension("cogs.economy")
        await bot.load_extension("cogs.tavern")
        await bot.start(TOKEN)


asyncio.run(main())
