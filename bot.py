import asyncio
import os
import discord
from discord.ext import commands
from database import setup_database

TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    setup_database()
    await bot.tree.sync()
    print(f"Logged in as {bot.user}")

async def main():
    async with bot:
        await bot.load_extension("cogs.economy")
        await bot.load_extension("cogs.blackjack")
        await bot.start(TOKEN)

asyncio.run(main())
