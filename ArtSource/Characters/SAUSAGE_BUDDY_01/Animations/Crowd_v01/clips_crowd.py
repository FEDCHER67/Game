"""Clip registry of the Crowd_v01 package: clips, contract poses and the Unity placement contract."""
import clips_stand as CS
import clips_props as CP
import clips_floor as CF
import clips_run as CR

CLIPS = {}
CONTRACTS = {}
for _m in (CS, CP, CF, CR):
    CLIPS.update(_m.CLIPS)
    CONTRACTS.update(getattr(_m, 'CONTRACTS', {}))

# Where the world props sit relative to the NPC root (feet origin on the floor, character faces -Y = Unity +Z
# after the FBX axis conversion, left = +X). Review renders use exactly these numbers.
PLACEMENT = {
    'BenchSit': 'seat top %.2f m; seat front edge %.2f m behind the root, depth %.2f m; backrest from %.2f m behind; '
                'the root stays on the floor in front of the bench (feet keep their Idle spots)'
                % (CF.BENCH['seat_top'], CF.BENCH['front_y'], CF.BENCH['back_y'] - CF.BENCH['front_y'], CF.BENCH['backrest_y']),
    'BeachLie': 'towel (or sand) at floor level; the body lies behind the root: hips ~0.42 m, head top ~1.3 m behind; '
                'needs a free 0.9 x 2.2 m area from 0.45 m in front of the root',
    'BarDoor': 'wall plane %.2f m behind the root (the hood touches it, the right sole rests on it)' % CP.WALL_Y,
    'KioskBuy': 'kiosk counter in front: front edge 0.42 m ahead of the root, top 1.0 m (hands reach over it)',
    'Chat': 'two NPCs face each other 1.15 m apart; one plays Chat_Loop, the other Chat_Loop_Mirror at normalized time +0.5',
    'SmokeCorner / PhoneTalk / ShopQueue / BusWait': 'free standing, in place; no props (cigarette/phone implied by the hand)',
    'Flee_Panic_Run': 'in place; ground speed %.1f m/s' % CR.RUN_V,
}
