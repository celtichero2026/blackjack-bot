from datetime import datetime, timezone

from achievements import ACHIEVEMENTS
from database import award_achievement, get_profile, get_math_stats


def check_achievements(user_id: int):
    earned = []
    profile = get_profile(user_id)

    if profile is None:
        return earned

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
        xp,
        *_rest
    ) = profile

    math_stats = get_math_stats(user_id)

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
    ) = math_stats

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    def try_award(achievement_id):
        if award_achievement(user_id, achievement_id, today):
            earned.append(ACHIEVEMENTS[achievement_id]["name"])

    if games_played >= 1:
        try_award("FIRST_DRINK")

    if wins >= 1:
        try_award("FIRST_WIN")

    if losses >= 1:
        try_award("FIRST_LOSS")

    if pushes >= 1:
        try_award("PUSH_IT")

    if blackjacks >= 1:
        try_award("BLACKJACK")

    if doubles >= 1:
        try_award("DOUBLE_TROUBLE")

    if wins >= 3:
        try_award("HOT_STREAK")

    if wins >= 10:
        try_award("ON_A_HEATER")

    if losses >= 10:
        try_award("DOWN_BAD")

    if balance <= 0:
        try_award("BROKE_AGAIN")

    if balance >= 5000:
        try_award("GOLD_HOARDER")

    if balance >= 10000:
        try_award("TAVERN_ROYALTY")

    if games_played >= 25:
        try_award("REGULAR")

    if games_played >= 100:
        try_award("VETERAN")

    if biggest_win >= 500:
        try_award("BIG_WINNER")

    if total_wagered >= 5000:
        try_award("HIGH_ROLLER")

    if biggest_loss >= 5000:
        try_award("HOUSE_FAVORITE")

    if math_games_played >= 1:
        try_award("MATH_FIRST_BRAINCELL")

    if math_correct_answers >= 10:
        try_award("MATH_ACTUALLY_STUDYING")

    if math_medium_perfect_rounds >= 1:
        try_award("MATH_MENTAL_MENACE")

    if math_hard_perfect_rounds >= 1:
        try_award("MATH_BIG_BRAIN")

    if math_fastest_answer_ms > 0 and math_fastest_answer_ms <= 3000:
        try_award("MATH_QUICK_MATHS")

    return earned
