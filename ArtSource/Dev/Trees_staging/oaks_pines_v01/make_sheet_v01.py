from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import json
ROOT=Path(__file__).parent;GAME=ROOT.parents[3]
OUT=GAME/'Working/Reviews/Trees/oaks_pines_v01.png';assert not OUT.exists(),OUT
v=json.loads((ROOT/'validation_candidates_v01_02.json').read_text());m=json.loads((ROOT/'preview_manifest_v01_02.json').read_text());sizes=json.loads((ROOT/'map_sizes_v01.json').read_text())['summary']
assert json.loads((ROOT/'fbx_roundtrip_v01_02.json').read_text())['status']=='PASS'
sheet=Image.new('RGB',(4162,3790),'#EAEDE4');d=ImageDraw.Draw(sheet);ink='#233D2E';muted='#57665A';line='#BCC6B6'
def font(n,bold=False):return ImageFont.truetype('C:/Windows/Fonts/'+('segoeuib.ttf' if bold else 'segoeui.ttf'),n)
def text(x,y,s,n=30,bold=False,color=ink):d.text((x,y),s,font=font(n,bold),fill=color)
def center(x,y,s,n=29,bold=False,color=ink):
    f=font(n,bold);d.text((x-d.textlength(s,font=f)/2,y),s,font=f,fill=color)
text(40,25,'COZY OAKS + UMBRELLA PINES / v01',60,True)
text(42,105,'Blender approval candidate  /  Measured i08 map dimensions  /  Shared Hamlet daylight  /  All lineup trees at 72 pixels per metre',29,color=muted)
centers=[40+(x+20)*72 for x in m['positionsXM']]
for family,heading,y,caption in [('Oak',165,225,1088),('Pine',1218,1278,2442)]:
    text(40,heading,('OAKS / ROUND, FULL CROWNS' if family=='Oak' else 'PINES / HIGH, FLAT UMBRELLA CROWNS'),34,True)
    im=Image.open(ROOT/'Preview'/f'{family}_lineup_v01_02.png').convert('RGB');sheet.paste(im,(40,y))
    for k,(x,label) in enumerate(zip(centers,['CURRENT / MEDIAN MAP SIZE',family.upper()+' A',family.upper()+' B',family.upper()+' C'])):
        center(x,caption,label,28,True)
        row=m['references']['Current_'+family] if k==0 else next(r for r in v['lods'] if r['id']==family+'_'+'ABC'[k-1] and r['lod']==0)
        h=row['height'];w=row.get('width',row.get('crownWidth'));t=row['triangles']
        center(x,caption+38,f'H {h:.2f} m  /  crown W {w:.2f} m',27,color=muted)
        center(x,caption+72,f'LOD0  {t:,} tris',27,color=muted)
    text(40,caption+111,'Placeholder and A/B/C share the measured family median envelope; each individual map instance will retain its own size after approval.',22,color=muted)

rx=2970;text(rx,165,'APPROVED / SCALE + STYLE',32,True)
sheet.paste(Image.open(ROOT/'Preview/Approved_style_scale_v01_02.png').convert('RGB'),(rx,225))
names=['Apple_A_v04_03','Poplar_A_v04_04','Forest_Fir_v03_04'];labels=['APPLE A / v04_03','POPLAR A / v04_04','FOREST FIR / v03_04']
for x,name,label in zip(m['approvedPositionsXM'],names,labels):
    x=rx+(x+8)*72;r=m['references'][name]
    center(x,1392,label,23,True);center(x,1429,f'H {r["height"]:.2f} / W {r["width"]:.2f} m',22,color=muted);center(x,1463,f'{r["triangles"]:,} tris',23,color=muted)
text(rx,1535,'ACTUAL i08 MAP SIZES',32,True)
for i,family in enumerate(['Oak','Pine']):
    s=sizes[family];y=1590+i*165
    text(rx,y,f'{family.upper()}  /  {s["count"]:,} instances',29,True)
    text(rx,y+44,f'Median: H {s["heightMedian"]:.2f} m  /  W {s["widthMedian"]:.2f} m',27)
    text(rx,y+84,f'Range H {s["heightRange"][0]:.2f}–{s["heightRange"][1]:.2f} m',25,color=muted)
    text(rx,y+119,f'Range W {s["widthRange"][0]:.2f}–{s["widthRange"][1]:.2f} m',25,color=muted)
text(rx,1960,'EXISTING PALETTE',32,True)
for i,k in enumerate(['Bark','LeafDark','Leaf','LeafLight','LeafPine']):
    x=rx+i*226;d.rectangle((x,2020,x+190,2100),fill=v['palette'][k]);text(x,2115,k,24,color=muted)
text(rx,2200,'6 models / 18 LOD meshes',30,True)
text(rx,2250,'Two trunk capsule recipes per tree.',28)
text(rx,2300,'Opaque folded foliage; visible branch networks.',27)
text(rx,2350,'Shared V19Wind materials staged.',28)
text(rx,2400,'Pine wind is stiffer than oak wind.',28)
text(rx,2470,'Unity integration awaits Fedya’s approval.',28,True)

text(40,2620,'OAK A / FOLDED LEAVES + INTERNAL BRANCHES',31,True)
text(1500,2620,'PINE A / NEEDLE CLUSTERS + CROWN BRANCHES',31,True)
for family,x in [('Oak',40),('Pine',1500)]:
    im=Image.open(ROOT/'Preview'/f'{family}_detail_v01_02.png').convert('RGB');im=im.resize((1420,947),Image.Resampling.LANCZOS);sheet.paste(im,(x,2680))
text(40,3644,'Actual Oak A crown detail / enlarged',27,color=muted);text(1500,3644,'Actual Pine A crown detail / enlarged',27,color=muted)
text(40,3715,'Final candidates: Oak A/B/C v01_02 + Pine A/B/C v01.  Approved leafy v04, Forest v03, bare trees, rocks and all Unity assets untouched.',27,True)
sheet.save(OUT)
(ROOT/'sheet_manifest_v01.json').write_text(json.dumps({'sheet':str(OUT),'candidate':'Oak v01_02 / Pine v01','lineupsPixelsPerMetre':72,'lineupImages':[f'{f}_lineup_v01_02.png' for f in ['Oak','Pine']],'references':'Approved_style_scale_v01_02.png','closeups':[f'{f}_detail_v01_02.png' for f in ['Oak','Pine']],'dimensions':[4162,3790]},indent=2))
print('Saved',OUT)
