import sqlite3
from datetime import datetime, timedelta

DB_NAME = "data/casino.db"

def connect():
    return sqlite3.connect(DB_NAME)

def adjust_gold(user_id: int, amount: int):
    conn = connect()
    cur = conn.cursor()

    cur.execute(
        "INSERT OR IGNORE INTO players (user_id) VALUES (?)",
        (str(user_id),)
    )

    cur.execute(
        "UPDATE players SET balance = balance + ? WHERE user_id = ?",
        (amount, str(user_id))
    )

    conn.commit()
    conn.close()

def get_profile(user_id: int):
    conn = connect()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT
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
        FROM players
        WHERE user_id = ?
        """,
        (str(user_id),)
    )

    row = cur.fetchone()

    conn.close()

    return row


def add_gold(user_id, amount):
    conn = connect()
    cur = conn.cursor()

    cur.execute(
        "INSERT OR IGNORE INTO players (user_id) VALUES (?)",
        (str(user_id),)
    )

    cur.execute(
        "UPDATE players SET balance = balance + ? WHERE user_id = ?",
        (amount, str(user_id))
    )

    cur.execute(
        "SELECT balance FROM players WHERE user_id = ?",
        (str(user_id),)
    )

    balance = cur.fetchone()[0]

    conn.commit()
    conn.close()

    return balance

def setup_database():
    conn = connect()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS players (
            user_id TEXT PRIMARY KEY,
            balance INTEGER DEFAULT 1000,
            wins INTEGER DEFAULT 0,
            losses INTEGER DEFAULT 0,
            games_played INTEGER DEFAULT 0,
            last_daily TEXT
        )
    """)

    extra_columns = {
        "pushes": "INTEGER DEFAULT 0",
        "blackjacks": "INTEGER DEFAULT 0",
        "doubles": "INTEGER DEFAULT 0",
        "biggest_win": "INTEGER DEFAULT 0",
        "biggest_loss": "INTEGER DEFAULT 0",
        "total_wagered": "INTEGER DEFAULT 0",
        "title": "TEXT DEFAULT '🍺 Tavern Newbie'",
        "xp": "INTEGER DEFAULT 0",
        "tomatoes_thrown": "INTEGER DEFAULT 0",
        "tomatoes_taken": "INTEGER DEFAULT 0",
        "pies_thrown": "INTEGER DEFAULT 0",
        "pies_taken": "INTEGER DEFAULT 0",
        "featured_sticker_id": "TEXT DEFAULT ''",
        "title_changed_at": "TEXT DEFAULT ''",
        "daily_streak": "INTEGER DEFAULT 0",
    }

    for column, definition in extra_columns.items():
        try:
            cur.execute(
                f"ALTER TABLE players ADD COLUMN {column} {definition}"
            )
        except sqlite3.OperationalError:
            pass

    cur.execute("""
        CREATE TABLE IF NOT EXISTS player_achievements (
            user_id TEXT,
            achievement_id TEXT,
            date_earned TEXT,
            PRIMARY KEY (user_id, achievement_id)
        )
    """)
    
    cur.execute("""
        CREATE TABLE IF NOT EXISTS player_inventory (
            user_id TEXT,
            item_id TEXT,
            item_type TEXT,
            quantity INTEGER DEFAULT 1,
            date_acquired TEXT,
            PRIMARY KEY (user_id, item_id)
        )
    """)
    
    cur.execute("""
        CREATE TABLE IF NOT EXISTS player_stickers (
            user_id TEXT,
            sticker_id TEXT,
            quantity INTEGER DEFAULT 1,
            first_collected TEXT,
            PRIMARY KEY (user_id, sticker_id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS sticker_pack_settings (
            pack_id TEXT PRIMARY KEY,
            purchase_enabled INTEGER DEFAULT 1,
            tavern_mix_enabled INTEGER DEFAULT 1,
            updated_at TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS tavern_settings (
            setting_key TEXT PRIMARY KEY,
            setting_value TEXT,
            updated_at TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS player_effects (
            user_id TEXT,
            effect_id TEXT,
            quantity INTEGER DEFAULT 1,
            updated_at TEXT,
            PRIMARY KEY (user_id, effect_id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS player_math_stats (
            user_id TEXT PRIMARY KEY,
            games_played INTEGER DEFAULT 0,
            daily_games_played INTEGER DEFAULT 0,
            correct_answers INTEGER DEFAULT 0,
            wrong_answers INTEGER DEFAULT 0,
            perfect_rounds INTEGER DEFAULT 0,
            medium_perfect_rounds INTEGER DEFAULT 0,
            hard_perfect_rounds INTEGER DEFAULT 0,
            best_streak INTEGER DEFAULT 0,
            fastest_answer_ms INTEGER DEFAULT 0,
            last_daily_challenge TEXT DEFAULT ''
        )
    """)

    # Add newer math timing columns if this database already existed.
    for column, definition in {
        "total_answer_time_ms": "INTEGER DEFAULT 0",
        "timed_answer_count": "INTEGER DEFAULT 0",
        "total_match_time_ms": "INTEGER DEFAULT 0",
        "completed_match_count": "INTEGER DEFAULT 0",
    }.items():
        try:
            cur.execute(
                f"ALTER TABLE player_math_stats ADD COLUMN {column} {definition}"
            )
        except sqlite3.OperationalError:
            pass

    cur.execute("""
        CREATE TABLE IF NOT EXISTS player_hangman_stats (
            user_id TEXT PRIMARY KEY,
            games_played INTEGER DEFAULT 0,
            guesser_games INTEGER DEFAULT 0,
            undertaker_games INTEGER DEFAULT 0,
            guesser_wins INTEGER DEFAULT 0,
            undertaker_wins INTEGER DEFAULT 0,
            letters_guessed INTEGER DEFAULT 0,
            down_to_wire_wins INTEGER DEFAULT 0
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS player_daily_tasks (
            user_id TEXT,
            task_date TEXT,
            play_game INTEGER DEFAULT 0,
            take_shot INTEGER DEFAULT 0,
            use_mischief INTEGER DEFAULT 0,
            open_pack INTEGER DEFAULT 0,
            complete_math INTEGER DEFAULT 0,
            reward_claimed INTEGER DEFAULT 0,
            PRIMARY KEY (user_id, task_date)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS player_tip_limits (
            user_id TEXT,
            hour_key TEXT,
            total_tipped INTEGER DEFAULT 0,
            PRIMARY KEY (user_id, hour_key)
        )
    """)

    conn.commit()
    conn.close()



