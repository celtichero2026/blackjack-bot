import sqlite3

DB_NAME = "casino.db"


def connect():
    return sqlite3.connect(DB_NAME)


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

