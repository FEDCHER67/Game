"""Compose the requested sheet from actual Blender renders, without retouching."""
from pathlib import Path
import sys,json
from PIL import Image,ImageDraw,ImageFont,ImageOps
R=Path('C:/Dev/Game/Working/Reviews/Operations/organs_v03');OLD=R/'tiles'
revision=sys.argv[sys.argv.index('--revision')+1] if '--revision' in sys.argv else 'v03b'
four=revision=='v03c';T=R/('G38_v03c_tiles' if four else 'G38_tiles');count=4 if four else 5
V=json.loads((R/'G38_work'/('validation_four_final.json' if four else 'validation_final.json')).read_text())
W=2304;PAD=32;GAP=24
font=lambda n:ImageFont.load_default(size=n)
canvas=Image.new('RGB',(W,5900),'#15222c');d=ImageDraw.Draw(canvas)
d.text((PAD,28),f'G38  /  RIBCAGE {revision}',font=font(55),fill='#f3f1e8')
d.text((PAD,98),('4 rib pairs  |  5,840 triangles  |  46 draft UCX parts  |  1:1 scale' if four else '5 rib pairs  |  5,552 triangles  |  54 convex UCX parts  |  1:1 scale'),font=font(30),fill='#b4c7cf')
d.rounded_rectangle((PAD,150,W-PAD,230),radius=12,fill='#70432e')
d.text((PAD+22,173),('VISUAL REVISION / COLLISIONS BLOCKED - coarse hull fit and fixed body/neck. See G38_REPORT.md.' if four else 'BLOCKED REVIEW CANDIDATE - fixed body / neck contacts remain. See G38_REPORT.md.'),font=font(29),fill='#fff1df')
def tile(path,x,y,w,h,title,detail=''):
    d.rectangle((x,y,x+w,y+h+94),fill='#243642')
    im=Image.open(path).convert('RGB');im=ImageOps.contain(im,(w,h),Image.Resampling.LANCZOS)
    canvas.paste(im,(x+(w-im.width)//2,y+(h-im.height)//2))
    d.text((x+18,y+h+12),title,font=font(29),fill='#faf4e5')
    if detail:d.text((x+18,y+h+51),detail,font=font(21),fill='#b3c7d0')
half=(W-2*PAD-GAP)//2;y=262
tile(OLD/'05_front_open_torso.png',PAD,y,half,1288,'BEFORE / approved v03 - 9 pairs','Source review render; fixed organs and body.')
tile(T/'05_front_open_torso.png',PAD+half+GAP,y,half,1288,f'AFTER / {revision} - {count} thicker pairs',('Smooth curves; all four pairs join the sternum.' if four else 'Same material colours; fifth pair has short floating ends.'))
y+=1410
third=(W-2*PAD-2*GAP)//3
tile(T/'06_side_open_torso.png',PAD,y,third,700,'SIDE / open torso','Fixed organ layout preserved.')
tile(T/'01_operation_camera.png',PAD+third+GAP,y,third,700,'TOP / TABLE_REST','Actual game-camera direction.')
tile(T/('00_reference_front.png' if four else '04_chest_xray.png'),PAD+2*(third+GAP),y,third,700,('FRONT / unchanged organs' if four else 'TOP / chest reveal'),('Reference-inspired curves; original anatomy.' if four else 'Review-only body transparency.'))
y+=820
tile(T/'11_ribcage_closed.png',PAD,y,half,940,'RIBCAGE ALONE / closed','Same overall bounds; original spine and sternum.')
tile(T/'12_ribcage_open.png',PAD+half+GAP,y,half,940,'RIBCAGE ALONE / hinges open 35 degrees',('Render meshes clear organs; collider checks still fail.' if four else 'Minimum organ clearance: 11.58 mm.'))
y+=1060
tile(T/'20_colliders_front.png',PAD,y,half,830,'COLLIDERS / front','Triangulated UCX wire over translucent render meshes.')
tile(T/'21_colliders_side.png',PAD+half+GAP,y,half,830,'COLLIDERS / side',('4 parts/rib meet convexity; surface fit FAILS.' if four else '21-51 vertices per part; smallest rib gap 9.73 mm.'))
y+=950
quarter=(W-2*PAD-3*GAP)//4
items=[('22_neck_before_front.png','NECK / front, retained',f'v03 = delivered {revision}.'),('23_neck_before_side.png','NECK / side, retained','Fixed head shown translucent.'),('24_neck_trim_study_front.png','TRIM STUDY / front','84 mm removed; NOT applied.'),('25_neck_trim_study_side.png','TRIM STUDY / side','70% loss changes overall look.')]
for i,(name,title,detail) in enumerate(items):tile(T/name,PAD+i*(quarter+GAP),y,quarter,530,title,detail)
y+=645
d.text((PAD,y),('Mesh/transform/material preservation: PASS. Convex hull fit and organ/body clearance: FAIL. See detailed tables.' if four else 'Fit bounds: outside <= 1.50 mm; uncovered surface <= 0.84 mm. 20 / 20 filtered sphere sweeps pass.'),font=font(26),fill='#d3e6d7')
d.text((PAD,y+42),'Body/neck clearance FAILS. Unity runtime NOT RUN. Source v03, patient, organs, pivots and Assets remain unchanged.',font=font(25),fill='#f0c3ab')
out=R/f'organs_{revision}_ribs_sheet.png';assert not out.exists()
canvas.crop((0,0,W,y+98)).save(out)
preview=R/f'organs_{revision}_ribs_sheet_preview.png'
im=Image.open(out);im.thumbnail((1152,4000),Image.Resampling.LANCZOS);im.save(preview)
print(out,Image.open(out).size)
