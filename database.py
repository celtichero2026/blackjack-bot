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
