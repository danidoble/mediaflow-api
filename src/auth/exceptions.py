from fastapi import HTTPException, status

credentials_exception = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail={"type": "https://httpstatuses.com/401", "title": "Unauthorized", "status": 401},
    headers={"WWW-Authenticate": "Bearer"},
)

user_not_found_exception = HTTPException(
    status_code=status.HTTP_404_NOT_FOUND,
    detail={"type": "https://httpstatuses.com/404", "title": "User not found", "status": 404},
)

user_inactive_exception = HTTPException(
    status_code=status.HTTP_403_FORBIDDEN,
    detail={"type": "https://httpstatuses.com/403", "title": "Inactive user", "status": 403},
)

email_already_exists_exception = HTTPException(
    status_code=status.HTTP_409_CONFLICT,
    detail={"type": "https://httpstatuses.com/409", "title": "Email already registered", "status": 409},
)

invalid_credentials_exception = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail={"type": "https://httpstatuses.com/401", "title": "Invalid credentials", "status": 401},
    headers={"WWW-Authenticate": "Bearer"},
)
