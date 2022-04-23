import os

from aiohttp import BasicAuth
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# Core
TOKEN = os.environ["TOKEN"]
PREFIX = os.getenv("PREFIX", "p!")
DEV_MODE = os.getenv("DEV_MODE", "False").lower() != "false"

# Proxy
PROXY = None
PROXY_AUTH = None
proxy_str = os.getenv("PROXY")
if proxy_str:
    proxy_parts = proxy_str.split("@")
    PROXY = proxy_parts[0]
    if len(proxy_parts) == 2:
        username, password = proxy_parts[1].split(":")
        PROXY_AUTH = BasicAuth(username, password)

# Database
DATABASE_URL = os.environ["DATABASE_URL"]

# Bot
SELL_WAIFU_DEPRECIATION = float(os.getenv("SELL_WAIFU_DEPRECIATION", "0.6"))
FREE_MONEY_SPAWN_LIMIT = int(os.getenv("FREE_MONEY_SPAWN_LIMIT", "85"))
DAILIES_AMOUNT = int(os.getenv("DAILIES_AMOUNT", "300"))
HOURLIES_AMOUNT = int(os.getenv("HOURLIES_AMOUNT", "150"))
VOTE_REWARD = int(os.getenv("VOTE_REWARD", "500"))
DAILIES_DATE = os.getenv("DAILIES_DATE")
DONATOR_TIER_1 = int(os.getenv("DONATOR_TIER_1", "1"))
DONATOR_TIER_2 = int(os.getenv("DONATOR_TIER_2", "2"))
DEV_TIER = int(os.getenv("DEV_TIER", "5"))
ROLL_INTERVAL = int(os.getenv("ROLL_INTERVAL", "10800"))  # seconds
PRICE_CUT = float(os.getenv("PRICE_CUT", "0.08"))

# Music
MUSIC_CACHE_DIR = os.getenv("MUSIC_CACHE_DIR", "./cache/")

# APIs
DBL_TOKEN = os.getenv("DBL_TOKEN")  # None to disable.
NOFLYLIST_TOKEN = os.getenv("NOFLYLIST_TOKEN")  # None to disable.
TRACE_MOE_TOKEN = os.getenv("TRACE_MOE_TOKEN")  # None to disable.
TENOR_API_TOKEN = os.getenv("TENOR_API_TOKEN")
DISCOIN_TOKEN = os.getenv("DISCOIN_TOKEN")  # None to disable.
DISCOIN_SELF_CURRENCY = os.getenv("DISCOIN_SELF_CURRENCY", "PIC")

# Build-time config
# Load build config from build.env
load_dotenv("./build.env")

GIT_SHA = os.getenv("GIT_SHA", "00000000")
BUILD_DATE = os.getenv("BUILD_DATE", "0000-00-00T00:00:00+0000")
BUILD_VERSION = os.getenv("BUILD_VERSION", "dev")