def get_or_create_player(user_id: int):
    conn = connect()
    cur = conn.cursor()

    cur.execute(
        "INSERT OR IGNORE INTO players (user_id) VALUES (?)",
        (str(user_id),)
    )

    cur.execute(
        "SELECT balance, wins, losses, games_played, last_daily FROM players WHERE user_id = ?",
        (str(user_id),)
    )

    player = cur.fetchone()
    conn.commit()
    conn.close()

    return player

def claim_daily(user_id: int, reward: int, today: str):
    conn = connect()
    cur = conn.cursor()

    cur.execute(
        "INSERT OR IGNORE INTO players (user_id) VALUES (?)",
        (str(user_id),)
    )

    cur.execute(
        "SELECT balance, last_daily FROM players WHERE user_id = ?",
        (str(user_id),)
    )

    balance, last_daily = cur.fetchone()

    if last_daily == today:
        conn.close()
        return False, balance

    new_balance = balance + reward

    cur.execute(
        "UPDATE players SET balance = ?, last_daily = ? WHERE user_id = ?",
        (new_balance, today, str(user_id))
    )

    conn.commit()
    conn.close()

    return True, new_balance

def get_leaderboard(limit: int = 10):
    conn = connect()
    cur = conn.cursor()

    cur.execute("""
        SELECT user_id, xp, balance, games_played
        FROM players
        ORDER BY xp DESC, games_played DESC, balance DESC
        LIMIT ?
    """, (limit,))

    rows = cur.fetchall()
    conn.close()

    return rows

def get_balance(user_id: int):
    conn = connect()
    cur = conn.cursor()

    cur.execute(
        "INSERT OR IGNORE INTO players (user_id) VALUES (?)",
        (str(user_id),)
    )

    cur.execute(
        "SELECT balance FROM players WHERE user_id = ?",
        (str(user_id),)
    )

    balance = cur.fetchone()[0]

    conn.commit()
    conn.close()

    return balance


def record_game_result(user_id: int, result: str, amount_change: int):
    conn = connect()
    cur = conn.cursor()

    cur.execute(
        "INSERT OR IGNORE INTO players (user_id) VALUES (?)",
        (str(user_id),)
    )

    if result == "win":
        cur.execute("""
            UPDATE players
            SET balance = balance + ?,
                wins = wins + 1,
                games_played = games_played + 1
            WHERE user_id = ?
        """, (amount_change, str(user_id)))

    elif result == "loss":
        cur.execute("""
            UPDATE players
            SET balance = balance + ?,
                losses = losses + 1,
                games_played = games_played + 1
            WHERE user_id = ?
        """, (amount_change, str(user_id)))

    else:
        cur.execute("""
            UPDATE players
            SET games_played = games_played + 1
            WHERE user_id = ?
        """, (str(user_id),))

    conn.commit()
    conn.close()

