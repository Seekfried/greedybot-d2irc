from greedybot import Greedybot
import json
import yaml

# Get the bot settings from settings.yaml
with open('settings.yaml','r', encoding="utf-8") as f:
        settings = yaml.safe_load(f)

# Get the bot messagetexts from cmdresults.json
f = open("cmdresults.json", encoding="utf-8")
cmdresults = json.loads(f.read())
f.close()

# Get the bot killtexts from xonotic.json
f = open("xonotic.json", encoding="utf-8")
xonotic = json.loads(f.read())
f.close()

bot = Greedybot(settings, cmdresults, xonotic)
bot.run()