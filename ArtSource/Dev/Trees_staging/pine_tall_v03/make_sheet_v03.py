from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import json
ROOT=Path(__file__).parent;OLD=ROOT.parent/'pine_tall_v02';GAME=ROOT.parents[3]
OUT=GAME/'Working/Reviews/Trees/pine_tall_v03.png';assert not OUT.exists()
data=json.loads((ROOT/'validation_v03.json').read_text());before=json.loads((OLD/'validation_v02.json').read_text())
assert json.loads((ROOT/'fbx_roundtrip_v03.json').read_text())['status']=='PASS'
assert json.loads((ROOT/'branch_validation_v03.json').read_text())['status']=='PASS'
sheet=Image.new('RGB',(4320,4100),'#EAEDE4');d=ImageDraw.Draw(sheet);ink='#233D2E';muted='#57665A'
def font(n,b=False):return ImageFont.truetype('C:/Windows/Fonts/'+('segoeuib.ttf' if b else 'segoeui.ttf'),n)
def text(x,y,s,n=30,b=False,color=ink):d.text((x,y),s,font=font(n,b),fill=color)
def center(x,y,s,n=28,b=False,color=ink):
    f=font(n,b);d.text((x-d.textlength(s,font=f)/2,y),s,font=f,fill=color)
text(32,22,'COZY PINE_TALL / v03 / MORE BRANCHES, SAME CLUMP DENSITY',49,True)
text(34,102,'Five new main branches on A / B / C (+18–20%) / 17 needle plates per clump unchanged / Hamlet daylight / common scale',29,color=muted)
ref=Image.open(GAME/'ArtSource/References/Trees/REF_FEDYA_pine_tall_v01.png').convert('RGB').resize((660,880),Image.Resampling.LANCZOS)
sheet.paste(ref,(52,300));text(52,205,'FEDYA’S REFERENCE',31,True)
text(52,1210,'Sierra mountain pine',30,True);text(52,1265,'Photographic structure reference.',25,color=muted);text(52,1310,'The photo has no metric scale.',25,color=muted)
for j,line in enumerate(['More limbs in crown gaps','Approved tuft density retained','Same height and crown width','Same bare trunk and dead stubs']):text(52,1430+j*65,line,27)
sheet.paste(Image.open(ROOT/'Preview/PineTall_lineup_v03.png').convert('RGB'),(832,180))
for i,(variant,revision) in enumerate([(v,r) for v in 'ABC' for r in (2,3)]):
    source=before if revision==2 else data
    row=next(r for r in source['lods'] if r['id']=='PineTall_'+variant and r['lod']==0)
    x=832+(i+.5)*576;center(x,1880,f'{variant} / v0{revision} / '+('BEFORE' if revision==2 else 'AFTER'),29,True)
    center(x,1930,f'H {row["height"]:.2f} m / W {row["crownWidth"]:.2f} m',26,color=muted)
    center(x,1976,f'{row["mainBranches"]} branches / {row["triangles"]:,} tris',27)
    center(x,2020,'17 PLATES PER CLUMP',23,color=muted)
d.line((32,2100,4288,2100),fill='#BCC6B6',width=3)
text(32,2135,'BEFORE / v02 A / 26 MAIN BRANCHES',31,True)
text(1590,2135,'AFTER / v03 A / 31 MAIN BRANCHES',31,True)
sheet.paste(Image.open(OLD/'Preview/PineTall_A_clumps_stubs_v02.png').convert('RGB'),(32,2200))
sheet.paste(Image.open(ROOT/'Preview/PineTall_A_clumps_stubs_v03.png').convert('RGB'),(1590,2200))
x=3170;text(x,2200,'FIVE EXTRA BRANCHES EACH',30,True)
for j,s in enumerate(data['variants']):
    text(x,2265+j*60,f'{s["id"][-1]}: {s["previousMainBranches"]} > {s["mainBranches"]}  (+{s["branchIncreasePercent"]:.1f}%)',30)
text(x,2490,'DENSITY RETAINED',31,True)
for j,line in enumerate(['17 separate needle plates in every clump.','Two full clumps on each new branch.','All previous limbs and stubs retained.','Existing plate outlines retained.','Six smaller folds simplified for budget.']):text(x,2555+j*50,line,25)
text(x,2860,'LOD0 / LOD1 / LOD2 TRIANGLES',28,True)
for j,s in enumerate(data['variants']):
    counts=[next(r['triangles'] for r in data['lods'] if r['id']==s['id'] and r['lod']==lod) for lod in range(3)]
    text(x,2920+j*55,s['id'][-1]+': '+' / '.join(f'{n:,}' for n in counts),28)
text(x,3140,'CHECKED IN BLENDER',30,True)
for j,line in enumerate(['All 9 LODs exported and reimported.','Opaque closed geometry; below 8k tris.','Old wood and six capsules preserved.','Shared V19Wind / stiff unchanged.','Base pivots and metre scale preserved.']):text(x,3205+j*50,line,25)
for j,(name,color) in enumerate(data['palette'].items()):
    xx=x+j*355;d.rectangle((xx,3500,xx+310,3565),fill=color);text(xx,3585,name,24)
text(x,3700,'BLENDER ONLY / AWAITING OK',30,True);text(x,3760,'No Unity changes or i10 placement.',26)
text(32,3970,'All six tree renders share scale and camera. Before / after close-ups use identical Hamlet lighting, camera and scale.',28,color=muted)
text(32,4020,'Pine_Tall v01, v01_02 and v02 remain preserved. New candidate: PineTall A/B/C v03.',29,True)
sheet.save(OUT)
(ROOT/'sheet_manifest_v03.json').write_text(json.dumps(dict(sheet=str(OUT),candidate='PineTall A/B/C v03',dimensions=list(sheet.size),pixelsPerMetre=72,lineupOrder=['v02 A','v03 A','v02 B','v03 B','v02 C','v03 C'],before='pine_tall_v02/Preview/PineTall_A_clumps_stubs_v02.png',after='Preview/PineTall_A_clumps_stubs_v03.png'),indent=2))
print('SHEET_SAVED',OUT)
