from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status
import os
from pathlib import Path
from deps import CurrentUserDep

router = APIRouter(prefix="/account", tags=["account"])

UPLOAD_DIR = Path("static") / "uploads" / "profile_pics"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@router.post("/upload-profile-picture")
async def upload_profile_picture(current_user: CurrentUserDep, file: UploadFile = File(...)):
    """Accepts a multipart form file and saves it to `static/uploads/profile_pics`.

    Returns the public URL for the uploaded image.
    """
    if not file.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No file uploaded")

    # sanitize filename (simple approach)
    filename = f"{current_user.id}_{os.path.basename(file.filename)}"
    save_path = UPLOAD_DIR / filename

    try:
        contents = await file.read()
        with open(save_path, "wb") as f:
            f.write(contents)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    public_url = f"/static/uploads/profile_pics/{filename}"
    # NOTE: Persisting this URL to the user's DB record is optional and not implemented here.
    return {"url": public_url}
