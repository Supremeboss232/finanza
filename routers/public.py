from fastapi import APIRouter, Request, HTTPException, status
from fastapi.responses import FileResponse, RedirectResponse
import os

public_router = APIRouter()
STATIC_DIR = "static"

@public_router.get("/{page_name:path}", response_class=FileResponse)
async def serve_static_html(page_name: str):
    # Default to index.html if no page is specified
    if not page_name:
        page_name = "index.html"

    # Security: Prevent path traversal attacks.
    # Only allow .html files from the root of the static directory.
    if ".." in page_name or page_name.startswith("/") or not page_name.endswith(".html"):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Page not found")

    file_path = os.path.join(STATIC_DIR, page_name)

    # Security: Check if the resolved path is still within the static directory
    if not os.path.realpath(file_path).startswith(os.path.realpath(STATIC_DIR)):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Page not found")

    if not os.path.isfile(file_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Page not found")

    return FileResponse(file_path)