"""G13d: deterministic, review-only albedo grade over the latest live manifest.

python process_v3_v07.py process --output-root ArtSource/Textures/StyleKit_v3/candidate_v07
python process_v3_v07.py verify --output-root ArtSource/Textures/StyleKit_v3/candidate_v07

All writes are exclusive and outside Assets. Normal/mask PNG bytes are copied.
The candidate manifest contains FUTURE Assets paths; it is never published here.
"""
from __future__ import annotations

import argparse
import colorsys
import copy
import hashlib
import io
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[4]
KIT = ROOT / 'ArtSource/Textures/StyleKit_v3'
LIVE = ROOT / 'Assets/OnlyVolunteers/Art/StyleKit_v3'
REVISION = 7
TAG = f'v{REVISION:02}'
WATER_PREFIX = '8a_water'
WOODS = {'5a_wood_planks_fences', '5b_logs', '5b_logs_endcap', '7b_tree_bark'}
HEX_TARGETS = {
    '2a_asphalt': '#5F666C', '3a_brick': '#8C4F42',
    '4a_clay_roof_tiles': '#A2634B', '4b_slate_shingles': '#56677F',
    '4c_corrugated_metal': '#56677F', '4d_flat_bitumen_roof': '#3E4247',
    '6a_painted_metal_panels': '#8E9396', '6b_lightly_weathered_metal': '#8E9396',
}
WARM_SURFACES = {'2b_sidewalk_tiles', '2c_cobblestone', '3b_plaster_stucco',
                 '3c_concrete_panels', '3d_cinder_blocks'}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def relative(path):
    return Path(path).relative_to(ROOT).as_posix()


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def exclusive(path, data):
    path = Path(path).resolve()
    if not path.is_relative_to(KIT):
        raise ValueError(f'Write outside the approved ArtSource kit: {path}')
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as handle:
        handle.write(data)


def write_json(path, value):
    exclusive(path, (json.dumps(value, indent=2, ensure_ascii=False) + '\n').encode('utf-8'))


def png_bytes(image):
    if isinstance(image, np.ndarray):
        image = Image.fromarray(np.rint(np.clip(image, 0, 1) * 255).astype(np.uint8))
    data = io.BytesIO()
    image.save(data, format='PNG', compress_level=9)
    return data.getvalue()


def rgb(path):
    with Image.open(path) as image:
        return np.asarray(image.convert('RGB'), dtype=np.float64) / 255


def rgb_to_hsv(a):
    value = a.max(axis=-1)
    delta = value - a.min(axis=-1)
    safe = np.where(delta > 0, delta, 1)
    hue = np.zeros_like(value)
    red, green, blue = (a[..., channel] for channel in range(3))
    hue = np.where(value == blue, 4 + (red - green) / safe, hue)
    hue = np.where(value == green, 2 + (blue - red) / safe, hue)
    hue = np.where(value == red, (green - blue) / safe, hue)
    hue = np.where(delta > 0, (hue / 6) % 1, 0)
    saturation = np.divide(delta, value, out=np.zeros_like(value), where=value > 0)
    return np.stack((hue, saturation, value), axis=-1)


def hsv_to_rgb(a):
    h, s, v = (a[..., channel] for channel in range(3))
    channels = []
    for shift in (0, 2 / 3, 1 / 3):
        wave = np.abs(((h + shift) % 1) * 6 - 3) - 1
        channels.append(v * (1 - s + s * np.clip(wave, 0, 1)))
    return np.stack(channels, axis=-1)


def colour_stats(a):
    mean = a.mean(axis=(0, 1))
    h, s, v = colorsys.rgb_to_hsv(*mean)
    values = a.max(axis=-1)
    return {
        'mean_srgb': [round(float(c), 8) for c in mean],
        'mean_srgb_255': [round(float(c * 255), 4) for c in mean],
        'mean_hex': '#' + ''.join(f'{round(float(c * 255)):02X}' for c in mean),
        'hsv_of_mean_srgb': {'h': round(float(h), 8), 's': round(float(s), 8),
                             'v': round(float(v), 8), 'h_degrees': round(float(h * 360), 4)},
        'pixel_value_max': round(float(values.max()), 8),
        'pixel_value_std': round(float(values.std()), 8),
        'pixels_above_value_0_82': int(np.count_nonzero(values > .82)),
    }


