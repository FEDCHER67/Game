"""One poplar comparison sheet from actual Blender renders; no model resizing."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import json

ROOT = Path(__file__).parent
OUT = ROOT.parents[3] / 'Working/Reviews/Trees/poplars_v04_04.png'
assert not OUT.exists(), OUT
data = json.loads((ROOT / 'validation_v04_04.json').read_text())
checks = json.loads((ROOT / 'fbx_roundtrip_v04_04.json').read_text())
assert checks['status'] == 'PASS'
BG, INK, MUTED, RULE, ACCENT = '#EAEDE4', '#233D2E', '#57665A', '#BBC6B7', '#DAE3D3'
def font(n,bold=False):
    return ImageFont.truetype('C:/Windows/Fonts/' + ('segoeuib.ttf' if bold else 'segoeui.ttf'), n)

W,H = 4000,2860
sheet = Image.new('RGB',(W,H),BG)
d = ImageDraw.Draw(sheet)
def centered(text, x, y, size=30, bold=False, color=INK):
    f=font(size,bold)
    d.text((x-d.textlength(text,font=f)/2,y),text,font=f,fill=color)

d.text((70,25),'POPLARS / v04_04',font=font(62,True),fill=INK)
d.text((70,103),'Wider crowns + more leaf clusters  •  Same heights, leaf shapes and palette  •  Shared Hamlet daylight',font=font(29),fill=MUTED)
scale = .9375
raw = Image.open(ROOT / 'Preview/Poplars_lineup_v04_04.png').convert('RGB')
width,height = round(raw.width*scale),round(raw.height*scale)
left,top=(W-width)//2,225
sheet.paste(raw.resize((width,height),Image.Resampling.LANCZOS),(left,top))
centers=[left+(x+19.5)*93.75 for x in data['preview']['positions_x_m']]
centered('CURRENT i05',centers[0],165,31,True)
centered('v04_03  /  APPROVED BASELINE',centers[2],165,31,True)
centered('v04_04  /  POPLAR CANDIDATE',centers[5],165,31,True)
for split in ((centers[0]+centers[1])/2,(centers[3]+centers[4])/2):
    d.line((split,160,split,2110),fill=RULE,width=2)
labels=[('Current i05',data['current_i05']['height_m'],data['current_i05']['triangles'])]
labels += [(f'Poplar {letter} / v04_03',v['height_m'],5836) for letter,v in zip('ABC',data['variants'])]
labels += [(f'Poplar {letter} / v04_04',v['height_m'],v['lod_triangles'][0]) for letter,v in zip('ABC',data['variants'])]
for x,(label,h,tris) in zip(centers,labels):
    y=top+height+16
    centered(label,x,y,29,True)
    centered(f'{h:.2f} m',x,y+44,31)
    centered(f'LOD0: {tris:,} tris',x,y+87,28,color=MUTED)

y=2125
d.line((70,y,W-70,y),fill=RULE,width=2)
d.text((70,y+16),'POPLAR A / v04_04 FOLIAGE CLOSE-UP',font=font(30,True),fill=INK)
detail=Image.open(ROOT / 'Preview/Poplar_A_detail_v04_04.png').convert('RGB')
detail=detail.resize((880,640),Image.Resampling.LANCZOS)
sheet.paste(detail,(70,y+65))
tx=1030
d.text((tx,y+20),'CROWN WIDTH +22.5%',font=font(41,True),fill=INK)
d.text((tx,y+83),'Widened along the leafy column, with a gentle middle fullness.',font=font(29),fill=MUTED)
for i,spec in enumerate(data['variants']):
    x=tx+i*950
    d.rounded_rectangle((x,y+145,x+895,y+350),radius=12,fill=ACCENT)
    d.text((x+28,y+164),spec['variant'].replace('_',' '),font=font(34,True),fill=INK)
    d.text((x+28,y+222),f"{spec['crown_width_before_m']:.2f} m  →  {spec['crown_width_after_m']:.2f} m",font=font(43,True),fill=INK)
    d.text((x+28,y+289),'Maximum horizontal crown width',font=font(26),fill=MUTED)
for j,line in enumerate([
    'Each variant: 48 → 54 leaf clusters (+12.5%)  /  576 → 648 individual leaves.',
    'LOD0 / LOD1 / LOD2: 6,496 / 3,716 / 2,378 triangles. All nine exports checked.',
    'Same lower trunks, base pivots, metres, capsule settings and shared V19Wind materials.',
    'Lineup: 93.75 px/m, matching the previous sheet. Close-up uses a separate scale.',
    'Apple, palm and bush v04_03 unchanged. Blender-only candidate for Fedya’s review.'
]):
    d.text((tx,y+389+j*58),line,font=font(29),fill=MUTED)
sheet.save(OUT)
(ROOT / 'sheet_manifest_v04_04.json').write_text(json.dumps(dict(file=str(OUT), dimensions_px=[W,H],
    lineup_order=[l[0] for l in labels], common_pixels_per_m=93.75,
    lighting='Unmodified v04_03 Hamlet studio, Cycles, AgX Medium High Contrast, exposure +0.3',
    source_images=['Preview/Poplars_lineup_v04_04.png','Preview/Poplar_A_detail_v04_04.png'],
    closeups=1, individual_model_resizing=False, unity_capture=False),indent=2))
print('SHEET_COMPLETE',OUT,sheet.size)
