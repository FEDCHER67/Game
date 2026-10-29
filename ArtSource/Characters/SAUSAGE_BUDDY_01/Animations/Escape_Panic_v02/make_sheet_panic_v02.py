"""Frame strips and the contact sheet for Escape_Panic_v02 (system Python + Pillow). Never overwrites.

  python make_sheet_panic_v02.py strip <stem>     -> Previews/strips/<stem>_strip.png   (all rendered frames, 10 per row)
  python make_sheet_panic_v02.py sheet            -> Previews/Escape_Panic_v02_contact_sheet.png (one row per clip, key stills)
Input frames: Previews/strips/<stem>/<view>/fNNN_t<time>.png and Previews/stills/<stem>/<view>/sNNN_t<time>.png
as written by build_esc_panic_v02.py --strip / --stills. Row labels come from the *_authoring.json files.
"""
import sys, re, json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
PREV = HERE / 'Previews'
ORDER = ['Esc_Lie_TugArmR_Loop_Panic_v02', 'Esc_Lie_TugArmL_Loop_Panic_v02',
         'Esc_Lie_UnbuckleArmR_ByL_Panic_v02', 'Esc_Lie_UnbuckleArmL_ByR_Panic_v02',
         'Esc_SitUp_Panic_v02', 'Esc_Sit_UnbuckleLegL_Panic_v02', 'Esc_Sit_UnbuckleLegR_Panic_v02',
         'Esc_Sit_UnbuckleLegsBoth_Panic_v02', 'Esc_SwingOff_R_Panic_v02', 'Esc_SwingOff_L_Panic_v02',
         'Esc_HopRun_R_BellyClutch_v02', 'Esc_HopRun_L_BellyClutch_v02', 'Esc_Run_BellyClutch_Loop_Panic_v02',
         'Esc_Stumble_Off_R_Panic_v02', 'Esc_Stumble_Off_L_Panic_v02']
try:
    FB = ImageFont.truetype('segoeuib.ttf', 15)
    FN = ImageFont.truetype('segoeui.ttf', 13)
    FT = ImageFont.truetype('segoeuib.ttf', 20)
except OSError:
    FB = FN = FT = ImageFont.load_default()
BG = (33, 37, 44)


def frames_of(root, stem):
    d = root / stem
    vdirs = sorted(p for p in d.iterdir() if p.is_dir())
    files = sorted(vdirs[0].glob('*.png'))
    return vdirs[0].name, [(float(re.search(r'_t(\d+\.\d+)', p.stem).group(1)), p) for p in files]


def strip(stem, S=200, cols=10):
    out = PREV / 'strips' / (stem + '_strip.png')
    if out.exists():
        sys.exit('Refusing overwrite: %s' % out)
    view, fr = frames_of(PREV / 'strips', stem)
    rows = (len(fr) + cols - 1) // cols
    LH = 18
    img = Image.new('RGB', (cols * S, 40 + rows * (S + LH)), BG)
    d = ImageDraw.Draw(img)
    j = json.loads((HERE / (stem + '_authoring.json')).read_text(encoding='utf-8'))
    d.text((8, 8), '%s  %.2f s  %s -> %s  (%s view, every %d frames)' % (stem, j['duration_s'], j['start_pose_key'], j['end_pose_key'], view,
                                                                         max(1, round((fr[1][0] - fr[0][0]) * 30)) if len(fr) > 1 else 1),
           fill='white', font=FB)
    for k, (t, p) in enumerate(fr):
        x, y = (k % cols) * S, 40 + (k // cols) * (S + LH)
        img.paste(Image.open(p).convert('RGB').resize((S, S), Image.LANCZOS), (x, y))
        d.text((x + 4, y + S + 1), '%.2f s  f%d' % (t, round(1 + t * 30)), fill=(220, 220, 220), font=FN)
    img.save(out)
    print(out)


def sheet(S=200, cols=8):
    out = PREV / 'Escape_Panic_v02_contact_sheet.png'
    if out.exists():
        sys.exit('Refusing overwrite: %s' % out)
    stems = [s for s in ORDER if (PREV / 'stills' / s).exists()]
    LW, GAP = 330, 20
    H = 50 + len(stems) * (S + GAP)
    img = Image.new('RGB', (LW + cols * S, H), BG)
    d = ImageDraw.Draw(img)
    d.text((10, 12), 'VOLUNTEERS ONLY - Escape_Panic_v02: panic variants of the table escape (K10), %d clips, 30 fps. '
           'Contacts / StrapOpen times = v01.' % len(stems), fill='white', font=FT)
    for r, stem in enumerate(stems):
        y = 50 + r * (S + GAP)
        j = json.loads((HERE / (stem + '_authoring.json')).read_text(encoding='utf-8'))
        lines = [stem, '%.2f s (v01 %s s, %s)%s  %s -> %s' % (j['duration_s'], j.get('v01_duration_s'),
                                                              ('%+.0f%%' % j['duration_vs_v01_pct']) if j.get('duration_vs_v01_pct') is not None else 'new',
                                                              '  loop' if j['loop'] else '', j['start_pose_key'], j['end_pose_key'])]
        for e in j['events']:
            if e['name'] in ('Grab', 'StrapOpen'):
                lines.append('%s %s %s @ %.2f s (f%.1f)' % (e['name'], e.get('hand', ''), e['strap'].replace('STRAP_', ''), e['t'], e['frame']))
        lines = lines[:9]
        for i, ln in enumerate(lines):
            d.text((8, y + 2 + i * 19), ln, fill='white' if i == 0 else (200, 210, 220), font=FB if i == 0 else FN)
        view, fr = frames_of(PREV / 'stills', stem)
        for k, (t, p) in enumerate(fr[:cols]):
            x = LW + k * S
            img.paste(Image.open(p).convert('RGB').resize((S, S), Image.LANCZOS), (x, y))
            d.text((x + 4, y + S + 1), '%.2f s (%s)' % (t, view), fill=(220, 220, 220), font=FN)
    img.save(out)
    print(out)


if __name__ == '__main__':
    if sys.argv[1] == 'strip':
        for st in sys.argv[2:]:
            strip(st)
    else:
        sheet()
