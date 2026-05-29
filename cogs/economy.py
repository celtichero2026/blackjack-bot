import discord
from discord.ext import commands
from discord import app_commands
from database import get_or_create_player
from config import TAVERN_CHANNEL_ID


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


async def setup(bot):
    await bot.add_cog(Economy(bot))
