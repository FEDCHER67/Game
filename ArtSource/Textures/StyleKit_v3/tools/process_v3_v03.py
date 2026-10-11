"""G13: anonymous official acquisition and deterministic OAR palette processing.

Revision v03: centred palette Y; readable roof seams/end rings; softened slate relief.
Revision v02: missing source AO is neutral; grass detail softened; brick normals corrected.
Python 3.12 / Pillow / numpy only. No Unity process, authentication, or payment.
Commands: download, process, verify. Every write is exclusive; reruns must use
--revision N with a NEW number. Originals are never altered. Palette values
come from STYLE_BIBLE_v2's authoritative JSON appendix.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
import re
import sys
import urllib.request
import zipfile
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlparse, parse_qs

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = Path(__file__).resolve().parents[4]
KIT = ROOT / 'ArtSource/Textures/StyleKit_v3'
THIRD = ROOT / 'ArtSource/Textures/ThirdParty'
ASSETS = ROOT / 'Assets/OnlyVolunteers/Art/StyleKit_v3'
REVIEW = ROOT / 'Working/Reviews/Textures_2026-10-11'
DATE = '2026-10-11'
SIZE = 1024
UA = 'Mozilla/5.0 (G13 approved texture acquisition)'

# palette key, metres per tile X/Y, contrast fraction, smoothing radius,
# smoothness minimum/maximum, metallic fallback. 1 UV unit means 1 metre.
RECIPES = {
 '1a_grass': ('lawn', 2, 2, .20, 12, .05, .16, 0),
 '1b_dirt_road': ('sand', 2, 2, .30, 3, .05, .17, 0),
 '1c_beach_sand': ('sand', 2, 2, .24, 5, .05, .15, 0),
 '1d_gravel': ('grey.light', 2, 2, .30, 3, .06, .19, 0),
 '1e_mud': ('wood.dark', 2, 2, .24, 4, .38, .55, 0),
 '2a_asphalt': ('asphalt', 3, 3, .18, 12, .08, .19, 0),
 '2b_sidewalk_tiles': ('paving', 2, 2, .36, 1.2, .08, .21, 0),
 '2c_cobblestone': ('paving', 2, 2, .34, 1.5, .08, .21, 0),
 '3a_brick': ('brick', 1, 1, .40, 1, .08, .22, 0),
 '3b_plaster_stucco': ('cream', 2, 2, .20, 5, .05, .15, 0),
 '3c_concrete_panels': ('panel', 2, 2, .22, 5, .08, .20, 0),
 '3d_cinder_blocks': ('panel', 1.6, 1.6, .38, 1, .08, .19, 0),
 '4a_clay_roof_tiles': ('terracotta', 2, 2, .36, 1.5, .10, .24, 0),
 '4b_slate_shingles': ('slate', 2, 2, .20, 6, .10, .26, 0),
 '4c_corrugated_metal': ('slate', 2, 2, .22, 2, .20, .35, 1),
 '4d_flat_bitumen_roof': ('ink.light', 4, 4, .55, 2, .10, .22, 0),
 '5a_wood_planks_fences': ('wood', 1.6, 1.6, .28, 3, .08, .21, 0),
 '5b_logs': ('wood', 2.4, 2.4, .30, 1, .08, .20, 0),
 '5b_logs_endcap': ('wood', .30, .30, .30, 1, .08, .20, 0),
 '6a_painted_metal_panels': ('grey', 2, 2, .25, 2, .16, .29, 0),
 '6b_lightly_weathered_metal': ('grey', 2, 2, .22, 5, .17, .30, 0),
 '7a_rock_cliff': ('grey.dark', 4, 4, .26, 5, .07, .20, 0),
 '7b_tree_bark': ('wood', 1, 1, .30, 3, .05, .16, 0),
 '8a_water': ('water', 4, 4, .12, 7, .48, .60, 0),
}

def exclusive_bytes(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as f:
        f.write(data)

def exclusive_text(path, text):
    exclusive_bytes(path, text.encode('utf-8'))

def write_json(path, obj):
    exclusive_text(path, json.dumps(obj, indent=2, ensure_ascii=False) + '\n')

def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))

def rel(path):
    return Path(path).relative_to(ROOT).as_posix()

def sha(data):
    return hashlib.sha256(data).hexdigest()

def slug(text):
    return re.sub(r'[^A-Za-z0-9._-]+', '_', text).strip('_')

def request(url):
    # No cookie jar, credentials, tokens, or authenticated browser session.
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read(), r.geturl(), dict(r.headers)

class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'a' and 'href' in attrs:
            self.links.append(attrs['href'])

def official_links(html, page):
    p = Links()
    p.feed(html)
    return [urljoin(page, x) for x in p.links]

def download(revision):
    manifest_path = KIT / f'sources_v{revision:02}.json'
    if manifest_path.exists():
        raise FileExistsError(f'Use a new revision: {manifest_path}')
    picks = read_json(REVIEW / 'picks_OAR.json')
    picks['1a_grass'] = read_json(REVIEW / 'picks.json')['1a_grass']
    records = []
    # Mandatory grass gate first, before all other acquisitions.
    for category, pick in picks.items():
        if category in ('4d_flat_bitumen_roof', '5b_logs'):
            records.append({'category': category, 'status': 'procedural',
                            'author': 'OnlyVolunteers / G13', 'licence': 'Project original',
                            'title': category, 'files': []})
            continue
        record = {k: pick.get(k) for k in ('title', 'author', 'page')}
        record.update(category=category, date=DATE, files=[], status='pending')
        folder = THIRD / slug(record['author']) / slug(record['title']) / f'v{revision:02}'
        if folder.exists():
            raise FileExistsError(f'Existing source revision: {folder}')
        try:
            raw_html, final_page, headers = request(pick['page'])
            html = raw_html.decode('utf-8')
            links = official_links(html, final_page)
            host = urlparse(final_page).hostname
            if host == 'freestylized.com':
                quote = 'Royalty Free License: Free to use for all Commercial and Non-Commercial purposes.'
                assert quote in re.sub(r'<[^>]+>', '', html), 'Grass licence not verified'
                record.update(licence='Custom royalty-free', licence_quote=quote)
                candidates = [x for x in links if x.endswith('grass_01_1k.zip')]
                if not candidates:
                    raise RuntimeError('No anonymous 1K grass link; stop for login/access review')
            elif host == 'proctexture.com':
                quote = 'CC0 - free for commercial use, no attribution'
                assert quote in html, 'CC0 licence not verified'
                record.update(licence='CC0', licence_quote=quote)
                candidates = [x for x in links if '/pbr-packs/' in x and x.endswith('.zip')]
            elif host == 'ambientcg.com':
                quote = 'All assets are released under the Creative Commons CC0 license'
                assert quote in html, 'CC0 licence not verified'
                record.update(licence='CC0', licence_quote=quote)
                candidates = [x for x in links if '_1K-PNG.zip' in x]
            elif host == 'stylizedtextures.com':
                quote = 'Creative Commons Zero (CC0)'
                assert quote in html, 'CC0 metadata not verified'
                record.update(licence='CC0', licence_quote=quote,
                              status='skipped', reason='Official page and linked folder offer 4K only; brief permits 1K or 2K only.')
                exclusive_bytes(folder / 'official_page_v01.html', raw_html)
                record['evidence'] = rel(folder / 'official_page_v01.html')
                records.append(record)
                print(category, 'SKIPPED: 4K only', flush=True)
                continue
            else:
                raise RuntimeError(f'Unapproved page host: {host}')
            if not candidates:
                raise RuntimeError('Official 1K raw PBR archive not found')
            url = candidates[0]
            data, final_download, download_headers = request(url)
            archive = zipfile.ZipFile(io.BytesIO(data))
            if archive.testzip():
                raise RuntimeError('Invalid archive CRC')
            members = [x for x in archive.infolist() if not x.is_dir()]
            image_members = [x for x in members if x.filename.lower().endswith(('.png','.jpg','.jpeg'))]
            if not image_members:
                raise RuntimeError('Archive contains no PBR images (possible login page)')
            for member in image_members:
                with Image.open(io.BytesIO(archive.read(member))) as image:
                    if max(image.size) > 2048:
                        raise RuntimeError(f'Download exceeds 2K limit: {member.filename} {image.size}')
            name = Path(urlparse(url).path).name
            if not name.endswith('.zip'):
                name = parse_qs(urlparse(url).query)['file'][0]
            exclusive_bytes(folder / name, data)
            record.update(status='downloaded', resolution=1024, archive=rel(folder/name),
                          archive_bytes=len(data), archive_sha256=sha(data),
                          download_url=url, final_download_url=final_download,
                          anonymous_http_status=200, page_final_url=final_page)
            exclusive_bytes(folder/'official_page_v01.html', raw_html)
            record['evidence'] = rel(folder/'official_page_v01.html')
            for member in members:
                path = folder/'originals'/member.filename
                if '..' in Path(member.filename).parts or Path(member.filename).is_absolute():
                    raise RuntimeError('Unsafe archive member')
                blob = archive.read(member)
                exclusive_bytes(path, blob)
                item = {'path': rel(path), 'bytes': len(blob), 'sha256': sha(blob)}
                if member in image_members:
                    with Image.open(io.BytesIO(blob)) as image:
                        item.update(size=list(image.size), mode=image.mode)
                record['files'].append(item)
            records.append(record)
            print(category, 'DOWNLOADED', len(data), 'bytes', flush=True)
        except Exception as exc:
            record.update(status='failed', reason=str(exc))
            records.append(record)
            print(category, 'FAILED', str(exc), flush=True)
            if category == '1a_grass':
                write_json(manifest_path, {'revision': revision, 'date': DATE, 'records': records})
                raise RuntimeError('Mandatory grass anonymous-download gate failed; stopped') from exc
    write_json(manifest_path, {'revision': revision, 'date': DATE, 'records': records})
    provenance = THIRD / ('PROVENANCE.md' if not (THIRD/'PROVENANCE.md').exists() else f'PROVENANCE_v{revision:02}.md')
    lines = ['# G13 official texture provenance', '', f'Acquired {DATE}; revision v{revision:02}. Anonymous HTTP only; no login or payment.',
             'Archives and extracted originals are preserved unchanged. No alternate picks were downloaded.', '']
    for r in records:
        lines += [f"## {r['category']} — {r.get('title')}", '', f"Author: {r.get('author')}", f"Status: {r['status']}"]
        if r.get('page'):
            lines += [f"Official page: {r['page']}", f"Licence: {r.get('licence')}",
                      f"Licence quote: \"{r.get('licence_quote', '')}\"", f'Date: {DATE}']
        if r.get('archive'):
            lines += [f"Archive: `{r['archive']}` ({r['archive_bytes']:,} bytes)",
                      f"Official download: {r['download_url']}",
                      f"Actual redirect: {r['final_download_url']}", f"SHA-256: `{r['archive_sha256']}`", '', '| Original file | Bytes | Resolution | SHA-256 |', '|---|---:|---|---|']
            for f in r['files']:
                lines.append(f"| `{f['path']}` | {f['bytes']:,} | {f.get('size','—')} | `{f['sha256']}` |")
        if r.get('reason'):
            lines += [f"Reason: {r['reason']}"]
        lines += ['']
    exclusive_text(provenance, '\n'.join(lines))

def palette():
    text = (ROOT/'docs/art/STYLE_BIBLE_v2.md').read_text(encoding='utf-8')
    result = {}
    for obj in re.findall(r'\{[^{}]*"name"[^{}]*"hex"[^{}]*\}', text):
        s = json.loads(obj)
        result[s['name']] = s['hex']
        for key in ('light', 'dark'):
            if s.get(key):
                result[s['name']+'.'+key] = s[key]
    return result

def blur_wrap(a, radius):
    # FFT Gaussian: exact toroidal boundary condition, no clamp-edge halos.
    if radius <= 0:
        return a.copy()
    fy = np.fft.fftfreq(a.shape[0])[:, None]
    fx = np.fft.rfftfreq(a.shape[1])[None, :]
    kernel = np.exp(-2*np.pi**2*radius**2*(fx*fx+fy*fy))
    if a.ndim == 3:
        kernel = kernel[..., None]
    return np.fft.irfft2(np.fft.rfft2(a, axes=(0,1))*kernel, s=a.shape[:2], axes=(0,1)).astype(np.float32)

def median_wrap(a, pixels=5):
    pad = pixels//2
    padded = np.pad(a, ((pad,pad),(pad,pad)), mode='wrap')
    out = Image.fromarray(np.uint8(np.clip(padded,0,1)*255)).filter(ImageFilter.MedianFilter(pixels))
    return np.asarray(out, dtype=np.float32)[pad:-pad,pad:-pad]/255

def seal(a, width=12):
    """Smoothly reconcile the nearest edge samples; no hard pasted edge strip."""
    a = a.copy()
    for axis in (0,1):
        for i in range(width):
            w = .5*(1-i/width)**3
            first, last = [slice(None)]*a.ndim, [slice(None)]*a.ndim
            first[axis],last[axis] = i,-1-i
            f,l = a[tuple(first)].copy(),a[tuple(last)].copy()
            a[tuple(first)] = f*(1-w)+l*w
            a[tuple(last)] = l*(1-w)+f*w
    return a

def srgb_to_linear(a):
    return np.where(a <= .04045, a/12.92, ((a+.055)/1.055)**2.4)

def linear_to_srgb(a):
    return np.where(a <= .0031308, a*12.92, 1.055*np.maximum(a,0)**(1/2.4)-.055)

def luminance(rgb):
    return srgb_to_linear(rgb) @ np.array([.2126,.7152,.0722], dtype=np.float32)

def hue_saturation_map(source, hex_colour, contrast, radius, despeckle=False):
    """Replace chromaticity with palette hue/saturation, preserve soft source Y.

    Palette RGB is converted to linear light. Multiplying by target Y/source Y
    preserves the luminance ordering without copying source hue, stains, or AO.
    Contrast compression is applied to log luminance, centred on the swatch.
    """
    y = luminance(source)
    if despeckle:
        y = median_wrap(y, 9)
    y = blur_wrap(y, radius)
    log_y = np.log(np.maximum(y,.015))
    detail = np.clip(log_y-log_y.mean(), -.60, .60)
    detail = (detail-detail.mean())*contrast
    target = np.array([int(hex_colour[i:i+2],16)/255 for i in (1,3,5)], dtype=np.float32)
    base = srgb_to_linear(target)
    mapped = base[None,None,:]*np.exp(detail[...,None])
    return np.clip(linear_to_srgb(mapped),0,1)

def normal_from_height(height, amplitude=1):
    dx = (np.roll(height,-1,axis=1)-np.roll(height,1,axis=1))*.5
    dy = (np.roll(height,-1,axis=0)-np.roll(height,1,axis=0))*.5
    n = np.stack((-dx*amplitude,dy*amplitude,np.ones_like(dx)),axis=-1)
    return n/np.linalg.norm(n,axis=-1,keepdims=True)

def normal_gl(normal, height, filename, radius, brick=False):
    n = normal*2-1
    format_note = 'OpenGL from explicit filename'
    if 'dx' in filename.lower() or 'directx' in filename.lower():
        n[...,1] *= -1
        format_note = 'DirectX filename; green inverted to OpenGL'
    elif not any(k in filename.lower() for k in ('gl','opengl')):
        dy = (np.roll(height,-1,axis=0)-np.roll(height,1,axis=0))*.5
        covariance = float(np.sum((n[...,1]-n[...,1].mean())*dy))
        if abs(covariance) < 1e-6:
            # Uninformative flat source: generate a known OpenGL vector field.
            n = normal_from_height(height, 25)
            format_note = 'Flat/ambiguous source; OpenGL reconstructed from source height'
        else:
            if covariance < 0:
                n[...,1] *= -1
            format_note = f'Height-gradient Y orientation verified; green flipped={covariance < 0}'
    slope = n[...,:2]/np.maximum(n[...,2:3],.20)
    slope = blur_wrap(slope, min(radius,4))*.50
    if brick:
        # Doubling Y repeats compresses the height field vertically 2x.
        slope[...,1] *= 2.0
    if 'RoofingTiles002' in filename:
        magnitude = np.linalg.norm(slope,axis=-1,keepdims=True)
        slope *= np.minimum(1,.35/np.maximum(magnitude,.001))
        format_note += '; slate relief capped at 19 degrees after 50% reduction'
    slope = seal(slope)
    n = np.concatenate((slope,np.ones((*slope.shape[:2],1),dtype=np.float32)),axis=-1)
    n /= np.linalg.norm(n,axis=-1,keepdims=True)
    return n*.5+.5, format_note

def source_maps(record):
    maps = {}
    for item in record['files']:
        if 'size' not in item:
            continue
        p = Path(item['path'])
        name = p.stem.lower()
        if any(x in name for x in ('basecolor','_color_','_color')):
            key = 'albedo'
        elif 'normal' in name:
            if 'dx' in name and 'normal' in maps:
                continue
            key = 'normal'
        elif 'roughness' in name:
            key = 'roughness'
        elif any(x in name for x in ('ambientocclusion','ambient_occlusion')):
            key = 'ao'
        elif any(x in name for x in ('height','displacement')):
            key = 'height'
        elif any(x in name for x in ('metallic','metalness')):
            key = 'metallic'
        else:
            continue
        maps[key] = p
    required = ('albedo','normal','roughness','height')
    if any(k not in maps for k in required):
        raise ValueError(f"Missing maps for {record['category']}: {maps}")
    result = {}
    for key,p in maps.items():
        im = Image.open(ROOT/p).convert('RGB' if key in ('albedo','normal') else 'L')
        if im.size != (SIZE,SIZE):
            im = im.resize((SIZE,SIZE),Image.Resampling.LANCZOS)
        result[key] = np.asarray(im,dtype=np.float32)/255
    if 'ao' not in result:
        result['ao'] = np.ones((SIZE,SIZE),dtype=np.float32)
    result['normal_filename'] = str(maps['normal'])
    return result

def brick_stretch(maps):
    # Stretch X by 2 using one half-cycle, then repeat the original Y cycle twice.
    # Equivalent to stretching the SOURCE bricks 2x horizontally in world space
    # without cropping a nonperiodic half tile: keep full X cycle, double Y count.
    for key,a in list(maps.items()):
        if not isinstance(a,np.ndarray):
            continue
        im = Image.fromarray(np.uint8(np.clip(a,0,1)*255))
        half = np.asarray(im.resize((SIZE,SIZE//2),Image.Resampling.LANCZOS),dtype=np.float32)/255
        maps[key] = np.concatenate((half,half),axis=0)
    return maps

def procedural(category):
    yy,xx = np.mgrid[:SIZE,:SIZE].astype(np.float32)/SIZE
    if category == '4d_flat_bitumen_roof':
        phase = np.mod(xx*4,1)
        seam = np.exp(-((np.minimum(phase,1-phase))/.030)**2)
        field = .53 + .008*np.cos(2*np.pi*xx)+.006*np.sin(2*np.pi*yy)
        # Three large clean polygon patches, repeated toroidally.
        patch_im = Image.new('L',(SIZE,SIZE),0)
        draw = ImageDraw.Draw(patch_im)
        for points,tone in [([(130,180),(390,200),(420,390),(170,430)],80),
                            ([(550,620),(850,540),(900,800),(590,840)],115),
                            ([(610,110),(820,130),(860,290),(630,310)],60)]:
            draw.polygon(points,fill=tone)
        patches = blur_wrap(np.asarray(patch_im,dtype=np.float32)/255,4)
        field += .18*patches+.065*seam
        height = .5+.015*seam+.004*patches
        rough = .90-.16*patches
    elif category == '5b_logs':
        phase = np.mod(yy*8,1)
        seam = np.exp(-((np.minimum(phase,1-phase))/.025)**2)
        volume = np.sin(np.pi*phase)**2
        # Three sparse lengthwise grain bands per course, no dense wood hatch.
        grain = np.zeros_like(xx)
        for centre,width in ((.23,.018),(.58,.014),(.79,.022)):
            curve = centre+.018*np.sin(2*np.pi*xx)
            grain += np.exp(-((phase-curve)/width)**2)
        field = .51+.055*volume-.060*seam-.018*grain
        height = .5+.026*volume-.012*seam-.002*grain
        rough = .87+.02*grain
    elif category == '5b_logs_endcap':
        r = np.sqrt((xx-.5)**2+(yy-.5)**2)
        rings = sum(np.exp(-((r-c)/.008)**2) for c in (.17,.33))
        field = .54-.070*rings
        height = .5-.006*rings
        rough = .86+.03*rings
    else:
        raise ValueError(category)
    field = seal(field)
    return {'albedo':np.repeat(field[...,None],3,axis=-1), 'height':seal(height),
            'normal':normal_from_height(seal(height),120)*.5+.5,
            'normal_filename':'procedural_normal_gl', 'roughness':seal(rough),
            'ao':np.ones_like(field)}

def png_bytes(a):
    im = Image.fromarray(np.round(np.clip(a,0,1)*255).astype(np.uint8))
    out = io.BytesIO()
    im.save(out,format='PNG',compress_level=9)
    return out.getvalue()

def save_image(path, image):
    data = io.BytesIO()
    image.save(data,format='PNG',compress_level=9)
    exclusive_bytes(path,data.getvalue())

def font(size):
    for p in ('C:/Windows/Fonts/arial.ttf','C:/Windows/Fonts/segoeui.ttf'):
        if Path(p).exists():
            return ImageFont.truetype(p,size)
    return ImageFont.load_default(size=size)

def process(revision, source_revision):
    sources = read_json(KIT/f'sources_v{source_revision:02}.json')
    manifest_path = ASSETS / ('materials_v3.json' if not (ASSETS/'materials_v3.json').exists() else f'materials_v3_v{revision:02}.json')
    if (KIT/f'validation_v{revision:02}.json').exists():
        raise FileExistsError('Processing revision already exists')
    colours = palette()
    for record in sources['records']:
        if record['status']=='downloaded':
            source_maps(record)
    entries,skipped = [],[]
    for record in sources['records']:
        if record['status'] not in ('downloaded','procedural'):
            skipped.append({'category':record['category'],'reason':record.get('reason',record['status'])})
            continue
        categories = [record['category']]
        if record['category'] == '5b_logs':
            categories.append('5b_logs_endcap')
        for category in categories:
            key,mx,my,contrast,radius,smin,smax,metal = RECIPES[category]
            maps = procedural(category) if record['status']=='procedural' else source_maps(record)
            if category == '3a_brick':
                maps = brick_stretch(maps)
            albedo = hue_saturation_map(maps['albedo'],colours[key],contrast,radius,category=='2a_asphalt')
            albedo = seal(albedo)
            normal,format_note = normal_gl(maps['normal'],maps['height'],maps['normal_filename'],radius,category=='3a_brick')
            # Calm AO: no source black pockets; no AO multiplied into the albedo.
            ao = .90+.10*blur_wrap(maps['ao'],radius)
            roughness = blur_wrap(maps['roughness'],radius)
            smoothness = smin+(1-roughness)*(smax-smin)
            metallic = blur_wrap(maps.get('metallic',np.full((SIZE,SIZE),metal,dtype=np.float32)),radius)
            if category.startswith('6'):
                metallic = np.minimum(metallic,.18)  # Paint is dielectric; sparse exposed chips only.
            mask = seal(np.stack((metallic,ao,np.zeros_like(ao),smoothness),axis=-1))
            folder = ASSETS/'Textures'/record['category']
            stem = f'{category}_v{revision:02}'
            outputs = {}
            for kind,a in (('albedo',albedo),('normal',normal),('mask',mask)):
                path = folder/f'{stem}_{kind}.png'
                exclusive_bytes(path,png_bytes(a))
                outputs[kind] = rel(path)
            material = ASSETS/'Materials'/f'M3_{category}.mat'
            if material.exists() or revision>1:
                material = ASSETS/'Materials'/f'M3_{category}_v{revision:02}.mat'
            entries.append({'category':category,'material_path':rel(material),
                            'metres_per_tile':{'x':mx,'y':my},'palette_key':key,'palette_hex':colours[key],
                            'albedo':outputs['albedo'],'normal':outputs['normal'],'mask':outputs['mask'],
                            'source_category':record['category'],'normal_convention':'OpenGL',
                            'normal_strength_baked':.5,'normal_format_evidence':format_note,
                            'environment_reflections':category=='8a_water',
                            'contrast_fraction':contrast,'smoothing_radius_px':radius,
                            'notes': ('Opaque static URP Lit baseline; scrolling/depth/foam shader is outside G13.' if category=='8a_water' else
                                      'Two-ring end cap, one log end per 0.30 m tile.' if category=='5b_logs_endcap' else
                                      'Full source X period, Y cycle repeated twice: brick width/height doubled.' if category=='3a_brick' else '')})
            print(category,'PROCESSED',flush=True)
    manifest = {'schema':'OnlyVolunteers.StyleKitV3/1','revision':revision,'date':DATE,
                'uv_convention':'1 UV unit = 1 metre; builder uses scale 1/metres_per_tile on every map.',
                'mask_layout':'R=metallic G=ambient occlusion B=0 A=smoothness; linear texture',
                'source_manifest':rel(KIT/f'sources_v{source_revision:02}.json'),
                'categories':{e['category']:{'material_path':e['material_path'],'metres_per_tile':e['metres_per_tile']} for e in entries},
                'entries':entries,'skipped':skipped}
    write_json(manifest_path,manifest)
    contact_sheet(entries,revision)
    verify(manifest_path, revision, write=True)

def contact_sheet(entries,revision):
    cols,cell,header = 4,448,92
    rows = math.ceil(len(entries)/cols)
    sheet = Image.new('RGB',(cols*cell,header+rows*(cell+70)), '#ECE9E2')
    d = ImageDraw.Draw(sheet)
    d.text((20,15),f'G13 / STYLE KIT v3 / v{revision:02} / OAR palette',fill='#303641',font=font(27))
    d.text((20,52),'Each swatch repeats 2 x 2. 1024 px maps / quiet colour / softened normals / no grime.',fill='#515661',font=font(18))
    for i,e in enumerate(entries):
        x,y = (i%cols)*cell,header+(i//cols)*(cell+70)
        tile = Image.open(ROOT/e['albedo']).convert('RGB').resize((216,216),Image.Resampling.LANCZOS)
        for iy in range(2):
            for ix in range(2):
                sheet.paste(tile,(x+8+216*ix,y+8+216*iy))
        d.text((x+8,y+444),e['category'],fill='#303641',font=font(17))
        d.text((x+8,y+468),f"{e['palette_key']} {e['palette_hex']} / {e['metres_per_tile']['x']:g} x {e['metres_per_tile']['y']:g} m",fill='#515661',font=font(16))
    save_image(KIT/('previews/contact_v01.png' if not (KIT/'previews/contact_v01.png').exists() else f'previews/contact_v{revision:02}.png'),sheet)

def verify(manifest_path,revision,write=False):
    manifest = read_json(manifest_path)
    checks = []
    for e in manifest['entries']:
        offset = Image.new('RGB',(SIZE*3,SIZE+46),'#ECE9E2')
        draw = ImageDraw.Draw(offset)
        item = {'category':e['category'],'maps':{}}
        for index,kind in enumerate(('albedo','normal','mask')):
            path = ROOT/e[kind]
            data = path.read_bytes()
            im = Image.open(io.BytesIO(data))
            assert im.size==(SIZE,SIZE), (path,im.size)
            assert im.mode==('RGBA' if kind=='mask' else 'RGB'), (path,im.mode)
            a = np.asarray(im).astype(np.int16)
            xdiff = np.abs(a[:,0]-a[:,-1])
            ydiff = np.abs(a[0]-a[-1])
            assert xdiff.max()==0 and ydiff.max()==0, f'Seam mismatch: {path}'
            if kind=='normal':
                n = a.astype(np.float32)/255*2-1
                error = float(np.max(np.abs(np.linalg.norm(n,axis=-1)-1)))
                assert error<.015 and np.min(n[...,2])>0, (path,error)
            if kind=='mask':
                assert np.min(a[...,1])>=229 and np.max(a[...,2])==0
            item['maps'][kind] = {'path':e[kind], 'bytes':len(data),'sha256':sha(data),
                'size':list(im.size),'mode':im.mode,'edge_difference_max_x':int(xdiff.max()),
                'edge_difference_max_y':int(ydiff.max()),
                'wrap_step_mean':float((xdiff.mean()+ydiff.mean())/2)}
            rolled = np.roll(np.roll(a,SIZE//2,axis=0),SIZE//2,axis=1)
            offset.paste(Image.fromarray(rolled.astype(np.uint8)).convert('RGB'),(index*SIZE,46))
            draw.text((index*SIZE+12,8),f"{e['category']} / {kind} / offset 512 px",fill='#303641',font=font(25))
        if write:
            save_image(KIT/f"previews/offset_v{revision:02}/{e['category']}_offset.png",offset)
        # Byte-for-byte determinism evidence regenerates all three maps in memory.
        checks.append(item)
    sources = read_json(ROOT/manifest['source_manifest'])
    for record in sources['records']:
        if record['status']=='downloaded':
            assert sha((ROOT/record['archive']).read_bytes())==record['archive_sha256']
            for f in record['files']:
                assert sha((ROOT/f['path']).read_bytes())==f['sha256']
    validation = {'revision':revision,'date':DATE,'manifest':rel(manifest_path),
                  'texture_sets':len(checks),'game_pngs':len(checks)*3,
                  'normal_convention':'OpenGL; source Y verified against height or explicit GL filenames',
                  'mask_channels':'R metallic; G restrained AO; B zero; A smoothness',
                  'original_hashes_unchanged':True,'checks':checks,
                  'limits':['Unity not launched; editor menu execution and in-scene lighting acceptance remain for the lead.',
                            'Numerical edge checks plus saved full-size half-offset images; visual inspection is also required.']}
    if write:
        write_json(KIT/f'validation_v{revision:02}.json',validation)
    print(json.dumps({'texture_sets':len(checks),'game_pngs':len(checks)*3,'seams':'PASS','source_hashes':'PASS'}),flush=True)
    return validation

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=('download','process','verify'))
    parser.add_argument('--revision',type=int,default=1)
    parser.add_argument('--source-revision',type=int,default=1)
    parser.add_argument('--manifest',type=Path)
    args = parser.parse_args()
    if args.revision<1:
        parser.error('Revision must be positive')
    if args.command=='download':
        download(args.revision)
    elif args.command=='process':
        process(args.revision,args.source_revision)
    else:
        verify(args.manifest or ASSETS/'materials_v3.json',args.revision)

if __name__=='__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    main()
