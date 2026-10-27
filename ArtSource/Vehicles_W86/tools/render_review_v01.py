import bpy,sys,json,re,struct,math
from pathlib import Path
sys.path.insert(0,r'C:\Dev\Game\ArtSource\Vehicles_W86\tools');import blender_runner_v01 as R
ROOT=R.ROOT;BASE=Path(r'C:\Dev\Game');OUT=ROOT/'tools/review_cells_v01';OUT.mkdir(exist_ok=True)
CURRENT={'SEDAN':BASE/'Assets/OnlyVolunteers/Art/Map/Prefabs/Meshes/car_sedan_blue.asset','COMPACT':BASE/'Assets/OnlyVolunteers/Art/Map/Prefabs/Meshes/car_hatchback.asset','DISPLAY_COUPE':BASE/'Assets/OnlyVolunteers/Art/Map/Prefabs/Meshes/car_sedan_beige.asset','DISPLAY_GT':BASE/'Assets/OnlyVolunteers/Art/Map/Prefabs/Meshes/car_sedan_green.asset','PANEL_VAN':BASE/'ArtSource/Props/MAP_W86_v01/vehicles/van_on_jacks/MW86_VanOnJacks_v01.blend','ASTRA_STATIC_VAN':BASE/'ArtSource/Props/VAN-TIER0-ASTRA-001/VAN-TIER0-ASTRA-001_v02.blend','DUMP_TRUCK':BASE/'ArtSource/Props/MAP_W86_v01/vehicles/dump_truck/MW86_DumpTruck_v01.blend','CONTAINER_TRUCK':BASE/'ArtSource/Props/MAP_W86_v01/vehicles/truck_container/MW86_TruckContainer_v01.blend'}

def assetmesh(path):
 s=path.read_text();count=int(re.search(r'm_VertexCount: (\d+)',s).group(1));data=bytes.fromhex(re.search(r'_typelessdata: ([0-9a-f]+)',s).group(1));stride=len(data)//count;verts=[];uv=[]
 for i in range(count):
  x,y,z=struct.unpack_from('<3f',data,i*stride);verts.append((x,-z,y));uv.append(struct.unpack_from('<2f',data,i*stride+44))
 ib=bytes.fromhex(re.search(r'm_IndexBuffer: ([0-9a-f]+)',s).group(1));fmt='I' if 'm_IndexFormat: 1' in s else 'H';idx=struct.unpack('<'+fmt*(len(ib)//struct.calcsize(fmt)),ib);faces=[tuple(idx[i:i+3])[::-1] for i in range(0,len(idx),3)]
 me=bpy.data.meshes.new(path.stem);me.from_pydata(verts,[],faces);me.update();o=bpy.data.objects.new(path.stem,me);bpy.context.collection.objects.link(o);layer=me.uv_layers.new()
 for f in me.polygons:
  for li in f.loop_indices:layer.data[li].uv=uv[me.loops[li].vertex_index]
 m=bpy.data.materials.new('CURRENT_SK_Palette');m.use_nodes=True;n=m.node_tree.nodes.new('ShaderNodeTexImage');n.image=bpy.data.images.load(str(BASE/'ArtSource/Props/STREET_KIT/_lib/SK_Palette.png'));n.interpolation='Closest';m.node_tree.links.new(n.outputs['Color'],m.node_tree.nodes.get('Principled BSDF').inputs['Base Color']);m.node_tree.nodes.get('Principled BSDF').inputs['Roughness'].default_value=.8;me.materials.append(m)
 return [o]

def clear_helpers():
 for o in list(bpy.context.scene.objects):
  if o.type!='MESH':bpy.data.objects.remove(o,do_unlink=True)

if __name__=='__main__':
 stats=json.loads((ROOT/'validation_v01.json').read_text());meta=[]
 for p in stats:
  name=p['name'];path=Path(p['folder'])/(name+'_v01.blend')
  R.clean();obs=R.center(R.load(path,True));clear_helpers();R.render(OUT/(name+'_new.png'),900,520)
  scale=bpy.context.scene.camera.data.ortho_scale if bpy.context.scene.camera else None
  # Get camera fitting at equal real-world dimensions by using the stored image fit values from R.render.
  scale=R.LAST_ORTHO
  R.clean();cur=CURRENT[name];obs=assetmesh(cur) if cur.suffix=='.asset' else R.load(cur,True);obs=R.center(obs);clear_helpers();curtris=R.tris(obs);R.render(OUT/(name+'_current.png'),900,520,ortho=scale)
  R.clean();obs=R.center(R.load(BASE/'ArtSource/Props/FRIDGE-ASTRA-001/G34_v02/FRIDGE_ASTRA_001_v02.blend',True));clear_helpers();R.render(OUT/(name+'_astra.png'),900,520,ortho=scale)
  meta.append({'name':name,'current_source':str(cur),'current_triangles':curtris,'orthographic_width_m':scale})
 (OUT/'comparison_meta_v01.json').write_text(json.dumps(meta,indent=2),encoding='utf-8')
