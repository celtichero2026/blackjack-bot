import discord
from discord.ext import commands
from discord import app_commands
from database import get_or_create_player


class Economy(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="balance", description="Check your casino balance")
    async def balance(self, interaction: discord.Interaction):
        player = get_or_create_player(interaction.user.id)
        balance = player[0]

        await interaction.response.send_message(
            f"💰 {interaction.user.mention}, you have **{balance:,} coins**."
        )


async def setup(bot):
    await bot.add_cog(Economy(bot))
