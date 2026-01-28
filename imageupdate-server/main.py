import os
import requests
from io import BytesIO
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from mcp.server.fastmcp import FastMCP
from PIL import Image

# Get CheetahO API key from environment variable (kept for backwards compatibility)
CHEETAHO_API_KEY = os.environ.get("CHEETAHO_API_KEY")

mcp = FastMCP("ImageUpdate Server", instructions="Tools to resize and optimize images using CheetahO API.")

class ResizeResult(BaseModel):
    width: int = Field(description="Width of the resized image")
    height: int = Field(description="Height of the resized image")
    original_size: int = Field(description="Original image size in bytes")
    optimized_size: int = Field(description="Optimized image size in bytes")
    saved_bytes: int = Field(description="Bytes saved after optimization")
    saved_percent: float = Field(description="Percent saved after optimization")
    format: str = Field(description="Image format (JPEG, PNG, etc)")

@mcp.tool()
def resize_image(
    image_url: str,
    width: int,
    height: int,
    strategy: str = "auto",
    quality: int = 80,
    keep_exif: bool = False,
    web_p: bool = False,
) -> ResizeResult:
    """Resize and optimize an image locally using PIL. Accepts a local Windows path or URL."""
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
        
        # Calculate new dimensions based on strategy
        orig_width, orig_height = img.size
        if strategy == "exact":
            new_width, new_height = width, height
        elif strategy == "portrait":
            new_height = height
            new_width = int((height / orig_height) * orig_width)
        elif strategy == "landscape":
            new_width = width
            new_height = int((width / orig_width) * orig_height)
        elif strategy == "fit":
            # Crop and resize to fit
            ratio = max(width / orig_width, height / orig_height)
            new_w = int(orig_width * ratio)
            new_h = int(orig_height * ratio)
            img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
            left = (new_w - width) / 2
            top = (new_h - height) / 2
            img = img.crop((left, top, left + width, top + height))
            new_width, new_height = width, height
        else:  # auto
            if orig_width > orig_height:
                new_width = width
                new_height = int((width / orig_width) * orig_height)
            else:
                new_height = height
                new_width = int((height / orig_height) * orig_width)
        
        # Resize if not already done by fit
        if strategy != "fit":
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        # Save with quality
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
        
        return ResizeResult(
            width=new_width,
            height=new_height,
            original_size=original_size,
            optimized_size=optimized_size,
            saved_bytes=max(0, saved_bytes),
            saved_percent=max(0, saved_percent),
            format=save_format,
        )
    except Exception as e:
        raise RuntimeError(f"Image resize error: {str(e)}")

class OptimizeResult(BaseModel):
    original_size: int = Field(description="Original image size in bytes")
    optimized_size: int = Field(description="Optimized image size in bytes")
    saved_bytes: int = Field(description="Bytes saved after optimization")
    saved_percent: float = Field(description="Percent saved after optimization")
    format: str = Field(description="Image format (JPEG, PNG, etc)")

@mcp.tool()
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

@mcp.tool()
def batch_resize_images(
    folder_path: str,
    width: int = 100,
    height: int = 100,
    strategy: str = "exact",
    quality: int = 80,
    web_p: bool = False,
) -> dict:
    """Resize all images in a folder to the given size. Overwrites each image in place. Returns a summary."""
    import glob
    supported_exts = ("*.jpg", "*.jpeg", "*.png", "*.webp", "*.bmp", "*.tiff", "*.gif")
    files = []
    for ext in supported_exts:
        files.extend(glob.glob(os.path.join(folder_path, ext)))
    results = []
    for f in files:
        try:
            res = resize_image(f, width, height, strategy, quality, False, web_p)
            results.append({"file": f, "status": "ok", "width": res.width, "height": res.height})
        except Exception as e:
            results.append({"file": f, "status": f"error: {e}"})
    return {"processed": len(files), "results": results}

@mcp.tool()
def get_image_size(image_path: str) -> dict:
    """Return the width, height, format, and file size (bytes) of an image file."""
    if not os.path.isfile(image_path):
        raise RuntimeError(f"File not found: {image_path}")
    from PIL import Image
    with Image.open(image_path) as img:
        width, height = img.size
        fmt = img.format
    file_size = os.path.getsize(image_path)
    return {"width": width, "height": height, "format": fmt, "file_size": file_size}


if __name__ == "__main__":
    mcp.run(transport="stdio")
