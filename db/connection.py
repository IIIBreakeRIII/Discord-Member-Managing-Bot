import os
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

# Refactor: centralize Mongo connection; behavior unchanged
load_dotenv()
MONGO_URI = os.getenv("MONGODB_URI")

client = AsyncIOMotorClient(MONGO_URI)
db = client.watchersdb

userlogs = db.userlogs
quitlogs = db.quitlogs
voice_sessions = db.voice_sessions