def award_achievement(user_id: int, achievement_id: str, date_earned: str):
    conn = connect()
    cur = conn.cursor()

    cur.execute(
        """
        INSERT OR IGNORE INTO player_achievements
        (user_id, achievement_id, date_earned)
        VALUES (?, ?, ?)
        """,
        (str(user_id), achievement_id, date_earned)
    )

    awarded = cur.rowcount > 0

    conn.commit()
    conn.close()

    return awarded


def get_player_achievements(user_id: int):
    conn = connect()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT achievement_id, date_earned
        FROM player_achievements
        WHERE user_id = ?
        ORDER BY date_earned ASC
        """,
        (str(user_id),)
    )

    rows = cur.fetchall()

    conn.close()

    return rows

def record_wager(user_id: int, amount: int):
    conn = connect()
    cur = conn.cursor()

    cur.execute("INSERT OR IGNORE INTO players (user_id) VALUES (?)", (str(user_id),))

    cur.execute("""
        UPDATE players
        SET total_wagered = total_wagered + ?
        WHERE user_id = ?
    """, (amount, str(user_id)))

    conn.commit()
    conn.close()


def record_double(user_id: int):
    conn = connect()
    cur = conn.cursor()

    cur.execute("INSERT OR IGNORE INTO players (user_id) VALUES (?)", (str(user_id),))

    cur.execute("""
        UPDATE players
        SET doubles = doubles + 1
        WHERE user_id = ?
    """, (str(user_id),))

    conn.commit()
    conn.close()


def record_blackjack(user_id: int):
    conn = connect()
    cur = conn.cursor()

    cur.execute("INSERT OR IGNORE INTO players (user_id) VALUES (?)", (str(user_id),))

    cur.execute("""
        UPDATE players
        SET blackjacks = blackjacks + 1
        WHERE user_id = ?
    """, (str(user_id),))

    conn.commit()
    conn.close()


def update_biggest_win(user_id: int, amount: int):
    conn = connect()
    cur = conn.cursor()

    cur.execute("""
        UPDATE players
        SET biggest_win = MAX(biggest_win, ?)
        WHERE user_id = ?
    """, (amount, str(user_id)))

    conn.commit()
    conn.close()


def update_biggest_loss(user_id: int, amount: int):
    conn = connect()
    cur = conn.cursor()

    cur.execute("""
        UPDATE players
        SET biggest_loss = MAX(biggest_loss, ?)
        WHERE user_id = ?
    """, (amount, str(user_id)))

    conn.commit()
    conn.close()

def record_game_stat(user_id: int, result: str):
    conn = connect()
    cur = conn.cursor()

    cur.execute(
        "INSERT OR IGNORE INTO players (user_id) VALUES (?)",
        (str(user_id),)
    )

    if result == "win":
        cur.execute(
            "UPDATE players SET wins = wins + 1, games_played = games_played + 1 WHERE user_id = ?",
            (str(user_id),)
        )
    elif result == "loss":
        cur.execute(
            "UPDATE players SET losses = losses + 1, games_played = games_played + 1 WHERE user_id = ?",
            (str(user_id),)
        )
    elif result == "push":
        cur.execute(
            "UPDATE players SET pushes = pushes + 1, games_played = games_played + 1 WHERE user_id = ?",
            (str(user_id),)
        )

    conn.commit()
    conn.close()

def add_xp(user_id: int, amount: int):
    conn = connect()
    cur = conn.cursor()

    cur.execute(
        "INSERT OR IGNORE INTO players (user_id) VALUES (?)",
        (str(user_id),)
    )

    cur.execute(
        "SELECT xp FROM players WHERE user_id = ?",
        (str(user_id),)
    )

    old_xp = cur.fetchone()[0]

    old_level, old_current, old_needed = get_level_info(old_xp)

    new_xp = old_xp + amount
    new_level, new_current, new_needed = get_level_info(new_xp)

    cur.execute(
        "UPDATE players SET xp = ? WHERE user_id = ?",
        (new_xp, str(user_id))
    )

    conn.commit()
    conn.close()

    return {
        "xp_gained": amount,
        "old_xp": old_xp,
        "new_xp": new_xp,
        "old_level": old_level,
        "new_level": new_level,
        "level_up": new_level > old_level,
        "xp_current": new_current,
        "xp_needed": new_needed,
    }


def get_level_info(xp: int):
    level = 1
    xp_remaining = xp

    while xp_remaining >= level * 100:
        xp_remaining -= level * 100
        level += 1

    xp_needed = level * 100

    return level, xp_remaining, xp_needed

def add_inventory_item(user_id: int, item_id: str, item_type: str, date_acquired: str):
    conn = connect()
    cur = conn.cursor()

    cur.execute(
        """
        INSERT OR IGNORE INTO player_inventory
        (user_id, item_id, item_type, quantity, date_acquired)
        VALUES (?, ?, ?, 1, ?)
        """,
        (str(user_id), item_id, item_type, date_acquired)
    )

    added = cur.rowcount > 0

    conn.commit()
    conn.close()

    return added


def player_owns_item(user_id: int, item_id: str):
    conn = connect()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT 1
        FROM player_inventory
        WHERE user_id = ? AND item_id = ?
        """,
        (str(user_id), item_id)
    )

    owns = cur.fetchone() is not None

    conn.close()

    return owns


