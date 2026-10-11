"""G13 v04: five-category delta over immutable v03, Pillow/numpy only.

Usage: python process_v3_v04.py process  (once; exclusive creation)
       python process_v3_v04.py verify   (read-only, repeatable)
No downloads, Unity launch, old-file writes, or scene changes.
"""
from __future__ import annotations
import sys
sys.dont_write_bytecode = True
import argparse
import copy
import importlib.util
import json
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

spec = importlib.util.spec_from_file_location('g13_v03',Path(__file__).with_name('process_v3_v03.py'))
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)
CHANGED = ('1b_dirt_road','4c_corrugated_metal','3b_plaster_stucco','3c_concrete_panels','2a_asphalt')
MANIFEST = p.ASSETS/'materials_v3_v04.json'
BASE = p.ASSETS/'materials_v3_v03.json'
VALIDATION = p.KIT/'validation_v04.json'

def rgb(path):
    with Image.open(p.ROOT/path) as im:
        return np.asarray(im.convert('RGB'),dtype=np.float32)/255

def patch_field(seed):
    """A few large painted volumes, periodic in both axes; no speckle/streaks.

    The sample includes both periodic endpoints, so opposite edge colours are
    identical without pasting an artificial seam strip over the painted shape.
    """
    rng = np.random.default_rng(seed)
    uv = np.linspace(0,1,p.SIZE,dtype=np.float64)
    yy,xx = np.meshgrid(uv,uv,indexing='ij')
    phase = rng.uniform(0,2*np.pi,4)
    field = (.52*np.cos(2*np.pi*xx+phase[0])*np.cos(2*np.pi*yy+phase[1])
             +.30*np.cos(2*np.pi*(xx+yy)+phase[2])
             +.18*np.sin(2*np.pi*(2*xx-yy)+phase[3]))
    field -= field.mean()
    field /= np.max(np.abs(field))
    field[:,-1] = field[:,0]
    field[-1,:] = field[0,:]
    return field.astype(np.float32)

def value_paint(base, multiplier):
    # Multiplying sRGB by a scalar preserves hue/saturation and modulates HSV
    # value by the requested percentage; patches are not baked black AO.
    return np.clip(base*multiplier[...,None],0,1)

def concrete_pattern():
    uv = np.linspace(0,1,p.SIZE,dtype=np.float64)
    yy,xx = np.meshgrid(uv,uv,indexing='ij')
    px,py = np.mod(xx*2,1),np.mod(yy*2,1)
    # 3 m tile / 2 panels = 1.5 m. Soft 15 mm-wide seam falloff.
    distance_x = np.minimum(px,1-px)*1.5
    distance_y = np.minimum(py,1-py)*1.5
    seams = np.maximum(np.exp(-(distance_x/.015)**2),np.exp(-(distance_y/.015)**2))
    # A clean lower-edge shade within each panel, rather than downward streaks.
    bottom = np.exp(-((py-.93)/.055)**2)
    for field in (seams,bottom):
        field[:,-1] = field[:,0]
        field[-1,:] = field[0,:]
    return seams.astype(np.float32),bottom.astype(np.float32)

def ridge_pattern():
    x = np.linspace(0,1,p.SIZE,dtype=np.float64)
    theta = 2*np.pi*26*x
    tone = np.broadcast_to(np.cos(theta),(p.SIZE,p.SIZE)).copy().astype(np.float32)
    # z = 4 mm * cos(2 pi x / 76 mm); OpenGL tangent x = -dz/dx.
    tangent_x = np.broadcast_to((2*np.pi*.004/.076)*np.sin(theta),(p.SIZE,p.SIZE)).copy().astype(np.float32)
    tone[:,-1] = tone[:,0]
    tangent_x[:,-1] = tangent_x[:,0]
    n = np.stack((tangent_x,np.zeros_like(tone),np.ones_like(tone)),axis=-1)
    n /= np.linalg.norm(n,axis=-1,keepdims=True)
    return tone,n*.5+.5

