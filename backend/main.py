"""
Entry point for the backend server.
Run with:  python main.py
Or:        uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
"""

import uvicorn

from app.core.config import get_settings

settings = get_settings()

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.debug,
        log_level="debug" if settings.debug else "info",
    )
