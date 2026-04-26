import logging
import math
import random
import struct
import zlib
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DATA_DIR = ROOT / "data"


def _png_chunk(tag: bytes, data: bytes) -> bytes:
    return (
        struct.pack(">I", len(data))
        + tag
        + data
        + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    )


def _write_rgba_png(path: Path, width: int, height: int, rgba: bytearray):
    raw = bytearray()
    row_size = width * 4

    for y in range(height):
        raw.append(0)
        start = y * row_size
        raw.extend(rgba[start:start + row_size])

    png = bytearray()
    png.extend(b"\x89PNG\r\n\x1a\n")
    png.extend(_png_chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)))
    png.extend(_png_chunk(b"IDAT", zlib.compress(bytes(raw), 6)))
    png.extend(_png_chunk(b"IEND", b""))

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(bytes(png))


def _generate_sand_texture(path: Path, size: int = 256, seed: int = 1337):
    rng = random.Random(seed)
    pixels = bytearray()

    for y in range(size):
        for x in range(size):
            wave = (
                math.sin(x * 0.11 + y * 0.035) * 7
                + math.sin(x * 0.031 - y * 0.085) * 5
                + math.sin((x + y) * 0.045) * 4
            )
            grain = rng.randint(-18, 18)

            r = 190 + int(wave) + grain
            g = 158 + int(wave * 0.75) + grain
            b = 98 + int(wave * 0.45) + grain

            p = rng.random()
            if p < 0.028:
                r -= rng.randint(18, 42)
                g -= rng.randint(14, 34)
                b -= rng.randint(8, 24)
            elif p > 0.982:
                r += rng.randint(18, 42)
                g += rng.randint(14, 34)
                b += rng.randint(8, 20)

            pixels.extend((
                max(0, min(255, r)),
                max(0, min(255, g)),
                max(0, min(255, b)),
                255,
            ))

    _write_rgba_png(path, size, size, pixels)
    logger.info("Generated texture: %s", path)


def ensure_generated_assets(data_dir: Optional[Path] = None):
    data_dir = Path(data_dir) if data_dir else DEFAULT_DATA_DIR
    textures_dir = data_dir / "textures"

    sand = textures_dir / "sand.png"

    if not sand.exists():
        _generate_sand_texture(sand)

    return {
        "sand": "/data/textures/sand.png",
    }