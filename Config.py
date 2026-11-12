import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://kasange:123@localhost:5432/kasange_academic",
)
SECRET_KEY = os.getenv(
    "SECRET_KEY", "mfumo-wa-matokeo-kasange-academic-2026-kasange123-ndefu-sana"
)
ACCESS_TOKEN_EXPIRE_MINUTES = int(
    os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "480")
)
ALGORITHM = "HS256"

# Usahihi: Jina la Key linakaa kwanza, thamani ya kawaida (default) inakaa pili
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@kasange.ac.tz")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "Admin12345")