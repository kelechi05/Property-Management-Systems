import struct
import zlib


def chunk(tag: bytes, data: bytes) -> bytes:
    return (
        struct.pack(">I", len(data))
        + tag
        + data
        + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    )


def generate_logo(path: str = "static/img/logo.png", size: int = 256) -> None:
    w = h = size
    rows = []
    for y in range(h):
        row = bytearray()
        for x in range(w):
            # base background
            r, g, b, a = 248, 250, 252, 255

            # soft circular vignette
            dx, dy = x - w / 2, y - h / 2
            r2 = dx * dx + dy * dy
            radius2 = (size * 0.47) ** 2
            if r2 < radius2:
                shade = max(0, min(18, int(18 * (1 - r2 / radius2))))
                r, g, b = r - shade, g - shade, b - shade

            # house body
            if 0.49 * h < y < 0.78 * h and abs(x - w / 2) < 0.22 * w:
                r, g, b = 244, 161, 26

            # roof (triangle)
            if 0.31 * h < y < 0.55 * h and abs(x - w / 2) < (0.55 * h - y) * 1.1:
                r, g, b = 15, 118, 110

            # door
            if 0.59 * h < y < 0.78 * h and 0.47 * w < x < 0.53 * w:
                r, g, b = 11, 84, 77

            # windows
            if 0.55 * h < y < 0.63 * h and 0.35 * w < x < 0.43 * w:
                r, g, b = 255, 255, 255
            if 0.55 * h < y < 0.63 * h and 0.57 * w < x < 0.65 * w:
                r, g, b = 255, 255, 255

            # base line
            if abs(y - 0.78 * h) < 1 and abs(x - w / 2) < 0.24 * w:
                r, g, b = 15, 118, 110

            row.extend([int(r), int(g), int(b), a])
        rows.append(b"\x00" + bytes(row))

    raw = b"".join(rows)
    comp = zlib.compress(raw, 9)

    with open(path, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n")
        f.write(chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0)))
        f.write(chunk(b"IDAT", comp))
        f.write(chunk(b"IEND", b""))


if __name__ == "__main__":
    generate_logo()
