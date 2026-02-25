from fastapi import APIRouter, UploadFile, File, HTTPException
import os
import uuid
import shutil

router = APIRouter()

# 1. Define where we want to save the images
UPLOAD_DIR = "uploads"

# 2. Automatically create the folder if it doesn't exist
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/")
def upload_image(file: UploadFile = File(...)):
    # 3. Security Check: Make sure it's actually an image!
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image format (jpg, png, etc.)")

    # 4. Generate a unique name so two customers don't overwrite each other's lists
    file_extension = file.filename.split(".")[-1]
    unique_filename = f"chitty_{uuid.uuid4().hex}.{file_extension}"
    file_path = os.path.join(UPLOAD_DIR, unique_filename)

    # 5. Save the file to your hard drive
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # 6. Return the public URL to the frontend
    # The frontend will grab this URL and put it inside the Order creation payload!
    return {"list_image_url": f"/static/{unique_filename}"}