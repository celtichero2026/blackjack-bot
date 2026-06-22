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
    record_game_stat,
    get_profile,
    get_player_achievements,
    add_xp,
    get_level_info,
    record_wager,
    record_double,
    record_blackjack,
    update_biggest_win,
    update_biggest_loss,
    adjust_gold,
    add_gold,
    add_inventory_item,
    player_owns_item,
    get_player_titles,
    set_player_title,
    add_inventory_quantity,
    consume_inventory_item,
    get_inventory_by_type,
    record_mischief_hit,
    get_mischief_stats,
)
from games.blackjack_engine import Deck, hand_value
from achievement_service import check_achievements
from achievements import ACHIEVEMENTS


TROPHY_ID = 875349215876894720
FOUNDER_ID = 502268158749573132
BASE_BET = 100
DEFAULT_TITLE = "🍺 Tavern Newbie"

TITLE_ITEMS = {
    "gold_hoarder": {
        "name": "💰 Gold Hoarder",
        "price": 5000,
    },
    "dice_goblin": {
        "name": "🎲 Dice Goblin",
        "price": 10000,
    },
    "card_shark": {
        "name": "🃏 Card Shark",
        "price": 25000,
    },
    "high_roller": {
        "name": "🎖 High Roller",
        "price": 50000,
    },
    "tavern_royalty": {
        "name": "👑 Tavern Royalty",
        "price": 100000,
    },
}



CONFETTI_DUD_GIF = "PUT_YOUR_CONFETTI_GIF_URL_HERE"

MISCHIEF_ITEMS = {
    "rotten_tomato": {
        "name": "🍅 Rotten Tomato",
        "price": 250,
    },
    "cream_pie": {
        "name": "🥧 Cream Pie",
        "price": 500,
    },
    "mystery_box": {
        "name": "🎁 Mystery Box",
        "price": 1000,
    },
}

def is_tavern_channel(interaction):
    return interaction.channel_id == TAVERN_CHANNEL_ID


def format_hand(hand):
    return " ".join([f"{card[0]}{card[1]}" for card in hand])


def progress_bar(current, needed, size=10):
    if needed <= 0:
        return "▰" * size

    filled = int((current / needed) * size)
    filled = max(0, min(size, filled))

    return "▰" * filled + "▱" * (size - filled)


def add_achievement_text(player_id, result):
    new_achievements = check_achievements(player_id)

    if new_achievements:
        result += (
            "\n🏆 Achievement Unlocked:\n"
            + "\n".join(new_achievements)
        )

    return result


def xp_result_text(xp_info):
    if not xp_info:
        return ""

    bar = progress_bar(xp_info["xp_current"], xp_info["xp_needed"])

    return (
        f"\n⭐ **+{xp_info['xp_gained']} XP**"
        f"\n{bar} **{xp_info['xp_current']}/{xp_info['xp_needed']} XP**"
    )


async def send_level_up_messages(interaction, level_ups):
    for player_id, xp_info in level_ups:
        if not xp_info or not xp_info["level_up"]:
            continue

        embed = discord.Embed(
            title="⭐ LEVEL UP!",
            description=(
                f"<@{player_id}> reached **Level {xp_info['new_level']}**!\n\n"
                f"Total XP: **{xp_info['new_xp']:,}**"
            ),
            color=discord.Color.gold()
        )

        await interaction.followup.send(embed=embed)
        
def get_active_title(user_id):
    profile = get_profile(user_id)

    if profile and profile[10]:
        return profile[10]

    return DEFAULT_TITLE


def format_table_player(player_id):
    title = get_active_title(player_id)
    return f"- <@{player_id}> — {title}"


def get_owned_mischief_items(user_id):
    rows = get_inventory_by_type(user_id, "mischief")

    owned = []

    for item_id, quantity in rows:
        if item_id in MISCHIEF_ITEMS and quantity > 0:
            owned.append((item_id, quantity))

    return owned


def get_mischief_bonus_line(item_id):
    if random.random() > 0.05:
        return ""

    if item_id == "rotten_tomato":
        return "\n\n💦 Oof, that one was extra juicy."

    if item_id == "cream_pie":
        return random.choice([
            "\n\n😳 The Tavern will not be commenting on where the whipped cream ended up.",
            "\n\n🫣 That pie hit dangerously close to HR territory.",
            "\n\n🥴 Someone get a towel. Actually... get two.",
            "\n\n😏 That was a very questionable use of dairy.",
            "\n\n🍰 The pie was consensual. The cleanup was not.",
        ])

    return ""


def build_mischief_result_embed(attacker, target, item_id):
    if item_id == "rotten_tomato":
        description = (
            f"**{attacker.display_name}** launched a rotten tomato at "
            f"**{target.display_name}**."
        )
        description += get_mischief_bonus_line(item_id)

        embed = discord.Embed(
            title="🍅 Rotten Tomato!",
            description=description,
            color=discord.Color.red()
        )
        embed.set_thumbnail(url=target.display_avatar.url)
        return embed

    if item_id == "cream_pie":
        description = (
            f"**{attacker.display_name}** hit **{target.display_name}** "
            "with a cream pie."
        )
        description += get_mischief_bonus_line(item_id)

        embed = discord.Embed(
            title="🥧 Cream Pie!",
            description=description,
            color=discord.Color.gold()
        )
        embed.set_thumbnail(url=target.display_avatar.url)
        return embed

    embed = discord.Embed(
        title="🎭 Mischief!",
        description="Something questionable happened.",
        color=discord.Color.gold()
    )
    return embed


