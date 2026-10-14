"""Lay out unchanged Unity render evidence; never synthesize a missing screenshot."""
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import sys
root=Path(r'C:\Dev\Game\Working\Reviews\Grass')
version=sys.argv[1] if len(sys.argv)>1 else 'v01'
out=root/f'grass_{version}.jpg'
assert not out.exists(),f'Refusing existing review sheet {out}'
pairs=[('hamlet_meadow','Hamlet meadow'),('hamlet_road','Hamlet road edge'),('between_hill','Between-districts hill'),('rough_yard','Rough District yard'),('beach_dune','Beach dune')]
def capture(key,side):return root/f'{key}_{side}_{"v02" if key=="rough_yard" and version=="v01" else version}.png'
files=[capture(key,side) for key,_ in pairs for side in ('before','after')]+[root/f'wind_{i:02d}_{version}.png' for i in range(6)]
assert all(p.exists() for p in files),'Missing actual captures: '+str([str(p) for p in files if not p.exists()])
font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',25)
title=ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf',35)
small=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',21)
W=2000;pad=24;tile=(W-pad*3)//2;imageh=round(tile*9/16);rowh=imageh+44
windw=(W-pad*4)//3;windh=round(windw*9/16)
H=100+5*(rowh+pad)+75+2*(windh+44+pad)+40
sheet=Image.new('RGB',(W,H),(22,28,29));draw=ImageDraw.Draw(sheet)
draw.text((pad,20),'G24 | Tall grass in map v19',font=title,fill=(234,238,218))
draw.text((pad,64),'Matched Unity renders | low layer preserved | 3 triangles per blade | travelling gusts',font=small,fill=(176,193,173))
y=110
for key,label in pairs:
 for c,side in enumerate(('before','after')):
  x=pad+c*(tile+pad)
  with Image.open(capture(key,side)) as im:sheet.paste(im.resize((tile,imageh),Image.Resampling.LANCZOS),(x,y+38))
  draw.text((x,y),f'{label}  /  {side.upper()}',font=font,fill=(225,234,215))
 y+=rowh+pad
draw.text((pad,y+4),'Wind progression | same camera, six shader-time samples',font=font,fill=(234,238,218));y+=61
for i in range(6):
 x=pad+(i%3)*(windw+pad);yy=y+(i//3)*(windh+44+pad)
 with Image.open(root/f'wind_{i:02d}_{version}.png') as im:sheet.paste(im.resize((windw,windh),Image.Resampling.LANCZOS),(x,yy+32))
 draw.text((x,yy),f'Frame {i+1}   t={12+i*.4:.1f}s',font=small,fill=(208,222,200))
sheet.save(out,quality=93,subsampling=0)
print(out)
