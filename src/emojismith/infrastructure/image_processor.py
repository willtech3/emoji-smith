"""Image processing utilities for Slack emoji optimization.

Handles compression and resizing to meet Slack's 128KB file size limit
while preserving transparency for emoji display.
"""

from __future__ import annotations

import io

from PIL import Image


def compress_for_slack(image_bytes: bytes, max_size_kb: int = 128) -> bytes:
    """Compress image to meet Slack's 128KB limit while preserving transparency.

    Args:
        image_bytes: Original PNG image bytes
        max_size_kb: Maximum file size in KB (default: 128)

    Returns:
        Compressed PNG bytes under the size limit
    """
    img = Image.open(io.BytesIO(image_bytes))

    # Resize if needed (start at 512x512, reduce if still too large)
    sizes = [512, 256, 128]

    for size in sizes:
        output = io.BytesIO()
        resized = img.resize((size, size), Image.Resampling.LANCZOS)
        resized.save(output, format="PNG", optimize=True)

        if output.tell() <= max_size_kb * 1024:
            return output.getvalue()

    # Final fallback: use maximum compression
    output = io.BytesIO()
    img.resize((128, 128), Image.Resampling.LANCZOS).save(
        output, format="PNG", optimize=True, compress_level=9
    )
    return output.getvalue()
