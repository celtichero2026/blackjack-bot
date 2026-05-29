import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime, timezone
from config import TAVERN_CHANNEL_ID, DAILY_REWARD
from database import get_or_create_player, claim_daily, get_leaderboard




def is_tavern_channel(interaction):
    return interaction.channel_id == TAVERN_CHANNEL_ID

class BlackjackTableView(discord.ui.View):
    def __init__(self, host_id):
        super().__init__(timeout=None)
        self.host_id = host_id
        self.players = [host_id]

    @discord.ui.button(label="Join Table", emoji="🍺", style=discord.ButtonStyle.green)
    async def join_table(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id in self.players:
            await interaction.response.send_message(
                "You are already sitting at this table.",
                ephemeral=True
            )
            return

        self.players.append(interaction.user.id)

        player_list = "\n".join([f"- <@{player_id}>" for player_id in self.players])

        embed = discord.Embed(
            title="🃏 Blackjack Table",
            description=(
                "**Bet:** 100 gold\n\n"
                f"**Players:**\n{player_list}\n\n"
                "Click **Join Table** to sit down.\n"
                "Host can click **Start Game** when ready."
            ),
            color=discord.Color.dark_gold()
        )

        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Start Game", emoji="▶️", style=discord.ButtonStyle.blurple)
    async def start_game(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.host_id:
            await interaction.response.send_message(
                "Only the table host can start the game.",
                ephemeral=True
            )
            return

        await interaction.response.send_message(
            "🃏 Game start is next. Table creation works!",
            ephemeral=True
        )

class TavernView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Claim Daily", emoji="🍺", style=discord.ButtonStyle.green)
    async def daily_button(self, interaction: discord.Interaction, button: discord.ui.Button):
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

    @discord.ui.button(label="Balance", emoji="💰", style=discord.ButtonStyle.blurple)
    async def balance_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        player = get_or_create_player(interaction.user.id)
        balance = player[0]

        await interaction.response.send_message(
            f"💰 You have **{balance:,} gold**.",
            ephemeral=True
        )

    @discord.ui.button(label="Blackjack", emoji="🃏", style=discord.ButtonStyle.red)
    async def blackjack_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="🃏 Blackjack Table",
            description=(
                "**Bet:** 100 gold\n\n"
                "**Players:**\n"
                f"- {interaction.user.mention}\n\n"
                "Click **Join Table** to sit down.\n"
                "Host can click **Start Game** when ready."
            ),
            color=discord.Color.dark_gold()
        )

        await interaction.response.send_message(
            embed=embed,
            view=BlackjackTableView(host_id=interaction.user.id)
        )

    @discord.ui.button(label="Leaderboard", emoji="🏆", style=discord.ButtonStyle.gray)
    async def leaderboard_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        rows = get_leaderboard(10)

        if not rows:
            await interaction.response.send_message(
                "🍺 No Tavern players yet.",
                ephemeral=True
            )
            return

        description = ""

        for index, row in enumerate(rows, start=1):
            user_id, balance, wins, losses, games_played = row
            description += f"**{index}.** <@{user_id}> — **{balance:,} gold**\n"

        embed = discord.Embed(
            title="🏆 The Tavern Leaderboard",
            description=description,
            color=discord.Color.gold()
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)


class Tavern(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="tavern", description="Open The Tavern menu")
    async def tavern(self, interaction: discord.Interaction):

        if not is_tavern_channel(interaction):
            await interaction.response.send_message(
                "🍺 TrophyBot only runs in **The Tavern**.",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title="🍺 Welcome to The Tavern",
            description=(
                "Try your luck, claim your gold, and make questionable decisions.\n\n"
                "**Available:**\n"
                "🍺 Daily Gold\n"
                "💰 Balance\n"
                "🃏 Blackjack\n"
                "🏆 Leaderboard"
            ),
            color=discord.Color.gold()
        )

        embed.set_footer(text="The house always wins. Unless it doesn't.")

        await interaction.response.send_message(embed=embed, view=TavernView())


async def setup(bot):
    await bot.add_cog(Tavern(bot))
