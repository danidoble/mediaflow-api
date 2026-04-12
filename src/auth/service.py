import uuid

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from src.auth.exceptions import email_already_exists_exception, invalid_credentials_exception
from src.auth.models import User
from src.auth.schemas import TokenPair, UserRegister
from src.auth.security import create_access_token, create_refresh_token, hash_password, verify_password


async def register_user(data: UserRegister, db: AsyncSession) -> tuple[User, TokenPair]:
    result = await db.execute(select(User).where(User.email == data.email))
    if result.scalar_one_or_none():
        raise email_already_exists_exception

    user = User(email=data.email, hashed_password=hash_password(data.password))
    db.add(user)
    await db.commit()
    await db.refresh(user)

    tokens = TokenPair(
        access_token=create_access_token(str(user.id)),
        refresh_token=create_refresh_token(str(user.id)),
    )
    return user, tokens


async def login_user(email: str, password: str, db: AsyncSession) -> TokenPair:
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(password, user.hashed_password):
        raise invalid_credentials_exception

    return TokenPair(
        access_token=create_access_token(str(user.id)),
        refresh_token=create_refresh_token(str(user.id)),
    )


async def get_user_by_id(user_id: uuid.UUID, db: AsyncSession) -> User | None:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()