def target_for(category, initial):
    mean_hsv = np.array(colorsys.rgb_to_hsv(*initial.mean(axis=(0, 1))))
    target = mean_hsv.copy()
    note = 'Initial S x 0.75 and V x 0.85 only; source hue retained.'
    if category in HEX_TARGETS:
        colour = HEX_TARGETS[category]
        target = np.array(colorsys.rgb_to_hsv(*(int(colour[i:i+2], 16) / 255 for i in (1, 3, 5))))
        note = f'Mean calibrated to brief target {colour}; one uniform HSV correction.'
    elif category == '1a_grass':
        target = np.array([.22, .40, .50])
        note = 'Olive green: mean H=79.2 degrees, S=0.40, V=0.50; current FreeStylized v03 grass.'
    elif category == '1c_beach_sand':
        target[2] = .76
        note = 'Sand mean V=0.76, inside 0.70-0.80; source hue and graded saturation retained.'
    elif category in WARM_SURFACES:
        target[0] = .11 if category in {'3c_concrete_panels', '3d_cinder_blocks'} else mean_hsv[0]
        target[1] = max(.045, mean_hsv[1])
        target[2] = .72 if category == '3b_plaster_stucco' else (
            .68 if category in {'3c_concrete_panels', '3d_cinder_blocks'} else mean_hsv[2])
        note = 'Warm grey/beige mean, V inside 0.62-0.76; no bluish white.'
    elif category in WOODS:
        target[0] = (mean_hsv[0] - .01) % 1
        note = 'One 15% value reduction total; 25% less saturation, 3.6 degree hue shift away from orange.'
    return target, note


def render(category, source):
    hsv = rgb_to_hsv(source)
    hsv[..., 1] *= .75
    hsv[..., 2] *= .85
    initial = hsv_to_rgb(hsv)
    target, note = target_for(category, initial)
    corrections = []
    # Correct HSV of the arithmetic sRGB mean, rather than averaging pixel HSV.
    # Uniform offsets/scales retain relative hues, saturation and value relief.
    for _ in range(6):
        mean_hsv = np.array(colorsys.rgb_to_hsv(*hsv_to_rgb(hsv).mean(axis=(0, 1))))
        delta_h = (target[0] - mean_hsv[0] + .5) % 1 - .5
        scale_s = target[1] / mean_hsv[1] if mean_hsv[1] > 1e-12 else 1
        scale_v = target[2] / mean_hsv[2]
        corrections.append([float(delta_h), float(scale_s), float(scale_v)])
        hsv[..., 0] = (hsv[..., 0] + delta_h) % 1
        hsv[..., 1] *= scale_s
        hsv[..., 2] *= scale_v
        if np.max(np.abs(mean_hsv - target)) < 1e-8:
            break
    if hsv[..., 1].max() > 1 or hsv[..., 2].max() > .82:
        raise ValueError(f'{category}: target would clip saturation or exceed V=0.82; no silent contrast loss')
    result = hsv_to_rgb(hsv)
    return result, {'initial_saturation_multiplier': .75, 'initial_value_multiplier': .85,
                    'target_mean_hsv': target.tolist(), 'uniform_hsv_corrections': corrections,
                    'note': note, 'initial_grade': colour_stats(initial)}


def latest_manifest():
    manifests = []
    for path in LIVE.glob('materials_v3*.json'):
        data = read_json(path)
        if data.get('schema') == 'OnlyVolunteers.StyleKitV3/1':
            manifests.append((data['revision'], path.name != 'materials_v3.json', path, data))
    _, _, path, data = max(manifests, key=lambda item: item[:2])
    return path, data


def protected_files():
    files = [path for path in LIVE.rglob('*') if path.is_file()]
    files += list((ROOT / 'Assets/OnlyVolunteers/Art/Editor').glob('StyleKitV3MaterialBuilder.cs*'))
    files += [path for path in KIT.rglob('*') if path.is_file()]
    return {relative(path): digest(path.read_bytes()) for path in sorted(set(files))}


def assert_unchanged(snapshot):
    changed = [name for name, sha in snapshot.items() if digest((ROOT / name).read_bytes()) != sha]
    if changed:
        raise RuntimeError(f'Protected files changed externally during processing: {changed}')


def font(size):
    return ImageFont.truetype('C:/Windows/Fonts/arial.ttf', size)


