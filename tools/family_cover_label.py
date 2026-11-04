#!/usr/bin/env python3
"""Change "SchriftOhr Edition" on a front cover to "SchriftOhr Family Edition" (John, 2026-11-03).

    family_cover_label.py IN.jpg OUT.jpg ID

The covers are finished pictures with the words painted in, so the old words are lifted out of the picture and the
new ones set in their place, at the old size, colour and centre. BOX is where the old words stand on each cover.
Needs numpy and opencv (a throwaway venv will do); PIL for the type.
"""
import pathlib, sys
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

SUP = '/System/Library/Fonts/Supplemental/'
BI = (SUP + 'Baskerville.ttc', 3)   # bold italic
IT = (SUP + 'Baskerville.ttc', 2)   # italic
BD = (SUP + 'Baskerville.ttc', 1)   # bold
# x1, y1, x2, y2 of the old words; the face nearest the old lettering; text threshold over the ground
BOX = {
    'shenanigans-at-sugar-creek':    ((372, 447, 710, 492), IT, 14),
    'sugar-creek-goes-north':        ((406, 743, 682, 781), BI, 18),
    'sugar-creek-digs-for-treasure': ((376, 657, 718, 707), BI, 18),
    'north-woods-manhunt':           ((400, 556, 675, 594), IT, 9),
    'watermelon-mystery':            ((378, 405, 705, 451), IT, 14),
    'mystery-of-the-fires':          ((400, 618, 674, 655), BI, 18),
    'mystery-of-the-secret-band':    ((388, 804, 684, 835), BD, 18),
    'green-tent-mystery':            ((364, 1439, 712, 1485), BI, 18),
    'mystery-at-dark-cedars':        ((384, 628, 692, 660), BD, 18),
}

# how much wider than the old words the new may stand before they meet the cover's ornaments
ROOM = {'shenanigans-at-sugar-creek': 1.03, 'north-woods-manhunt': 1.2, 'watermelon-mystery': 1.2,
        'mystery-of-the-secret-band': 1.12, 'green-tent-mystery': 1.15, 'mystery-at-dark-cedars': 1.02,
        'sugar-creek-digs-for-treasure': 1.02}


def main():
    src, out, book = sys.argv[1:4]
    (x1, y1, x2, y2), (face, idx), t = BOX[book]
    im = np.array(Image.open(src).convert('RGB'))
    lab = cv2.cvtColor(im, cv2.COLOR_RGB2LAB)
    L = lab[:, :, 0].astype(np.int16)
    pad = 40
    region = lab[max(0, y1 - pad):y2 + pad, x1 - pad:x2 + pad, 0]
    ground = cv2.medianBlur(region, 61).astype(np.int16)
    diff = np.zeros_like(L)
    diff[max(0, y1 - pad):y2 + pad, x1 - pad:x2 + pad] = region.astype(np.int16) - ground
    box = np.zeros(L.shape, np.uint8)
    box[y1:y2, x1:x2] = 1
    bright = (diff > t) & (box > 0)
    # the old words' measure and colour
    ys, xs = np.nonzero(bright)
    wx1, wx2 = int(xs.min()), int(xs.max())
    counts = bright.sum(axis=1)
    rows = np.nonzero(counts >= counts.max() * 0.25)[0]
    base = int(rows.max())
    top = int(rows.min())
    colour = np.percentile(im[bright], 92, axis=0)
    # lift them out, shadow and all
    mask = (bright | ((diff < -t) & (box > 0))).astype(np.uint8) * 255
    mask = cv2.dilate(mask, np.ones((5, 5), np.uint8))
    clean = cv2.inpaint(im, mask, 5, cv2.INPAINT_TELEA)
    # grain back into the mended places, at the strength of the cloth around them: noise, because grain copied from
    # elsewhere on a cover brings the shapes of the words there with it
    blur = cv2.GaussianBlur(im.astype(np.float32), (0, 0), 2)
    high = im.astype(np.float32) - blur
    ring = np.zeros(L.shape, bool)
    ring[max(0, y1 - 14):y2 + 14, x1:x2] = True
    ring &= cv2.dilate(mask, np.ones((9, 9), np.uint8)) == 0
    strength = float(np.median(np.abs(high[ring]))) * 1.48
    rng = np.random.default_rng(1918)
    noise = cv2.GaussianBlur(rng.normal(0, 1, L.shape).astype(np.float32), (0, 0), 0.7) * 2.3 * strength
    soft = cv2.GaussianBlur(mask, (0, 0), 2).astype(np.float32)[:, :, None] / 255
    clean = np.clip(clean.astype(np.float32) + noise[:, :, None] * soft, 0, 255).astype(np.uint8)
    # the new words, set at four times over and brought down
    S = 4
    text = 'SchriftOhr Family Edition'
    probe = ImageFont.truetype(face, 100, index=idx)
    size = 100 * (wx2 - wx1) * ROOM.get(book, 1.05) / probe.getlength(text)
    f = ImageFont.truetype(face, round(size * S), index=idx)
    H, W = im.shape[:2]
    x = ((wx1 + wx2) / 2) * S - f.getlength(text) / 2
    layer = Image.new('L', (W * S, H * S), 0)
    ImageDraw.Draw(layer).text((x, base * S), text, font=f, fill=255, anchor='ls')
    letters = layer.resize((W, H), Image.LANCZOS)
    shadow = Image.new('L', (W, H), 0)
    shadow.paste(letters, (1, 2))
    shadow = shadow.filter(ImageFilter.GaussianBlur(1.2))
    res = Image.fromarray(clean)
    res.paste(Image.new('RGB', (W, H), (0, 0, 0)), (0, 0), shadow.point(lambda v: int(v * 0.35)))
    res.paste(Image.new('RGB', (W, H), tuple(int(c) for c in colour)), (0, 0), letters)
    res.save(out, 'JPEG', quality=93, optimize=True, progressive=True, subsampling=0)
    print(f'{book}: old words {wx1}-{wx2}, rows {top}-{base}, size {size:.0f}, colour {[int(c) for c in colour]}')


if __name__ == '__main__':
    main()
