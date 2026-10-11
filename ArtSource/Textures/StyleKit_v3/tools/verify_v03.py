"""Read-only G13 v03 checks; writes only a new numbered verification receipt.

Re-renders every output from preserved originals in memory and compares PNG
SHA-256, tests palette centring, mask ranges, normal direction, opposite edges,
and the material manifest. No assets or source files are changed.
"""
import importlib.util
import json
from pathlib import Path
import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('g13_process_v03',HERE/'process_v3_v03.py')
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)
root = p.ROOT
manifest = p.read_json(p.ASSETS/'materials_v3_v03.json')
source = p.read_json(root/manifest['source_manifest'])
records = {r['category']:r for r in source['records']}
palette = p.palette()
receipt = {'revision':3,'python':__import__('sys').version,'pillow':__import__('PIL').__version__,
           'numpy':np.__version__,'byte_identical_rerender':True,'sets':[]}
seen_paths = set()
for e in manifest['entries']:
    category = e['category']
    record = records[e['source_category']]
    key,mx,my,contrast,radius,smin,smax,metal = p.RECIPES[category]
    maps = p.procedural(category) if record['status']=='procedural' else p.source_maps(record)
    if category=='3a_brick':
        maps = p.brick_stretch(maps)
    albedo = p.seal(p.hue_saturation_map(maps['albedo'],palette[key],contrast,radius,category=='2a_asphalt'))
    normal,evidence = p.normal_gl(maps['normal'],maps['height'],maps['normal_filename'],radius,category=='3a_brick')
    ao = .90+.10*p.blur_wrap(maps['ao'],radius)
    rough = p.blur_wrap(maps['roughness'],radius)
    smooth = smin+(1-rough)*(smax-smin)
    metallic = p.blur_wrap(maps.get('metallic',np.full((p.SIZE,p.SIZE),metal,dtype=np.float32)),radius)
    if category.startswith('6'):
        metallic = np.minimum(metallic,.18)
    mask = p.seal(np.stack((metallic,ao,np.zeros_like(ao),smooth),axis=-1))
    item = {'category':category,'files':{},'normal_format_evidence':evidence}
    for kind,a in (('albedo',albedo),('normal',normal),('mask',mask)):
        path = root/e[kind]
        assert path not in seen_paths, f'Duplicate output: {path}'
        seen_paths.add(path)
        expected = p.sha(p.png_bytes(a))
        actual = p.sha(path.read_bytes())
        assert actual==expected, f'Non-deterministic output: {path}'
        q = np.asarray(Image.open(path))
        assert (q[:,0]==q[:,-1]).all() and (q[0]==q[-1]).all()
        item['files'][kind] = {'sha256':actual,'deterministic':True,'seam_equal':True}
    # Y-centred hue/saturation mapping: the geometric luminance mean stays
    # near the authoritative swatch despite source colour/noise differences.
    target = np.array([int(palette[key][i:i+2],16)/255 for i in (1,3,5)])
    centre = np.exp(np.log(np.maximum(p.luminance(albedo),.001)).mean())
    ratio = float(centre/p.luminance(target))
    assert abs(ratio-1)<.025, (category,ratio)
    item['geometric_luminance_to_palette_ratio'] = ratio
    slopes = (normal*2-1)
    assert np.min(slopes[...,2])>.05
    dy = np.roll(maps['height'],-1,axis=0)-np.roll(maps['height'],1,axis=0)
    item['output_normal_y_height_covariance'] = float(np.sum(slopes[...,1]*dy))
    assert item['output_normal_y_height_covariance'] >= -1e-5, ('Incorrect OpenGL Y',category)
    qmask = np.asarray(Image.open(root/e['mask']))
    assert np.min(qmask[...,1]) >= 229 and np.max(qmask[...,2]) == 0
    assert np.min(qmask[...,3]) >= round(smin*255)-1
    assert np.max(qmask[...,3]) <= round(smax*255)+1
    assert e['metres_per_tile']=={'x':mx,'y':my}
    assert manifest['categories'][category]['material_path']==e['material_path']
    item['mask_channel_min'] = qmask.min(axis=(0,1)).tolist()
    item['mask_channel_max'] = qmask.max(axis=(0,1)).tolist()
    receipt['sets'].append(item)
    print(category,'DETERMINISTIC / PALETTE / SEAMS / NORMAL / MASK PASS',flush=True)
p.verify(p.ASSETS/'materials_v3_v03.json',3)
receipt['game_pngs'] = len(seen_paths)
receipt['original_hashes_unchanged'] = True
p.write_json(p.KIT/'verification_v03.json',receipt)
print(json.dumps({'sets':len(receipt['sets']),'pngs':len(seen_paths),'result':'PASS'}))
