"""Contact sheet of the GEAR room previews: python contact_sheet.py <Previews/vNN folder> [out.png] [cell width]
Puts every NN_*.png of the folder into a 3-column grid with its file name as a label (never overwrites an existing sheet)."""
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

src = Path(sys.argv[1])
out = Path(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2] else src / f'contact_sheet_{src.name}.png'
cw = int(sys.argv[3]) if len(sys.argv) > 3 else 800
if out.exists():
    sys.exit(f'Refusing to overwrite {out}')
files = sorted(p for p in src.glob('[0-9][0-9]_*.png'))
ims = [Image.open(p).convert('RGB') for p in files]
ch = int(cw * ims[0].height / ims[0].width)
cols = 3
rows = (len(ims) + cols - 1) // cols
lab = 34
sheet = Image.new('RGB', (cols * cw, rows * (ch + lab)), (24, 24, 26))
d = ImageDraw.Draw(sheet)
try:
    font = ImageFont.truetype('arial.ttf', 22)
except OSError:
    font = ImageFont.load_default()
for i, (p, im) in enumerate(zip(files, ims)):
    x, y = (i % cols) * cw, (i // cols) * (ch + lab)
    sheet.paste(im.resize((cw, ch), Image.LANCZOS), (x, y + lab))
    d.text((x + 10, y + 6), p.stem, fill=(235, 225, 205), font=font)
sheet.save(out)
print(out)