def get_player_titles(user_id: int):
    conn = connect()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT item_id
        FROM player_inventory
        WHERE user_id = ? AND item_type = 'title'
        ORDER BY date_acquired ASC
        """,
        (str(user_id),)
    )

    rows = cur.fetchall()

    conn.close()

    return [row[0] for row in rows]


def set_player_title(user_id: int, title: str):
    conn = connect()
    cur = conn.cursor()

    cur.execute(
        "INSERT OR IGNORE INTO players (user_id) VALUES (?)",
        (str(user_id),)
    )

    cur.execute(
        """
        UPDATE players
        SET title = ?
        WHERE user_id = ?
        """,
        (title, str(user_id))
    )

    conn.commit()
    conn.close()


def get_title_changed_at(user_id: int):
    conn = connect()
    cur = conn.cursor()

    cur.execute(
        "INSERT OR IGNORE INTO players (user_id) VALUES (?)",
        (str(user_id),)
    )

    cur.execute(
        """
        SELECT title_changed_at
        FROM players
        WHERE user_id = ?
        """,
        (str(user_id),)
    )

    row = cur.fetchone()

    conn.commit()
    conn.close()

    if not row:
        return ""

    return row[0] or ""


def set_title_changed_at(user_id: int, changed_at: str):
    conn = connect()
    cur = conn.cursor()

    cur.execute(
        "INSERT OR IGNORE INTO players (user_id) VALUES (?)",
        (str(user_id),)
    )

    cur.execute(
        """
        UPDATE players
        SET title_changed_at = ?
        WHERE user_id = ?
        """,
        (changed_at, str(user_id))
    )

    conn.commit()
    conn.close()


def add_inventory_quantity(user_id: int, item_id: str, item_type: str, amount: int, date_acquired: str):
    conn = connect()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT quantity
        FROM player_inventory
        WHERE user_id = ? AND item_id = ?
        """,
        (str(user_id), item_id)
    )

    row = cur.fetchone()

    if row:
        cur.execute(
            """
            UPDATE player_inventory
            SET quantity = quantity + ?
            WHERE user_id = ? AND item_id = ?
            """,
            (amount, str(user_id), item_id)
        )
    else:
        cur.execute(
            """
            INSERT INTO player_inventory
            (user_id, item_id, item_type, quantity, date_acquired)
            VALUES (?, ?, ?, ?, ?)
            """,
            (str(user_id), item_id, item_type, amount, date_acquired)
        )

    conn.commit()
    conn.close()


def get_inventory_quantity(user_id: int, item_id: str):
    conn = connect()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT quantity
        FROM player_inventory
        WHERE user_id = ? AND item_id = ?
        """,
        (str(user_id), item_id)
    )

    row = cur.fetchone()

    conn.close()

    if not row:
        return 0

    return row[0]


def consume_inventory_item(user_id: int, item_id: str, amount: int = 1):
    conn = connect()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT quantity
        FROM player_inventory
        WHERE user_id = ? AND item_id = ?
        """,
        (str(user_id), item_id)
    )

    row = cur.fetchone()

    if not row or row[0] < amount:
        conn.close()
        return False

    new_quantity = row[0] - amount

    if new_quantity <= 0:
        cur.execute(
            """
            DELETE FROM player_inventory
            WHERE user_id = ? AND item_id = ?
            """,
            (str(user_id), item_id)
        )
    else:
        cur.execute(
            """
            UPDATE player_inventory
            SET quantity = ?
            WHERE user_id = ? AND item_id = ?
            """,
            (new_quantity, str(user_id), item_id)
        )

    conn.commit()
    conn.close()

    return True


def get_inventory_by_type(user_id: int, item_type: str):
    conn = connect()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT item_id, quantity
        FROM player_inventory
        WHERE user_id = ? AND item_type = ?
        ORDER BY date_acquired ASC
        """,
        (str(user_id), item_type)
    )

    rows = cur.fetchall()

    conn.close()

    return rows



def add_player_effect(user_id: int, effect_id: str, amount: int = 1, updated_at: str = ""):
    conn = connect()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT quantity
        FROM player_effects
        WHERE user_id = ? AND effect_id = ?
        """,
        (str(user_id), effect_id)
    )

    row = cur.fetchone()

    if row:
        cur.execute(
            """
            UPDATE player_effects
            SET quantity = quantity + ?, updated_at = ?
            WHERE user_id = ? AND effect_id = ?
            """,
            (amount, updated_at, str(user_id), effect_id)
        )
    else:
        cur.execute(
            """
            INSERT INTO player_effects
            (user_id, effect_id, quantity, updated_at)
            VALUES (?, ?, ?, ?)
            """,
            (str(user_id), effect_id, amount, updated_at)
        )

    conn.commit()
    conn.close()


