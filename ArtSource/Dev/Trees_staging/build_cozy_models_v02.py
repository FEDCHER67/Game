"""Original G23 geometry, designed from visual study only; no reference files copied."""
import bpy, math, random, json
from pathlib import Path
from mathutils import Vector

ROOT = Path(r'C:\Dev\Game\ArtSource\Dev\Trees_staging')
OUT = ROOT/'v02/Models'
OUT.mkdir(parents=True, exist_ok=True)
SOURCE = ROOT/'Source'
SOURCE.mkdir(exist_ok=True)
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
report=[]

def material(name, color):
    m=bpy.data.materials.new(name); m.diffuse_color=(*color,1); m.use_nodes=True
    m.node_tree.nodes.get('Principled BSDF').inputs['Base Color'].default_value=(*color,1)
    m.node_tree.nodes.get('Principled BSDF').inputs['Roughness'].default_value=.9
    return m
bark=material('MAT_Cozy_Bark',(.29,.16,.075))
pine=[bark,material('MAT_Cozy_PineShade',(.045,.18,.17)),material('MAT_Cozy_PineLight',(.10,.29,.24))]
gold=[bark,material('MAT_Cozy_GoldShade',(.72,.38,.06)),material('MAT_Cozy_GoldLight',(.94,.66,.12))]

def cone_between(a,b,r0,r1,sides,mat,items):
    d=Vector(b)-Vector(a)
    bpy.ops.mesh.primitive_cone_add(vertices=sides, radius1=r0, radius2=r1, depth=d.length, location=(Vector(a)+Vector(b))/2)
    ob=bpy.context.object; ob.rotation_euler=d.to_track_quat('Z','Y').to_euler()
    ob.data.materials.append(mat); items.append(ob)

def crown_tier(z,rad,height,spokes,seed,items,mats):
    rng=random.Random(seed); vertices=[]
    # Three faceted rings: drooping uneven tips, a shoulder, and an off-centre apex.
    for ring in range(2):
        for i in range(spokes*2):
            angle=math.tau*i/(spokes*2)+seed*.43
            r=rad*(1 if i%2==0 else .62)*(1+rng.uniform(-.14,.12))
            if ring: r*=.48
            zz=z+(rng.uniform(-.045,.015) if not ring else height*.45+rng.uniform(-.02,.02))
            vertices.append((math.cos(angle)*r,math.sin(angle)*r,zz))
    n=spokes*2; vertices += [(rad*.09,rad*-.06,z+height),(0,0,z+.01)]
    faces=[]
    for i in range(n):
        j=(i+1)%n
        faces += [(i,j,n+j),(i,n+j,n+i),(n+i,n+j,2*n),(j,i,2*n+1)]
    mesh=bpy.data.meshes.new('CrownTier'); mesh.from_pydata(vertices,[],faces); mesh.update()
    ob=bpy.data.objects.new('CrownTier',mesh); bpy.context.collection.objects.link(ob)
    for m in mats[1:]: mesh.materials.append(m)
    for f in mesh.polygons: f.material_index=0 if f.index%7<3 else 1
    items.append(ob)

