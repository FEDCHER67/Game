"""Build driver for Forest v02 (clips_forest_v02): same commands as build_forest.py, stems <Clip>_v02.

  blender -b --factory-startup --python build_forest_v02.py -- --clip all --final
  blender -b --factory-startup --python build_forest_v02.py -- --clip all --manifest <abs>/forest_manifest_v02.json
  blender -b --factory-startup --python build_forest_v02.py -- --clip all --review <abs dir> --saved <this folder>
          --every 1 --seq --views three_quarter --res 480

The face track (clips_forest_v02.FACE_*) is keyed on the Face mesh shape keys (Blink, Surprised, Worried, Happy) of the
saved .blend as action <Clip>_Face, AFTER the FBX export, so the FBX stays one armature take; Unity gets the same track
from the manifest ('face_track': [time s, shape, weight]) for GreyboxFace. Previews set the junkie face from it.
"""
from pathlib import Path
import sys, json, types
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
for _p in (str(HERE.parent / 'Crowd_v01'), str(HERE)):
    if _p not in sys.path:
        sys.path.insert(0, _p)
import bpy
import build_forest as BF
import acting_core as C
import clips_forest_v02 as V2

REG = types.SimpleNamespace(CLIPS=V2.CLIPS, CONTRACTS=V2.CONTRACTS, PLACEMENT=V2.PLACEMENT)
BF.REG = REG
BF.REV = V2.REV
BF.BC.CC = REG
BF.BC.REV = V2.REV
_final = BF.final
_manifest = BF.manifest


def key_face(name):
    face = bpy.data.objects['Face']
    sk = face.data.shape_keys
    track = REG.CLIPS[name]['face']
    sk.animation_data_create()
    act = bpy.data.actions.new(name + '_Face')
    sk.animation_data.action = act
    for t, d in track.keys:
        for s, v in d.items():
            if s in sk.key_blocks:
                sk.key_blocks[s].value = v
                sk.key_blocks[s].keyframe_insert('value', frame=1 + t * C.FPS)
    for fc in C.fcurves_of(act):
        for kp in fc.keyframe_points:
            kp.interpolation = 'LINEAR'
    return act


def final(A, name, act, N, info, dest):
    _final(A, name, act, N, info, dest)          # .blend + FBX (armature only, one take)
    key_face(name)
    bpy.ops.wm.save_mainfile(filepath=str(dest / (BF.stem(name) + '.blend')))
    rep = dest / (BF.stem(name) + '_authoring.json')
    d = json.loads(rep.read_text(encoding='utf-8'))
    d.pop('face_hints', None)
    d['face_track'] = REG.CLIPS[name]['face'].listing()
    d['face_note'] = 'keyed in the .blend as action %s_Face (Face shape keys); not in the FBX' % name
    d['revision_of'] = '%s_v01 (owner: simpler, pose-to-pose, face snaps)' % name
    rep.write_text(json.dumps(d, indent=2), encoding='utf-8')


def manifest(path):
    _manifest(path)
    p = Path(path)
    d = json.loads(p.read_text(encoding='utf-8'))
    d.pop('face_hints', None)
    d['face_track_format'] = '[time s, shape, weight] at each key; linear between keys; a snap = keys 1-2 frames apart'
    for n in d['clips']:
        d['clips'][n]['face_track'] = REG.CLIPS[n]['face'].listing()
        d['clips'][n]['file'] = BF.stem(n) + '.fbx'
    p.write_text(json.dumps(d, indent=2), encoding='utf-8')


BF.final = final
BF.manifest = manifest

if __name__ == '__main__':
    BF.main()
