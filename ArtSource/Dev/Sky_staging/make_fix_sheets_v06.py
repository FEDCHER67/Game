"""Assemble only actual v04/v05 renders; preserve all earlier review sheets."""
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont,ImageOps
import json,math
r=Path('C:/Dev/Game');images=r/'Working/Reviews/Sky';refs=r/'ArtSource/Dev/Sky_staging/References'
font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',26);small=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',20)
phases=['dawn','morning','noon','golden_hour','dusk','night','sunrise_sunfacing','sunset_sunfacing']
times=['05:39','08:00','12:00','17:27','19:06','22:00','06:15','18:15']
required=[images/f'{p}_{c}_v05.png' for p in phases for c in ['clear','overcast']]
if any(not p.is_file() for p in required):raise SystemExit('Missing real Unity captures: '+', '.join(p.name for p in required if not p.is_file()))
def save(im,path):
    with path.open('xb') as f:im.save(f,format='PNG')
board=Image.new('RGB',(1640,8*510+125),'#162330');d=ImageDraw.Draw(board)
d.text((22,20),'G22 v05 / Day, night and sun-facing views — actual Unity captures',font=font,fill='white')
d.text((22,62),'Fair / cloud cover 0.28                                      Overcast / cloud cover 0.97',font=font,fill='#AFC9D8')
for i,p in enumerate(required):
    row,col=divmod(i,2);x=20+col*810;y=115+row*510
    board.paste(ImageOps.contain(Image.open(p).convert('RGB'),(790,445)),(x,y))
    d.text((x,y+451),phases[row].replace('_',' ').title()+' '+times[row],font=font,fill='white')
save(board,images/'cycle_contact_sheet_v06.png')
sheet=Image.new('RGB',(2460,1120),'#162330');d=ImageDraw.Draw(sheet)
d.text((20,16),'G22 / COZY reference, previous v04, cloud fix v05',font=font,fill='white')
tiles=[(refs/'cozy_day_reference.jpg','COZY day reference'),(images/'noon_clear_v04.png','G22 v04 noon / previous'),(images/'noon_clear_v05.png','G22 v05 noon / fix round 1'),
       (refs/'cozy_night_reference.jpg','COZY night reference'),(images/'night_clear_v04.png','G22 v04 night / previous'),(images/'night_clear_v05.png','G22 v05 night / fix round 1')]
for i,(p,label) in enumerate(tiles):
    row,col=divmod(i,3);x=20+col*815;y=65+row*505
    sheet.paste(ImageOps.contain(Image.open(p).convert('RGB'),(795,447)),(x,y));d.text((x,y+455),label,font=font,fill='white')
d.text((20,1080),'COZY promotional images © Distant Lands. Internal study only; excluded from Assets.',font=small,fill='#AFC9D8')
save(sheet,images/'cozy_style_comparison_v06.png')
crop=Image.new('RGB',(2020,650),'#162330');d=ImageDraw.Draw(crop)
for i,version in enumerate(['v04','v05']):
    im=Image.open(images/f'noon_clear_{version}.png').convert('RGB').crop((120,20,1220,620))
    crop.paste(ImageOps.contain(im,(990,550)),(10+i*1010,60));d.text((20+i*1010,15),version+' / same camera, cloud phase and cover',font=font,fill='white')
save(crop,images/'cloud_shape_before_after_v05.png')
steps_paths=[images/f'noon_clear_steps{s}_v05.png' for s in [64,48,32]]
if all(p.is_file() for p in steps_paths):
    board=Image.new('RGB',(2460,560),'#162330');d=ImageDraw.Draw(board);stats=[]
    full=[Image.open(p).convert('RGB') for p in steps_paths];base=full[0].crop((0,0,1920,800))
    base_values=list(base.getdata())
    for i,(steps,im) in enumerate(zip([64,48,32],full)):
        board.paste(ImageOps.contain(im,(795,447)),(20+815*i,55));d.text((25+815*i,12),str(steps)+' cloud steps',font=font,fill='white')
        values=list(im.crop((0,0,1920,800)).getdata());error=sum((a-b)**2 for pa,pb in zip(base_values,values) for a,b in zip(pa,pb))/(len(values)*3)
        stats.append({'steps':steps,'sky_crop_rmse_0_255_vs_64':math.sqrt(error)})
    save(board,images/'cloud_steps_comparison_v05.png')
    with (images/'cloud_steps_difference_v05.json').open('x') as f:json.dump(stats,f,indent=2)
print('Created new v06 contact/style sheets and v05 cloud comparison evidence.')
