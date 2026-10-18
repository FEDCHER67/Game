"""Contact sheet for Escape_v01 (system Python + Pillow): one row per clip, key-pose stills.

  python make_sheet_esc.py <stills_root> <out.png>
<stills_root>/<ClipName>/<view>/sNN_t<time>.png as written by build_esc_v01.py --stills.
Row labels come from the clips' *_authoring.json next to this script. Refuses to overwrite.
"""
import sys, re, json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
ROWS = [  # (build name, stem)
    ('UnbuckleArmR_ByL', 'Esc_Lie_UnbuckleArmR_ByL_v01'), ('UnbuckleArmL_ByR', 'Esc_Lie_UnbuckleArmL_ByR_v01'),
    ('TugArmR', 'Esc_Lie_TugArmR_Loop_v01'), ('TugArmL', 'Esc_Lie_TugArmL_Loop_v01'),
    ('SlumpLieReachR', 'Esc_Slump_LieReachR_v01'), ('SlumpLieReachL', 'Esc_Slump_LieReachL_v01'),
    ('SitUp', 'Esc_SitUp_v01'), ('UnbuckleLegL', 'Esc_Sit_UnbuckleLegL_v01'), ('UnbuckleLegR', 'Esc_Sit_UnbuckleLegR_v01'),
    ('UnbuckleLegsBoth', 'Esc_Sit_UnbuckleLegsBoth_v01'), ('TugLegs', 'Esc_Sit_TugLegs_Loop_v01'),
    ('SlumpSit', 'Esc_Slump_Sit_v01'), ('SwingOff', 'Esc_SwingOff_R_v01'), ('HopRun', 'Esc_HopRun_R_v01'),
]
src, out = Path(sys.argv[1]), Path(sys.argv[2])
if out.exists():
    sys.exit('Refusing overwrite: %s' % out)
try:
    F = ImageFont.truetype('segoeuib.ttf', 15)
    f = ImageFont.truetype('segoeui.ttf', 13)
    T = ImageFont.truetype('segoeuib.ttf', 20)
except OSError:
    F = f = T = ImageFont.load_default()
S, LW, GAP = 220, 300, 22
cols = 8
H = 54 + len(ROWS) * (S + GAP)
sheet = Image.new('RGB', (LW + cols * S, H), (33, 37, 44))
d = ImageDraw.Draw(sheet)
d.text((12, 10), 'VOLUNTEERS ONLY - patient escape set Escape_v01 (14 clips, 30 fps). 4 limb straps, torso strap removed. '
       'Strap state shown as authored (grey band = strap; open = flipped outward).', fill='white', font=T)
for r, (name, stem) in enumerate(ROWS):
    y = 54 + r * (S + GAP)
    j = json.loads((HERE / (stem + '_authoring.json')).read_text(encoding='utf-8'))
    ev = [e for e in j['events'] if e['name'] == 'StrapOpen']
    lines = [stem, '%.2f s  %s%s -> %s' % (j['duration_s'], 'loop  ' if j['loop'] else '', j['start_pose_key'], j['end_pose_key']),
             'closed: ' + (', '.join(x.replace('STRAP_', '') for x in j['preconditions']['closed']) or '-'),
             'open: ' + (', '.join(x.replace('STRAP_', '') for x in j['preconditions']['open']) or '-'),
             'any: ' + (', '.join(x.replace('STRAP_', '') for x in j['preconditions']['any']) or '-')]
    lines += ['OPEN %s @ %.2f s (%.2f)' % (e['strap'].replace('STRAP_', ''), e['t'], e['norm']) for e in ev]
    for i, ln in enumerate(lines):
        d.text((10, y + 4 + i * 19), ln, fill='white' if i == 0 else (200, 210, 220), font=F if i == 0 else f)
    vdirs = [p for p in (src / name).iterdir() if p.is_dir()]
    files = sorted(vdirs[0].glob('*.png'))
    for k, p in enumerate(files[:cols]):
        x = LW + k * S
        sheet.paste(Image.open(p).convert('RGB').resize((S, S), Image.LANCZOS), (x, y))
        m = re.search(r't(\d+\.\d+)', p.stem)
        d.rectangle((x, y + S, x + S, y + S + GAP - 2), fill=(33, 37, 44))
        d.text((x + 6, y + S + 2), '%s s  (%s)' % (m.group(1), vdirs[0].name), fill=(220, 220, 220), font=f)
sheet.save(out)
print(out)
