import discord
from discord.ext import commands
from discord import app_commands


class Blackjack(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="blackjack", description="Create a blackjack table")
    async def blackjack(self, interaction: discord.Interaction):
        await interaction.response.send_message("🎰 Blackjack table created!")


async def setup(bot):
    await bot.add_cog(Blackjack(bot))
