"""Build stage of PLAYER_SAUSAGE_W86 through the unchanged Sausage Buddy type pipeline (Blender 5.2, background).

  blender -b --factory-startup --python ArtSource/Characters/PLAYER_SAUSAGE_W86/build_player_w86.py -- --variant PLAYER --revision 1 --no-render --work <scratch dir>

What it does: registers the PLAYER type (player_w86_parts.py: base shoes/socks + every option of every aspect, each
object tagged with its part id) into buddy_types in memory, then runs the text of SAUSAGE_BUDDY_01/build_buddy.py with
three substitutions only:
  - the output folder is --work (this stage's .blend/.fbx/.json are intermediates for post_player_w86.py);
  - the file stem is PLAYER_SAUSAGE_W86_vNN;
  - instead of joining every garment into one 'Outfit', the garments are joined per part id (Shoes, Socks, Top_01 ...),
    each skinned to the rig; 'Shoes' takes the Outfit's place (floor contact), the rest ride along with the props list
    (exported, validated, never counted for floor contact).
Body, face, rig fit, dressing, clips, grounding, validation and the FBX export are the pipeline's own code. Nothing in
SAUSAGE_BUDDY_01 is written. Never overwrites a revision (build_buddy.py refuses)."""
import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
BUDDY = HERE.parent / 'SAUSAGE_BUDDY_01'
sys.dont_write_bytecode = True
sys.path.insert(0, str(BUDDY))
sys.path.insert(0, str(HERE))

ap = argparse.ArgumentParser()
ap.add_argument('--work', required=True)
args, _ = ap.parse_known_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])
WORK = Path(args.work)
WORK.mkdir(parents=True, exist_ok=True)

import buddy_types as T          # noqa: E402  (loads the district pools)
import buddy_geo as G            # noqa: E402
import player_w86_parts as PP    # noqa: E402

PP.register()


def split(garments, props, skin_to_rig):
    """Join the garments per part id; returns the 'Shoes' mesh (the pipeline's Outfit slot: floor contact)."""
    groups = {}
    for o in garments:
        pid = o.get('pl_part')
        assert pid, f'{o.name}: no part id'
        groups.setdefault(pid, []).append(o)
    made = {}
    for pid, objs in groups.items():
        pm = objs[0]
        G.join(pm, objs[1:])
        pm.name = pid
        pm.data.name = pid
        made[pid] = pm
    for pid in sorted(made):
        if pid != 'Shoes':
            skin_to_rig(made[pid])
            props.append(made[pid])
    print('[PLAYER] parts', sorted(made))
    return made['Shoes']


src = (BUDDY / 'build_buddy.py').read_text(encoding='utf-8')
SUBS = [("BASE_DIR = HERE / 'Types' / TYPE if TYPE else HERE", "BASE_DIR = PLAYER_WORK_DIR"),
        ("STEM = f'SAUSAGE_BUDDY_{args.variant}_{REV}'", "STEM = f'PLAYER_SAUSAGE_W86_{REV}'"),
        ("    outfit = garments[0]\n    G.join(outfit, garments[1:])\n    outfit.name = 'Outfit'; outfit.data.name = 'Outfit'\n",
         "    outfit = PLAYER_SPLIT(garments, props, skin_to_rig)\n")]
for a, b in SUBS:
    assert src.count(a) == 1, f'build_buddy.py changed: {a!r} not found exactly once'
    src = src.replace(a, b)
glob = {'__name__': '__main__', '__file__': str(BUDDY / 'build_buddy.py'), 'PLAYER_WORK_DIR': WORK, 'PLAYER_SPLIT': split}
exec(compile(src, str(BUDDY / 'build_buddy.py'), 'exec'), glob)
