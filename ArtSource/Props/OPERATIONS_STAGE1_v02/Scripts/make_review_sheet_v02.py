from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import json
base=Path('C:/Dev/Game/ArtSource/Props/OPERATIONS_STAGE1_v02');src=base/'Previews/v02_review';dest=Path('C:/Dev/Game/Working/Reviews/Operations/props_stage1_v02.png');assert not dest.exists(),str(dest)
font='C:/Windows/Fonts/segoeui.ttf';bold='C:/Windows/Fonts/segoeuib.ttf'
def f(n,b=False):return ImageFont.truetype(bold if b else font,n)
W=3000;H=2910;im=Image.new('RGB',(W,H),'#18232a');d=ImageDraw.Draw(im)
d.text((36,22),'G26  /  OPERATIONS STAGE 1',font=f(46,True),fill='#f4eee1')
d.text((36,82),'v02  •  Approved bare PATIENT fixture  •  Astra palette  •  Blender review for Fedya',font=f(27),fill='#bfccd0')
panels=[('01_closed','01  FIVE STRAPS / CLOSED','Normal patient • fixed mounts + independent moving bands'),('02_open','02  FIVE STRAPS / OPEN','open = 1 • hinge pivots stay at the mounts'),('05_fixed','03  FIXED TABLE CAMERA','G25 camera framing • three distinct belly openings'),('03_incisions_open','04  INCISIONS / OPEN','Crosses = projected source markers • exact origin + normal'),('04_incisions_closed','05  INCISIONS / CLOSED','Individual skin covers • subtle site guides'),('06_girth_MUSCLE105','06  MUSCLE + SCALE CHECK','muscle 1.7 • scale 1.05 • all five straps closed'),('06_girth_THIN','07  GIRTH / THIN','girth -1 • thin 1.0 • scale 1.0'),('06_girth_NORMAL','08  GIRTH / NORMAL','girth 0 • normal body • scale 1.0'),('06_girth_FAT','09  GIRTH / FAT','girth +1 • belly 1.0 • scale 1.0')]
proj=json.loads((src/'marker_projection.json').read_text());pw=960;ph=800;step=982
for idx,(name,title,caption) in enumerate(panels):
 col=idx%3;row=idx//3;x=36+col*step;y=148+row*890
 tile=Image.open(src/(name+'.png')).convert('RGB').resize((pw,ph),Image.Resampling.LANCZOS);im.paste(tile,(x,y))
 if name in ['03_incisions_open','04_incisions_closed']:
  for key,(px,py) in proj.items():
   cx=x+px*pw;cy=y+py*ph;color='#e9f8f6';d.line((cx-7,cy,cx+7,cy),fill=color,width=2);d.line((cx,cy-7,cx,cy+7),fill=color,width=2)
   label={'INC_KIDNEY_L':'KIDNEY L','INC_KIDNEY_R':'KIDNEY R','INC_LIVER':'LIVER'}[key]
   tx=cx+14;ty=cy-13;bb=d.textbbox((tx,ty),label,font=f(18,True));d.rounded_rectangle((bb[0]-5,bb[1]-4,bb[2]+5,bb[3]+4),radius=4,fill='#263a40');d.text((tx,ty),label,font=f(18,True),fill='#f0f5ef')
 d.text((x,y+811),title,font=f(27,True),fill='#f4eee1');d.text((x,y+848),caption,font=f(21),fill='#bfccd0')
d.line((36,2830,W-36,2830),fill='#51636d',width=2)
d.text((36,2845),'20 checks PASS  •  11 body/scale cases  •  3,492 prop triangles  •  No Unity import  •  Awaiting Fedya OK',font=f(26,True),fill='#c4dfd7')
dest.parent.mkdir(parents=True,exist_ok=True);im.save(dest)
print(dest)
