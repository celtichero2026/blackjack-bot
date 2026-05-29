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
