import uuid  # Gen random uuid
from io import BytesIO  # Working with image bytes in the memory
from pathlib import Path    # FileOperation
from PIL import Image, ImageOps  # Image operations

PROFILE_PICS_DIR = Path("media/profile_pics")   # Image directory

# FastAPI works well with async for I/O-bound operations #  Examples: database queries, HTTP calls, file reads/writes

# Pillow image processing is typically CPU-bound # Examples: resize, blur, compression, image transformations

# Running CPU-bound work directly inside an async endpoint blocks the event loop thread.

# While the event loop is busy processing the image, it cannot efficiently handle other requests.

# Solution - Write this as SYNC fun and offload this to threadpull which runs this on seperate thread


def process_profile_image(content: bytes) -> str:
    """Resize, optimize, and save a profile image. Returns the saved filename."""
    with Image.open(BytesIO(content)) as original:  # img= the final op image / original= starting image //\\ Open the bytes of the images
        img = ImageOps.exif_transpose(original)  # exif - fix orientation

        img = ImageOps.fit(img, (300, 300), method=Image.Resampling.LANCZOS)    # Resize and crop while maintaning the aspect ration //\\ LANCZOS-High Quality Resampling

        if img.mode in ("RGBA", "LA", "P"):
            img = img.convert("RGB")    # Convert to RGB

        filename = f"{uuid.uuid4().hex}.jpg"    # Unique filename
        filepath = PROFILE_PICS_DIR / filename  # Create file path

        PROFILE_PICS_DIR.mkdir(parents=True, exist_ok=True)  # Confirm directory is present else create dir

        img.save(filepath, "JPEG", quality=85, optimize=True)

    return filename


def delete_profile_image(filename: str | None) -> None:
    """Delete the profile image if exists"""
    if filename is None:
        return

    filepath = PROFILE_PICS_DIR / filename
    if filepath.exists():
        filepath.unlink()  # Delete if exist - unlink => path lib way of deleting a file
