import asyncio
import time
from chattype import ChatType
from nio import AsyncClient, MatrixRoom, RoomMessageText, LoginResponse
from utils import create_logger

logger = create_logger(__name__)

class MatrixConnector:

    def __init__(self, settings: dict, bot):
        self.settings = settings
        self.bot = bot
        self.server = settings["server"]
        self.botname = settings["botname"]
        self.password = settings["password"]        
        self.room = settings["room"]

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
                # Process the new message
                logger.info(f"New message in {room.display_name} : {event.body}")
                self.bot.send_all(message=event.body, chattype=ChatType.MATRIX.value, messagehead="<"+ event.sender + "> ", discordmention=True)
    
    async def send_my_message_async(self,message):
        await self.client.room_send(
            room_id=self.room,
            message_type="m.room.message",
            content={"msgtype": "m.text", "body": message})
    
    def send_my_message(self,message):
        asyncio.run_coroutine_threadsafe(self.send_my_message_async(message), self.loop)