def build_mystery_box_embed(attacker, target):
    outcome = random.choices(
        ["rotten_tomato", "cream_pie", "backfire", "confetti"],
        weights=[35, 35, 15, 15],
        k=1
    )[0]

    if outcome in ["rotten_tomato", "cream_pie"]:
        record_mischief_hit(attacker.id, target.id, outcome)
        return build_mischief_result_embed(attacker, target, outcome)

    if outcome == "backfire":
        embed = discord.Embed(
            title="💥 Mystery Box Backfire!",
            description=(
                f"**{attacker.display_name}** opened the Mystery Box...\n\n"
                "It immediately exploded in their face."
            ),
            color=discord.Color.dark_red()
        )
        embed.set_thumbnail(url=attacker.display_avatar.url)
        return embed

    embed = discord.Embed(
        title="✨ Confetti Dud!",
        description=(
            f"**{attacker.display_name}** opened the Mystery Box...\n\n"
            "A sad little puff of confetti fell out. That was it."
        ),
        color=discord.Color.light_grey()
    )

    if CONFETTI_DUD_GIF != "PUT_YOUR_CONFETTI_GIF_URL_HERE":
        embed.set_image(url=CONFETTI_DUD_GIF)

    return embed


async def send_usable_inventory_menu(interaction, allowed_target_ids=None):
    owned_items = get_owned_mischief_items(interaction.user.id)

    if not owned_items:
        await interaction.response.send_message(
            "🎭 You do not have any usable consumables yet.\n\n"
            "Buy some from the **Mischief Market** first.\n"
            "Sounds will be added here later.",
            ephemeral=True
        )
        return

    embed = discord.Embed(
        title="🎭 Use a Consumable",
        description=(
            "Choose a consumable from your inventory.\n\n"
            "Sounds will be added here later."
        ),
        color=discord.Color.gold()
    )

    await interaction.response.send_message(
        embed=embed,
        view=UseConsumableSelectView(
            owner_id=interaction.user.id,
            allowed_target_ids=allowed_target_ids
        ),
        ephemeral=True
    )


