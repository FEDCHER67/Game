from pathlib import Path
import re
ROOT=Path(__file__).parent
def revision(s):return re.sub(r'_v04(?![\d_])','_v04_02',s).replace("'v04'","'v04_02'").replace('V04_COMPLETE','V04_02_COMPLETE')
s=revision((ROOT/'build_pine_tall_v04.py').read_text())
s=s.replace("h=spec['height'];xy=meta['xyNormalization'];zs=meta['zNormalization'];lean=Vector((*spec['lean'],0))", "h=spec['height'];xy=meta['xyNormalization'];zs=meta['zNormalization'];lean=Vector((*spec['lean'],0));tuft_scale=[1.175,1.19,1.155][spec['variant']]")
s=s.replace('(Vector(mesh.v[i])-center)*1.12','(Vector(mesh.v[i])-center)*tuft_scale').replace('clumpLinearScale=1.12','clumpLinearScale=tuft_scale')
out=ROOT/'build_pine_tall_v04_02.py';assert not out.exists();out.write_text(s)
for source,target in [('render_preview_v04.py','render_preview_v04_02.py'),('validate_roundtrip_v04.py','validate_roundtrip_v04_02.py'),('measure_fullness_v04.py','measure_fullness_v04_02.py')]:
    out=ROOT/target;assert not out.exists();out.write_text(revision((ROOT/source).read_text()))
print('Prepared numbered fullness refinement v04_02; initial v04 preserved')
