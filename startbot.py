from greedybot import Greedybot
import asyncio
import json
import yaml
from utils import create_logger

logger = create_logger("startbot")

# Get the bot settings from settings.yaml
logger.info("Loading settings")
with open('settings.yaml','r', encoding="utf-8") as f:
    settings = yaml.safe_load(f)

# Get the bot messagetexts from cmdresults.json
logger.info("Loading cmdresults.json")
f = open("cmdresults.json", encoding="utf-8")
cmdresults = json.loads(f.read())
f.close()

# Get the bot killtexts from xonotic.json
logger.info("Loading xonotic.json")
f = open("xonotic.json", encoding="utf-8")
xonotic = json.loads(f.read())
f.close()

bot = Greedybot(settings, cmdresults, xonotic)
try:
    logger.info("Starting bot")
    asyncio.run(bot.run())
except asyncio.exceptions.CancelledError:
    logger.info("Bot cancelled by user")
      