def render(category,base_entry,records):
    base = rgb(base_entry['albedo'])
    normal = rgb(base_entry['normal'])
    recipe = {}
    if category=='1b_dirt_road':
        maps = p.source_maps(records[category])
        key='wood.light'
        base = p.seal(p.hue_saturation_map(maps['albedo'],p.palette()[key],.30,3))
        recipe = {'palette_key':key,'palette_hex':p.palette()[key],
            'palette_note':'Existing STYLE_BIBLE_v2 wood.light (#AB825B): warm earth brown-ochre between sand and mud; no new palette swatch.'}
    elif category=='4c_corrugated_metal':
        stripes,normal = ridge_pattern()
        base = value_paint(base,1+.06*stripes)
        recipe = {'metres_per_tile':{'x':1.976,'y':2},'ridge_period_metres':.076,
            'ridge_cycles_per_tile_x':26,'ridge_albedo_value_amplitude':.06,
            'ridge_height_amplitude_metres':.004,'normal_strength_baked':1.0,
            'normal_format_evidence':'Procedural OpenGL corrugation normal, tangent X = -dz/dx; 4 mm ridge height amplitude, 76 mm period; replaces v03 source relief.',
            'notes':'Vertical ridge bands at 7.6 cm centres. BumpScale=1: stronger ridge relief is baked into the map.'}
    elif category=='3b_plaster_stucco':
        patches=patch_field(3403)
        base=value_paint(base,1+.05*patches)
        recipe={'painted_patch_value_amplitude':.05,'painted_patch_seed':3403,
                'notes':'Large soft painted tonal patches, +/-5% HSV value; no grime or streaks.'}
    elif category=='3c_concrete_panels':
        patches=patch_field(3404)
        seams,bottom=concrete_pattern()
        base=value_paint(base,(1+.05*patches)*(1-.025*seams)*(1-.018*bottom))
        recipe={'metres_per_tile':{'x':3,'y':3},'panel_spacing_metres':1.5,
                'panel_seam_value_darken':.025,'panel_bottom_value_darken':.018,
                'painted_patch_value_amplitude':.05,'painted_patch_seed':3404,
                'notes':'2x2 panels in a 3x3 m tile; faint 1.5 m seam grid and restrained lower edge shade per panel, plus +/-5% large tonal patches. Normal/mask preserved.'}
    elif category=='2a_asphalt':
        patches=patch_field(3405)
        base=value_paint(base,1+.03*patches)
        recipe={'painted_patch_value_amplitude':.03,'painted_patch_seed':3405,
                'notes':'Keeps the v03 despeckled field; adds only large soft painted tonal patches, +/-3% HSV value.'}
    else:
        raise ValueError(category)
    return base,normal,recipe

def prior_files():
    roots=(p.KIT,p.THIRD,p.ASSETS)
    files=[x for folder in roots for x in folder.rglob('*') if x.is_file()]
    files += list((p.ROOT/'Assets/OnlyVolunteers/Art/Editor').glob('StyleKitV3MaterialBuilder.cs*'))
    return {p.rel(x):p.sha(x.read_bytes()) for x in files}

def process():
    if MANIFEST.exists() or VALIDATION.exists():
        raise FileExistsError('v04 already exists. Use verify; existing deliverables must not be overwritten.')
    # Preflight every path before generating a deliverable.
    base=p.read_json(BASE)
    src=p.read_json(p.ROOT/base['source_manifest'])
    records={r['category']:r for r in src['records']}
    entries={e['category']:e for e in base['entries']}
    for category in CHANGED:
        for kind in ('albedo','normal','mask'):
            path=p.ASSETS/'Textures'/category/f'{category}_v04_{kind}.png'
            if path.exists():
                raise FileExistsError(path)
    before=prior_files()
    manifest=copy.deepcopy(base)
    manifest.update(revision=4,parent_manifest=p.rel(BASE),
                    changed_categories=list(CHANGED),
                    revision_note='Four requested fixes affect five texture categories; other 18 sets retain v03 references.')
    for e in manifest['entries']:
        category=e['category']
        if category not in CHANGED:
            continue
        previous=entries[category]
        albedo,normal,recipe=render(category,previous,records)
        e.update(recipe)
        e['material_path']=p.rel(p.ASSETS/'Materials'/f'M3_{category}_v04.mat')
        for kind in ('albedo','normal','mask'):
            path=p.ASSETS/'Textures'/category/f'{category}_v04_{kind}.png'
            # Preserve unrelated normal/mask content byte-for-byte in the new
            # numbered set; the requested corrugation normal is the exception.
            if kind=='albedo':
                data=p.png_bytes(albedo)
            elif kind=='normal' and category=='4c_corrugated_metal':
                data=p.png_bytes(normal)
            else:
                data=(p.ROOT/previous[kind]).read_bytes()
            p.exclusive_bytes(path,data)
            e[kind]=p.rel(path)
        # Keep the category lookup and JsonUtility entries in sync.
        manifest['categories'][category]={'material_path':e['material_path'],'metres_per_tile':e['metres_per_tile']}
        print(category,'v04 CREATED',flush=True)
    p.write_json(MANIFEST,manifest)
    p.contact_sheet(manifest['entries'],4)
    validation=verify(manifest,before)
    validation.update(revision=4,prior_file_sha256=before,changed_categories=list(CHANGED))
    p.write_json(VALIDATION,validation)
    offset_and_comparison(manifest,entries)
    print(json.dumps({'new_sets':5,'new_pngs':15,'all_manifest_pngs_checked':69,'result':'PASS'}),flush=True)

