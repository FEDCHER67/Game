from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import json

root=Path('C:/Dev/Game');e=root/'Working/Reviews/Trees/i07';out=root/'Working/Reviews/Trees/leafy_v04_in_map_i07.jpg'
assert not out.exists(),out
def font(size,bold=False):return ImageFont.truetype('C:/Windows/Fonts/'+('segoeuib.ttf' if bold else 'segoeui.ttf'),size)
bg='#E9EDE5';ink='#253E2D';muted='#526556'
sheet=Image.new('RGB',(3260,4110),bg);d=ImageDraw.Draw(sheet)
d.text((35,24),'APPROVED LEAFY TREES / i07',font=font(57,True),fill=ink)
d.text((35,100),'Same map positions and camera poses  •  08:00 light  •  Shared V19Wind  •  Actual Play renders',font=font(29),fill=muted)
d.text((35,158),'BEFORE / i06',font=font(32,True),fill=ink);d.text((1660,158),'AFTER / i07',font=font(32,True),fill=ink)
titles=['HAMLET ORCHARD / APPLE v04_03','POPLAR ROAD / POPLAR v04_04','BEACH / PALM v04_03','GARDEN / BUSH v04_03']
for i,title in enumerate(titles):
    y=215+i*945;d.text((35,y),title,font=font(29,True),fill=ink)
    for col,revision in enumerate(['i06_v02','i07_v02']):
        image=Image.open(e/f'{revision}_{i}.png').convert('RGB');assert image.size==(1600,900)
        sheet.paste(image,(30+col*1630,y+41))
d.text((35,4010),'999 poplars  •  243 apples  •  47 palms  •  1,949 bushes  |  Seeded A/B/C, native metre sizes with ±10% scale.',font=font(30,True),fill=ink)
d.text((35,4060),'Forest v03, bare trees and rocks preserved. Earlier scenes and approved source models unchanged.',font=font(27),fill=muted)
sheet.save(out,quality=94,subsampling=0)
frames=[Image.open(e/f'wind_{i:02d}.png').convert('RGB') for i in range(32)]
palette=frames[0].quantize(colors=256,method=Image.Quantize.MEDIANCUT)
frames=[im.quantize(palette=palette,dither=Image.Dither.NONE) for im in frames]
gif=root/'Working/Reviews/Trees/leafy_v04_wind_i07.gif';assert not gif.exists()
frames[0].save(gif,save_all=True,append_images=frames[1:],duration=125,loop=0,disposal=2)
manifest={'sheet':str(out),'gif':str(gif),'comparison_frames':[f'{rev}_{i}.png' for i in range(4) for rev in ['i06_v02','i07_v02']],
          'wind_frames':[f'wind_{i:02d}.png' for i in range(32)],'wind_seconds':4,'wind_view':'Hamlet orchard',
          'excluded':'Initial i06/i07 stills; Beach sheet pose revised from shallow water to dry land. Performance uses the completed original matched runs; optional resample was interrupted and excluded.'}
(e/'capture_manifest_final.json').write_text(json.dumps(manifest,indent=2))
print('Saved',out,'and',gif)
