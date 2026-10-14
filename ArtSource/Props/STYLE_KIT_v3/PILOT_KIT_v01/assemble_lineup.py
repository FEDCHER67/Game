"""Create the 1280px labelled lineup from Blender-rendered tile PNGs. New files only."""
import json, textwrap
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
HERE=Path(__file__).resolve().parent
report=json.loads((HERE/'validation_v01.json').read_text(encoding='utf8'))
out=HERE/'Previews/v01/01_all_modules_lineup.png'
if out.exists(): raise FileExistsError(out)
fontroot=Path('C:/Windows/Fonts')
def font(size,bold=False): return ImageFont.truetype(str(fontroot/('segoeuib.ttf' if bold else 'segoeui.ttf')),size)
sheet=Image.new('RGB',(1280,1280),'#E1E2DC'); d=ImageDraw.Draw(sheet)
d.text((25,16),'PILOT KIT / v01',font=font(28,True),fill='#293332')
d.text((26,52),f'G16   |   Hamlet + Rough District   |   {report["total_assets"]} modules   |   {report["total_triangles"]:,} triangles',font=font(15),fill='#52605B')
badges={'A':'#756C4B','B':'#7F6351','C':'#616E56','D':'#596A79'}
for idx,(name,r) in enumerate(report['assets'].items()):
    col,row=idx%7,idx//7; x=24+col*177; y=88+row*188
    d.rounded_rectangle((x,y,x+170,y+180),radius=5,fill='#F1F1EB')
    im=Image.open(HERE/'Previews/v01/Tiles'/f'{name}_three_quarter.png').convert('RGB')
    im=im.resize((166,135),Image.Resampling.LANCZOS); sheet.paste(im,(x+2,y+2))
    d.rectangle((x+5,y+5,x+27,y+23),fill=badges[r['group']]); d.text((x+10,y+4),r['group'],font=font(12,True),fill='white')
    title=name.replace('_',' ')
    lines=textwrap.wrap(title,width=24)
    for j,line in enumerate(lines[:2]): d.text((x+7,y+139+j*13),line,font=font(10,True),fill='#293332')
    d.text((x+7,y+166),f'{r["triangles"]} tris  /  '+ ' x '.join(f'{s:.2f}' for s in r['size_m'])+' m',font=font(9),fill='#65706A')
d.text((25,1228),'A Hamlet props    B House details    C Plots & yards    D Courtyard/service',font=font(15,True),fill='#374742')
d.text((25,1254),'Individual tiles fitted for inspection; group views use a shared metre scale. Packed v07 target palette; geometry detail only.',font=font(12),fill='#52605B')
sheet.save(out)
print(out)
