import json
import os
from dotenv import load_dotenv

# Refactor: settings/config centralized; behavior unchanged
load_dotenv()

CONFIG_FILE = os.getenv("CONFIG_FILE", "config.json")

# Discord roles and channel IDs
ALERT_CHANNEL_ID = int(os.getenv("ALERT_CHANNEL_ID", "1378740342953742417"))
ROLE_MASTER_MENTION = os.getenv("ROLE_MASTER_MENTION", "<@&1376452625972727808>")
ROLE_ORGANIZER_MENTION = os.getenv("ROLE_ORGANIZER_MENTION", "<@&1205565991162089553>")

MEMBER_ROLE_NAME = os.getenv("MEMBER_ROLE_NAME")
GUEST_ROLE_NAME = os.getenv("GUEST_ROLE_NAME")


def load_config() -> dict:
    try:
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def update_config(key: str, value: str) -> None:
    config = load_config()
    config[key] = value
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=4)
