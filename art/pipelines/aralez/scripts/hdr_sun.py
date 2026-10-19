import numpy as np, sys, re
f = open(sys.argv[1], 'rb'); hdr = b''
while True:
    l = f.readline(); hdr += l
    if l.strip() == b'': break
dims = f.readline().decode().split(); H, W = int(dims[1]), int(dims[3])
data = np.frombuffer(f.read(), np.uint8); img = np.zeros((H, W, 4), np.uint8); p = 0
for y in range(H):  # new-style RLE
    p += 4; row = np.zeros((4, W), np.uint8)
    for c in range(4):
        x = 0
        while x < W:
            n = data[p]; p += 1
            if n > 128: n -= 128; row[c, x:x + n] = data[p]; p += 1
            else: row[c, x:x + n] = data[p:p + n]; p += n
            x += n
    img[y] = row.T
e = img[..., 3].astype(np.int32); rgb = img[..., :3].astype(np.float32) * np.ldexp(1.0, e - 136)[..., None]
lum = rgb.mean(-1); y, x = np.unravel_index(np.argmax(lum), lum.shape)
print('size', W, H, 'max', lum.max(), 'at x', x, 'y', y, 'lon_deg(from left)', x / W * 360, 'elev_deg', 90 - y / H * 180)
# smaller preview for my eyes
from PIL import Image
t = np.clip((rgb / (1 + rgb)) ** (1 / 2.2), 0, 1); Image.fromarray((t[::4, ::4] * 255).astype(np.uint8)).save(sys.argv[2])
