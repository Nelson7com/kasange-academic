from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db,engine,Base
from fastapi import FastAPI,Depends,HTTPException,status
from contextlib import asynccontextmanager
from schema import StudentCreate,StudentRead,StudentUpdate
from models import Student


@asynccontextmanager

async def lifespan(app:FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
    yield
    await engine.dispose()
        