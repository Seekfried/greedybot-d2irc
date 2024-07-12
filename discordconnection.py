import logging
import discord
import asyncio

# Based on discordc.py from https://github.com/milandamen/Discord-IRC-Python

logging.basicConfig(level=logging.INFO)

thread_lock = None

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
    def __init__(self, sett, lock, fbot):
        global settings
        global thread_lock
        global bot
        
        settings = sett
        thread_lock = lock
        bot = fbot
        
        if not settings["token"]:
            with thread_lock:
                print("[Discord] No token given. Get a token at https://discordapp.com/developers/applications/me")
            exit()
    
    def send_my_message(self, message):
        global client
        asyncio.run_coroutine_threadsafe(send_my_message_async(message), client.loop)

    def send_my_file(self, path):
        global client
        asyncio.run_coroutine_threadsafe(send_my_file_async(path), client.loop)

    def get_online_members(self):
        online_members =[]
        for user in channel.guild.members:
            if str(user.status) != "offline":
                online_members.append(user.display_name)
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
    await channel.send(message.strip())

async def send_my_file_async(path):
    await channel.send(file=discord.File(path))
    
@client.event
async def on_message(message):
    global settings
    global client
    global channel
    global thread_lock
    global bot
    
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

    with thread_lock:
        print("[Discord] %s: %s" % (message.author.name, message.content.strip()))
    
    content = message.clean_content
    bot.ircconnect.send_my_message("%s: %s" % (message.author.name, content))

    if message.content.startswith('!'):
        if settings["modrole"] in [y.name.lower() for y in message.author.roles]:
            bot.send_command(message.author, message.content, "discord", True)
        else:
            bot.send_command(message.author, message.content, "discord", False)

@client.event
async def on_presence_update(before, after):
    pass #todo delete pickup if going offline
    # await channel.send(f"""{after}'s activity changed from {before.status} to {after.status}""")
    # bot.ircconnect.send_my_message(f"""{after}'s activity changed from {before.status} to {after.status}""")

@client.event
async def on_ready():
    global server
    global channel
    global thread_lock
    
    with thread_lock:
        print("[Discord] Logged in as:")
        print("[Discord] " + client.user.name)
        print("[Discord] " + str(client.user.id))
        
        if len(client.guilds) == 0:
            print("[Discord] Bot is not yet in any server.")
            await client.close()
            return
        
        if settings["server"] == "":
            print("[Discord] You have not configured a server to use in settings.json")
            print("[Discord] Please put one of the server IDs listed below in settings.json")
            
            for server in client.guilds:
                print("[Discord] %s: %s" % (server.name, server.id))
            
            await client.close()
            return
        
        findServer = [x for x in client.guilds if str(x.id) == settings["server"]]
        if not len(findServer):
            print("[Discord] No server could be found with the specified id: " + settings["server"])
            print("[Discord] Available servers:")
            
            for server in client.guilds:
                print("[Discord] %s: %s" % (server.name, server.id))
                
            await client.close()
            return
        
        server = findServer[0]
        
        if settings["channel"] == "":
            print("[Discord] You have not configured a channel to use in settings.json")
            print("[Discord] Please put one of the channel IDs listed below in settings.json")
            
            for channel in server.channels:
                if channel.type == discord.ChannelType.text:
                    print("[Discord] %s: %s" % (channel.name, channel.id))
            
            await client.close()
            return
        
        findChannel = [x for x in server.channels if str(x.id) == settings["channel"] and x.type == discord.ChannelType.text]
        if not len(findChannel):
            print("[Discord] No channel could be found with the specified id: " + settings["server"])
            print("[Discord] Note that you can only use text channels.")
            print("[Discord] Available channels:")
            
            for channel in server.channels:
                if channel.type == discord.ChannelType.text:
                    print("[Discord] %s: %s" % (channel.name, channel.id))
            
            await client.close()
            return
        
        channel = findChannel[0]