class BlackjackGameView(discord.ui.View):
    def __init__(self, deck, dealer_hand, player_hands, players, bet):
        super().__init__(timeout=None)
        self.deck = deck
        self.dealer_hand = dealer_hand
        self.players = players
        self.bet = bet
        self.level_ups = []

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

        self.turns = [
            (player_id, 0)
            for player_id in players
        ]

        self.current_index = 0

    async def on_error(self, interaction, error, item):
        import traceback
        traceback.print_exception(type(error), error, error.__traceback__)

        if not interaction.response.is_done():
            await interaction.response.send_message(
                f"Blackjack error: `{error}`",
                ephemeral=True
            )

    def award_xp(self, player_id, amount):
        xp_info = add_xp(player_id, amount)

        if xp_info and xp_info.get("level_up"):
            self.level_ups.append((player_id, xp_info))

        return xp_info

    def current_turn(self):
        return self.turns[self.current_index]

    def current_player_id(self):
        player_id, hand_index = self.current_turn()
        return player_id

    def current_hand(self):
        player_id, hand_index = self.current_turn()
        return self.player_hands[player_id][hand_index]

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
        achievement_checked = set()
        self.level_ups = []

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
                    record_game_stat(player_id, "loss")
                    xp_info = self.award_xp(player_id, 10)
                    result += xp_result_text(xp_info)
                    update_biggest_loss(player_id, bet)

                elif dealer_total > 21:
                    payout = bet * 2
                    adjust_gold(player_id, payout)
                    result = f"{hand_label} dealer bust — won **{bet:,} gold**"
                    record_game_stat(player_id, "win")
                    xp_info = self.award_xp(player_id, 25)
                    result += xp_result_text(xp_info)
                    update_biggest_win(player_id, bet)

                elif player_total > dealer_total:
                    payout = bet * 2
                    adjust_gold(player_id, payout)
                    result = f"{hand_label} won **{bet:,} gold**"
                    record_game_stat(player_id, "win")
                    xp_info = self.award_xp(player_id, 25)
                    result += xp_result_text(xp_info)
                    update_biggest_win(player_id, bet)

                elif player_total < dealer_total:
                    result = f"{hand_label} lost **{bet:,} gold**"
                    record_game_stat(player_id, "loss")
                    xp_info = self.award_xp(player_id, 10)
                    result += xp_result_text(xp_info)
                    update_biggest_loss(player_id, bet)

                else:
                    adjust_gold(player_id, bet)
                    result = f"{hand_label} push"
                    record_game_stat(player_id, "push")
                    xp_info = self.award_xp(player_id, 5)
                    result += xp_result_text(xp_info)

                if player_id not in achievement_checked:
                    result = add_achievement_text(player_id, result)
                    achievement_checked.add(player_id)

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
            view=PlayAgainView("Blackjack")
        )

        await send_level_up_messages(interaction, self.level_ups)

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

        if balance < current_bet:
            await interaction.response.send_message(
                "You do not have enough gold to double down.",
                ephemeral=True
            )
            return

        adjust_gold(player_id, -current_bet)
        record_wager(player_id, current_bet)

        self.player_bets[player_id][hand_index] = current_bet * 2
        record_double(player_id)
        self.award_xp(player_id, 5)

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

        if balance < current_bet:
            await interaction.response.send_message(
                "You do not have enough gold to split this hand.",
                ephemeral=True
            )
            return

        adjust_gold(player_id, -current_bet)
        record_wager(player_id, current_bet)
        self.award_xp(player_id, 5)

        original_hand = self.player_hands[player_id][0]

        hand_one = [original_hand[0], self.deck.draw()]
        hand_two = [original_hand[1], self.deck.draw()]

        self.player_hands[player_id] = [hand_one, hand_two]
        self.player_bets[player_id] = [current_bet, current_bet]
        self.has_acted[player_id] = [False, False]

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

    async def on_error(self, interaction, error, item):
        import traceback
        traceback.print_exception(type(error), error, error.__traceback__)

        if not interaction.response.is_done():
            await interaction.response.send_message(
                f"Blackjack table error: `{error}`",
                ephemeral=True
            )

    def build_table_embed(self):
        player_list = "\n".join(
            [format_table_player(player_id) for player_id in self.players]
        )

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


    @discord.ui.button(label="Use Consumable", emoji="🎭", style=discord.ButtonStyle.secondary)
    async def use_consumable_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await send_usable_inventory_menu(
            interaction,
            allowed_target_ids=self.players
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
            adjust_gold(player_id, -self.bet)
            record_wager(player_id, self.bet)

            player_hands[player_id] = [deck.draw(), deck.draw()]

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

    async def on_error(self, interaction, error, item):
        import traceback
        traceback.print_exception(type(error), error, error.__traceback__)

        if not interaction.response.is_done():
            await interaction.response.send_message(
                f"Dice error: `{error}`",
                ephemeral=True
            )

    def award_xp(self, player_id, amount, level_ups):
        xp_info = add_xp(player_id, amount)

        if xp_info and xp_info.get("level_up"):
            level_ups.append((player_id, xp_info))

        return xp_info

    def build_table_embed(self):
        player_list = "\n".join(
            [format_table_player(player_id) for player_id in self.players]
        )

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


    @discord.ui.button(label="Use Consumable", emoji="🎭", style=discord.ButtonStyle.secondary)
    async def use_consumable_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await send_usable_inventory_menu(
            interaction,
            allowed_target_ids=self.players
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

        level_ups = []

        if bot_wins and not human_winners:
            for player_id in self.players:
                record_game_result(player_id, "loss", -self.bet)
                xp_info = self.award_xp(player_id, 10, level_ups)
                update_biggest_loss(player_id, self.bet)

                result = f"Lost **{self.bet:,} gold**"
                result += xp_result_text(xp_info)
                result = add_achievement_text(player_id, result)

                description += f"<@{player_id}>: **{result}**\n"

            description += f"\n🤖 Tavern Bot takes the **{pot:,} gold** pot."

        elif len(human_winners) == 1 and not bot_wins:
            winner = human_winners[0]
            winnings = pot - self.bet

            for player_id in self.players:
                if player_id == winner:
                    record_game_result(player_id, "win", winnings)
                    xp_info = self.award_xp(player_id, 25, level_ups)
                    update_biggest_win(player_id, winnings)

                    result = (
                        f"Won the **{pot:,} gold** pot! "
                        f"Net gain: **{winnings:,} gold**"
                    )
                    result += xp_result_text(xp_info)

                else:
                    record_game_result(player_id, "loss", -self.bet)
                    xp_info = self.award_xp(player_id, 10, level_ups)
                    update_biggest_loss(player_id, self.bet)

                    result = f"Lost **{self.bet:,} gold**"
                    result += xp_result_text(xp_info)

                result = add_achievement_text(player_id, result)
                description += f"<@{player_id}>: **{result}**\n"

        else:
            for player_id in self.players:
                record_game_result(player_id, "push", 0)
                xp_info = self.award_xp(player_id, 5, level_ups)

                result = "Push"
                result += xp_result_text(xp_info)
                result = add_achievement_text(player_id, result)

                description += f"<@{player_id}>: **{result}**\n"

            description += f"\nTie! The **{pot:,} gold** pot is pushed."

        embed = discord.Embed(
            title="🎲 Dice Game",
            description=description,
            color=discord.Color.dark_gold()
        )

        await interaction.response.edit_message(
            embed=embed,
            view=PlayAgainView("Dice")
        )
        await send_level_up_messages(interaction, level_ups)

class PlayAgainView(discord.ui.View):
    def __init__(self, game_type):
        super().__init__(timeout=180)
        self.game_type = game_type

    @discord.ui.button(label="Play Again", emoji="🔁", style=discord.ButtonStyle.green)
    async def play_again_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(BetModal(self.game_type))

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
    @discord.ui.button(label="Shop", emoji="🏪", style=discord.ButtonStyle.gray)
    async def shop_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            embed=build_shop_embed(interaction.user.id),
            view=ShopView(interaction.user.id),
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
        title,
        xp
    ) = profile

    level, xp_current, xp_needed = get_level_info(xp)
    bar = progress_bar(xp_current, xp_needed)

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
        name="⭐ Progress",
        value=(
            f"Level: **{level}**\n"
            f"{bar} **{xp_current}/{xp_needed} XP**\n"
            f"Total XP: **{xp:,}**"
        ),
        inline=True
    )

    tomatoes_thrown, tomatoes_taken, pies_thrown, pies_taken = get_mischief_stats(target_user.id)

    embed.add_field(
        name="🎭 Mischief",
        value=(
            f"🍅 Thrown: **{tomatoes_thrown:,}** | Taken: **{tomatoes_taken:,}**\n"
            f"🥧 Thrown: **{pies_thrown:,}** | Taken: **{pies_taken:,}**"
        ),
        inline=False
    )

    embed.add_field(
        name="🎖 Achievements",
        value=achievement_text,
        inline=False
    )

    await interaction.response.send_message(embed=embed, ephemeral=True)

