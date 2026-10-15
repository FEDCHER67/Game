from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import json
ROOT=Path(__file__).parent;OLD=ROOT.parent/'oaks_pines_v01';GAME=ROOT.parents[3]
OUT=GAME/'Working/Reviews/Trees/pines_v02.png';assert not OUT.exists(),OUT
data=json.loads((ROOT/'validation_v02_02.json').read_text());previous=json.loads((OLD/'validation_candidates_v01_02.json').read_text())
assert json.loads((ROOT/'fbx_roundtrip_v02_02.json').read_text())['status']=='PASS'
sheet=Image.new('RGB',(4384,3210),'#EAEDE4');d=ImageDraw.Draw(sheet);ink='#233D2E';muted='#57665A'
def font(n,b=False):return ImageFont.truetype('C:/Windows/Fonts/'+('segoeuib.ttf' if b else 'segoeui.ttf'),n)
def text(x,y,s,n=32,b=False,color=ink):d.text((x,y),s,font=font(n,b),fill=color)
def center(x,y,s,n=29,b=False,color=ink):
    f=font(n,b);d.text((x-d.textlength(s,font=f)/2,y),s,font=f,fill=color)
text(32,24,'COZY UMBRELLA PINES / v02',64,True)
text(34,112,'Blender approval candidate  /  Shared Hamlet daylight  /  Every lineup tree at 72 pixels per metre  /  Approved Oak A unchanged',30,color=muted)
sheet.paste(Image.open(ROOT/'Preview/Pines_lineup_v02_02.png').convert('RGB'),(32,190))
H=data['variants'][0]['height'];W=data['variants'][0]['width']
oak=next(r for r in previous['lods'] if r['id']=='Oak_A' and r['lod']==0)
rows=[dict(height=H,crownWidth=W,triangles=748),next(r for r in previous['lods'] if r['id']=='Pine_A' and r['lod']==0)]+[next(r for r in data['lods'] if r['id']=='Pine_'+v and r['lod']==0) for v in 'ABC']+[oak]
labels=['CURRENT PLACEHOLDER','PINE v01 A','PINE v02 A','PINE v02 B','PINE v02 C','APPROVED OAK A']
notes=['Measured median map envelope','30 clusters / single crown','42 clusters / 3 tiers','50 clusters / 3 tiers','42 clusters / 3 tiers','v01_02 / unchanged']
for i,(row,label,note) in enumerate(zip(rows,labels,notes)):
    x=32+(i+.5)*720;center(x,1363,label,31,True)
    center(x,1409,f'H {row["height"]:.2f} m  /  crown W {row["crownWidth"]:.2f} m',28,color=muted)
    center(x,1450,f'LOD0  {row["triangles"]:,} tris',29,color=muted);center(x,1492,note,27)
text(34,1555,'Pines retain the 12.986 m height / 6.861 m crown-width envelope. The lower crown starts at 8.571 m: foliage spans the top 34% of the tree.',28,color=muted)
d.line((32,1615,4352,1615),fill='#BCC6B6',width=3)
text(32,1650,'PINE v02 A / CROWN FROM BELOW',39,True)
sheet.paste(Image.open(ROOT/'Preview/Pine_A_below_v02_02.png').convert('RGB'),(32,1720))
x=2130;text(x,1660,'DENSER, DEEPER CROWNS',44,True)
text(x,1740,'Three staggered flat tiers; individual folded needle fronds.',34)
text(x,1795,'Overlapping clusters close the gaps inside each tier.',34)
text(x,1850,'Gentle trunk curves retained; trunk and main-limb radii +15%.',34)
text(x,1960,'VARIANT',30,True);text(x+310,1960,'CLUSTERS  v01 → v02',30,True);text(x+1010,1960,'LOD0 / LOD1 / LOD2',30,True)
for i,s in enumerate(data['variants']):
    y=2025+i*80;lods=[next(r for r in data['lods'] if r['id']==s['id'] and r['lod']==j)['triangles'] for j in range(3)]
    text(x,y,s['id'].replace('_',' '),34,True);pct=(s['clusters']/s['oldClusters']-1)*100
    text(x+310,y,f'{s["oldClusters"]} → {s["clusters"]}  (+{pct:.1f}%)',34)
    text(x+1010,y,' / '.join(f'{t:,}' for t in lods),34)
text(x,2320,'EXISTING PALETTE / UNCHANGED',34,True)
for i,(name,color) in enumerate(data['palette'].items()):
    xx=x+i*450;d.rectangle((xx,2380,xx+370,2475),fill=color);text(xx,2495,name+'  '+color,29,color=muted)
text(x,2600,'3 FBX files / 9 LOD meshes / 2 trunk capsules per tree',34,True)
text(x,2660,'Metres, base pivots, closed opaque foliage and UVs verified.',32)
text(x,2720,'Shared V19Wind: unchanged stiff Pine material settings.',32)
text(x,2825,'Final candidate files: Pine A/B/C v02_02.',34,True)
text(x,2885,'Earlier candidates preserved. No Unity import or scene edits.',32)
text(x,2945,'Awaiting Fedya’s visual approval.',34,True)
text(32,3150,'Below-crown close-up is enlarged. Approved oaks, v04 leafy trees, Forest v03 trees, bare trees and rocks remain unchanged.',27,color=muted)
sheet.save(OUT)
(ROOT/'sheet_manifest_v02.json').write_text(json.dumps(dict(sheet=str(OUT),candidate='Pine A/B/C v02_02',pixelsPerMetre=72,dimensions=list(sheet.size),lineup='Preview/Pines_lineup_v02_02.png',closeup='Preview/Pine_A_below_v02_02.png'),indent=2))
print('Saved',OUT)
