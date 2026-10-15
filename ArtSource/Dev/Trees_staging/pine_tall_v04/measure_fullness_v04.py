"""Orthographic opaque foliage silhouette area, four azimuths, same pixels/metre."""
from pathlib import Path
from PIL import Image,ImageDraw
import json,math
ROOT=Path(__file__).parent;data=json.loads((ROOT/'coverage_geometry_v04.json').read_text());rows=[]
for name,pair in data.items():
    angles=[]
    for degrees in (0,45,90,135):
        a=math.radians(degrees);areas={}
        for version in ('before','after'):
            geo=pair[version];im=Image.new('1',(1200,1200));draw=ImageDraw.Draw(im)
            points=[(600+(p[0]*math.cos(a)+p[1]*math.sin(a))*50,1120-p[2]*50) for p in geo['vertices']]
            for face in geo['faces']:draw.polygon([points[i] for i in face],fill=1)
            areas[version]=sum(im.getdata());im.save(ROOT/'Preview'/f'{name}_{version}_coverage_{degrees}_v04.png')
        angles.append(dict(azimuth=degrees,**areas,increasePercent=100*(areas['after']/areas['before']-1)))
    mean=sum(r['increasePercent'] for r in angles)/len(angles)
    rows.append(dict(id=name,meanProjectedFoliageIncreasePercent=mean,views=angles));print(name,'foliage coverage +',round(mean,1),'percent')
out=dict(metric='Opaque foliage silhouette union at 50 px/metre, orthographic, four azimuths. A proxy for visual fullness, not a universal physical definition.',rows=rows)
(ROOT/'fullness_measurement_v04.json').write_text(json.dumps(out,indent=2))
