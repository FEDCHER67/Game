import bpy,math,json
from pathlib import Path
from mathutils import Vector
ROOT=Path(r'C:\Dev\Game\ArtSource\Vehicles_W86')
def clean():
 bpy.ops.wm.read_factory_settings(use_empty=True)
 bpy.context.scene.unit_settings.system='METRIC';bpy.context.scene.unit_settings.scale_length=1

def load(path,lod0=False):
 path=Path(path)
 if path.suffix=='.blend':
  with bpy.data.libraries.load(str(path),link=False) as (a,b):b.objects=a.objects
  for o in b.objects:
   if o:bpy.context.collection.objects.link(o)
  bpy.context.scene.frame_set(1)
 elif path.suffix=='.fbx':bpy.ops.import_scene.fbx(filepath=str(path))
 else:bpy.ops.wm.obj_import(filepath=str(path),forward_axis='NEGATIVE_Z',up_axis='Y')
 obs=[o for o in bpy.context.scene.objects if o.type=='MESH' and not o.name.startswith('UCX')]
 if lod0 and any('LOD0' in o.name for o in obs):obs=[o for o in obs if 'LOD0' in o.name]
 for o in list(bpy.context.scene.objects):
  if o.type=='MESH' and o not in obs:bpy.data.objects.remove(o,do_unlink=True)
 return obs

def bounds(obs):
 pts=[o.matrix_world@v.co for o in obs for v in o.data.vertices]
 return Vector([min(v[i] for v in pts) for i in range(3)]),Vector([max(v[i] for v in pts) for i in range(3)])

def center(obs):
 lo,hi=bounds(obs);shift=Vector(((lo.x+hi.x)/2,(lo.y+hi.y)/2,lo.z))
 for o in obs:
  mx=o.matrix_world.copy();o.parent=None;o.matrix_world=mx
  o.matrix_world.translation-=shift
 return obs

def tris(obs):return sum(sum(len(p.vertices)-2 for p in o.data.polygons) for o in obs)

def material(name,hex,metal=0,rough=.5):
 m=bpy.data.materials.get(name)
 if m:return m
 h=hex.lstrip('#');rgb=[int(h[i:i+2],16)/255 for i in (0,2,4)];rgb=[c/12.92 if c<.04045 else ((c+.055)/1.055)**2.4 for c in rgb]
 m=bpy.data.materials.new(name);m.diffuse_color=(*rgb,1);m.use_nodes=True;n=m.node_tree.nodes.get('Principled BSDF');n.inputs['Base Color'].default_value=(*rgb,1);n.inputs['Metallic'].default_value=metal;n.inputs['Roughness'].default_value=rough
 return m

def aim(o,p):o.rotation_euler=(Vector(p)-o.location).to_track_quat('-Z','Y').to_euler()

def render(path,width=720,height=460,ortho=None):
 sc=bpy.context.scene;obs=[o for o in sc.objects if o.type=='MESH' and not o.hide_render];lo,hi=bounds(obs);target=(lo+hi)/2
 bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-.015));floor=bpy.context.object;floor.name='PREVIEW_Floor';floor.data.materials.append(material('PREVIEW_Floor','#858C91',0,.82))
 sc.render.engine='CYCLES';sc.cycles.samples=12;sc.cycles.use_denoising=True;sc.cycles.device='CPU'
 sc.world=bpy.data.worlds.new('PREVIEW_World');sc.world.color=(.26,.26,.26)
 for name,loc,power,size in [('Key',(4,-6,9),1800,7),('Fill',(-5,-2,5),1000,6),('Rim',(3,7,7),1600,5)]:
  bpy.ops.object.light_add(type='AREA',location=loc);l=bpy.context.object;l.name='PREVIEW_'+name;l.data.energy=power;l.data.shape='DISK';l.data.size=size;aim(l,target)
 bpy.ops.object.camera_add(location=target+Vector((8,-11,7)));cam=bpy.context.object;cam.name='PREVIEW_Camera';cam.data.type='ORTHO';aim(cam,target);sc.camera=cam;bpy.context.view_layer.update()
 inv=cam.matrix_world.inverted();pts=[inv@Vector((x,y,z)) for x in (lo.x,hi.x) for y in (lo.y,hi.y) for z in (lo.z,hi.z)];sp=[max(v[i] for v in pts)-min(v[i] for v in pts) for i in (0,1)];cam.data.ortho_scale=ortho or max(sp[0],sp[1]*width/height)*1.15
 global LAST_ORTHO;LAST_ORTHO=cam.data.ortho_scale
 sc.render.resolution_x=width;sc.render.resolution_y=height;sc.render.resolution_percentage=100;sc.view_settings.view_transform='AgX';sc.render.image_settings.file_format='PNG';sc.render.filepath=str(path);bpy.ops.render.render(write_still=True)
 for o in list(sc.objects):
  if o.name.startswith('PREVIEW_'):bpy.data.objects.remove(o,do_unlink=True)

if __name__=='__main__':
 out=ROOT/'tools/research_previews_v01';out.mkdir(exist_ok=True)
 specs=json.loads((ROOT/'picks_v01.json').read_text())
 specs += [dict(name=n,source=str(Path(r'C:\Dev\Game\ArtSource\Props\MAP_W86_v01\vehicles')/folder/(n+'_v01.blend'))) for n,folder in [('MW86_DumpTruck','dump_truck'),('MW86_MilTruck','mil_truck'),('MW86_TruckContainer','truck_container')]]
 stats=[]
 for p in specs:
  clean();obs=center(load(p['source'],True));lo,hi=bounds(obs)
  stats.append({'name':p['name'],'triangles':tris(obs),'dimensions':list(hi-lo)})
  render(out/(p['name']+'.png'),600,380)
 (out/'stats.json').write_text(json.dumps(stats,indent=2))

