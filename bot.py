import asyncio
import discord
from discord.ext import commands
from database import setup_database

TOKEN = "YOUR_BOT_TOKEN_HERE"

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
