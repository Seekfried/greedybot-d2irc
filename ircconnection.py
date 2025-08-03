import irc.bot
import time
import asyncio
import threading
from collections import deque
from chattype import ChatType
from utils import create_logger
from flood_control_config import get_flood_control_config

logger = create_logger(__name__)

# Based on ircc.py from https://github.com/milandamen/Discord-IRC-Python

class IrcConnector(irc.bot.SingleServerIRCBot):    
    def __init__(self, settings, fbot):
        self.settings = settings
        self.bot = fbot        
        self.running = True
        self.connection = None
        
        # Load flood control configuration
        flood_profile = settings.get("flood_control_profile", "default")
        flood_config = get_flood_control_config(flood_profile)
        
        # Flood control settings
        self.message_queue = deque()
        self.queue_lock = threading.Lock()
        self.last_message_time = 0
        self.message_interval = flood_config["message_interval"]
        self.burst_limit = flood_config["burst_limit"]
        self.burst_window = flood_config["burst_window"]
        self.min_message_delay = flood_config["min_message_delay"]
        self.chunk_delay = flood_config["chunk_delay"]
        self.burst_count = 0
        self.burst_reset_time = 0
        self.queue_processor_running = False
        
        logger.info(f"[IRC] Using flood control profile: {flood_profile}")
        logger.info(f"[IRC] Flood control settings: interval={self.message_interval}s, burst_limit={self.burst_limit}, window={self.burst_window}s")

        irc.client.ServerConnection.buffer_class.encoding = "utf-8"
        irc.client.ServerConnection.buffer_class.errors = "replace"        
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
    
    def __queue_message(self, message, messagehead=None, is_notice=False, target=None):
        """Queue a message for rate-limited sending"""
        with self.queue_lock:
            message_data = {
                'message': message,
                'messagehead': messagehead,
                'is_notice': is_notice,
                'target': target,
                'timestamp': time.time()
            }
            self.message_queue.append(message_data)
            
            # Start queue processor if not running
            if not self.queue_processor_running:
                self.queue_processor_running = True
                processor_thread = threading.Thread(target=self.__process_message_queue, daemon=True)
                processor_thread.start()

    def __process_message_queue(self):
        """Process queued messages with rate limiting"""
        while self.running:
            try:
                with self.queue_lock:
                    if not self.message_queue:
                        self.queue_processor_running = False
                        break
                    
                    message_data = self.message_queue.popleft()
                
                current_time = time.time()
                
                # Reset burst counter if window has passed
                if current_time - self.burst_reset_time > self.burst_window:
                    self.burst_count = 0
                    self.burst_reset_time = current_time
                
                # Calculate delay needed
                time_since_last = current_time - self.last_message_time
                delay_needed = 0
                
                if self.burst_count >= self.burst_limit:
                    # We've hit burst limit, enforce minimum interval
                    if time_since_last < self.message_interval:
                        delay_needed = self.message_interval - time_since_last
                elif time_since_last < self.min_message_delay:
                    delay_needed = self.min_message_delay - time_since_last
                
                if delay_needed > 0:
                    time.sleep(delay_needed)
                
                # Send the message
                self.__send_message_now(message_data)
                
                # Update counters
                self.last_message_time = time.time()
                self.burst_count += 1
                
            except Exception as e:
                logger.error(f"Error in message queue processor: {e}")
                time.sleep(1)  # Prevent tight error loops

    def __send_message_now(self, message_data):
        """Actually send the message to IRC"""
        if not self.connection:
            return
            
        message = message_data['message']
        messagehead = message_data['messagehead']
        is_notice = message_data['is_notice']
        target = message_data['target']
        
        try:
            if is_notice and target:
                # Direct notice to user
                self.connection.notice(target, message)
            else:
                # Channel message
                if isinstance(message, str) and len(message) > 400:
                    # Split long messages
                    chunks = self.__split_text_into_chunks(message)
                    for i, chunk in enumerate(chunks):
                        if i > 0:  # Add delay between chunks
                            time.sleep(self.chunk_delay)
                        
                        final_message = (messagehead + chunk) if messagehead else chunk
                        self.connection.privmsg(self.settings["channel"], final_message)
                else:
                    final_message = (messagehead + message) if messagehead else message
                    self.connection.privmsg(self.settings["channel"], final_message)
                    
        except Exception as e:
            logger.error(f"Error sending IRC message: {e}")

    def __flood_control(self, message, messagehead=None):
        """Legacy method - now queues messages instead of sending directly"""
        self.__queue_message(message, messagehead)

    def get_online_users(self):
        online_users = list(self.channels[self.settings["channel"]]._users.keys())
        online_users.sort()
        return online_users

    def send_my_message(self, message, messagehead = None):
        clean_message: str = message.strip()

        if "\n" in clean_message:
            for line in clean_message.splitlines():
                if line.strip() != "":
                    self.__flood_control(line, messagehead)
        else:
            self.__flood_control(clean_message, messagehead)

    def send_single_message(self, user, message):
        """Send a notice to a specific user with rate limiting"""
        self.__queue_message(message, is_notice=True, target=user)
        
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
            if self.settings["remove-offline"]:
                self.bot.remove_user_on_exit(event.arguments[0], ChatType.IRC.value)
            if self.settings["presence-update"]:
                self.bot.send_all(message=event.arguments[0] + " got kicked.", chattype=ChatType.IRC.value)

    def on_part(self, connection, event):
        if self.settings["remove-offline"]:
            self.bot.remove_user_on_exit(event.source.nick, ChatType.IRC.value)
        if self.settings["presence-update"]:
            self.bot.send_all(message=event.source.nick + " left.", chattype=ChatType.IRC.value)
            
    def on_quit(self, connection, event):
        if self.settings["remove-offline"]:
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
                self.bot.send_all(message=message, chattype=ChatType.IRC.value, messagehead="<"+ author + "> ")
            if self.channels[event.target].is_oper(author):
                self.bot.send_command(author, message, ChatType.IRC.value, True)
            else:
                self.bot.send_command(author, message, ChatType.IRC.value, False)            
        elif should_bridge:
            self.bot.send_all(message=message, chattype=ChatType.IRC.value, discordmention=True, messagehead="<"+ author + "> ")
    
    def run(self):
        self.start()
        
        if self.running:
            self.running = False
            ircc = IrcConnector(self.settings, self.bot)
            self.bot.ircconnect = ircc
            ircc.run()
