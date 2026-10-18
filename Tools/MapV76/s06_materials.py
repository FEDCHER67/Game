"""Step 6: material map for map v76 — approved texture per key (handoff v02 §7.1, TEXTURE_DECISIONS.md) and the EXISTING
Unity material / terrain layer that already uses that texture (addendum 01: no duplicate materials for the same texture).

For each key: texture file -> GUID (.meta) -> every .mat / .terrainlayer under Assets referencing that GUID as its main/base map.
Preference: materials used in Map_Look_v19_Play_i10_capture_delivery.unity, then Map/Look/Materials, Map/LookV3, Art/StyleKit_v3.
Textures that live outside Assets (Working/Reviews/...) have no material yet -> 'create' (W76Builder imports the PNG into
Map/W76Build/Textures_v01 and makes ONE material per such texture).
Output: Data/v01/materials_v76.json (+ a table for the handoff).
"""
import glob
import os
import re

from common import ROOT, save_json

A = 'Assets/OnlyVolunteers/'
D = A + 'Art/Map/Textures/Detail/'
SK = A + 'Art/StyleKit_v3/Textures/'
TX = 'Working/Reviews/Textures_2026-10-17/'
GPT = TX + 'gpt_missing_v02_2026-10-18/Textures/'
TL = 'terrain_layer'
# key: (use, texture path (repo), tile m)
TEXTURES = {
    'L01_meadow': (TL, D + 'TL_meadow_albedo.png', 8),
    'L02_worn_grass': (TL, D + 'TL_worn_grass_albedo.png', 8),
    'L03_dirt_SK1b': (TL, SK + '1b_dirt_road/1b_dirt_road_v07_albedo.png', 6),
    'L04_forest_floor_p10': (TL, TX + 'TL_forest_floor_albedo_v02_brighter.png', 8),
    'L05_sand_white': (TL, D + 'TL_sand_albedo.png', 8),
    'L05b_sand_wet': (TL, TX + 'own_textures_v01/TL_sand_wet_albedo_v01.png', 8),
    'L06_gravel_SK1d': (TL, SK + '1d_gravel/1d_gravel_v07_albedo.png', 6),
    'L07_rock_macro': (TL, GPT + 'Rock_Macro.png', 12),
    'L08_lawn_park': (TL, D + 'TL_park_grass_albedo.png', 8),
    'L09_field_plowed': (TL, GPT + 'Field_plowed.png', 4),
    'L10_field_stubble': (TL, GPT + 'Field_stubble.png', 4),
    'asphalt_A5d12': ('road', TX + 'candidates_asphalt_v01/2a_asphalt_v07_A5d12_albedo.png', 6),
    'asphalt_old_SK2a': ('road', SK + '2a_asphalt/2a_asphalt_v01_albedo.png', 6),
    'sidewalk_S1': ('road', TX + 'candidates_paving_v01/S1_sidewalk_oar_1p5m_albedo.png', 3),
    'plaza_M3': ('road', TX + 'candidates_paving_v01/M3_plaza_1m_granite_bands_albedo.png', 8),
    'cobble_SK2c': ('road', SK + '2c_cobblestone/2c_cobblestone_v07_albedo.png', 4),
    'concrete_SK3c': ('road', SK + '3c_concrete_panels/3c_concrete_panels_v07_albedo.png', 4),
    'stucco_SK3b': ('wall', SK + '3b_plaster_stucco/3b_plaster_stucco_v01_albedo.png', 4),
    'stucco_SK3b_v07': ('wall', SK + '3b_plaster_stucco/3b_plaster_stucco_v07_albedo.png', 4),
    'brick_SK3a': ('wall', SK + '3a_brick/3a_brick_v07_albedo.png', 3),
    'concrete_panel_SK3c': ('wall', SK + '3c_concrete_panels/3c_concrete_panels_v07_albedo.png', 4),
    'cinder_SK3d': ('wall', SK + '3d_cinder_blocks/3d_cinder_blocks_v07_albedo.png', 3),
    'boards_SK5a': ('wall', SK + '5a_wood_planks_fences/5a_wood_planks_fences_v07_albedo.png', 3),
    'boards_pier_SK5a_v02': ('wall', SK + '5a_wood_planks_fences/5a_wood_planks_fences_v02_albedo.png', 3),
    'logs_SK5b': ('wall', SK + '5b_logs/5b_logs_v07_albedo.png', 3),
    'KH1b': ('wall', TX + 'candidates_rough_soviet_v02/KH1b_panel_grey_shabby_albedo.png', 12.8),
    'KH_windows_atlas': ('decal', TX + 'own_textures_v01/KH_windows_atlas_v01.png', 0),
    'facade_downtown_stucco': ('wall', GPT + 'Facade_DT_plaster.png', 3.5),
    'facade_downtown_brick': ('wall', GPT + 'Facade_DT_brick.png', 3.5),
    'facade_storefront': ('wall', GPT + 'Facade_DT_shop.png', 4),
    'facade_hamlet': ('wall', GPT + 'Facade_Hamlet_wood.png', 3.5),
    'facade_elite_villa': ('wall', GPT + 'Facade_Elite_villa.png', 3.5),
    'facade_warehouse': ('wall', GPT + 'Facade_Warehouse.png', 3.5),
    'tower_glass': ('wall', GPT + 'TowerGlass.png', 4),
    'facade_trim': ('wall', GPT + 'FacadeTrim.png', 2),
    'roof_tile_SK4a': ('roof', SK + '4a_clay_roof_tiles/4a_clay_roof_tiles_v07_albedo.png', 3),
    'roof_slate_SK4b': ('roof', SK + '4b_slate_shingles/4b_slate_shingles_v07_albedo.png', 3),
    'roof_wavy_slate': ('roof', None, 3),                                  # roof_slate_wavy — resolved by name below
    'roof_flat_SK4d': ('roof', SK + '4d_flat_bitumen_roof/4d_flat_bitumen_roof_v03_albedo.png', 4),
    'roof_profsheet_SK4c': ('roof', SK + '4c_corrugated_metal/4c_corrugated_metal_v07_albedo.png', 3),
    'metal_rusty': ('roof', D + 'facade_corrugated_metal_albedo_detail.png', 3),
    'metal_painted_SK6a': ('wall', SK + '6a_painted_metal_panels/6a_painted_metal_panels_v07_albedo.png', 3),
    'pool_tile': ('wall', GPT + 'PoolTile.png', 1),
    'fence_net': ('wall', GPT + 'FenceNet.png', 1),
    'fabric_blue': ('wall', GPT + 'Fabric_blue.png', 1.2),
    'fabric_red': ('wall', GPT + 'Fabric_red.png', 1.2),
    'fabric_green': ('wall', GPT + 'Fabric_green.png', 1.2),
    'road_marks': ('decal', GPT + 'RoadMarks.png', 0),
    'road_wear': ('decal', GPT + 'RoadWear.png', 0),
    'street_utility': ('decal', GPT + 'StreetUtility.png', 0),
    'oil_tar': ('decal', GPT + 'OilTar.png', 0),
    'shore_foam': ('decal', GPT + 'WaterFX_shore_foam.png', 0),
    'waterfall': ('decal', TX + 'own_textures_v01/WaterFX_waterfall_v02_tileY.png', 0),
}
EXISTING = {   # approved non-texture assets used as-is
    'water_sea': A + 'Art/StyleKit_v3/WaterTests/WaterTest_v02_001/Sea_trial_calm_v09.mat',
    'water_sea_alt_v10': A + 'Art/StyleKit_v3/WaterTests/WaterTest_v02_001/Sea_trial_calm_v10.mat',
    'water_shader': 'OnlyVolunteers/Uber Stylized Water v05',
}
SCENE_I10 = A + 'Scenes/Map/Map_Look_v19_Play_i10_capture_delivery.unity'
PREF = [A + 'Map/Look/Materials/', A + 'Map/LookV3/', A + 'Art/StyleKit_v3/', A + 'Art/Map/']


