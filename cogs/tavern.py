import discord
import random
import asyncio
import os
import time
from discord.ext import commands, tasks
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
    add_player_sticker,
    get_player_stickers,
    get_player_sticker_quantity,
    set_featured_sticker,
    get_featured_sticker,
    get_sticker_pack_setting,
    set_sticker_pack_setting,
    get_tavern_setting,
    set_tavern_setting,
    get_title_changed_at,
    set_title_changed_at,
    record_math_drill_result,
    get_math_stats,
    get_last_daily_math_challenge,
    get_daily_claim_preview,
    claim_daily_streak,
    get_daily_tasks,
    mark_daily_task,
    claim_daily_task_reward_if_ready,
    record_hangman_result,
    get_hangman_stats,
    get_hourly_tip_total,
    add_hourly_tip_total,
    get_all_player_ids,
    add_player_effect,
    get_player_effect_quantity,
    consume_player_effect,
)
from games.blackjack_engine import Deck, hand_value
from achievement_service import check_achievements
from achievements import ACHIEVEMENTS


FOUNDER_ID = 502268158749573132
SHOP_CHANNEL_ID = 1518842044020297801
BASE_BET = 100
DEFAULT_TITLE = "🍺 Tavern Newbie"

TITLE_ITEMS = {
    "gold_hoarder": {
        "name": "💰 Gold Hoarder",
        "price": 2500,
        "rarity": "Uncommon",
        "bonus_description": "Daily Gold +10%",
        "daily_gold_bonus": 0.10,
    },
    "dice_goblin": {
        "name": "🎲 Dice Goblin",
        "price": 7500,
        "rarity": "Rare",
        "bonus_description": "Dice XP +10%",
        "xp_bonus": 0.10,
        "xp_sources": ["dice"],
    },
    "card_shark": {
        "name": "🃏 Card Shark",
        "price": 7500,
        "rarity": "Rare",
        "bonus_description": "Blackjack XP +10%",
        "xp_bonus": 0.10,
        "xp_sources": ["blackjack"],
    },
    "high_roller": {
        "name": "🎖 High Roller",
        "price": 25000,
        "rarity": "Epic",
        "bonus_description": "All game XP +12%",
        "xp_bonus": 0.12,
        "xp_sources": ["all"],
    },
    "tavern_royalty": {
        "name": "👑 Tavern Royalty",
        "price": 75000,
        "rarity": "Legendary",
        "bonus_description": "Shop Discount +10%, All game XP +15%",
        "shop_discount": 0.10,
        "xp_bonus": 0.15,
        "xp_sources": ["all"],
    },
}

TITLE_SWAP_COOLDOWN_SECONDS = 24 * 60 * 60

MATH_DRILL_TOTAL_QUESTIONS = 5
MATH_QUICK_ANSWER_MS = 3000
MATH_ACTIVE_CHANNELS = {}
MATH_ACTIVE_USERS = set()
MATH_CHANNEL_LOCKS = {}

MATH_DRILL_DIFFICULTIES = {
    "easy": {
        "name": "Easy",
        "emoji": "🟢",
        "time_limit": 20,
        "xp_per_correct": 5,
        "perfect_gold": 5,
        "operators": ["+", "-"],
        "description": "Addition and subtraction. 20 seconds per question.",
    },
    "medium": {
        "name": "Medium",
        "emoji": "🟡",
        "time_limit": 15,
        "xp_per_correct": 8,
        "perfect_gold": 10,
        "operators": ["+", "-", "×"],
        "description": "Addition, subtraction, and multiplication. 15 seconds per question.",
    },
    "hard": {
        "name": "Hard",
        "emoji": "🔴",
        "time_limit": 10,
        "xp_per_correct": 12,
        "perfect_gold": 15,
        "operators": ["×", "÷"],
        "description": "Multiplication and clean division. 10 seconds per question.",
    },
}

DAILY_MATH_CHALLENGE_GOLD = 100

DAILY_TASK_REWARD_GOLD = 100
DAILY_TASK_REWARD_XP = 25
TIP_HOURLY_LIMIT = 100
TAVERN_EVENT_CHANCE = 0.40
TAVERN_EVENT_INTERVAL_HOURS = 1

DAILY_TASK_LABELS = {
    "play_game": "🎮 Play 1 game",
    "take_shot": "🥃 Take 1 shot",
    "use_mischief": "🎭 Use 1 mischief item",
    "open_pack": "📦 Open 1 sticker pack",
    "complete_math": "🧠 Complete 1 math drill",
}


CONFETTI_DUD_GIF = os.getenv("CONFETTI_DUD_GIF", "").strip()
STICKER_ASSET_BASE_URL = "https://raw.githubusercontent.com/celtichero2026/blackjack-bot/main/assets/stickers"
GIF_ASSET_BASE_URL = "https://raw.githubusercontent.com/celtichero2026/blackjack-bot/main/assets/gifs"
IMAGE_ASSET_BASE_URL = "https://raw.githubusercontent.com/celtichero2026/blackjack-bot/main/assets/images"
SOUND_ASSET_FOLDER = "assets/sounds"

HANGMAN_WORDS_FOLDER = "assets/words"
HANGMAN_MIN_WORD_LENGTH = 4
HANGMAN_MAX_WORD_LENGTH = 12
HANGMAN_MAX_MISTAKES = 6
HANGMAN_ACTIVE_CHANNELS = {}
HANGMAN_WORD_CACHE = None
HANGMAN_VOWELS = "AEIOUY"
HANGMAN_CONSONANTS = "BCDFGHJKLMNPQRSTVWXZ"
HANGMAN_GUESSER_WIN_GOLD = 25
HANGMAN_GUESSER_WIN_XP = 30
HANGMAN_UNDERTAKER_LOSE_XP = 10
HANGMAN_UNDERTAKER_WIN_GOLD = 75
HANGMAN_UNDERTAKER_WIN_XP = 40
HANGMAN_GUESSER_LOSE_XP = 15
HANGMAN_SOLO_WIN_GOLD = 25
HANGMAN_SOLO_WIN_XP = 30
HANGMAN_SOLO_LOSE_XP = 10

SHOT_GIF_FILES = [
    "shot_1.gif",
    "shot_2.gif",
    "shot_3.gif",
    "shot_4.gif",
    "shot_5.gif",
]

SHOT_ITEMS = {
    "tavern_shot": {
        "name": "🥃 Tavern Shot",
        "price": 750,
        "description": "Instantly posts a random shot GIF in the current Tavern channel.",
    },
}

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

GAMEPLAY_ITEMS = {
    "lucky_shield": {
        "name": "🍀 Lucky Shield",
        "price": 500,
        "description": "Activate before playing. Your next gold loss has a 25% chance to be blocked.",
    },
    "sturdy_shield": {
        "name": "🛡️ Sturdy Shield",
        "price": 1250,
        "description": "Activate before playing. Your next gold loss has a 40% chance to be blocked.",
    },
    "fortune_shield": {
        "name": "💎 Fortune Shield",
        "price": 2500,
        "description": "Activate before playing. Your next gold loss has a 60% chance to be blocked.",
    },
}

SHIELD_TIERS = {
    "lucky_shield": {
        "effect_id": "lucky_shield_active",
        "name": "🍀 Lucky Shield",
        "short_name": "Lucky Shield",
        "chance": 0.25,
        "priority": 1,
    },
    "sturdy_shield": {
        "effect_id": "sturdy_shield_active",
        "name": "🛡️ Sturdy Shield",
        "short_name": "Sturdy Shield",
        "chance": 0.40,
        "priority": 2,
    },
    "fortune_shield": {
        "effect_id": "fortune_shield_active",
        "name": "💎 Fortune Shield",
        "short_name": "Fortune Shield",
        "chance": 0.60,
        "priority": 3,
    },
}

LUCKY_SHIELD_EFFECT_ID = SHIELD_TIERS["lucky_shield"]["effect_id"]
LUCKY_SHIELD_PROTECT_CHANCE = SHIELD_TIERS["lucky_shield"]["chance"]

SOUND_ITEMS = {
    "cat_girl": {
        "name": "🐈‍⬛ Cat Girl",
        "price": 2500,
        "description": "A grown man making deeply questionable cat noises.",
        "file": "cat_girl.mp3",
        "message": "has unleashed Cat Girl upon the Tavern.",
        "attack_title": "🐈‍⬛ CAT GIRL ATTACK",
        "attack_lines": [
            "A grown man has entered his meow era.",
            "The Tavern has suffered emotional damage.",
            "Someone take the microphone away from him.",
            "This is why we cannot have nice things.",
            "The cat noises were not requested, but here we are.",
            "Management refuses to explain this sound.",
            "The vibes are cursed and unfortunately audible.",
        ],
    },
    "come_to_your_house": {
        "name": "🏠 Come to Your House",
        "price": 3500,
        "description": "A suspicious clip with an even more suspicious clarification.",
        "file": "come_to_your_house.mp3",
        "message": "has issued a deeply questionable house call.",
        "attack_title": "🏠 COME TO YOUR HOUSE",
        "attack_lines": [
            "Just so we are clear, he meant the house.",
            "The awkward silence was the loudest part.",
            "That clarification did not help as much as he hoped.",
            "The Tavern would like the record corrected immediately.",
            "A legally important pause has entered the chat.",
            "This audio clip has been reviewed by absolutely no one.",
        ],
    },
}

SOUND_ATTACK_COOLDOWN_SECONDS = 45
SOUND_ATTACK_COOLDOWNS = {}

ITEM_CONFIRMATIONS_SETTING_KEY = "item_confirmations_enabled"


STICKER_RARITIES = {
    "common": {
        "label": "⚪ Common",
        "weight": 55,
    },
    "uncommon": {
        "label": "🟢 Uncommon",
        "weight": 25,
    },
    "rare": {
        "label": "🔵 Rare",
        "weight": 12,
    },
    "epic": {
        "label": "🟣 Epic",
        "weight": 6,
    },
    "legendary": {
        "label": "🟡 Legendary",
        "weight": 2,
    },
}

