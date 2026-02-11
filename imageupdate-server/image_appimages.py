import os
from typing import List

from PIL import Image
from pydantic import BaseModel, Field


class AndroidImageVariant(BaseModel):
    density: str = Field(description="Android density bucket (mdpi, hdpi, xhdpi, xxhdpi, xxxhdpi)")
    width: int = Field(description="Width of the generated asset in pixels")
    height: int = Field(description="Height of the generated asset in pixels")
    path: str = Field(description="Output file path")


class AndroidAppImagesResult(BaseModel):
    source_path: str = Field(description="Original image path")
    output_dir: str = Field(description="Directory containing generated assets")
    base_size: int = Field(description="Base mdpi size in pixels")
    variants: List[AndroidImageVariant] = Field(description="Generated Android density assets")


class IphoneImageVariant(BaseModel):
    width: int = Field(description="Width of the generated asset in pixels")
    height: int = Field(description="Height of the generated asset in pixels")
    path: str = Field(description="Output file path")


class IphoneAppImagesResult(BaseModel):
    source_path: str = Field(description="Original image path")
    output_dir: str = Field(description="Directory containing generated assets")
    variants: List[IphoneImageVariant] = Field(description="Generated iPhone app preview assets")


def _center_crop_square(img: Image.Image) -> Image.Image:
    width, height = img.size
    side = min(width, height)
    left = (width - side) // 2
    top = (height - side) // 2
    return img.crop((left, top, left + side, top + side))


def _center_crop_to_ratio(img: Image.Image, target_ratio: float) -> Image.Image:
    width, height = img.size
    current_ratio = width / height

    if current_ratio > target_ratio:
        new_width = int(height * target_ratio)
        left = (width - new_width) // 2
        return img.crop((left, 0, left + new_width, height))
    if current_ratio < target_ratio:
        new_height = int(width / target_ratio)
        top = (height - new_height) // 2
        return img.crop((0, top, width, top + new_height))
    return img


def create_android_appimages(
    image_path: str,
    output_dir: str | None = None,
) -> AndroidAppImagesResult:
    """Create Android density assets from a source image (>= 1024x1024)."""
    if not os.path.isfile(image_path):
        raise RuntimeError(f"File not found: {image_path}")

    with Image.open(image_path) as img:
        img = img.convert("RGBA")
        width, height = img.size
        min_dim = min(width, height)
        if min_dim < 1024:
            raise RuntimeError("Image must be at least 1024x1024 pixels.")

        img = _center_crop_square(img)

        if output_dir is None:
            output_dir = os.path.join(os.path.dirname(image_path), "android_appimages")

        density_scales = {
            "mdpi": 1.0,
            "hdpi": 1.5,
            "xhdpi": 2.0,
            "xxhdpi": 3.0,
            "xxxhdpi": 4.0,
        }

        base_size = round(min_dim / 4)
        variants: List[AndroidImageVariant] = []

        for density, scale in density_scales.items():
            size = max(1, round(base_size * scale))
            resized = img.resize((size, size), Image.Resampling.LANCZOS)
            density_dir = os.path.join(output_dir, f"drawable-{density}")
            os.makedirs(density_dir, exist_ok=True)
            filename = f"{os.path.splitext(os.path.basename(image_path))[0]}_{size}x{size}.png"
            out_path = os.path.join(density_dir, filename)
            resized.save(out_path, format="PNG", optimize=True)
            variants.append(
                AndroidImageVariant(
                    density=density,
                    width=size,
                    height=size,
                    path=out_path,
                )
            )

    return AndroidAppImagesResult(
        source_path=image_path,
        output_dir=output_dir,
        base_size=base_size,
        variants=variants,
    )


def create_iphone_appimages(
    image_path: str,
    output_dir: str | None = None,
) -> IphoneAppImagesResult:
    """Create iPhone app preview image sizes from a source image (>= 1024x1024)."""
    if not os.path.isfile(image_path):
        raise RuntimeError(f"File not found: {image_path}")

    with Image.open(image_path) as img:
        img = img.convert("RGBA")
        width, height = img.size
        min_dim = min(width, height)
        if min_dim < 1024:
            raise RuntimeError("Image must be at least 1024x1024 pixels.")

        if output_dir is None:
            output_dir = os.path.join(os.path.dirname(image_path), "iphone_appimages")

        os.makedirs(output_dir, exist_ok=True)

        target_sizes = [
            (886, 1920),
            (1920, 886),
            (1080, 1920),
            (1920, 1080),
            (750, 1334),
            (1334, 750),
        ]

        variants: List[IphoneImageVariant] = []
        base_name = os.path.splitext(os.path.basename(image_path))[0]

        for width, height in target_sizes:
            target_ratio = width / height
            cropped = _center_crop_to_ratio(img, target_ratio)
            resized = cropped.resize((width, height), Image.Resampling.LANCZOS)
            out_path = os.path.join(output_dir, f"{base_name}_{width}x{height}.png")
            resized.save(out_path, format="PNG", optimize=True)
            variants.append(IphoneImageVariant(width=width, height=height, path=out_path))

    return IphoneAppImagesResult(
        source_path=image_path,
        output_dir=output_dir,
        variants=variants,
    )
