"""Contact sheet for the Workshop_W86 lift v01 previews (system Python + Pillow, not Blender).
  python make_lift_contact_sheet_v01.py [--force] [--dir DIR]
Reads preview_lift_v01_<view>.png and writes preview_lift_v01_contact_sheet.png in the same folder.
"""
import os
import sys

from PIL import Image, ImageDraw, ImageFont

ARGS = sys.argv[1:]
FORCE = '--force' in ARGS
DIR = ARGS[ARGS.index('--dir') + 1] if '--dir' in ARGS else os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
TILES = [
    ('down', 'DOWN - lift lowered, arms stowed (FBX rest pose): drive-in path and pit clear'),
    ('up', 'UP - van dummy 5.2 x 2.0 x 2.4 raised +1.6 m on engaged arms'),
    ('eye', 'EYE 1.7 m - player view from the doorway side, van raised'),
    ('elevation', 'ELEVATION from the door, raised: van top 4.00 / shut-off bar 4.10 / beam 4.22 / purlins 4.85+'),
    ('plan', 'PLAN section at 3.7 m - arms engaged, pads beside the pit, dummy wheels (wb 3.16)'),
    ('detail', 'DETAIL - R post: power unit, control box, hoses, hazard band, base plate'),
]
W, H, BAR, COLS = 960, 540, 34, 2


def main():
    out = os.path.join(DIR, 'preview_lift_v01_contact_sheet.png')
    if os.path.exists(out) and not FORCE:
        raise SystemExit('refusing to overwrite ' + out)
    rows = (len(TILES) + COLS - 1) // COLS
    head = 46
    sheet = Image.new('RGB', (COLS * W, head + rows * (H + BAR)), (24, 24, 26))
    d = ImageDraw.Draw(sheet)
    try:
        f = ImageFont.truetype('arial.ttf', 19)
        fh = ImageFont.truetype('arialbd.ttf', 24)
    except OSError:
        f = fh = ImageFont.load_default()
    d.text((12, 10), 'Workshop_W86 vehicle lift v01 - two-post overhead lift over the middle-bay pit (palette A), travel 0 -> 1.6 m', fill=(235, 235, 235), font=fh)
    for i, (name, label) in enumerate(TILES):
        img = Image.open(os.path.join(DIR, 'preview_lift_v01_%s.png' % name)).convert('RGB').resize((W, H), Image.LANCZOS)
        x, y = (i % COLS) * W, head + (i // COLS) * (H + BAR)
        sheet.paste(img, (x, y + BAR))
        d.text((x + 10, y + 6), label, fill=(240, 200, 90), font=f)
    sheet.save(out, optimize=True)
    print('wrote', out)


if __name__ == '__main__':
    main()
