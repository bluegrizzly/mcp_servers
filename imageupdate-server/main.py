import os
from mcp.server.fastmcp import FastMCP

from image_dimension import (
    batch_resize_images as _batch_resize_images,
    get_image_dimension as _get_image_dimension,
    get_image_size as _get_image_size,
    resize_image as _resize_image,
)
from image_appimages import (
    create_android_appimages as _create_android_appimages,
    create_iphone_appimages as _create_iphone_appimages,
)
from image_optim import optimize_image as _optimize_image

# Get CheetahO API key from environment variable (kept for backwards compatibility)
CHEETAHO_API_KEY = os.environ.get("CHEETAHO_API_KEY")

mcp = FastMCP("ImageUpdate Server", instructions="Tools to resize and optimize images using CheetahO API.")

@mcp.tool()
def resize_image(
    image_url: str,
    width: int,
    height: int,
    strategy: str = "auto",
    quality: int = 80,
    keep_exif: bool = False,
    web_p: bool = False,
):
    """Resize and optimize an image locally using PIL. Accepts a local Windows path or URL."""
    return _resize_image(
        image_url=image_url,
        width=width,
        height=height,
        strategy=strategy,
        quality=quality,
        keep_exif=keep_exif,
        web_p=web_p,
    )


@mcp.tool()
def optimize_image(
    image_url: str,
    quality: int = 80,
    keep_exif: bool = False,
    web_p: bool = False,
):
    """Optimize an image locally using PIL. Accepts a local Windows path or URL."""
    return _optimize_image(
        image_url=image_url,
        quality=quality,
        keep_exif=keep_exif,
        web_p=web_p,
    )


@mcp.tool()
def batch_resize_images(
    folder_path: str,
    width: int = 100,
    height: int = 100,
    strategy: str = "exact",
    quality: int = 80,
    web_p: bool = False,
):
    """Resize all images in a folder to the given size. Overwrites each image in place. Returns a summary."""
    return _batch_resize_images(
        folder_path=folder_path,
        width=width,
        height=height,
        strategy=strategy,
        quality=quality,
        web_p=web_p,
    )


@mcp.tool()
def get_image_size(image_path: str):
    """Return the width, height, format, and file size (bytes) of an image file."""
    return _get_image_size(image_path=image_path)


@mcp.tool()
def get_image_dimension(image_path: str):
    """Return the width and height of an image file."""
    return _get_image_dimension(image_path=image_path)


@mcp.tool()
def create_android_appimages(image_path: str, output_dir: str | None = None):
    """Create all Android app images assets from a source image (>= 1024x1024)."""
    return _create_android_appimages(image_path=image_path, output_dir=output_dir)


@mcp.tool()
def create_iphone_appimages(image_path: str, output_dir: str | None = None):
    """Create all iPhone app preview image sizes from a source image (>= 1024x1024)."""
    return _create_iphone_appimages(image_path=image_path, output_dir=output_dir)


if __name__ == "__main__":
    mcp.run(transport="stdio")
