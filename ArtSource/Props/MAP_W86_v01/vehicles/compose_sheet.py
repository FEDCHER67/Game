"""Contact sheets for the M1 vehicles (system Python + Pillow).

python compose_sheet.py <tiles_dir_A> <tiles_dir_variants> <models_json> <out_sheet.jpg> <out_variants.jpg>
Tiles: <Name>.png (LOD0, variant A) and <Name>_B.png / <Name>_C.png from render_tiles.py.
"""
import json, sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ORDER = ['MW86_Tank', 'MW86_AirDefence', 'MW86_MissileSilo', 'MW86_MilJeep', 'MW86_MilTruck', 'MW86_Helicopter', 'MW86_PatrolBoat',
         'MW86_Yacht_Motor22', 'MW86_Yacht_Cruiser10', 'MW86_Boat_KeelBlocks', 'MW86_Rowboat_Upturned', 'MW86_JetSki', 'MW86_SUP',
         'MW86_MixerTruck', 'MW86_DumpTruck', 'MW86_WheelLoader', 'MW86_VanOnJacks', 'MW86_ReachStacker', 'MW86_Forklift',
         'MW86_TruckContainer', 'MW86_FoodTruck', 'MW86_RailWagon_Base1', 'MW86_SUV_Black']


def font(sz, bold=False):
    for f in (('C:/Windows/Fonts/segoeuib.ttf' if bold else 'C:/Windows/Fonts/segoeui.ttf'), 'C:/Windows/Fonts/arial.ttf'):
        try:
            return ImageFont.truetype(f, sz)
        except OSError:
            pass
    return ImageFont.load_default()


def main(tiles, vtiles, models_json, out_a, out_v):
    doc = json.load(open(models_json, encoding='utf-8'))
    kinds_of = {}
    for k, v in doc['kinds'].items():
        ms = v['model'] if isinstance(v['model'], list) else [v['model']]
        for mname in ms:
            kinds_of.setdefault(mname, []).append(f"{k} x{len(v['instances'])}")
    kinds_of.setdefault('MW86_RailWagon_Base1', []).append('rail_wagon_base1 (building 01_B01)')
    TW, TH, LH, COLS = 560, 420, 64, 6
    rows = (len(ORDER) + COLS - 1) // COLS
    W, H = TW * COLS, 78 + rows * (TH + LH)
    sheet = Image.new('RGB', (W, H), (246, 244, 238))
    d = ImageDraw.Draw(sheet)
    d.text((20, 14), 'M1 - vehicles & big machines for the W85/W86 map (replace the grey concrete boxes)  |  LOD0, colour variant A, grey block = 1.75 m person',
           fill=(30, 30, 34), font=font(30, True))
    f1, f2 = font(22, True), font(17)
    for i, name in enumerate(ORDER):
        x, y = (i % COLS) * TW, 78 + (i // COLS) * (TH + LH)
        im = Image.open(Path(tiles) / f'{name}.png').convert('RGB').resize((TW, TH), Image.LANCZOS)
        sheet.paste(im, (x, y))
        m = doc['models'][name]
        sz = m['size_unity_xyz_m']
        d.rectangle([x, y + TH, x + TW - 1, y + TH + LH - 1], fill=(255, 255, 255))
        d.text((x + 10, y + TH + 4), name.replace('MW86_', ''), fill=(20, 20, 24), font=f1)
        d.text((x + 10, y + TH + 34), f"{', '.join(kinds_of.get(name, ['-']))}  |  {m['lod']['LOD0_tris']}/{m['lod']['LOD1_tris']} tris  |  "
               f"{sz[0]:.1f} x {sz[2]:.1f} x {sz[1]:.1f} m", fill=(70, 70, 78), font=f2)
        d.rectangle([x, y, x + TW - 1, y + TH + LH - 1], outline=(200, 198, 190))
    sheet.save(out_a, quality=90)
    # variants B / C
    VW, VH = 400, 300
    COLS = 4
    rows = (len(ORDER) + COLS - 1) // COLS
    W, H = COLS * 2 * VW, 70 + rows * (VH + 40)
    vs = Image.new('RGB', (W, H), (246, 244, 238))
    d = ImageDraw.Draw(vs)
    d.text((20, 12), 'M1 colour variants B | C (same mesh, only the family atlas texture changes)', fill=(30, 30, 34), font=font(28, True))
    for i, name in enumerate(ORDER):
        x, y = (i % COLS) * 2 * VW, 70 + (i // COLS) * (VH + 40)
        for j, v in enumerate('BC'):
            p = Path(vtiles) / f'{name}_{v}.png'
            if p.exists():
                vs.paste(Image.open(p).convert('RGB').resize((VW, VH), Image.LANCZOS), (x + j * VW, y))
        d.rectangle([x, y + VH, x + 2 * VW - 1, y + VH + 39], fill=(255, 255, 255))
        d.text((x + 10, y + VH + 6), f"{name.replace('MW86_', '')}   B | C", fill=(20, 20, 24), font=font(20, True))
        d.rectangle([x, y, x + 2 * VW - 1, y + VH + 39], outline=(200, 198, 190))
    vs.save(out_v, quality=88)
    print('written', out_a, out_v)


if __name__ == '__main__':
    main(*sys.argv[1:6])
