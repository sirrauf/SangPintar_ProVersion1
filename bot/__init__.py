import os
import logging
from telegram import Bot

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("SangPintar")

BOT_TOKEN = os.getenv("TOKEN_BOT_TELEGRAM", "")
BOT_VERSION = "1.0.0.0 Pro Version"
BOT_NAME = "SangPintar"
COMPANY_NAME = "PT Ananda Technology Solution"
BOT_UPDATE_LINK = "https://t.me/@sangpintar_antsgroupsbot"

OPENCLAW_HOST = os.getenv("OPENCLAW_HOST", "http://localhost:18789")
OLLAMA_HOST = os.getenv("OLAMA_HOST", os.getenv("OLLAMA_HOST", "http://localhost:11434"))

