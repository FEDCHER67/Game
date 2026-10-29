"""Writes MECHANIC_W86_v01_notes.json: rig, meshes, LODs, materials, the wrench attachment, the Grip_R setup for Unity, the
clip set and the checks (Blender 5.2, background; reads the built files, never overwrites).

  blender -b --factory-startup --python ArtSource/Characters/MECHANIC_W86/notes_mechanic_w86.py"""
import json, sys
from pathlib import Path
import bpy
from mathutils import Vector

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import mech_rig as MR                      # noqa: E402
import mechanic_w86_type as MT             # noqa: E402

OUT = HERE / 'MECHANIC_W86_v01_notes.json'
if OUT.exists():
    sys.exit(f'Refusing to overwrite {OUT}')
P = MR.P
REF_TYPE = MR.BUDDY / 'Types' / 'BAD_DRUNK' / 'SAUSAGE_BUDDY_BAD_DRUNK_v04.blend'

val = json.loads((HERE / 'validation_MECHANIC_W86_v01.json').read_text(encoding='utf-8'))
lods = json.loads((HERE / 'lods_MECHANIC_W86_v01_opt_v02.json').read_text(encoding='utf-8'))
clips = json.loads((HERE / 'Animations_v01' / 'clips_mechanic_v01.json').read_text(encoding='utf-8'))

rig, rest = MR.open_model(HERE / 'MECHANIC_W86_v01.blend')
# the crowd types' rig (BAD_DRUNK v04) for a rest-pose comparison
with bpy.data.libraries.load(str(REF_TYPE), link=False) as (src, dst):
    dst.objects = [MR.RIG]
ref_rig = dst.objects[0]
ref_rest = {b.name: b.matrix_local.copy() for b in ref_rig.data.bones}
dev = max(max(abs(a - b) for ra, rb in zip(rest[n], ref_rest[n]) for a, b in zip(ra, rb)) for n in rest)
same_names = set(rest) == set(ref_rest)
bones = [{'name': b.name, 'parent': b.parent.name if b.parent else None, 'deform': b.use_deform} for b in rig.data.bones]

grip_loc = MR.hand_locals(rest, 'Right', 'grip')
hand_rest = rest[P + 'RightHand']
g = MT.WRENCH_GRIP
local_c = hand_rest.inverted() @ Vector(g['center'])
local_a = (hand_rest.to_3x3().inverted() @ Vector(g['axis'])).normalized()
keyed = MR.hand_children(rig, 'Right')

