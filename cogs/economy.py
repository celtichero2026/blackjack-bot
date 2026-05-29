import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime, timezone

from config import TAVERN_CHANNEL_ID, DAILY_REWARD
from database import get_or_create_player, claim_daily


def is_tavern_channel(interaction):
    return interaction.channel_id == TAVERN_CHANNEL_ID


class Economy(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="balance", description="Check your Tavern gold")
    async def balance(self, interaction: discord.Interaction):

        if not is_tavern_channel(interaction):
            await interaction.response.send_message(
                "🍺 TrophyBot only runs games in **The Tavern**.",
                ephemeral=True
            )
            return

        player = get_or_create_player(interaction.user.id)
        balance = player[0]

        await interaction.response.send_message(
            f"💰 You have **{balance:,} gold**.",
            ephemeral=True
        )

    @app_commands.command(name="daily", description="Claim your daily Tavern gold")
    async def daily(self, interaction: discord.Interaction):

        if not is_tavern_channel(interaction):
            await interaction.response.send_message(
                "🍺 TrophyBot only runs games in **The Tavern**.",
                ephemeral=True
            )
            return

        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        claimed, balance = claim_daily(
            interaction.user.id,
            DAILY_REWARD,
            today
        )

        if not claimed:
            await interaction.response.send_message(
                f"🍺 You already claimed your daily gold today.\n💰 Balance: **{balance:,} gold**.",
                ephemeral=True
            )
            return

        await interaction.response.send_message(
            f"🍺 You claimed **{DAILY_REWARD:,} gold** from The Tavern.\n💰 New balance: **{balance:,} gold**.",
            ephemeral=True
        )


async def setup(bot):
    await bot.add_cog(Economy(bot))