def guid_of(path):
    meta = os.path.join(ROOT, path + '.meta')
    if not os.path.exists(meta):
        return None
    m = re.search(r'guid: ([0-9a-f]{32})', open(meta, encoding='utf-8', errors='ignore').read())
    return m.group(1) if m else None


def main():
    mats = glob.glob(os.path.join(ROOT, 'Assets', '**', '*.mat'), recursive=True) + \
        glob.glob(os.path.join(ROOT, 'Assets', '**', '*.terrainlayer'), recursive=True)
    text = {}
    for p in mats:
        try:
            t = open(p, encoding='utf-8', errors='ignore').read()
        except OSError:
            continue
        if t.startswith('version https://git-lfs'):
            continue
        text[os.path.relpath(p, ROOT).replace(os.sep, '/')] = t
    scene = open(os.path.join(ROOT, SCENE_I10), encoding='utf-8', errors='ignore').read() if os.path.exists(os.path.join(ROOT, SCENE_I10)) else ''
    scene_guids = set(re.findall(r'guid: ([0-9a-f]{32})', scene))
    index = {}                                                          # guid -> asset path (one level deeper: TerrainData -> layers)
    for meta in glob.glob(os.path.join(ROOT, 'Assets', 'OnlyVolunteers', '**', '*.asset.meta'), recursive=True):
        g_ = re.search(r'guid: ([0-9a-f]{32})', open(meta, encoding='utf-8', errors='ignore').read())
        if g_:
            index[g_.group(1)] = meta[:-5]
    for g_ in list(scene_guids):
        p_ = index.get(g_)
        if p_ and os.path.getsize(p_) < 50_000_000:
            head = open(p_, 'rb').read(4096)
            if not head.startswith(b'version https://git-lfs'):
                scene_guids |= set(re.findall(r'guid: ([0-9a-f]{32})', open(p_, encoding='utf-8', errors='ignore').read()))
    out, reused, created = {}, [], []
    for key, (use, tex, tile) in TEXTURES.items():
        if tex is None:
            cands = [p for p in glob.glob(os.path.join(ROOT, 'Assets', '**', '*roof_slate_wavy*'), recursive=True) if not p.endswith('.meta')]
            tex = os.path.relpath(cands[0], ROOT).replace(os.sep, '/') if cands else None
        rec = {'use': use, 'texture': tex, 'tile_m': tile, 'texture_exists': bool(tex and os.path.exists(os.path.join(ROOT, tex)))}
        g = guid_of(tex) if tex and tex.startswith('Assets/') else None
        rec['texture_guid'] = g
        hits = []
        if g:
            for p, t in text.items():
                if g in t:
                    main = re.search(r'_(?:BaseMap|MainTex|BaseColorMap|Albedo\w*|DiffuseTexture)\s*:\s*\n\s*m_Texture: \{fileID: \d+, guid: ' + g, t) or \
                        re.search(r'm_DiffuseTexture: \{fileID: \d+, guid: ' + g, t)
                    hits.append((p, bool(main), guid_of(p) in scene_guids))
        hits.sort(key=lambda h: (not h[2], not h[1], next((i for i, pf in enumerate(PREF) if h[0].startswith(pf)), 9), h[0]))
        wanted = '.terrainlayer' if use == TL else '.mat'
        best = next((h for h in hits if h[0].endswith(wanted) and h[1]), None) or next((h for h in hits if h[0].endswith(wanted)), None)
        if best:
            rec.update(action='reuse', asset=best[0], asset_guid=guid_of(best[0]), in_i10_scene=best[2],
                       also_referenced_by=[h[0] for h in hits if h[0] != best[0]][:6])
            reused.append(key)
        elif use == 'decal':
            rec.update(action='texture_only', asset=None, note='atlas/mask: assigned on decal/props material by the builder')
        else:
            rec.update(action='create', asset='Assets/OnlyVolunteers/Map/W76Build/Materials_v01/W76_%s%s' % (key, wanted),
                       note='no existing %s uses this approved texture' % wanted[1:])
            created.append(key)
        out[key] = rec
    for k, p in EXISTING.items():
        out[k] = {'use': 'water' if 'water' in k else 'shader', 'action': 'reuse', 'asset': p, 'asset_guid': guid_of(p) if p.startswith('Assets') else None,
                  'texture_exists': os.path.exists(os.path.join(ROOT, p)) if p.startswith('Assets') else True}
    save_json('materials_v76.json', {'note': 'reuse = existing asset referenced by the builder as-is (never modified); create = new asset in W76Build/Materials_v01',
                                     'materials': out})
    print('reuse', len(reused), reused)
    print('create', len(created), created)
    print('missing textures', [k for k, v in out.items() if not v.get('texture_exists', True)])


if __name__ == '__main__':
    main()
