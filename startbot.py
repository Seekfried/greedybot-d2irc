from friedybot import FriedyBot
import json

# Get the bot settings from settings.json
f = open("settings.json", encoding="utf-8")
settings = json.loads(f.read())
f.close()

# Get the bot messagetexts from cmdresults.json
f = open("cmdresults.json", encoding="utf-8")
cmdresults = json.loads(f.read())
f.close()

# Get the bot killtexts from xonotic.json
f = open("xonotic.json", encoding="utf-8")
xonotic = json.loads(f.read())
f.close()

bot = FriedyBot(settings, cmdresults, xonotic)
bot.run()