def contact(entries, output, means):
    # Every live-manifest category appears. Water rows are read-only references;
    # the last two shader-only presets show their existing shallow/deep swatches.
    width, cell_w, cell_h, tile = 1800, 600, 348, 128
    rows = (len(entries) + 2) // 3
    sheet = Image.new('RGB', (width, 82 + rows * cell_h), '#D8D6D0')
    draw = ImageDraw.Draw(sheet)
    draw.text((18, 12), f'G13d candidate {TAG} | CURRENT versus CANDIDATE | 2 x 2 tiles', fill='#24272A', font=font(25))
    draw.text((18, 46), 'Mean hex = arithmetic sRGB mean. Water unchanged; shader-only rows show shallow/deep colours.', fill='#34383B', font=font(18))
    for index, entry in enumerate(entries):
        category = entry['category']
        x, y = (index % 3) * cell_w, 82 + (index // 3) * cell_h
        draw.text((x + 14, y + 5), category, fill='#24272A', font=font(19))
        is_water = category.startswith(WATER_PREFIX)
        for col in range(2):
            bx, by = x + 14 + col * 292, y + 48
            label = 'current' if col == 0 else ('unchanged' if is_water else TAG)
            draw.text((bx, y + 29), label, fill='#34383B', font=font(16))
            if 'albedo' in entry:
                path = ROOT / entry['albedo'] if col == 0 or is_water else output / category / f'{category}_{TAG}_albedo.png'
                with Image.open(path) as image:
                    small = image.convert('RGB').resize((tile, tile), Image.Resampling.LANCZOS)
                for iy in range(2):
                    for ix in range(2):
                        sheet.paste(small, (bx + ix * tile, by + iy * tile))
                if is_water:
                    label_hex = colour_stats(rgb(path))['mean_hex'] + ' (history only)'
                else:
                    label_hex = means[category]['before' if col == 0 else 'after']['mean_hex']
            else:
                draw.rectangle((bx, by, bx + tile - 1, by + 2 * tile - 1), fill=entry['shallow_hex'])
                draw.rectangle((bx + tile, by, bx + 2 * tile - 1, by + 2 * tile - 1), fill=entry['deep_hex'])
                label_hex = entry['shallow_hex'] + ' / ' + entry['deep_hex']
            draw.text((bx, by + 262), label_hex, fill='#24272A', font=font(18))
    return png_bytes(sheet)


def verify(output, expected=None):
    manifest = read_json(output / f'materials_v3_{TAG}.json')
    receipt = expected or read_json(output / f'grade_{TAG}.json')
    source = read_json(ROOT / receipt['source_manifest'])
    original = {e['category']: e for e in source['entries']}
    for name, sha in receipt['protected_file_sha256'].items():
        assert digest((ROOT / name).read_bytes()) == sha, f'Protected file changed: {name}'
    assert len(receipt['categories']) == 22
    for entry in manifest['entries']:
        category = entry['category']
        old = original[category]
        if category.startswith(WATER_PREFIX):
            assert entry == old, f'Water entry changed: {category}'
            assert manifest['categories'][category] == source['categories'][category]
            continue
        for kind in ('albedo', 'normal', 'mask'):
            local = output / category / f'{category}_{TAG}_{kind}.png'
            expected_path = f'Assets/OnlyVolunteers/Art/StyleKit_v3/Textures/{category}/{local.name}'
            assert entry[kind] == expected_path
            with Image.open(local) as image:
                assert image.size == (1024, 1024)
                assert image.mode == ('RGBA' if kind == 'mask' else 'RGB')
                a = np.asarray(image)
            assert np.array_equal(a[0], a[-1]) and np.array_equal(a[:, 0], a[:, -1]), f'Seam: {category}/{kind}'
            if kind != 'albedo':
                assert local.read_bytes() == (ROOT / old[kind]).read_bytes(), f'{kind} changed: {category}'
        source_rgb = rgb(ROOT / old['albedo'])
        result, _ = render(category, source_rgb)
        assert (output / category / f'{category}_{TAG}_albedo.png').read_bytes() == png_bytes(result)
        after = colour_stats(rgb(output / category / f'{category}_{TAG}_albedo.png'))
        assert after == receipt['categories'][category]['after']
        assert after['pixel_value_max'] <= .82
        before_v = source_rgb.max(axis=-1)
        after_v = rgb(output / category / f'{category}_{TAG}_albedo.png').max(axis=-1)
        correlation = float(np.corrcoef(before_v.ravel(), after_v.ravel())[0, 1])
        assert correlation > .98, f'Tonal variation lost: {category}'
        h, s, v = (after['hsv_of_mean_srgb'][key] for key in ('h', 's', 'v'))
        if category in WARM_SURFACES:
            assert .62 <= v <= .76 and .07 <= h <= .15 and .03 <= s <= .25
        if category == '1c_beach_sand':
            assert .70 <= v <= .80
        if category == '1a_grass':
            assert .45 <= v <= .55 and .35 <= s <= .45 and .20 <= h <= .24
        if category in HEX_TARGETS:
            target = np.array([int(HEX_TARGETS[category][i:i+2], 16) for i in (1, 3, 5)])
            assert np.max(np.abs(np.array(after['mean_srgb_255']) - target)) < .5
        if category in WOODS:
            expected_v = receipt['categories'][category]['before']['hsv_of_mean_srgb']['v'] * .85
            assert abs(v - expected_v) < .002
        assert entry['material_path'].endswith(f'M3_{category}_{TAG}.mat')
        assert entry['metres_per_tile'] == old['metres_per_tile']
    preview = KIT / f'previews/contact_{TAG}.png'
    assert preview.read_bytes() == contact(source['entries'], output, receipt['categories'])
    return {'albedos': 22, 'normal_mask_byte_copies': 44, 'exact_seam_maps': 66,
            'water_entries_unchanged': sum(e['category'].startswith(WATER_PREFIX) for e in source['entries']),
            'deterministic_rerenders': 22,
            'mean_targets_passed': True, 'all_albedo_pixels_value_at_most_0_82': True,
            'tonal_value_correlation_above_0_98': True,
            'protected_preexisting_files_unchanged': len(receipt['protected_file_sha256']),
            'unity_test': 'Not run; candidate is outside Assets pending visual acceptance.'}


def process(output):
    manifest_path, source = latest_manifest()
    if source['revision'] >= REVISION:
        raise ValueError('Revision occupied; create the next numbered script/candidate instead.')
    non_water = [entry for entry in source['entries'] if not entry['category'].startswith(WATER_PREFIX)]
    assert len(non_water) == 22
    grass = next(entry for entry in non_water if entry['category'] == '1a_grass')
    assert grass['material_path'].endswith('M3_1a_grass_v03.mat')
    fixes = {'1b_dirt_road', '2a_asphalt', '3b_plaster_stucco', '3c_concrete_panels', '4c_corrugated_metal'}
    assert all('_v04_albedo.png' in entry['albedo'] for entry in non_water if entry['category'] in fixes)
    preview = KIT / f'previews/contact_{TAG}.png'
    if output.exists() or preview.exists():
        raise FileExistsError('Candidate/preview already exists; never overwrite a deliverable.')
    baseline = protected_files()
    candidate = copy.deepcopy(source)
    candidate.update(revision=REVISION, parent_manifest=relative(manifest_path),
                     changed_categories=[e['category'] for e in non_water],
                     candidate_status='review_only_do_not_import_before_acceptance',
                     candidate_output_root=relative(output),
                     revision_note='G13d muted albedo candidate; v04 fixes retained, every G14 water entry untouched.')
    means = {}
    total_size = 0
    for entry in candidate['entries']:
        category = entry['category']
        if category.startswith(WATER_PREFIX):
            continue
        before = rgb(ROOT / entry['albedo'])
        graded, recipe = render(category, before)
        payload = png_bytes(graded)
        after = rgb_bytes_stats(payload)
        means[category] = {'source_albedo': entry['albedo'], 'before': colour_stats(before),
                           'after': after, 'recipe': recipe}
        for kind in ('albedo', 'normal', 'mask'):
            data = payload if kind == 'albedo' else (ROOT / entry[kind]).read_bytes()
            name = f'{category}_{TAG}_{kind}.png'
            exclusive(output / category / name, data)
            entry[kind] = f'Assets/OnlyVolunteers/Art/StyleKit_v3/Textures/{category}/{name}'
            total_size += len(data)
        entry['material_path'] = f'Assets/OnlyVolunteers/Art/StyleKit_v3/Materials/M3_{category}_{TAG}.mat'
        entry['palette_hex'] = after['mean_hex']
        entry['grade_note'] = recipe['note']
        entry['grade_initial_saturation_multiplier'] = .75
        entry['grade_initial_value_multiplier'] = .85
        candidate['categories'][category]['material_path'] = entry['material_path']
    write_json(output / f'materials_v3_{TAG}.json', candidate)
    exclusive(preview, contact(source['entries'], output, means))
    receipt = {'task': 'G13d', 'revision': REVISION, 'source_manifest': relative(manifest_path),
               'candidate_manifest': relative(output / f'materials_v3_{TAG}.json'),
               'preview': relative(preview), 'mean_definition': 'Arithmetic sRGB mean; HSV is HSV of that mean.',
               'categories': means, 'unmet_targets': [], 'texture_count': 66,
               'texture_total_bytes': total_size, 'protected_file_sha256': baseline}
    assert_unchanged(baseline)
    receipt['validation'] = verify(output, receipt)
    write_json(output / f'grade_{TAG}.json', receipt)
    print(json.dumps({'output_root': relative(output), 'validation': receipt['validation'],
                      'texture_bytes': total_size}, indent=2))


def rgb_bytes_stats(payload):
    with Image.open(io.BytesIO(payload)) as image:
        return colour_stats(np.asarray(image, dtype=np.float64) / 255)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('process', 'verify'))
    parser.add_argument('--output-root', required=True, type=Path,
                        help='New candidate directory inside ArtSource/Textures/StyleKit_v3; never Assets.')
    args = parser.parse_args()
    output_root = (ROOT / args.output_root).resolve()
    if not output_root.is_relative_to(KIT) or output_root == KIT:
        parser.error('--output-root must be a new directory inside the ArtSource kit')
    if args.command == 'process':
        process(output_root)
    else:
        print(json.dumps(verify(output_root), indent=2))
