import discord
import random
from discord.ext import commands
from discord import app_commands
from datetime import datetime, timezone
from typing import Optional

from config import TAVERN_CHANNEL_ID, DAILY_REWARD
from database import (
    get_or_create_player,
    claim_daily,
    get_leaderboard,
    get_balance,
    record_game_result,
    get_profile,
    get_player_achievements,
    record_wager,
    record_double,
    record_blackjack,
    update_biggest_win,
    update_biggest_loss,
)
from games.blackjack_engine import Deck, hand_value
from achievement_service import check_achievements
from achievements import ACHIEVEMENTS


TROPHY_ID = 875349215876894720
FOUNDER_ID = 502268158749573132
BASE_BET = 100


def is_tavern_channel(interaction):
    return interaction.channel_id == TAVERN_CHANNEL_ID


def format_hand(hand):
    return " ".join([f"{card[0]}{card[1]}" for card in hand])


def add_achievement_text(player_id, result):
    new_achievements = check_achievements(player_id)

    if new_achievements:
        result += (
            "\n🏆 Achievement Unlocked:\n"
            + "\n".join(new_achievements)
        )

    return result


cclass BlackjackGameView(discord.ui.View):
    def __init__(self, deck, dealer_hand, player_hands, players, bet):
        super().__init__(timeout=None)
        self.deck = deck
        self.dealer_hand = dealer_hand
        self.players = players
        self.bet = bet

        # Convert each player from one hand into a list of hands
        self.player_hands = {
            player_id: [player_hands[player_id]]
            for player_id in players
        }

        self.player_bets = {
            player_id: [bet]
            for player_id in players
        }

        self.has_acted = {
            player_id: [False]
            for player_id in players
        }

        # Turns are now player + hand number
        self.turns = [
            (player_id, 0)
            for player_id in players
        ]

        self.current_index = 0

    def current_turn(self):
        return self.turns[self.current_index]

    def current_player_id(self):
        player_id, hand_index = self.current_turn()
        return player_id

    def current_hand_index(self):
        player_id, hand_index = self.current_turn()
        return hand_index

    def current_hand(self):
        player_id, hand_index = self.current_turn()
        return self.player_hands[player_id][hand_index]

    def current_bet(self):
        player_id, hand_index = self.current_turn()
        return self.player_bets[player_id][hand_index]

    def can_split_current_hand(self):
        player_id, hand_index = self.current_turn()
        hand = self.player_hands[player_id][hand_index]

        if hand_index != 0:
            return False

        if len(self.player_hands[player_id]) > 1:
            return False

        if len(hand) != 2:
            return False

        first_rank = hand[0][0]
        second_rank = hand[1][0]
        
        ten_value = {"10", "J", "Q", "K"}
        
        if first_rank in ten_value and second_rank in ten_value:
            return True
        
        return first_rank == second_rank

    def build_embed(self, reveal_dealer=False, game_over=False):
        description = ""

        if reveal_dealer:
            dealer_cards = format_hand(self.dealer_hand)
            dealer_total = hand_value(self.dealer_hand)
            description += f"**Dealer**\n{dealer_cards}\nTotal: **{dealer_total}**\n\n"
        else:
            visible = self.dealer_hand[1]
            description += f"**Dealer**\n🂠 {visible[0]}{visible[1]}\n\n"

        current_player, current_hand_index = self.current_turn()

        for player_id in self.players:
            hands = self.player_hands[player_id]

            for hand_index, hand in enumerate(hands):
                cards = format_hand(hand)
                total = hand_value(hand)
                bet = self.player_bets[player_id][hand_index]

                marker = ""
                hand_label = ""

                if len(hands) > 1:
                    hand_label = f" — Hand {hand_index + 1}"

                if (
                    not game_over
                    and player_id == current_player
                    and hand_index == current_hand_index
                ):
                    marker = "⬅️ Current Turn"

                description += (
                    f"**<@{player_id}>{hand_label}** {marker}\n"
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
            hands = self.player_hands[player_id]

            for hand_index, hand in enumerate(hands):
                player_total = hand_value(hand)
                bet = self.player_bets[player_id][hand_index]

                hand_label = ""
                if len(hands) > 1:
                    hand_label = f" Hand {hand_index + 1}"

                if player_total > 21:
                    result = f"{hand_label} bust — lost **{bet:,} gold**"
                    record_game_result(player_id, "loss", -bet)
                    update_biggest_loss(player_id, bet)

                elif dealer_total > 21:
                    result = f"{hand_label} dealer bust — won **{bet:,} gold**"
                    record_game_result(player_id, "win", bet)
                    update_biggest_win(player_id, bet)

                elif player_total > dealer_total:
                    result = f"{hand_label} won **{bet:,} gold**"
                    record_game_result(player_id, "win", bet)
                    update_biggest_win(player_id, bet)

                elif player_total < dealer_total:
                    result = f"{hand_label} lost **{bet:,} gold**"
                    record_game_result(player_id, "loss", -bet)
                    update_biggest_loss(player_id, bet)

                else:
                    result = f"{hand_label} push"
                    record_game_result(player_id, "push", 0)

                result = add_achievement_text(player_id, result)
                text += f"<@{player_id}>: **{result}**\n"

        return text

    async def advance_turn_or_finish(self, interaction):
        while self.current_index < len(self.turns) - 1:
            self.current_index += 1

            if hand_value(self.current_hand()) <= 21:
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

        player_id, hand_index = self.current_turn()

        self.has_acted[player_id][hand_index] = True
        self.player_hands[player_id][hand_index].append(self.deck.draw())

        if hand_value(self.player_hands[player_id][hand_index]) > 21:
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

        player_id, hand_index = self.current_turn()
        self.has_acted[player_id][hand_index] = True

        await self.advance_turn_or_finish(interaction)

    @discord.ui.button(label="Double", emoji="💰", style=discord.ButtonStyle.red)
    async def double(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.current_player_id():
            await interaction.response.send_message(
                "It is not your turn.",
                ephemeral=True
            )
            return

        player_id, hand_index = self.current_turn()

        if self.has_acted[player_id][hand_index]:
            await interaction.response.send_message(
                "You can only double before taking another action.",
                ephemeral=True
            )
            return

        current_bet = self.player_bets[player_id][hand_index]
        balance = get_balance(player_id)

        if balance < current_bet * 2:
            await interaction.response.send_message(
                "You do not have enough gold to double down.",
                ephemeral=True
            )
            return

        self.player_bets[player_id][hand_index] = current_bet * 2
        record_double(player_id)

        self.has_acted[player_id][hand_index] = True
        self.player_hands[player_id][hand_index].append(self.deck.draw())

        await self.advance_turn_or_finish(interaction)

    @discord.ui.button(label="Split", emoji="✂️", style=discord.ButtonStyle.secondary)
    async def split(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.current_player_id():
            await interaction.response.send_message(
                "It is not your turn.",
                ephemeral=True
            )
            return

        if not self.can_split_current_hand():
            await interaction.response.send_message(
                "You can only split when your first two cards are the same rank.",
                ephemeral=True
            )
            return

        player_id, hand_index = self.current_turn()
        current_bet = self.player_bets[player_id][hand_index]
        balance = get_balance(player_id)

        if balance < current_bet * 2:
            await interaction.response.send_message(
                "You do not have enough gold to split this hand.",
                ephemeral=True
            )
            return

        original_hand = self.player_hands[player_id][0]

        hand_one = [original_hand[0], self.deck.draw()]
        hand_two = [original_hand[1], self.deck.draw()]

        self.player_hands[player_id] = [hand_one, hand_two]
        self.player_bets[player_id] = [current_bet, current_bet]
        self.has_acted[player_id] = [False, False]

        record_wager(player_id, current_bet)

        # Add second split hand right after current hand
        self.turns.insert(self.current_index + 1, (player_id, 1))

        await interaction.response.edit_message(
            embed=self.build_embed(),
            view=self
        )

class BlackjackTableView(discord.ui.View):
    def __init__(self, host_id, bet):
        super().__init__(timeout=None)
        self.host_id = host_id
        self.players = [host_id]
        self.bet = bet

    def build_table_embed(self):
        player_list = "\n".join([f"- <@{player_id}>" for player_id in self.players])

        if TROPHY_ID in self.players:
            player_list += (
                "\n\n🎰 **THE INSPIRATION OF THE TAVERN HAS ARRIVED** 🎰\n"
                "This entire establishment is technically his fault."
            )

        if FOUNDER_ID in self.players:
            player_list += (
                "\n\n👑 **THE CREATOR OF THE TAVERN HAS ARRIVED** 👑\n"
                "All complaints may be directed to management."
            )

        return discord.Embed(
            title="🃏 Blackjack Table",
            description=(
                f"**Bet:** {self.bet:,} gold\n\n"
                f"**Players:**\n{player_list}\n\n"
                "Click **Join Table** to sit down.\n"
                "Host can click **Start Game** when ready."
            ),
            color=discord.Color.dark_gold()
        )

    @discord.ui.button(label="Join Table", emoji="🍺", style=discord.ButtonStyle.green)
    async def join_table(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id in self.players:
            await interaction.response.send_message(
                "You are already sitting at this table.",
                ephemeral=True
            )
            return

        if get_balance(interaction.user.id) < self.bet:
            await interaction.response.send_message(
                f"You need at least **{self.bet:,} gold** to join this table.",
                ephemeral=True
            )
            return

        self.players.append(interaction.user.id)

        await interaction.response.edit_message(
            embed=self.build_table_embed(),
            view=self
        )

    @discord.ui.button(label="Start Game", emoji="▶️", style=discord.ButtonStyle.blurple)
    async def start_game(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.host_id:
            await interaction.response.send_message(
                "Only the table host can start the game.",
                ephemeral=True
            )
            return

        for player_id in self.players:
            if get_balance(player_id) < self.bet:
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
            record_wager(player_id, self.bet)

            if len(player_hands[player_id]) == 2 and hand_value(player_hands[player_id]) == 21:
                record_blackjack(player_id)

        game_view = BlackjackGameView(deck, dealer_hand, player_hands, self.players, self.bet)

        await interaction.response.edit_message(
            embed=game_view.build_embed(),
            view=game_view
        )


class DiceTableView(discord.ui.View):
    def __init__(self, host_id, bet):
        super().__init__(timeout=None)
        self.host_id = host_id
        self.players = [host_id]
        self.bot_added = False
        self.bet = bet

    def build_table_embed(self):
        player_list = "\n".join([f"- <@{player_id}>" for player_id in self.players])

        if self.bot_added:
            player_list += "\n- 🤖 Tavern Bot"

        if TROPHY_ID in self.players:
            player_list += (
                "\n\n🎰 **THE INSPIRATION OF THE TAVERN HAS ARRIVED** 🎰\n"
                "This entire establishment is technically his fault."
            )

        if FOUNDER_ID in self.players:
            player_list += (
                "\n\n👑 **THE CREATOR OF THE TAVERN HAS ARRIVED** 👑\n"
                "All complaints may be directed to management."
            )

        return discord.Embed(
            title="🎲 Dice Table",
            description=(
                f"**Bet:** {self.bet:,} gold\n\n"
                f"**Players:**\n{player_list}\n\n"
                "Highest roll wins."
            ),
            color=discord.Color.dark_gold()
        )

    @discord.ui.button(label="Join Dice", emoji="🎲", style=discord.ButtonStyle.green)
    async def join_dice(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id in self.players:
            await interaction.response.send_message(
                "You already joined this dice table.",
                ephemeral=True
            )
            return

        if get_balance(interaction.user.id) < self.bet:
            await interaction.response.send_message(
                f"You need at least **{self.bet:,} gold** to join.",
                ephemeral=True
            )
            return

        self.players.append(interaction.user.id)

        await interaction.response.edit_message(
            embed=self.build_table_embed(),
            view=self
        )

    @discord.ui.button(label="Add Bot", emoji="🤖", style=discord.ButtonStyle.blurple)
    async def add_bot(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.host_id:
            await interaction.response.send_message(
                "Only the host can add the bot.",
                ephemeral=True
            )
            return

        if self.bot_added:
            await interaction.response.send_message(
                "Bot player is already at the table.",
                ephemeral=True
            )
            return

        self.bot_added = True

        await interaction.response.edit_message(
            embed=self.build_table_embed(),
            view=self
        )

    @discord.ui.button(label="Roll Dice", emoji="🎲", style=discord.ButtonStyle.red)
    async def roll_dice(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.host_id:
            await interaction.response.send_message(
                "Only the host can roll.",
                ephemeral=True
            )
            return

        if len(self.players) < 2 and not self.bot_added:
            await interaction.response.send_message(
                "🎲 You need at least **one opponent** or the **bot player** before rolling.",
                ephemeral=True
            )
            return

        for player_id in self.players:
            if get_balance(player_id) < self.bet:
                await interaction.response.send_message(
                    f"<@{player_id}> does not have enough gold to roll.",
                    ephemeral=True
                )
                return

        for player_id in self.players:
            record_wager(player_id, self.bet)

        rolls = {}

        for player_id in self.players:
            rolls[player_id] = random.randint(1, 6)

        bot_roll = None
        if self.bot_added:
            bot_roll = random.randint(1, 6)

        all_rolls = list(rolls.values())
        if bot_roll is not None:
            all_rolls.append(bot_roll)

        highest = max(all_rolls)

        human_winners = [
            player_id for player_id, roll in rolls.items()
            if roll == highest
        ]

        bot_wins = self.bot_added and bot_roll == highest

        description = f"**Bet:** {self.bet:,} gold\n\n**Rolls:**\n"

        for player_id, roll in rolls.items():
            description += f"<@{player_id}> rolled **{roll}**\n"

        if self.bot_added:
            description += f"🤖 Tavern Bot rolled **{bot_roll}**\n"

        description += "\n**Results:**\n"

        pot = len(self.players) * self.bet

        if self.bot_added:
            pot += self.bet

        if bot_wins and not human_winners:
            for player_id in self.players:
                record_game_result(player_id, "loss", -self.bet)
                update_biggest_loss(player_id, self.bet)
                result = f"Lost **{self.bet:,} gold**"
                result = add_achievement_text(player_id, result)
                description += f"<@{player_id}>: **{result}**\n"

            description += f"\n🤖 Tavern Bot takes the **{pot:,} gold** pot."

        elif len(human_winners) == 1 and not bot_wins:
            winner = human_winners[0]
            winnings = pot - self.bet

            for player_id in self.players:
                if player_id == winner:
                    record_game_result(player_id, "win", winnings)
                    update_biggest_win(player_id, winnings)
                    result = f"Won the **{pot:,} gold** pot! Net gain: **{winnings:,} gold**"
                else:
                    record_game_result(player_id, "loss", -self.bet)
                    update_biggest_loss(player_id, self.bet)
                    result = f"Lost **{self.bet:,} gold**"

                result = add_achievement_text(player_id, result)
                description += f"<@{player_id}>: **{result}**\n"

        else:
            for player_id in self.players:
                record_game_result(player_id, "push", 0)
                result = "Push"
                result = add_achievement_text(player_id, result)
                description += f"<@{player_id}>: **{result}**\n"

            description += f"\nTie! The **{pot:,} gold** pot is pushed."

        embed = discord.Embed(
            title="🎲 Dice Game",
            description=description,
            color=discord.Color.dark_gold()
        )

        await interaction.response.edit_message(embed=embed, view=None)

class BetModal(discord.ui.Modal):
    def __init__(self, game_type):
        super().__init__(title=f"Create {game_type} Table")
        self.game_type = game_type

    amount = discord.ui.TextInput(
        label="Bet amount",
        placeholder="Example: 100",
        required=True,
        max_length=10
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            bet = int(self.amount.value)
        except ValueError:
            await interaction.response.send_message(
                "Enter a valid number.",
                ephemeral=True
            )
            return

        if bet <= 0:
            await interaction.response.send_message(
                "Bet must be greater than 0.",
                ephemeral=True
            )
            return

        if get_balance(interaction.user.id) < bet:
            await interaction.response.send_message(
                f"You need at least **{bet:,} gold** to create this table.",
                ephemeral=True
            )
            return

        if self.game_type == "Blackjack":
            table_view = BlackjackTableView(
                host_id=interaction.user.id,
                bet=bet
            )

            await interaction.response.send_message(
                embed=table_view.build_table_embed(),
                view=table_view
            )

        elif self.game_type == "Dice":
            table_view = DiceTableView(
                host_id=interaction.user.id,
                bet=bet
            )

            await interaction.response.send_message(
                embed=table_view.build_table_embed(),
                view=table_view
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

    @discord.ui.button(label="Profile", emoji="👤", style=discord.ButtonStyle.secondary)
    async def profile_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await send_profile(interaction, interaction.user)


    @discord.ui.button(label="Blackjack", emoji="🃏", style=discord.ButtonStyle.red)
    async def blackjack_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(BetModal("Blackjack"))
      
    @discord.ui.button(label="Dice", emoji="🎲", style=discord.ButtonStyle.green)
    async def dice_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(BetModal("Dice"))

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

async def send_profile(interaction, target_user):
    profile = get_profile(target_user.id)

    if profile is None:
        get_or_create_player(target_user.id)
        profile = get_profile(target_user.id)

    (
        balance,
        wins,
        losses,
        games_played,
        pushes,
        blackjacks,
        doubles,
        biggest_win,
        biggest_loss,
        total_wagered,
        title
    ) = profile

    win_rate = 0
    if games_played > 0:
        win_rate = (wins / games_played) * 100

    earned_achievements = get_player_achievements(target_user.id)

    if earned_achievements:
        achievement_text = "\n".join(
            [
                ACHIEVEMENTS.get(
                    achievement_id,
                    {"name": achievement_id}
                )["name"]
                for achievement_id, date_earned in earned_achievements[:10]
            ]
        )
    else:
        achievement_text = "No achievements yet. Go make questionable choices."

    embed = discord.Embed(
        title=f"👤 {target_user.display_name}'s Tavern Profile",
        description=f"**Title:** {title}",
        color=discord.Color.gold()
    )

    embed.add_field(name="💰 Gold", value=f"{balance:,}", inline=True)
    embed.add_field(name="🎮 Games", value=f"{games_played:,}", inline=True)
    embed.add_field(name="📊 Win Rate", value=f"{win_rate:.1f}%", inline=True)

    embed.add_field(
        name="🏆 Record",
        value=(
            f"Wins: **{wins:,}**\n"
            f"Losses: **{losses:,}**\n"
            f"Pushes: **{pushes:,}**"
        ),
        inline=True
    )

    embed.add_field(
        name="🃏 Blackjack Stats",
        value=(
            f"Blackjacks: **{blackjacks:,}**\n"
            f"Doubles: **{doubles:,}**"
        ),
        inline=True
    )

    embed.add_field(
        name="💸 Wager Stats",
        value=(
            f"Total Wagered: **{total_wagered:,}**\n"
            f"Biggest Win: **{biggest_win:,}**\n"
            f"Biggest Loss: **{biggest_loss:,}**"
        ),
        inline=False
    )

    embed.add_field(
        name="🎖 Achievements",
        value=achievement_text,
        inline=False
    )

    await interaction.response.send_message(embed=embed, ephemeral=True)

class Tavern(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    @app_commands.command(name="profile", description="View a Tavern profile")
    @app_commands.describe(user="Player to view")
    async def profile(self, interaction: discord.Interaction, user: Optional[discord.User] = None):
        if not is_tavern_channel(interaction):
            await interaction.response.send_message(
                "🍺 TrophyBot only runs in **The Tavern**.",
                ephemeral=True
            )
            return

        target = user or interaction.user
        await send_profile(interaction, target)
    
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
                "👤 Profile\n"
                "🃏 Blackjack\n"
                "🎲 Dice\n"
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
