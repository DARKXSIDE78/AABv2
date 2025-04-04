from motor.motor_asyncio import AsyncIOMotorClient
from bot import Var

class MongoDB:
    def __init__(self, uri, database_name):
        self.__client = AsyncIOMotorClient(uri)
        self.__db = self.__client[database_name]
        self.__animes = self.__db.animes[Var.BOT_TOKEN.split(':')[0]]

    async def getAnime(self, ani_id):
        botset = await self.__animes.find_one({'_id': ani_id})
        return botset or {}

    async def saveAnime(self, ani_id, ep, qual, post_id=None):
        quals = (await self.getAnime(ani_id)).get(ep, {qual: False for qual in Var.QUALS})
        quals[qual] = True
        await self.__animes.update_one({'_id': ani_id}, {'$set': {ep: quals}}, upsert=True)
        if post_id:
            await self.__animes.update_one({'_id': ani_id}, {'$set': {"msg_id": post_id}}, upsert=True)

    async def reboot(self):
        await self.__animes.drop()

db = MongoDB(Var.MONGO_URI, "GenAnimeOngoingV2")

class DualAudioDB:
    def __init__(self):
        self.client = AsyncIOMotorClient(Var.MONGO_URI)
        self.db = self.client['AutoDualAudio']
        self.col = self.db['dub_torrents']

    async def add_dual_entry(self, data: dict):
        await self.col.update_one(
            {'_id': data['title']},
            {'$set': data},
            upsert=True
        )

    async def get_dual_entry(self, title: str):
        return await self.col.find_one({'_id': title})

dual_db = DualAudioDB()
