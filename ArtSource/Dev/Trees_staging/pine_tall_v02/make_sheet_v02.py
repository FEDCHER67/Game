from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import json
ROOT=Path(__file__).parent;OLD=ROOT.parent/'pine_tall_v01';GAME=ROOT.parents[3]
OUT=GAME/'Working/Reviews/Trees/pine_tall_v02.png';assert not OUT.exists()
data=json.loads((ROOT/'validation_v02.json').read_text());preview=json.loads((ROOT/'preview_manifest_v02.json').read_text())
assert json.loads((ROOT/'fbx_roundtrip_v02.json').read_text())['status']=='PASS'
sheet=Image.new('RGB',(4320,4100),'#EAEDE4');d=ImageDraw.Draw(sheet);ink='#233D2E';muted='#57665A'
def font(n,b=False):return ImageFont.truetype('C:/Windows/Fonts/'+('segoeuib.ttf' if b else 'segoeui.ttf'),n)
def text(x,y,s,n=30,b=False,color=ink):d.text((x,y),s,font=font(n,b),fill=color)
def center(x,y,s,n=28,b=False,color=ink):
    f=font(n,b);d.text((x-d.textlength(s,font=f)/2,y),s,font=f,fill=color)
text(32,22,'COZY PINE_TALL / v02 / DENSER NEEDLE CLUMPS',54,True)
text(34,102,'9 to 17 leaf plates per clump (+89%) / unchanged branches and tree sizes / Hamlet daylight / common model scale',29,color=muted)
ref=Image.open(GAME/'ArtSource/References/Trees/REF_FEDYA_pine_tall_v01.png').convert('RGB').resize((660,880),Image.Resampling.LANCZOS)
sheet.paste(ref,(52,300));text(52,205,'FEDYA’S REFERENCE',31,True)
text(52,1210,'Sierra mountain pine',30,True)
text(52,1265,'Photographic structure reference.',25,color=muted);text(52,1310,'The photo has no metric scale.',25,color=muted)
for j,line in enumerate(['Denser individual clumps','More overlapping needle plates','Same exposed main branches','Same narrow, irregular crown']):text(52,1430+j*65,line,27)
sheet.paste(Image.open(ROOT/'Preview/PineTall_lineup_v02.png').convert('RGB'),(832,180))
rows=[next(r for r in data['lods'] if r['id']=='PineTall_'+v and r['lod']==0) for v in 'ABC']+preview['comparisonModels']
for i,(row,label) in enumerate(zip(rows,['PINE_TALL v02 A','PINE_TALL v02 B','PINE_TALL v02 C','PINE v04 A','FOREST v03 FIR','POPLAR v04_04 A'])):
    x=832+(i+.5)*576;center(x,1880,label,29,True)
    width=row.get('crownWidth',row.get('width'));center(x,1930,f'H {row["height"]:.2f} m / W {width:.2f} m',26,color=muted)
    center(x,1976,f'LOD0 {row["triangles"]:,} tris',28,color=muted)
    center(x,2020,'NEW / APPROVAL CANDIDATE' if i<3 else 'APPROVED / UNCHANGED',23)
d.line((32,2100,4288,2100),fill='#BCC6B6',width=3)
text(32,2135,'BEFORE / v01_02 A / 9 PLATES PER CLUMP',31,True)
text(1590,2135,'AFTER / v02 A / 17 PLATES PER CLUMP',31,True)
sheet.paste(Image.open(OLD/'Preview/PineTall_A_clumps_stubs_v01_02.png').convert('RGB'),(32,2200))
sheet.paste(Image.open(ROOT/'Preview/PineTall_A_clumps_stubs_v02.png').convert('RGB'),(1590,2200))
x=3170;text(x,2200,'NEARLY TWICE THE LEAVES',32,True)
for j,line in enumerate(['New plates fill gaps inside each clump.','65 / 69 / 63 clump positions unchanged.','Trunk, limbs and dead stubs unchanged.','Two trunk capsules unchanged.','LeafPine / LeafDark palette unchanged.']):text(x,2270+j*50,line,25)
text(x,2570,'LEAF PLATES / BEFORE > AFTER',28,True)
for j,s in enumerate(data['variants']):
    text(x,2630+j*50,f'{s["id"][-1]}: {s["clusters"]*9:,} > {s["leafPlates"]:,}',29)
text(x,2830,'LOD0 / LOD1 / LOD2 TRIANGLES',28,True)
for j,s in enumerate(data['variants']):
    counts=[next(r['triangles'] for r in data['lods'] if r['id']==s['id'] and r['lod']==lod) for lod in range(3)]
    text(x,2895+j*55,s['id'][-1]+': '+' / '.join(f'{n:,}' for n in counts),28)
text(x,3120,'CHECKED IN BLENDER',30,True)
for j,line in enumerate(['All 9 LODs exported and reimported.','Closed geometry; opaque folded plates.','Base pivots; metres; below 8k tris.','Existing shared V19Wind / stiff.','Unity import and motion test: not run.']):text(x,3185+j*50,line,25)
for j,(name,color) in enumerate(data['palette'].items()):
    xx=x+j*355;d.rectangle((xx,3490,xx+310,3555),fill=color);text(xx,3575,name,24)
text(x,3690,'BLENDER ONLY / AWAITING OK',30,True)
text(x,3750,'No Unity changes or i10 placement.',26)
text(32,3970,'Before / after close-ups use the same camera, lighting and scale. All six lineup models share metre scale; reference photo is illustrative.',28,color=muted)
text(32,4020,'Pine_Tall v01 and v01_02 remain preserved. New candidate: PineTall A/B/C v02.',29,True)
sheet.save(OUT)
(ROOT/'sheet_manifest_v02.json').write_text(json.dumps(dict(sheet=str(OUT),candidate='PineTall A/B/C v02',dimensions=list(sheet.size),pixelsPerMetre=72,before='pine_tall_v01/Preview/PineTall_A_clumps_stubs_v01_02.png',after='Preview/PineTall_A_clumps_stubs_v02.png'),indent=2))
print('SHEET_SAVED',OUT)
