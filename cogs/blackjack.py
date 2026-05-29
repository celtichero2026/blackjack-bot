import discord
from discord.ext import commands
from discord import app_commands

from config import TAVERN_CHANNEL_ID


def is_tavern_channel(interaction):
    return interaction.channel_id == TAVERN_CHANNEL_ID


class Blackjack(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="blackjack",
        description="Create a blackjack table"
    )
    async def blackjack(self, interaction: discord.Interaction):

        if not is_tavern_channel(interaction):
            await interaction.response.send_message(
                "🍺 TrophyBot only runs games in **The Tavern**.",
                ephemeral=True
            )
            return

        await interaction.response.send_message(
            "🎰 Blackjack table created!"
        )


async def setup(bot):
    await bot.add_cog(Blackjack(bot))
