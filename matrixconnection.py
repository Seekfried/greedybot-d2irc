import asyncio
import time
from chattype import ChatType
from nio import AsyncClient, MatrixRoom, RoomMessageText, LoginResponse
from utils import create_logger
import re

logger = create_logger(__name__)

class MatrixConnector:

    def __init__(self, settings: dict, bot):
        self.settings = settings
        self.bot = bot
        self.server = settings["server"]
        self.botname = settings["botname"]
        self.password = settings["password"]        
        self.room = settings["room"]


    def __replace_tags(self, text):
        # Step 1: Use regex to find all font tags and temporarily replace them with placeholders
        placeholders = []
        def replace_font_tag(match):
            placeholders.append(match.group(0))
            return f'__FONT_TAG_{len(placeholders) - 1}__'
        
        text = re.sub(r'<font[^>]*>.*?</font>', replace_font_tag, text, flags=re.DOTALL)
        
        # Step 2: Escape all remaining < and > with &lt; and &gt;
        text = re.sub(r'<', '&lt;', text)
        text = re.sub(r'>', '&gt;', text)
        
        # Step 3: Restore the font tags from placeholders
        def restore_font_tag(match):
            index = int(match.group(1))
            return placeholders[index]
        
        text = re.sub(r'__FONT_TAG_(\d+)__', restore_font_tag, text)
        
        return text

    async def start(self) -> None:
        self.client: AsyncClient = AsyncClient(self.server, self.botname)
        self.client.add_event_callback(self.message_callback, RoomMessageText)
        try:
            self.loop = asyncio.get_event_loop()
        except RuntimeError:
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
        
        response = await self.client.login(self.password)
        
        if isinstance(response, LoginResponse):
            logger.info("Matrix log in successfully")
            # Set the start time as the current time
            self.start_time = time.time()
            
            # Start listening for messages
            await self.client.sync_forever(timeout=30000)
        else:
            logger.info("Failed to log in:", response)
    
    async def message_callback(self, room: MatrixRoom, event: RoomMessageText) -> None:
        logger.info(f"Message received in {room.display_name} : {event.sender} : {event.body}")
        if event.sender == self.botname:
            return
        # Check if the event is a message (e.g., text message)
        if isinstance(event, RoomMessageText) and room.room_id == self.room:
            # Get the timestamp of the event
            event_timestamp = event.server_timestamp / 1000
            
            # Compare the event timestamp with the start time
            if event_timestamp > self.start_time:
                logger.info(f"New message in {room.display_name} : {event.body}")
                await self.__process_message(room, event)
    
    async def __process_message(self, room: MatrixRoom, event: RoomMessageText) -> None:
        logger.info(f"Process message. room: {room.display_name} message: <{event.sender}> {event.body}")

        # TODO: Implement muted users feature in matrix
        should_bridge = True

        if event.sender in self.bot.muted_matrix_users:
            should_bridge = False

        if should_bridge:
            logger.info(f"New message in {room.display_name} : {event.body}")
            self.bot.send_all(message=event.body, chattype=ChatType.MATRIX.value, messagehead="<"+ event.sender + "> ", discordmention=True)
            
        # criteria for admin: if the user can kick in the room
        isAdmin = room.power_levels.can_user_kick(event.sender)
        if event.body.startswith("!"):
            self.bot.send_command(event.sender, event.body, ChatType.MATRIX.value, isAdmin)

    async def send_my_message_async(self,message, html):
        if html:
            formatted_message = self.__replace_tags(message)
            await self.client.room_send(
                room_id=self.room,
                message_type="m.room.message",
                content={"msgtype": "m.text", "body": formatted_message, "format": "org.matrix.custom.html", "formatted_body": formatted_message})
        else:
            await self.client.room_send(
                room_id=self.room,
                message_type="m.room.message",
                content={"msgtype": "m.text", "body": message})

    def send_my_message(self, message, html=False):
        asyncio.run_coroutine_threadsafe(self.send_my_message_async(message, html), self.loop)

