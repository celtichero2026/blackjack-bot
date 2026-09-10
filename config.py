import os

# Existing default so your current server keeps working even before you
# change Railway variables.
DEFAULT_GUILD_ID = 1415053350482739222
DEFAULT_TAVERN_CHANNEL_ID = 1509796381756227756


def _parse_id_list(value):
    """Turn a comma-separated Railway variable into a set of Discord IDs."""
    ids = set()
    for part in (value or "").split(","):
        part = part.strip()
        if not part:
            continue
        try:
            ids.add(int(part))
        except ValueError:
            print(f"WARNING: Ignoring invalid Discord ID in configuration: {part!r}")
    return ids


# Kept for backward compatibility. The bot is not restricted to one guild.
GUILD_ID = int(os.getenv("GUILD_ID", str(DEFAULT_GUILD_ID)))

# Multi-server Tavern channels. Example:
# TAVERN_CHANNEL_IDS=111111111111111111,222222222222222222
#
# If the plural variable is absent, the old singular variable still works.
TAVERN_CHANNEL_IDS = _parse_id_list(os.getenv("TAVERN_CHANNEL_IDS", ""))
if not TAVERN_CHANNEL_IDS:
    TAVERN_CHANNEL_IDS = _parse_id_list(
        os.getenv("TAVERN_CHANNEL_ID", str(DEFAULT_TAVERN_CHANNEL_ID))
    )

# Backward-compatible singular value for any old code that still imports it.
TAVERN_CHANNEL_ID = next(iter(TAVERN_CHANNEL_IDS))

STARTING_BALANCE = 1000
DAILY_REWARD = 250
MIN_BET = 50
MAX_BET = 500
