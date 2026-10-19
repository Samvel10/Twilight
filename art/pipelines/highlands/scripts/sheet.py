# sheet.py <out.jpg> <width_per_image> <cols> img1 label1 img2 label2 ...
import sys
from PIL import Image, ImageDraw
out, W, cols = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
pairs = list(zip(sys.argv[4::2], sys.argv[5::2]))
ims = []
for f, lab in pairs:
    im = Image.open(f).convert('RGB'); h = int(im.height * W / im.width); ims.append((im.resize((W, h), Image.LANCZOS), lab))
H = max(i.height for i, _ in ims) + 22
rows = (len(ims) + cols - 1) // cols
S = Image.new('RGB', (W * cols, H * rows), (20, 20, 20)); d = ImageDraw.Draw(S)
for k, (im, lab) in enumerate(ims):
    x, y = (k % cols) * W, (k // cols) * H
    S.paste(im, (x, y + 22)); d.text((x + 6, y + 5), lab, fill=(255, 255, 255))
S.save(out, quality=88)
print(out)