STICKERS = {
    "welcome_tavern_newbie": {
        "name": "🍺 Tavern Newbie",
        "rarity": "common",
        "collection": "welcome",
        "quote": "Everyone starts somewhere. Usually broke.",
        "file": "tavern_newbie.png",
    },
    "welcome_daily_gold": {
        "name": "💰 Daily Gold",
        "rarity": "common",
        "collection": "welcome",
        "quote": "A responsible financial decision, somehow.",
        "file": "daily_gold.png",
    },
    "welcome_first_drink": {
        "name": "🍻 First Drink",
        "rarity": "common",
        "collection": "welcome",
        "quote": "The beginning of many questionable choices.",
        "file": "first_drink.png",
    },
    "welcome_questionable_choices": {
        "name": "🤔 Questionable Choices",
        "rarity": "uncommon",
        "collection": "welcome",
        "quote": "The official Tavern lifestyle.",
        "file": "questionable_choices.png",
    },
    "welcome_bar_tab": {
        "name": "🧾 Open Bar Tab",
        "rarity": "uncommon",
        "collection": "welcome",
        "quote": "Nobody knows who approved this.",
        "file": "bar_tab.png",
    },
    "welcome_house_rules": {
        "name": "📜 House Rules",
        "rarity": "rare",
        "collection": "welcome",
        "quote": "The house always wins. Unless it does not.",
        "file": "house_rules.png",
    },
    "welcome_warm_seat": {
        "name": "🪑 Warm Seat",
        "rarity": "rare",
        "collection": "welcome",
        "quote": "Someone has been here too long.",
        "file": "warm_seat.png",
    },
    "welcome_tavern_regular": {
        "name": "🎰 Tavern Regular",
        "rarity": "epic",
        "collection": "welcome",
        "quote": "They say they can quit whenever they want.",
        "file": "tavern_regular.png",
    },
    "welcome_founders_favor": {
        "name": "🏆 Founder's Favor",
        "rarity": "legendary",
        "collection": "welcome",
        "quote": "Blessed by management. Probably dangerous.",
        "file": "founders_favor.png",

    "mischief_tomato_target": {
        "name": "🍅 Tomato Target",
        "rarity": "common",
        "collection": "mischief",
        "quote": "A face made for produce.",
    },
    "mischief_pie_face": {
        "name": "🥧 Pie Face",
        "rarity": "common",
        "collection": "mischief",
        "quote": "Dessert has consequences.",
    },
    "mischief_confetti_dud": {
        "name": "✨ Confetti Dud",
        "rarity": "common",
        "collection": "mischief",
        "quote": "A sad little puff of celebration.",
    },
    "mischief_extra_juicy": {
        "name": "💦 Extra Juicy",
        "rarity": "uncommon",
        "collection": "mischief",
        "quote": "Oof. That one had splash damage.",
    },
    "mischief_hr_territory": {
        "name": "🫣 HR Territory",
        "rarity": "uncommon",
        "collection": "mischief",
        "quote": "The Tavern will not be taking questions.",
    },
    "mischief_mystery_box": {
        "name": "🎁 Mystery Box",
        "rarity": "rare",
        "collection": "mischief",
        "quote": "Nothing bad has ever come from opening boxes.",
    },
    "mischief_backfire": {
        "name": "💥 Backfire",
        "rarity": "rare",
        "collection": "mischief",
        "quote": "The prank became self-aware.",
    },
    "mischief_managed": {
        "name": "🎭 Mischief Managed",
        "rarity": "epic",
        "collection": "mischief",
        "quote": "It was handled poorly, but confidently.",
    },
    "mischief_chaos_goblin": {
        "name": "🧨 Chaos Goblin",
        "rarity": "epic",
        "collection": "mischief",
        "quote": "Small, loud, and absolutely not sorry.",
    },
    "mischief_public_menace": {
        "name": "🚨 Public Menace",
        "rarity": "legendary",
        "collection": "mischief",
        "quote": "The Tavern's most wanted menace.",
    },

    "casino_bad_roll": {
        "name": "🎲 Bad Roll",
        "rarity": "common",
        "collection": "casino",
        "quote": "The dice were emotionally unavailable.",
    },
    "casino_broke_again": {
        "name": "💸 Broke Again",
        "rarity": "common",
        "collection": "casino",
        "quote": "A classic Tavern condition.",
    },
    "casino_suspicious_hand": {
        "name": "🃏 Suspicious Hand",
        "rarity": "common",
        "collection": "casino",
        "quote": "Nobody saw anything. Probably.",
    },
    "casino_push_it": {
        "name": "🤝 Push It",
        "rarity": "uncommon",
        "collection": "casino",
        "quote": "Not winning. Not losing. Just vibing.",
    },
    "casino_dice_goblin": {
        "name": "🎲 Dice Goblin",
        "rarity": "uncommon",
        "collection": "casino",
        "quote": "Rolls with confidence. Loses with style.",
    },
    "casino_card_shark": {
        "name": "🦈 Card Shark",
        "rarity": "rare",
        "collection": "casino",
        "quote": "Knows the odds and ignores them anyway.",
    },
    "casino_dealer_knows": {
        "name": "👀 The Dealer Knows",
        "rarity": "rare",
        "collection": "casino",
        "quote": "The dealer saw that.",
    },
    "casino_hot_streak": {
        "name": "🔥 Hot Streak",
        "rarity": "epic",
        "collection": "casino",
        "quote": "Finally, suspiciously lucky.",
    },
    "casino_high_roller": {
        "name": "💎 High Roller",
        "rarity": "epic",
        "collection": "casino",
        "quote": "Big bets. Bigger denial.",
    },
    "casino_house_lost": {
        "name": "🍀 The House Lost",
        "rarity": "legendary",
        "collection": "casino",
        "quote": "A rare and beautiful disaster.",
    },
}

STICKER_COLLECTIONS = {
    "welcome": {
        "name": "🍺 Welcome Collection",
        "short_name": "Welcome",
        "description": "The starter set for Tavern regulars.",
        "stickers": [
            "welcome_tavern_newbie",
            "welcome_daily_gold",
            "welcome_first_drink",
            "welcome_questionable_choices",
            "welcome_bar_tab",
            "welcome_house_rules",
            "welcome_warm_seat",
            "welcome_tavern_regular",
            "welcome_founders_favor",
        ],
    },
    "mischief": {
        "name": "🎭 Mischief Collection",
        "short_name": "Mischief",
        "description": "Tomatoes, pies, boxes, and poor choices.",
        "stickers": [
            "mischief_tomato_target",
            "mischief_pie_face",
            "mischief_confetti_dud",
            "mischief_extra_juicy",
            "mischief_hr_territory",
            "mischief_mystery_box",
            "mischief_backfire",
            "mischief_managed",
            "mischief_chaos_goblin",
            "mischief_public_menace",
        ],
    },
    "casino": {
        "name": "🎲 Casino Collection",
        "short_name": "Casino",
        "description": "Dice rolls, bad hands, and impossible luck.",
        "stickers": [
            "casino_bad_roll",
            "casino_broke_again",
            "casino_suspicious_hand",
            "casino_push_it",
            "casino_dice_goblin",
            "casino_card_shark",
            "casino_dealer_knows",
            "casino_hot_streak",
            "casino_high_roller",
            "casino_house_lost",
        ],
    },
}

STICKER_PACKS = {
    "welcome_pack": {
        "name": "🍺 Welcome Pack",
        "price": 1000,
        "pulls": 3,
        "collections": ["welcome"],
        "purchase_enabled": True,
        "tavern_mix_enabled": True,
        "weights": {
            "common": 62,
            "uncommon": 24,
            "rare": 10,
            "epic": 3,
            "legendary": 1,
        },
    },
    "mischief_pack": {
        "name": "🎭 Mischief Pack",
        "price": 1250,
        "pulls": 3,
        "collections": ["mischief"],
        "purchase_enabled": False,
        "tavern_mix_enabled": False,
        "weights": {
            "common": 58,
            "uncommon": 25,
            "rare": 12,
            "epic": 4,
            "legendary": 1,
        },
    },
    "casino_pack": {
        "name": "🎲 Casino Pack",
        "price": 1500,
        "pulls": 3,
        "collections": ["casino"],
        "purchase_enabled": False,
        "tavern_mix_enabled": False,
        "weights": {
            "common": 56,
            "uncommon": 25,
            "rare": 13,
            "epic": 5,
            "legendary": 1,
        },
    },
    "tavern_mix_pack": {
        "name": "📦 Tavern Mix Pack",
        "price": 3000,
        "pulls": 5,
        "collections": ["welcome", "mischief", "casino"],
        "purchase_enabled": True,
        "tavern_mix_enabled": False,
        "uses_tavern_mix_pool": True,
        "weights": {
            "common": 48,
            "uncommon": 27,
            "rare": 16,
            "epic": 7,
            "legendary": 2,
        },
    },
}

def get_sticker_image_url(sticker_id):
    sticker = STICKERS.get(sticker_id)

    if not sticker:
        return None

    file_name = sticker.get("file")

    if not file_name:
        return None

    collection_id = sticker["collection"]

    return f"{STICKER_ASSET_BASE_URL}/{collection_id}/{file_name}"

def is_tavern_channel(interaction):
    return interaction.channel_id == TAVERN_CHANNEL_ID


def is_shop_channel(interaction):
    return interaction.channel_id == SHOP_CHANNEL_ID


def is_tavern_or_shop_channel(interaction):
    return is_tavern_channel(interaction) or is_shop_channel(interaction)


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
    title_bonus = xp_info.get("title_xp_bonus", 0)
    bonus_line = ""

    if title_bonus > 0:
        bonus_line = f"\n🎖 Title Bonus: **+{title_bonus} XP**"

    return (
        f"\n⭐ **+{xp_info['xp_gained']} XP**"
        f"{bonus_line}"
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
    return f"- <@{player_id}> — {title}{lucky_shield_badge(player_id)}"


def get_title_id_by_name(title_name):
    if not title_name or title_name == DEFAULT_TITLE:
        return "default"

    for title_id, title in TITLE_ITEMS.items():
        if title.get("name") == title_name:
            return title_id

    return "default"


def get_active_title_id(user_id):
    return get_title_id_by_name(get_active_title(user_id))


def get_title_bonus_description(title_id):
    if title_id == "default":
        return "No active bonus."

    title = TITLE_ITEMS.get(title_id)
    if not title:
        return "No active bonus."

    return title.get("bonus_description", "No active bonus.")


def get_active_title_bonus_description(user_id):
    return get_title_bonus_description(get_active_title_id(user_id))


def get_shop_discount_percent(user_id):
    title_id = get_active_title_id(user_id)
    title = TITLE_ITEMS.get(title_id, {})
    return float(title.get("shop_discount", 0) or 0)


def get_discounted_shop_price(user_id, base_price):
    discount = get_shop_discount_percent(user_id)

    if discount <= 0:
        return base_price

    discounted = int(base_price * (1 - discount))
    return max(1, discounted)


def format_shop_price(user_id, base_price):
    discounted = get_discounted_shop_price(user_id, base_price)

    if discounted == base_price:
        return f"{base_price:,} gold"

    percent = int(get_shop_discount_percent(user_id) * 100)
    return f"{discounted:,} gold ({percent}% off; was {base_price:,})"


def shop_discount_line(user_id):
    discount = get_shop_discount_percent(user_id)

    if discount <= 0:
        return ""

    return f"\n🎖 Shop Discount: **{int(discount * 100)}% off**"


def get_daily_gold_reward(user_id, base_reward):
    title_id = get_active_title_id(user_id)
    title = TITLE_ITEMS.get(title_id, {})
    bonus_percent = float(title.get("daily_gold_bonus", 0) or 0)

    if bonus_percent <= 0:
        return base_reward, 0, ""

    bonus_amount = max(1, int((base_reward * bonus_percent) + 0.999999))
    return base_reward + bonus_amount, bonus_amount, title.get("name", "")


def get_title_xp_bonus_percent(user_id, source):
    title_id = get_active_title_id(user_id)
    title = TITLE_ITEMS.get(title_id, {})

    bonus_percent = float(title.get("xp_bonus", 0) or 0)
    sources = title.get("xp_sources", [])

    if bonus_percent <= 0:
        return 0

    if "all" in sources or source in sources:
        return bonus_percent

    return 0


def award_tavern_xp(user_id, amount, source):
    bonus_percent = get_title_xp_bonus_percent(user_id, source)
    bonus_amount = 0

    if bonus_percent > 0:
        bonus_amount = max(1, int((amount * bonus_percent) + 0.999999))

    total_xp = amount + bonus_amount
    xp_info = add_xp(user_id, total_xp)

    if xp_info:
        xp_info["base_xp"] = amount
        xp_info["title_xp_bonus"] = bonus_amount
        xp_info["title_bonus_name"] = get_active_title(user_id)

    return xp_info



def utc_today_text():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def current_hour_key():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d-%H")


def apply_daily_task_progress(user_id, task_key):
    today = utc_today_text()
    tasks_snapshot = mark_daily_task(user_id, today, task_key)
    reward_awarded = claim_daily_task_reward_if_ready(user_id, today)
    xp_info = None

    if reward_awarded:
        add_gold(user_id, DAILY_TASK_REWARD_GOLD)
        xp_info = award_tavern_xp(user_id, DAILY_TASK_REWARD_XP, "tasks")

    return tasks_snapshot, reward_awarded, xp_info


def daily_task_reward_text(reward_awarded, xp_info=None):
    if not reward_awarded:
        return ""

    text = (
        f"\n\n✅ **Daily Tavern Tasks complete!** "
        f"+{DAILY_TASK_REWARD_GOLD:,} gold and +{DAILY_TASK_REWARD_XP} XP awarded."
    )

    if xp_info and xp_info.get("title_xp_bonus", 0) > 0:
        text += f"\n🎖 Title Bonus: +{xp_info['title_xp_bonus']} XP"

    return text


def format_daily_tasks_lines(user_id):
    tasks_snapshot = get_daily_tasks(user_id, utc_today_text())
    lines = []

    for task_key, label in DAILY_TASK_LABELS.items():
        marker = "✅" if tasks_snapshot.get(task_key) else "⬜"
        lines.append(f"{marker} {label}")

    reward_marker = "✅ Claimed" if tasks_snapshot.get("reward_claimed") else "🎁 Available after all tasks"
    lines.append("")
    lines.append(f"Reward: **{DAILY_TASK_REWARD_GOLD:,} gold + {DAILY_TASK_REWARD_XP} XP** — {reward_marker}")
    return "\n".join(lines)


def build_daily_tasks_embed(user_id):
    embed = discord.Embed(
        title="✅ Daily Tavern Tasks",
        description=format_daily_tasks_lines(user_id),
        color=discord.Color.gold()
    )
    embed.set_footer(text="Tasks reset each UTC day.")
    return embed


def award_bonus_sticker_pack(user_id, pack_id="welcome_pack"):
    pack = STICKER_PACKS.get(pack_id)

    if not pack:
        return []

    pulls = []
    date_collected = datetime.now(timezone.utc).isoformat()

    for index in range(pack.get("pulls", 3)):
        sticker_id = roll_sticker_from_pack(pack_id)

        if not sticker_id:
            continue

        old_quantity = get_player_sticker_quantity(user_id, sticker_id)
        add_player_sticker(user_id, sticker_id, 1, date_collected)
        pulls.append((sticker_id, old_quantity, old_quantity + 1))

    return pulls


def format_bonus_pack_lines(pulls):
    if not pulls:
        return ""

    lines = []
    for sticker_id, old_quantity, new_quantity in pulls:
        sticker = STICKERS.get(sticker_id, {"name": sticker_id})
        status = "NEW!" if old_quantity == 0 else f"x{new_quantity}"
        lines.append(f"{get_sticker_rarity_label(sticker_id)} {sticker['name']} — **{status}**")

    return "\n".join(lines)


def get_common_sticker_ids():
    return [
        sticker_id
        for sticker_id, sticker in STICKERS.items()
        if sticker.get("rarity") == "common"
    ]

def parse_title_changed_at(value):
    if not value:
        return None

    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def get_title_swap_remaining_seconds(user_id):
    if user_id == FOUNDER_ID:
        return 0

    changed_at = parse_title_changed_at(get_title_changed_at(user_id))

    if not changed_at:
        return 0

    now = datetime.now(timezone.utc)

    if changed_at.tzinfo is None:
        changed_at = changed_at.replace(tzinfo=timezone.utc)

    elapsed = (now - changed_at).total_seconds()
    remaining = int(TITLE_SWAP_COOLDOWN_SECONDS - elapsed)
    return max(0, remaining)


def format_seconds_compact(seconds):
    seconds = max(0, int(seconds))
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60

    if hours > 0:
        return f"{hours}h {minutes}m"

    if minutes > 0:
        return f"{minutes}m"

    return "less than 1m"


def title_swap_status_text(user_id):
    remaining = get_title_swap_remaining_seconds(user_id)

    if remaining <= 0:
        return "✅ Title swap available now."

    return f"⏳ Next title swap available in **{format_seconds_compact(remaining)}**."


def mark_title_changed(user_id):
    set_title_changed_at(
        user_id,
        datetime.now(timezone.utc).isoformat()
    )


def math_drill_active_player(channel_id):
    active = MATH_ACTIVE_CHANNELS.get(channel_id)

    if not active:
        return None

    return active.get("player_id")


def is_math_drill_active(channel_id):
    return channel_id in MATH_ACTIVE_CHANNELS


def math_focus_block_text(channel_id):
    player_id = math_drill_active_player(channel_id)

    if not player_id:
        return "🧠 A Math Drill is active in this channel. Please wait for it to finish."

    return f"🧠 <@{player_id}> is in a Math Drill right now. Please wait for the drill to finish."


def can_start_math_drill(interaction):
    if is_math_drill_active(interaction.channel_id):
        return False, math_focus_block_text(interaction.channel_id)

    if interaction.user.id in MATH_ACTIVE_USERS:
        return False, "🧠 You already have an active Math Drill. Finish that one first."

    return True, ""


def generate_math_question(difficulty_id):
    config = MATH_DRILL_DIFFICULTIES[difficulty_id]
    operator = random.choice(config["operators"])

    if difficulty_id == "easy":
        a = random.randint(1, 20)
        b = random.randint(1, 20)

        if operator == "+":
            answer = a + b
            question = f"{a} + {b}"
        else:
            high = max(a, b)
            low = min(a, b)
            answer = high - low
            question = f"{high} - {low}"

    elif difficulty_id == "medium":
        if operator == "×":
            a = random.randint(2, 12)
            b = random.randint(2, 12)
            answer = a * b
            question = f"{a} × {b}"
        else:
            a = random.randint(10, 50)
            b = random.randint(5, 50)

            if operator == "+":
                answer = a + b
                question = f"{a} + {b}"
            else:
                high = max(a, b)
                low = min(a, b)
                answer = high - low
                question = f"{high} - {low}"

    else:
        if operator == "÷":
            answer = random.randint(2, 20)
            divisor = random.randint(2, 12)
            dividend = answer * divisor
            question = f"{dividend} ÷ {divisor}"
        else:
            a = random.randint(6, 20)
            b = random.randint(6, 20)
            answer = a * b
            question = f"{a} × {b}"

    return question, answer


def generate_math_choices(answer):
    choices = {answer}
    spread = max(4, abs(answer) // 4)

    while len(choices) < 4:
        offset = random.randint(-spread, spread)

        if offset == 0:
            continue

        candidate = answer + offset

        if candidate < 0:
            continue

        choices.add(candidate)

    choice_list = list(choices)
    random.shuffle(choice_list)
    return choice_list


async def start_math_channel_focus(interaction, player_id):
    channel = interaction.channel
    guild = interaction.guild

    if not guild or not channel:
        return "⚠️ Math Focus could not lock the channel here, but the drill is still playable."

    bot_member = guild.me

    if not bot_member or not channel.permissions_for(bot_member).manage_channels:
        return "⚠️ Math Focus needs **Manage Channels** to pause chat during drills. The drill is still playable."

    default_role = guild.default_role
    player_member = guild.get_member(player_id)

    if not player_member:
        return "⚠️ Math Focus could not find the player member, but the drill is still playable."

    original_default = channel.overwrites_for(default_role)
    original_player = channel.overwrites_for(player_member)
    original_bot = channel.overwrites_for(bot_member)

    MATH_CHANNEL_LOCKS[channel.id] = {
        "channel": channel,
        "default_role": default_role,
        "player_member": player_member,
        "bot_member": bot_member,
        "original_default": original_default,
        "original_player": original_player,
        "original_bot": original_bot,
    }

    try:
        default_overwrite = channel.overwrites_for(default_role)
        default_overwrite.send_messages = False

        player_overwrite = channel.overwrites_for(player_member)
        player_overwrite.send_messages = True

        bot_overwrite = channel.overwrites_for(bot_member)
        bot_overwrite.send_messages = True

        await channel.set_permissions(
            default_role,
            overwrite=default_overwrite,
            reason="Tavern Math Drill focus mode"
        )
        await channel.set_permissions(
            player_member,
            overwrite=player_overwrite,
            reason="Tavern Math Drill focus mode"
        )
        await channel.set_permissions(
            bot_member,
            overwrite=bot_overwrite,
            reason="Tavern Math Drill focus mode"
        )

        return "🔒 Math Focus is active. Chat is paused until the drill ends."

    except Exception:
        await release_math_channel_focus(channel.id)
        return "⚠️ Math Focus could not change channel permissions, but the drill is still playable."


async def restore_permission_overwrite(channel, target, overwrite):
    if overwrite.is_empty():
        await channel.set_permissions(target, overwrite=None, reason="Tavern Math Drill ended")
    else:
        await channel.set_permissions(target, overwrite=overwrite, reason="Tavern Math Drill ended")


async def release_math_channel_focus(channel_id):
    lock = MATH_CHANNEL_LOCKS.pop(channel_id, None)

    if not lock:
        return

    channel = lock["channel"]

    try:
        await restore_permission_overwrite(channel, lock["default_role"], lock["original_default"])
        await restore_permission_overwrite(channel, lock["player_member"], lock["original_player"])
        await restore_permission_overwrite(channel, lock["bot_member"], lock["original_bot"])
    except Exception:
        pass




def get_sticker_quantity_map(user_id):
    rows = get_player_stickers(user_id)
    return {
        sticker_id: quantity
        for sticker_id, quantity, first_collected in rows
    }


def get_sticker_rarity_label(sticker_id):
    sticker = STICKERS.get(sticker_id)

    if not sticker:
        return "⚪ Common"

    rarity = sticker.get("rarity", "common")
    return STICKER_RARITIES.get(rarity, STICKER_RARITIES["common"])["label"]


def get_collection_progress(user_id, collection_id):
    collection = STICKER_COLLECTIONS.get(collection_id)

    if not collection:
        return 0, 0

    sticker_map = get_sticker_quantity_map(user_id)
    stickers = collection["stickers"]
    owned = sum(
        1
        for sticker_id in stickers
        if sticker_map.get(sticker_id, 0) > 0
    )

    return owned, len(stickers)


def get_total_sticker_progress(user_id):
    sticker_map = get_sticker_quantity_map(user_id)
    total = len(STICKERS)
    owned = sum(
        1
        for sticker_id in STICKERS
        if sticker_map.get(sticker_id, 0) > 0
    )

    return owned, total


def get_featured_sticker_for_user(user_id):
    featured_id = get_featured_sticker(user_id)
    sticker_map = get_sticker_quantity_map(user_id)

    if featured_id in STICKERS and sticker_map.get(featured_id, 0) > 0:
        return featured_id

    for sticker_id in STICKERS:
        if sticker_map.get(sticker_id, 0) > 0:
            return sticker_id

    return ""


def get_sticker_pack_flags(pack_id):
    pack = STICKER_PACKS.get(pack_id)

    if not pack:
        return False, False

    purchase_enabled = bool(pack.get("purchase_enabled", True))
    tavern_mix_enabled = bool(pack.get("tavern_mix_enabled", True))

    setting = get_sticker_pack_setting(pack_id)

    if setting:
        purchase_enabled = bool(setting[0])
        tavern_mix_enabled = bool(setting[1])

    return purchase_enabled, tavern_mix_enabled


def is_sticker_pack_purchase_enabled(pack_id):
    purchase_enabled, tavern_mix_enabled = get_sticker_pack_flags(pack_id)
    return purchase_enabled


def is_sticker_pack_tavern_mix_enabled(pack_id):
    purchase_enabled, tavern_mix_enabled = get_sticker_pack_flags(pack_id)
    return tavern_mix_enabled


def get_tavern_mix_enabled_collections():
    enabled_collections = set()

    for pack_id, pack in STICKER_PACKS.items():
        if pack.get("uses_tavern_mix_pool", False):
            continue

        if not is_sticker_pack_tavern_mix_enabled(pack_id):
            continue

        enabled_collections.update(pack.get("collections", []))

    return enabled_collections


def get_allowed_collections_for_pack(pack_id):
    pack = STICKER_PACKS.get(pack_id)

    if not pack:
        return []

    collections = list(pack.get("collections", []))

    if pack.get("uses_tavern_mix_pool", False):
        mix_enabled_collections = get_tavern_mix_enabled_collections()
        collections = [
            collection_id
            for collection_id in collections
            if collection_id in mix_enabled_collections
        ]

    return collections


def can_roll_sticker_pack(pack_id):
    return len(get_allowed_collections_for_pack(pack_id)) > 0


def get_available_sticker_pack_ids():
    return [
        pack_id
        for pack_id in STICKER_PACKS
        if (
            is_sticker_pack_purchase_enabled(pack_id)
            and can_roll_sticker_pack(pack_id)
        )
    ]


def format_enabled_status(is_enabled):
    if is_enabled:
        return "✅ Enabled"

    return "🚫 Disabled"


def parse_setting_bool(value, default=True):
    if value is None or value == "":
        return default

    normalized = str(value).strip().lower()

    if normalized in ["1", "true", "yes", "on", "enabled"]:
        return True

    if normalized in ["0", "false", "no", "off", "disabled"]:
        return False

    return default


def item_confirmations_enabled():
    value = get_tavern_setting(
        ITEM_CONFIRMATIONS_SETTING_KEY,
        "1"
    )

    return parse_setting_bool(value, default=True)


def set_item_confirmations_enabled(enabled):
    set_tavern_setting(
        ITEM_CONFIRMATIONS_SETTING_KEY,
        "1" if enabled else "0",
        datetime.now(timezone.utc).isoformat()
    )


def build_confirmation_control_embed():
    enabled = item_confirmations_enabled()

    embed = discord.Embed(
        title="⚙️ Tavern Confirmation Messages",
        description=(
            f"Private success confirmations are currently: {format_enabled_status(enabled)}\n\n"
            "This controls small success messages after public item actions, like:\n"
            "• 🎭 Mischief deployed\n"
            "• 🔊 Sound attack posted\n\n"
            "Error, refund, cooldown, and permission messages will still show."
        ),
        color=discord.Color.gold()
    )

    embed.set_footer(text="Founder only.")
    return embed


def build_pack_control_embed():
    lines = []
    mix_collections = get_tavern_mix_enabled_collections()

    for pack_id, pack in STICKER_PACKS.items():
        purchase_enabled, tavern_mix_enabled = get_sticker_pack_flags(pack_id)

        if pack.get("uses_tavern_mix_pool", False):
            mix_text = "Uses enabled mix collections"
            if mix_collections:
                mix_text += f": {', '.join(sorted(mix_collections))}"
            else:
                mix_text += ": none"
        else:
            mix_text = format_enabled_status(tavern_mix_enabled)

        lines.append(
            f"**{pack['name']}** `/{pack_id}`\n"
            f"Purchase: {format_enabled_status(purchase_enabled)}\n"
            f"Tavern Mix: {mix_text}"
        )

    embed = discord.Embed(
        title="📦 Sticker Pack Control",
        description="\n\n".join(lines),
        color=discord.Color.gold()
    )

    embed.set_footer(text="Founder only. Collections remain viewable for players who own stickers.")
    return embed


def roll_sticker_from_pack(pack_id):
    pack = STICKER_PACKS[pack_id]
    allowed_collections = get_allowed_collections_for_pack(pack_id)

    if not allowed_collections:
        return None

    rarity_names = list(pack["weights"].keys())
    rarity_weights = list(pack["weights"].values())

    selected_rarity = random.choices(
        rarity_names,
        weights=rarity_weights,
        k=1
    )[0]

    possible_stickers = [
        sticker_id
        for sticker_id, sticker in STICKERS.items()
        if (
            sticker["collection"] in allowed_collections
            and sticker["rarity"] == selected_rarity
        )
    ]

    if not possible_stickers:
        possible_stickers = [
            sticker_id
            for sticker_id, sticker in STICKERS.items()
            if sticker["collection"] in allowed_collections
        ]

    return random.choice(possible_stickers)


def progress_line(current, total):
    percent = 0

    if total > 0:
        percent = (current / total) * 100

    return f"**{current} / {total}** • {percent:.0f}%"

def get_owned_mischief_items(user_id):
    rows = get_inventory_by_type(user_id, "mischief")

    owned = []

    for item_id, quantity in rows:
        if item_id in MISCHIEF_ITEMS and quantity > 0:
            owned.append((item_id, quantity))

    return owned


def get_owned_sound_items(user_id):
    rows = get_inventory_by_type(user_id, "sound")

    owned = []

    for sound_id, quantity in rows:
        if sound_id in SOUND_ITEMS and quantity > 0:
            owned.append((sound_id, quantity))

    return owned


def get_owned_gameplay_items(user_id):
    rows = get_inventory_by_type(user_id, "gameplay")

    owned = []

    for item_id, quantity in rows:
        if item_id in GAMEPLAY_ITEMS and quantity > 0:
            owned.append((item_id, quantity))

    return owned


def get_active_shield_tiers(user_id):
    active = []

    for item_id, shield in SHIELD_TIERS.items():
        count = get_player_effect_quantity(user_id, shield["effect_id"])

        if count > 0:
            active.append((item_id, shield, count))

    active.sort(key=lambda entry: entry[1]["priority"], reverse=True)
    return active


def get_active_lucky_shields(user_id):
    return sum(count for item_id, shield, count in get_active_shield_tiers(user_id))


def get_best_active_shield(user_id):
    active = get_active_shield_tiers(user_id)

    if not active:
        return None, None, 0

    return active[0]


def activate_shield_item(user_id, item_id):
    shield = SHIELD_TIERS.get(item_id)

    if not shield:
        return False

    removed = consume_inventory_item(user_id, item_id, 1)

    if not removed:
        return False

    add_player_effect(
        user_id,
        shield["effect_id"],
        1,
        datetime.now(timezone.utc).isoformat()
    )

    return True


def activate_lucky_shield(user_id):
    return activate_shield_item(user_id, "lucky_shield")


def try_lucky_shield_protection(user_id):
    item_id, shield, active_count = get_best_active_shield(user_id)

    if not shield or active_count <= 0:
        return False, False, None

    consumed = consume_player_effect(user_id, shield["effect_id"], 1)

    if not consumed:
        return False, False, None

    protected = random.random() < shield["chance"]
    return True, protected, shield


def lucky_shield_attempt_text(attempted, protected, loss_amount, shield=None):
    if not attempted:
        return ""

    shield_name = shield["name"] if shield else "🍀 Lucky Shield"

    if protected:
        return (
            f"\n{shield_name} **activated!** The loss was blocked and "
            f"**{loss_amount:,} gold** was saved."
        )

    return f"\n{shield_name} **shattered!** It failed to block the loss."


def lucky_shield_badge(user_id):
    item_id, shield, active_count = get_best_active_shield(user_id)
    total_count = get_active_lucky_shields(user_id)

    if not shield or total_count <= 0:
        return ""

    if total_count == 1:
        return f" {shield['name']} **SHIELDED**"

    return f" {shield['name']} **SHIELDED x{total_count}**"


def lucky_shield_status_text(user_id):
    active = get_active_shield_tiers(user_id)

    if not active:
        return ""

    lines = []

    for item_id, shield, count in active:
        percent = int(shield["chance"] * 100)
        lines.append(f"{shield['name']} x{count} — **{percent}%** loss protection")

    return (
        "🛡️ **ACTIVE SHIELD PROTECTION**\n"
        + "\n".join(lines)
        + "\nYour next possible gold loss will trigger your strongest active shield first."
    )


def lucky_shield_short_text(user_id):
    active = get_active_shield_tiers(user_id)

    if not active:
        return ""

    lines = []

    for item_id, shield, count in active:
        percent = int(shield["chance"] * 100)
        lines.append(f"{shield['name']} active x{count} — {percent}% loss protection")

    return "\n".join(lines)

def get_mischief_bonus_line(item_id):
    # 60% chance to add an extra line so the throws feel more alive.
    if random.random() > 0.60:
        return ""

    if item_id == "rotten_tomato":
        return random.choice([
            "\n\n💦 Oof, that one was extra juicy.",
            "\n\n🍅 Direct hit. Produce-based violence has occurred.",
            "\n\n😬 That tomato had emotional baggage.",
            "\n\n🧼 Someone get a mop. And maybe a therapist.",
            "\n\n🎯 The Tavern judges this throw as deeply unnecessary, but accurate.",
            "\n\n🤢 That tomato was absolutely past its expiration date.",
        ])

    if item_id == "cream_pie":
        return random.choice([
            "\n\n😳 The Tavern will not be commenting on where the whipped cream ended up.",
            "\n\n🫣 That pie hit dangerously close to HR territory.",
            "\n\n🥴 Someone get a towel. Actually... get two.",
            "\n\n😏 That was a very questionable use of dairy.",
            "\n\n🍰 The pie was consensual. The cleanup was not.",
            "\n\n🧁 Dessert has been weaponized.",
            "\n\n🙃 That pie had malicious intent.",
            "\n\n🧽 Cleanup crew has officially resigned.",
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


def build_mystery_box_result(attacker, target):
    outcome = random.choices(
        ["rotten_tomato", "cream_pie", "backfire", "confetti"],
        weights=[35, 35, 15, 15],
        k=1
    )[0]

    if outcome in ["rotten_tomato", "cream_pie"]:
        return build_mischief_result_embed(attacker, target, outcome), outcome

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
        return embed, None

    embed = discord.Embed(
        title="✨ Confetti Dud!",
        description=(
            f"**{attacker.display_name}** opened the Mystery Box...\n\n"
            "A sad little puff of confetti fell out. That was it."
        ),
        color=discord.Color.light_grey()
    )

    if CONFETTI_DUD_GIF:
        embed.set_image(url=CONFETTI_DUD_GIF)

    return embed, None


def build_mystery_box_embed(attacker, target):
    embed, stat_item_id = build_mystery_box_result(attacker, target)
    return embed

def get_shot_gif_url():
    if not SHOT_GIF_FILES:
        return ""

    file_name = random.choice(SHOT_GIF_FILES).strip()

    if not file_name:
        return ""

    return f"{GIF_ASSET_BASE_URL}/shots/{file_name}"


def build_tavern_shot_embed(user):
    shot_lines = [
        "The Tavern poured a shot. Questionable decisions may follow.",
        "A shot has entered the chat. Hydration has left it.",
        "The bartender has stopped asking questions.",
        "One tiny glass. One large mistake.",
        "The Tavern acknowledges this as a liquid bad idea.",
        "Someone yelled shots and unfortunately the bot listened.",
    ]

    embed = discord.Embed(
        title="🥃 Tavern Shot!",
        description=(
            f"**{user.display_name}** took a Tavern shot.\n\n"
            f"{random.choice(shot_lines)}"
        ),
        color=discord.Color.dark_gold()
    )

    gif_url = get_shot_gif_url()

    if gif_url:
        embed.set_image(url=gif_url)

    embed.set_footer(text="Shot GIFs are pulled from the GitHub repo.")
    return embed


def get_tavern_shot_definition():
    return SHOT_ITEMS["tavern_shot"]


def get_tavern_shot_price(user_id):
    shot = get_tavern_shot_definition()
    return get_discounted_shop_price(user_id, shot["price"])


def format_tavern_shot_price(user_id):
    shot = get_tavern_shot_definition()
    return format_shop_price(user_id, shot["price"])


async def buy_and_pour_tavern_shot(interaction, allowed_user_ids=None):
    if allowed_user_ids is not None and interaction.user.id not in allowed_user_ids:
        await interaction.response.send_message(
            "🥃 Only players sitting at this table can order a shot here.",
            ephemeral=True
        )
        return

    if is_math_drill_active(interaction.channel_id):
        await interaction.response.send_message(
            math_focus_block_text(interaction.channel_id),
            ephemeral=True
        )
        return

    if is_shop_channel(interaction):
        await interaction.response.send_message(
            "🥃 Shots are public and rowdy. Use them from a Tavern table so the shop channel stays clean.",
            ephemeral=True
        )
        return

    if interaction.channel is None:
        await interaction.response.send_message(
            "🥃 I could not find a public channel to post the shot in. You were not charged.",
            ephemeral=True
        )
        return

    shot = get_tavern_shot_definition()
    price = get_tavern_shot_price(interaction.user.id)
    balance = get_balance(interaction.user.id)

    if balance < price:
        await interaction.response.send_message(
            f"You need **{price:,} gold** to order {shot['name']}.\n"
            f"Your balance is **{balance:,} gold**.",
            ephemeral=True
        )
        return

    await interaction.response.defer(ephemeral=True)

    embed = build_tavern_shot_embed(interaction.user)

    try:
        public_message = await interaction.channel.send(embed=embed)
    except Exception as error:
        await interaction.followup.send(
            f"🥃 Shot failed before charging you: `{error}`",
            ephemeral=True
        )
        return

    add_gold(interaction.user.id, -price)
    new_balance = get_balance(interaction.user.id)
    tasks_snapshot, task_rewarded, task_xp_info = apply_daily_task_progress(interaction.user.id, "take_shot")
    task_reward_text = daily_task_reward_text(task_rewarded, task_xp_info)

    if task_reward_text:
        await interaction.followup.send(task_reward_text.strip(), ephemeral=True)
    elif item_confirmations_enabled():
        await interaction.followup.send(
            f"🥃 Shot poured for **{price:,} gold**: {public_message.jump_url}\n"
            f"💰 New balance: **{new_balance:,} gold**.",
            ephemeral=True
        )
    else:
        # For button interactions, deleting the original response deletes the table message.
        # The interaction was already acknowledged with defer(), so leave the table intact.
        pass


async def use_tavern_shot(interaction):
    await buy_and_pour_tavern_shot(interaction)

def get_sound_file_path(sound_id):
    sound = SOUND_ITEMS.get(sound_id)

    if not sound:
        return ""

    file_name = sound.get("file", "").strip()

    if not file_name:
        return ""

    return os.path.join(SOUND_ASSET_FOLDER, file_name)


def get_sound_attack_cooldown_remaining(user_id, sound_id):
    key = (user_id, sound_id)
    cooldown_until = SOUND_ATTACK_COOLDOWNS.get(key, 0)
    remaining = int(cooldown_until - time.time())
    return max(0, remaining)


def mark_sound_attack_used(user_id, sound_id):
    key = (user_id, sound_id)
    SOUND_ATTACK_COOLDOWNS[key] = time.time() + SOUND_ATTACK_COOLDOWN_SECONDS


def build_sound_target_embed(user_id, sound_id):
    sound = SOUND_ITEMS.get(sound_id)

    if not sound:
        return discord.Embed(
            title="🔊 Sound Attack",
            description="That sound does not exist.",
            color=discord.Color.gold()
        )

    embed = discord.Embed(
        title="🎯 Pick a Sound Target",
        description=(
            f"Using: **{sound['name']}**\n\n"
            "Choose who gets publicly subjected to this questionable audio."
        ),
        color=discord.Color.gold()
    )

    embed.set_footer(text="No @everyone. No @here. Just one poor victim.")
    return embed


def build_sound_play_embed(user, sound_id, target=None, file_ready=True):
    sound = SOUND_ITEMS.get(sound_id)

    if not sound:
        return discord.Embed(
            title="🔊 Sound Board",
            description="That sound does not exist.",
            color=discord.Color.gold()
        )

    attack_line = random.choice(sound.get("attack_lines", [sound.get("description", "")]))

    if target:
        description = (
            f"**{user.display_name}** has subjected **{target.display_name}** "
            f"to **{sound['name']}**.\n\n"
            f"{attack_line}"
        )
    else:
        description = (
            f"**{user.display_name}** {sound.get('message', 'played a sound.')}\n\n"
            f"{attack_line}"
        )

    if file_ready:
        description += "\n\n▶️ Press play on the attached audio below."
    else:
        description += (
            "\n\n⚠️ The sound file is missing from the repo. "
            "Upload it to `assets/sounds/` and redeploy."
        )

    embed = discord.Embed(
        title=sound.get("attack_title", f"🔊 {sound['name']}"),
        description=description,
        color=discord.Color.dark_gold()
    )

    if target:
        embed.set_thumbnail(url=target.display_avatar.url)

    embed.set_footer(text="The Tavern is not responsible for emotional damage.")
    return embed


async def play_soundboard_sound(interaction, sound_id, target_user=None):
    if is_math_drill_active(interaction.channel_id):
        await interaction.response.send_message(
            math_focus_block_text(interaction.channel_id),
            ephemeral=True
        )
        return

    sound = SOUND_ITEMS.get(sound_id)

    if not sound:
        await interaction.response.send_message(
            "That sound does not exist.",
            ephemeral=True
        )
        return

    if not player_owns_item(interaction.user.id, sound_id):
        await interaction.response.send_message(
            "You do not own that sound yet.",
            ephemeral=True
        )
        return

    if target_user and target_user.bot:
        await interaction.response.send_message(
            "The Tavern Bot refuses to be sound-attacked by its own customers.",
            ephemeral=True
        )
        return

    remaining = get_sound_attack_cooldown_remaining(interaction.user.id, sound_id)

    if remaining > 0:
        await interaction.response.send_message(
            f"🔊 That sound is on cooldown for **{remaining} more seconds**.",
            ephemeral=True
        )
        return

    file_path = get_sound_file_path(sound_id)
    file_name = sound.get("file", "sound.mp3").strip() or "sound.mp3"
    file_exists = bool(file_path and os.path.exists(file_path))
    embed = build_sound_play_embed(
        interaction.user,
        sound_id,
        target=target_user,
        file_ready=file_exists
    )

    mark_sound_attack_used(interaction.user.id, sound_id)

    await interaction.response.defer(ephemeral=True)

    content = None
    if target_user:
        content = f"{target_user.mention} 🐈‍⬛ you have been chosen by The Tavern."

    send_kwargs = {
        "content": content,
        "embed": embed,
        "allowed_mentions": discord.AllowedMentions(
            users=True,
            roles=False,
            everyone=False
        )
    }

    if file_exists:
        send_kwargs["file"] = discord.File(file_path, filename=file_name)

    public_message = await interaction.channel.send(**send_kwargs)

    if item_confirmations_enabled():
        await interaction.followup.send(
            f"🔊 Sound attack posted: {public_message.jump_url}",
            ephemeral=True
        )


async def send_usable_inventory_menu(interaction, allowed_target_ids=None):
    owned_mischief = get_owned_mischief_items(interaction.user.id)
    owned_gameplay = get_owned_gameplay_items(interaction.user.id)
    owned_sounds = get_owned_sound_items(interaction.user.id)

    if not owned_mischief and not owned_gameplay and not owned_sounds:
        await interaction.response.send_message(
            "🎭 You do not have any usable items or sounds yet.\n\n"
            "Buy some from the **Mischief Market** or **Sound Shop** first.",
            ephemeral=True
        )
        return

    lines = []

    if owned_mischief:
        lines.append("**🎭 Mischief**")
        for item_id, quantity in owned_mischief:
            item = MISCHIEF_ITEMS.get(item_id)
            if item:
                lines.append(f"{item['name']} x{quantity}")

    if owned_gameplay:
        if lines:
            lines.append("")
        lines.append("**🍀 Gameplay Items**")
        for item_id, quantity in owned_gameplay:
            item = GAMEPLAY_ITEMS.get(item_id)
            if item:
                lines.append(f"{item['name']} x{quantity}")

    active_shields = get_active_lucky_shields(interaction.user.id)
    if active_shields > 0:
        if lines:
            lines.append("")
        lines.append("**🍀 ACTIVE PROTECTION**")
        lines.append(lucky_shield_short_text(interaction.user.id))

    if owned_sounds:
        if lines:
            lines.append("")
        lines.append("**🔊 Sound Attacks**")
        for sound_id, quantity in owned_sounds:
            sound = SOUND_ITEMS.get(sound_id)
            if sound:
                lines.append(sound["name"])

    embed = discord.Embed(
        title="🎒 Use Tavern Item",
        description=(
            "Choose something from your Tavern inventory.\n\n"
            f"{chr(10).join(lines)}"
        ),
        color=discord.Color.gold()
    )

    embed.set_footer(text="Consumables and sounds are public. Lucky Shield arms your next possible loss.")

    await interaction.response.send_message(
        embed=embed,
        view=UseConsumableSelectView(
            owner_id=interaction.user.id,
            allowed_target_ids=allowed_target_ids,
            include_sounds=True,
            include_gameplay=True
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
        xp_info = award_tavern_xp(player_id, amount, "blackjack")

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

                shield_line = ""
                if get_active_lucky_shields(player_id) > 0:
                    shield_line = f"\n{lucky_shield_short_text(player_id)}"

                description += (
                    f"**<@{player_id}>{hand_label}** {marker}{lucky_shield_badge(player_id)}\n"
                    f"{cards}\n"
                    f"Total: **{total}** | Bet: **{bet:,} gold**{shield_line}\n\n"
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
                    shield_attempted, shield_protected, shield_used = try_lucky_shield_protection(player_id)

                    if shield_protected:
                        adjust_gold(player_id, bet)
                        result = f"{hand_label} bust — lost **0 gold**"
                    else:
                        result = f"{hand_label} bust — lost **{bet:,} gold**"
                        update_biggest_loss(player_id, bet)

                    result += lucky_shield_attempt_text(shield_attempted, shield_protected, bet, shield_used)
                    record_game_stat(player_id, "loss")
                    xp_info = self.award_xp(player_id, 10)
                    result += xp_result_text(xp_info)

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
                    shield_attempted, shield_protected, shield_used = try_lucky_shield_protection(player_id)

                    if shield_protected:
                        adjust_gold(player_id, bet)
                        result = f"{hand_label} lost the hand — lost **0 gold**"
                    else:
                        result = f"{hand_label} lost **{bet:,} gold**"
                        update_biggest_loss(player_id, bet)

                    result += lucky_shield_attempt_text(shield_attempted, shield_protected, bet, shield_used)
                    record_game_stat(player_id, "loss")
                    xp_info = self.award_xp(player_id, 10)
                    result += xp_result_text(xp_info)

                else:
                    adjust_gold(player_id, bet)
                    result = f"{hand_label} push"
                    record_game_stat(player_id, "push")
                    xp_info = self.award_xp(player_id, 5)
                    result += xp_result_text(xp_info)

                tasks_snapshot, task_rewarded, task_xp_info = apply_daily_task_progress(player_id, "play_game")
                if task_rewarded:
                    if task_xp_info and task_xp_info.get("level_up"):
                        self.level_ups.append((player_id, task_xp_info))
                    result += daily_task_reward_text(task_rewarded, task_xp_info)

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

    @discord.ui.button(label="Take Shot", emoji="🥃", style=discord.ButtonStyle.secondary)
    async def take_shot_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await buy_and_pour_tavern_shot(
            interaction,
            allowed_user_ids=self.players
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


    @discord.ui.button(label="Take Shot", emoji="🥃", style=discord.ButtonStyle.secondary)
    async def take_shot_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await buy_and_pour_tavern_shot(
            interaction,
            allowed_user_ids=self.players
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

    def build_table_embed(self):
        player_list = "\n".join(
            [format_table_player(player_id) for player_id in self.players]
        )

        if self.bot_added:
            player_list += "\n- 🤖 Tavern Bot"


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
                "Each player takes **3 turns** rolling one die at a time.\n"
                "Highest total after all 3 rolls wins."
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

    @discord.ui.button(label="Take Shot", emoji="🥃", style=discord.ButtonStyle.secondary)
    async def take_shot_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await buy_and_pour_tavern_shot(
            interaction,
            allowed_user_ids=self.players
        )

    @discord.ui.button(label="Use Consumable", emoji="🎭", style=discord.ButtonStyle.secondary)
    async def use_consumable_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await send_usable_inventory_menu(
            interaction,
            allowed_target_ids=self.players
        )

    @discord.ui.button(label="Start Dice", emoji="▶️", style=discord.ButtonStyle.red)
    async def start_dice(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.host_id:
            await interaction.response.send_message(
                "Only the host can start the dice game.",
                ephemeral=True
            )
            return

        if len(self.players) < 2 and not self.bot_added:
            await interaction.response.send_message(
                "🎲 You need at least **one opponent** or the **bot player** before starting.",
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

        game_view = DiceGameView(
            host_id=self.host_id,
            players=self.players,
            bot_added=self.bot_added,
            bet=self.bet
        )

        await interaction.response.edit_message(
            embed=game_view.build_embed(),
            view=game_view
        )


class DiceGameView(discord.ui.View):
    def __init__(self, host_id, players, bot_added, bet):
        super().__init__(timeout=300)
        self.host_id = host_id
        self.players = list(players)
        self.bot_added = bot_added
        self.bet = bet
        self.rolls = {player_id: [] for player_id in self.players}
        self.bot_rolls = []
        self.turn_order = list(self.players)

        if self.bot_added:
            self.turn_order.append("bot")

        self.round_index = 0
        self.turn_index = 0
        self.level_ups = []

    async def on_error(self, interaction, error, item):
        import traceback
        traceback.print_exception(type(error), error, error.__traceback__)

        if not interaction.response.is_done():
            await interaction.response.send_message(
                f"Dice turn error: `{error}`",
                ephemeral=True
            )

    def award_xp(self, player_id, amount):
        xp_info = award_tavern_xp(player_id, amount, "dice")

        if xp_info and xp_info.get("level_up"):
            self.level_ups.append((player_id, xp_info))

        return xp_info

    def is_complete(self):
        return self.round_index >= 3

    def current_actor(self):
        if self.is_complete():
            return None

        return self.turn_order[self.turn_index]

    def current_turn_text(self):
        actor = self.current_actor()

        if actor == "bot":
            return f"🤖 Tavern Bot is rolling for round **{self.round_index + 1} / 3**."

        return f"<@{actor}> is up for round **{self.round_index + 1} / 3**."

    def advance_turn(self):
        self.turn_index += 1

        if self.turn_index >= len(self.turn_order):
            self.turn_index = 0
            self.round_index += 1

    def roll_for_actor(self, actor):
        roll = random.randint(1, 6)

        if actor == "bot":
            self.bot_rolls.append(roll)
        else:
            self.rolls[actor].append(roll)

        self.advance_turn()
        return roll

    def process_bot_turns(self):
        bot_rolls = []

        while not self.is_complete() and self.current_actor() == "bot":
            bot_rolls.append(self.roll_for_actor("bot"))

        return bot_rolls

    def format_rolls(self, values):
        shown = [str(value) for value in values]

        while len(shown) < 3:
            shown.append("—")

        return " + ".join(shown)

    def build_embed(self, last_roll_text=""):
        description = f"**Bet:** {self.bet:,} gold\n\n"

        if last_roll_text:
            description += f"{last_roll_text}\n\n"

        if not self.is_complete():
            description += f"**Current Turn:** {self.current_turn_text()}\n\n"

        description += "**Roll Board:**\n"

        for player_id in self.players:
            player_rolls = self.rolls[player_id]
            total = sum(player_rolls)
            description += (
                f"<@{player_id}>{lucky_shield_badge(player_id)}: **{self.format_rolls(player_rolls)}** "
                f"= **{total}**\n"
            )

        if self.bot_added:
            description += (
                f"🤖 Tavern Bot: **{self.format_rolls(self.bot_rolls)}** "
                f"= **{sum(self.bot_rolls)}**\n"
            )

        description += "\nPress **Roll** when it is your turn."

        return discord.Embed(
            title="🎲 Dice Game",
            description=description,
            color=discord.Color.dark_gold()
        )

    def build_results_embed(self):
        totals = {
            player_id: sum(player_rolls)
            for player_id, player_rolls in self.rolls.items()
        }

        bot_total = sum(self.bot_rolls) if self.bot_added else None
        all_totals = list(totals.values())

        if bot_total is not None:
            all_totals.append(bot_total)

        highest = max(all_totals)

        human_winners = [
            player_id for player_id, total in totals.items()
            if total == highest
        ]

        bot_wins = self.bot_added and bot_total == highest

        description = f"**Bet:** {self.bet:,} gold\n\n**Final Rolls:**\n"

        for player_id in self.players:
            player_rolls = self.rolls[player_id]
            roll_text = " + ".join(str(roll) for roll in player_rolls)
            description += f"<@{player_id}>{lucky_shield_badge(player_id)} rolled **{roll_text} = {sum(player_rolls)}**\n"

        if self.bot_added:
            roll_text = " + ".join(str(roll) for roll in self.bot_rolls)
            description += f"🤖 Tavern Bot rolled **{roll_text} = {bot_total}**\n"

        description += "\n**Results:**\n"

        pot = len(self.players) * self.bet

        if self.bot_added:
            pot += self.bet

        if bot_wins and not human_winners:
            for player_id in self.players:
                shield_attempted, shield_protected, shield_used = try_lucky_shield_protection(player_id)

                if shield_protected:
                    record_game_stat(player_id, "loss")
                    xp_info = self.award_xp(player_id, 10)
                    result = "Lost the round, but lost **0 gold**"
                    result += lucky_shield_attempt_text(shield_attempted, shield_protected, self.bet, shield_used)
                else:
                    record_game_result(player_id, "loss", -self.bet)
                    xp_info = self.award_xp(player_id, 10)
                    update_biggest_loss(player_id, self.bet)
                    result = f"Lost **{self.bet:,} gold**"
                    result += lucky_shield_attempt_text(shield_attempted, shield_protected, self.bet, shield_used)

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
                    xp_info = self.award_xp(player_id, 25)
                    update_biggest_win(player_id, winnings)

                    result = (
                        f"Won the **{pot:,} gold** pot! "
                        f"Net gain: **{winnings:,} gold**"
                    )
                    result += xp_result_text(xp_info)

                else:
                    shield_attempted, shield_protected, shield_used = try_lucky_shield_protection(player_id)

                    if shield_protected:
                        record_game_stat(player_id, "loss")
                        xp_info = self.award_xp(player_id, 10)
                        result = "Lost the round, but lost **0 gold**"
                        result += lucky_shield_attempt_text(shield_attempted, shield_protected, self.bet, shield_used)
                    else:
                        record_game_result(player_id, "loss", -self.bet)
                        xp_info = self.award_xp(player_id, 10)
                        update_biggest_loss(player_id, self.bet)
                        result = f"Lost **{self.bet:,} gold**"
                        result += lucky_shield_attempt_text(shield_attempted, shield_protected, self.bet, shield_used)

                    result += xp_result_text(xp_info)

                tasks_snapshot, task_rewarded, task_xp_info = apply_daily_task_progress(player_id, "play_game")
                if task_rewarded:
                    if task_xp_info and task_xp_info.get("level_up"):
                        self.level_ups.append((player_id, task_xp_info))
                    result += daily_task_reward_text(task_rewarded, task_xp_info)

                result = add_achievement_text(player_id, result)
                description += f"<@{player_id}>: **{result}**\n"

        else:
            for player_id in self.players:
                record_game_result(player_id, "push", 0)
                xp_info = self.award_xp(player_id, 5)

                result = "Push"
                result += xp_result_text(xp_info)
                result = add_achievement_text(player_id, result)

                description += f"<@{player_id}>: **{result}**\n"

            description += f"\nTie! The **{pot:,} gold** pot is pushed."

        return discord.Embed(
            title="🎲 Dice Results",
            description=description,
            color=discord.Color.dark_gold()
        )

    @discord.ui.button(label="Take Shot", emoji="🥃", style=discord.ButtonStyle.secondary)
    async def take_shot_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await buy_and_pour_tavern_shot(
            interaction,
            allowed_user_ids=self.players
        )

    @discord.ui.button(label="Roll", emoji="🎲", style=discord.ButtonStyle.red)
    async def roll_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        actor = self.current_actor()

        if actor is None:
            await interaction.response.send_message(
                "This dice game is already finished.",
                ephemeral=True
            )
            return

        if actor == "bot":
            self.process_bot_turns()
        elif interaction.user.id != actor:
            await interaction.response.send_message(
                "It is not your dice turn.",
                ephemeral=True
            )
            return
        else:
            rolled = self.roll_for_actor(actor)
            last_roll_text = f"🎲 <@{actor}> rolled **{rolled}**."
            bot_rolls = self.process_bot_turns()

            if bot_rolls:
                last_roll_text += "\n🤖 Tavern Bot rolled " + ", ".join(f"**{roll}**" for roll in bot_rolls) + "."

            if self.is_complete():
                await interaction.response.edit_message(
                    embed=self.build_results_embed(),
                    view=PlayAgainView("Dice")
                )
                await send_level_up_messages(interaction, self.level_ups)
                return

            await interaction.response.edit_message(
                embed=self.build_embed(last_roll_text),
                view=self
            )



class MathAnswerButton(discord.ui.Button):
    def __init__(self, value):
        super().__init__(
            label=str(value),
            style=discord.ButtonStyle.blurple,
            row=0
        )
        self.value = value

    async def callback(self, interaction: discord.Interaction):
        view = self.view

        if not isinstance(view, MathDrillGameView):
            await interaction.response.send_message(
                "This math button is no longer active.",
                ephemeral=True
            )
            return

        await view.handle_answer(interaction, self.value)


class MathDrillGameView(discord.ui.View):
    def __init__(self, player, difficulty_id, is_daily=False, challenge_date=""):
        super().__init__(timeout=300)
        self.player = player
        self.player_id = player.id
        self.difficulty_id = difficulty_id
        self.config = MATH_DRILL_DIFFICULTIES[difficulty_id]
        self.is_daily = is_daily
        self.challenge_date = challenge_date
        self.current_index = 0
        self.correct_count = 0
        self.wrong_count = 0
        self.current_streak = 0
        self.best_streak = 0
        self.fastest_answer_ms = 0
        self.total_answer_time_ms = 0
        self.timed_answer_count = 0
        self.question = ""
        self.answer = 0
        self.choices = []
        self.question_started_at = 0
        self.drill_started_at = time.monotonic()
        self.message = None
        self.timer_task = None
        self.finished = False
        self.lock_note = ""
        self.level_ups = []
        self.daily_task_text = ""
        self.next_question()

    def next_question(self):
        self.question, self.answer = generate_math_question(self.difficulty_id)
        self.choices = generate_math_choices(self.answer)
        self.question_started_at = time.monotonic()
        self.refresh_buttons()

    def refresh_buttons(self):
        self.clear_items()

        for choice in self.choices:
            self.add_item(MathAnswerButton(choice))

    def build_embed(self, timed_out=False, previous_answer=None):
        difficulty_name = f"{self.config['emoji']} {self.config['name']}"
        title = "🧠 Daily Math Challenge" if self.is_daily else "🧠 Math Drill"
        time_limit = self.config["time_limit"]

        status_lines = [
            f"Player: {self.player.mention}",
            f"Difficulty: **{difficulty_name}**",
            f"Question: **{self.current_index + 1}/{MATH_DRILL_TOTAL_QUESTIONS}**",
            f"Score: **{self.correct_count}/{self.current_index}** answered correctly so far",
            f"Time: **{time_limit}s** per question",
        ]

        if self.is_daily:
            status_lines.append(f"Daily perfect reward: **{DAILY_MATH_CHALLENGE_GOLD:,} gold**")
        else:
            status_lines.append(f"Perfect reward: **{self.config['perfect_gold']:,} gold**")

        if timed_out:
            status_lines.append(f"⏰ Previous question timed out. Correct answer was **{previous_answer}**.")

        if self.lock_note:
            status_lines.append(self.lock_note)

        embed = discord.Embed(
            title=title,
            description=(
                "\n".join(status_lines)
                + "\n\n"
                + f"### What is **{self.question}**?"
            ),
            color=discord.Color.gold()
        )

        embed.set_footer(text="Only the active player can answer. Pick one button.")
        return embed

    def build_result_embed(self, xp_info, gold_reward, new_achievements):
        difficulty_name = f"{self.config['emoji']} {self.config['name']}"
        perfect = self.correct_count == MATH_DRILL_TOTAL_QUESTIONS
        title = "🧠 Daily Math Challenge Complete" if self.is_daily else "🧠 Math Drill Complete"

        if perfect:
            outcome = "Perfect game! The Tavern braincell has been located."
        elif self.correct_count >= 3:
            outcome = "Solid run. The Tavern accepts this answer sheet."
        else:
            outcome = "Math happened. We are all trying our best."

        xp_text = xp_result_text(xp_info) if xp_info else ""
        gold_text = ""

        if gold_reward > 0:
            balance = get_balance(self.player_id)
            gold_text = f"\n💰 Perfect reward: **+{gold_reward:,} gold**\nNew balance: **{balance:,} gold**"
        elif self.is_daily:
            gold_text = f"\n💰 Daily challenge reward requires a perfect **5/5**."

        task_text = self.daily_task_text

        achievement_text = ""
        if new_achievements:
            achievement_text = (
                "\n🏆 Achievement Unlocked:\n"
                + "\n".join(new_achievements)
            )

        fastest_text = "No correct answers yet."
        if self.fastest_answer_ms > 0:
            fastest_text = f"{self.fastest_answer_ms / 1000:.2f}s"

        average_text = "None yet"
        if self.timed_answer_count > 0:
            average_text = f"{(self.total_answer_time_ms / self.timed_answer_count) / 1000:.2f}s"

        match_time_text = f"{(time.monotonic() - self.drill_started_at):.1f}s"

        embed = discord.Embed(
            title=title,
            description=(
                f"{self.player.mention}\n"
                f"{outcome}\n\n"
                f"Difficulty: **{difficulty_name}**\n"
                f"Score: **{self.correct_count}/{MATH_DRILL_TOTAL_QUESTIONS}**\n"
                f"Best Streak: **{self.best_streak}**\n"
                f"Fastest Correct Answer: **{fastest_text}**\n"
                f"Average Answer Time: **{average_text}**\n"
                f"Drill Time: **{match_time_text}**"
                f"{xp_text}"
                f"{gold_text}"
                f"{task_text}"
                f"{achievement_text}"
            ),
            color=discord.Color.gold() if perfect else discord.Color.blurple()
        )

        embed.set_footer(text="Math Focus released. Tavern chaos may resume.")
        return embed

    async def start_timer(self):
        if self.timer_task and not self.timer_task.done():
            self.timer_task.cancel()

        question_index = self.current_index
        self.timer_task = asyncio.create_task(self.question_timer(question_index))

    async def question_timer(self, question_index):
        try:
            await asyncio.sleep(self.config["time_limit"])
        except asyncio.CancelledError:
            return

        if self.finished or self.current_index != question_index:
            return

        previous_answer = self.answer
        self.wrong_count += 1
        self.current_streak = 0
        self.current_index += 1

        if self.current_index >= MATH_DRILL_TOTAL_QUESTIONS:
            await self.finish_from_timer()
            return

        self.next_question()

        if self.message:
            await self.message.edit(
                embed=self.build_embed(timed_out=True, previous_answer=previous_answer),
                view=self
            )

        await self.start_timer()

    async def handle_answer(self, interaction, selected_value):
        if interaction.user.id != self.player_id:
            await interaction.response.send_message(
                f"🧠 This is {self.player.mention}'s Math Drill. Let them cook.",
                ephemeral=True
            )
            return

        if self.finished:
            await interaction.response.send_message(
                "This Math Drill is already finished.",
                ephemeral=True
            )
            return

        if self.timer_task and not self.timer_task.done():
            self.timer_task.cancel()

        elapsed_ms = int((time.monotonic() - self.question_started_at) * 1000)
        self.total_answer_time_ms += elapsed_ms
        self.timed_answer_count += 1
        was_correct = selected_value == self.answer

        if was_correct:
            self.correct_count += 1
            self.current_streak += 1
            self.best_streak = max(self.best_streak, self.current_streak)

            if self.fastest_answer_ms == 0 or elapsed_ms < self.fastest_answer_ms:
                self.fastest_answer_ms = elapsed_ms
        else:
            self.wrong_count += 1
            self.current_streak = 0

        self.current_index += 1

        if self.current_index >= MATH_DRILL_TOTAL_QUESTIONS:
            await self.finish(interaction)
            return

        self.next_question()
        await interaction.response.edit_message(
            embed=self.build_embed(),
            view=self
        )
        await self.start_timer()

    async def finish_from_timer(self):
        if self.finished:
            return

        self.finished = True
        self.clear_items()
        xp_info, gold_reward, new_achievements = self.apply_rewards()

        if self.message:
            await self.message.edit(
                embed=self.build_result_embed(xp_info, gold_reward, new_achievements),
                view=self
            )

        await self.cleanup()

    async def finish(self, interaction):
        if self.finished:
            return

        self.finished = True
        self.clear_items()
        xp_info, gold_reward, new_achievements = self.apply_rewards()

        await interaction.response.edit_message(
            embed=self.build_result_embed(xp_info, gold_reward, new_achievements),
            view=self
        )

        await self.cleanup()
        await send_level_up_messages(interaction, self.level_ups)

    def apply_rewards(self):
        perfect = self.correct_count == MATH_DRILL_TOTAL_QUESTIONS
        base_xp = self.correct_count * self.config["xp_per_correct"]
        xp_info = None
        gold_reward = 0

        if base_xp > 0:
            xp_info = award_tavern_xp(self.player_id, base_xp, "math")

            if xp_info and xp_info.get("level_up"):
                self.level_ups.append((self.player_id, xp_info))

        if perfect:
            gold_reward = DAILY_MATH_CHALLENGE_GOLD if self.is_daily else self.config["perfect_gold"]
            adjust_gold(self.player_id, gold_reward)

        record_math_drill_result(
            self.player_id,
            self.difficulty_id,
            self.correct_count,
            self.wrong_count,
            perfect,
            self.best_streak,
            self.fastest_answer_ms,
            self.is_daily,
            self.total_answer_time_ms,
            self.timed_answer_count,
            int((time.monotonic() - self.drill_started_at) * 1000),
            self.challenge_date,
        )

        task_text = ""
        for task_key in ["play_game", "complete_math"]:
            tasks_snapshot, task_rewarded, task_xp_info = apply_daily_task_progress(self.player_id, task_key)
            if task_rewarded:
                if task_xp_info and task_xp_info.get("level_up"):
                    self.level_ups.append((self.player_id, task_xp_info))
                task_text += daily_task_reward_text(task_rewarded, task_xp_info)

        self.daily_task_text = task_text
        new_achievements = check_achievements(self.player_id)
        return xp_info, gold_reward, new_achievements

    async def cleanup(self):
        if self.timer_task and not self.timer_task.done():
            self.timer_task.cancel()

        MATH_ACTIVE_CHANNELS.pop(self.message.channel.id if self.message else 0, None)
        MATH_ACTIVE_USERS.discard(self.player_id)

        if self.message:
            await release_math_channel_focus(self.message.channel.id)

    async def on_timeout(self):
        if self.finished:
            return

        self.finished = True
        self.clear_items()

        if self.message:
            embed = discord.Embed(
                title="🧠 Math Drill Timed Out",
                description=f"{self.player.mention}'s Math Drill was abandoned. Math Focus released.",
                color=discord.Color.light_grey()
            )
            await self.message.edit(embed=embed, view=self)
            await release_math_channel_focus(self.message.channel.id)
            MATH_ACTIVE_CHANNELS.pop(self.message.channel.id, None)

        MATH_ACTIVE_USERS.discard(self.player_id)


class MathDrillStartView(discord.ui.View):
    def __init__(self, owner_id):
        super().__init__(timeout=180)
        self.owner_id = owner_id

    async def interaction_check(self, interaction):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message(
                "This Math Drill menu belongs to someone else. Use The Tavern menu to start your own.",
                ephemeral=True
            )
            return False

        return True

    async def begin_drill(self, interaction, difficulty_id, is_daily=False):
        can_start, message = can_start_math_drill(interaction)

        if not can_start:
            await interaction.response.send_message(message, ephemeral=True)
            return

        challenge_date = ""

        if is_daily:
            challenge_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

            if get_last_daily_math_challenge(interaction.user.id) == challenge_date:
                await interaction.response.send_message(
                    "🧠 You already attempted today's Daily Math Challenge. Try again tomorrow.",
                    ephemeral=True
                )
                return

        await interaction.response.defer(ephemeral=True, thinking=True)

        view = MathDrillGameView(
            interaction.user,
            difficulty_id,
            is_daily=is_daily,
            challenge_date=challenge_date
        )

        MATH_ACTIVE_CHANNELS[interaction.channel_id] = {
            "player_id": interaction.user.id,
            "started_at": time.time(),
        }
        MATH_ACTIVE_USERS.add(interaction.user.id)

        view.lock_note = await start_math_channel_focus(interaction, interaction.user.id)

        try:
            message = await interaction.channel.send(
                embed=view.build_embed(),
                view=view
            )
        except Exception as error:
            MATH_ACTIVE_CHANNELS.pop(interaction.channel_id, None)
            MATH_ACTIVE_USERS.discard(interaction.user.id)
            await release_math_channel_focus(interaction.channel_id)
            await interaction.followup.send(
                f"🧠 I could not start the Math Drill: `{error}`",
                ephemeral=True
            )
            return

        view.message = message
        await view.start_timer()

        await interaction.followup.send(
            f"🧠 Math Drill started: {message.jump_url}",
            ephemeral=True
        )

    @discord.ui.button(label="Easy", emoji="🟢", style=discord.ButtonStyle.green)
    async def easy_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.begin_drill(interaction, "easy")

    @discord.ui.button(label="Medium", emoji="🟡", style=discord.ButtonStyle.blurple)
    async def medium_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.begin_drill(interaction, "medium")

    @discord.ui.button(label="Hard", emoji="🔴", style=discord.ButtonStyle.red)
    async def hard_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.begin_drill(interaction, "hard")

    @discord.ui.button(label="Daily Challenge", emoji="🏆", style=discord.ButtonStyle.gray)
    async def daily_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.begin_drill(interaction, "hard", is_daily=True)


def build_math_drill_start_embed(user_id):
    daily_status = "Available now"
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    if get_last_daily_math_challenge(user_id) == today:
        daily_status = "Already attempted today"

    embed = discord.Embed(
        title="🧠 Math Drills",
        description=(
            "Answer **5 timed multiple-choice questions**.\n"
            "Only one player can drill in the channel at a time.\n\n"
            "**Easy** — +5 XP per correct answer, +5 gold for perfect\n"
            "**Medium** — +8 XP per correct answer, +10 gold for perfect\n"
            "**Hard** — +12 XP per correct answer, +15 gold for perfect\n\n"
            f"🏆 **Daily Hard Challenge:** {daily_status}\n"
            f"Perfect daily challenge reward: **{DAILY_MATH_CHALLENGE_GOLD:,} gold**"
        ),
        color=discord.Color.gold()
    )

    embed.set_footer(text="Math Focus pauses chat when the bot has Manage Channels.")
    return embed


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

        if is_math_drill_active(interaction.channel_id):
            await interaction.response.send_message(
                math_focus_block_text(interaction.channel_id),
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



def clean_hangman_word(value):
    return (value or "").strip().lower()


def load_hangman_words():
    global HANGMAN_WORD_CACHE

    if HANGMAN_WORD_CACHE is not None:
        return HANGMAN_WORD_CACHE

    words = set()

    if not os.path.isdir(HANGMAN_WORDS_FOLDER):
        HANGMAN_WORD_CACHE = words
        return words

    for root, dirs, files in os.walk(HANGMAN_WORDS_FOLDER):
        for file_name in files:
            if not file_name.lower().endswith(".txt"):
                continue

            path = os.path.join(root, file_name)

            try:
                with open(path, "r", encoding="utf-8") as word_file:
                    for line in word_file:
                        word = clean_hangman_word(line)

                        if (
                            word.isalpha()
                            and HANGMAN_MIN_WORD_LENGTH <= len(word) <= HANGMAN_MAX_WORD_LENGTH
                        ):
                            words.add(word)
            except Exception:
                continue

    HANGMAN_WORD_CACHE = words
    return words


def validate_hangman_word(word):
    cleaned = clean_hangman_word(word)

    if not cleaned:
        return False, "Enter a word first.", cleaned

    if not cleaned.isalpha():
        return False, "Words can only use letters. No spaces, hyphens, apostrophes, or numbers.", cleaned

    if len(cleaned) < HANGMAN_MIN_WORD_LENGTH or len(cleaned) > HANGMAN_MAX_WORD_LENGTH:
        return False, f"Words must be {HANGMAN_MIN_WORD_LENGTH}-{HANGMAN_MAX_WORD_LENGTH} letters long.", cleaned

    valid_words = load_hangman_words()

    if not valid_words:
        return False, "The Hangman word list could not be loaded from `assets/words/`.", cleaned

    if cleaned not in valid_words:
        return False, "That word was not found in the Tavern word list.", cleaned

    return True, "", cleaned


def get_random_hangman_word():
    valid_words = list(load_hangman_words())

    if not valid_words:
        return ""

    return random.choice(valid_words)


def get_hangman_stage_image_url(mistakes):
    mistakes = max(0, min(HANGMAN_MAX_MISTAKES, int(mistakes)))
    return f"{IMAGE_ASSET_BASE_URL}/hangman/stage_{mistakes}.png"


def hangman_board_text(word, guessed_letters):
    return " ".join(
        letter.upper() if letter in guessed_letters else "_"
        for letter in word
    )


def format_hangman_guessers(guessers):
    if not guessers:
        return "Open"

    return "\n".join(
        f"{index}. <@{player_id}>"
        for index, player_id in enumerate(guessers, start=1)
    )


def is_hangman_active(channel_id):
    return channel_id in HANGMAN_ACTIVE_CHANNELS


def hangman_active_text(channel_id):
    game = HANGMAN_ACTIVE_CHANNELS.get(channel_id)

    if not game:
        return "🪦 A Hangman game is active in this channel."

    return "🪦 A Hangman game is active in this channel. Finish that game before starting another."


class HangmanWordModal(discord.ui.Modal, title="🪦 Undertaker Word"):
    def __init__(self, lobby_view):
        super().__init__(timeout=180)
        self.lobby_view = lobby_view

        self.word_input = discord.ui.TextInput(
            label="Hidden word",
            placeholder="4-12 letters, real word only",
            min_length=HANGMAN_MIN_WORD_LENGTH,
            max_length=HANGMAN_MAX_WORD_LENGTH,
            required=True
        )
        self.add_item(self.word_input)

    async def on_submit(self, interaction: discord.Interaction):
        if interaction.user.id != self.lobby_view.undertaker_id:
            await interaction.response.send_message(
                "Only the Undertaker can set the hidden word.",
                ephemeral=True
            )
            return

        is_valid, message, word = validate_hangman_word(str(self.word_input.value))

        if not is_valid:
            await interaction.response.send_message(
                f"🚫 {message}",
                ephemeral=True
            )
            return

        self.lobby_view.word = word
        self.lobby_view.word_set_by = interaction.user.id

        if self.lobby_view.message:
            try:
                await self.lobby_view.message.edit(
                    embed=self.lobby_view.build_lobby_embed(),
                    view=self.lobby_view
                )
            except Exception:
                pass

        await interaction.response.send_message(
            "🪦 Word accepted. The host can start the game when ready.",
            ephemeral=True
        )


class HangmanStartView(discord.ui.View):
    def __init__(self, owner_id):
        super().__init__(timeout=180)
        self.owner_id = owner_id

    async def interaction_check(self, interaction):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message(
                "Open your own Hangman menu from The Tavern.",
                ephemeral=True
            )
            return False

        return True

    @discord.ui.button(label="Solo", emoji="🧍", style=discord.ButtonStyle.green)
    async def solo_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if is_shop_channel(interaction):
            await interaction.response.send_message(
                "🪦 Hangman is public. Start it in The Tavern channel so the shop stays clean.",
                ephemeral=True
            )
            return

        if is_math_drill_active(interaction.channel_id):
            await interaction.response.send_message(
                math_focus_block_text(interaction.channel_id),
                ephemeral=True
            )
            return

        if is_hangman_active(interaction.channel_id):
            await interaction.response.send_message(
                hangman_active_text(interaction.channel_id),
                ephemeral=True
            )
            return

        word = get_random_hangman_word()

        if not word:
            await interaction.response.send_message(
                "🪦 I could not load any Hangman words from `assets/words/`.",
                ephemeral=True
            )
            return

        game_view = HangmanGameView(
            channel_id=interaction.channel_id,
            mode="solo",
            host_id=interaction.user.id,
            undertaker_id=None,
            guessers=[interaction.user.id],
            word=word
        )
        HANGMAN_ACTIVE_CHANNELS[interaction.channel_id] = game_view

        await interaction.response.defer(ephemeral=True)
        public_message = await interaction.channel.send(
            embed=game_view.build_game_embed(),
            view=game_view
        )
        game_view.message = public_message


    @discord.ui.button(label="Multiplayer", emoji="👥", style=discord.ButtonStyle.blurple)
    async def multiplayer_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if is_shop_channel(interaction):
            await interaction.response.send_message(
                "🪦 Hangman is public. Start it in The Tavern channel so the shop stays clean.",
                ephemeral=True
            )
            return

        if is_math_drill_active(interaction.channel_id):
            await interaction.response.send_message(
                math_focus_block_text(interaction.channel_id),
                ephemeral=True
            )
            return

        if is_hangman_active(interaction.channel_id):
            await interaction.response.send_message(
                hangman_active_text(interaction.channel_id),
                ephemeral=True
            )
            return

        lobby_view = HangmanLobbyView(
            channel_id=interaction.channel_id,
            host_id=interaction.user.id
        )
        HANGMAN_ACTIVE_CHANNELS[interaction.channel_id] = lobby_view

        await interaction.response.defer(ephemeral=True)
        public_message = await interaction.channel.send(
            embed=lobby_view.build_lobby_embed(),
            view=lobby_view
        )
        lobby_view.message = public_message



class HangmanLobbyView(discord.ui.View):
    def __init__(self, channel_id, host_id):
        super().__init__(timeout=900)
        self.channel_id = channel_id
        self.host_id = host_id
        self.undertaker_id = None
        self.guessers = []
        self.word = ""
        self.word_set_by = None
        self.message = None

    def build_lobby_embed(self):
        undertaker_text = "Open"
        if self.undertaker_id:
            undertaker_text = f"<@{self.undertaker_id}>"

        word_status = "Not set"
        if self.word:
            word_status = "✅ Set privately"

        embed = discord.Embed(
            title="🪦 Hangman Table",
            description=(
                f"**Host:** <@{self.host_id}>\n"
                f"**Undertaker:** {undertaker_text}\n"
                f"**Hidden Word:** {word_status}\n\n"
                f"**Guessers:**\n{format_hangman_guessers(self.guessers)}\n\n"
                "The host creates the table, but the Undertaker is chosen separately.\n"
                "The Undertaker must set a valid 4-12 letter word before the game starts."
            ),
            color=discord.Color.dark_gold()
        )
        embed.set_footer(text="Word rules: real word list only, letters only, no spaces/hyphens/names/abbreviations.")
        return embed

    async def interaction_check(self, interaction):
        if HANGMAN_ACTIVE_CHANNELS.get(self.channel_id) is not self:
            await interaction.response.send_message(
                "This Hangman table is no longer active.",
                ephemeral=True
            )
            return False

        return True

    async def on_timeout(self):
        if HANGMAN_ACTIVE_CHANNELS.get(self.channel_id) is self:
            HANGMAN_ACTIVE_CHANNELS.pop(self.channel_id, None)

    @discord.ui.button(label="Become Undertaker", emoji="🪦", style=discord.ButtonStyle.secondary)
    async def become_undertaker_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id in self.guessers:
            await interaction.response.send_message(
                "You cannot be both Undertaker and guesser.",
                ephemeral=True
            )
            return

        if self.undertaker_id and self.undertaker_id != interaction.user.id:
            await interaction.response.send_message(
                "The Undertaker slot is already taken.",
                ephemeral=True
            )
            return

        self.undertaker_id = interaction.user.id
        self.word = ""
        self.word_set_by = None

        await interaction.response.edit_message(
            embed=self.build_lobby_embed(),
            view=self
        )

    @discord.ui.button(label="Join Guessers", emoji="🔤", style=discord.ButtonStyle.green)
    async def join_guesser_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id == self.undertaker_id:
            await interaction.response.send_message(
                "The Undertaker cannot also be a guesser.",
                ephemeral=True
            )
            return

        if interaction.user.id in self.guessers:
            await interaction.response.send_message(
                "You are already guessing.",
                ephemeral=True
            )
            return

        if len(self.guessers) >= 3:
            await interaction.response.send_message(
                "This Hangman table already has 3 guessers.",
                ephemeral=True
            )
            return

        self.guessers.append(interaction.user.id)

        await interaction.response.edit_message(
            embed=self.build_lobby_embed(),
            view=self
        )

    @discord.ui.button(label="Set Word", emoji="✍️", style=discord.ButtonStyle.blurple)
    async def set_word_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.undertaker_id:
            await interaction.response.send_message(
                "Someone needs to become the Undertaker first.",
                ephemeral=True
            )
            return

        if interaction.user.id != self.undertaker_id:
            await interaction.response.send_message(
                "Only the Undertaker can set the hidden word.",
                ephemeral=True
            )
            return

        await interaction.response.send_modal(HangmanWordModal(self))

    @discord.ui.button(label="Start Game", emoji="▶️", style=discord.ButtonStyle.blurple)
    async def start_game_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.host_id:
            await interaction.response.send_message(
                "Only the table host can start the game.",
                ephemeral=True
            )
            return

        if not self.undertaker_id:
            await interaction.response.send_message(
                "The table needs an Undertaker first.",
                ephemeral=True
            )
            return

        if not self.guessers:
            await interaction.response.send_message(
                "The table needs at least one guesser.",
                ephemeral=True
            )
            return

        if not self.word:
            await interaction.response.send_message(
                "The Undertaker needs to set the hidden word first.",
                ephemeral=True
            )
            return

        game_view = HangmanGameView(
            channel_id=self.channel_id,
            mode="multiplayer",
            host_id=self.host_id,
            undertaker_id=self.undertaker_id,
            guessers=self.guessers,
            word=self.word
        )
        game_view.message = self.message
        HANGMAN_ACTIVE_CHANNELS[self.channel_id] = game_view

        await interaction.response.edit_message(
            embed=game_view.build_game_embed(),
            view=game_view
        )

    @discord.ui.button(label="Cancel", emoji="✖️", style=discord.ButtonStyle.red)
    async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.host_id:
            await interaction.response.send_message(
                "Only the table host can cancel this Hangman table.",
                ephemeral=True
            )
            return

        HANGMAN_ACTIVE_CHANNELS.pop(self.channel_id, None)
        await interaction.response.edit_message(
            embed=discord.Embed(
                title="🪦 Hangman Cancelled",
                description="The Hangman table was closed.",
                color=discord.Color.dark_gold()
            ),
            view=None
        )


class HangmanLetterButton(discord.ui.Button):
    def __init__(self, letter, row=None):
        super().__init__(
            label=letter,
            style=discord.ButtonStyle.secondary,
            custom_id=f"hangman_letter_{letter}_{random.randint(1, 999999)}",
            row=row
        )
        self.letter = letter.lower()

    async def callback(self, interaction: discord.Interaction):
        await self.view.handle_letter_guess(interaction, self.letter)


class HangmanPageButton(discord.ui.Button):
    def __init__(self, target_page, row=4):
        label = "Consonants" if target_page == "consonants" else "Vowels"
        emoji = "🔤" if target_page == "consonants" else "🅰️"
        super().__init__(
            label=label,
            emoji=emoji,
            style=discord.ButtonStyle.blurple,
            custom_id=f"hangman_page_{target_page}_{random.randint(1, 999999)}",
            row=row
        )
        self.target_page = target_page

    async def callback(self, interaction: discord.Interaction):
        # Store the view immediately. refresh_letter_buttons() clears/rebuilds the view,
        # which detaches this old button from self.view. Referencing self.view after that
        # causes an exception and Discord shows "Interaction failed."
        view = self.view

        if view is None:
            await interaction.response.send_message(
                "This Hangman button is stale. Start a fresh Hangman table.",
                ephemeral=True
            )
            return

        if HANGMAN_ACTIVE_CHANNELS.get(view.channel_id) is not view:
            await interaction.response.send_message(
                "This Hangman game is no longer active.",
                ephemeral=True
            )
            return

        if view.finished:
            await interaction.response.send_message(
                "This Hangman game is already finished.",
                ephemeral=True
            )
            return

        allowed_page_users = set(view.guessers)
        allowed_page_users.add(view.host_id)
        if view.undertaker_id:
            allowed_page_users.add(view.undertaker_id)

        if interaction.user.id not in allowed_page_users:
            await interaction.response.send_message(
                "Only players in this Hangman game can switch letter pages.",
                ephemeral=True
            )
            return

        view.page = self.target_page
        view.refresh_letter_buttons()

        await interaction.response.edit_message(
            embed=view.build_game_embed(),
            view=view
        )


class HangmanQuitButton(discord.ui.Button):
    def __init__(self, row=4):
        super().__init__(
            label="End Game",
            emoji="✖️",
            style=discord.ButtonStyle.red,
            custom_id=f"hangman_quit_{random.randint(1, 999999)}",
            row=row
        )

    async def callback(self, interaction: discord.Interaction):
        view = self.view

        if view is None:
            await interaction.response.send_message(
                "This Hangman button is stale. Start a fresh Hangman table.",
                ephemeral=True
            )
            return

        if interaction.user.id != view.host_id:
            await interaction.response.send_message(
                "Only the host can end this Hangman game.",
                ephemeral=True
            )
            return

        view.finished = True
        HANGMAN_ACTIVE_CHANNELS.pop(view.channel_id, None)
        view.clear_items()

        await interaction.response.edit_message(
            embed=discord.Embed(
                title="🪦 Hangman Ended",
                description="The host ended the Hangman game.",
                color=discord.Color.dark_gold()
            ),
            view=None
        )


class HangmanGameView(discord.ui.View):
    def __init__(self, channel_id, mode, host_id, undertaker_id, guessers, word):
        super().__init__(timeout=1200)
        self.channel_id = channel_id
        self.mode = mode
        self.host_id = host_id
        self.undertaker_id = undertaker_id
        self.guessers = list(guessers)
        self.word = clean_hangman_word(word)
        self.guessed_letters = set()
        self.wrong_letters = []
        self.mistakes = 0
        self.turn_index = 0
        self.page = "vowels"
        self.finished = False
        self.level_ups = []
        self.letter_guess_counts = {player_id: 0 for player_id in self.guessers}
        self.message = None
        self.refresh_letter_buttons()

    async def on_timeout(self):
        if HANGMAN_ACTIVE_CHANNELS.get(self.channel_id) is self:
            HANGMAN_ACTIVE_CHANNELS.pop(self.channel_id, None)

    def current_guesser_id(self):
        if not self.guessers:
            return None

        return self.guessers[self.turn_index % len(self.guessers)]

    def advance_turn(self):
        if self.guessers:
            self.turn_index = (self.turn_index + 1) % len(self.guessers)

    def can_user_use_game(self, interaction):
        if HANGMAN_ACTIVE_CHANNELS.get(self.channel_id) is not self:
            try:
                interaction.response.send_message("This Hangman game is no longer active.", ephemeral=True)
            except Exception:
                pass
            return False

        return True

    def refresh_letter_buttons(self):
        self.clear_items()
        letters = HANGMAN_VOWELS if self.page == "vowels" else HANGMAN_CONSONANTS

        # Explicit rows keep Discord from trying to reshuffle a full consonant page
        # and makes page swapping much more reliable. Row 4 is reserved for controls.
        button_index = 0
        for letter in letters:
            if letter.lower() in self.guessed_letters:
                continue

            row = min(button_index // 5, 3)
            self.add_item(HangmanLetterButton(letter, row=row))
            button_index += 1

        next_page = "consonants" if self.page == "vowels" else "vowels"
        self.add_item(HangmanPageButton(next_page, row=4))
        self.add_item(HangmanQuitButton(row=4))

    def build_game_embed(self, result_text=""):
        board = hangman_board_text(self.word, self.guessed_letters)
        wrong_text = ", ".join(letter.upper() for letter in self.wrong_letters) or "None"
        current_text = "Game over" if self.finished else f"<@{self.current_guesser_id()}>"
        undertaker_text = "🤖 Tavern Bot" if self.mode == "solo" else f"<@{self.undertaker_id}>"

        description = (
            f"**Word:** `{board}`\n"
            f"**Wrong Letters:** {wrong_text}\n"
            f"**Mistakes:** {self.mistakes} / {HANGMAN_MAX_MISTAKES}\n\n"
            f"**Undertaker:** {undertaker_text}\n"
            f"**Guessers:**\n{format_hangman_guessers(self.guessers)}\n\n"
            f"**Current Guesser:** {current_text}\n"
            f"**Letter Page:** {self.page.title()}"
        )

        if result_text:
            description += f"\n\n{result_text}"

        embed = discord.Embed(
            title="🪦 Hangman",
            description=description,
            color=discord.Color.dark_gold()
        )
        embed.set_image(url=get_hangman_stage_image_url(self.mistakes))
        embed.set_footer(text="Vowels and consonants are separate pages. Guessed letters disappear from the buttons.")
        return embed

    def word_is_complete(self):
        return all(letter in self.guessed_letters for letter in self.word)

    def award_xp(self, player_id, amount):
        xp_info = award_tavern_xp(player_id, amount, "hangman")

        if xp_info and xp_info.get("level_up"):
            self.level_ups.append((player_id, xp_info))

        return xp_info

    def finish_bonus_text_for_player(self, player_id, task_keys=None):
        text = ""
        task_keys = task_keys or ["play_game"]

        for task_key in task_keys:
            tasks_snapshot, task_rewarded, task_xp_info = apply_daily_task_progress(player_id, task_key)
            if task_rewarded:
                if task_xp_info and task_xp_info.get("level_up"):
                    self.level_ups.append((player_id, task_xp_info))
                text += daily_task_reward_text(task_rewarded, task_xp_info)

        new_achievements = check_achievements(player_id)
        if new_achievements:
            text += "\n🏆 Achievement Unlocked:\n" + "\n".join(new_achievements)

        return text

    def finish_results_text(self, guessers_win):
        self.finished = True
        HANGMAN_ACTIVE_CHANNELS.pop(self.channel_id, None)

        if self.mode == "solo":
            if guessers_win:
                add_gold(self.guessers[0], HANGMAN_SOLO_WIN_GOLD)
                xp_info = self.award_xp(self.guessers[0], HANGMAN_SOLO_WIN_XP)
                text = (
                    f"🎉 **Solved!** The word was **{self.word.upper()}**.\n"
                    f"<@{self.guessers[0]}> earned **{HANGMAN_SOLO_WIN_GOLD:,} gold**"
                    f"{xp_result_text(xp_info)}"
                )
            else:
                xp_info = self.award_xp(self.guessers[0], HANGMAN_SOLO_LOSE_XP)
                text = (
                    f"💀 **The word survived.** The word was **{self.word.upper()}**.\n"
                    f"<@{self.guessers[0]}> earned participation XP"
                    f"{xp_result_text(xp_info)}"
                )

            return text

        lines = []

        if guessers_win:
            lines.append(f"🎉 **Guessers win!** The word was **{self.word.upper()}**.")
            lines.append(f"Each guesser earns **{HANGMAN_GUESSER_WIN_GOLD:,} gold** and **{HANGMAN_GUESSER_WIN_XP} XP**.")

            down_to_wire = self.mistakes == 5
            for player_id in self.guessers:
                add_gold(player_id, HANGMAN_GUESSER_WIN_GOLD)
                self.award_xp(player_id, HANGMAN_GUESSER_WIN_XP)
                record_hangman_result(
                    player_id,
                    "guesser",
                    True,
                    self.letter_guess_counts.get(player_id, 0),
                    down_to_wire,
                )

            self.award_xp(self.undertaker_id, HANGMAN_UNDERTAKER_LOSE_XP)
            record_hangman_result(self.undertaker_id, "undertaker", False, 0, False)
            lines.append(f"The Undertaker earns **{HANGMAN_UNDERTAKER_LOSE_XP} XP** for hosting the word.")
        else:
            lines.append(f"💀 **Undertaker wins!** The word was **{self.word.upper()}**.")
            add_gold(self.undertaker_id, HANGMAN_UNDERTAKER_WIN_GOLD)
            self.award_xp(self.undertaker_id, HANGMAN_UNDERTAKER_WIN_XP)
            lines.append(f"<@{self.undertaker_id}> earns **{HANGMAN_UNDERTAKER_WIN_GOLD:,} gold** and **{HANGMAN_UNDERTAKER_WIN_XP} XP**.")
            lines.append(f"Each guesser earns **{HANGMAN_GUESSER_LOSE_XP} XP** for playing.")

            for player_id in self.guessers:
                self.award_xp(player_id, HANGMAN_GUESSER_LOSE_XP)

        return "\n".join(lines)

    async def send_level_messages_after_finish(self, interaction):
        await send_level_up_messages(interaction, self.level_ups)

    async def handle_letter_guess(self, interaction: discord.Interaction, letter):
        if HANGMAN_ACTIVE_CHANNELS.get(self.channel_id) is not self:
            await interaction.response.send_message(
                "This Hangman game is no longer active.",
                ephemeral=True
            )
            return

        if self.finished:
            await interaction.response.send_message(
                "This Hangman game is already finished.",
                ephemeral=True
            )
            return

        current_player = self.current_guesser_id()

        if interaction.user.id != current_player:
            await interaction.response.send_message(
                "It is not your turn to guess.",
                ephemeral=True
            )
            return

        if letter in self.guessed_letters:
            await interaction.response.send_message(
                "That letter has already been guessed.",
                ephemeral=True
            )
            return

        self.guessed_letters.add(letter)
        self.letter_guess_counts[interaction.user.id] = self.letter_guess_counts.get(interaction.user.id, 0) + 1

        result_text = ""
        if letter in self.word:
            result_text = f"✅ <@{interaction.user.id}> guessed **{letter.upper()}** correctly."
        else:
            self.wrong_letters.append(letter)
            self.mistakes += 1
            result_text = f"❌ <@{interaction.user.id}> guessed **{letter.upper()}**. That letter is not in the word."

        game_over = False

        if self.word_is_complete():
            result_text += "\n\n" + self.finish_results_text(True)
            game_over = True
        elif self.mistakes >= HANGMAN_MAX_MISTAKES:
            result_text += "\n\n" + self.finish_results_text(False)
            game_over = True
        else:
            self.advance_turn()

        if not game_over:
            self.refresh_letter_buttons()
            await interaction.response.edit_message(
                embed=self.build_game_embed(result_text),
                view=self
            )
            return

        self.clear_items()
        await interaction.response.edit_message(
            embed=self.build_game_embed(result_text),
            view=None
        )
        await self.send_level_messages_after_finish(interaction)


class TavernView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Claim Daily", emoji="🍺", style=discord.ButtonStyle.green)
    async def daily_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        today = utc_today_text()
        preview = get_daily_claim_preview(interaction.user.id, today)

        if not preview["can_claim"]:
            await interaction.response.send_message(
                f"🍺 You already claimed your daily gold today.\n"
                f"🔥 Current streak: **{preview['streak']} day(s)**\n"
                f"💰 Balance: **{preview['balance']:,} gold**.",
                ephemeral=True
            )
            return

        base_reward = preview["base_reward"]
        daily_reward, title_bonus, title_name = get_daily_gold_reward(interaction.user.id, base_reward)
        claimed, balance, streak = claim_daily_streak(interaction.user.id, daily_reward, today, preview["streak"])

        if not claimed:
            await interaction.response.send_message(
                f"🍺 You already claimed your daily gold today.\n💰 Balance: **{balance:,} gold**.",
                ephemeral=True
            )
            return

        bonus_line = ""
        if title_bonus > 0:
            bonus_line = f"\n🎖 {title_name} bonus: **+{title_bonus:,} gold**"

        pack_line = ""
        if preview["bonus_pack"]:
            pulls = award_bonus_sticker_pack(interaction.user.id, "welcome_pack")
            pack_lines = format_bonus_pack_lines(pulls)
            if pack_lines:
                pack_line = (
                    "\n\n📦 **7-Day Streak Bonus: Welcome Pack opened!**\n"
                    f"{pack_lines}"
                )
            else:
                pack_line = "\n\n📦 **7-Day Streak Bonus earned!** No rollable stickers were available."

        await interaction.response.send_message(
            f"🍺 You claimed **{daily_reward:,} gold** from The Tavern.\n"
            f"🔥 Daily streak: **Day {streak}**"
            f"{bonus_line}\n"
            f"💰 New balance: **{balance:,} gold**."
            f"{pack_line}",
            ephemeral=True
        )

    @discord.ui.button(label="Balance", emoji="💰", style=discord.ButtonStyle.blurple)
    async def balance_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        player = get_or_create_player(interaction.user.id)
        balance = player[0]

        shield_text = lucky_shield_short_text(interaction.user.id)
        message = f"💰 You have **{balance:,} gold**."

        if shield_text:
            message += f"\n{shield_text}"

        await interaction.response.send_message(
            message,
            ephemeral=True
        )
    @discord.ui.button(label="Daily Tasks", emoji="✅", style=discord.ButtonStyle.green)
    async def daily_tasks_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            embed=build_daily_tasks_embed(interaction.user.id),
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

    @discord.ui.button(label="Sticker Book", emoji="📖", style=discord.ButtonStyle.blurple)
    async def sticker_book_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            embed=build_sticker_book_embed(interaction.user),
            view=PublicStickerBookView(interaction.user)
        )

    @discord.ui.button(label="Use Item", emoji="🎒", style=discord.ButtonStyle.secondary)
    async def use_item_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if is_math_drill_active(interaction.channel_id):
            await interaction.response.send_message(
                math_focus_block_text(interaction.channel_id),
                ephemeral=True
            )
            return

        await send_usable_inventory_menu(interaction)

    @discord.ui.button(label="Math Drills", emoji="🧠", style=discord.ButtonStyle.blurple)
    async def math_drill_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            embed=build_math_drill_start_embed(interaction.user.id),
            view=MathDrillStartView(interaction.user.id),
            ephemeral=True
        )

    @discord.ui.button(label="Hangman", emoji="🪦", style=discord.ButtonStyle.secondary)
    async def hangman_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if is_math_drill_active(interaction.channel_id):
            await interaction.response.send_message(
                math_focus_block_text(interaction.channel_id),
                ephemeral=True
            )
            return

        await interaction.response.send_message(
            embed=discord.Embed(
                title="🪦 Hangman",
                description=(
                    "Choose a Hangman mode.\n\n"
                    "**Solo:** Tavern Bot picks the word.\n"
                    "**Multiplayer:** A host creates the table, an Undertaker sets the word privately, and 1-3 guessers take turns."
                ),
                color=discord.Color.dark_gold()
            ),
            view=HangmanStartView(interaction.user.id),
            ephemeral=True
        )

    @discord.ui.button(label="Blackjack", emoji="🃏", style=discord.ButtonStyle.red)
    async def blackjack_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if is_math_drill_active(interaction.channel_id):
            await interaction.response.send_message(
                math_focus_block_text(interaction.channel_id),
                ephemeral=True
            )
            return

        await interaction.response.send_modal(BetModal("Blackjack"))

    @discord.ui.button(label="Dice", emoji="🎲", style=discord.ButtonStyle.green)
    async def dice_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if is_math_drill_active(interaction.channel_id):
            await interaction.response.send_message(
                math_focus_block_text(interaction.channel_id),
                ephemeral=True
            )
            return

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
            user_id, xp, balance, games_played = row
            level, xp_current, xp_needed = get_level_info(xp or 0)
            description += (
                f"**{index}.** <@{user_id}> — "
                f"⭐ **Level {level}** • **{(xp or 0):,} XP** "
                f"• {games_played or 0:,} games\n"
            )

        embed = discord.Embed(
            title="🏆 Tavern XP Leaderboard",
            description=description,
            color=discord.Color.gold()
        )

        embed.set_footer(text="Ranked by total XP, then games played, then gold.")

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True
        )


def build_profile_embed(target_user):
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
    recent_achievements = list(reversed(earned_achievements))[:5]

    if recent_achievements:
        achievement_text = "\n".join(
            [
                ACHIEVEMENTS.get(
                    achievement_id,
                    {"name": achievement_id}
                )["name"]
                for achievement_id, date_earned in recent_achievements
            ]
        )
    else:
        achievement_text = "No achievements yet. Go make questionable choices."

    tomatoes_thrown, tomatoes_taken, pies_thrown, pies_taken = get_mischief_stats(target_user.id)
    math_stats = get_math_stats(target_user.id)
    hangman_stats = get_hangman_stats(target_user.id)

    (
        math_games_played,
        math_daily_games_played,
        math_correct_answers,
        math_wrong_answers,
        math_perfect_rounds,
        math_medium_perfect_rounds,
        math_hard_perfect_rounds,
        math_best_streak,
        math_fastest_answer_ms,
        math_last_daily_challenge,
        math_total_answer_time_ms,
        math_timed_answer_count,
        math_total_match_time_ms,
        math_completed_match_count,
    ) = math_stats

    fastest_math = "None yet"
    if math_fastest_answer_ms > 0:
        fastest_math = f"{math_fastest_answer_ms / 1000:.2f}s"

    average_math = "None yet"
    if math_timed_answer_count > 0:
        average_math = f"{(math_total_answer_time_ms / math_timed_answer_count) / 1000:.2f}s"

    average_match = "None yet"
    if math_completed_match_count > 0:
        average_match = f"{(math_total_match_time_ms / math_completed_match_count) / 1000:.1f}s"

    (
        hangman_games_played,
        hangman_guesser_games,
        hangman_undertaker_games,
        hangman_guesser_wins,
        hangman_undertaker_wins,
        hangman_letters_guessed,
        hangman_down_to_wire_wins,
    ) = hangman_stats

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

    shield_text = lucky_shield_status_text(target_user.id)
    if shield_text:
        embed.add_field(
            name="🍀 Active Protection",
            value=shield_text,
            inline=False
        )

    embed.add_field(
        name="🪦 Hangman",
        value=(
            f"Games Played: **{hangman_games_played:,}**\n"
            f"Guesser Wins: **{hangman_guesser_wins:,}**\n"
            f"Undertaker Wins: **{hangman_undertaker_wins:,}**\n"
            f"Letters Guessed: **{hangman_letters_guessed:,}**"
        ),
        inline=False
    )

    embed.add_field(
        name="🎭 Mischief",
        value=(
            f"🍅 Thrown: **{tomatoes_thrown:,}** | Taken: **{tomatoes_taken:,}**\n"
            f"🥧 Thrown: **{pies_thrown:,}** | Taken: **{pies_taken:,}**"
        ),
        inline=False
    )

    embed.add_field(
        name="🎖 Recent Achievements",
        value=achievement_text,
        inline=False
    )

    embed.set_footer(text="Use the buttons below for more profile pages.")
    return embed


async def send_profile(interaction, target_user):
    await interaction.response.send_message(
        embed=build_profile_embed(target_user),
        view=ProfileView(interaction.user.id, target_user),
        ephemeral=True
    )


def build_inventory_embed(target_user):
    title_ids = get_player_titles(target_user.id)
    title_lines = [DEFAULT_TITLE]

    for title_id in title_ids:
        title = TITLE_ITEMS.get(title_id)
        if title:
            title_lines.append(title["name"])

    mischief_items = get_owned_mischief_items(target_user.id)

    if mischief_items:
        mischief_lines = []
        for item_id, quantity in mischief_items:
            item = MISCHIEF_ITEMS.get(item_id)
            if item:
                mischief_lines.append(f"{item['name']} x{quantity}")
        mischief_text = "\n".join(mischief_lines)
    else:
        mischief_text = "No mischief items owned."

    gameplay_items = get_owned_gameplay_items(target_user.id)
    active_shields = get_active_lucky_shields(target_user.id)

    gameplay_lines = []

    for item_id, quantity in gameplay_items:
        item = GAMEPLAY_ITEMS.get(item_id)
        if item:
            gameplay_lines.append(f"{item['name']} x{quantity}")

    if active_shields > 0:
        gameplay_lines.append(lucky_shield_short_text(user_id))

    gameplay_text = "\n".join(gameplay_lines) if gameplay_lines else "No gameplay consumables owned."

    embed = discord.Embed(
        title=f"🎒 {target_user.display_name}'s Inventory",
        description="Inventory is only visible on your own profile.",
        color=discord.Color.gold()
    )

    embed.add_field(
        name="🎖 Titles",
        value="\n".join(title_lines),
        inline=False
    )

    embed.add_field(
        name="🎭 Consumables",
        value=mischief_text,
        inline=False
    )

    embed.add_field(
        name="🍀 Gameplay Items",
        value=gameplay_text,
        inline=False
    )

    owned_sounds = get_owned_sound_items(target_user.id)

    if owned_sounds:
        sound_lines = []
        for sound_id, quantity in owned_sounds:
            sound = SOUND_ITEMS.get(sound_id)
            if sound:
                sound_lines.append(sound["name"])
        sound_text = "\n".join(sound_lines)
    else:
        sound_text = "No sounds owned."

    embed.add_field(
        name="🔊 Sounds",
        value=sound_text,
        inline=False
    )

    return embed


def build_sticker_book_embed(target_user):
    sticker_map = get_sticker_quantity_map(target_user.id)
    owned_total, total_stickers = get_total_sticker_progress(target_user.id)
    featured_id = get_featured_sticker_for_user(target_user.id)

    if featured_id:
        featured = STICKERS[featured_id]
        featured_text = (
            f"{get_sticker_rarity_label(featured_id)}\n"
            f"**{featured['name']}**\n"
            f"*{featured['quote']}*"
        )
    else:
        featured_text = (
            "No featured sticker yet.\n"
            "Open sticker packs to start your collection."
        )

    collection_lines = []

    for collection_id, collection in STICKER_COLLECTIONS.items():
        owned, total = get_collection_progress(target_user.id, collection_id)
        collection_lines.append(
            f"{collection['name']}: {progress_line(owned, total)}"
        )

    embed = discord.Embed(
        title=f"📖 {target_user.display_name}'s Sticker Book",
        description=(
            f"**Featured Sticker**\n"
            f"{featured_text}\n\n"
            f"**Total Completion**\n"
            f"{progress_line(owned_total, total_stickers)}"
        ),
        color=discord.Color.gold()
    )

    embed.add_field(
        name="📚 Collections",
        value="\n".join(collection_lines),
        inline=False
    )

    if featured_id:
        image_url = get_sticker_image_url(featured_id)
    
        if image_url:
            embed.set_image(url=image_url)
    
    embed.set_footer(text="Choose a collection below to flip through the sticker pages.")
    return embed


def build_sticker_collection_embed(target_user, collection_id, page_index):
    collection = STICKER_COLLECTIONS.get(collection_id)

    if not collection:
        return discord.Embed(
            title="📖 Sticker Collection",
            description="That sticker collection does not exist.",
            color=discord.Color.gold()
        )

    stickers = collection["stickers"]
    total = len(stickers)

    if total == 0:
        page_index = 0
    else:
        page_index = page_index % total

    sticker_id = stickers[page_index]
    sticker = STICKERS[sticker_id]
    quantity = get_player_sticker_quantity(target_user.id, sticker_id)
    owned = quantity > 0
    collection_owned, collection_total = get_collection_progress(target_user.id, collection_id)

    if owned:
        sticker_name = sticker["name"]
        owned_text = f"Owned: **Yes x{quantity}**"
        quote_text = f"*{sticker['quote']}*"
    else:
        sticker_name = "🔒 Unknown Sticker"
        owned_text = "Owned: **No**"
        quote_text = "Find this sticker in a sticker pack."

    embed = discord.Embed(
        title=collection["name"],
        description=(
            f"Sticker **{page_index + 1} / {total}**\n\n"
            f"{get_sticker_rarity_label(sticker_id)}\n"
            f"**{sticker_name}**\n"
            f"{owned_text}\n\n"
            f"{quote_text}\n\n"
            f"Collection Progress: {progress_line(collection_owned, collection_total)}"
        ),
        color=discord.Color.gold()
    )

    image_url = get_sticker_image_url(sticker_id)
    
    if owned and image_url:
        embed.set_image(url=image_url)
    
    embed.set_footer(text="Flip pages to browse the collection.")
    return embed


class StickerBookView(discord.ui.View):
    def __init__(self, owner_id, target_user):
        super().__init__(timeout=180)
        self.owner_id = owner_id
        self.target_user = target_user

    async def interaction_check(self, interaction):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message(
                "This sticker book view belongs to someone else. Use `/profile` to open your own view.",
                ephemeral=True
            )
            return False

        return True

    @discord.ui.button(label="Welcome", emoji="🍺", style=discord.ButtonStyle.green)
    async def welcome_collection_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(
            embed=build_sticker_collection_embed(self.target_user, "welcome", 0),
            view=StickerCollectionView(self.owner_id, self.target_user, "welcome", 0)
        )

    @discord.ui.button(label="Mischief", emoji="🎭", style=discord.ButtonStyle.red)
    async def mischief_collection_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(
            embed=build_sticker_collection_embed(self.target_user, "mischief", 0),
            view=StickerCollectionView(self.owner_id, self.target_user, "mischief", 0)
        )

    @discord.ui.button(label="Casino", emoji="🎲", style=discord.ButtonStyle.blurple)
    async def casino_collection_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(
            embed=build_sticker_collection_embed(self.target_user, "casino", 0),
            view=StickerCollectionView(self.owner_id, self.target_user, "casino", 0)
        )

    @discord.ui.button(label="Back to Profile", emoji="⬅️", style=discord.ButtonStyle.secondary)
    async def back_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(
            embed=build_profile_embed(self.target_user),
            view=ProfileView(self.owner_id, self.target_user)
        )


class StickerCollectionView(discord.ui.View):
    def __init__(self, owner_id, target_user, collection_id, page_index):
        super().__init__(timeout=180)
        self.owner_id = owner_id
        self.target_user = target_user
        self.collection_id = collection_id
        self.page_index = page_index

        if not self.can_feature_current_sticker():
            for item in list(self.children):
                if getattr(item, "custom_id", None) == "feature_sticker_button":
                    self.remove_item(item)

    async def interaction_check(self, interaction):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message(
                "This sticker collection view belongs to someone else. Use `/profile` to open your own view.",
                ephemeral=True
            )
            return False

        return True

    def current_sticker_id(self):
        collection = STICKER_COLLECTIONS[self.collection_id]
        stickers = collection["stickers"]
        return stickers[self.page_index % len(stickers)]

    def can_feature_current_sticker(self):
        if self.owner_id != self.target_user.id:
            return False

        sticker_id = self.current_sticker_id()
        return get_player_sticker_quantity(self.target_user.id, sticker_id) > 0

    @discord.ui.button(label="Previous", emoji="⬅️", style=discord.ButtonStyle.secondary)
    async def previous_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        collection = STICKER_COLLECTIONS[self.collection_id]
        new_index = (self.page_index - 1) % len(collection["stickers"])

        await interaction.response.edit_message(
            embed=build_sticker_collection_embed(self.target_user, self.collection_id, new_index),
            view=StickerCollectionView(self.owner_id, self.target_user, self.collection_id, new_index)
        )

    @discord.ui.button(label="Next", emoji="➡️", style=discord.ButtonStyle.secondary)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        collection = STICKER_COLLECTIONS[self.collection_id]
        new_index = (self.page_index + 1) % len(collection["stickers"])

        await interaction.response.edit_message(
            embed=build_sticker_collection_embed(self.target_user, self.collection_id, new_index),
            view=StickerCollectionView(self.owner_id, self.target_user, self.collection_id, new_index)
        )

    @discord.ui.button(label="Feature Sticker", emoji="⭐", style=discord.ButtonStyle.green, custom_id="feature_sticker_button")
    async def feature_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        sticker_id = self.current_sticker_id()
        sticker = STICKERS[sticker_id]

        if get_player_sticker_quantity(interaction.user.id, sticker_id) <= 0:
            await interaction.response.send_message(
                "You can only feature stickers you own.",
                ephemeral=True
            )
            return

        set_featured_sticker(interaction.user.id, sticker_id)

        embed = build_sticker_collection_embed(self.target_user, self.collection_id, self.page_index)
        embed.set_footer(text=f"Featured sticker set to {sticker['name']}.")

        await interaction.response.edit_message(
            embed=embed,
            view=StickerCollectionView(self.owner_id, self.target_user, self.collection_id, self.page_index)
        )

    @discord.ui.button(label="Back to Book", emoji="📖", style=discord.ButtonStyle.blurple)
    async def back_to_book_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(
            embed=build_sticker_book_embed(self.target_user),
            view=StickerBookView(self.owner_id, self.target_user)
        )


class PublicStickerBookView(discord.ui.View):
    def __init__(self, target_user):
        super().__init__(timeout=180)
        self.target_user = target_user

    @discord.ui.button(label="Welcome", emoji="🍺", style=discord.ButtonStyle.green)
    async def welcome_collection_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(
            embed=build_sticker_collection_embed(self.target_user, "welcome", 0),
            view=PublicStickerCollectionView(self.target_user, "welcome", 0)
        )

    @discord.ui.button(label="Mischief", emoji="🎭", style=discord.ButtonStyle.red)
    async def mischief_collection_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(
            embed=build_sticker_collection_embed(self.target_user, "mischief", 0),
            view=PublicStickerCollectionView(self.target_user, "mischief", 0)
        )

    @discord.ui.button(label="Casino", emoji="🎲", style=discord.ButtonStyle.blurple)
    async def casino_collection_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(
            embed=build_sticker_collection_embed(self.target_user, "casino", 0),
            view=PublicStickerCollectionView(self.target_user, "casino", 0)
        )


class PublicStickerCollectionView(discord.ui.View):
    def __init__(self, target_user, collection_id, page_index):
        super().__init__(timeout=180)
        self.target_user = target_user
        self.collection_id = collection_id
        self.page_index = page_index

        if not self.target_owns_current_sticker():
            for item in list(self.children):
                if getattr(item, "custom_id", None) == "public_feature_sticker_button":
                    self.remove_item(item)

    def current_sticker_id(self):
        collection = STICKER_COLLECTIONS[self.collection_id]
        stickers = collection["stickers"]
        return stickers[self.page_index % len(stickers)]

    def target_owns_current_sticker(self):
        sticker_id = self.current_sticker_id()
        return get_player_sticker_quantity(self.target_user.id, sticker_id) > 0

    @discord.ui.button(label="Previous", emoji="⬅️", style=discord.ButtonStyle.secondary)
    async def previous_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        collection = STICKER_COLLECTIONS[self.collection_id]
        new_index = (self.page_index - 1) % len(collection["stickers"])

        await interaction.response.edit_message(
            embed=build_sticker_collection_embed(self.target_user, self.collection_id, new_index),
            view=PublicStickerCollectionView(self.target_user, self.collection_id, new_index)
        )

    @discord.ui.button(label="Next", emoji="➡️", style=discord.ButtonStyle.secondary)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        collection = STICKER_COLLECTIONS[self.collection_id]
        new_index = (self.page_index + 1) % len(collection["stickers"])

        await interaction.response.edit_message(
            embed=build_sticker_collection_embed(self.target_user, self.collection_id, new_index),
            view=PublicStickerCollectionView(self.target_user, self.collection_id, new_index)
        )

    @discord.ui.button(label="Feature Sticker", emoji="⭐", style=discord.ButtonStyle.green, custom_id="public_feature_sticker_button")
    async def public_feature_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.target_user.id:
            await interaction.response.send_message(
                f"Only **{self.target_user.display_name}** can set the featured sticker for this book.",
                ephemeral=True
            )
            return

        sticker_id = self.current_sticker_id()
        sticker = STICKERS[sticker_id]

        if get_player_sticker_quantity(interaction.user.id, sticker_id) <= 0:
            await interaction.response.send_message(
                "You can only feature stickers you own.",
                ephemeral=True
            )
            return

        set_featured_sticker(interaction.user.id, sticker_id)

        embed = build_sticker_collection_embed(self.target_user, self.collection_id, self.page_index)
        embed.set_footer(text=f"Featured sticker set to {sticker['name']}.")

        await interaction.response.edit_message(
            embed=embed,
            view=PublicStickerCollectionView(self.target_user, self.collection_id, self.page_index)
        )

    @discord.ui.button(label="Back to Book", emoji="📖", style=discord.ButtonStyle.blurple)
    async def back_to_book_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(
            embed=build_sticker_book_embed(self.target_user),
            view=PublicStickerBookView(self.target_user)
        )


def build_detailed_stats_embed(target_user):
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

    win_rate = 0
    if games_played > 0:
        win_rate = (wins / games_played) * 100

    tomatoes_thrown, tomatoes_taken, pies_thrown, pies_taken = get_mischief_stats(target_user.id)

    embed = discord.Embed(
        title=f"📊 {target_user.display_name}'s Detailed Stats",
        description=f"**Title:** {title}",
        color=discord.Color.gold()
    )

    embed.add_field(
        name="💰 Economy",
        value=(
            f"Gold: **{balance:,}**\n"
            f"Total Wagered: **{total_wagered:,}**\n"
            f"Biggest Win: **{biggest_win:,}**\n"
            f"Biggest Loss: **{biggest_loss:,}**"
        ),
        inline=False
    )

    embed.add_field(
        name="🎮 Games",
        value=(
            f"Games Played: **{games_played:,}**\n"
            f"Wins: **{wins:,}**\n"
            f"Losses: **{losses:,}**\n"
            f"Pushes: **{pushes:,}**\n"
            f"Win Rate: **{win_rate:.1f}%**"
        ),
        inline=True
    )

    embed.add_field(
        name="🃏 Blackjack",
        value=(
            f"Blackjacks: **{blackjacks:,}**\n"
            f"Doubles: **{doubles:,}**"
        ),
        inline=True
    )

    embed.add_field(
        name="⭐ Progress",
        value=(
            f"Level: **{level}**\n"
            f"Current XP: **{xp_current}/{xp_needed}**\n"
            f"Total XP: **{xp:,}**"
        ),
        inline=True
    )

    embed.add_field(
        name="🧠 Math Drills",
        value=(
            f"Rounds Played: **{math_games_played:,}**\n"
            f"Correct Answers: **{math_correct_answers:,}**\n"
            f"Perfect Rounds: **{math_perfect_rounds:,}**\n"
            f"Best Streak: **{math_best_streak:,}**\n"
            f"Fastest Answer: **{fastest_math}**\n"
            f"Average Answer: **{average_math}**\n"
            f"Average Drill Time: **{average_match}**"
        ),
        inline=False
    )

    embed.add_field(
        name="🪦 Hangman",
        value=(
            f"Games Played: **{hangman_games_played:,}**\n"
            f"Guesser Wins: **{hangman_guesser_wins:,}**\n"
            f"Undertaker Wins: **{hangman_undertaker_wins:,}**\n"
            f"Letters Guessed: **{hangman_letters_guessed:,}**"
        ),
        inline=False
    )

    embed.add_field(
        name="🎭 Mischief",
        value=(
            f"🍅 Tomatoes Thrown: **{tomatoes_thrown:,}**\n"
            f"🍅 Tomatoes Taken: **{tomatoes_taken:,}**\n"
            f"🥧 Pies Thrown: **{pies_thrown:,}**\n"
            f"🥧 Pies Taken: **{pies_taken:,}**"
        ),
        inline=False
    )

    return embed


def build_achievements_embed(target_user):
    earned_rows = get_player_achievements(target_user.id)
    earned_ids = {achievement_id for achievement_id, date_earned in earned_rows}

    earned_lines = []
    locked_lines = []

    for achievement_id, achievement in ACHIEVEMENTS.items():
        name = achievement["name"]
        description = achievement.get("description", "")

        if achievement_id in earned_ids:
            earned_lines.append(f"✅ {name} — {description}")
        else:
            locked_lines.append(f"🔒 {name} — {description}")

    earned_text = "\n".join(earned_lines) if earned_lines else "No achievements earned yet."
    locked_text = "\n".join(locked_lines) if locked_lines else "All achievements unlocked."

    if len(earned_text) > 1000:
        earned_text = earned_text[:997] + "..."

    if len(locked_text) > 1000:
        locked_text = locked_text[:997] + "..."

    embed = discord.Embed(
        title=f"🏆 {target_user.display_name}'s Achievements",
        description=f"Earned **{len(earned_ids)} / {len(ACHIEVEMENTS)}** achievements.",
        color=discord.Color.gold()
    )

    embed.add_field(
        name="✅ Earned",
        value=earned_text,
        inline=False
    )

    embed.add_field(
        name="🔒 Locked",
        value=locked_text,
        inline=False
    )

    return embed


class ProfileView(discord.ui.View):
    def __init__(self, owner_id, target_user):
        super().__init__(timeout=180)
        self.owner_id = owner_id
        self.target_user = target_user

        if owner_id != target_user.id:
            for item in list(self.children):
                if getattr(item, "custom_id", None) == "profile_inventory_button":
                    self.remove_item(item)

    async def interaction_check(self, interaction):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message(
                "This profile menu belongs to someone else. Use `/profile` to open your own view.",
                ephemeral=True
            )
            return False

        return True

    @discord.ui.button(label="Inventory", emoji="🎒", style=discord.ButtonStyle.green, custom_id="profile_inventory_button")
    async def inventory_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.owner_id != self.target_user.id:
            await interaction.response.send_message(
                "You can only view your own inventory.",
                ephemeral=True
            )
            return

        await interaction.response.edit_message(
            embed=build_inventory_embed(self.target_user),
            view=ProfileBackView(self.owner_id, self.target_user)
        )

    @discord.ui.button(label="Sticker Book", emoji="📖", style=discord.ButtonStyle.blurple)
    async def sticker_book_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(
            embed=build_sticker_book_embed(self.target_user),
            view=StickerBookView(self.owner_id, self.target_user)
        )

    @discord.ui.button(label="Detailed Stats", emoji="📊", style=discord.ButtonStyle.gray)
    async def detailed_stats_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(
            embed=build_detailed_stats_embed(self.target_user),
            view=ProfileBackView(self.owner_id, self.target_user)
        )

    @discord.ui.button(label="Achievements", emoji="🏆", style=discord.ButtonStyle.secondary)
    async def achievements_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(
            embed=build_achievements_embed(self.target_user),
            view=ProfileBackView(self.owner_id, self.target_user)
        )


class ProfileBackView(discord.ui.View):
    def __init__(self, owner_id, target_user):
        super().__init__(timeout=180)
        self.owner_id = owner_id
        self.target_user = target_user

    async def interaction_check(self, interaction):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message(
                "This profile menu belongs to someone else. Use `/profile` to open your own view.",
                ephemeral=True
            )
            return False

        return True

    @discord.ui.button(label="Back to Profile", emoji="⬅️", style=discord.ButtonStyle.secondary)
    async def back_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(
            embed=build_profile_embed(self.target_user),
            view=ProfileView(self.owner_id, self.target_user)
        )


def build_shop_embed(user_id):
    balance = get_balance(user_id)
    active_title = get_active_title(user_id)
    bonus_description = get_active_title_bonus_description(user_id)
    discount_text = shop_discount_line(user_id)

    embed = discord.Embed(
        title="🏪 The Tavern Shop",
        description=(
            f"💰 Gold: **{balance:,}**\n\n"
            f"🎖 Active Title:\n"
            f"{active_title}\n"
            f"Bonus: **{bonus_description}**"
            f"{discount_text}\n\n"
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

    @discord.ui.button(label="Shots", emoji="🥃", style=discord.ButtonStyle.gray)
    async def shots_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(
            content=None,
            embed=build_shot_bar_embed(self.owner_id),
            view=ShotBarView(self.owner_id)
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
            embed=build_sticker_pack_shop_embed(self.owner_id),
            view=StickerPackShopView(self.owner_id)
        )

    @discord.ui.button(label="Sounds", emoji="🔊", style=discord.ButtonStyle.gray)
    async def sounds_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(
            content=None,
            embed=build_sound_shop_embed(self.owner_id),
            view=SoundShopView(self.owner_id)
        )


def build_shot_bar_embed(user_id):
    balance = get_balance(user_id)
    shot = get_tavern_shot_definition()

    embed = discord.Embed(
        title="🥃 Shot Bar",
        description=(
            f"💰 Gold: **{balance:,}**\n\n"
            f"**{shot['name']}** — **{format_tavern_shot_price(user_id)}**\n"
            f"{shot['description']}\n\n"
            "Shots are **instant use**. They do not go into your inventory.\n"
            "Use them from a Tavern table before or during a game."
        ),
        color=discord.Color.dark_gold()
    )

    embed.set_footer(text="Shots post publicly. The shop channel stays clean.")
    return embed


class ShotBarView(discord.ui.View):
    def __init__(self, owner_id):
        super().__init__(timeout=180)
        self.owner_id = owner_id

    async def interaction_check(self, interaction):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message(
                "This Shot Bar menu belongs to someone else. Use `/shop` to open your own.",
                ephemeral=True
            )
            return False

        return True

    @discord.ui.button(label="Pour Shot", emoji="🥃", style=discord.ButtonStyle.green)
    async def pour_shot_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await buy_and_pour_tavern_shot(interaction)

    @discord.ui.button(label="Back to Shop", emoji="⬅️", style=discord.ButtonStyle.secondary)
    async def back_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(
            content=None,
            embed=build_shop_embed(self.owner_id),
            view=ShopView(self.owner_id)
        )


def build_sound_shop_embed(user_id):
    balance = get_balance(user_id)
    owned_sounds = {sound_id for sound_id, quantity in get_owned_sound_items(user_id)}

    lines = []

    for sound_id, sound in SOUND_ITEMS.items():
        if sound_id in owned_sounds:
            lines.append(f"✅ {sound['name']} — Owned")
        else:
            lines.append(f"{sound['name']} — **{format_shop_price(user_id, sound['price'])}**")

    embed = discord.Embed(
        title="🔊 Sound Shop",
        description=(
            f"💰 Gold: **{balance:,}**\n\n"
            f"**Available Sounds:**\n"
            f"{chr(10).join(lines)}\n\n"
            "Sounds are permanent unlocks. Buy once, use as targeted sound attacks."
        ),
        color=discord.Color.gold()
    )

    embed.set_footer(text="Sounds post publicly, ping one target, and attach playable audio.")
    return embed


def build_buy_sounds_embed(user_id):
    balance = get_balance(user_id)
    lines = []

    for sound_id, sound in SOUND_ITEMS.items():
        if player_owns_item(user_id, sound_id):
            continue

        lines.append(f"{sound['name']} — {format_shop_price(user_id, sound['price'])}")

    available_text = "\n".join(lines) if lines else "You already own every sound."

    embed = discord.Embed(
        title="💰 Buy a Sound",
        description=(
            f"💰 Gold: **{balance:,}**\n\n"
            f"{available_text}\n\n"
            "Choose a sound from the dropdown below."
        ),
        color=discord.Color.gold()
    )

    return embed


def build_use_sounds_embed(user_id):
    owned_sounds = get_owned_sound_items(user_id)

    if owned_sounds:
        lines = []
        for sound_id, quantity in owned_sounds:
            sound = SOUND_ITEMS.get(sound_id)
            if sound:
                lines.append(sound["name"])
        owned_text = "\n".join(lines)
    else:
        owned_text = "No sounds owned yet."

    embed = discord.Embed(
        title="🔊 Use a Sound",
        description=(
            f"**Your Sounds:**\n"
            f"{owned_text}\n\n"
            "Choose a sound, then pick a target."
        ),
        color=discord.Color.gold()
    )

    return embed


class SoundShopView(discord.ui.View):
    def __init__(self, owner_id):
        super().__init__(timeout=180)
        self.owner_id = owner_id

    async def interaction_check(self, interaction):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message(
                "This sound shop belongs to someone else. Use `/shop` to open your own.",
                ephemeral=True
            )
            return False

        return True

    @discord.ui.button(label="Buy Sound", emoji="💰", style=discord.ButtonStyle.green)
    async def buy_sound_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        available_sounds = [
            sound_id
            for sound_id in SOUND_ITEMS
            if not player_owns_item(self.owner_id, sound_id)
        ]

        if not available_sounds:
            embed = build_sound_shop_embed(self.owner_id)
            embed.set_footer(text="You already own every sound.")

            await interaction.response.edit_message(
                content=None,
                embed=embed,
                view=SoundShopView(self.owner_id)
            )
            return

        await interaction.response.edit_message(
            content=None,
            embed=build_buy_sounds_embed(self.owner_id),
            view=BuySoundSelectView(self.owner_id)
        )

    @discord.ui.button(label="Use Sound Attack", emoji="🔊", style=discord.ButtonStyle.blurple)
    async def use_sound_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if is_shop_channel(interaction):
            await interaction.response.send_message(
                "🔊 Sound attacks are public. Use them from The Tavern menu so the shop channel stays clean.",
                ephemeral=True
            )
            return

        owned_sounds = get_owned_sound_items(self.owner_id)

        if not owned_sounds:
            embed = build_sound_shop_embed(self.owner_id)
            embed.set_footer(text="You do not own any sounds yet.")

            await interaction.response.edit_message(
                content=None,
                embed=embed,
                view=SoundShopView(self.owner_id)
            )
            return

        await interaction.response.edit_message(
            content=None,
            embed=build_use_sounds_embed(self.owner_id),
            view=UseSoundSelectView(self.owner_id)
        )

    @discord.ui.button(label="Back to Shop", emoji="⬅️", style=discord.ButtonStyle.secondary)
    async def back_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(
            content=None,
            embed=build_shop_embed(self.owner_id),
            view=ShopView(self.owner_id)
        )


class BuySoundSelect(discord.ui.Select):
    def __init__(self, owner_id):
        self.owner_id = owner_id

        options = []

        for sound_id, sound in SOUND_ITEMS.items():
            if player_owns_item(owner_id, sound_id):
                continue

            options.append(
                discord.SelectOption(
                    label=sound["name"],
                    description=format_shop_price(owner_id, sound["price"]),
                    value=sound_id
                )
            )

        super().__init__(
            placeholder="Choose a sound to buy...",
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        sound_id = self.values[0]
        sound = SOUND_ITEMS.get(sound_id)

        if not sound:
            await interaction.response.send_message(
                "That sound does not exist.",
                ephemeral=True
            )
            return

        if player_owns_item(interaction.user.id, sound_id):
            await interaction.response.send_message(
                "You already own that sound.",
                ephemeral=True
            )
            return

        base_price = sound["price"]
        price = get_discounted_shop_price(interaction.user.id, base_price)
        balance = get_balance(interaction.user.id)

        if balance < price:
            await interaction.response.send_message(
                f"You need **{price:,} gold** to buy {sound['name']}.\n"
                f"Your balance is **{balance:,} gold**.",
                ephemeral=True
            )
            return

        add_gold(interaction.user.id, -price)

        add_inventory_item(
            interaction.user.id,
            sound_id,
            "sound",
            datetime.now(timezone.utc).isoformat()
        )

        embed = build_sound_shop_embed(interaction.user.id)
        embed.set_footer(text=f"Purchased {sound['name']} for {price:,} gold.")

        await interaction.response.edit_message(
            content=None,
            embed=embed,
            view=SoundShopView(interaction.user.id)
        )


class BuySoundSelectView(discord.ui.View):
    def __init__(self, owner_id):
        super().__init__(timeout=180)
        self.owner_id = owner_id
        self.add_item(BuySoundSelect(owner_id))

    async def interaction_check(self, interaction):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message(
                "This buy menu belongs to someone else. Use `/shop` to open your own.",
                ephemeral=True
            )
            return False

        return True

    @discord.ui.button(label="Back to Sounds", emoji="⬅️", style=discord.ButtonStyle.secondary)
    async def back_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(
            content=None,
            embed=build_sound_shop_embed(self.owner_id),
            view=SoundShopView(self.owner_id)
        )


class UseSoundSelect(discord.ui.Select):
    def __init__(self, owner_id):
        self.owner_id = owner_id

        options = []

        for sound_id, quantity in get_owned_sound_items(owner_id):
            sound = SOUND_ITEMS.get(sound_id)
            if not sound:
                continue

            options.append(
                discord.SelectOption(
                    label=sound["name"],
                    description="Target someone with this sound",
                    value=sound_id
                )
            )

        super().__init__(
            placeholder="Choose a sound attack...",
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        sound_id = self.values[0]

        await interaction.response.edit_message(
            content=None,
            embed=build_sound_target_embed(interaction.user.id, sound_id),
            view=UseSoundTargetView(
                owner_id=interaction.user.id,
                sound_id=sound_id,
                back_to="sounds"
            )
        )


class UseSoundSelectView(discord.ui.View):
    def __init__(self, owner_id):
        super().__init__(timeout=180)
        self.owner_id = owner_id
        self.add_item(UseSoundSelect(owner_id))

    async def interaction_check(self, interaction):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message(
                "This sound menu belongs to someone else. Use `/shop` to open your own.",
                ephemeral=True
            )
            return False

        return True

    @discord.ui.button(label="Back to Sounds", emoji="⬅️", style=discord.ButtonStyle.secondary)
    async def back_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(
            content=None,
            embed=build_sound_shop_embed(self.owner_id),
            view=SoundShopView(self.owner_id)
        )


class UseSoundTargetSelect(discord.ui.UserSelect):
    def __init__(self, owner_id, sound_id, allowed_target_ids=None):
        self.owner_id = owner_id
        self.sound_id = sound_id
        self.allowed_target_ids = allowed_target_ids

        super().__init__(
            placeholder="Choose a sound target...",
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
                "The Tavern Bot refuses to be sound-attacked by its own customers.",
                ephemeral=True
            )
            return

        await play_soundboard_sound(interaction, self.sound_id, target_user=target)


class UseSoundTargetView(discord.ui.View):
    def __init__(self, owner_id, sound_id, allowed_target_ids=None, back_to="sounds"):
        super().__init__(timeout=180)
        self.owner_id = owner_id
        self.sound_id = sound_id
        self.allowed_target_ids = allowed_target_ids
        self.back_to = back_to

        self.add_item(
            UseSoundTargetSelect(
                owner_id,
                sound_id,
                allowed_target_ids
            )
        )

    async def interaction_check(self, interaction):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message(
                "This sound target menu belongs to someone else.",
                ephemeral=True
            )
            return False

        return True

    @discord.ui.button(label="Back", emoji="⬅️", style=discord.ButtonStyle.secondary)
    async def back_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.back_to == "items":
            await interaction.response.edit_message(
                content=None,
                embed=discord.Embed(
                    title="🎭 Use Item / Sound",
                    description="Choose something from your Tavern inventory.",
                    color=discord.Color.gold()
                ),
                view=UseConsumableSelectView(
                    owner_id=self.owner_id,
                    allowed_target_ids=self.allowed_target_ids,
                    include_sounds=True
                )
            )
            return

        await interaction.response.edit_message(
            content=None,
            embed=build_use_sounds_embed(self.owner_id),
            view=UseSoundSelectView(self.owner_id)
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


def build_sticker_pack_shop_embed(user_id):
    balance = get_balance(user_id)
    owned_total, total_stickers = get_total_sticker_progress(user_id)

    available_pack_lines = []
    unavailable_pack_lines = []

    for pack_id, pack in STICKER_PACKS.items():
        purchase_enabled = is_sticker_pack_purchase_enabled(pack_id)
        rollable = can_roll_sticker_pack(pack_id)

        if purchase_enabled and rollable:
            available_pack_lines.append(
                f"{pack['name']} — **{format_shop_price(user_id, pack['price'])}** "
                f"({pack['pulls']} stickers)"
            )
        else:
            unavailable_pack_lines.append(f"{pack['name']} — not currently for sale")

    if available_pack_lines:
        available_text = chr(10).join(available_pack_lines)
    else:
        available_text = "No sticker packs are currently for sale."

    unavailable_text = ""
    if unavailable_pack_lines:
        unavailable_text = (
            f"\n\n**Not Currently Available:**\n"
            f"{chr(10).join(unavailable_pack_lines)}"
        )

    embed = discord.Embed(
        title="📦 Sticker Packs",
        description=(
            f"💰 Gold: **{balance:,}**\n"
            f"📖 Sticker Completion: {progress_line(owned_total, total_stickers)}\n\n"
            f"**Available Packs:**\n"
            f"{available_text}"
            f"{unavailable_text}\n\n"
            "Buy a pack to immediately open it. Duplicates stack for future trading."
        ),
        color=discord.Color.gold()
    )

    embed.set_footer(text="Collections stay viewable for players who already own those stickers.")
    return embed


def build_sticker_pack_result_embed(user_id, pack_id, pulls):
    pack = STICKER_PACKS[pack_id]
    lines = []
    legendary_pulled = False

    for sticker_id, old_quantity, new_quantity in pulls:
        sticker = STICKERS[sticker_id]
        rarity = sticker["rarity"]
        rarity_label = get_sticker_rarity_label(sticker_id)

        if rarity == "legendary":
            legendary_pulled = True

        status = "NEW!" if old_quantity == 0 else f"x{new_quantity}"

        lines.append(
            f"{rarity_label} {sticker['name']} — **{status}**"
        )

    owned_total, total_stickers = get_total_sticker_progress(user_id)

    title = f"📦 Opened {pack['name']}!"

    if legendary_pulled:
        title = f"🟡 LEGENDARY PULL! {pack['name']}"

    embed = discord.Embed(
        title=title,
        description=(
            f"You pulled:\n"
            f"{chr(10).join(lines)}\n\n"
            f"Sticker Completion: {progress_line(owned_total, total_stickers)}"
        ),
        color=discord.Color.gold()
    )

    embed.set_footer(text="Duplicates are saved for future sticker trading.")
    return embed


class StickerPackShopView(discord.ui.View):
    def __init__(self, owner_id):
        super().__init__(timeout=180)
        self.owner_id = owner_id

    async def interaction_check(self, interaction):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message(
                "This sticker pack shop belongs to someone else. Use `/shop` to open your own.",
                ephemeral=True
            )
            return False

        return True

    @discord.ui.button(label="Buy Pack", emoji="📦", style=discord.ButtonStyle.green)
    async def buy_pack_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(
            content=None,
            embed=build_sticker_pack_shop_embed(self.owner_id),
            view=BuyStickerPackSelectView(self.owner_id)
        )

    @discord.ui.button(label="Back to Shop", emoji="⬅️", style=discord.ButtonStyle.secondary)
    async def back_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(
            content=None,
            embed=build_shop_embed(self.owner_id),
            view=ShopView(self.owner_id)
        )


class BuyStickerPackSelect(discord.ui.Select):
    def __init__(self, owner_id):
        self.owner_id = owner_id

        options = []

        for pack_id in get_available_sticker_pack_ids():
            pack = STICKER_PACKS[pack_id]
            options.append(
                discord.SelectOption(
                    label=pack["name"],
                    description=f"{format_shop_price(owner_id, pack['price'])} • {pack['pulls']} stickers",
                    value=pack_id
                )
            )

        disabled = False

        if not options:
            disabled = True
            options.append(
                discord.SelectOption(
                    label="No packs available",
                    description="Check back later.",
                    value="none"
                )
            )

        super().__init__(
            placeholder="Choose a sticker pack to buy...",
            min_values=1,
            max_values=1,
            options=options,
            disabled=disabled
        )

    async def callback(self, interaction: discord.Interaction):
        pack_id = self.values[0]
        pack = STICKER_PACKS.get(pack_id)

        if not pack:
            await interaction.response.send_message(
                "That sticker pack does not exist.",
                ephemeral=True
            )
            return

        if not is_sticker_pack_purchase_enabled(pack_id):
            await interaction.response.send_message(
                f"{pack['name']} is not currently for sale.",
                ephemeral=True
            )
            return

        if not can_roll_sticker_pack(pack_id):
            await interaction.response.send_message(
                f"{pack['name']} does not have any enabled stickers to pull right now.",
                ephemeral=True
            )
            return

        base_price = pack["price"]
        price = get_discounted_shop_price(interaction.user.id, base_price)
        balance = get_balance(interaction.user.id)

        if balance < price:
            await interaction.response.send_message(
                f"You need **{price:,} gold** to buy {pack['name']}.\n"
                f"Your balance is **{balance:,} gold**.",
                ephemeral=True
            )
            return

        add_gold(interaction.user.id, -price)

        pulls = []
        date_collected = datetime.now(timezone.utc).isoformat()

        for index in range(pack["pulls"]):
            sticker_id = roll_sticker_from_pack(pack_id)

            if not sticker_id:
                await interaction.response.send_message(
                    f"{pack['name']} does not have any enabled stickers to pull right now.",
                    ephemeral=True
                )
                return

            old_quantity = get_player_sticker_quantity(interaction.user.id, sticker_id)

            add_player_sticker(
                interaction.user.id,
                sticker_id,
                1,
                date_collected
            )

            new_quantity = old_quantity + 1
            pulls.append((sticker_id, old_quantity, new_quantity))

        tasks_snapshot, task_rewarded, task_xp_info = apply_daily_task_progress(interaction.user.id, "open_pack")
        task_reward_text = daily_task_reward_text(task_rewarded, task_xp_info)

        await interaction.response.edit_message(
            content=None,
            embed=build_sticker_pack_result_embed(interaction.user.id, pack_id, pulls),
            view=StickerPackResultView(interaction.user.id)
        )

        if task_reward_text:
            await interaction.followup.send(task_reward_text.strip(), ephemeral=True)


class BuyStickerPackSelectView(discord.ui.View):
    def __init__(self, owner_id):
        super().__init__(timeout=180)
        self.owner_id = owner_id

        self.add_item(BuyStickerPackSelect(owner_id))

    async def interaction_check(self, interaction):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message(
                "This sticker pack menu belongs to someone else. Use `/shop` to open your own.",
                ephemeral=True
            )
            return False

        return True

    @discord.ui.button(label="Back to Sticker Packs", emoji="⬅️", style=discord.ButtonStyle.secondary)
    async def back_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(
            content=None,
            embed=build_sticker_pack_shop_embed(self.owner_id),
            view=StickerPackShopView(self.owner_id)
        )


class StickerPackResultView(discord.ui.View):
    def __init__(self, owner_id):
        super().__init__(timeout=180)
        self.owner_id = owner_id

    async def interaction_check(self, interaction):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message(
                "This sticker pack result belongs to someone else. Use `/shop` to open your own.",
                ephemeral=True
            )
            return False

        return True

    @discord.ui.button(label="Buy Another Pack", emoji="📦", style=discord.ButtonStyle.green)
    async def buy_another_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(
            content=None,
            embed=build_sticker_pack_shop_embed(self.owner_id),
            view=BuyStickerPackSelectView(self.owner_id)
        )

    @discord.ui.button(label="View Sticker Book", emoji="📖", style=discord.ButtonStyle.blurple)
    async def view_book_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(
            content=None,
            embed=build_sticker_book_embed(interaction.user),
            view=StickerBookView(self.owner_id, interaction.user)
        )

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
    owned_gameplay = get_owned_gameplay_items(user_id)
    active_shields = get_active_lucky_shields(user_id)

    owned_lines = []

    for item_id, quantity in owned_items:
        item = MISCHIEF_ITEMS.get(item_id)
        if item:
            owned_lines.append(f"{item['name']} x{quantity}")

    for item_id, quantity in owned_gameplay:
        item = GAMEPLAY_ITEMS.get(item_id)
        if item:
            owned_lines.append(f"{item['name']} x{quantity}")

    if active_shields > 0:
        owned_lines.append(lucky_shield_short_text(user_id))

    owned_text = "\n".join(owned_lines) if owned_lines else "No consumables owned yet."

    shop_lines = []

    for item_id, item in MISCHIEF_ITEMS.items():
        shop_lines.append(f"{item['name']} — {format_shop_price(user_id, item['price'])}")

    for item_id, item in GAMEPLAY_ITEMS.items():
        shop_lines.append(f"{item['name']} — {format_shop_price(user_id, item['price'])}")

    embed = discord.Embed(
        title="🎭 Consumables Market",
        description=(
            f"💰 Gold: **{balance:,}**\n\n"
            f"**For Sale:**\n"
            f"{chr(10).join(shop_lines)}\n\n"
            f"**Your Consumables:**\n"
            f"{owned_text}"
        ),
        color=discord.Color.gold()
    )

    embed.set_footer(text="Consumables are for chaos. Lucky Shield protects your next possible gold loss.")
    return embed


def build_buy_mischief_embed(user_id):
    balance = get_balance(user_id)

    lines = []

    for item_id, item in MISCHIEF_ITEMS.items():
        lines.append(f"{item['name']} — {format_shop_price(user_id, item['price'])}")

    for item_id, item in GAMEPLAY_ITEMS.items():
        lines.append(f"{item['name']} — {format_shop_price(user_id, item['price'])}")

    embed = discord.Embed(
        title="💰 Buy Consumables",
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
    owned_gameplay = get_owned_gameplay_items(user_id)

    lines = []

    for item_id, quantity in owned_items:
        item = MISCHIEF_ITEMS.get(item_id)
        if item:
            lines.append(f"{item['name']} x{quantity}")

    for item_id, quantity in owned_gameplay:
        item = GAMEPLAY_ITEMS.get(item_id)
        if item:
            lines.append(f"{item['name']} x{quantity}")

    active_shields = get_active_lucky_shields(user_id)
    if active_shields > 0:
        lines.append(lucky_shield_short_text(user_id))

    owned_text = "\n".join(lines) if lines else "No usable consumables owned."

    embed = discord.Embed(
        title="🎒 Use Consumables",
        description=(
            f"**Your Consumables:**\n"
            f"{owned_text}\n\n"
            "Choose an item. Mischief needs a target; Lucky Shield arms immediately."
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
                "This Consumables Market belongs to someone else. Use `/shop` to open your own.",
                ephemeral=True
            )
            return False

        return True

    @discord.ui.button(label="Buy Consumable", emoji="💰", style=discord.ButtonStyle.green)
    async def buy_mischief_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(
            content=None,
            embed=build_buy_mischief_embed(self.owner_id),
            view=BuyMischiefSelectView(self.owner_id)
        )

    @discord.ui.button(label="Use Consumable", emoji="🎒", style=discord.ButtonStyle.blurple)
    async def use_mischief_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        owned_items = get_owned_mischief_items(self.owner_id)
        owned_gameplay = get_owned_gameplay_items(self.owner_id)

        if not owned_items and not owned_gameplay:
            embed = build_mischief_market_embed(self.owner_id)
            embed.set_footer(text="You do not own any consumables yet.")

            await interaction.response.edit_message(
                content=None,
                embed=embed,
                view=MischiefMarketView(self.owner_id)
            )
            return

        await interaction.response.edit_message(
            content=None,
            embed=build_use_mischief_embed(self.owner_id),
            view=UseConsumableSelectView(
                self.owner_id,
                include_sounds=False,
                include_gameplay=True
            )
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
            item_label = item.get("description", "Mischief item")
            options.append(
                discord.SelectOption(
                    label=item["name"],
                    description=f"{item_label} • {format_shop_price(owner_id, item['price'])}",
                    value=f"mischief:{item_id}"
                )
            )

        for item_id, item in GAMEPLAY_ITEMS.items():
            options.append(
                discord.SelectOption(
                    label=item["name"],
                    description=f"Gameplay • {format_shop_price(owner_id, item['price'])}",
                    value=f"gameplay:{item_id}"
                )
            )

        super().__init__(
            placeholder="Choose consumable to buy...",
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        selected = self.values[0]

        if ":" not in selected:
            await interaction.response.send_message(
                "That consumable does not exist.",
                ephemeral=True
            )
            return

        item_type, item_id = selected.split(":", 1)

        if item_type == "gameplay":
            item = GAMEPLAY_ITEMS.get(item_id)
            inventory_type = "gameplay"
        else:
            item = MISCHIEF_ITEMS.get(item_id)
            inventory_type = "mischief"

        if not item:
            await interaction.response.send_message(
                "That consumable does not exist.",
                ephemeral=True
            )
            return

        base_price = item["price"]
        price = get_discounted_shop_price(interaction.user.id, base_price)
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
            inventory_type,
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
    def __init__(self, owner_id, allowed_target_ids=None, include_sounds=True, include_gameplay=True):
        self.owner_id = owner_id
        self.allowed_target_ids = allowed_target_ids
        self.include_sounds = include_sounds
        self.include_gameplay = include_gameplay

        owned_items = get_owned_mischief_items(owner_id)
        owned_gameplay = get_owned_gameplay_items(owner_id) if include_gameplay else []
        owned_sounds = get_owned_sound_items(owner_id) if include_sounds else []

        options = []

        for item_id, quantity in owned_items:
            item = MISCHIEF_ITEMS.get(item_id)
            if not item:
                continue

            options.append(
                discord.SelectOption(
                    label=item["name"],
                    description=f"Mischief • Owned: {quantity}",
                    value=f"mischief:{item_id}"
                )
            )

        for item_id, quantity in owned_gameplay:
            item = GAMEPLAY_ITEMS.get(item_id)
            if not item:
                continue

            options.append(
                discord.SelectOption(
                    label=item["name"],
                    description=f"Gameplay • Owned: {quantity}",
                    value=f"gameplay:{item_id}"
                )
            )

        for sound_id, quantity in owned_sounds:
            sound = SOUND_ITEMS.get(sound_id)
            if not sound:
                continue

            options.append(
                discord.SelectOption(
                    label=sound["name"],
                    description="Sound Attack • Permanent unlock",
                    value=f"sound:{sound_id}"
                )
            )

        super().__init__(
            placeholder="Choose an item or sound...",
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        selected = self.values[0]

        if ":" not in selected:
            await interaction.response.send_message(
                "That item does not exist.",
                ephemeral=True
            )
            return

        item_type, item_id = selected.split(":", 1)

        if item_type == "sound":
            await interaction.response.edit_message(
                content=None,
                embed=build_sound_target_embed(interaction.user.id, item_id),
                view=UseSoundTargetView(
                    owner_id=interaction.user.id,
                    sound_id=item_id,
                    allowed_target_ids=self.allowed_target_ids,
                    back_to="items"
                )
            )
            return

        if item_type == "gameplay":
            item = GAMEPLAY_ITEMS.get(item_id)

            if not item:
                await interaction.response.send_message(
                    "That gameplay item does not exist.",
                    ephemeral=True
                )
                return

            if item_id in SHIELD_TIERS:
                shield = SHIELD_TIERS[item_id]
                activated = activate_shield_item(interaction.user.id, item_id)

                if not activated:
                    await interaction.response.send_message(
                        f"You do not have {shield['name']} to activate.",
                        ephemeral=True
                    )
                    return

                active_text = lucky_shield_status_text(interaction.user.id)
                percent = int(shield["chance"] * 100)

                embed = discord.Embed(
                    title=f"{shield['name']} ACTIVE",
                    description=(
                        "Your next possible gold loss is now protected.\n\n"
                        f"This shield block chance: **{percent}%**\n\n"
                        f"{active_text}\n\n"
                        "You will see a **SHIELDED** badge next to your name at tables and in your inventory while protection is armed."
                    ),
                    color=discord.Color.green()
                )
                embed.set_footer(text="A shield is consumed when it attempts to protect you, whether it succeeds or shatters.")

                await interaction.response.edit_message(
                    content=None,
                    embed=embed,
                    view=UseConsumableSelectView(
                        owner_id=interaction.user.id,
                        allowed_target_ids=self.allowed_target_ids,
                        include_sounds=self.include_sounds,
                        include_gameplay=self.include_gameplay
                    )
                )
                return

        item = MISCHIEF_ITEMS.get(item_id)

        if not item:
            await interaction.response.send_message(
                "That consumable does not exist.",
                ephemeral=True
            )
            return

        if item.get("requires_target", True) is False:
            await interaction.response.send_message(
                "That consumable is not configured with a use action yet.",
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
    def __init__(self, owner_id, allowed_target_ids=None, include_sounds=True, include_gameplay=True):
        super().__init__(timeout=180)
        self.owner_id = owner_id
        self.allowed_target_ids = allowed_target_ids
        self.include_sounds = include_sounds
        self.include_gameplay = include_gameplay

        self.add_item(UseConsumableSelect(owner_id, allowed_target_ids, include_sounds, include_gameplay))

    async def interaction_check(self, interaction):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message(
                "This item menu belongs to someone else.",
                ephemeral=True
            )
            return False

        return True

    @discord.ui.button(label="Back", emoji="⬅️", style=discord.ButtonStyle.secondary)
    async def back_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.allowed_target_ids is None and not self.include_sounds:
            await interaction.response.edit_message(
                content=None,
                embed=build_mischief_market_embed(self.owner_id),
                view=MischiefMarketView(self.owner_id)
            )
        else:
            await interaction.response.edit_message(
                content=None,
                embed=discord.Embed(
                    title="🎒 Use Tavern Item",
                    description="Choose something from your Tavern inventory.",
                    color=discord.Color.gold()
                ),
                view=UseConsumableSelectView(
                    owner_id=self.owner_id,
                    allowed_target_ids=self.allowed_target_ids,
                    include_sounds=self.include_sounds,
                    include_gameplay=self.include_gameplay
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
        try:
            target = self.values[0]

            if interaction.user.id != self.owner_id:
                await interaction.response.send_message(
                    "This target menu belongs to someone else.",
                    ephemeral=True
                )
                return

            if is_math_drill_active(interaction.channel_id):
                await interaction.response.send_message(
                    math_focus_block_text(interaction.channel_id),
                    ephemeral=True
                )
                return

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

            if get_inventory_by_type(interaction.user.id, "mischief") is None:
                await interaction.response.send_message(
                    "Could not read your consumable inventory.",
                    ephemeral=True
                )
                return

            # Acknowledge the target click first so Discord does not silently time out.
            await interaction.response.defer(ephemeral=True)

            # Build the public result before consuming anything.
            # Mystery Box returns the actual effect so stats only update after the public post succeeds.
            mischief_stat_item_id = None

            if self.item_id == "mystery_box":
                embed, mischief_stat_item_id = build_mystery_box_result(interaction.user, target)
            else:
                embed = build_mischief_result_embed(interaction.user, target, self.item_id)
                mischief_stat_item_id = self.item_id

            public_channel = interaction.channel

            if public_channel is None:
                await interaction.followup.send(
                    "🎭 I could not find a public channel to post the mischief in. Item was not consumed.",
                    ephemeral=True
                )
                return

            # Send the public embed first. If this fails, do not consume the item.
            public_message = await public_channel.send(embed=embed)

            quantity_removed = consume_inventory_item(
                interaction.user.id,
                self.item_id,
                1
            )

            if not quantity_removed:
                try:
                    await public_message.delete()
                except Exception:
                    pass

                await interaction.followup.send(
                    "You do not have that consumable anymore.",
                    ephemeral=True
                )
                return

            task_reward_text = ""
            if mischief_stat_item_id:
                record_mischief_hit(interaction.user.id, target.id, mischief_stat_item_id)
                tasks_snapshot, task_rewarded, task_xp_info = apply_daily_task_progress(interaction.user.id, "use_mischief")
                task_reward_text = daily_task_reward_text(task_rewarded, task_xp_info)

            if task_reward_text:
                await interaction.followup.send(task_reward_text.strip(), ephemeral=True)
            elif item_confirmations_enabled():
                await interaction.followup.send(
                    f"🎭 Mischief deployed: {public_message.jump_url}",
                    ephemeral=True
                )

        except Exception as error:
            import traceback
            traceback.print_exception(type(error), error, error.__traceback__)

            message = f"🎭 Mischief failed before consuming your item: `{error}`"

            try:
                if interaction.response.is_done():
                    await interaction.followup.send(message, ephemeral=True)
                else:
                    await interaction.response.send_message(message, ephemeral=True)
            except Exception:
                pass


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

    async def on_error(self, interaction, error, item):
        import traceback
        traceback.print_exception(type(error), error, error.__traceback__)

        message = f"Mischief target menu error: `{error}`"

        if interaction.response.is_done():
            await interaction.followup.send(message, ephemeral=True)
        else:
            await interaction.response.send_message(message, ephemeral=True)

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
    active_title = get_active_title(user_id)
    active_title_id = get_active_title_id(user_id)
    active_bonus = get_title_bonus_description(active_title_id)
    owned_title_ids = get_player_titles(user_id)

    owned_titles = [f"{DEFAULT_TITLE} — No bonus"]

    for title_id in owned_title_ids:
        title = TITLE_ITEMS.get(title_id)
        if title:
            owned_titles.append(
                f"{title['name']} — {title.get('bonus_description', 'No bonus')}"
            )

    owned_text = "\n".join(owned_titles)

    available_lines = []

    for title_id, title in TITLE_ITEMS.items():
        price_text = format_shop_price(user_id, title["price"])
        name = title["name"]
        rarity = title.get("rarity", "Title")
        bonus = title.get("bonus_description", "No bonus")

        if title_id in owned_title_ids:
            available_lines.append(f"✅ {name} — Owned — {bonus}")
        else:
            available_lines.append(f"{name} [{rarity}] — {price_text} — {bonus}")

    available_text = "\n".join(available_lines)

    embed = discord.Embed(
        title="🎖 Title Shop",
        description=(
            f"💰 Gold: **{balance:,}**\n\n"
            f"**Current Title:**\n"
            f"{active_title}\n"
            f"Bonus: **{active_bonus}**\n"
            f"{title_swap_status_text(user_id)}\n\n"
            f"**Owned Titles:**\n"
            f"{owned_text}\n\n"
            f"**Available Titles:**\n"
            f"{available_text}"
        ),
        color=discord.Color.gold()
    )

    embed.set_footer(text="Buy a title, then equip it. You can change titles once every 24 hours.")
    return embed



def build_buy_titles_embed(user_id):
    balance = get_balance(user_id)

    lines = []

    for title_id, title in TITLE_ITEMS.items():
        if player_owns_item(user_id, title_id):
            continue

        lines.append(
            f"{title['name']} — {format_shop_price(user_id, title['price'])} — "
            f"{title.get('bonus_description', 'No bonus')}"
        )

    available_text = "\n".join(lines)

    if not available_text:
        available_text = "You already own every title in the shop."

    embed = discord.Embed(
        title="💰 Buy a Title",
        description=(
            f"💰 Gold: **{balance:,}**"
            f"{shop_discount_line(user_id)}\n\n"
            f"{available_text}\n\n"
            "Choose a title from the dropdown below."
        ),
        color=discord.Color.gold()
    )

    return embed



def build_equip_titles_embed(user_id):
    active_title = get_active_title(user_id)
    active_title_id = get_active_title_id(user_id)
    active_bonus = get_title_bonus_description(active_title_id)

    owned_title_ids = get_player_titles(user_id)

    owned_titles = [f"{DEFAULT_TITLE} — No bonus"]

    for title_id in owned_title_ids:
        title = TITLE_ITEMS.get(title_id)
        if title:
            owned_titles.append(
                f"{title['name']} — {title.get('bonus_description', 'No bonus')}"
            )

    embed = discord.Embed(
        title="🎖 Equip a Title",
        description=(
            f"**Current Title:**\n"
            f"{active_title}\n"
            f"Bonus: **{active_bonus}**\n"
            f"{title_swap_status_text(user_id)}\n\n"
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
                    description=format_shop_price(owner_id, title["price"]),
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

        base_price = title["price"]
        price = get_discounted_shop_price(interaction.user.id, base_price)
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
                    description=title.get("bonus_description", "Owned title"),
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
        current_title = get_active_title(interaction.user.id)

        if selected == "default":
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

        if equipped_title == current_title:
            await interaction.response.send_message(
                f"{equipped_title} is already your active title.",
                ephemeral=True
            )
            return

        remaining = get_title_swap_remaining_seconds(interaction.user.id)

        if remaining > 0:
            await interaction.response.send_message(
                "⏳ You already changed your title recently.\n"
                f"You can change it again in **{format_seconds_compact(remaining)}**.",
                ephemeral=True
            )
            return

        set_player_title(interaction.user.id, equipped_title)
        mark_title_changed(interaction.user.id)

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

    async def cog_load(self):
        if not self.tavern_event_loop.is_running():
            self.tavern_event_loop.start()

    async def cog_unload(self):
        if self.tavern_event_loop.is_running():
            self.tavern_event_loop.cancel()

    @tasks.loop(hours=1)
    async def tavern_event_loop(self):
        await self.bot.wait_until_ready()

        if random.random() > TAVERN_EVENT_CHANCE:
            return

        channel = self.bot.get_channel(TAVERN_CHANNEL_ID)
        if channel is None:
            return

        player_ids = get_all_player_ids()
        if not player_ids:
            return

        player_id = random.choice(player_ids)

        try:
            player_id_int = int(player_id)
        except ValueError:
            return

        outcome = random.choice([
            "found_gold",
            "lost_gold",
            "xp",
            "tomato",
            "common_sticker",
        ])

        title = "🍻 Tavern Event"
        description = f"<@{player_id_int}> "

        if outcome == "found_gold":
            add_gold(player_id_int, 50)
            description += "found **50 gold** under the bar. Nobody ask why it was sticky."

        elif outcome == "lost_gold":
            balance = get_balance(player_id_int)
            loss = min(25, balance)
            if loss > 0:
                add_gold(player_id_int, -loss)
                description += f"lost **{loss} gold** buying mystery peanuts. Worth it? Unknown."
            else:
                description += "tried to buy mystery peanuts, but was too broke to suffer financially."

        elif outcome == "xp":
            award_tavern_xp(player_id_int, 10, "event")
            description += "gained **10 XP** from questionable Tavern wisdom."

        elif outcome == "tomato":
            description += "got splashed by a rogue tomato. No one has claimed responsibility."

        else:
            common_stickers = get_common_sticker_ids()
            if common_stickers:
                sticker_id = random.choice(common_stickers)
                sticker = STICKERS.get(sticker_id, {"name": sticker_id})
                old_quantity = get_player_sticker_quantity(player_id_int, sticker_id)
                add_player_sticker(
                    player_id_int,
                    sticker_id,
                    1,
                    datetime.now(timezone.utc).isoformat()
                )
                status = "NEW!" if old_quantity == 0 else f"x{old_quantity + 1}"
                description += f"found a common sticker: **{sticker['name']}** — **{status}**."
            else:
                description += "almost found a sticker, but the sticker drawer was empty."

        embed = discord.Embed(
            title=title,
            description=description,
            color=discord.Color.gold()
        )
        embed.set_footer(text="Random Tavern Events roll once per hour with a 40% chance.")

        await channel.send(embed=embed, allowed_mentions=discord.AllowedMentions(users=True, roles=False, everyone=False))

    @tavern_event_loop.before_loop
    async def before_tavern_event_loop(self):
        await self.bot.wait_until_ready()

    @app_commands.command(name="tasks", description="View your Daily Tavern Tasks")
    async def tasks(self, interaction: discord.Interaction):
        if not is_tavern_or_shop_channel(interaction):
            await interaction.response.send_message(
                "✅ Use `/tasks` in The Tavern or the Tavern shop channel.",
                ephemeral=True
            )
            return

        await interaction.response.send_message(
            embed=build_daily_tasks_embed(interaction.user.id),
            ephemeral=True
        )

    @app_commands.command(name="tip", description="Tip another Tavern player gold")
    @app_commands.describe(user="Player to tip", amount="Gold amount, up to 100 per hour")
    async def tip(self, interaction: discord.Interaction, user: discord.User, amount: int):
        if not is_tavern_or_shop_channel(interaction):
            await interaction.response.send_message(
                "💸 Use `/tip` in The Tavern or the Tavern shop channel.",
                ephemeral=True
            )
            return

        if user.bot:
            await interaction.response.send_message(
                "💸 You cannot tip bots. The Tavern Bot refuses your hush money.",
                ephemeral=True
            )
            return

        if user.id == interaction.user.id:
            await interaction.response.send_message(
                "💸 You cannot tip yourself. That is just moving coins between pockets.",
                ephemeral=True
            )
            return

        if amount <= 0:
            await interaction.response.send_message(
                "💸 Tip amount must be greater than 0.",
                ephemeral=True
            )
            return

        hour_key = current_hour_key()
        tipped_this_hour = get_hourly_tip_total(interaction.user.id, hour_key)
        remaining = max(0, TIP_HOURLY_LIMIT - tipped_this_hour)

        if amount > remaining:
            await interaction.response.send_message(
                f"💸 You can only tip **{TIP_HOURLY_LIMIT} gold per hour**.\n"
                f"Remaining this hour: **{remaining} gold**.",
                ephemeral=True
            )
            return

        balance = get_balance(interaction.user.id)

        if balance < amount:
            await interaction.response.send_message(
                f"💸 You only have **{balance:,} gold**.",
                ephemeral=True
            )
            return

        add_gold(interaction.user.id, -amount)
        new_recipient_balance = add_gold(user.id, amount)
        add_hourly_tip_total(interaction.user.id, hour_key, amount)

        await interaction.response.send_message(
            f"💸 {interaction.user.mention} tipped {user.mention} **{amount:,} gold**.\n"
            f"{user.mention}'s new balance: **{new_recipient_balance:,} gold**.",
            allowed_mentions=discord.AllowedMentions(users=True, roles=False, everyone=False)
        )

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

    @app_commands.command(name="packcontrol", description="Founder only - enable or disable sticker pack availability")
    @app_commands.describe(
        pack="Sticker pack to update",
        purchase_enabled="Can users buy this pack from the shop?",
        tavern_mix_enabled="Can this pack's collection appear in Tavern Mix?"
    )
    @app_commands.choices(pack=[
        app_commands.Choice(name="Welcome Pack", value="welcome_pack"),
        app_commands.Choice(name="Mischief Pack", value="mischief_pack"),
        app_commands.Choice(name="Casino Pack", value="casino_pack"),
        app_commands.Choice(name="Tavern Mix Pack", value="tavern_mix_pack"),
    ])
    async def packcontrol(
        self,
        interaction: discord.Interaction,
        pack: app_commands.Choice[str],
        purchase_enabled: bool,
        tavern_mix_enabled: bool
    ):
        if interaction.user.id != FOUNDER_ID:
            await interaction.response.send_message("🚫 Founder only.", ephemeral=True)
            return

        pack_id = pack.value

        if pack_id not in STICKER_PACKS:
            await interaction.response.send_message(
                "That sticker pack does not exist.",
                ephemeral=True
            )
            return

        updated_at = datetime.now(timezone.utc).isoformat()

        set_sticker_pack_setting(
            pack_id,
            purchase_enabled,
            tavern_mix_enabled,
            updated_at
        )

        await interaction.response.send_message(
            embed=build_pack_control_embed(),
            ephemeral=True
        )

    @app_commands.command(name="packstatus", description="Founder only - view sticker pack availability")
    async def packstatus(self, interaction: discord.Interaction):
        if interaction.user.id != FOUNDER_ID:
            await interaction.response.send_message("🚫 Founder only.", ephemeral=True)
            return

        await interaction.response.send_message(
            embed=build_pack_control_embed(),
            ephemeral=True
        )

    @app_commands.command(name="confirmations", description="Founder only - toggle private item success confirmations")
    @app_commands.describe(enabled="Show private success confirmations after public item actions?")
    async def confirmations(self, interaction: discord.Interaction, enabled: Optional[bool] = None):
        if interaction.user.id != FOUNDER_ID:
            await interaction.response.send_message("🚫 Founder only.", ephemeral=True)
            return

        if enabled is not None:
            set_item_confirmations_enabled(enabled)

        await interaction.response.send_message(
            embed=build_confirmation_control_embed(),
            ephemeral=True
        )

    @app_commands.command(name="profile", description="View a Tavern profile")
    @app_commands.describe(user="Player to view")
    async def profile(self, interaction: discord.Interaction, user: Optional[discord.User] = None):
        if not is_tavern_or_shop_channel(interaction):
            await interaction.response.send_message(
                "🍺 Use `/profile` in **The Tavern** or the Tavern shop channel.",
                ephemeral=True
            )
            return

        target = user or interaction.user
        await send_profile(interaction, target)
        
    @app_commands.command(name="shop", description="Open The Tavern shop")
    async def shop(self, interaction: discord.Interaction):
        if not is_tavern_or_shop_channel(interaction):
            await interaction.response.send_message(
                "🏪 Use `/shop` in The Tavern or the Tavern shop channel.",
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
        if not is_tavern_or_shop_channel(interaction):
            await interaction.response.send_message(
                "🍺 Use `/profile` in **The Tavern** or the Tavern shop channel.",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title="🍺 Welcome to The Tavern",
            description=(
                "Try your luck, claim your gold, and make questionable decisions.\n\n"
                "**Available:**\n"
                "🍺 Daily Gold\n"
                "✅ Daily Tasks\n"
                "💰 Balance\n"
                "👤 Profile\n"
                "🏪 Shop\n"
                "🧠 Math Drills\n"
                "🪦 Hangman\n"
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
