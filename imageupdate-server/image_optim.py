import os
from io import BytesIO

import requests
from PIL import Image
from pydantic import BaseModel, Field


class OptimizeResult(BaseModel):
    original_size: int = Field(description="Original image size in bytes")
    optimized_size: int = Field(description="Optimized image size in bytes")
    saved_bytes: int = Field(description="Bytes saved after optimization")
    saved_percent: float = Field(description="Percent saved after optimization")
    format: str = Field(description="Image format (JPEG, PNG, etc)")


def optimize_image(
    image_url: str,
    quality: int = 80,
    keep_exif: bool = False,
    web_p: bool = False,
) -> OptimizeResult:
    """Optimize an image locally using PIL. Accepts a local Windows path or URL."""
    try:
        # Load image from file or URL
        is_url = image_url.lower().startswith("http://") or image_url.lower().startswith("https://")
        if is_url:
            resp = requests.get(image_url)
            resp.raise_for_status()
            img = Image.open(BytesIO(resp.content))
        else:
            if not os.path.isfile(image_url):
                raise RuntimeError(f"File not found: {image_url}")
            img = Image.open(image_url)

        # Store original size
        original_img_bytes = BytesIO()
        img.save(original_img_bytes, format=img.format or "JPEG")
        original_size = len(original_img_bytes.getvalue())

        # Save with optimization
        output = BytesIO()
        save_format = "WEBP" if web_p else (img.format or "JPEG")

        # Convert RGBA to RGB if saving as JPEG
        if save_format.upper() == "JPEG" and img.mode in ("RGBA", "LA"):
            background = Image.new("RGB", img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[-1])
            img = background

        img.save(output, format=save_format, quality=quality, optimize=True)
        optimized_size = len(output.getvalue())
        saved_bytes = original_size - optimized_size
        saved_percent = (saved_bytes / original_size * 100) if original_size > 0 else 0

        # Save the optimized image back to the same location if local file
        if not is_url:
            try:
                with open(image_url, "wb") as f:
                    f.write(output.getvalue())
            except Exception as e:
                raise RuntimeError(f"Failed to write optimized image to disk: {e}")

        return OptimizeResult(
            original_size=original_size,
            optimized_size=optimized_size,
            saved_bytes=max(0, saved_bytes),
            saved_percent=max(0, saved_percent),
            format=save_format,
        )
    except Exception as e:
        raise RuntimeError(f"Image optimize error: {str(e)}")
