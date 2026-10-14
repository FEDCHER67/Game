"""Layout actual Unity screenshots and unchanged public references; never synthesize missing evidence."""
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont,ImageOps
root=Path(r'C:\Dev\Game')
captures=root/'Working/Reviews/Sky'
refs=root/'ArtSource/Dev/Sky_staging/References'
font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',26)
small=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',19)
phases=['dawn','morning','noon','golden_hour','dusk','night']
hours=['05:39','08:00','12:00','17:27','19:06','22:00']
paths=[captures/f'{phase}_{cover}_v03.png' for phase in phases for cover in ('clear','overcast')]
missing=[str(p) for p in paths if not p.is_file()]
if missing:raise SystemExit('BLOCKED: real Unity captures required; missing '+', '.join(missing))
def save_new(im,path):
    with path.open('xb') as f:im.save(f,format='PNG')
board=Image.new('RGB',(1640,6*510+125),'#162330');draw=ImageDraw.Draw(board)
draw.text((22,20),'G22 / Day & night — actual Unity 6000.5 captures',font=font,fill='white')
draw.text((22,62),'Fair / cloud cover 0.38                                      Overcast / cloud cover 0.97',font=font,fill='#AFC9D8')
for i,p in enumerate(paths):
    r,c=divmod(i,2);x=20+c*810;y=115+r*510
    im=ImageOps.contain(Image.open(p).convert('RGB'),(790,445));board.paste(im,(x,y))
    draw.text((x,y+451),phases[r].replace('_',' ').title()+'  '+hours[r],font=font,fill='white')
save_new(board,captures/'cycle_contact_sheet_v03.png')
sheet=Image.new('RGB',(1840,1260),'#162330');draw=ImageDraw.Draw(sheet)
draw.text((24,20),'G22 / Style study — public COZY references vs. original Unity sky',font=font,fill='white')
tiles=[(refs/'cozy_day_reference.jpg','COZY day — Distant Lands reference'),(captures/'noon_clear_v03.png','G22 noon — original procedural sky'),
       (refs/'cozy_night_reference.jpg','COZY night — Distant Lands reference'),(captures/'night_clear_v03.png','G22 night — original procedural sky')]
for i,(path,label) in enumerate(tiles):
    r,c=divmod(i,2);x=20+c*910;y=80+r*570
    im=ImageOps.contain(Image.open(path).convert('RGB'),(890,501));sheet.paste(im,(x,y));draw.text((x,y+511),label,font=font,fill='white')
draw.text((24,1220),'COZY promotional images © Distant Lands. Internal comparison only; excluded from game Assets.',font=small,fill='#AFC9D8')
save_new(sheet,captures/'cozy_style_comparison_v03.png')
print('Created two sheets from verified existing screenshot files.')
