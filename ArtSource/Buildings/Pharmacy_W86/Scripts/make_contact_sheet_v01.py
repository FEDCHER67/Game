"""Pharmacy_W86 v01 - contact sheet of the preview renders (system Python + Pillow).
Run:  python make_contact_sheet_v01.py [--force]   ->  ../Renders/preview_v01_contact_sheet.png
"""
import os
import sys

from PIL import Image, ImageDraw, ImageFont

RD = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'Renders'))
OUTP = os.path.join(RD, 'preview_v01_contact_sheet.png')
VIEWS = [('exterior_street', 'Street exterior, eye height 1.7 m (C, wordless, green cross)'),
         ('exterior_oblique', 'Storefront oblique: frames, beads, sill, riser panels, step'),
         ('sales_entrance', 'Sales floor from the entrance, eye height (B)'),
         ('sales_oblique', 'Counter / cash desk / STAFF ONLY gate + door, oblique'),
         ('shelf_oblique', 'Wall shelving (boards, lips, brackets, wall gap) + fridge'),
         ('counter_a', 'Counter close-up 1: Body Bag $5, Trash Bag $5, Organ Bag $10'),
         ('counter_b', 'Counter close-up 2: Empty Blood Bag $5, Blood Syringe $2, Empty Anesthetic Syringe $2'),
         ('counter_c', 'Counter close-up 3: Cable Tie $5, Cable Ties Pack of 4 $20, Basic Anesthetic $200 / vial'),
         ('stockroom', 'Stockroom (A) toward the open rear door, eye height'),
         ('stock_oblique', 'Stockroom racks oblique: posts, lips, cartons'),
         ('rear_courtyard', 'Courtyard side: rear door 1.30 m clear, canopy, ramp, van stop'),
         ('top_cutaway', 'Top cutaway: yellow customer, blue staff route, red carry path, orange van')]
TW, TH, CAP = 640, 360, 30


def main():
    if os.path.exists(OUTP) and '--force' not in sys.argv:
        raise SystemExit('refusing to overwrite ' + OUTP)
    cols = 3
    rows = (len(VIEWS) + cols - 1) // cols
    sheet = Image.new('RGB', (cols * TW, rows * (TH + CAP) + 50), (32, 34, 38))
    d = ImageDraw.Draw(sheet)
    fb = ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf', 26)
    f = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 15)
    d.text((14, 10), 'Pharmacy_W86 v01 - Rough 04-H3 ground-floor unit 11.5 x 12.7 m  (exterior C / sales floor B / stockroom A)', font=fb,
           fill=(235, 235, 230))
    for i, (name, cap) in enumerate(VIEWS):
        im = Image.open(os.path.join(RD, 'preview_v01_%s.png' % name)).convert('RGB')
        im.thumbnail((TW, TH))
        x = (i % cols) * TW
        y = 50 + (i // cols) * (TH + CAP)
        sheet.paste(im, (x + (TW - im.width) // 2, y + (TH - im.height) // 2))
        d.text((x + 8, y + TH + 6), cap, font=f, fill=(225, 225, 220))
    sheet.save(OUTP)
    print('wrote', OUTP)


if __name__ == '__main__':
    main()
