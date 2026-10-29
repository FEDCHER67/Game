"""MECHANIC_W86 crowd LOD chain with the unchanged opt_v02 pipeline (Blender 5.2, background).

  blender -b --factory-startup --python ArtSource/Characters/MECHANIC_W86/lods_mechanic_w86.py -- --revision 1 --work <scratch dir>
  blender -b --factory-startup --python ArtSource/Characters/MECHANIC_W86/lods_mechanic_w86.py -- --revision 1 --work <scratch dir> --verify

Step 1 (default): SAUSAGE_BUDDY_01/Types_opt_v02/build_types_opt_v02.optimise() on MECHANIC_W86_vNN.blend as a 'source'
type (the branch the 10 pool types without an opt_v01 take): LOD0 = the source minus the Face interior nobody sees,
LOD1 (~45 %) and LOD2 (~20 %) by limit-checked collapse, FBX with <name>_LOD0/1/2 (Unity's LOD import convention), the
Idle clip only and the pipeline's export options. It writes into --work under the pipeline's stem, then copies the
results here as MECHANIC_W86_vNN_opt_v02.{blend,fbx} + lods_MECHANIC_W86_vNN_opt_v02.json (never over existing files).
Step 2 (--verify): the pipeline's verify_opt_v02 checks (rig, actions, groups, materials, shape keys, weights, bounds,
.blend and FBX) of the --work output against the source."""
import argparse, json, shutil, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
OPT = HERE.parent / 'SAUSAGE_BUDDY_01' / 'Types_opt_v02'
sys.dont_write_bytecode = True
sys.path.insert(0, str(OPT))
sys.path.insert(0, str(HERE.parent / 'SAUSAGE_BUDDY_01'))
TID = 'MECHANIC_W86'

ap = argparse.ArgumentParser()
ap.add_argument('--revision', type=int, required=True)
ap.add_argument('--work', required=True)
ap.add_argument('--verify', action='store_true')
args, _ = ap.parse_known_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])
REV = args.revision
SRC = HERE / f'{TID}_v{REV:02d}'
work = Path(args.work)
work.mkdir(parents=True, exist_ok=True)


def baseline(tid, rev):
    return SRC.with_suffix('.blend'), SRC.with_suffix('.fbx'), 'source'


if args.verify:
    import verify_opt_v02 as V
    V.baseline = baseline
    ok = V.check_blend(TID, REV, work)
    ok = V.check_fbx(TID, REV, work) and ok
    print('[VERIFY] MECHANIC_W86', 'OK' if ok else 'FAILED')
    sys.exit(0)

import build_types_opt_v02 as O   # noqa: E402
O.baseline = baseline
rep = O.optimise(TID, REV, work)
rep['input'] = SRC.with_suffix('.blend').name
print(f"[OPT] {TID} v{REV:02d} {rep['total_v01']} -> LOD0 {rep.get('total_lod0')} LOD1 {rep.get('total_lod1')} "
      f"LOD2 {rep.get('total_lod2')} {rep['result']} {rep.get('problems', '')} {rep['seconds']} s")
stem = f'SAUSAGE_BUDDY_{TID}_v{REV:02d}_{O.TAG}'
out_stem = f'{TID}_v{REV:02d}_{O.TAG}'
(work / f'{stem}.json').write_text(json.dumps(rep, indent=1, ensure_ascii=False), encoding='utf-8')
if rep['result'] == 'optimised':
    for ext in ('blend', 'fbx'):
        dst = HERE / f'{out_stem}.{ext}'
        if dst.exists():
            sys.exit(f'Refusing to overwrite {dst}')
        shutil.copyfile(work / f'{stem}.{ext}', dst)
    (HERE / f'lods_{out_stem}.json').write_text(json.dumps(rep, indent=1, ensure_ascii=False), encoding='utf-8')
    print('[OPT] written', out_stem)
