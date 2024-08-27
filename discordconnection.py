import logging
import discord
import asyncio
from utils import create_logger
from xonotic.utils import strip_irc_colors

# Based on discordc.py from https://github.com/milandamen/Discord-IRC-Python

#logging.basicConfig(level=logging.INFO)
logger = create_logger("discordconnection", logging.INFO)

settings = None
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True
intents.presences = True

client = discord.Client(intents=intents)
server = None
channel = None
bot = None

class DiscordConnector:
    def __init__(self, sett, fbot):
        global settings
        global bot
        
        settings = sett
        bot = fbot
        
        if not settings["token"]:
            logger.error("[Discord] No token given. Get a token at https://discordapp.com/developers/applications/me")
            exit()
    
    def send_my_message(self, message):
        global client
        asyncio.run_coroutine_threadsafe(send_my_message_async(message), client.loop)

    def send_my_message_with_mention(self, message):
        global client
        for user in channel.guild.members:
            if message.find('@' + user.name) != -1:
                message = message.replace('@' + user.name, user.mention)
        asyncio.run_coroutine_threadsafe(send_my_message_async(message), client.loop)

    def send_my_file(self, path):
        global client
        asyncio.run_coroutine_threadsafe(send_my_file_async(path), client.loop)

    def send_promote_message(self, message, gametype):
        global client
        role_name:str = "player_" + gametype
        role = discord.utils.get(channel.guild.roles, name=role_name)
        if role:
            message = role.mention + " " + (message)
            asyncio.run_coroutine_threadsafe(send_my_message_async(message), client.loop)

    def give_role(self, username, gametype):
        global client
        user = discord.utils.get(channel.guild.members, name=username)
        rolename = "player_" + gametype
        asyncio.run_coroutine_threadsafe(give_role_async(user, rolename), client.loop)        

    def take_role(self, username, gametype):
        global client
        user = discord.utils.get(channel.guild.members, name=username)
        rolename = "player_" + gametype
        asyncio.run_coroutine_threadsafe(take_role_async(user, rolename), client.loop)  

    def get_online_members(self):
        online_members =[]
        for user in channel.guild.members:
            if str(user.status) != "offline":
                online_members.append(user.name)
        return online_members
    
    def run(self):
        global settings
        global client
        
        client.run(settings["token"])
    
    def close(self):
        global client
        global bot
        bot.ircconnect.set_running(False)
        asyncio.run_coroutine_threadsafe(client.close(), client.loop)

async def send_my_message_async(message):
    colorless_message = strip_irc_colors(message)
    await channel.send(colorless_message.strip())

async def send_my_file_async(path):
    await channel.send(file=discord.File(path))

async def give_role_async(user, rolename):
    role = discord.utils.get(channel.guild.roles, name=rolename)
    if role:
        await user.add_roles(role)
    else:
        try:
            await channel.guild.create_role(name=rolename)
            role = discord.utils.get(channel.guild.roles, name=rolename)
            await user.add_roles(role)
        except Exception as e:
            logger.error("Error in give_role_async: ", e)

async def take_role_async(user, rolename):
    role = discord.utils.get(channel.guild.roles, name=rolename)
    if role:
        await user.remove_roles(role)
    
@client.event
async def on_message(message):
    global settings
    global client
    global channel
    global bot
    
    should_bridge = True
        
    if message.author.name in bot.muted_discord_users:
        should_bridge = False

    # Don't reply to itself, except cup pictures
    if message.author == client.user:
        if len(message.attachments) > 0:
            bot.ircconnect.send_my_message('Cup: ' + message.attachments[0].url)
        return
    
    if message.channel != channel:
        return

    if message.author.name == settings["botowner"]:
        if message.content.strip() == "!quit":
            await client.close()
            return

    logger.info("[Discord] %s: %s" % (message.author.name, message.content.strip()))
    
    if should_bridge:
        content = message.clean_content
        bot.ircconnect.send_my_message("<%s> %s" % (message.author.name, content))
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        asyncio.run_coroutine_threadsafe(
            bot.matrixconnect.send_my_message("<" + author + "> " + message), loop
        )

        for attachment in message.attachments:
            bot.ircconnect.send_my_message("URL: " + attachment.url)
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            asyncio.run_coroutine_threadsafe(
                bot.matrixconnect.send_my_message("<" + author + "> " + message), loop
            )

    if message.content.startswith('!'):
        if settings["modrole"] in [y.name.lower() for y in message.author.roles]:
            bot.send_command(message.author, message.content, "discord", True)
        else:
            bot.send_command(message.author, message.content, "discord", False)

@client.event
async def on_presence_update(before, after):
    if after.status.name == "offline":
        bot.remove_user_on_exit(after, "discord")
    #pass #todo delete pickup if going offline
    # await channel.send(f"""{after}'s activity changed from {before.status} to {after.status}""")
    # bot.ircconnect.send_my_message(f"""{after}'s activity changed from {before.status} to {after.status}""")

@client.event
async def on_ready():
    global server
    global channel
    

    logger.info("[Discord] Logged in as:")
    logger.info("[Discord] " + client.user.name)
    logger.info("[Discord] " + str(client.user.id))
    
    if len(client.guilds) == 0:
        logger.warning("[Discord] Bot is not yet in any server.")
        await client.close()
        return
    
    if settings["server"] == "":
        logger.error("[Discord] You have not configured a server to use in settings.json")
        logger.error("[Discord] Please put one of the server IDs listed below in settings.json")
        
        for server in client.guilds:
            logger.info("[Discord] %s: %s" % (server.name, server.id))
        
        await client.close()
        return
    
    findServer = [x for x in client.guilds if str(x.id) == settings["server"]]
    if not len(findServer):
        logger.error("[Discord] No server could be found with the specified id: " + settings["server"])
        logger.error("[Discord] Available servers:")
        
        for server in client.guilds:
            logger.error("[Discord] %s: %s" % (server.name, server.id))
            
        await client.close()
        return
    
    server = findServer[0]
    
    if settings["channel"] == "":
        logger.error("[Discord] You have not configured a channel to use in settings.json")
        logger.error("[Discord] Please put one of the channel IDs listed below in settings.json")
        
        for channel in server.channels:
            if channel.type == discord.ChannelType.text:
                logger.error("[Discord] %s: %s" % (channel.name, channel.id))
        
        await client.close()
        return
    
    findChannel = [x for x in server.channels if str(x.id) == settings["channel"] and x.type == discord.ChannelType.text]
    if not len(findChannel):
        logger.error("[Discord] No channel could be found with the specified id: " + settings["server"])
        logger.error("[Discord] Note that you can only use text channels.")
        logger.error("[Discord] Available channels:")
        
        for channel in server.channels:
            if channel.type == discord.ChannelType.text:
                logger.error("[Discord] %s: %s" % (channel.name, channel.id))
        
        await client.close()
        return
    
    channel = findChannel[0]