def build_shop_embed(user_id):
    balance = get_balance(user_id)

    profile = get_profile(user_id)

    active_title = "🍺 Tavern Newbie"

    if profile:
        active_title = profile[10]

    embed = discord.Embed(
        title="🏪 The Tavern Shop",
        description=(
            f"💰 Gold: **{balance:,}**\n\n"
            f"🎖 Active Title:\n"
            f"{active_title}\n\n"
            "Spend your questionable winnings on things you probably do not need."
        ),
        color=discord.Color.gold()
    )

    embed.set_footer(
        text="No refunds. The Tavern is not responsible for poor decisions."
    )

    return embed
    
class ShopView(discord.ui.View):
    def __init__(self, owner_id):
        super().__init__(timeout=180)
        self.owner_id = owner_id

    async def interaction_check(self, interaction):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message(
                "This shop menu belongs to someone else. Use `/shop` to open your own.",
                ephemeral=True
            )
            return False

        return True

    @discord.ui.button(label="Mischief", emoji="🎭", style=discord.ButtonStyle.red)
    async def mischief_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(
            content=None,
            embed=build_mischief_market_embed(self.owner_id),
            view=MischiefMarketView(self.owner_id)
        )

    @discord.ui.button(label="Titles", emoji="🎖", style=discord.ButtonStyle.blurple)
    async def titles_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(
            content=None,
            embed=build_titles_embed(self.owner_id),
            view=TitleShopView(self.owner_id)
        )

    @discord.ui.button(label="Sticker Packs", emoji="📦", style=discord.ButtonStyle.green)
    async def sticker_packs_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(
            content=None,
            embed=discord.Embed(
                title="📦 Sticker Packs",
                description="Sticker packs are coming soon.",
                color=discord.Color.gold()
            ),
            view=ShopBackView(self.owner_id)
        )

    @discord.ui.button(label="Sounds", emoji="🔊", style=discord.ButtonStyle.gray)
    async def sounds_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(
            content=None,
            embed=discord.Embed(
                title="🔊 Sound Shop",
                description="Sound collection is coming soon.",
                color=discord.Color.gold()
            ),
            view=ShopBackView(self.owner_id)
        )


class ShopBackView(discord.ui.View):
    def __init__(self, owner_id):
        super().__init__(timeout=180)
        self.owner_id = owner_id

    async def interaction_check(self, interaction):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message(
                "This shop menu belongs to someone else. Use `/shop` to open your own.",
                ephemeral=True
            )
            return False

        return True

    @discord.ui.button(label="Back to Shop", emoji="⬅️", style=discord.ButtonStyle.secondary)
    async def back_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(
            content=None,
            embed=build_shop_embed(self.owner_id),
            view=ShopView(self.owner_id)
        )


def build_mischief_market_embed(user_id):
    balance = get_balance(user_id)
    owned_items = get_owned_mischief_items(user_id)

    owned_lines = []

    for item_id, quantity in owned_items:
        item = MISCHIEF_ITEMS.get(item_id)
        if item:
            owned_lines.append(f"{item['name']} x{quantity}")

    owned_text = "\n".join(owned_lines) if owned_lines else "No mischief items owned yet."

    shop_lines = []

    for item_id, item in MISCHIEF_ITEMS.items():
        shop_lines.append(f"{item['name']} — {item['price']:,} gold")

    embed = discord.Embed(
        title="🎭 Mischief Market",
        description=(
            f"💰 Gold: **{balance:,}**\n\n"
            f"**For Sale:**\n"
            f"{chr(10).join(shop_lines)}\n\n"
            f"**Your Mischief:**\n"
            f"{owned_text}"
        ),
        color=discord.Color.gold()
    )

    embed.set_footer(text="Buy mischief, then use it on someone.")
    return embed