notes = {
    'asset': 'MECHANIC_W86 v01: the workshop mechanic (reference variant B, Working/Reviews/Mechanic_2026-10-29/mechanic_reference_B_chosen.webp)',
    'files': {
        'source_blend': 'ArtSource/Characters/MECHANIC_W86/MECHANIC_W86_v01.blend (LOD0 source, rig, the Sausage Buddy built-in clips)',
        'fbx_lod0_only': 'ArtSource/Characters/MECHANIC_W86/MECHANIC_W86_v01.fbx (pipeline export: Body, Face, Outfit, Wrench_RightHand, Idle take)',
        'fbx_game': 'ArtSource/Characters/MECHANIC_W86/MECHANIC_W86_v01_opt_v02.fbx (use this one: <mesh>_LOD0/_LOD1/_LOD2, Idle take; Unity LOD import naming)',
        'opt_blend': 'ArtSource/Characters/MECHANIC_W86/MECHANIC_W86_v01_opt_v02.blend',
        'validation': 'validation_MECHANIC_W86_v01.json, lods_MECHANIC_W86_v01_opt_v02.json',
        'clips': 'ArtSource/Characters/MECHANIC_W86/Animations_v01/*.fbx + clips_mechanic_v01.json + MECHANIC_W86_Anim_v01.blend',
        'grip_clip': 'ArtSource/Characters/MECHANIC_W86/Animations_v01/MECHANIC_W86_Grip_R_v01.fbx',
        'sheet': 'ArtSource/Characters/MECHANIC_W86/MECHANIC_W86_v01_sheet.png (+ Previews_v01/, palette PNG)',
        'scripts': ['mechanic_w86_type.py (the type: body, outfit, wrench)', 'build_mechanic_w86.py (runs SAUSAGE_BUDDY_01/build_buddy.py)',
                    'lods_mechanic_w86.py (runs Types_opt_v02 optimise + verify)', 'mech_rig.py (grip, hand poses, helpers)',
                    'mechanic_w86_anim.py (the clips)', 'render_mechanic_w86.py (previews, sheet)', 'notes_mechanic_w86.py (this file)'],
    },
    'rig': {
        'armature': MR.RIG, 'bones': len(bones), 'root': P + 'Hips', 'naming': 'Mixamo 65 (mixamorig:*)',
        'same_as_crowd_types': {'compared_with': REF_TYPE.name, 'same_bone_names': same_names,
                                'max_rest_matrix_difference': round(dev, 9),
                                'meaning': 'identical rest pose: every shared Sausage Buddy clip (Walk_v04, Idle_Stand_v04, crowd, '
                                           'escape, get-up...) plays on him unchanged; Unity: Generic, copy the avatar from the '
                                           'Sausage Buddy BASE like the crowd types (avatarSetup copy), no root motion'},
        'scale': 'metres, 1.748 m tall (crowd types 1.75 m), FBX axis_forward -Z, axis_up Y, apply_unit_scale, no leaf bones',
        'bone_list': bones},
    'body': {'base': 'Sausage Buddy body (buddy_body), pot belly = buddy_wear.reshape belly 1.25 applied to the body and every garment '
                     '(real geometry, layers keep their gaps; TRANSIT_TRUCKER 1.0, POLICE_FAT 1.6)', 'idle_arm_down_deg_builtin_clips': 62.0,
             'height_m': val['height_m']},
    'meshes_lod0_source': {k: {'triangles': v['triangles'], 'materials': v['materials'], 'shape_keys': v['shape_keys']}
                           for k, v in val['meshes'].items()},
    'lods_opt_v02': {'LOD0': lods['total_lod0'], 'LOD1': lods['total_lod1'], 'LOD2': lods['total_lod2'],
                     'per_mesh': {'LOD0': lods['tris_lod0'], 'LOD1': lods['tris_lod1'], 'LOD2': lods['tris_lod2']},
                     'method': 'SAUSAGE_BUDDY_01/Types_opt_v02 pipeline unchanged ("source" branch): LOD0 = source minus the hidden '
                               'Face interior; LOD1/LOD2 limit-checked collapse (LOD1 p99 8 mm/max 16 mm, LOD2 p99 20 mm/max 43 mm). '
                               'verify_opt_v02 checks passed on .blend and FBX.',
                     'unity_lod_screen_heights_suggested': {'LOD0': 0.10, 'LOD1': 0.037, 'LOD2_cull': 0.01}},
    'materials': {'convention': 'flat colour Principled materials per slot named MECHANIC_W86_<Slot> + the shared Buddy_* skin/eye '
                                'materials; no UVs, no textures (as every Sausage Buddy type); colourways tint the slot materials',
                  'slots': val['npc_type']['slots'], 'colourways': val['npc_type']['colourways'],
                  'look': {k: '#%02X%02X%02X' % v for k, v in MT.TYPE['look'].items()}},
    'wrench': {
        'mesh': 'Wrench_RightHand (opt FBX: Wrench_RightHand_LOD0/_LOD1/_LOD2)', 'triangles': {'LOD0': lods['tris_lod0']['Wrench_RightHand'],
                                                                                            'LOD1': lods['tris_lod1']['Wrench_RightHand'],
                                                                                            'LOD2': lods['tris_lod2']['Wrench_RightHand']},
        'skinning': 'every vertex weight 1.0 on mixamorig:RightHand (rigid), a SkinnedMeshRenderer on the same rig, so it stays '
                    'in the hand in every clip, ragdoll and crossfade without any script',
        'material': 'MECHANIC_W86_Wrench (metallic grey)',
        'shape': 'double open-ended spanner, ~0.27 m (cartoon 1.25x), chunky oval shank in the fist, big jaw on the thumb side',
        'grip_centre_in_RightHand_bone_space_m': [round(x, 4) for x in local_c],
        'shank_axis_in_RightHand_bone_space': [round(x, 4) for x in local_a],
        'name_note': 'deliberately NOT Props_RightHand: NpcTypesImportV01 adds NpcHeldProps for Props_*Hand meshes and NpcHeldProps '
                     'drops them at the first danger; the mechanic never lets go of his wrench. Do not add NpcHeldProps to him.'},
    'grip': {
        'what': 'Grip_R: local rotations of the right-hand finger bones only (Index/Middle/Ring/Pinky 1-3 curled 20/34/24 deg '
                'toward the palm, Thumb 1-3 closing over the shank 35/15/15 deg). Checked on the mesh: 36 of 320 finger vertices '
                'within 4 mm of the shank, deepest overlap 3.3 mm (a tight grip, no visible gap or slipping).',
        'why_a_layer': 'every shared clip keys all 65 bones including the fingers (Walk_v04 up to 20 deg, Idle_Stand_v04 15 deg, '
                       'Cop_ShakeFist_v02 84 deg), so a grip baked into the mesh would break; the override layer replaces only the '
                       'right-hand finger rotations and keeps everything else of the base clip',
        'clip': 'Animations_v01/MECHANIC_W86_Grip_R_v01.fbx, take Grip_R, 2 frames (constant), loop',
        'unity_setup': [
            'AvatarMask "Mechanic_HandR_Grip.mask" (Generic: Transform mask): import the skeleton from the mechanic FBX, untick '
            'everything, tick only the transforms listed in keyed_bones (mixamorig:RightHand children).',
            'Animator layer "HandGrip_R" as the LAST layer: blending Override, weight 1, mask Mechanic_HandR_Grip, one state playing '
            'Grip_R (loop) with no transitions.',
            'Leave NpcHeldProps off the mechanic. The Grip_R layer also covers the mechanic clips (they already hold the grip).',
            'Alternative without a layer: a LateUpdate script that sets these transforms to the Grip_R clip pose after the '
            'Animator (read the values from the clip, not from Blender quaternions: the FBX import converts axes).'],
        'keyed_bones': keyed,
        'blender_local_quaternions_wxyz': {b: [round(x, 6) for x in grip_loc.get(b, (1, 0, 0, 0))] for b in keyed}},
    'face': {'shape_keys': ['Blink', 'Blink_L', 'Blink_R', 'Surprised', 'Worried', 'Happy'],
             'expressions': {'neutral': {}, 'annoyed': {'Blink': 0.55, 'Worried': 0.15}, 'grinning': {'Happy': 1.0},
                             'mock_serious_aim': {'Blink_L': 1.0, 'Worried': 0.45}},
             'note': 'no dedicated angry/annoyed shape on the Sausage Buddy face: annoyed is an approximation (heavy lids)'},
    'clips': {'manifest': 'Animations_v01/clips_mechanic_v01.json', 'count': len(clips['clips']),
              'list': [{'state': c['state'], 'role': c['role'], 'seconds': c['seconds'], 'loop': c['loop'], 'events': list(c['events'])}
                       for c in clips['clips']],
              'shared_clips_he_uses': {'Walk': 'Walk_v04 (+Grip_R layer)', 'Idle': 'Idle_Stand_v04 (+Grip_R layer)',
                                       'others': 'any Sausage Buddy clip (same rig)'},
              'suggested_wiring': [
                  'Idle/work loop: Idle_Stand_v04; occasional gags Mech_Gag_WrenchGun / Mech_Gag_CockNod every 20-45 active seconds '
                  '(random, no repeat of the same gag twice in a row), suppressed during dialogue, hand-in, a service session or '
                  'any higher-priority action.',
                  'Work stops on the route: Mech_Work_InspectPart (bench), Mech_Work_WipeBench (shelf/cabinet), Mech_Work_CheckBay '
                  '(bay side, outside the lift footprint); each starts and ends on Idle_Stand_v04 frame 1 (cross-fade 0.2-0.25 s).',
                  'Player attention: the controller turns him; Mech_Attend_Enter -> Mech_Attend_Loop (loop) -> Mech_Attend_Exit.',
                  'Upgrade: turn to the van, then Mech_Upgrade_Perform; its Poof event (frame 52, 1.70 s) is the presentation cue '
                  'for the puff and the visible change; the server commits the purchase and syncs the cue (an animation event '
                  'never grants anything on its own).']},
    'deviations_from_reference': [
        'Sausage Buddy style instead of the painted reference: mitten hands (3 fingers + thumb), capsule head, the shared big '
        'eyes and brows (brows only recoloured dark grey, not thicker), flat colour materials (no fabric/stubble texture).',
        'Oil stains, stubble, pockets, rolled cuffs are modelled decals; the jacket yoke is a thin seam line.',
        'Annoyed face is Blink + Worried (no angry shape on the rig); the pupils cannot look sideways as in the reference.',
        'The pot belly is a little smaller than the painting (belly 1.25) so the shared clips keep the arms clear of it.',
        'The wrench sits front-back through the fist (the mitten fingers wrap round it): with the arm hanging it points forward, '
        'not down along the leg; raised in front of the chest it stands upright as in the reference three-quarter view.',
        'The rag is a static hanging cloth on the back pocket (weights from the trousers), it has no cloth simulation.'],
}
OUT.write_text(json.dumps(notes, indent=1, ensure_ascii=False), encoding='utf-8')
print('[NOTES]', OUT, 'rig deviation vs', REF_TYPE.name, dev, 'same names', same_names)
