"""Generate PWA icons as simple PNG files."""
import struct, zlib, math

def png(w, h, pixels):
    def chunk(name, data):
        c = zlib.crc32(name + data) & 0xffffffff
        return struct.pack('>I', len(data)) + name + data + struct.pack('>I', c)
    raw = b''
    for y in range(h):
        raw += b'\x00'
        for x in range(w):
            raw += bytes(pixels[y][x])
    return b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0)) + chunk(b'IDAT', zlib.compress(raw, 9)) + chunk(b'IEND', b'')

def make_icon(size):
    bg = (13, 15, 18)        # #0D0F12
    teal = (10, 191, 184)    # #0ABFB8
    white = (255, 255, 255)
    pixels = [[list(bg) for _ in range(size)] for _ in range(size)]
    # Rounded background (approximate by clipping corners)
    r = size // 8
    cx, cy = size // 2, size // 2
    for y in range(size):
        for x in range(size):
            # Round corners
            in_corner = False
            for (cx2, cy2) in [(r,r),(size-r-1,r),(r,size-r-1),(size-r-1,size-r-1)]:
                dx, dy = x - cx2, y - cy2
                if abs(x - (r if x<size//2 else size-r-1)) < r and abs(y - (r if y<size//2 else size-r-1)) < r:
                    if dx*dx + dy*dy > r*r:
                        in_corner = True
            if in_corner:
                pixels[y][x] = list(teal)  # teal border on corners

    # Draw "V" shape in center
    pad = size // 4
    mid = size // 2
    thick = max(2, size // 24)
    for t in range(-thick, thick+1):
        # Left arm of V (top-left to bottom-center)
        steps = size - 2*pad
        for i in range(steps):
            x = pad + i + t
            y = pad + i
            if 0 <= x < size and 0 <= y < size:
                pixels[y][x] = list(teal)
        # Right arm of V (top-right to bottom-center)
        for i in range(steps):
            x = size - pad - i + t
            y = pad + i
            if 0 <= x < size and 0 <= y < size:
                pixels[y][x] = list(teal)
    return pixels

for size in [192, 512]:
    pixels = make_icon(size)
    data = png(size, size, pixels)
    with open(f'assets/icons/icon-{size}.png', 'wb') as f:
        f.write(data)
    print(f'Generated icon-{size}.png')
