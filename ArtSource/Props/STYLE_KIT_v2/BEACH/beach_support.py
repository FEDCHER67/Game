"""BEACH-local adapters. Import the shared kit without writing anywhere outside BEACH."""
import hashlib
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
LIB = HERE.parent / '_lib'
sys.path.insert(0, str(LIB))
import stylekit2 as sk
import bpy


def readonly_atlas(out_dir=None):
    png, layout = LIB / 'Look_Palette_v2.png', LIB / 'Look_Palette_v2.json'
    if not png.is_file() or not layout.is_file():
        raise RuntimeError('The existing shared palette is required; BEACH never regenerates it.')
    data = json.loads(layout.read_text(encoding='utf-8'))
    for name in sk.CELLS:
        if data['swatches'][name]['hex'] != sk._hexstr(sk.SWATCH[name]):
            raise RuntimeError(f'Shared palette does not match the bible: {name}')
    return png, layout


sk.write_atlas = readonly_atlas
sk.write_patterns = lambda out_dir=None: {}
sk.write_kit_summary = lambda *args, **kwargs: None


class BeachStudio(sk.Studio):
    def _person(self):
        # The brief excludes people even in previews. A hidden empty satisfies the studio interface.
        ob = bpy.data.objects.new('NoScaleFigure', None)
        self.coll.objects.link(ob)
        ob.hide_render = True
        return ob


class BeachFamily(sk.Family):
    def __init__(self, *args, **kwargs):
        self.preview_existing = '--preview-existing' in sys.argv
        argv = list(sys.argv)
        output_arguments = [arg.split('=', 1)[1] for arg in argv if arg.startswith('--out=')]
        output_arguments += [argv[i + 1] for i, arg in enumerate(argv[:-1]) if arg == '--out']
        for value in output_arguments:
            target = Path(value).resolve()
            if not target.is_relative_to(HERE):
                raise RuntimeError('--out must stay inside BEACH/')
        if self.preview_existing and '--force' not in sys.argv:
            # Only bypass the constructor's existence guard. finish() is prohibited in this mode.
            sys.argv.append('--force')
        try:
            super().__init__(*args, **kwargs)
        finally:
            sys.argv[:] = argv
        if self.args.revision < 1:
            raise RuntimeError('--revision must be positive')
        if self.preview_existing:
            self.args.force = False

    def studio(self):
        if self._studio is None:
            self._studio = BeachStudio(self.scene, self.args.samples, not self.args.cpu)
        return self._studio

    def want(self, fname):
        # Supplementary preview runs never replace an already rendered image.
        return super().want(fname) and not (self.preview_dir / fname).exists()

    def finish(self, *args, **kwargs):
        if self.preview_existing:
            raise RuntimeError('--preview-existing cannot export or save a model')
        report = super().finish(*args, **kwargs)
        if not report['all_checks_passed']:
            raise RuntimeError('BEACH validation failed')
        return report


def bevel(m, size, col, at=(0, 0, 0), radius=0.025, segments=2, M=None, name='body', **kw):
    return m.bevel_box(*size, radius, col, M=(M or sk.Matrix.Identity(4)) @ sk.T(*at),
                       segments=segments, normals='weighted', name=name, **kw)


def beam(m, p0, p1, width, depth, col, radius=0.02, name='beam'):
    """Two-segment bevel on longitudinal edges, without spending 108 tris on every beam end.
    Closed 12-corner cross section, weighted normals, 44 triangles per member.
    """
    from mathutils import Vector
    import math
    a, b = Vector(p0), Vector(p1)
    direction = b - a
    mat = direction.to_track_quat('Z', 'Y').to_matrix().to_4x4()
    mat.translation = (a + b) / 2
    r = min(radius, width * 0.4, depth * 0.4)
    poly = []
    for cx, cy, start in ((width / 2 - r, depth / 2 - r, 0),
                          (-width / 2 + r, depth / 2 - r, 90),
                          (-width / 2 + r, -depth / 2 + r, 180),
                          (width / 2 - r, -depth / 2 + r, 270)):
        for i in range(3):
            t = math.radians(start + i * 45)
            poly.append((cx + r * math.cos(t), cy + r * math.sin(t)))
    m.prism_xy(poly, -direction.length / 2, direction.length / 2, col, M=mat,
               normals='weighted', member=min(width, depth), name=name)


def cross(m, size, thickness, col, at):
    s, a = size / 2, size * 0.17
    poly = [(-a, -s), (a, -s), (a, -a), (s, -a), (s, a), (a, a),
            (a, s), (-a, s), (-a, a), (-s, a), (-s, -a), (-a, -a)]
    m.prism(poly, thickness, col, M=sk.T(*at), normals='flat', member=thickness,
            name='red_cross')


def load_preview_assets(fam, folder, blend_name, names):
    """Read-only library load for comparison/dressing, after the deliverable .blend was saved."""
    path = HERE.parent / folder / blend_name
    with bpy.data.libraries.load(str(path), link=False) as (src, dst):
        missing = set(names) - set(src.objects)
        if missing:
            raise RuntimeError(f'Missing reference assets: {missing}')
        dst.objects = list(names)
    coll = bpy.data.collections.get('Showcase_NotExported')
    if coll is None:
        coll = bpy.data.collections.new('Showcase_NotExported')
        fam.scene.collection.children.link(coll)
    result = {}
    for requested, ob in zip(names, dst.objects):
        coll.objects.link(ob)
        ob.location = (0, 0, 0)
        ob.rotation_euler = (0, 0, 0)
        ob.scale = (1, 1, 1)
        # Same palette material under precisely the same studio lighting.
        ob.data.materials.clear()
        ob.data.materials.append(sk.palette_material())
        result[requested] = ob
    return result


def palette_fingerprint():
    return hashlib.sha256((LIB / 'Look_Palette_v2.png').read_bytes()).hexdigest()
