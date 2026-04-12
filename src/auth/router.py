from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.dependencies import get_current_user, require_active
from src.auth.exceptions import credentials_exception
from src.auth.models import User
from src.auth.schemas import RefreshTokenRequest, TokenPair, UserRead, UserRegister
from src.auth.security import create_access_token, create_refresh_token, decode_token
from src.auth.service import login_user, register_user
from src.dependencies import get_db

router = APIRouter()


def _ok(data, message: str = "") -> dict:
    return {"success": True, "data": data, "message": message}


@router.post("/register", status_code=201)
async def register(body: UserRegister, db: AsyncSession = Depends(get_db)):
    user, tokens = await register_user(body, db)
    return _ok(
        {"user": UserRead.model_validate(user), "tokens": tokens},
        "Registration successful",
    )


@router.post("/login")
async def login(
    form: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    tokens = await login_user(form.username, form.password, db)
    # OAuth2 spec requires access_token + token_type at the top level
    return {
        "access_token": tokens.access_token,
        "refresh_token": tokens.refresh_token,
        "token_type": "bearer",
    }


@router.post("/refresh")
async def refresh(body: RefreshTokenRequest):
    try:
        payload = decode_token(body.refresh_token)
        if payload.get("type") != "refresh":
            raise credentials_exception
        subject: str | None = payload.get("sub")
        if not subject:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    return _ok(
        TokenPair(
            access_token=create_access_token(subject),
            refresh_token=create_refresh_token(subject),
        ),
        "Token refreshed",
    )


@router.get("/me")
async def me(current_user: User = Depends(require_active)):
    return _ok(UserRead.model_validate(current_user))
