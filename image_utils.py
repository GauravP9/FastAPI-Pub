import uuid  # Gen random uuid
from io import BytesIO  # Working with image bytes in the memory

import boto3

# from pathlib import Path    # FileOperation
from PIL import Image, ImageOps  # Image operations
from starlette.concurrency import run_in_threadpool  # Offload blocking call to threadpool

from config import settings

# PROFILE_PICS_DIR = Path("media/profile_pics")  # Image directory

# FastAPI works well with async for I/O-bound operations #  Examples: database queries, HTTP calls, file reads/writes
# Pillow image processing is typically CPU-bound # Examples: resize, blur, compression, image transformations
# Running CPU-bound work directly inside an async endpoint blocks the event loop thread.
# While the event loop is busy processing the image, it cannot efficiently handle other requests.
# Solution - Write this as SYNC fun and offload this to threadpull which runs this on seperate thread


def _get_s3_client():  # Private Helper
    """Helper fun for the s3 client"""
    return boto3.client(
        "s3",
        region_name=settings.s3_bucket_region,
        aws_access_key_id=(settings.s3_access_key_id.get_secret_value() if settings.s3_access_key_id else None),
        aws_secret_access_key=(settings.s3_secret_access_key.get_secret_value() if settings.s3_secret_access_key else None),
        endpoint_url=settings.s3_enpoint_url,
    )


def process_profile_image(content: bytes) -> tuple[bytes, str]:
    """Resize, optimize, and save a profile image. Returns the saved filename."""
    with Image.open(BytesIO(content)) as original:  # img= the final op image / original= starting image //\\ Open the bytes of the images
        img = ImageOps.exif_transpose(original)  # exif - fix orientation

        img = ImageOps.fit(img, (300, 300), method=Image.Resampling.LANCZOS)  # Resize and crop while maintaning the aspect ration //\\ LANCZOS-High Quality Resampling

        if img.mode in ("RGBA", "LA", "P"):
            img = img.convert("RGB")  # Convert to RGB

        filename = f"{uuid.uuid4().hex}.jpg"  # Unique filename
        # filepath = PROFILE_PICS_DIR / filename  # Create file path

        output = BytesIO()  # In-Memory as we will be uploading directly from here not saving to disk

        # PROFILE_PICS_DIR.mkdir(parents=True, exist_ok=True)  # Confirm directory is present else create dir

        img.save(output, "JPEG", quality=85, optimize=True)  # Pillow writes the JPEG data into the BytesIO object.
        output.seek(0)  # We set cursor to start of the object so that at time of reading we read all the bytes
    return output.read(), filename  # Read the bytes and name [ COULD DO output.getvalue() this return same result]


def _upload_to_s3(file_byte: bytes, key: str):
    s3 = _get_s3_client()

    s3.upload_fileobj(  # Read Documentation about upload fun for more info on fun
        BytesIO(file_byte),
        settings.s3_bucket_name,
        key,
        ExtraArgs={"ContentType": "image/jpeg"},  # Sometime browser may download so used content-type
    )


def _del_from_s3(key) -> None:
    s3 = _get_s3_client()
    s3.delete_object(Bucket=settings.s3_bucket_name, Key=key)


# ASYNC wrapper on the above funs
async def upload_profile_image(file_byte: bytes, filename: str) -> None:
    key = f"profile_pics/{filename}"
    await run_in_threadpool(_upload_to_s3, file_byte=file_byte, key=key)


async def delete_profile_image(filename: str) -> None:
    if filename is None:
        return
    key = f"profile_pics/{filename}"
    await run_in_threadpool(_del_from_s3, key=key)
