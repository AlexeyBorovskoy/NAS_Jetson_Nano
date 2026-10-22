"""Generate deterministic synthetic TIFF/PSD fixtures.

The script writes generated images to OUTDIR and creates manifest.json with
expected dimensions, modes, and SHA-256 hashes of uncompressed pixel buffers.
Hashes are computed from in-memory images before writing; generated fixtures
are not decoded again.

Usage:
    python generate_images.py OUTDIR

OUTDIR must not already exist.
"""

from __future__ import annotations

import hashlib
import json
import struct
import sys
from pathlib import Path

from PIL import Image

SCHEMA_VERSION = 1
TRUNCATED_BYTES = 20


def _frame(image: Image.Image) -> dict[str, object]:
    """Describe a frame: dimensions, mode, and uncompressed-pixel hash."""
    width, height = image.size
    return {
        "width": int(width),
        "height": int(height),
        "mode": image.mode,
        "pixel_sha256": hashlib.sha256(image.tobytes()).hexdigest(),
    }


def _positive_case(
    filename: str,
    image_format: str,
    frames: list[dict[str, object]],
) -> dict[str, object]:
    return {
        "file": filename,
        "expected_error": False,
        "format": image_format,
        "frames": frames,
    }


def _negative_case(filename: str, image_format: str) -> dict[str, object]:
    return {
        "file": filename,
        "expected_error": True,
        "format": image_format,
        "frames": [],
    }


def _pattern_row(width: int, y: int) -> bytes:
    """Return a deterministic RGB row without large tuple lists."""
    row = bytearray(width * 3)
    for x in range(width):
        offset = x * 3
        row[offset] = (x + 3 * y) & 0xFF
        row[offset + 1] = (2 * x + y) & 0xFF
        row[offset + 2] = ((5 * x) ^ (7 * y)) & 0xFF
    return bytes(row)


def _pattern_rgb(width: int, height: int) -> Image.Image:
    """Build an RGB image from repeated deterministic rows."""
    rows = [_pattern_row(width, y) for y in range(16)]
    data = b"".join(rows[y % len(rows)] for y in range(height))
    return Image.frombytes("RGB", (width, height), data)


_PSD_PALETTE: tuple[tuple[int, int, int], ...] = (
    (204, 32, 48),
    (32, 192, 64),
    (40, 64, 208),
    (192, 192, 48),
    (48, 192, 192),
    (192, 48, 192),
    (96, 96, 96),
    (240, 160, 32),
)


def _psd_source(width: int, height: int) -> tuple[Image.Image, bytes]:
    """Build an RGB image and independent interleaved buffer for PSD.

    Rows use solid colors that cycle, keeping the RLE fixture compact.
    """
    row_variants = [bytes(color) * width for color in _PSD_PALETTE]
    interleaved = b"".join(
        row_variants[y % len(row_variants)] for y in range(height)
    )
    image = Image.frombytes("RGB", (width, height), interleaved)
    return image, interleaved


def _psd_header(height: int, width: int, compression: int) -> bytes:
    """Build a PSD header from the public format description."""
    return b"".join(
        (
            b"8BPS",
            struct.pack(">H", 1),
            b"\x00" * 6,
            struct.pack(">H", 3),
            struct.pack(">II", height, width),
            struct.pack(">H", 8),
            struct.pack(">H", 3),
            struct.pack(">I", 0),
            struct.pack(">I", 0),
            struct.pack(">I", 0),
            struct.pack(">H", compression),
        )
    )


def _packbits(data: bytes) -> bytes:
    """Encode PackBits runs and literals."""
    out = bytearray()
    index = 0
    length = len(data)

    while index < length:
        run_end = index + 1
        while (
            run_end < length
            and run_end - index < 128
            and data[run_end] == data[index]
        ):
            run_end += 1
        run_length = run_end - index

        if run_length >= 3:
            # Repeat N copies: signed byte 1-N, then value; 1 <= N <= 128.
            out.append((1 - run_length) & 0xFF)
            out.append(data[index])
            index = run_end
            continue

        literal_start = index
        index = run_end
        while index < length and index - literal_start < 128:
            probe = index + 1
            while (
                probe < length
                and probe - index < 3
                and data[probe] == data[index]
            ):
                probe += 1
            if probe - index >= 3:
                break
            index = probe

        literal_end = min(index, literal_start + 128)
        literal = data[literal_start:literal_end]
        # Literal packet: byte count minus one, then the bytes.
        out.append(len(literal) - 1)
        out.extend(literal)
        index = literal_end

    return bytes(out)


def _psd_raw(interleaved: bytes, height: int, width: int) -> bytes:
    """Build an uncompressed PSD with full R, G, and B planes."""
    planes = b"".join(interleaved[channel::3] for channel in range(3))
    return _psd_header(height, width, 0) + planes


