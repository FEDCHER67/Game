from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import json
root=Path(__file__).parent;out=Path('C:/Dev/Game/Working/Reviews/Trees/leafy_trees_v04.png')
assert not out.exists(),out
data=json.loads((root/'validation_v04_03.json').read_text());palette=data['palette']
BG='#EAEDE4';INK='#233D2E';MUTED='#57665A';RULE='#BBC6B7'
def font(n,bold=False):return ImageFont.truetype('C:/Windows/Fonts/'+('segoeuib.ttf' if bold else 'segoeui.ttf'),n)
W=4000;mainw=3000;detailx=3080;detailw=850
row_specs=[('Apple',650,'HAMLET / APPLE TREES','Full, irregular crowns; visible forks; a few red apples.'),('Poplar',1740,'COMMON LAND / POPLARS','Narrow leafy columns; rising branches; overlapping clusters.'),('Palm',1035,'BEACH / PALMS','Curved segmented trunks; long fronds with individual leaflets.'),('Bush',650,'GARDENS / BUSHES','Low leafy silhouettes; compact, upright and spreading variants.')]
H=185+sum(h+105 for _,h,_,_ in row_specs)+210
sheet=Image.new('RGB',(W,H),BG);d=ImageDraw.Draw(sheet)
d.text((40,20),'LEAFY TREES / v04',font=font(64,True),fill=INK)
d.text((40,105),'12 original Blender models  •  Shared Hamlet daylight  •  Current models alongside  •  Fedya approval before Unity import',font=font(30),fill=MUTED)
positions=[(.159375,'CURRENT'),(.390625,'A'),(.615625,'B'),(.840625,'C')]
heights_old={'Apple':4.62,'Poplar':16.50,'Palm':8.94,'Bush':1.17}
y=185
for family,bodyh,title,desc in row_specs:
    d.line((40,y,W-40,y),fill=RULE,width=2);d.text((40,y+12),title,font=font(37,True),fill=INK);d.text((40,y+59),desc,font=font(27),fill=MUTED)
    top=y+105;img=Image.open(root/'Preview'/(family+'_lineup_v04_03.png')).convert('RGB');nh=round(img.height*mainw/img.width)
    img=img.resize((mainw,nh),Image.Resampling.LANCZOS);iy=top+max(0,(bodyh-55-nh)//2);sheet.paste(img,(40,iy))
    group=[s for s in data['variants'] if s['family']==family]
    for i,(x,label) in enumerate(positions):
        h=heights_old[family] if i==0 else group[i-1]['height'];name='Current / i05' if i==0 else family+' '+label
        text=f'{name}  ·  {h:.2f} m';width=d.textlength(text,font=font(28,True));d.text((40+x*mainw-width/2,iy+nh+9),text,font=font(28,True),fill=INK)
    detail=Image.open(root/'Preview'/(family+'_detail_v04_03.png')).convert('RGB');dh=round(detail.height*detailw/detail.width)
    if dh>bodyh-65:
        scale=(bodyh-65)/dh;dw=round(detailw*scale);dh=bodyh-65
    else:dw=detailw
    detail=detail.resize((dw,dh),Image.Resampling.LANCZOS);sheet.paste(detail,(detailx+(detailw-dw)//2,top+5))
    d.text((detailx,top+dh+18),'Actual '+family+' A leaf / branch close-up',font=font(26),fill=INK)
    if family=='Poplar':
        yy=top+dh+100
        for line in ['COMMON SCALE','All four lineups: 93.75 px per metre.','No individual model resizing in the sheet.','Close-ups use a separate scale.']:
            d.text((detailx,yy),line,font=font(29,line=='COMMON SCALE'),fill=INK if line=='COMMON SCALE' else MUTED);yy+=48
        yy+=40
        d.text((detailx,yy),'ORIGINAL DISTRICT PALETTE',font=font(29,True),fill=INK);yy+=60
        for name in ('LeafDark','Leaf','LeafLight','Bark','Apple','PalmLeaf','PalmBark'):
            d.rounded_rectangle((detailx,yy,detailx+58,yy+42),radius=5,fill=palette[name]);d.text((detailx+80,yy+2),name+'  '+palette[name],font=font(26),fill=MUTED);yy+=55
        yy+=25
        for line in ['Opaque folded leaf geometry.','No foliage blobs or alpha texture.','Base pivots, metres, three LODs.','Shared V19Wind material set staged.']:
            d.text((detailx,yy),line,font=font(28),fill=MUTED);yy+=45
    y+=bodyh+105
d.line((40,y+15,W-40,y+15),fill=RULE,width=2)
d.text((40,y+40),'LOD0 triangles: apple 5,276  |  poplar 5,836  |  palm 3,806  |  bush 1,916',font=font(34,True),fill=INK)
d.text((40,y+93),'Candidate v04_03  •  Original geometry + existing project palette  •  COZY studied for foliage structure; no reference assets copied.',font=font(29),fill=MUTED)
d.text((40,y+140),'Blender-only preview. i06 already contains retained-tree wind and 762 birch replacements with current poplar/apple models.',font=font(29),fill=MUTED)
sheet.save(out)
(root/'sheet_manifest_v04_03.json').write_text(json.dumps({'file':str(out),'candidate':'v04_03','common_lineup_px_per_m':93.75,'common_camera':'orthographic, direction (0,-36,6), unchanged across all lineups','models':'12 LOD0 candidates + four unscaled current prototype comparisons','lighting':'Same sunny Hamlet studio approximation in Blender; exact source RGB palette; not a Unity capture','images':[str(p.relative_to(root)) for p in (root/'Preview').glob('*_v04_03.png')]},indent=2))
print(out, sheet.size)
