from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import json
ROOT=Path(__file__).parent;OLD=ROOT.parent/'pine_tall_v03';GAME=ROOT.parents[3]
OUT=GAME/'Working/Reviews/Trees/pine_tall_v04.png';assert not OUT.exists()
data=json.loads((ROOT/'validation_v04_04.json').read_text());before=json.loads((OLD/'validation_v03.json').read_text());full=json.loads((ROOT/'fullness_measurement_v04_04.json').read_text())
assert json.loads((ROOT/'fbx_roundtrip_v04_04.json').read_text())['status']=='PASS'
assert json.loads((ROOT/'structure_validation_v04_04.json').read_text())['status']=='PASS'
assert json.loads((ROOT/'geometry_identity_v04_04.json').read_text())['status']=='PASS'
sheet=Image.new('RGB',(4320,4100),'#EAEDE4');d=ImageDraw.Draw(sheet);ink='#233D2E';muted='#57665A'
def font(n,b=False):return ImageFont.truetype('C:/Windows/Fonts/'+('segoeuib.ttf' if b else 'segoeui.ttf'),n)
def text(x,y,s,n=30,b=False,color=ink):d.text((x,y),s,font=font(n,b),fill=color)
def center(x,y,s,n=28,b=False,color=ink):
    f=font(n,b);d.text((x-d.textlength(s,font=f)/2,y),s,font=f,fill=color)
text(32,22,'COZY PINE_TALL / v04 / APPROXIMATELY 40% FULLER CROWNS',49,True)
text(34,102,'Eight extra main limbs + two intermediate twigs per tree / longer lateral reach / ten extra clumps / Hamlet daylight',29,color=muted)
ref=Image.open(GAME/'ArtSource/References/Trees/REF_FEDYA_pine_tall_v01.png').convert('RGB').resize((660,880),Image.Resampling.LANCZOS)
sheet.paste(ref,(52,300));text(52,205,'FEDYA’S REFERENCE',31,True)
text(52,1210,'Sierra mountain pine',30,True);text(52,1265,'Photographic structure reference.',25,color=muted);text(52,1310,'The photo has no metric scale.',25,color=muted)
for j,line in enumerate(['Intermediate limbs fill gaps','Longer, irregular side branches','Larger, overlapping needle tufts','Same height and bare lower trunk']):text(52,1430+j*65,line,27)
sheet.paste(Image.open(ROOT/'Preview/PineTall_lineup_v04_03.png').convert('RGB'),(832,180))
for i,(variant,revision) in enumerate([(v,r) for v in 'ABC' for r in (3,4)]):
    source=before if revision==3 else data;row=next(r for r in source['lods'] if r['id']=='PineTall_'+variant and r['lod']==0)
    x=832+(i+.5)*576;center(x,1880,f'{variant} / v0{revision} / '+('BEFORE' if revision==3 else 'AFTER'),29,True)
    center(x,1930,f'H {row["height"]:.2f} m / W {row["crownWidth"]:.2f} m',26,color=muted)
    center(x,1976,f'{row["mainBranches"]} branches / {row["triangles"]:,} tris',27)
    center(x,2020,f'{row["clusters"]} clumps / {row["leafPlates"]:,} needle plates',23,color=muted)
d.line((32,2100,4288,2100),fill='#BCC6B6',width=3)
text(32,2135,'BEFORE / v03 A',31,True);text(1590,2135,'AFTER / v04 A',31,True)
sheet.paste(Image.open(OLD/'Preview/PineTall_A_clumps_stubs_v03.png').convert('RGB'),(32,2200))
sheet.paste(Image.open(ROOT/'Preview/PineTall_A_clumps_stubs_v04_03.png').convert('RGB'),(1590,2200))
x=3170;text(x,2200,'MEASURED FOLIAGE COVERAGE',29,True)
for j,row in enumerate(full['rows']):text(x,2265+j*55,f'{row["id"][-1]}: +{row["meanProjectedFoliageIncreasePercent"]:.1f}% vs v03',30)
for j,line in enumerate(['Average opaque foliage silhouette area','from four sides, at identical scale.','A visual-fullness proxy, not a volume unit.']):text(x,2455+j*43,line,23,color=muted)
text(x,2630,'BRANCHES / CLUMPS',30,True)
for j,s in enumerate(data['variants']):text(x,2690+j*55,f'{s["id"][-1]}: {s["previousMainBranches"]} > {s["mainBranches"]} limbs / {s["previousClusters"]} > {s["clusters"]} clumps',27)
text(x,2910,'LOD0 / LOD1 / LOD2 TRIANGLES',28,True)
for j,s in enumerate(data['variants']):
    counts=[next(r['triangles'] for r in data['lods'] if r['id']==s['id'] and r['lod']==lod) for lod in range(3)]
    text(x,2970+j*55,s['id'][-1]+': '+' / '.join(f'{n:,}' for n in counts),28)
text(x,3190,'CHECKED IN BLENDER',30,True)
for j,line in enumerate(['17 plates per clump; more/larger clumps.','Trunk, roots and dead stubs preserved.','Six capsules and shared wind unchanged.','3 LODs; base pivots; below 8k tris.']):text(x,3255+j*48,line,25)
for j,(name,color) in enumerate(data['palette'].items()):
    xx=x+j*355;d.rectangle((xx,3500,xx+310,3565),fill=color);text(xx,3585,name,24)
text(x,3700,'BLENDER ONLY / AWAITING OK',30,True);text(x,3760,'Final candidate: A/B/C v04_04.',26)
text(32,3970,'Full trees and before / after close-ups use the same cameras, Hamlet lighting and scale. Previous models remain preserved.',28,color=muted)
text(32,4020,'No Unity import, map placement or commits. v04_04 uses the rendered v04_03 geometry unchanged, with corrected width metadata.',27)
sheet.save(OUT)
(ROOT/'sheet_manifest_v04.json').write_text(json.dumps(dict(sheet=str(OUT),candidate='PineTall A/B/C v04_04',dimensions=list(sheet.size),pixelsPerMetre=72,lineupOrder=['v03 A','v04 A','v03 B','v04 B','v03 C','v04 C'],renderSource='Preview/*_v04_03.png',geometryIdentity='geometry_identity_v04_04.json'),indent=2))
print('SHEET_SAVED',OUT)
