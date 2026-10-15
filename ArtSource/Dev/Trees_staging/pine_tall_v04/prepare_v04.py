"""Prepare a numbered, self-contained revision driver without touching older files."""
from pathlib import Path
ROOT=Path(__file__).parent;OLD=ROOT.parent/'pine_tall_v03'
s=(OLD/'build_pine_tall_v03.py').read_text()
s=s.replace('v03','v04').replace('PINE_TALL_V03','PINE_TALL_V04')
s=s.replace("[FIRST,OLD,GAME/", "[FIRST,OLD,ROOT.parent/'pine_tall_v03',GAME/")
s=s.replace("pine_tall_v0[12]*","pine_tall_v0[123]*")
# Reduce only branch tube cross-section tessellation; trunk, roots and dead stubs stay.
needle="exec(compile(ast.fix_missing_locations(ast.Module(body=[node],type_ignores=[])),'baseline_skeleton','exec'));baseline_build=build"
change="""tier_loop=next(n for n in node.body if isinstance(n,ast.For) and isinstance(n.target,ast.Tuple))
for call in ast.walk(tier_loop):
    if isinstance(call,ast.Call) and isinstance(call.func,ast.Attribute) and call.func.attr=='tube' and len(call.args)>2:
        sub=call.args[2]
        if isinstance(sub,ast.Subscript) and isinstance(sub.value,ast.Tuple):
            values=[n.value for n in sub.value.elts]
            if values==[5,4,3]:sub.value.elts[0].value=4
            elif values==[4,3,3]:sub.value.elts[0].value=3
"""+needle
assert needle in s;s=s.replace(needle,change)
s=s.replace("reverse=True)[:3]","reverse=True)[:0]")
s=s.replace('len(out.f)==74 and len(out.v)==71','len(out.f)==68 and len(out.v)==68')
s=s.replace("new_wood.tube([start,mid,tip],[br,br*.64,.022*xy],(5,4,3)[lod])","new_wood.tube([start,mid,tip],[br,br*.64,.022*xy],(4,4,3)[lod])")
s=s.replace("new_wood.tube([mid,end.lerp(mid,.35)+Vector((0,0,.08*zs)),end],[br*.55,.025*xy,.009*xy],(4,3,3)[lod])","new_wood.tube([mid,end.lerp(mid,.35)+Vector((0,0,.08*zs)),end],[br*.55,.025*xy,.009*xy],(3,3,3)[lod])")
s=s.replace('optimizedInteriorFoldsPerClump=6 if lod==0 else 0','optimizedInteriorFoldsPerClump=9 if lod==0 else 0')
insertion=(ROOT/'fuller_crown_v04.py').read_text()
s=s.replace('SPECS=copy.deepcopy(olddata',insertion+'\nSPECS=copy.deepcopy(olddata')
s=s.replace('mesh,meta=build_more(spec,lod);ob=', 'mesh,meta=build_fuller(spec,lod);ob=')
s=s.replace("and .15<=meta['branchIncreasePercent']/100<=.20", "and meta['mainBranches']==previous_data['variants'][spec['variant']]['mainBranches']+8")
s=s.replace("crownWidth=spec['width']","crownWidth=max(dims[:2])")
s=s.replace("five added limbs; same 17-plate foliage density","fuller crown: eight more limbs, ten more clumps, longer lateral reach")
s=s.replace("Pine_Tall v04: +5 limbs, approved density retained", "Pine_Tall v04: fuller crown vs v03")
s=s.replace("for s in recipe['variants']:s['fbx']=s['fbx'].replace('v02','v04')", "for s in recipe['variants']:\n    s['fbx']=s['fbx'].replace('v02','v04');s['width']=next(r['crownWidth'] for r in rows if r['id']==s['id'] and r['lod']==0)")
s += "\n(ROOT/'coverage_geometry_v04.json').write_text(json.dumps(coverage_geometry))\n"
out=ROOT/'build_pine_tall_v04.py';assert not out.exists();out.write_text(s)
render=(OLD/'render_preview_v03.py').read_text().replace('_v03','_v04').replace("pine_tall_v02/Cozy_PineTall_v02.blend","pine_tall_v03/Cozy_PineTall_v03.blend").replace("'_v02_LOD0'","'_v03_LOD0'")
# The comparison path was not changed by the suffix replacement (it names v02).
(ROOT/'render_preview_v04.py').write_text(render)
validator=(OLD/'validate_roundtrip_v03.py').read_text().replace('v03','v04')
(ROOT/'validate_roundtrip_v04.py').write_text(validator)
print('Prepared v04 driver, renderer and roundtrip validator')
