"""Step 2b (v02, local 2026-10-18): corrections of the water bodies vectorised by s02 from the v76 render.

s02 takes every blue blob of the render as water. Checked one by one over the 2D map (sheet in the build report):
  lake_01  = the legend swatch "River, canal, lake, sea" (bottom-right legend box)          -> dropped
  lake_03  = sea between the Elite piers (a yacht cuts it off)                               -> dropped (it is sea)
  river_05 = the letters of the label "INTERNATIONAL CONSTRUCTION" (carved a trench in v01) -> dropped
  lake_08  = the lavender roof of the Hamlet church 02-A-CHURCH (carved a 1.4 m pit in v01)  -> dropped
  lake_00  = the river in the Quiet Valley gorge (one river, handoff v02 §3)                  -> river
  lake_04  = the river from the land bridge at y 349 to the Construction road bridge         -> river
Dropped bodies stay in the file with kind "dropped" (outline + reason) so s03 also ignores their pixels of the
water class; the builder skips them. Names for the disposal kinds: forest_lake / mountain_lake = Lake,
hamlet_pond = Pond (no disposal), swamp = Bog, river = River (handoff v02 §7.3; no canal since v38).
Run: MAPV76_REV=v02 python s02b_water_fix.py   (idempotent)
"""
from common import load_json, save_json

DROP = {
    'lake_01': 'legend swatch in the legend box, not water',
    'lake_03': 'sea between the Elite piers (yacht drawn over it), not a lake',
    'river_05': 'label text INTERNATIONAL CONSTRUCTION, not water',
    'lake_08': 'roof of the Hamlet church 02-A-CHURCH, not water',
}
TO_RIVER = {
    'lake_00': 'river in the Quiet Valley gorge (one river)',
    'lake_04': 'river from the land bridge (y 349) to the Construction road bridge',
}


def main():
    w = load_json('water_v76.json')
    for b in w['bodies']:
        if b['id'] in DROP:
            b.update(kind='dropped', reason=DROP[b['id']])
            b.pop('name', None)
        elif b['id'] in TO_RIVER:
            b.update(kind='river', name=None, depth_m=1.6, flow=True, gorge_depth_m=[6, 13], reason=TO_RIVER[b['id']],
                     note='one river: mountain lake -> waterfall -> gorge -> Hamlet (2 land bridges) -> Quiet Valley -> waterfall into the sea')
        if b.get('name') == 'forest_lake' and b['kind'] == 'lake':
            b['note'] = 'one lake, rounder, at the northern edge of the forest'
    w['fixes_v02'] = {'dropped': DROP, 'to_river': TO_RIVER, 'script': 'Tools/MapV76/s02b_water_fix.py'}
    save_json('water_v76.json', w)
    print({b['id']: b['kind'] for b in w['bodies']})


if __name__ == '__main__':
    main()
