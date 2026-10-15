from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import json
ROOT=Path(__file__).parent;GAME=ROOT.parents[3];OUT=GAME/'Working/Reviews/Trees/pines_v04.png';assert not OUT.exists()
data=json.loads((ROOT/'validation_v04.json').read_text());pine3=json.loads((ROOT.parent/'pines_v03/validation_v03_02.json').read_text());old=json.loads((ROOT.parent/'oaks_pines_v01/validation_candidates_v01_02.json').read_text())
assert json.loads((ROOT/'fbx_roundtrip_v04.json').read_text())['status']=='PASS'
sheet=Image.new('RGB',(4384,3210),'#EAEDE4');d=ImageDraw.Draw(sheet);ink='#233D2E';muted='#57665A'
def font(n,b=False):return ImageFont.truetype('C:/Windows/Fonts/'+('segoeuib.ttf' if b else 'segoeui.ttf'),n)
def text(x,y,s,n=32,b=False,color=ink):d.text((x,y),s,font=font(n,b),fill=color)
def center(x,y,s,n=29,b=False,color=ink):
    f=font(n,b);d.text((x-d.textlength(s,font=f)/2,y),s,font=f,fill=color)
text(32,24,'COZY UMBRELLA PINES / v04 — CONNECTED, RAGGED CROWNS',58,True)
text(34,112,'Blender approval candidate  /  Shared Hamlet daylight  /  Lineup at 72 pixels per metre  /  Original trunks, limbs and approved Oak A unchanged',29,color=muted)
sheet.paste(Image.open(ROOT/'Preview/Pines_lineup_v04.png').convert('RGB'),(32,190))
H=data['variants'][0]['height'];W=data['variants'][0]['width']
rows=[dict(height=H,crownWidth=W,triangles=748),next(r for r in pine3['lods'] if r['id']=='Pine_A' and r['lod']==0)]+[next(r for r in data['lods'] if r['id']=='Pine_'+v and r['lod']==0) for v in 'ABC']+[next(r for r in old['lods'] if r['id']=='Oak_A' and r['lod']==0)]
labels=['CURRENT PLACEHOLDER','PINE v03 A','PINE v04 A','PINE v04 B','PINE v04 C','APPROVED OAK A']
notes=['3 tiers / median map size','3 separated oval tiers','3 connected lobes / 87 clusters','3 connected lobes / 91 clusters','3 connected lobes / 87 clusters','Single crown / v01_02 unchanged']
for i,(row,label,note) in enumerate(zip(rows,labels,notes)):
    x=32+(i+.5)*720;center(x,1363,label,31,True);center(x,1409,f'H {row["height"]:.2f} m  /  crown W {row["crownWidth"]:.2f} m',28,color=muted)
    center(x,1450,f'LOD0  {row["triangles"]:,} tris',29,color=muted);center(x,1492,note,25)
text(34,1555,'Envelope preserved: 12.986 m high × 6.861 m wide. Foliage spans 7.792–12.986 m (upper 40%). The new sprigs bridge the former horizontal gaps.',28,color=muted)
d.line((32,1615,4352,1615),fill='#BCC6B6',width=3)
text(32,1650,'PINE v04 A / SIDE VIEW — CONNECTIONS + RAGGED EDGES',34,True)
sheet.paste(Image.open(ROOT/'Preview/Pine_A_side_v04.png').convert('RGB'),(32,1720))
x=2130;text(x,1660,'ONE CROWN / THREE DOMINANT LOBES',40,True)
text(x,1740,'12 staggered sprigs on short new twigs connect the lobes.',33)
text(x,1795,'Broader, offset upper lobes; small uneven see-through pockets.',33)
text(x,1850,'Varied cluster size and tilt, lumpy outlines and 3 larger edge tufts.',32)
text(x,1960,'VARIANT',30,True);text(x+310,1960,'CLUSTERS  v03 → v04',30,True);text(x+1010,1960,'LOD0 / LOD1 / LOD2',30,True)
for i,s in enumerate(data['variants']):
    y=2025+i*80;lods=[next(r for r in data['lods'] if r['id']==s['id'] and r['lod']==j)['triangles'] for j in range(3)]
    text(x,y,s['id'].replace('_',' '),34,True);text(x+310,y,f'{s["oldClusters"]} → {s["clusters"]}',34);text(x+1010,y,' / '.join(f'{t:,}' for t in lods),34)
text(x,2300,'PRESERVED STRUCTURE / LOCAL ADDITIONS',33,True)
text(x,2360,'Original trunk, roots and every existing limb match v03 exactly.',32)
text(x,2415,'Only 12 short supporting twigs added per tree (0.16–0.96 m).',32)
text(x,2470,'Capsules, gentle lean and the approved +15% thickness retained.',32)
text(x,2525,'Side and top silhouettes inspected; all 9 exported LODs validated.',31)
text(x,2620,'UNCHANGED PALETTE + STIFF SHARED V19WIND',32,True)
for i,(name,color) in enumerate(data['palette'].items()):
    xx=x+i*430;d.rectangle((xx,2680,xx+350,2745),fill=color);text(xx,2760,name+'  '+color,28,color=muted)
text(x,2860,'3 FBX files / 9 LODs / 2 trunk capsules per tree.',33,True)
text(x,2920,'Final files: Pine A/B/C v04. No Unity import or scene changes.',31)
text(x,2990,'Awaiting Fedya’s visual approval.',34,True)
text(32,3150,'Side close-up is enlarged. All previous numbered models and the approved oaks remain untouched. No Unity work or commits.',27,color=muted)
sheet.save(OUT)
(ROOT/'sheet_manifest_v04.json').write_text(json.dumps(dict(sheet=str(OUT),candidate='Pine A/B/C v04',dimensions=list(sheet.size),pixelsPerMetre=72,lineup='Preview/Pines_lineup_v04.png',closeup='Preview/Pine_A_side_v04.png',internalTopCheck='Preview/Pines_topcheck_v04.png'),indent=2))
print('Saved',OUT)
