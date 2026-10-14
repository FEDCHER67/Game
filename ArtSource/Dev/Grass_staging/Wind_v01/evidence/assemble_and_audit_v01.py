from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageChops, ImageStat
import json, hashlib, re, difflib, math
root=Path(r"C:\Dev\Game")
out=root/"Working/Reviews/Wind"
font_path=r"C:\Windows\Fonts\segoeui.ttf"
bold_path=r"C:\Windows\Fonts\segoeuib.ttf"
font=lambda s:ImageFont.truetype(font_path,s)
bold=lambda s:ImageFont.truetype(bold_path,s)
sheet=Image.new("RGB",(2400,1200),(19,26,31))
draw=ImageDraw.Draw(sheet)
draw.text((30,17),"V19  /  SHARED GRASS WIND",font=bold(36),fill=(232,242,232))
draw.text((30,65),"Six Play captures • Breezy • same camera and original grass placement • 08:00 lighting held for comparison",font=font(23),fill=(185,203,196))
imgs=[]
for i in range(6):
    im=Image.open(out/f"hamlet_sequence_{i:02}_v01.png").convert("RGB")
    imgs.append(im)
    x=(i%3)*800; y=115+(i//3)*495
    sheet.paste(im.resize((800,450),Image.Resampling.LANCZOS),(x,y))
    # Identical crop in all panels makes the same blades easy to compare.
    crop=im.crop((780,450,1120,650)).resize((340,200),Image.Resampling.LANCZOS)
    sheet.paste(crop,(x+450,y+240))
    draw.rectangle((x+449,y+239,x+791,y+441),outline=(162,215,179),width=2)
    draw.rectangle((x+450,y+240,x+565,y+267),fill=(19,26,31))
    draw.text((x+458,y+243),"SAME BLADES",font=bold(15),fill=(232,242,232))
    draw.text((x+18,y+458),f"{i+1:02}  |  wind time {12+i*.8:.1f} s",font=bold(22),fill=(232,242,232))
draw.text((30,1115),"Generic material: height/pivot bend + radial flutter. Shared direction, travelling gusts and district strength.",font=font(23),fill=(201,219,208))
draw.text((30,1154),"Inherited base issue: terrain layers / some tree prototypes are missing. This wind revision preserves the original bake.",font=font(21),fill=(234,201,144))
target=out/"wind_grass_v01.jpg"
if target.exists(): raise RuntimeError("Sheet exists")
sheet.save(target,quality=94,subsampling=0)
frames=[]
for i in range(40):
    frame=Image.open(out/f"gif_{i:03}_v01.png").convert("RGB")
    d=ImageDraw.Draw(frame)
    d.rectangle((0,0,960,31),fill=(19,26,31))
    d.text((12,4),f"i05 shared wind  |  Hamlet  |  density unchanged  |  {i/10:.1f} s",font=bold(17),fill=(232,242,232))
    frames.append(frame)
palette=frames[0].quantize(colors=256,method=Image.Quantize.MEDIANCUT)
indexed=[f.quantize(palette=palette,dither=Image.Dither.NONE) for f in frames]
target=out/"wind_grass_v01.gif"
if target.exists(): raise RuntimeError("GIF exists")
indexed[0].save(target,save_all=True,append_images=indexed[1:],duration=100,loop=0,disposal=2,optimize=False)
diffs=[]
for i in range(1,6):
    diff=ImageChops.difference(imgs[0],imgs[i])
    pixels=sum(1 for p in diff.crop((0,400,1600,900)).getdata() if max(p)>5)
    diffs.append({"frame":i,"changed_grass_region_pixels":pixels,"region_pixels":800000,"full_mean_abs_rgb":ImageStat.Stat(diff).mean})
gif=Image.open(target)
result={"sheet_size":sheet.size,"gif_size":gif.size,"gif_frames":gif.n_frames,"gif_duration_ms":sum(gif.seek(i) or gif.info.get("duration",0) for i in range(gif.n_frames)),"differences":diffs}
(out/"capture_validation_v01.json").write_text(json.dumps(result,indent=2))
baseline=json.loads((root/"ArtSource/Dev/Grass_staging/Wind_v01/evidence/protected_resume_i05.json").read_text(encoding="utf-8-sig"))
modified=[];missing=[]
for key,expected in baseline.items():
    path=root/key
    if not path.exists(): missing.append(key);continue
    if hashlib.file_digest(path.open("rb"),"sha256").hexdigest().lower()!=expected.lower():modified.append(key)
before=(root/"Assets/OnlyVolunteers/Scenes/Map/Map_Look_v19_Play_i04_vanpaint.unity").read_text()
after=(root/"Assets/OnlyVolunteers/Scenes/Map/Map_Look_v19_Play_i05_wind_grass.unity").read_text()
def blocks(text):
    return {m.group(1):m.group(0) for m in re.finditer(r"^--- !u!\d+ &(-?\d+)[^\n]*\n.*?(?=^--- !u!|\Z)",text,re.M|re.S)}
a,b=blocks(before),blocks(after)
changed=[k for k in a.keys()&b.keys() if a[k]!=b[k]]
added=list(b.keys()-a.keys());removed=list(a.keys()-b.keys())
scene_diff=[]
for k in changed:
    scene_diff.extend(difflib.unified_diff(a[k].splitlines(),b[k].splitlines(),fromfile=f"i04:{k}",tofile=f"i05:{k}",lineterm=""))
integrity={"protected_files":len(baseline),"modified":modified,"missing":missing,"scene_blocks_changed":changed,"scene_blocks_added":added,"scene_blocks_removed":removed,"scene_diff":scene_diff}
(out/"integrity_i05_v01.json").write_text(json.dumps(integrity,indent=2))
print(json.dumps({"capture":result,"integrity":integrity},indent=2))

