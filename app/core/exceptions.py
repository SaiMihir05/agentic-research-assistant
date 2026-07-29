from fastapi import Request
from fastapi.responses import JSONResponse
import logging

logger = logging.getLogger("app.core.exceptions")

async def global_exception_handler(request: Request, exc: Exception):
    logger.exception(f"Unhandled exception on {request.url.path}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error. Please try again later."},
    )
