from os import path as ospath, mkdir, system, getenv
from logging import INFO, ERROR, FileHandler, StreamHandler, basicConfig, getLogger
from traceback import format_exc
from asyncio import Queue, Lock

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from pyrogram import Client
from pyrogram.enums import ParseMode
from dotenv import load_dotenv
from uvloop import install

install()
basicConfig(format="[%(asctime)s] [%(name)s | %(levelname)s] - %(message)s [%(filename)s:%(lineno)d]",
            datefmt="%m/%d/%Y, %H:%M:%S %p",
            handlers=[FileHandler('bot.log'), StreamHandler()],
            level=INFO)

getLogger("pyrogram").setLevel(ERROR)
LOGS = getLogger(__name__)

load_dotenv('config.env')

# Audio type constants
SUBBED = "subbed"
DUBBED = "dubbed"

class AudioCache:
    """Enhanced cache system for dual-audio tracking"""
    def __init__(self):
        self.sub: Set[int] = set()  # AniList IDs of subbed content
        self.dub: Set[int] = set()  # AniList IDs of dubbed content
        self.ongoing: Set[int] = set()
        self.completed: Set[int] = set()
        self.fetch_enabled = True

    def add(self, ani_id: int, audio_type: str):
        """Add processed content to cache"""
        if audio_type == SUBBED:
            self.sub.add(ani_id)
        else:
            self.dub.add(ani_id)

    def exists(self, ani_id: int, audio_type: str) -> bool:
        """Check if content exists in cache"""
        return ani_id in (self.sub if audio_type == SUBBED else self.dub)