for kind,mats in [('Conifer',pine),('BroadleafTrial',gold)]:
  for variant in range(2):
    model=f'Cozy_{kind}_{chr(65+variant)}_v02'
    collection=bpy.data.collections.new(model); bpy.context.scene.collection.children.link(collection)
    exported=[]
    for lod in range(2):
      rng=random.Random(2300+variant); items=[]
      sides=9 if lod==0 else 6
      cone_between((0,0,0),(.014,-.009,.95 if kind=='Conifer' else .76),.045,.006,sides,bark,items)
      if kind=='Conifer':
        layers=8 if lod==0 else 6
        for i in range(layers):
          q=i/(layers-1); z=.24+q*.62
          radius=(.265 if variant==0 else .225)*(1-q*.82)
          crown_tier(z,radius,.20*(1-q*.35),10 if lod==0 else 6,variant*29+i+1,items,mats)
          if lod==0 and i<6:
            for j in range(3):
              angle=j*math.tau/3+i*.72
              cone_between((0,0,z+.06),(math.cos(angle)*radius*.86,math.sin(angle)*radius*.86,z+.015),.011,.002,5,bark,items)
        cone_between((.008,-.005,.87),(.012,-.008,1),.045,0,7,mats[2],items)
      else:
        # Uneven crown lobes and visible rising forks, with warm shaded lower clumps.
        clusters=[(-.18,-.03,.63,.19),(.16,.015,.69,.205),(-.055,.08,.83,.21),(.07,-.07,.89,.15),(-.025,-.16,.73,.18),(.13,.15,.77,.15)]
        for i,(x,y,z,r) in enumerate(clusters):
          if variant: x,y=x*.90+.025,y*1.12; z-=.025 if i%2 else 0
          cone_between((0,0,.24+i*.035),(x*.90,y*.9,z),.022,.006,sides,bark,items)
          bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2 if lod==0 else 1,radius=r,location=(x,y,z))
          ob=bpy.context.object; ob.scale=(1+rng.uniform(-.08,.08),1+rng.uniform(-.10,.10),.8+rng.uniform(-.08,.12))
          ob.data.materials.append(mats[1]); ob.data.materials.append(mats[2])
          for p in ob.data.polygons: p.material_index=0 if p.center.z<-.035 or rng.random()<.15 else 1
          items.append(ob)
      bpy.ops.object.select_all(action='DESELECT')
      for ob in items: ob.select_set(True)
      bpy.context.view_layer.objects.active=items[0]; bpy.ops.object.join()
      ob=bpy.context.object; ob.name=f'SM_{model}_LOD{lod}'
      bpy.ops.object.transform_apply(location=False,rotation=True,scale=True)
      bpy.context.scene.cursor.location=(0,0,0); bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
      # Consolidate to exactly three deterministic material slots.
      old=list(ob.data.materials); indices=[mats.index(old[p.material_index]) for p in ob.data.polygons]
      ob.data.materials.clear()
      for m in mats: ob.data.materials.append(m)
      for p,idx in zip(ob.data.polygons,indices): p.material_index=idx; p.use_smooth=False
      maxz=max(v.co.z for v in ob.data.vertices); minz=min(v.co.z for v in ob.data.vertices)
      for v in ob.data.vertices:
          v.co.z-=minz; v.co/=(maxz-minz)
      # UVs are intentionally immaterial: solid colour faceted surfaces, no texture atlas.
      bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT'); bpy.ops.mesh.normals_make_consistent(inside=False) if hasattr(bpy.ops.mesh,'normals_make_consistent') else None
      bpy.ops.object.mode_set(mode='OBJECT')
      tri=ob.modifiers.new('ExportTriangles','TRIANGULATE'); bpy.ops.object.modifier_apply(modifier=tri.name)
      for c in list(ob.users_collection): c.objects.unlink(ob)
      collection.objects.link(ob); exported.append(ob)
      report.append(dict(model=model,lod=lod,vertices=len(ob.data.vertices),triangles=len(ob.data.polygons),materials=len(ob.data.materials),height=max(v.co.z for v in ob.data.vertices),scale=list(ob.scale)))
    bpy.ops.object.select_all(action='DESELECT')
    for ob in exported: ob.select_set(True)
    bpy.ops.export_scene.fbx(filepath=str(OUT/(model+'.fbx')),use_selection=True,object_types={'MESH'},global_scale=1,apply_unit_scale=True,apply_scale_options='FBX_SCALE_UNITS',axis_forward='-Z',axis_up='Y',use_mesh_modifiers=True,add_leaf_bones=False,bake_anim=False,path_mode='AUTO')

bpy.context.scene.unit_settings.system='METRIC'
bpy.ops.wm.save_as_mainfile(filepath=str(SOURCE/'Trees_Cozy_v02.blend'))
(SOURCE/'model_validation_v02.json').write_text(json.dumps(report,indent=2))
assert all(r['height']> .999 and r['triangles']<4500 and r['materials']==3 for r in report)
print('G23 MODEL VALIDATION PASS',json.dumps(report))
