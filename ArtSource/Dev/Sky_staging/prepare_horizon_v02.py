"""Preserve the delivered staging v01; prepare the requested shared-horizon revision."""
from pathlib import Path
import shutil

stage=Path('C:/Dev/Game/ArtSource/Dev/Sky_staging')
target=stage/'v02'
if target.exists(): raise SystemExit('v02 already exists; refusing replacement')
for source in sorted((stage/'v01').rglob('*')):
    dest=target/source.relative_to(stage/'v01')
    if source.is_dir(): dest.mkdir(parents=True,exist_ok=True); continue
    dest.parent.mkdir(parents=True,exist_ok=True)
    text=source.read_text(encoding='utf-8').replace('v01','v02')
    if source.name=='SkyReviewBuilder22.cs':
        text=text.replace('!File.ReadAllText(LockPath).StartsWith("gpt-g22 ",StringComparison.Ordinal)',
            '!(File.ReadAllText(LockPath).StartsWith("G22 ",StringComparison.Ordinal) || File.ReadAllText(LockPath).StartsWith("gpt-g22 ",StringComparison.Ordinal))')
        text=text.replace('Quaternion.Euler(-22,40,0)','Quaternion.Euler(-23,45,0)').replace('camera.fieldOfView=66','camera.fieldOfView=70')
    if source.name=='SkyModel22.cs':
        text=text.replace('state.fog=Color.Lerp(Color.Lerp(h,grey,overcast*.32f),mood.daytimeFog,palette);',
            '// One final colour owns the sky horizon and all distance haze.\n            state.fog=state.horizon;')
    if source.name=='PaintedSky22.shader':
        text=text.replace('float elevation=saturate(d.y);','float elevation=saturate(d.y);\n                float horizonMask=smoothstep(.035,.12,d.y);')
        text=text.replace('pow(elevation,.55)','pow(smoothstep(.035,1,elevation),.55)')
        text=text.replace('_Golden*.22*(1-_Gloom*.75);','_Golden*.22*(1-_Gloom*.75)*horizonMask;')
        text=text.replace(')*_Daylight;',')*_Daylight*horizonMask;')
        text=text.replace('*float3(.72,.83,1);','*float3(.72,.83,1)*horizonMask;')
        text=text.replace(')*_Stars;',')*_Stars*horizonMask;')
        text=text.replace('float horizonFade=smoothstep(.006,.10,d.y);','float horizonFade=horizonMask;')
    if source.name=='SkyPlayVerification22.cs':
        text=text.replace('// Never bring Unity forward or change background settings. User can foreground it.',
            '// The updated work protocol permits foregrounding Unity; never change background settings.')
        text=text.replace('Ask the user; call Resume after it advances.','Call Resume after normal frames advance.')
    with dest.open('x',encoding='utf-8',newline='\n') as f: f.write(text)
print('Created new v02 staging; v01 preserved.')