def get_player_effect_quantity(user_id: int, effect_id: str):
    conn = connect()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT quantity
        FROM player_effects
        WHERE user_id = ? AND effect_id = ?
        """,
        (str(user_id), effect_id)
    )

    row = cur.fetchone()

    conn.close()

    if not row:
        return 0

    return row[0]


def consume_player_effect(user_id: int, effect_id: str, amount: int = 1):
    conn = connect()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT quantity
        FROM player_effects
        WHERE user_id = ? AND effect_id = ?
        """,
        (str(user_id), effect_id)
    )

    row = cur.fetchone()

    if not row or row[0] < amount:
        conn.close()
        return False

    new_quantity = row[0] - amount

    if new_quantity <= 0:
        cur.execute(
            """
            DELETE FROM player_effects
            WHERE user_id = ? AND effect_id = ?
            """,
            (str(user_id), effect_id)
        )
    else:
        cur.execute(
            """
            UPDATE player_effects
            SET quantity = ?
            WHERE user_id = ? AND effect_id = ?
            """,
            (new_quantity, str(user_id), effect_id)
        )

    conn.commit()
    conn.close()

    return True


def record_mischief_hit(attacker_id: int, target_id: int, item_id: str):
    conn = connect()
    cur = conn.cursor()

    cur.execute(
        "INSERT OR IGNORE INTO players (user_id) VALUES (?)",
        (str(attacker_id),)
    )

    cur.execute(
        "INSERT OR IGNORE INTO players (user_id) VALUES (?)",
        (str(target_id),)
    )

    if item_id == "rotten_tomato":
        cur.execute(
            """
            UPDATE players
            SET tomatoes_thrown = tomatoes_thrown + 1
            WHERE user_id = ?
            """,
            (str(attacker_id),)
        )

        cur.execute(
            """
            UPDATE players
            SET tomatoes_taken = tomatoes_taken + 1
            WHERE user_id = ?
            """,
            (str(target_id),)
        )

    elif item_id == "cream_pie":
        cur.execute(
            """
            UPDATE players
            SET pies_thrown = pies_thrown + 1
            WHERE user_id = ?
            """,
            (str(attacker_id),)
        )

        cur.execute(
            """
            UPDATE players
            SET pies_taken = pies_taken + 1
            WHERE user_id = ?
            """,
            (str(target_id),)
        )

    conn.commit()
    conn.close()


def get_mischief_stats(user_id: int):
    conn = connect()
    cur = conn.cursor()

    cur.execute(
        "INSERT OR IGNORE INTO players (user_id) VALUES (?)",
        (str(user_id),)
    )

    cur.execute(
        """
        SELECT
            tomatoes_thrown,
            tomatoes_taken,
            pies_thrown,
            pies_taken
        FROM players
        WHERE user_id = ?
        """,
        (str(user_id),)
    )

    row = cur.fetchone()

    conn.commit()
    conn.close()

    if not row:
        return 0, 0, 0, 0

    return row

def add_player_sticker(user_id: int, sticker_id: str, amount: int, first_collected: str):
    conn = connect()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT quantity
        FROM player_stickers
        WHERE user_id = ? AND sticker_id = ?
        """,
        (str(user_id), sticker_id)
    )

    row = cur.fetchone()

    if row:
        cur.execute(
            """
            UPDATE player_stickers
            SET quantity = quantity + ?
            WHERE user_id = ? AND sticker_id = ?
            """,
            (amount, str(user_id), sticker_id)
        )
    else:
        cur.execute(
            """
            INSERT INTO player_stickers
            (user_id, sticker_id, quantity, first_collected)
            VALUES (?, ?, ?, ?)
            """,
            (str(user_id), sticker_id, amount, first_collected)
        )

    conn.commit()
    conn.close()


def get_player_stickers(user_id: int):
    conn = connect()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT sticker_id, quantity, first_collected
        FROM player_stickers
        WHERE user_id = ?
        ORDER BY first_collected ASC
        """,
        (str(user_id),)
    )

    rows = cur.fetchall()

    conn.close()

    return rows


