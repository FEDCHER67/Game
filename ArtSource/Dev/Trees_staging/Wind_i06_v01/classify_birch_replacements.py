from pathlib import Path
import json,csv,random,math
root=Path('C:/Dev/Game');e=root/'Working/Reviews/Wind/trees_i06'
d=json.loads((root/'ArtSource/References/Map/Look/look_v19_build_v07_flat.json').read_text(encoding='utf-8'))
def inside(poly,x,z):
    hit=False
    for i in range(0,len(poly),2):
        j=(i+2)%len(poly);ax,az=poly[i:i+2];bx,bz=poly[j:j+2]
        if (az>z)!=(bz>z) and x<(bx-ax)*(z-az)/(bz-az)+ax:hit=not hit
    return hit
gardens=[y for y in d['yards'] if y['district']=='village' and (y['ground']=='lawn' or any(k in y['id'] for k in ['garden','allotment','orchard']))]
apples=[t for t in d['trees'] if t['sp']=='apple' and 132.6<t['x']<374 and 373.6<t['y']<605]
rows=[];rng=random.Random(230406)
for tr in csv.DictReader((e/'birch_positions_before.csv').open()):
    x,z=float(tr['x']),float(tr['z']);hamlet=132.6<=x<=374 and 373.6<=z<=605
    garden=next((g['id'] for g in gardens if inside(g['pts'],x,z)),None) if hamlet else None
    orchard=hamlet and any(math.hypot(t['x']-x,t['y']-z)<=12 for t in apples)
    apple=bool(garden or orchard)
    rows.append(dict(index=int(tr['index']),prototype=(7 if rng.random()<.5 else 8) if apple else (3 if rng.random()<.5 else 4),rotation=rng.random()*math.tau,scale=.9+rng.random()*.2,reason=garden or ('Hamlet existing apple cluster <=12m' if orchard else 'poplar, outside Hamlet fruit garden'),x=x,z=z))
out=dict(seed=230406,classification='Hamlet box from v19 pilot; authored lawn/garden/allotment/orchard yards OR <=12m from an existing Hamlet apple (orchard/garden cluster). Everything else poplar.',source='ArtSource/References/Map/Look/look_v19_build_v07_flat.json',rows=rows)
(e/'birch_replacements_v02.json').write_text(json.dumps(out,indent=2))
print('Replacement manifest:',len(rows),'apple',sum(r['prototype'] in (7,8) for r in rows),'poplar',sum(r['prototype'] in (3,4) for r in rows))
