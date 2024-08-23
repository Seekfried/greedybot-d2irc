import logging
import asyncio
import time
from nio import AsyncClient, MatrixRoom, RoomMessageText, LoginResponse
from utils import create_logger

logger = create_logger("discordconnection", logging.INFO)

class MatrixConnector:
    def __init__(self, settings: dict, bot):
        self.client = AsyncClient(settings["server"], settings["botname"])
        self.password = settings["password"]
        self.room = settings["room"]
        self.bot = bot

    # def run(self, loop):
    #     #asyncio.run(self.start())
    #     coro = self.start()
    #     future = asyncio.run_coroutine_threadsafe(coro, loop)
    #     return future

    async def start(self):
        response = await self.client.login(self.password)
        self.client.add_event_callback(self.message_callback, RoomMessageText)
        if isinstance(response, LoginResponse):
            logger.info("Matrix log in successfully")
            # Set the start time as the current time
            self.start_time = time.time()
            
            # Start listening for messages
            await self.client.sync_forever(timeout=30000)
        else:
            logger.info("Failed to log in:", response)
    
    async def message_callback(self, room: MatrixRoom, event: RoomMessageText) -> None:
        # Check if the event is a message (e.g., text message)
        if isinstance(event, RoomMessageText):
            # Get the timestamp of the event
            event_timestamp = event.server_timestamp / 1000
            
            # Compare the event timestamp with the start time
            if event_timestamp > self.start_time:
                # Process the new message
                logger.info("New message in", room.display_name, ":", event.body)
                self.bot.send_all("<"+ room.user_name(event.sender) + "> " + event.body)
    
    async def send_my_message(self,message):
        await self.client.room_send(
             room_id=self.room,
             message_type="m.room.message",
             content={"msgtype": "m.text", "body": message})