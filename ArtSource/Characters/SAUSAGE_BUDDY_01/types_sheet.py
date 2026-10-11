"""After the NPC type builds (build_buddy.py --variant <TYPE> --revision N): per-type colourway strips, the line-up of
all types in three colourways and the colour manifest for the game. Plain Python + Pillow (no Blender).

  python ArtSource/Characters/SAUSAGE_BUDDY_01/types_sheet.py --revision 1
"""
import argparse, json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
TYPES = HERE / 'Types'
ORDER = ['JUNKIE', 'VILLAGE_GRANDPA', 'VILLAGE_GRANDMA', 'VILLAGE_MAN', 'CITY_CLERK', 'CITY_STUDENT', 'CITY_JOGGER',
         'RICH_BUSINESS', 'RICH_NEWRUSSIAN', 'RICH_YACHT', 'POLICE_THIN', 'POLICE_FAT', 'FSB_GUARD']
CROP = (190, 110, 730, 1150)          # character area of the 900x1200 three-quarter stills
BG = (196, 198, 204)


def font(size):
    for f in ('C:/Windows/Fonts/segoeui.ttf', 'C:/Windows/Fonts/arial.ttf', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'):
        try:
            return ImageFont.truetype(f, size)
        except OSError:
            continue
    return ImageFont.load_default()


def tile(path, w):
    im = Image.open(path).convert('RGB').crop(CROP)
    return im.resize((w, int(im.height * w / im.width)), Image.LANCZOS)


ap = argparse.ArgumentParser()
ap.add_argument('--revision', type=int, required=True)
args = ap.parse_args()
REV = f'v{args.revision:02d}'
out_dir = TYPES / 'Previews'
out_dir.mkdir(parents=True, exist_ok=True)
lineup_path, manifest_path = out_dir / f'LINEUP_{REV}.png', TYPES / f'npc_types_{REV}.json'
for p in (lineup_path, manifest_path):
    if p.exists():
        raise SystemExit(f'Refusing to overwrite {p}; choose a new --revision')

manifest = {'revision': REV, 'note': 'Each garment is its own material <TYPE>_<Slot>: recolour a slot by tinting that material '
                                     '(colours below are sRGB). Clips come from SAUSAGE_BUDDY_BASE (same skeleton).', 'types': {}}
cols = []
for name in ORDER:
    prev = TYPES / name / 'Previews' / REV
    shots = [prev / '04_idle_three_quarter.png', prev / '06_colourway_1.png', prev / '06_colourway_2.png']
    if not all(p.exists() for p in shots):
        print('skip', name, '(no previews)')
        continue
    report = json.loads((TYPES / name / f'validation_{name}_{REV}.json').read_text(encoding='utf-8'))
    info = report['npc_type']
    info.update({'blend': f'Types/{name}/SAUSAGE_BUDDY_{name}_{REV}.blend', 'fbx': f'Types/{name}/SAUSAGE_BUDDY_{name}_{REV}.fbx',
                 'triangles': report['total_triangles']})
    manifest['types'][name] = info
    tiles = [tile(p, 300) for p in shots]
    # per-type strip: default + two colourways
    strip = Image.new('RGB', (sum(t.width for t in tiles), tiles[0].height + 44), BG)
    d = ImageDraw.Draw(strip)
    for k, t in enumerate(tiles):
        strip.paste(t, (k * t.width, 44))
        d.text((k * t.width + 12, 8), ('по умолчанию', 'вариант 1', 'вариант 2')[k], fill=(40, 40, 44), font=font(24))
    strip.save(prev / '06_colourways.png')
    for p in shots[1:]:
        p.unlink()
    cols.append((info['label'], tiles))

# line-up: one column per type, rows = default and the two colourways
w, h = cols[0][1][0].width, cols[0][1][0].height
head = 70
sheet = Image.new('RGB', (w * len(cols), head + h * 3), BG)
d = ImageDraw.Draw(sheet)
for i, (label, tiles) in enumerate(cols):
    for r, t in enumerate(tiles):
        sheet.paste(t, (i * w, head + r * h))
    lines = ['']
    for word in label.split():
        if lines[-1] and len(lines[-1]) + 1 + len(word) > 17:
            lines.append(word)
        else:
            lines[-1] = (lines[-1] + ' ' + word).strip()
    for k, line in enumerate(lines[:2]):
        d.text((i * w + 10, 6 + k * 30), line, fill=(30, 30, 34), font=font(24))
sheet.save(lineup_path)
manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding='utf-8')
print('line-up', lineup_path, sheet.size, '| manifest', manifest_path, len(manifest['types']), 'types')