def build_buy_mischief_embed(user_id):
    balance = get_balance(user_id)

    lines = []

    for item_id, item in MISCHIEF_ITEMS.items():
        lines.append(f"{item['name']} — {item['price']:,} gold")

    embed = discord.Embed(
        title="💰 Buy Mischief",
        description=(
            f"💰 Gold: **{balance:,}**\n\n"
            f"{chr(10).join(lines)}\n\n"
            "Choose an item from the dropdown below."
        ),
        color=discord.Color.gold()
    )

    return embed


def build_use_mischief_embed(user_id):
    owned_items = get_owned_mischief_items(user_id)

    lines = []

    for item_id, quantity in owned_items:
        item = MISCHIEF_ITEMS.get(item_id)
        if item:
            lines.append(f"{item['name']} x{quantity}")

    owned_text = "\n".join(lines) if lines else "No usable mischief items owned."

    embed = discord.Embed(
        title="🎭 Use Mischief",
        description=(
            f"**Your Consumables:**\n"
            f"{owned_text}\n\n"
            "Choose an item, then pick a target."
        ),
        color=discord.Color.gold()
    )

    return embed


class MischiefMarketView(discord.ui.View):
    def __init__(self, owner_id):
        super().__init__(timeout=180)
        self.owner_id = owner_id

    async def interaction_check(self, interaction):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message(
                "This Mischief Market belongs to someone else. Use `/shop` to open your own.",
                ephemeral=True
            )
            return False

        return True

    @discord.ui.button(label="Buy Mischief", emoji="💰", style=discord.ButtonStyle.green)
    async def buy_mischief_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(
            content=None,
            embed=build_buy_mischief_embed(self.owner_id),
            view=BuyMischiefSelectView(self.owner_id)
        )

    @discord.ui.button(label="Use Mischief", emoji="🎭", style=discord.ButtonStyle.blurple)
    async def use_mischief_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        owned_items = get_owned_mischief_items(self.owner_id)

        if not owned_items:
            embed = build_mischief_market_embed(self.owner_id)
            embed.set_footer(text="You do not own any mischief items yet.")

            await interaction.response.edit_message(
                content=None,
                embed=embed,
                view=MischiefMarketView(self.owner_id)
            )
            return

        await interaction.response.edit_message(
            content=None,
            embed=build_use_mischief_embed(self.owner_id),
            view=UseConsumableSelectView(self.owner_id)
        )

    @discord.ui.button(label="Back to Shop", emoji="⬅️", style=discord.ButtonStyle.secondary)
    async def back_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(
            content=None,
            embed=build_shop_embed(self.owner_id),
            view=ShopView(self.owner_id)
        )


