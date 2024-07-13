import irc.bot
import re

# Based on ircc.py from https://github.com/milandamen/Discord-IRC-Python


class IrcConnector(irc.bot.SingleServerIRCBot):    
    def __init__(self, settings, lock, fbot):
        self.settings = settings
        self.thread_lock = lock
        self.bot = fbot        
        self.running = True
        self.connection = None

        irc.client.ServerConnection.buffer_class.encoding = "utf-8"
        irc.bot.SingleServerIRCBot.__init__(self, [\
            (settings["server"],\
            int(settings["port"]))],\
            settings["nickname"],\
            settings["nickname"])
       
    def send_my_message(self, message):
        self.connection.privmsg(self.settings["channel"], message.strip())

    def send_single_message(self, user, message):
        self.connection.notice(user, message)
        
    def close(self):
        self.running = False
        self.connection.quit(self.settings.get("quitmsg"))
    
    def set_running(self, value):
        self.running = False

    def on_nick(self, connection, event):
            before = event.source.nick
            after = event.target
            self.bot.change_name(before, after)

    def on_part(self, connection, event):
        self.bot.remove_user_on_exit(event.source.nick, "irc")

    def on_quit(self, connection, event):
        self.bot.remove_user_on_exit(event.source.nick, "irc")
    
    def on_nicknameinuse(self, connection, event):
        connection.nick(connection.get_nickname() + "y")
    
    def on_welcome(self, connection, event):
        self.connection = connection
        channel = self.settings["channel"]
        
        connection.join(channel)
        
        with self.thread_lock:
            print("[IRC] Connected to server")
    
    def on_join(self, connection, event):
        with self.thread_lock:
            print("[IRC] Connected to channel")
    
    def on_pubmsg(self, connection, event):
        message = event.arguments[0].strip()
        author = event.source.nick
        #author = re.sub(r"(]|-|\\|[`*_{}[()#+.!])", r'\\\1', event.source.nick)

        with self.thread_lock:
            print("[IRC] " + "{:s} : {:s}".format(author,message))
        
        if event.source.nick == self.settings["botowner"]:
            if event.arguments[0].strip() == "!quit":
                self.bot.discordconnect.close()
                return

        self.bot.discordconnect.send_my_message("<"+ author + "> " + message)

        if message.startswith('!'):
            if self.channels[event.target].is_oper(author):
                self.bot.send_command(author, message, "irc", True)
            else:
                self.bot.send_command(author, message, "irc", False)
    
    def run(self):
        self.start()
        
        if self.running:
            self.running = False
            ircc = IrcConnector(self.settings, self.thread_lock, self.bot)
            self.bot.ircconnect = ircc
            ircc.run()