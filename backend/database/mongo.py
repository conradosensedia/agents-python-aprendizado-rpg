from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import IndexModel, ASCENDING
import os

MONGO_URL = os.getenv("MONGO_URL", "mongodb://rpg:rpg123@localhost:27017/rpg_db?authSource=admin")

client: AsyncIOMotorClient = None
db = None


async def conectar():
    global client, db
    client = AsyncIOMotorClient(MONGO_URL)
    db = client["rpg_db"]

    # Índices para buscas comuns
    await db.sessions.create_indexes([
        IndexModel([("criado_em", ASCENDING)]),
        IndexModel([("status", ASCENDING)]),
    ])
    await db.characters.create_indexes([
        IndexModel([("session_id", ASCENDING)]),
    ])
    print("MongoDB conectado.")


async def desconectar():
    if client:
        client.close()


def get_db():
    return db
