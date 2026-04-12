from fastapi import HTTPException, status

job_not_found = HTTPException(
    status_code=status.HTTP_404_NOT_FOUND,
    detail={"type": "https://httpstatuses.com/404", "title": "Job not found", "status": 404},
)

job_not_owned = HTTPException(
    status_code=status.HTTP_403_FORBIDDEN,
    detail={"type": "https://httpstatuses.com/403", "title": "Access denied", "status": 403},
)

job_not_cancellable = HTTPException(
    status_code=status.HTTP_409_CONFLICT,
    detail={"type": "https://httpstatuses.com/409", "title": "Job cannot be cancelled", "status": 409},
)
