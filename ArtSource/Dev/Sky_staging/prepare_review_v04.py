"""Prepare the final review candidate without replacing earlier deliverables."""
from pathlib import Path
stage=Path('C:/Dev/Game/ArtSource/Dev/Sky_staging');target=stage/'v04'
if target.exists():raise SystemExit('v04 already exists')
for p in sorted((stage/'v03').rglob('*')):
    dest=target/p.relative_to(stage/'v03')
    if p.is_dir():dest.mkdir(parents=True,exist_ok=True);continue
    s=p.read_text(encoding='utf-8').replace('v03','v04').replace('Sky22V03','Sky22V04').replace('G22V03','G22V04')
    if p.name=='SkyModel22.cs':s=s.replace('cloudCover=.38f, gloom=0','cloudCover=.28f, gloom=0')
    if p.name=='SkyReviewCapture22.cs':s=s.replace('overcast?.97f:.38f','overcast?.97f:.28f').replace('sky.CloudTime=25','sky.CloudTime=650')
    if p.name=='SkyReviewBuilder22.cs':
        s=s.replace('renderer.Configure(clock,sky,sun,moon);','renderer.Configure(clock,sky,sun,moon);renderer.CloudTime=650;')
        s=s.replace('tone.mode.value=TonemappingMode.ACES;','tone.mode.value=TonemappingMode.ACES;\n                var grade=profile.Add<ColorAdjustments>(true);grade.postExposure.value=.35f;')
    if p.name=='SkyRenderer22.cs':
        s=s.replace('public SkyState22 LastState { get; private set; }','public SkyState22 LastState { get; private set; }\n        // G18g can consume this per-camera result once its horizon API exists. Colours are Unity gamma-space Color values.\n        public event System.Action<Camera,Color> HorizonColourEvaluated;')
        s=s.replace('LastState=state;','LastState=state;HorizonColourEvaluated?.Invoke(camera,state.horizon);')
    if p.name=='PaintedSky22.shader':
        s=s.replace('star*step(.975,h)*(.45+hash31(a+8)*1.8)','star*step(.984,h)*(.35+hash31(a+8)*1.3)')
        s=s.replace('sky+=_MoonColour.rgb*(moonDisc*crater*1.65+exp(-md*24)*.045)*_Stars*horizonMask;',
          'sky=lerp(sky,_MoonColour.rgb*crater*1.65,moonDisc*saturate(_Stars*2)*horizonMask);\n                sky+=_MoonColour.rgb*exp(-md*24)*.045*_Stars*horizonMask;')
        s=s.replace('(n-threshold)*5.0','(n-threshold)*8.0')
    if p.name=='README.md':
        s=s.replace('0.38 cover','0.28 cover')
        s += '\nThe final per-camera `HorizonColourEvaluated(Camera, Color)` event exposes the exact shared sky/fog colour. G18g has not yet created its controller API; no connection to a nonexistent component is claimed. The existing V05 bridge and the new sky/fog pixel test are separate from that pending G18g integration.\n'
    dest.parent.mkdir(parents=True,exist_ok=True)
    with dest.open('x',encoding='utf-8',newline='\n') as f:f.write(s)
for name in ('compile_staging','install_new_only','make_review_sheet'):
    s=(stage/(name+'_v03.py')).read_text(encoding='utf-8').replace('v03','v04').replace('Sky22V03','Sky22V04')
    with (stage/(name+'_v04.py')).open('x',encoding='utf-8',newline='\n') as f:f.write(s)
print('Created v04 review candidate; previous files preserved.')
