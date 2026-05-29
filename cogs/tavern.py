import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime, timezone

from config import TAVERN_CHANNEL_ID, DAILY_REWARD
from database import (
    get_or_create_player,
    claim_daily,
    get_leaderboard,
    get_balance,
    record_game_result,
)
from games.blackjack_engine import Deck, hand_value


BASE_BET = 100


def is_tavern_channel(interaction):
    return interaction.channel_id == TAVERN_CHANNEL_ID


def format_hand(hand):
    return " ".join([f"{card[0]}{card[1]}" for card in hand])


class BlackjackGameView(discord.ui.View):
    def __init__(self, deck, dealer_hand, player_hands, players):
        super().__init__(timeout=None)
        self.deck = deck
        self.dealer_hand = dealer_hand
        self.player_hands = player_hands
        self.players = players
        self.current_index = 0

        self.player_bets = {
            player_id: BASE_BET
            for player_id in players
        }

        self.has_acted = {
            player_id: False
            for player_id in players
        }

    def current_player_id(self):
        return self.players[self.current_index]

    def build_embed(self, reveal_dealer=False, game_over=False):
        description = ""

        if reveal_dealer:
            dealer_cards = format_hand(self.dealer_hand)
            dealer_total = hand_value(self.dealer_hand)
            description += f"**Dealer**\n{dealer_cards}\nTotal: **{dealer_total}**\n\n"
        else:
            visible = self.dealer_hand[1]
            description += f"**Dealer**\n🂠 {visible[0]}{visible[1]}\n\n"

        for player_id in self.players:
            hand = self.player_hands[player_id]
            cards = format_hand(hand)
            total = hand_value(hand)
            bet = self.player_bets[player_id]

            marker = ""
            if not game_over and player_id == self.current_player_id():
                marker = "⬅️ Current Turn"

            description += (
                f"**<@{player_id}>** {marker}\n"
                f"{cards}\n"
                f"Total: **{total}** | Bet: **{bet:,} gold**\n\n"
            )

        if game_over:
            description += self.finish_game_and_results()

        return discord.Embed(
            title="🃏 Blackjack",
            description=description,
            color=discord.Color.dark_gold()
        )

    def finish_game_and_results(self):
        dealer_total = hand_value(self.dealer_hand)
        text = "**Results**\n"

        for player_id in self.players:
            player_total = hand_value(self.player_hands[player_id])
            bet = self.player_bets[player_id]

            if player_total > 21:
                result = "Bust — lost"
                record_game_result(player_id, "loss", -bet)

            elif dealer_total > 21:
                result = f"Dealer bust — won **{bet:,} gold**"
                record_game_result(player_id, "win", bet)

            elif player_total > dealer_total:
                result = f"Won **{bet:,} gold**"
                record_game_result(player_id, "win", bet)

            elif player_total < dealer_total:
                result = f"Lost **{bet:,} gold**"
                record_game_result(player_id, "loss", -bet)

            else:
                result = "Push"
                record_game_result(player_id, "push", 0)

            text += f"<@{player_id}>: **{result}**\n"

        return text

    async def advance_turn_or_finish(self, interaction):
        while self.current_index < len(self.players) - 1:
            self.current_index += 1
            current_id = self.current_player_id()

            if hand_value(self.player_hands[current_id]) <= 21:
                await interaction.response.edit_message(
                    embed=self.build_embed(),
                    view=self
                )
                return

        while hand_value(self.dealer_hand) < 17:
            self.dealer_hand.append(self.deck.draw())

        await interaction.response.edit_message(
            embed=self.build_embed(reveal_dealer=True, game_over=True),
            view=None
        )

    @discord.ui.button(label="Hit", emoji="🃏", style=discord.ButtonStyle.green)
    async def hit(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.current_player_id():
            await interaction.response.send_message(
                "It is not your turn.",
                ephemeral=True
            )
            return

        self.has_acted[interaction.user.id] = True
        self.player_hands[interaction.user.id].append(self.deck.draw())

        if hand_value(self.player_hands[interaction.user.id]) > 21:
            await self.advance_turn_or_finish(interaction)
            return

        await interaction.response.edit_message(
            embed=self.build_embed(),
            view=self
        )

    @discord.ui.button(label="Stand", emoji="✋", style=discord.ButtonStyle.blurple)
    async def stand(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.current_player_id():
            await interaction.response.send_message(
                "It is not your turn.",
                ephemeral=True
            )
            return

        self.has_acted[interaction.user.id] = True
        await self.advance_turn_or_finish(interaction)

    @discord.ui.button(label="Double", emoji="💰", style=discord.ButtonStyle.red)
    async def double(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.current_player_id():
            await interaction.response.send_message(
                "It is not your turn.",
                ephemeral=True
            )
            return

        if self.has_acted[interaction.user.id]:
            await interaction.response.send_message(
                "You can only double before taking another action.",
                ephemeral=True
            )
            return

        current_bet = self.player_bets[interaction.user.id]
        balance = get_balance(interaction.user.id)

        if balance < current_bet * 2:
            await interaction.response.send_message(
                "You do not have enough gold to double down.",
                ephemeral=True
            )
            return

        self.player_bets[interaction.user.id] = current_bet * 2
        self.has_acted[interaction.user.id] = True
        self.player_hands[interaction.user.id].append(self.deck.draw())

        await self.advance_turn_or_finish(interaction)


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

        if get_balance(interaction.user.id) < BASE_BET:
            await interaction.response.send_message(
                f"You need at least **{BASE_BET:,} gold** to join this table.",
                ephemeral=True
            )
            return

        self.players.append(interaction.user.id)

        player_list = "\n".join([f"- <@{player_id}>" for player_id in self.players])

        embed = discord.Embed(
            title="🃏 Blackjack Table",
            description=(
                f"**Bet:** {BASE_BET:,} gold\n\n"
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

        for player_id in self.players:
            if get_balance(player_id) < BASE_BET:
                await interaction.response.send_message(
                    f"<@{player_id}> does not have enough gold to play.",
                    ephemeral=True
                )
                return

        deck = Deck()
        dealer_hand = [deck.draw(), deck.draw()]
        player_hands = {}

        for player_id in self.players:
            player_hands[player_id] = [deck.draw(), deck.draw()]

        game_view = BlackjackGameView(deck, dealer_hand, player_hands, self.players)

        await interaction.response.edit_message(
            embed=game_view.build_embed(),
            view=game_view
        )


class TavernView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Claim Daily", emoji="🍺", style=discord.ButtonStyle.green)
    async def daily_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        claimed, balance = claim_daily(interaction.user.id, DAILY_REWARD, today)

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
        if get_balance(interaction.user.id) < BASE_BET:
            await interaction.response.send_message(
                f"You need at least **{BASE_BET:,} gold** to open a blackjack table.",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title="🃏 Blackjack Table",
            description=(
                f"**Bet:** {BASE_BET:,} gold\n\n"
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

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True
        )


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

        await interaction.response.send_message(
            embed=embed,
            view=TavernView()
        )


async def setup(bot):
    await bot.add_cog(Tavern(bot))
