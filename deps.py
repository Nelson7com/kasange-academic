import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import Role, Teacher, User
from security import decode_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def _credentials_error() -> HTTPException:
    return HTTPException(
        status.HTTP_401_UNAUTHORIZED,
        "Token si sahihi au imekwisha muda",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    try:
        payload = decode_access_token(token)
        user_id = int(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        raise _credentials_error()

    user = await db.get(User, user_id)
    if user is None or not user.is_active:
        raise _credentials_error()
    return user


async def get_current_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != Role.ADMIN:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Ruhusa ya admin tu")
    return user


async def get_current_teacher(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Teacher:
    if user.role != Role.TEACHER:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Ruhusa ya mwalimu tu")
    result = await db.execute(select(Teacher).where(Teacher.user_id == user.id))
    teacher = result.scalar_one_or_none()
    if teacher is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Akaunti haina profile ya mwalimu")
    return teacher