"""Contact sheet using actual Blender renders; accepted v03c visual tiles reused."""
import json
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont,ImageOps
R=Path('C:/Dev/Game/Working/Reviews/Operations/organs_v03');C=R/'G38_v03c_tiles';D=R/'G38_v03d_tiles';W=R/'G38_work'
v=json.loads((W/'validation_v03d_01.json').read_text());f=json.loads((W/'fit_v03d_final.json').read_text())
out=R/'organs_v03d_ribs_sheet.png';preview=R/'organs_v03d_ribs_sheet_preview.png'
assert not out.exists() and not preview.exists()
width=2304;pad=32;gap=24;half=(width-2*pad-gap)//2;third=(width-2*pad-2*gap)//3
canvas=Image.new('RGB',(width,6000),'#15222c');draw=ImageDraw.Draw(canvas)
font=lambda size:ImageFont.load_default(size=size)
draw.text((pad,24),'G38 / v03d COLLIDERS',font=font(54),fill='#f4f2e9')
draw.text((pad,90),'Accepted v03c visual unchanged / 4 pairs / 5,840 render triangles / 96 UCX / 1:1 scale',font=font(30),fill='#b4c7cf')
draw.rounded_rectangle((pad,140,width-pad,218),radius=12,fill='#234e3c')
draw.text((pad+20,163),'BLENDER VALIDATION PASS / body-neck overlap accepted / Unity integration NOT RUN',font=font(30),fill='#e5f5e7')
def tile(path,x,y,w,h,title,detail):
    draw.rectangle((x,y,x+w,y+h+92),fill='#243642')
    im=ImageOps.contain(Image.open(path).convert('RGB'),(w,h),Image.Resampling.LANCZOS)
    canvas.paste(im,(x+(w-im.width)//2,y+(h-im.height)//2))
    draw.text((x+18,y+h+12),title,font=font(29),fill='#faf4e5')
    draw.text((x+18,y+h+52),detail,font=font(22),fill='#bdd0d8')
y=246
tile(R/'tiles/05_front_open_torso.png',pad,y,half,1000,'ORIGINAL v03 / 9 pairs','Original source review. All organs remain fixed.')
tile(C/'05_front_open_torso.png',pad+half+gap,y,half,1000,'ACCEPTED v03c = v03d / 4 pairs','Identical render geometry, materials and transforms.')
y+=1116
tile(C/'11_ribcage_closed.png',pad,y,half,820,'ACCEPTED RIBCAGE / closed','Original sternum and spine retained.')
tile(C/'12_ribcage_open.png',pad+half+gap,y,half,820,'ACCEPTED RIBCAGE / opened 35 degrees','Hinge positions and BREAK targets unchanged.')
y+=936
tile(C/'06_side_open_torso.png',pad,y,third,580,'SIDE / accepted visual','No render edits in v03d.')
tile(C/'01_operation_camera.png',pad+third+gap,y,third,580,'TOP / TABLE_REST','20 filtered sphere sweeps: PASS.')
tile(C/'00_reference_front.png',pad+2*(third+gap),y,third,580,'FRONT / fixed organs','Liver and kidneys stay lowered.')
y+=696
tile(D/'20_colliders_front.png',pad,y,half,830,'v03d UCX / front, closed','10 short convex parts per rib; 8 per sternum half.')
tile(D/'21_colliders_side.png',pad+half+gap,y,half,830,'v03d UCX / side, closed',f"Nearest organ: {v['summary']['min_organ_clearance_closed_mm']:.3f} mm.")
y+=946
tile(D/'22_colliders_open35_front.png',pad,y,half,790,'v03d UCX / front, open 35 degrees','All colliders follow their existing hinge parents.')
tile(D/'23_colliders_open35_side.png',pad+half+gap,y,half,790,'v03d UCX / side, open 35 degrees',f"Nearest organ: {v['summary']['min_organ_clearance_open_mm']:.3f} mm.")
y+=906
draw.text((pad,y),f"Outside bound <= {f['summary']['maximum_outside_bound_mm']:.4f} mm / Uncovered bound <= {f['summary']['maximum_uncovered_bound_mm']:.4f} mm / Minimum rib gap 12.175 mm",font=font(27),fill='#d3ebd9')
draw.text((pad,y+42),'45 non-UCX objects + all 17 materials exact. Full tables, 20 probe hits and file hashes: G38_REPORT.md.',font=font(26),fill='#bdd0d8')
canvas=canvas.crop((0,0,width,y+95));canvas.save(out)
canvas.thumbnail((1152,4000),Image.Resampling.LANCZOS);canvas.save(preview)
print('V03D_SHEET',str(out),Image.open(out).size)