def _psd_rle(interleaved: bytes, height: int, width: int) -> bytes:
    """Build a PackBits RLE PSD with a row-length table and compressed rows."""
    lengths = bytearray()
    packed_rows: list[bytes] = []

    for channel in range(3):
        plane = interleaved[channel::3]
        for y in range(height):
            row = plane[y * width:(y + 1) * width]
            packed = _packbits(row)
            if len(packed) > 0xFFFF:
                raise ValueError("PSD row does not fit in uint16")
            lengths.extend(struct.pack(">H", len(packed)))
            packed_rows.append(packed)

    return _psd_header(height, width, 1) + bytes(lengths) + b"".join(packed_rows)


def _write_truncated_tiff(path: Path, image: Image.Image) -> None:
    """Write a TIFF and retain only its first 20 bytes."""
    image.save(path, format="TIFF", compression="raw")
    with path.open("r+b") as handle:
        handle.truncate(TRUNCATED_BYTES)


def generate(outdir: str | Path) -> dict[str, object]:
    """Create OUTDIR (which must not exist) and return its manifest."""
    target = Path(outdir)
    target.mkdir(parents=False, exist_ok=False)

    cases: list[dict[str, object]] = []

    rgb = _pattern_rgb(512, 384)
    rgb_frame = _frame(rgb)

    name = "rgb_512x384_uncompressed.tif"
    rgb.save(target / name, format="TIFF", compression="raw")
    cases.append(_positive_case(name, "TIFF", [rgb_frame]))

    name = "rgb_512x384_deflate.tif"
    rgb.save(target / name, format="TIFF", compression="tiff_deflate")
    cases.append(_positive_case(name, "TIFF", [rgb_frame]))

    name = "rgb_512x384_lzw.tif"
    rgb.save(target / name, format="TIFF", compression="tiff_lzw")
    cases.append(_positive_case(name, "TIFF", [rgb_frame]))

    gray = Image.new("I;16", (256, 128))
    gray_values = [
        ((x * 257) ^ (y * 131)) & 0xFFFF
        for y in range(128)
        for x in range(256)
    ]
    gray.putdata(gray_values)
    gray_frame = _frame(gray)
    name = "gray16_256x128.tif"
    gray.save(target / name, format="TIFF", compression="raw")
    cases.append(_positive_case(name, "TIFF", [gray_frame]))

    page_one = Image.new("RGB", (320, 240), (176, 48, 32))
    page_two = Image.new("RGB", (320, 240), (32, 64, 176))
    pages_frames = [_frame(page_one), _frame(page_two)]
    name = "rgb_two_page.tif"
    page_one.save(
        target / name,
        format="TIFF",
        save_all=True,
        append_images=[page_two],
        compression="raw",
    )
    cases.append(_positive_case(name, "TIFF", pages_frames))

    large = _pattern_rgb(2048, 2048)
    large_frame = _frame(large)
    name = "rgb_2048x2048_deflate.tif"
    large.save(target / name, format="TIFF", compression="tiff_deflate")
    cases.append(_positive_case(name, "TIFF", [large_frame]))

    psd_image, psd_interleaved = _psd_source(512, 384)
    psd_frame = _frame(psd_image)
    raw_psd = _psd_raw(psd_interleaved, 384, 512)
    name = "rgb_512x384_raw.psd"
    (target / name).write_bytes(raw_psd)
    cases.append(_positive_case(name, "PSD", [psd_frame]))

    rle_psd = _psd_rle(psd_interleaved, 384, 512)
    name = "rgb_512x384_rle.psd"
    (target / name).write_bytes(rle_psd)
    cases.append(_positive_case(name, "PSD", [psd_frame]))

    name = "truncated_20b.tif"
    _write_truncated_tiff(target / name, rgb)
    cases.append(_negative_case(name, "TIFF"))

    name = "truncated_20b.psd"
    (target / name).write_bytes(raw_psd[:TRUNCATED_BYTES])
    cases.append(_negative_case(name, "PSD"))

    manifest: dict[str, object] = {
        "schema": SCHEMA_VERSION,
        "cases": cases,
    }
    (target / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return manifest


def main(argv: list[str] | None = None) -> int:
    """CLI entry point; print a compact JSON report."""
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1:
        print(
            json.dumps(
                {"error": "usage: python generate_images.py OUTDIR"},
                ensure_ascii=False,
            )
        )
        return 2

    outdir = Path(args[0])
    try:
        manifest = generate(outdir)
    except FileExistsError:
        print(
            json.dumps(
                {"error": f"directory already exists: {outdir}"},
                ensure_ascii=False,
            )
        )
        return 1
    except OSError as exc:
        print(
            json.dumps(
                {"error": f"failed to generate fixtures: {exc}"},
                ensure_ascii=False,
            )
        )
        return 1

    cases = manifest["cases"]
    summary = {
        "manifest": str(outdir / "manifest.json"),
        "outdir": str(outdir),
        "case_count": len(cases),
        "positive_count": sum(
            1 for case in cases if not case["expected_error"]
        ),
        "negative_count": sum(
            1 for case in cases if case["expected_error"]
        ),
        "files": [case["file"] for case in cases],
    }
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