def get_player_sticker_quantity(user_id: int, sticker_id: str):
    conn = connect()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT quantity
        FROM player_stickers
        WHERE user_id = ? AND sticker_id = ?
        """,
        (str(user_id), sticker_id)
    )

    row = cur.fetchone()

    conn.close()

    if not row:
        return 0

    return row[0]


def set_featured_sticker(user_id: int, sticker_id: str):
    conn = connect()
    cur = conn.cursor()

    cur.execute(
        "INSERT OR IGNORE INTO players (user_id) VALUES (?)",
        (str(user_id),)
    )

    cur.execute(
        """
        UPDATE players
        SET featured_sticker_id = ?
        WHERE user_id = ?
        """,
        (sticker_id, str(user_id))
    )

    conn.commit()
    conn.close()


def get_featured_sticker(user_id: int):
    conn = connect()
    cur = conn.cursor()

    cur.execute(
        "INSERT OR IGNORE INTO players (user_id) VALUES (?)",
        (str(user_id),)
    )

    cur.execute(
        """
        SELECT featured_sticker_id
        FROM players
        WHERE user_id = ?
        """,
        (str(user_id),)
    )

    row = cur.fetchone()

    conn.commit()
    conn.close()

    if not row or not row[0]:
        return ""

    return row[0]

def get_sticker_pack_setting(pack_id: str):
    conn = connect()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT purchase_enabled, tavern_mix_enabled
        FROM sticker_pack_settings
        WHERE pack_id = ?
        """,
        (pack_id,)
    )

    row = cur.fetchone()

    conn.close()

    return row


def set_sticker_pack_setting(
    pack_id: str,
    purchase_enabled: bool,
    tavern_mix_enabled: bool,
    updated_at: str
):
    conn = connect()
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO sticker_pack_settings
        (pack_id, purchase_enabled, tavern_mix_enabled, updated_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(pack_id) DO UPDATE SET
            purchase_enabled = excluded.purchase_enabled,
            tavern_mix_enabled = excluded.tavern_mix_enabled,
            updated_at = excluded.updated_at
        """,
        (
            pack_id,
            1 if purchase_enabled else 0,
            1 if tavern_mix_enabled else 0,
            updated_at,
        )
    )

    conn.commit()
    conn.close()



def get_tavern_setting(setting_key: str, default_value: str = ""):
    conn = connect()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT setting_value
        FROM tavern_settings
        WHERE setting_key = ?
        """,
        (setting_key,)
    )

    row = cur.fetchone()

    conn.close()

    if not row:
        return default_value

    return row[0]


