"""Registry of M2 static prop types (filled by props_*.py)."""
TYPES = {}


def prop(name, kinds, variants=('A',), data_size=None, placement='box', front=None, collider_note='',
         notes='', y_offset=0.0, rotation_offset_y=0.0, scale_rule=None, folder=None, lod_over=1000, budget=1500,
         variant_rule=None, model_size=None, view=None):
    """placement 'box'   : Unity rotation Euler(0, -rot_deg + rotation_offset_y, 0), model frame = W85 placeholder box frame
                           (Unity local X = data size[0], local Z = data size[1]).
       placement 'facing': Euler(0, 90 - rot_deg, 0) (prefab convention; model front = Unity +Z faces the data rot direction)."""
    def wrap(fn):
        TYPES[name] = dict(fn=fn, kinds=list(kinds), variants=list(variants), data_size=data_size, placement=placement,
                           front=front, collider_note=collider_note, notes=notes, y_offset=y_offset,
                           rotation_offset_y=rotation_offset_y, scale_rule=scale_rule, folder=folder or name,
                           lod_over=lod_over, budget=budget, variant_rule=variant_rule, model_size=model_size,
                           view=view)
        return fn
    return wrap
