"""Front reference comparison using the actual unchanged organs."""
import sys,types
from pathlib import Path
import bpy
HERE=Path(__file__).resolve().parent
R=types.ModuleType('g38_reference_render');R.__file__=str(HERE/'render_review_v03.py')
s=Path(R.__file__).read_text(encoding='utf-8');exec(compile(s[:s.rfind('\nmain()')],R.__file__,'exec'),R.__dict__)
R.OUT=Path(sys.argv[sys.argv.index('--out')+1]) if '--out' in sys.argv else Path('C:/Dev/Game/Working/Reviews/Operations/organs_v03/G38_work/four03_render');R.OUT.mkdir(exist_ok=True);R.ONLY=None
for o in bpy.context.scene.objects:o.hide_render=o.type=='MESH' and not o.name.startswith(('RIB_','STERNUM_','SPINE_','ORGAN_','VESSELS_','AIRWAY_','DIAPHRAGM'))
cam=R.setup()
R.shoot(cam,'00_reference_front',(0,-.85,1.24),(0,-.015,1.085),ortho=.36,res=(1400,1400))