def set_tavern_setting(setting_key: str, setting_value: str, updated_at: str):
    conn = connect()
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO tavern_settings
        (setting_key, setting_value, updated_at)
        VALUES (?, ?, ?)
        ON CONFLICT(setting_key) DO UPDATE SET
            setting_value = excluded.setting_value,
            updated_at = excluded.updated_at
        """,
        (setting_key, setting_value, updated_at)
    )

    conn.commit()
    conn.close()


def get_math_stats(user_id: int):
    conn = connect()
    cur = conn.cursor()

    cur.execute(
        """
        INSERT OR IGNORE INTO player_math_stats (user_id)
        VALUES (?)
        """,
        (str(user_id),)
    )

    cur.execute(
        """
        SELECT
            games_played,
            daily_games_played,
            correct_answers,
            wrong_answers,
            perfect_rounds,
            medium_perfect_rounds,
            hard_perfect_rounds,
            best_streak,
            fastest_answer_ms,
            last_daily_challenge,
            total_answer_time_ms,
            timed_answer_count,
            total_match_time_ms,
            completed_match_count
        FROM player_math_stats
        WHERE user_id = ?
        """,
        (str(user_id),)
    )

    row = cur.fetchone()
    conn.commit()
    conn.close()

    return row


def get_last_daily_math_challenge(user_id: int):
    stats = get_math_stats(user_id)

    if not stats:
        return ""

    return stats[9] or ""


def record_math_drill_result(
    user_id: int,
    difficulty: str,
    correct: int,
    wrong: int,
    perfect: bool,
    best_streak: int,
    fastest_answer_ms: int,
    is_daily: bool,
    total_answer_time_ms: int = 0,
    timed_answer_count: int = 0,
    match_duration_ms: int = 0,
    challenge_date: str = ""
):
    conn = connect()
    cur = conn.cursor()

    cur.execute(
        """
        INSERT OR IGNORE INTO player_math_stats (user_id)
        VALUES (?)
        """,
        (str(user_id),)
    )

    medium_perfect = 1 if perfect and difficulty == "medium" else 0
    hard_perfect = 1 if perfect and difficulty == "hard" else 0
    perfect_count = 1 if perfect else 0
    daily_count = 1 if is_daily else 0
    daily_date_value = challenge_date if is_daily else None
    fastest_value = int(fastest_answer_ms or 0)
    total_answer_time_value = int(total_answer_time_ms or 0)
    timed_answer_count_value = int(timed_answer_count or 0)
    match_duration_value = int(match_duration_ms or 0)
    match_count_value = 1 if match_duration_value > 0 else 0

    cur.execute(
        """
        UPDATE player_math_stats
        SET
            games_played = games_played + 1,
            daily_games_played = daily_games_played + ?,
            correct_answers = correct_answers + ?,
            wrong_answers = wrong_answers + ?,
            perfect_rounds = perfect_rounds + ?,
            medium_perfect_rounds = medium_perfect_rounds + ?,
            hard_perfect_rounds = hard_perfect_rounds + ?,
            best_streak = MAX(best_streak, ?),
            fastest_answer_ms = CASE
                WHEN ? > 0 AND (fastest_answer_ms = 0 OR ? < fastest_answer_ms) THEN ?
                ELSE fastest_answer_ms
            END,
            last_daily_challenge = CASE
                WHEN ? IS NOT NULL AND ? != '' THEN ?
                ELSE last_daily_challenge
            END,
            total_answer_time_ms = total_answer_time_ms + ?,
            timed_answer_count = timed_answer_count + ?,
            total_match_time_ms = total_match_time_ms + ?,
            completed_match_count = completed_match_count + ?
        WHERE user_id = ?
        """,
        (
            daily_count,
            correct,
            wrong,
            perfect_count,
            medium_perfect,
            hard_perfect,
            best_streak,
            fastest_value,
            fastest_value,
            fastest_value,
            daily_date_value,
            daily_date_value,
            daily_date_value,
            total_answer_time_value,
            timed_answer_count_value,
            match_duration_value,
            match_count_value,
            str(user_id),
        )
    )

    conn.commit()
    conn.close()


# ---------- Daily claim streaks ----------

def _parse_day(value: str):
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def _daily_streak_reward_for_day(streak: int):
    if streak <= 1:
        return 250
    if streak == 2:
        return 275
    return 300


def get_daily_claim_preview(user_id: int, today: str):
    conn = connect()
    cur = conn.cursor()

    cur.execute("INSERT OR IGNORE INTO players (user_id) VALUES (?)", (str(user_id),))
    cur.execute(
        "SELECT balance, last_daily, daily_streak FROM players WHERE user_id = ?",
        (str(user_id),)
    )
    balance, last_daily, current_streak = cur.fetchone()
    conn.commit()
    conn.close()

    if last_daily == today:
        return {
            "can_claim": False,
            "balance": balance,
            "streak": current_streak or 0,
            "base_reward": 0,
            "bonus_pack": False,
        }

    today_date = _parse_day(today)
    last_date = _parse_day(last_daily)

    if today_date and last_date and last_date == today_date - timedelta(days=1):
        next_streak = int(current_streak or 0) + 1
    else:
        next_streak = 1

    return {
        "can_claim": True,
        "balance": balance,
        "streak": next_streak,
        "base_reward": _daily_streak_reward_for_day(next_streak),
        "bonus_pack": next_streak > 0 and next_streak % 7 == 0,
    }


def claim_daily_streak(user_id: int, reward: int, today: str, streak: int):
    conn = connect()
    cur = conn.cursor()

    cur.execute("INSERT OR IGNORE INTO players (user_id) VALUES (?)", (str(user_id),))
    cur.execute(
        "SELECT balance, last_daily, daily_streak FROM players WHERE user_id = ?",
        (str(user_id),)
    )
    balance, last_daily, current_streak = cur.fetchone()

    if last_daily == today:
        conn.close()
        return False, balance, current_streak or 0

    new_balance = balance + reward
    cur.execute(
        "UPDATE players SET balance = ?, last_daily = ?, daily_streak = ? WHERE user_id = ?",
        (new_balance, today, streak, str(user_id))
    )

    conn.commit()
    conn.close()
    return True, new_balance, streak


# ---------- Daily Tavern Tasks ----------

DAILY_TASK_KEYS = ["play_game", "take_shot", "use_mischief", "open_pack", "complete_math"]


def get_daily_tasks(user_id: int, task_date: str):
    conn = connect()
    cur = conn.cursor()

    cur.execute(
        """
        INSERT OR IGNORE INTO player_daily_tasks (user_id, task_date)
        VALUES (?, ?)
        """,
        (str(user_id), task_date)
    )

    cur.execute(
        """
        SELECT play_game, take_shot, use_mischief, open_pack, complete_math, reward_claimed
        FROM player_daily_tasks
        WHERE user_id = ? AND task_date = ?
        """,
        (str(user_id), task_date)
    )
    row = cur.fetchone()

    conn.commit()
    conn.close()

    if not row:
        row = (0, 0, 0, 0, 0, 0)

    return {
        "play_game": bool(row[0]),
        "take_shot": bool(row[1]),
        "use_mischief": bool(row[2]),
        "open_pack": bool(row[3]),
        "complete_math": bool(row[4]),
        "reward_claimed": bool(row[5]),
    }


def mark_daily_task(user_id: int, task_date: str, task_key: str):
    if task_key not in DAILY_TASK_KEYS:
        return get_daily_tasks(user_id, task_date)

    conn = connect()
    cur = conn.cursor()

    cur.execute(
        """
        INSERT OR IGNORE INTO player_daily_tasks (user_id, task_date)
        VALUES (?, ?)
        """,
        (str(user_id), task_date)
    )

    cur.execute(
        f"""
        UPDATE player_daily_tasks
        SET {task_key} = 1
        WHERE user_id = ? AND task_date = ?
        """,
        (str(user_id), task_date)
    )

    conn.commit()
    conn.close()
    return get_daily_tasks(user_id, task_date)


def claim_daily_task_reward_if_ready(user_id: int, task_date: str):
    conn = connect()
    cur = conn.cursor()

    cur.execute(
        """
        INSERT OR IGNORE INTO player_daily_tasks (user_id, task_date)
        VALUES (?, ?)
        """,
        (str(user_id), task_date)
    )

    cur.execute(
        """
        SELECT play_game, take_shot, use_mischief, open_pack, complete_math, reward_claimed
        FROM player_daily_tasks
        WHERE user_id = ? AND task_date = ?
        """,
        (str(user_id), task_date)
    )
    row = cur.fetchone()

    if not row:
        conn.close()
        return False

    all_done = all(bool(value) for value in row[:5])
    reward_claimed = bool(row[5])

    if not all_done or reward_claimed:
        conn.close()
        return False

    cur.execute(
        """
        UPDATE player_daily_tasks
        SET reward_claimed = 1
        WHERE user_id = ? AND task_date = ?
        """,
        (str(user_id), task_date)
    )

    conn.commit()
    conn.close()
    return True


# ---------- Hangman stats ----------

def get_hangman_stats(user_id: int):
    conn = connect()
    cur = conn.cursor()

    cur.execute(
        """
        INSERT OR IGNORE INTO player_hangman_stats (user_id)
        VALUES (?)
        """,
        (str(user_id),)
    )

    cur.execute(
        """
        SELECT games_played, guesser_games, undertaker_games, guesser_wins,
               undertaker_wins, letters_guessed, down_to_wire_wins
        FROM player_hangman_stats
        WHERE user_id = ?
        """,
        (str(user_id),)
    )
    row = cur.fetchone()

    conn.commit()
    conn.close()

    if not row:
        return (0, 0, 0, 0, 0, 0, 0)

    return row


def record_hangman_result(user_id: int, role: str, won: bool, letters_guessed: int = 0, down_to_wire: bool = False):
    conn = connect()
    cur = conn.cursor()

    cur.execute(
        """
        INSERT OR IGNORE INTO player_hangman_stats (user_id)
        VALUES (?)
        """,
        (str(user_id),)
    )

    guesser_game = 1 if role == "guesser" else 0
    undertaker_game = 1 if role == "undertaker" else 0
    guesser_win = 1 if role == "guesser" and won else 0
    undertaker_win = 1 if role == "undertaker" and won else 0
    wire_win = 1 if down_to_wire else 0

    cur.execute(
        """
        UPDATE player_hangman_stats
        SET games_played = games_played + 1,
            guesser_games = guesser_games + ?,
            undertaker_games = undertaker_games + ?,
            guesser_wins = guesser_wins + ?,
            undertaker_wins = undertaker_wins + ?,
            letters_guessed = letters_guessed + ?,
            down_to_wire_wins = down_to_wire_wins + ?
        WHERE user_id = ?
        """,
        (
            guesser_game,
            undertaker_game,
            guesser_win,
            undertaker_win,
            int(letters_guessed or 0),
            wire_win,
            str(user_id),
        )
    )

    conn.commit()
    conn.close()


# ---------- Tip limits and random events ----------

def get_hourly_tip_total(user_id: int, hour_key: str):
    conn = connect()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT total_tipped
        FROM player_tip_limits
        WHERE user_id = ? AND hour_key = ?
        """,
        (str(user_id), hour_key)
    )
    row = cur.fetchone()

    conn.close()
    return row[0] if row else 0


def add_hourly_tip_total(user_id: int, hour_key: str, amount: int):
    conn = connect()
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO player_tip_limits (user_id, hour_key, total_tipped)
        VALUES (?, ?, ?)
        ON CONFLICT(user_id, hour_key) DO UPDATE SET
            total_tipped = total_tipped + excluded.total_tipped
        """,
        (str(user_id), hour_key, int(amount))
    )

    conn.commit()
    conn.close()


def get_all_player_ids():
    conn = connect()
    cur = conn.cursor()

    cur.execute("SELECT user_id FROM players")
    rows = cur.fetchall()

    conn.close()
    return [row[0] for row in rows]
