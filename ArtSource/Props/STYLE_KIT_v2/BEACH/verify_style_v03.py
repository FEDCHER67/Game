"""Read-only v03 palette/value audit; writes only a new BEACH-local report."""
import hashlib
import json
import math
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from beach_support import sk
import bpy
import numpy as np

destination = HERE / 'style_audit_v03.json'
if destination.exists():
    raise RuntimeError('Refusing to replace style_audit_v03.json')
report = json.loads((HERE / 'validation_v03.json').read_text(encoding='utf-8'))
previous = json.loads((HERE / 'validation_v02.json').read_text(encoding='utf-8'))


def lab(swatch):
    r, g, b = sk.srgb_to_linear(sk.SWATCH[swatch])
    xyz = ((0.4124564*r + 0.3575761*g + 0.1804375*b) / 0.95047,
           0.2126729*r + 0.7151522*g + 0.0721750*b,
           (0.0193339*r + 0.1191920*g + 0.9503041*b) / 1.08883)
    f = [v**(1/3) if v > (6/29)**3 else v/(3*(6/29)**2) + 4/29 for v in xyz]
    return (116*f[1]-16, 500*(f[0]-f[1]), 200*(f[1]-f[2]))


def band(lightness):
    # Continuous boundaries avoid gaps from rounded band endpoints in the bible.
    return next(b for threshold, b in ((90, 'B1'), (78, 'B2'), (64, 'B3'),
                                      (48, 'B4'), (30, 'B5'), (0, 'B6')) if lightness >= threshold)


def delta(a, b):
    return math.dist(lab(a), lab(b))


assets = {}
for name, asset in report['assets'].items():
    colours = asset['swatches']
    pairs = [(a, b) for i, a in enumerate(colours) for b in colours[i+1:]]
    assets[name] = {
        'swatches': {s: {'hex': sk._hexstr(sk.SWATCH[s]), 'L_star': round(lab(s)[0], 3),
                         'band': band(lab(s)[0])} for s in colours},
        'pair_deltaE76': {f'{a} / {b}': round(delta(a, b), 3) for a, b in pairs},
        'checks': {
            'bible_palette_only': all(s in sk.SWATCH for s in colours),
            'no_B6_material_surfaces': all(lab(s)[0] >= 30 for s in colours),
            'R8_all_swatch_pairs_deltaE76_ge_9': all(delta(a, b) >= 9 for a, b in pairs),
            'geometry_unchanged_except_bollard': name == 'BE_Pier_Post' or
                asset['geometry_sha1'] == previous['assets'][name]['geometry_sha1'],
        },
    }

relationships = {
    'R2_kiosk_chalk_trim_over_teal_wall': lab('chalk')[0] - lab('teal')[0] >= 6,
    'R3_kiosk_grey_plinth_against_teal_wall': abs(lab('grey')[0] - lab('teal')[0]) >= 12,
    'R3_shower_grey_plinth_against_chalk_wall': abs(lab('grey')[0] - lab('chalk')[0]) >= 12,
    'R4_palm_crown_against_sand': lab('sand')[0] - lab('leaf.light')[0] >= 12,
    'bollard_cap_darker_than_body': lab('grey.dark')[0] < lab('grey')[0],
    'bollard_body_and_cap_distinct_from_wood_deck':
        delta('grey', 'wood.light') >= 9 and delta('grey.dark', 'wood.light') >= 9,
    'bollard_lower_than_lounger_back': report['assets']['BE_Pier_Post']['size_m'][2] <
        report['assets']['BE_Lounger']['size_m'][2],
}

previews = {}
for path in sorted((HERE / 'Previews' / 'v03').glob('*.png')):
    img = bpy.data.images.load(str(path), check_existing=False)
    img.colorspace_settings.name = 'Non-Color'
    pixels = np.empty(len(img.pixels), dtype=np.float32)
    img.pixels.foreach_get(pixels)
    rgb = pixels.reshape(-1, 4)[:, :3]
    linear = np.where(rgb <= 0.04045, rgb / 12.92, ((rgb + 0.055)/1.055)**2.4)
    y = linear @ np.array([0.2126729, 0.7151522, 0.0721750])
    lightness = 116*np.where(y > (6/29)**3, np.cbrt(y), y/(3*(6/29)**2)+4/29)-16
    b6_percent = float(np.mean(lightness < 30)*100)
    previews[path.name] = {'size_px': list(img.size), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                           'B6_pixels_percent': round(b6_percent, 4),
                           'B6_pixels_at_most_2_percent': b6_percent <= 2}
    bpy.data.images.remove(img)

expected_previews = {'01_BE_Pier_Post.png', '02_lineup.png', '03_beach_reference_top.png',
                     '04_beach_eye_level.png', '05_style_neighbours.png'}
checks = {
    'all_17_asset_value_and_palette_checks': len(assets) == 17 and
        all(all(a['checks'].values()) for a in assets.values()),
    'all_applicable_asset_contrast_relationships': all(relationships.values()),
    'five_fresh_v03_previews': set(previews) == expected_previews,
    'no_preview_has_over_2_percent_B6_pixels': all(p['B6_pixels_at_most_2_percent'] for p in previews.values()),
}
audit = {'revision': 'v03', 'method': 'CIELAB D65 from bible sRGB; actual PNG luminance histogram',
         'scope': 'All 17 BEACH assets; R2/R3/R4/R8 where applicable. R1 sloped building roofs absent. '
                  'PNG B6 counts include all shadows, a stricter check than ink-material share. '
                  'This does not certify URP sunlight calibration or game-camera acceptance.',
         'assets': assets, 'contrast_relationships': relationships, 'previews': previews,
         'checks': checks, 'all_checks_passed': all(checks.values())}
destination.write_text(json.dumps(audit, indent=2), encoding='utf-8')
print(json.dumps({'checks': checks, 'relationships': relationships,
                  'preview_B6_percent': {n: p['B6_pixels_percent'] for n, p in previews.items()}}, indent=2))
if not audit['all_checks_passed']:
    raise RuntimeError('BEACH v03 style audit failed; inspect the numbered report')
