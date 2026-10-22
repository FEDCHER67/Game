"""opt_v01 for the 14 Sausage Buddy models of Vadim's commit 976100c7 (W86, 2026-10-22). Blender 5.2, background.

  blender -b --factory-startup --python ArtSource/Characters/SAUSAGE_BUDDY_01/Types_opt_v01/build_types_opt_v01_w86.py -- [--types A,B] [--summary]

Runs build_types_opt_v01.optimise() unchanged (same budget, tolerances, hidden-face poses, decimation limits, weight
clean-up, export) on this POOL instead of the hard-coded one. Outputs SAUSAGE_BUDDY_<TYPE>_vNN_opt_v01.{blend,fbx} into
this folder (never overwritten). Reports go to reports/<TYPE>.json, or reports/<TYPE>_vNN.json when the type already has a
report of an older revision (the CONSTR updates), so no earlier report is overwritten. --summary writes
opt_report_opt_v01_w86.json and prints the table.

Per-type exceptions, each found on the review renders (Eevee, back-face culling, 1.2 m) and fixed at the smallest cost:
- FREEZE (materials whose name starts with a prefix are not decimated):
  VIP_BEASTMAN_Logo: the kitten logo (chest, cap) is a stack of decal layers 0.6-0.8 mm apart (Ring / Logo / Bg / Kitten),
  below TOL; each material is measured only against itself, and Logo_Bg moved up to 1.9 mm, showing through the
  kitten's face. +1.3k tris.
  CONSTR_INDIAN_Hair: the decimated glossy black hair got a bright highlight blotch behind the ear (side view; the
  accepted v07 opt has the same blotch). +374 tris.
- KEEP_HIDDEN (faces of these materials are never removed as hidden):
  VIP_BEASTMAN_Jeans: step 1 opened a hole at the back of the left rolled cuff (the 64-ray test sees the narrow fold as
  covered). +270 tris.
"""
import argparse, json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.dont_write_bytecode = True
import build_types_opt_v01 as B   # noqa: E402

POOL_W86 = [("CONSTR_INDIAN", 8), ("CONSTR_MEXICAN", 5), ("CONSTR_UZBEK", 5),
            ("HAMLET_MUZHIK", 1), ("OLD_POPKING", 1),
            ("POLICE_THIN", 2), ("POLICE_FAT", 2), ("FBI_AGENT", 1), ("ARMY_SOLDIER", 1), ("TRAMDURO", 1),
            ("VIP_BEASTMAN", 1), ("VIP_SPEEDSTER", 1), ("VIP_BLINDFOLD", 1), ("HAMLET_HUNTER_GRANDPA", 1)]
FREEZE = {'VIP_BEASTMAN': ('VIP_BEASTMAN_Logo',), 'CONSTR_INDIAN': ('CONSTR_INDIAN_Hair',)}   # see above
KEEP_HIDDEN = {'VIP_BEASTMAN': ('VIP_BEASTMAN_Jeans',)}
_freeze = ()
_keep_hidden = ()
_protect_group = B.protect_group
_hidden_faces = B.hidden_faces


def protect_group(ob, only=None):
    """B.protect_group; a frozen material reports no free vertex, so decimate() skips it (the others never touch it)."""
    group, free = _protect_group(ob, only)
    if only is not None and _freeze and ob.data.materials[only].name.startswith(_freeze):
        return group, 0
    return group, free


def hidden_faces(rig, cover, candidates):
    """B.hidden_faces without the faces of the KEEP_HIDDEN materials."""
    left = _hidden_faces(rig, cover, candidates)
    if _keep_hidden:
        for o in candidates:
            mats, polys = o.data.materials, o.data.polygons
            left[o.name] = {fi for fi in left[o.name] if not mats[polys[fi].material_index].name.startswith(_keep_hidden)}
    return left


B.protect_group = protect_group
B.hidden_faces = hidden_faces


def report_path(reports, tid, rev):
    p = reports / f'{tid}.json'
    if p.exists() and json.loads(p.read_text(encoding='utf-8')).get('revision') != rev:
        return reports / f'{tid}_v{rev:02d}.json'
    return p


def main():
    global _freeze, _keep_hidden
    ap = argparse.ArgumentParser()
    ap.add_argument('--types', default='')
    ap.add_argument('--summary', action='store_true')
    args, _ = ap.parse_known_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])
    want = [t for t in args.types.split(',') if t]
    reports = HERE / 'reports'; reports.mkdir(exist_ok=True)
    if args.summary:
        merged, rows = {}, []
        for tid, rev in POOL_W86:
            p = report_path(reports, tid, rev)
            if not p.exists():
                continue
            r = json.loads(p.read_text(encoding='utf-8'))
            merged[tid] = r
            after = r['total_after'] if r['result'] == 'optimised' else r['total_before']
            rows.append((r['total_before'], tid, rev, after, r['result']))
        (HERE / f'opt_report_{B.TAG}_w86.json').write_text(json.dumps(merged, indent=1, ensure_ascii=False), encoding='utf-8')
        for before, tid, rev, after, res in sorted(rows, reverse=True):
            print(f'[SUM] {tid:<22} v{rev:02d} {before:>6} -> {after:>6}  {100 * (1 - after / before):5.1f} %  {res}')
        print(f'[SUM] total {sum(r[0] for r in rows)} -> {sum(r[3] for r in rows)}')
        return
    settings = {'budget_tris': B.BUDGET, 'tolerance_mm': {k: round(v * 1000, 3) for k, v in B.TOL.items()},
                'min_gain': B.MIN_GAIN, 'normal_mean_deg': B.NORMAL_MEAN_DEG, 'normal_p98_deg': B.NORMAL_P98_DEG,
                'small_part_faces': B.SMALL_PART, 'poses': [f'{a}:{f}' if a else 'rest' for a, f in B.POSES]}
    for tid, rev in POOL_W86:
        if want and tid not in want:
            continue
        rp = report_path(reports, tid, rev)
        if rp.exists():
            sys.exit(f'Refusing to overwrite {rp}')
        _freeze = FREEZE.get(tid, ())
        _keep_hidden = KEEP_HIDDEN.get(tid, ())
        rep = B.optimise(tid, rev, HERE)
        rep['settings'] = settings
        if _freeze:
            rep['frozen_material_prefixes'] = list(_freeze)
        if _keep_hidden:
            rep['keep_hidden_material_prefixes'] = list(_keep_hidden)
        print(f"[OPT] {tid} v{rev:02d} {rep['total_before']} -> {rep.get('total_after', rep['total_before'])} {rep['result']} "
              f"{rep.get('problems', '')}", flush=True)
        rp.write_text(json.dumps(rep, indent=1, ensure_ascii=False), encoding='utf-8')


if __name__ == '__main__':
    main()
