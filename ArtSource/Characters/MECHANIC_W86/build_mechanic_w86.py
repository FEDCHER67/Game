"""Build the MECHANIC_W86 character through the unchanged Sausage Buddy type pipeline (Blender 5.2, background).

  blender -b --factory-startup --python ArtSource/Characters/MECHANIC_W86/build_mechanic_w86.py -- --variant MECHANIC_W86 --revision 1 --no-render
  (--stage dress --prev <dir> : quick review renders, no export)

What it does: registers the MECHANIC_W86 type (mechanic_w86_type.py) into buddy_types in memory, names the carried
wrench mesh 'Wrench_RightHand' instead of the pipeline's 'Props_RightHand' (so the game's NpcHeldProps never drops it),
then runs the text of SAUSAGE_BUDDY_01/build_buddy.py with two substitutions only: the output folder is this folder and
the file stem is MECHANIC_W86_vNN (not SAUSAGE_BUDDY_<TYPE>_vNN). Body, face, rig fit, dressing, belly reshape, clips,
grounding, validation and the FBX export are the pipeline's own code. Nothing in SAUSAGE_BUDDY_01 is written.
Never overwrites a revision (build_buddy.py refuses)."""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
BUDDY = HERE.parent / 'SAUSAGE_BUDDY_01'
sys.dont_write_bytecode = True
sys.path.insert(0, str(BUDDY))
sys.path.insert(0, str(HERE))

import buddy_types as T          # noqa: E402  (loads the district pools)
import buddy_wear as W           # noqa: E402
import mechanic_w86_type as MT   # noqa: E402

MT.register()
_prop_group = W.prop_group


def prop_group(bone):
    """The mechanic's wrench is not a droppable hand prop: its own mesh name."""
    return 'Wrench_RightHand' if bone in ('RightHand', 'RightForeArm') else _prop_group(bone)


W.prop_group = prop_group
_manifest = T.manifest


def manifest(name):
    m = _manifest(name)
    if name == MT.TID:
        m['hand_props_note'] = ('Wrench_RightHand: the wrench, rigid on mixamorig:RightHand; never dropped (deliberately not '
                                'named Props_*Hand, so NpcHeldProps ignores it). Grip: Grip_R finger pose, see MECHANIC_W86 notes JSON.')
    return m


T.manifest = manifest

src = (BUDDY / 'build_buddy.py').read_text(encoding='utf-8')
SUBS = [("BASE_DIR = HERE / 'Types' / TYPE if TYPE else HERE", "BASE_DIR = MECH_OUT_DIR"),
        ("STEM = f'SAUSAGE_BUDDY_{args.variant}_{REV}'", "STEM = f'{args.variant}_{REV}'")]
for a, b in SUBS:
    assert src.count(a) == 1, f'build_buddy.py changed: {a!r} not found exactly once'
    src = src.replace(a, b)
glob = {'__name__': '__main__', '__file__': str(BUDDY / 'build_buddy.py'), 'MECH_OUT_DIR': HERE}
exec(compile(src, str(BUDDY / 'build_buddy.py'), 'exec'), glob)