def verify(manifest=None,before=None):
    manifest=manifest or p.read_json(MANIFEST)
    base=p.read_json(BASE)
    records={r['category']:r for r in p.read_json(p.ROOT/base['source_manifest'])['records']}
    base_entries={e['category']:e for e in base['entries']}
    # Re-run all 69 map checks, including unchanged sets used by the manifest.
    validation=p.verify(MANIFEST,4,write=False)
    checks=[]
    for e in manifest['entries']:
        category=e['category']
        if category not in CHANGED:
            assert e==base_entries[category],f'Unrequested category changed: {category}'
            continue
        expected_a,expected_n,recipe=render(category,base_entries[category],records)
        for kind in ('albedo','normal','mask'):
            data=p.png_bytes(expected_a) if kind=='albedo' else (
                 p.png_bytes(expected_n) if kind=='normal' and category=='4c_corrugated_metal' else
                 (p.ROOT/base_entries[category][kind]).read_bytes())
            assert p.sha(data)==p.sha((p.ROOT/e[kind]).read_bytes()),('Non-deterministic output',category,kind)
        assert manifest['categories'][category]=={'material_path':e['material_path'],'metres_per_tile':e['metres_per_tile']}
        checks.append({'category':category,'deterministic':True,'recipe':recipe})
    if before is None:
        before=p.read_json(VALIDATION)['prior_file_sha256']
    for path,digest in before.items():
        assert p.sha((p.ROOT/path).read_bytes())==digest,f'Old file altered: {path}'
    corr=next(e for e in manifest['entries'] if e['category']=='4c_corrugated_metal')
    assert abs(corr['metres_per_tile']['x']/corr['ridge_cycles_per_tile_x']-.076)<1e-10
    # Quantitative evidence that corrugation is visible in colour and stronger
    # in the normal than v03; compare frequency 26 and tangent slope RMS.
    old=rgb(base_entries['4c_corrugated_metal']['albedo'])
    new=rgb(corr['albedo'])
    wave=(new/np.maximum(old,.001)).mean(axis=(0,2))-1
    spectrum=np.abs(np.fft.rfft(wave-wave.mean()))
    assert np.argmax(spectrum[1:])+1==26
    oldn=rgb(base_entries['4c_corrugated_metal']['normal'])*2-1
    newn=rgb(corr['normal'])*2-1
    oldrms=float(np.sqrt(np.mean((oldn[...,:2]/np.maximum(oldn[...,2:3],.01))**2)))
    newrms=float(np.sqrt(np.mean((newn[...,:2]/np.maximum(newn[...,2:3],.01))**2)))
    assert newrms>oldrms*1.5,(oldrms,newrms)
    dirt=next(e for e in manifest['entries'] if e['category']=='1b_dirt_road')
    assert dirt['palette_hex']=='#AB825B'
    concrete=next(e for e in manifest['entries'] if e['category']=='3c_concrete_panels')
    assert concrete['metres_per_tile']['x']/2==concrete['panel_spacing_metres']==1.5
    validation.update(delta_checks=checks,prior_deliverables_unchanged=True,
                      ridge_period_metres=.076,ridge_fourier_peak_cycles=26,
                      ridge_normal_tangent_rms_v03=oldrms,ridge_normal_tangent_rms_v04=newrms)
    print('v04: deterministic delta / prior file hashes / physical spacing / stronger ridge normal PASS',flush=True)
    return validation

def offset_and_comparison(manifest,previous):
    comparison=Image.new('RGB',(1440,len(CHANGED)*284),'#ECE9E2')
    draw=ImageDraw.Draw(comparison)
    for index,category in enumerate(CHANGED):
        e=next(e for e in manifest['entries'] if e['category']==category)
        offset=Image.new('RGB',(p.SIZE*3,p.SIZE+46),'#ECE9E2')
        od=ImageDraw.Draw(offset)
        for j,kind in enumerate(('albedo','normal','mask')):
            a=np.asarray(Image.open(p.ROOT/e[kind]))
            rolled=np.roll(a,(p.SIZE//2,p.SIZE//2),axis=(0,1))
            offset.paste(Image.fromarray(rolled).convert('RGB'),(j*p.SIZE,46))
            od.text((j*p.SIZE+12,8),f'{category} / {kind} / offset 512 px',fill='#303641',font=p.font(25))
        p.save_image(p.KIT/f'previews/offset_v04/{category}_offset.png',offset)
        # Two tiled fields, old and new, plus the authored normal for review.
        y=index*284
        for col,(label,path) in enumerate((('v03 albedo',previous[category]['albedo']),
                                          ('v04 albedo',e['albedo']),('v04 normal',e['normal']))):
            tile=Image.open(p.ROOT/path).convert('RGB').resize((224,112),Image.Resampling.LANCZOS)
            for iy in range(2):
                for ix in range(2):
                    comparison.paste(tile,(col*480+12+ix*224,y+40+iy*112))
            draw.text((col*480+12,y+8),f'{category} / {label}',fill='#303641',font=p.font(18))
    p.save_image(p.KIT/'previews/diff_v04.png',comparison)

if __name__=='__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=('process','verify'))
    args=parser.parse_args()
    process() if args.command=='process' else verify()
