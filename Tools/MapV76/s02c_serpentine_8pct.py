"""Step 2c (v02, local 2026-10-18): serpentine to VIEW B on hill B held to the 8 % rule (open question Q7 for Vadim).

v76 (build_world_v76.py ROAD_S) runs straight over the hill: ~156 m each side of VIEW B for ~40 m of climb, so the road
needs 12 % and still cuts ~15 m into the hill (VIEW B ends at ~+35 m instead of +46 m). Proposed default (lead, Q7):
keep the same ends and VIEW B, add hairpin loops so the climb stays <= 8 %: four legs on the north slope (Rough side),
four on the south slope (Downtown side), legs along the slope, hairpins rounded (Chaikin). The v76 line is kept in the
road record as `points_v76_original`; `--original` puts it back. s03 grades serpentines with 8 % for data v02.
Run: MAPV76_REV=v02 python s02c_serpentine_8pct.py [--original]   then s03, s05, s07.
DECISION (Fedya 18.10, Q7): keep the v76 serpentine with 12 % -> data v02 is generated with --original; this variant is
kept only as a ready option (s03 grades a road with a `variant` at 8 %, the original serpentine at 12 %).
"""
import math
import sys

from common import chaikin, load_json, save_json

VIEW_B = (1010.0, 601.05)
NORTH = [(945.0, 672.0), (945.0, 663.0), (1000.0, 660.0), (1048.0, 657.0), (1056.0, 651.0), (1046.0, 645.0), (960.0, 646.0),
         (912.0, 643.0), (903.0, 636.0), (913.0, 630.0), (990.0, 632.0), (1044.0, 629.0), (1052.0, 622.0), (1042.0, 616.0),
         (985.0, 616.0), (962.0, 611.0), (968.0, 604.0), VIEW_B]   # 4 legs within x 903..1056 (clear of the Rough -> Port road)
SOUTH = [VIEW_B, (1040.0, 590.0), (1085.0, 580.0), (1122.0, 574.0), (1130.0, 566.0), (1120.0, 559.0), (1060.0, 558.0),
         (1000.0, 556.0), (984.0, 548.0), (992.0, 539.0), (1050.0, 533.0), (1118.0, 528.0), (1128.0, 520.0), (1118.0, 512.0),
         (1080.0, 506.0), (1072.0, 494.0), (1082.0, 470.0), (1089.66, 449.48)]


def length(pl):
    return sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(pl[:-1], pl[1:]))


def main():
    r = load_json('roads_v76.json')
    s = next(x for x in r['roads'] if x['id'] == 'serpentine_view_b')
    s.setdefault('points_v76_original', s['points'])
    if '--original' in sys.argv:
        s['points'] = s['points_v76_original']
        s.pop('variant', None)
    else:
        pts = chaikin(NORTH, 2)[:-1] + chaikin(SOUTH, 2)
        s['points'] = [[round(p[0], 2), round(p[1], 2)] for p in pts]
        s['variant'] = 'v02 <= 8 %: hairpin loops (Q7 default, Tools/MapV76/s02c_serpentine_8pct.py)'
    s.pop('heights', None)
    save_json('roads_v76.json', r)
    print('serpentine', s.get('variant', 'v76 original'), 'length %.0f m (v76 %.0f m)' % (length(s['points']), length(s['points_v76_original'])))


if __name__ == '__main__':
    main()
