from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import json
ROOT=Path(__file__).parent;GAME=ROOT.parents[3]
OUT=GAME/'Working/Reviews/Trees/pines_v03.png';assert not OUT.exists()
data=json.loads((ROOT/'validation_v03_02.json').read_text());pine2=json.loads((ROOT.parent/'pines_v02/validation_v02_02.json').read_text());old=json.loads((ROOT.parent/'oaks_pines_v01/validation_candidates_v01_02.json').read_text())
assert json.loads((ROOT/'fbx_roundtrip_v03_02.json').read_text())['status']=='PASS'
sheet=Image.new('RGB',(4384,3210),'#EAEDE4');d=ImageDraw.Draw(sheet);ink='#233D2E';muted='#57665A'
def font(n,b=False):return ImageFont.truetype('C:/Windows/Fonts/'+('segoeuib.ttf' if b else 'segoeui.ttf'),n)
def text(x,y,s,n=32,b=False,color=ink):d.text((x,y),s,font=font(n,b),fill=color)
def center(x,y,s,n=29,b=False,color=ink):
    f=font(n,b);d.text((x-d.textlength(s,font=f)/2,y),s,font=f,fill=color)
text(32,24,'COZY UMBRELLA PINES / v03 — OVAL CROWN TIERS',61,True)
text(34,112,'Blender approval candidate  /  Shared Hamlet daylight  /  All lineup trees at 72 pixels per metre  /  v02 wood and approved Oak A unchanged',29,color=muted)
sheet.paste(Image.open(ROOT/'Preview/Pines_lineup_v03_02.png').convert('RGB'),(32,190))
H=data['variants'][0]['height'];W=data['variants'][0]['width']
rows=[dict(height=H,crownWidth=W,triangles=748),next(r for r in pine2['lods'] if r['id']=='Pine_A' and r['lod']==0)]+[next(r for r in data['lods'] if r['id']=='Pine_'+v and r['lod']==0) for v in 'ABC']+[next(r for r in old['lods'] if r['id']=='Oak_A' and r['lod']==0)]
labels=['CURRENT PLACEHOLDER','PINE v02 A','PINE v03 A','PINE v03 B','PINE v03 C','APPROVED OAK A']
notes=['3 tiers / median map size','3 tiers / 42 clusters','3 oval tiers / 72 clusters','3 oval tiers / 76 clusters','3 oval tiers / 72 clusters','Single crown / v01_02 unchanged']
for i,(row,label,note) in enumerate(zip(rows,labels,notes)):
    x=32+(i+.5)*720;center(x,1363,label,31,True);center(x,1409,f'H {row["height"]:.2f} m  /  crown W {row["crownWidth"]:.2f} m',28,color=muted)
    center(x,1450,f'LOD0  {row["triangles"]:,} tris',29,color=muted);center(x,1492,note,26)
text(34,1555,'Overall envelope: 12.986 m high × 6.861 m wide. Foliage spans 7.799–12.986 m (upper 39.9%). The v02 trunk, branches and lean are preserved.',28,color=muted)
d.line((32,1615,4352,1615),fill='#BCC6B6',width=3)
text(32,1650,'PINE v03 A / TRUE SIDE VIEW — OVAL TIERS',38,True)
sheet.paste(Image.open(ROOT/'Preview/Pine_A_side_v03_02.png').convert('RGB'),(32,1720))
x=2130;text(x,1660,'ROUNDED ABOVE AND BELOW',44,True)
text(x,1740,'Dense folded-frond clusters form each lens-shaped tier.',34)
text(x,1795,'Leafy, uneven edges; visible branches in the tier gaps.',34)
text(x,1850,'All v02 wood geometry, thickness and capsule recipes retained.',33)
text(x,1960,'VARIANT',30,True);text(x+310,1960,'CLUSTERS  v02 → v03',30,True);text(x+1010,1960,'LOD0 / LOD1 / LOD2',30,True)
for i,s in enumerate(data['variants']):
    y=2025+i*80;lods=[next(r for r in data['lods'] if r['id']==s['id'] and r['lod']==j)['triangles'] for j in range(3)]
    text(x,y,s['id'].replace('_',' '),34,True);text(x+310,y,f'{s["oldClusters"]} → {s["clusters"]}',34);text(x+1010,y,' / '.join(f'{t:,}' for t in lods),34)
text(x,2300,'LENS PROPORTIONS / FIT WITHIN THE FIXED HEIGHT',32,True)
text(x,2360,'Lower tier: 6.86 m wide × 2.29 m high  (1 : 3.00).',33)
text(x,2415,'Upper tiers: 3.60–3.70 m wide × 1.25 m high  (1 : 2.88–2.96).',32)
text(x,2470,'The upper tiers taper to retain separate ovals within the top 40%.',31)
text(x,2525,'Minimum vertical clearance between tier envelopes: 0.20 m.',31)
text(x,2620,'UNCHANGED PALETTE + SHARED V19WIND',33,True)
for i,(name,color) in enumerate(data['palette'].items()):
    xx=x+i*430;d.rectangle((xx,2680,xx+350,2745),fill=color);text(xx,2760,name+'  '+color,28,color=muted)
text(x,2860,'3 FBX / 9 LODs / 2 trunk capsules per tree — validated.',33,True)
text(x,2920,'Final files: Pine A/B/C v03_02. Unity integration not performed.',31)
text(x,2990,'Awaiting Fedya’s visual approval.',34,True)
text(32,3150,'Side-view close-up is enlarged. All earlier deliverables and the approved oaks remain unchanged. Stiff shared Pine wind materials are retained.',27,color=muted)
sheet.save(OUT)
(ROOT/'sheet_manifest_v03.json').write_text(json.dumps(dict(sheet=str(OUT),candidate='Pine A/B/C v03_02',dimensions=list(sheet.size),pixelsPerMetre=72,lineup='Preview/Pines_lineup_v03_02.png',closeup='Preview/Pine_A_side_v03_02.png'),indent=2))
print('Saved',OUT)
