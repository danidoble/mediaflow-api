from fastapi import HTTPException, status

unsupported_image_type = HTTPException(
    status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
    detail={"type": "https://httpstatuses.com/415", "title": "Unsupported image type", "status": 415},
)

file_too_large = HTTPException(
    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
    detail={"type": "https://httpstatuses.com/413", "title": "File too large", "status": 413},
)

conversion_failed = HTTPException(
    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    detail={"type": "https://httpstatuses.com/500", "title": "Conversion failed", "status": 500},
)
