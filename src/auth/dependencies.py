import uuid

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.exceptions import credentials_exception, user_inactive_exception
from src.auth.models import User
from src.auth.security import decode_token
from src.auth.service import get_user_by_id
from src.dependencies import get_db

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            raise credentials_exception
        user_id: str | None = payload.get("sub")
        if not user_id:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = await get_user_by_id(uuid.UUID(user_id), db)
    if not user:
        raise credentials_exception
    return user


async def require_active(user: User = Depends(get_current_user)) -> User:
    if not user.is_active:
        raise user_inactive_exception
    return user
