from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import json
ROOT=Path(__file__).parent;GAME=ROOT.parents[3];OUT=GAME/'Working/Reviews/Trees/pine_tall_v01.png';assert not OUT.exists()
data=json.loads((ROOT/'validation_v01_02.json').read_text());preview=json.loads((ROOT/'preview_manifest_v01_02.json').read_text())
assert json.loads((ROOT/'fbx_roundtrip_v01_02.json').read_text())['status']=='PASS'
sheet=Image.new('RGB',(4320,4100),'#EAEDE4');d=ImageDraw.Draw(sheet);ink='#233D2E';muted='#57665A'
def font(n,b=False):return ImageFont.truetype('C:/Windows/Fonts/'+('segoeuib.ttf' if b else 'segoeui.ttf'),n)
def text(x,y,s,n=30,b=False,color=ink):d.text((x,y),s,font=font(n,b),fill=color)
def center(x,y,s,n=28,b=False,color=ink):
    f=font(n,b);d.text((x-d.textlength(s,font=f)/2,y),s,font=f,fill=color)
text(32,22,'COZY PINE_TALL / v01 / MOUNTAIN PINE',54,True)
text(34,102,'Approval preview / final build v01_02 / Hamlet daylight / six Blender models at common scale: 72 pixels per metre',29,color=muted)
ref=Image.open(GAME/'ArtSource/References/Trees/REF_FEDYA_pine_tall_v01.png').convert('RGB');ref.thumbnail((660,1200));ref=ref.resize((660,880),Image.Resampling.LANCZOS)
sheet.paste(ref,(52,300));text(52,205,'FEDYA’S REFERENCE',31,True)
text(52,1210,'Sierra mountain pine',30,True);text(52,1265,'Photographic structure reference.',25,color=muted);text(52,1310,'The photo has no metric scale.',25,color=muted)
for j,line in enumerate(['Narrow, irregular crown','Visible horizontal limbs','Needles at branch ends','Bare lower trunk + stubs']):text(52,1430+j*65,line,29)
sheet.paste(Image.open(ROOT/'Preview/PineTall_lineup_v01_02.png').convert('RGB'),(832,180))
rows=[next(r for r in data['lods'] if r['id']=='PineTall_'+v and r['lod']==0) for v in 'ABC']+preview['comparisonModels']
labels=['PINE_TALL A','PINE_TALL B','PINE_TALL C','PINE v04 A','FOREST v03 FIR','POPLAR v04_04 A']
for i,(row,label) in enumerate(zip(rows,labels)):
    x=832+(i+.5)*576;center(x,1880,label,29,True)
    width=row.get('crownWidth',row.get('width'));center(x,1930,f'H {row["height"]:.2f} m / W {width:.2f} m',26,color=muted);center(x,1976,f'LOD0 {row["triangles"]:,} tris',28,color=muted)
    center(x,2020,'NEW / APPROVAL CANDIDATE' if i<3 else 'APPROVED / UNCHANGED',23)
d.line((32,2100,4288,2100),fill='#BCC6B6',width=3)
text(32,2135,'PINE_TALL A / CLUMPS, BRANCHES + DEAD STUBS',33,True)
sheet.paste(Image.open(ROOT/'Preview/PineTall_A_clumps_stubs_v01_02.png').convert('RGB'),(32,2200))
text(1590,2135,'PINE_TALL A / RAGGED UPPER CROWN',31,True)
sheet.paste(Image.open(ROOT/'Preview/PineTall_A_crown_v01_02.png').convert('RGB'),(1590,2200))
x=3010;text(x,2190,'NARROW, OPEN CROWN',36,True)
for j,line in enumerate(['Staggered branch heights and lengths.','Folded needle clusters at the tips.','Sky pockets between branch clumps.','Pointed leader; bare lower third.','Warm reddish bark; no smooth cone.']):text(x,2260+j*53,line,27)
text(x,2580,'FINAL LOD BUDGETS',33,True)
for j,s in enumerate(data['variants']):
    rr=[next(r for r in data['lods'] if r['id']==s['id'] and r['lod']==lod) for lod in range(3)]
    y=2650+j*145;text(x,y,s['id'].replace('PineTall_','Variant '),29,True)
    text(x,y+43,' / '.join(f'{r["triangles"]:,}' for r in rr)+' triangles',28)
    text(x,y+84,f'{s["clusters"]} clumps / {s["mainBranches"]} branches / {s["deadStubs"]} dead stubs',26,color=muted)
text(x,3125,'SHARED V19WIND / STIFF',32,True)
text(x,3180,'3 LODs + cull recipe; two trunk capsules.',27)
text(x,3230,'Base pivot; metres; intended native sizes.',27)
text(x,3280,'Nine exported LODs reimported and checked.',27)
text(x,3330,'Existing generic shader; no model wind code.',27)
for j,(name,color) in enumerate(data['palette'].items()):
    xx=x+j*395;d.rectangle((xx,3420,xx+345,3490),fill=color);text(xx,3510,name,26);text(xx,3550,color,24,color=muted)
text(x,3660,'BLENDER ONLY',37,True)
text(x,3720,'No Pine_Tall import or placement in i09.',28)
text(x,3770,'i10 waits for Fedya’s separate go.',28)
text(32,3990,'Common-scale comparison models are appended read-only. Close-ups are enlarged. Reference photo is supplied by Fedya.',28,color=muted)
text(32,4040,'Pine_Tall A/B/C v01_02 is the final preview candidate; the initial v01 build remains preserved. Awaiting visual approval.',28,True)
sheet.save(OUT)
(ROOT/'sheet_manifest_v01.json').write_text(json.dumps({'sheet':str(OUT),'candidate':'PineTall A/B/C v01_02','dimensions':list(sheet.size),'pixelsPerMetre':72,'reference':str(GAME/'ArtSource/References/Trees/REF_FEDYA_pine_tall_v01.png'),'lineup':'Preview/PineTall_lineup_v01_02.png','closeups':['Preview/PineTall_A_clumps_stubs_v01_02.png','Preview/PineTall_A_crown_v01_02.png']},indent=2));print('SHEET_SAVED',OUT)
