import bpy,sys,json,numpy as np
from pathlib import Path
from mathutils import Vector
sys.path.insert(0,r'C:\Dev\Game\ArtSource\Vehicles_W86\tools');import blender_runner_v01 as R
root=R.ROOT;specs=json.loads((root/'selected_models_v01.json').read_text());W,H=360,240;canvas=np.zeros((len(specs)*H,8*W,4),dtype=np.float32);canvas[:,:,3]=1
for row,p in enumerate(specs):
 R.clean();bpy.ops.wm.open_mainfile(filepath=str(Path(p['folder'])/(p['name']+f"_v{p['revision']:02}.blend")))
 obs=sorted([o for o in bpy.context.scene.objects if '_LOD' in o.name],key=lambda o:o.name);sc=bpy.context.scene
 for o in list(sc.objects):
  if o.type!='MESH':bpy.data.objects.remove(o,do_unlink=True)
 for o in sc.objects:o.hide_render=True;o.hide_set(False)
 lo,hi=R.bounds([obs[0]]);target=(hi+lo)/2
 sc.render.engine='BLENDER_WORKBENCH';sc.display.shading.light='STUDIO';sc.display.shading.color_type='SINGLE';sc.display.shading.single_color=(.55,.58,.62);sc.display.shading.show_shadows=True;sc.display.shading.show_cavity=True;sc.display.shading.cavity_type='BOTH';sc.display.shading.background_type='WORLD'
 sc.world=bpy.data.worlds.new('TechnicalWorld');sc.world.color=(.09,.11,.13)
 sc.render.resolution_x=W;sc.render.resolution_y=H;sc.render.resolution_percentage=100;sc.render.image_settings.file_format='PNG';sc.view_settings.view_transform='Standard'
 bpy.ops.object.camera_add();cam=bpy.context.object;cam.data.type='ORTHO';sc.camera=cam
 poses=[(0,-1,0),(0,1,0),(1,0,0),(-1,0,0),(0,0,1),(0,0,-1),(8,-11,7),(8,-11,7)]
 for col,pose in enumerate(poses):
  lev=0 if col<6 else col-5
  for i,o in enumerate(obs):o.hide_render=i!=lev
  cam.location=target+Vector(pose).normalized()*30;R.aim(cam,target);bpy.context.view_layer.update();inv=cam.matrix_world.inverted();pts=[inv@Vector((x,y,z)) for x in (lo.x,hi.x) for y in (lo.y,hi.y) for z in (lo.z,hi.z)];sp=[max(v[i] for v in pts)-min(v[i] for v in pts) for i in (0,1)];cam.data.ortho_scale=max(sp[0],sp[1]*W/H)*1.2
  scratch=root/'tools/technical_cell_tmp.png';sc.render.filepath=str(scratch);bpy.ops.render.render(write_still=True);im=bpy.data.images.load(str(scratch),check_existing=False);arr=np.array(im.pixels[:],dtype=np.float32).reshape(H,W,4);canvas[(len(specs)-1-row)*H:(len(specs)-row)*H,col*W:(col+1)*W]=arr;bpy.data.images.remove(im)
final=bpy.data.images.new('Technical_views_raw',width=W*8,height=H*len(specs),alpha=True);final.pixels.foreach_set(canvas.ravel());final.filepath_raw=str(root/'tools/technical_views_raw_v03.png');final.file_format='PNG';final.save()