class Var:
    # Core Configuration
    API_ID = getenv("API_ID")
    API_HASH = getenv("API_HASH")
    BOT_TOKEN = getenv("BOT_TOKEN")
    MONGO_URI = getenv("MONGO_URI")
    
    # Dual Audio Configuration
    DUAL_AUDIO = getenv("DUAL_AUDIO", "true").lower() == "true"
    DUB_KEYWORDS = [kw.strip().lower() for kw in getenv("DUB_KEYWORDS", "[dub],[eng dub]").split(",")]
    SUB_KEYWORDS = [kw.strip().lower() for kw in getenv("SUB_KEYWORDS", "[sub],[eng sub]").split(",")]
    
    # Path Configuration
    DUBBED_PATH = getenv("DUBBED_PATH", "encode/dubbed")
    SUBBED_PATH = getenv("SUBBED_PATH", "encode/subbed")
    
    # Existing Configuration (unchanged)
    RSS_ITEMS = getenv("RSS_ITEMS", "https://nyaa.land/?page=rss&q=ToonsHub+dual+multi").split()
    FSUB_CHATS = list(map(int, getenv('FSUB_CHATS').split()))
    BACKUP_CHANNEL = getenv("BACKUP_CHANNEL") or ""
    MAIN_CHANNEL = int(getenv("MAIN_CHANNEL"))
    LOG_CHANNEL = int(getenv("LOG_CHANNEL") or 0)
    FILE_STORE = int(getenv("FILE_STORE"))
    ADMINS = list(map(int, getenv("ADMINS", "1242011540").split()))
    
    SEND_SCHEDULE = getenv("SEND_SCHEDULE", "False").lower() == "true"
    BRAND_UNAME = getenv("BRAND_UNAME", "@Dubsplease")
    FFCODE_1080 = getenv("FFCODE_1080") or """ffmpeg -i '{}' -progress '{}' -preset veryfast -c:v libx264 -s 1920x1080 -pix_fmt yuv420p -crf 30 -c:a libopus -b:a 32k -c:s copy -map 0 -ac 2 -ab 32k -vbr 2 -level 3.1 '{}' -y"""
    FFCODE_720 = getenv("FFCODE_720") or """ffmpeg -i '{}' -progress '{}' -preset superfast -c:v libx264 -s 1280x720 -pix_fmt yuv420p -crf 30 -c:a libopus -b:a 32k -c:s copy -map 0 -ac 2 -ab 32k -vbr 2 -level 3.1 '{}' -y"""
    FFCODE_480 = getenv("FFCODE_480") or """ffmpeg -i '{}' -progress '{}' -preset superfast -c:v libx264 -s 854x480 -pix_fmt yuv420p -crf 30 -c:a libopus -b:a 32k -c:s copy -map 0 -ac 2 -ab 32k -vbr 2 -level 3.1 '{}' -y"""
    FFCODE_360 = getenv("FFCODE_360") or """ffmpeg -i '{}' -progress '{}' -preset superfast -c:v libx264 -s 640x360 -pix_fmt yuv420p -crf 30 -c:a libopus -b:a 32k -c:s copy -map 0 -ac 2 -ab 32k -vbr 2 -level 3.1 '{}' -y"""
    FFCODE_HDRip = getenv("FFCODE_HDRip") or """ffmpeg -i '{}' -progress '{}' -preset superfast -c:v libx264 -s 1920x1080 -pix_fmt yuv420p -crf 30 -c:a libopus -b:a 32k -c:s copy -map 0 -ac 2 -ab 32k -vbr 2 -level 3.1 '{}' -y"""
    QUALS = getenv("QUALS", "360 480 720 1080 HDRip").split()
    
    AS_DOC = getenv("AS_DOC", "True").lower() == "true"
    THUMB = getenv("THUMB")
    ANIME = getenv("ANIME", "Is It Wr2131ong to Try to Pi123ck Up Girls in a Dungeon?")
    CUSTOM_BANNER = getenv("CUSTOM_BANNER", "https://envs.sh/LyC.jpg")        
    AUTO_DEL = getenv("AUTO_DEL", "True").lower() == "true"
    DEL_TIMER = int(getenv("DEL_TIMER", "1800"))
    START_PHOTO = getenv("START_PHOTO", "https://te.legra.ph/file/120de4dbad87fb20ab862.jpg")
    START_MSG = getenv("START_MSG", "<b>Hey {first_name}</b>,\n\n    <i>I am Auto Animes Store & Automater Encoder Build with ❤️ !!</i>")
    START_BUTTONS = getenv("START_BUTTONS", "UPDATES|https://telegram.me/Rokubotz SUPPORT|https://telegram.me/Team_Roku")


    def __init__(self):
        self._validate()

    def _validate(self):
        """Validate critical configurations"""
        if not all([self.API_ID, self.API_HASH, self.BOT_TOKEN, self.MONGO_URI]):
            LOGS.critical('Missing required environment variables!')
            exit(1)
            
        if self.DUAL_AUDIO:
            LOGS.info("Dual audio mode enabled")
            if not all([self.DUBBED_PATH, self.SUBBED_PATH]):
                LOGS.critical("Dual audio paths not configured!")
                exit(1)

Var = Var()

for directory in ["encode", "thumbs", "downloads", Var.DUBBED_PATH, Var.SUBBED_PATH]:
    if not ospath.isdir(directory):
        mkdir(directory)
        LOGS.info(f"Created directory: {directory}")
                
# Initialize caches and queues
ani_cache = AudioCache()
ffpids_cache = []
ffLock = Lock()
ffQueue = Queue()
ff_queued = {}

# Initialize caches and queues
ani_cache = AudioCache()
ffpids_cache = []
ffLock = Lock()
ffQueue = Queue()
ff_queued = {}

try:
    bot = Client(
        name="AutoAniAdvance",
        api_id=Var.API_ID,
        api_hash=Var.API_HASH,
        bot_token=Var.BOT_TOKEN,
        plugins=dict(root="bot/modules"),
        parse_mode=ParseMode.HTML
    )
    bot_loop = bot.loop
    sch = AsyncIOScheduler(timezone="Asia/Kolkata", event_loop=bot_loop)
    
except Exception as e:
    LOGS.critical(f"Failed to initialize bot: {str(e)}")
    exit(1)