class BuyMischiefSelect(discord.ui.Select):
    def __init__(self, owner_id):
        self.owner_id = owner_id

        options = []

        for item_id, item in MISCHIEF_ITEMS.items():
            options.append(
                discord.SelectOption(
                    label=item["name"],
                    description=f"{item['price']:,} gold",
                    value=item_id
                )
            )

        super().__init__(
            placeholder="Choose mischief to buy...",
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        item_id = self.values[0]
        item = MISCHIEF_ITEMS.get(item_id)

        if not item:
            await interaction.response.send_message(
                "That mischief item does not exist.",
                ephemeral=True
            )
            return

        price = item["price"]
        balance = get_balance(interaction.user.id)

        if balance < price:
            await interaction.response.send_message(
                f"You need **{price:,} gold** to buy {item['name']}.\n"
                f"Your balance is **{balance:,} gold**.",
                ephemeral=True
            )
            return

        add_gold(interaction.user.id, -price)

        date_acquired = datetime.now(timezone.utc).isoformat()

        add_inventory_quantity(
            interaction.user.id,
            item_id,
            "mischief",
            1,
            date_acquired
        )

        embed = build_mischief_market_embed(interaction.user.id)
        embed.set_footer(text=f"Purchased {item['name']} for {price:,} gold.")

        await interaction.response.edit_message(
            content=None,
            embed=embed,
            view=MischiefMarketView(interaction.user.id)
        )


class BuyMischiefSelectView(discord.ui.View):
    def __init__(self, owner_id):
        super().__init__(timeout=180)
        self.owner_id = owner_id

        self.add_item(BuyMischiefSelect(owner_id))

    async def interaction_check(self, interaction):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message(
                "This Mischief Market belongs to someone else. Use `/shop` to open your own.",
                ephemeral=True
            )
            return False

        return True

    @discord.ui.button(label="Back to Mischief", emoji="⬅️", style=discord.ButtonStyle.secondary)
    async def back_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(
            content=None,
            embed=build_mischief_market_embed(self.owner_id),
            view=MischiefMarketView(self.owner_id)
        )


class UseConsumableSelect(discord.ui.Select):
    def __init__(self, owner_id, allowed_target_ids=None):
        self.owner_id = owner_id
        self.allowed_target_ids = allowed_target_ids

        owned_items = get_owned_mischief_items(owner_id)

        options = []

        for item_id, quantity in owned_items:
            item = MISCHIEF_ITEMS.get(item_id)
            if not item:
                continue

            options.append(
                discord.SelectOption(
                    label=item["name"],
                    description=f"Owned: {quantity}",
                    value=item_id
                )
            )

        super().__init__(
            placeholder="Choose a consumable...",
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        item_id = self.values[0]
        item = MISCHIEF_ITEMS.get(item_id)

        if not item:
            await interaction.response.send_message(
                "That consumable does not exist.",
                ephemeral=True
            )
            return

        await interaction.response.edit_message(
            content=None,
            embed=discord.Embed(
                title="🎯 Pick a Target",
                description=(
                    f"Using: **{item['name']}**\n\n"
                    "Choose who gets the Tavern treatment."
                ),
                color=discord.Color.gold()
            ),
            view=UseConsumableTargetView(
                owner_id=interaction.user.id,
                item_id=item_id,
                allowed_target_ids=self.allowed_target_ids
            )
        )


class UseConsumableSelectView(discord.ui.View):
    def __init__(self, owner_id, allowed_target_ids=None):
        super().__init__(timeout=180)
        self.owner_id = owner_id
        self.allowed_target_ids = allowed_target_ids

        self.add_item(UseConsumableSelect(owner_id, allowed_target_ids))

    async def interaction_check(self, interaction):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message(
                "This consumable menu belongs to someone else.",
                ephemeral=True
            )
            return False

        return True

    @discord.ui.button(label="Back", emoji="⬅️", style=discord.ButtonStyle.secondary)
    async def back_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.allowed_target_ids is None:
            await interaction.response.edit_message(
                content=None,
                embed=build_mischief_market_embed(self.owner_id),
                view=MischiefMarketView(self.owner_id)
            )
        else:
            await interaction.response.edit_message(
                content=None,
                embed=discord.Embed(
                    title="🎭 Use a Consumable",
                    description="Choose a consumable from your inventory.",
                    color=discord.Color.gold()
                ),
                view=UseConsumableSelectView(
                    owner_id=self.owner_id,
                    allowed_target_ids=self.allowed_target_ids
                )
            )


class UseConsumableTargetSelect(discord.ui.UserSelect):
    def __init__(self, owner_id, item_id, allowed_target_ids=None):
        self.owner_id = owner_id
        self.item_id = item_id
        self.allowed_target_ids = allowed_target_ids

        super().__init__(
            placeholder="Choose a target...",
            min_values=1,
            max_values=1
        )

    async def callback(self, interaction: discord.Interaction):
        target = self.values[0]

        if self.allowed_target_ids is not None and target.id not in self.allowed_target_ids:
            await interaction.response.send_message(
                "That player is not sitting at this table.",
                ephemeral=True
            )
            return

        if target.bot:
            await interaction.response.send_message(
                "The Tavern Bot refuses to be bullied by its own customers.",
                ephemeral=True
            )
            return

        quantity_removed = consume_inventory_item(
            interaction.user.id,
            self.item_id,
            1
        )

        if not quantity_removed:
            await interaction.response.send_message(
                "You do not have that consumable anymore.",
                ephemeral=True
            )
            return

        if self.item_id == "mystery_box":
            embed = build_mystery_box_embed(interaction.user, target)
        else:
            record_mischief_hit(interaction.user.id, target.id, self.item_id)
            embed = build_mischief_result_embed(interaction.user, target, self.item_id)

        await interaction.response.send_message(
            "🎭 Mischief deployed.",
            ephemeral=True
        )

        await interaction.channel.send(embed=embed)


class UseConsumableTargetView(discord.ui.View):
    def __init__(self, owner_id, item_id, allowed_target_ids=None):
        super().__init__(timeout=180)
        self.owner_id = owner_id
        self.item_id = item_id
        self.allowed_target_ids = allowed_target_ids

        self.add_item(
            UseConsumableTargetSelect(
                owner_id,
                item_id,
                allowed_target_ids
            )
        )

    async def interaction_check(self, interaction):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message(
                "This target menu belongs to someone else.",
                ephemeral=True
            )
            return False

        return True

    @discord.ui.button(label="Back to Consumables", emoji="⬅️", style=discord.ButtonStyle.secondary)
    async def back_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(
            content=None,
            embed=build_use_mischief_embed(self.owner_id),
            view=UseConsumableSelectView(
                owner_id=self.owner_id,
                allowed_target_ids=self.allowed_target_ids
            )
        )


def build_titles_embed(user_id):
    balance = get_balance(user_id)
    profile = get_profile(user_id)

    active_title = DEFAULT_TITLE
    if profile:
        active_title = profile[10]

    owned_title_ids = get_player_titles(user_id)

    owned_titles = [DEFAULT_TITLE]

    for title_id in owned_title_ids:
        title = TITLE_ITEMS.get(title_id)
        if title:
            owned_titles.append(title["name"])

    owned_text = "\n".join(owned_titles)

    available_lines = []

    for title_id, title in TITLE_ITEMS.items():
        price = title["price"]
        name = title["name"]

        if title_id in owned_title_ids:
            available_lines.append(f"✅ {name} — Owned")
        else:
            available_lines.append(f"{name} — {price:,} gold")

    available_text = "\n".join(available_lines)

    embed = discord.Embed(
        title="🎖 Title Shop",
        description=(
            f"💰 Gold: **{balance:,}**\n\n"
            f"**Current Title:**\n"
            f"{active_title}\n\n"
            f"**Owned Titles:**\n"
            f"{owned_text}\n\n"
            f"**Available Titles:**\n"
            f"{available_text}"
        ),
        color=discord.Color.gold()
    )

    embed.set_footer(text="Buy a title, then equip it from your owned titles.")
    return embed


def build_buy_titles_embed(user_id):
    balance = get_balance(user_id)

    lines = []

    for title_id, title in TITLE_ITEMS.items():
        if player_owns_item(user_id, title_id):
            continue

        lines.append(f"{title['name']} — {title['price']:,} gold")

    available_text = "\n".join(lines)

    if not available_text:
        available_text = "You already own every title in the shop."

    embed = discord.Embed(
        title="💰 Buy a Title",
        description=(
            f"💰 Gold: **{balance:,}**\n\n"
            f"{available_text}\n\n"
            "Choose a title from the dropdown below."
        ),
        color=discord.Color.gold()
    )

    return embed


def build_equip_titles_embed(user_id):
    profile = get_profile(user_id)

    active_title = DEFAULT_TITLE
    if profile:
        active_title = profile[10]

    owned_title_ids = get_player_titles(user_id)

    owned_titles = [DEFAULT_TITLE]

    for title_id in owned_title_ids:
        title = TITLE_ITEMS.get(title_id)
        if title:
            owned_titles.append(title["name"])

    embed = discord.Embed(
        title="🎖 Equip a Title",
        description=(
            f"**Current Title:**\n"
            f"{active_title}\n\n"
            f"**Owned Titles:**\n"
            f"{chr(10).join(owned_titles)}\n\n"
            "Choose a title from the dropdown below."
        ),
        color=discord.Color.gold()
    )

    return embed


class BuyTitleSelect(discord.ui.Select):
    def __init__(self, owner_id):
        self.owner_id = owner_id

        owned_title_ids = get_player_titles(owner_id)

        options = []

        for title_id, title in TITLE_ITEMS.items():
            if title_id in owned_title_ids:
                continue

            options.append(
                discord.SelectOption(
                    label=title["name"],
                    description=f"{title['price']:,} gold",
                    value=title_id
                )
            )

        super().__init__(
            placeholder="Choose a title to buy...",
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        title_id = self.values[0]
        title = TITLE_ITEMS.get(title_id)

        if not title:
            await interaction.response.send_message(
                "That title does not exist.",
                ephemeral=True
            )
            return

        if player_owns_item(interaction.user.id, title_id):
            await interaction.response.send_message(
                "You already own that title.",
                ephemeral=True
            )
            return

        price = title["price"]
        balance = get_balance(interaction.user.id)

        if balance < price:
            await interaction.response.send_message(
                f"You need **{price:,} gold** to buy {title['name']}.\n"
                f"Your balance is **{balance:,} gold**.",
                ephemeral=True
            )
            return

        add_gold(interaction.user.id, -price)

        date_acquired = datetime.now(timezone.utc).isoformat()

        add_inventory_item(
            interaction.user.id,
            title_id,
            "title",
            date_acquired
        )

        embed = build_titles_embed(interaction.user.id)
        embed.set_footer(text=f"Purchased {title['name']} for {price:,} gold.")

        await interaction.response.edit_message(
            content=None,
            embed=embed,
            view=TitleShopView(interaction.user.id)
        )


class BuyTitleSelectView(discord.ui.View):
    def __init__(self, owner_id):
        super().__init__(timeout=180)
        self.owner_id = owner_id

        self.add_item(BuyTitleSelect(owner_id))

    async def interaction_check(self, interaction):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message(
                "This title menu belongs to someone else. Use `/shop` to open your own.",
                ephemeral=True
            )
            return False

        return True

    @discord.ui.button(label="Back to Titles", emoji="⬅️", style=discord.ButtonStyle.secondary)
    async def back_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(
            content=None,
            embed=build_titles_embed(self.owner_id),
            view=TitleShopView(self.owner_id)
        )


class EquipTitleSelect(discord.ui.Select):
    def __init__(self, owner_id):
        self.owner_id = owner_id

        owned_title_ids = get_player_titles(owner_id)

        options = [
            discord.SelectOption(
                label=DEFAULT_TITLE,
                description="Default Tavern title",
                value="default"
            )
        ]

        for title_id in owned_title_ids:
            title = TITLE_ITEMS.get(title_id)
            if not title:
                continue

            options.append(
                discord.SelectOption(
                    label=title["name"],
                    description="Owned title",
                    value=title_id
                )
            )

        super().__init__(
            placeholder="Choose a title to equip...",
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        selected = self.values[0]

        if selected == "default":
            set_player_title(interaction.user.id, DEFAULT_TITLE)
            equipped_title = DEFAULT_TITLE
        else:
            title = TITLE_ITEMS.get(selected)

            if not title:
                await interaction.response.send_message(
                    "That title does not exist.",
                    ephemeral=True
                )
                return

            if not player_owns_item(interaction.user.id, selected):
                await interaction.response.send_message(
                    "You do not own that title.",
                    ephemeral=True
                )
                return

            equipped_title = title["name"]
            set_player_title(interaction.user.id, equipped_title)

        embed = build_titles_embed(interaction.user.id)
        embed.set_footer(text=f"Equipped title: {equipped_title}")

        await interaction.response.edit_message(
            content=None,
            embed=embed,
            view=TitleShopView(interaction.user.id)
        )


class EquipTitleSelectView(discord.ui.View):
    def __init__(self, owner_id):
        super().__init__(timeout=180)
        self.owner_id = owner_id

        self.add_item(EquipTitleSelect(owner_id))

    async def interaction_check(self, interaction):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message(
                "This title menu belongs to someone else. Use `/shop` to open your own.",
                ephemeral=True
            )
            return False

        return True

    @discord.ui.button(label="Back to Titles", emoji="⬅️", style=discord.ButtonStyle.secondary)
    async def back_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(
            content=None,
            embed=build_titles_embed(self.owner_id),
            view=TitleShopView(self.owner_id)
        )


class TitleShopView(discord.ui.View):
    def __init__(self, owner_id):
        super().__init__(timeout=180)
        self.owner_id = owner_id

    async def interaction_check(self, interaction):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message(
                "This title menu belongs to someone else. Use `/shop` to open your own.",
                ephemeral=True
            )
            return False

        return True

    @discord.ui.button(label="Buy Title", emoji="💰", style=discord.ButtonStyle.green)
    async def buy_title_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        owned_title_ids = get_player_titles(self.owner_id)

        available_titles = [
            title_id
            for title_id in TITLE_ITEMS
            if title_id not in owned_title_ids
        ]

        if not available_titles:
            embed = build_titles_embed(self.owner_id)
            embed.set_footer(text="You already own every title in the shop.")

            await interaction.response.edit_message(
                content=None,
                embed=embed,
                view=TitleShopView(self.owner_id)
            )
            return

        await interaction.response.edit_message(
            content=None,
            embed=build_buy_titles_embed(self.owner_id),
            view=BuyTitleSelectView(self.owner_id)
        )

    @discord.ui.button(label="Equip Title", emoji="🎖", style=discord.ButtonStyle.blurple)
    async def equip_title_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(
            content=None,
            embed=build_equip_titles_embed(self.owner_id),
            view=EquipTitleSelectView(self.owner_id)
        )

    @discord.ui.button(label="Back to Shop", emoji="⬅️", style=discord.ButtonStyle.secondary)
    async def back_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(
            content=None,
            embed=build_shop_embed(self.owner_id),
            view=ShopView(self.owner_id)
        )
        

class Tavern(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="addgold", description="Founder only - add gold to a player")
    @app_commands.describe(user="Player", amount="Amount of gold to add")
    async def addgold(self, interaction: discord.Interaction, user: discord.User, amount: int):
        if interaction.user.id != FOUNDER_ID:
            await interaction.response.send_message("🚫 Founder only.", ephemeral=True)
            return

        if amount <= 0:
            await interaction.response.send_message("Amount must be greater than 0.", ephemeral=True)
            return

        new_balance = add_gold(user.id, amount)

        await interaction.response.send_message(
            f"💰 {user.mention} received **{amount:,} gold**.\n"
            f"New balance: **{new_balance:,} gold**."
        )

    @app_commands.command(name="removegold", description="Founder only - remove gold from a player")
    @app_commands.describe(user="Player", amount="Amount of gold to remove")
    async def removegold(self, interaction: discord.Interaction, user: discord.User, amount: int):
        if interaction.user.id != FOUNDER_ID:
            await interaction.response.send_message("🚫 Founder only.", ephemeral=True)
            return

        if amount <= 0:
            await interaction.response.send_message("Amount must be greater than 0.", ephemeral=True)
            return

        new_balance = add_gold(user.id, -amount)

        if new_balance < 0:
            new_balance = add_gold(user.id, abs(new_balance))

        await interaction.response.send_message(
            f"💸 Removed **{amount:,} gold** from {user.mention}.\n"
            f"New balance: **{new_balance:,} gold**."
        )

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
        
    @app_commands.command(name="shop", description="Open The Tavern shop")
    async def shop(self, interaction: discord.Interaction):
        if not is_tavern_channel(interaction):
            await interaction.response.send_message(
                "🍺 TrophyBot only runs in **The Tavern**.",
                ephemeral=True
            )
            return


        await interaction.response.send_message(
            embed=build_shop_embed(interaction.user.id),
            view=ShopView(interaction.user.id),
            ephemeral=True
        )

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
                "🏪 Shop\n"
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
