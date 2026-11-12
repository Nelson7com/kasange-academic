from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import select

import models  # noqa: F401  (inasajili models kwenye Base)
from admin import router as admin_router
from auth import router as auth_router
from Config import ADMIN_EMAIL, ADMIN_PASSWORD
from database import AsyncSessionFactory, Base, engine
from models import Role, User
from security import hash_password
from teachers import router as teacher_router


async def seed_admin() -> None:
    """Tengeneza admin wa kwanza kutoka .env kama hakuna admin bado."""
    if not ADMIN_EMAIL or not ADMIN_PASSWORD:
        return
    async with AsyncSessionFactory() as session:
        existing = await session.scalar(select(User).where(User.role == Role.ADMIN).limit(1))
        if existing is None:
            session.add(
                User(
                    email=ADMIN_EMAIL.lower(),
                    hashed_password=hash_password(ADMIN_PASSWORD),
                    role=Role.ADMIN,
                )
            )
            await session.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Kwa maendeleo. Production tumia Alembic kwa migrations.
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await seed_admin()
    yield
    await engine.dispose()


app = FastAPI(title="Kasange Academic - Mfumo wa Matokeo", lifespan=lifespan)

app.include_router(auth_router)
app.include_router(teacher_router)
app.include_router(admin_router)


@app.get("/", tags=["Health"])
async def root():
    return {"status": "ok", "app": "Kasange Academic"}