from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
import json
ROOT=Path('C:/Dev/Game')
OUT=ROOT/'ArtSource/Props/OPERATIONS_STAGE1_v01'
SRC=OUT/'Previews/v02'
DEST=ROOT/'Working/Reviews/Operations/props_stage1_v01.png'
assert not DEST.exists(), 'Do not overwrite an existing review sheet.'
DEST.parent.mkdir(parents=True,exist_ok=True)
FONT='C:/Windows/Fonts/segoeui.ttf'; BOLD='C:/Windows/Fonts/segoeuib.ttf'
def font(size,bold=False): return ImageFont.truetype(BOLD if bold else FONT,size)
W=3000; margin=36; gap=24; pw=960; ih=800; cap=92; top=170
H=top+2*(ih+cap)+gap+145
sheet=Image.new('RGB',(W,H),(25,35,41)); d=ImageDraw.Draw(sheet)
cream=(239,236,222); muted=(164,187,198); accent=(210,184,136)
d.text((margin,25),'VOLUNTEERS ONLY',font=font(25,True),fill=muted)
d.text((margin,62),'OPERATIONS / STAGE 1',font=font(53,True),fill=cream)
d.text((margin,126),'G26  /  ASTRA + COZY  /  BLENDER PREVIEW  /  15 OCT 2026',font=font(22),fill=muted)
d.rounded_rectangle((2470,45,2964,115),radius=10,fill=(54,66,70),outline=accent,width=2)
d.text((2498,63),'AWAITING FEDYA’S OK',font=font(28,True),fill=cream)
panels=[
 ('01_patient_closed','01  /  PATIENT FIT','Sausage Buddy • all five restraints fastened'),
 ('02_table_open','02  /  FIVE RESTRAINTS — OPEN','Independent mount hinges • table geometry retained'),
 ('03_table_closed','03  /  FIVE RESTRAINTS — CLOSED','1 torso   2 left arm   3 right arm   4 left leg   5 right leg'),
 ('04_tray','04  /  INSTRUMENT TRAY','Syringe • scalpel • knife • one organ   |   original tool scale'),
 ('05_incisions','05  /  PREPARED BELLY OPENINGS','Separate liver / left kidney / right kidney • abstract recesses'),
 ('06_fixed_camera','06  /  APPROXIMATE FIXED TABLE CAMERA','Whole patient + reachable tray • shared abdomen zone'),
]
positions=json.loads((SRC/'label_positions.json').read_text())
def tag(im,point,label,number=False):
 dd=ImageDraw.Draw(im); x,y=point
 ff=font(21 if number else 20,True)
 box=dd.textbbox((0,0),label,font=ff); tw=box[2]; th=box[3]
 bw=40 if number else tw+22; bh=38
 x=max(4,min(im.width-bw-4,x-bw/2)); y=max(4,min(im.height-bh-4,y-bh/2))
 dd.rounded_rectangle((x,y,x+bw,y+bh),radius=10,fill=(29,40,46),outline=(224,219,198),width=2)
 dd.text((x+(bw-tw)/2,y+4),label,font=ff,fill=(246,240,223))
for idx,(key,title,sub) in enumerate(panels):
 x=margin+(idx%3)*(pw+gap); y=top+(idx//3)*(ih+cap+gap)
 im=Image.open(SRC/(key+'.png')).convert('RGB').resize((pw,ih),Image.Resampling.LANCZOS)
 if key in ['02_table_open','03_table_closed']:
  mapping={'STRAP_TORSO':'1','STRAP_L_ARM':'2','STRAP_R_ARM':'3','STRAP_L_LEG':'4','STRAP_R_LEG':'5'}
  for name,xy in positions[key].items():
   xx=xy[0]*pw; yy=(1-xy[1])*ih
   # Park the number next to the stationary hinge, leaving all band geometry visible.
   xx+=34 if name in ['STRAP_L_ARM','STRAP_L_LEG','STRAP_TORSO'] else -34
   yy-=32
   tag(im,(xx,yy),mapping[name],True)
 if key=='05_incisions':
  for name,xy in positions[key].items():
   label='LIVER' if name=='INCISION_LIVER' else 'KIDNEY L' if name.endswith('_L') else 'KIDNEY R'
   px,py=xy[0]*pw,(1-xy[1])*ih
   lx,ly=(px+210,py-100) if name=='INCISION_LIVER' else (px+195,py+112) if name.endswith('_L') else (px-190,py-120)
   dd=ImageDraw.Draw(im); dd.line((px,py,lx,ly),fill=(239,236,222),width=2); dd.ellipse((px-4,py-4,px+4,py+4),fill=(239,236,222))
   tag(im,(lx,ly),label)
 sheet.paste(im,(x,y))
 d.rectangle((x,y+ih,x+pw,y+ih+cap),fill=(37,48,54))
 d.text((x+18,y+ih+13),title,font=font(25,True),fill=cream)
 d.text((x+18,y+ih+52),sub,font=font(20),fill=muted)
footer=H-115
d.line((margin,footer-18,W-margin,footer-18),fill=(77,96,105),width=2)
d.text((margin,footer),'2,932 new triangles  /  metres  /  independent hinges  /  tray underside pivot  /  packed Blender source',font=font(25,True),fill=cream)
d.text((margin,footer+42),'Review fixture only: patient pose + lifted shirt + tray support. Original table/NPC/tool files are unchanged. No Unity import.',font=font(23),fill=muted)
sheet.save(DEST)
print(DEST)
