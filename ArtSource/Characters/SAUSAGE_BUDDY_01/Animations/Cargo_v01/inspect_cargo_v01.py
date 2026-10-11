from pathlib import Path
import sys,importlib.util,json,hashlib
sys.dont_write_bytecode=True
import bpy
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('cargo',HERE/'build_cargo_v03.py')
C=importlib.util.module_from_spec(spec);spec.loader.exec_module(C)
C.open_source()
report={'source_sha256':{},'bounds':{}}
for p in C.SRC.rglob('*'):
    if p.is_file() and HERE not in p.parents:
        report['source_sha256'][str(p.relative_to(C.SRC)).replace('\\','/')]=hashlib.sha256(p.read_bytes()).hexdigest()
for name,period in C.CLIPS.items():
    C.open_source();act,lifts=C.author(name,period)
    for t in ([0,.5,.95,1.15,1.4,2.1] if name=='SitUp_Cargo' else [0,.84,1.22,1.63,period/30]):
        f=1+t*30;C.scene.frame_set(int(f),subframe=f%1)
        lo,hi=C.bounds()
        report['bounds'][f'{name}_{t}']={'min':lo.tolist(),'max':hi.tolist(),
            'hips':list(C.rig.pose.bones[C.P+'Hips'].head),
            'right_wrist':list(C.rig.pose.bones[C.P+'RightHand'].head)}
output=HERE/'source_inspection_v01.json';assert not output.exists()
output.write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report['bounds'],indent=2))
