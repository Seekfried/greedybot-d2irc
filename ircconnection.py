import irc.bot
import time
from chattype import ChatType
from utils import create_logger

logger = create_logger(__name__)

# Based on ircc.py from https://github.com/milandamen/Discord-IRC-Python

class IrcConnector(irc.bot.SingleServerIRCBot):    
    def __init__(self, settings, fbot):
        self.settings = settings
        self.bot = fbot        
        self.running = True
        self.connection = None

        irc.client.ServerConnection.buffer_class.encoding = "utf-8"
        irc.bot.SingleServerIRCBot.__init__(self, [\
            (settings["server"],\
            int(settings["port"]))],\
            settings["nickname"],\
            settings["nickname"])
        
    def __split_text_into_chunks(self, text, max_chunk_size=400):
        # Split the text into words
        words = text.split()
        chunks = []
        current_chunk = ""

        for word in words:
            # Check if adding the next word exceeds the max_chunk_size
            if len(current_chunk) + len(word) + 1 <= max_chunk_size:  
                if current_chunk: 
                    current_chunk += " "
                current_chunk += word
            else:
                # If it exceeds, save the current_chunk and reset
                chunks.append(current_chunk)
                current_chunk = word  

        if current_chunk:
            chunks.append(current_chunk)

        return chunks
    
    def __flood_control(self, message, messagehead = None):
        if isinstance(message, str) and len(message) > 400:
            result = self.__split_text_into_chunks(message)
            for chunk in result:
                if messagehead:
                    self.connection.privmsg(self.settings["channel"], messagehead + chunk)
                else:
                    self.connection.privmsg(self.settings["channel"], chunk)
                time.sleep(0.5)
        else:
            if messagehead:
                self.connection.privmsg(self.settings["channel"], messagehead + message)
            else:
                self.connection.privmsg(self.settings["channel"], message)

    def get_online_users(self):
        return list(self.channels[self.settings["channel"]]._users.keys())

    def send_my_message(self, message, messagehead = None):
        clean_message: str = message.strip()

        if "\n" in clean_message:
            for line in clean_message.splitlines():
                if line.strip() != "":
                    self.__flood_control(line, messagehead)
        else:
            self.__flood_control(clean_message, messagehead)

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
        if self.settings["presence-update"]:
            self.bot.send_all(message=before + " now known as " + after + ".", chattype=ChatType.IRC.value)
    
    def on_kick(self, connection, event):
        if event.arguments[0]:
            self.bot.remove_user_on_exit(event.arguments[0], ChatType.IRC.value)
            if self.settings["presence-update"]:
                self.bot.send_all(message=event.arguments[0] + " got kicked.", chattype=ChatType.IRC.value)

    def on_part(self, connection, event):
        self.bot.remove_user_on_exit(event.source.nick, ChatType.IRC.value)
        if self.settings["presence-update"]:
            self.bot.send_all(message=event.source.nick + " left.", chattype=ChatType.IRC.value)
            

    def on_quit(self, connection, event):
        self.bot.remove_user_on_exit(event.source.nick, ChatType.IRC.value)
        if self.settings["presence-update"]:            
            self.bot.send_all(message=event.source.nick + " left.", chattype=ChatType.IRC.value)
    
    def on_nicknameinuse(self, connection, event):
        connection.nick(connection.get_nickname() + "y")

    def on_currenttopic(self, connection, event):
        self.bot.topic = event.arguments[1]

    def on_notopic(self, connection, event):
        self.bot.topic = event.arguments[1]
    
    def on_topic(self, connection, event):
        if event.arguments[0].find("Pickups: ") == -1:
            self.bot.topic = event.arguments[0]

    def on_welcome(self, connection, event):
        self.connection = connection
        channel = self.settings["channel"]
        self.connection.privmsg("Q@CServe.quakenet.org", "AUTH " + self.settings["nickname"] + " " + self.settings["password"] )
        connection.join(channel)
        
        logger.info("[IRC] Connected to server")
    
    def on_join(self, connection, event):
        if event.source.nick != connection.get_nickname() and self.settings["presence-update"]:
            self.bot.send_all(message=event.source.nick + " joined.", chattype=ChatType.IRC.value)
        else:
            logger.info("[IRC] Connected to channel")
    
    def on_pubmsg(self, connection, event):
        message = event.arguments[0].strip()
        author = event.source.nick
        #author = re.sub(r"(]|-|\\|[`*_{}[()#+.!])", r'\\\1', event.source.nick)

        should_bridge = True
        
        if author in self.bot.muted_irc_users:
            should_bridge = False

        logger.info("[IRC] " + "{:s} : {:s}".format(author,message))
        
        if event.source.nick == self.settings["botowner"]:
            if event.arguments[0].strip() == "!quit":
                #self.bot.discordconnect.close()
                self.bot.close()
                return

        if message.startswith('!'):
            if should_bridge:
                self.bot.send_all(message="<"+ author + "> " + message, chattype=ChatType.IRC.value)
            if self.channels[event.target].is_oper(author):
                self.bot.send_command(author, message, ChatType.IRC.value, True)
            else:
                self.bot.send_command(author, message, ChatType.IRC.value, False)            
        elif should_bridge:
            self.bot.send_all(message="<"+ author + "> " + message, chattype=ChatType.IRC.value, discordmention=True)
    
    def run(self):
        self.start()
        
        if self.running:
            self.running = False
            ircc = IrcConnector(self.settings, self.bot)
            self.bot.ircconnect = ircc
            ircc.run()