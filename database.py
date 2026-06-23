import sqlite3

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
        SELECT user_id, balance, wins, losses, games_played
        FROM players
        ORDER BY balance DESC
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
