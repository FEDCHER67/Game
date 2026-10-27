import bpy,math
from pathlib import Path
from mathutils import Vector
ROOT=Path(r'C:\Dev\Game\Working\Reviews\W86Polish_2026-10-25\G45')
bpy.ops.wm.read_factory_settings(use_empty=True);scene=bpy.context.scene
for filename,name,x in [(r'C:\Dev\Game\ArtSource\Dev\Trees_staging\v03\Forest_FrondTrees_v03_04.blend','SM_Forest_Spruce_A_v03_04_LOD0',-4),(r'C:\Dev\Game\ArtSource\Dev\Trees_staging\forest_v04_03\Forest_Conifers_v04_03.blend','SM_Forest_Spruce_A_v04_03_LOD0',4)]:
 with bpy.data.libraries.load(filename,link=False) as (a,b):b.objects=[n for n in a.objects if n==name]
 for ob in b.objects:scene.collection.objects.link(ob);ob.hide_render=False;ob.hide_set(False);ob.location=(x,0,0)
camd=bpy.data.cameras.new('G45_QA');cam=bpy.data.objects.new('G45_QA',camd);scene.collection.objects.link(cam);scene.camera=cam;camd.type='ORTHO';camd.ortho_scale=17
scene.render.engine='BLENDER_WORKBENCH';scene.display.shading.light='STUDIO';scene.display.shading.color_type='MATERIAL';scene.display.shading.show_shadows=True;scene.display.shading.show_cavity=True;scene.display.shading.background_type='WORLD'
scene.world=bpy.data.worlds.new('G45_solid_final_world');scene.world.color=(.22,.25,.26);scene.render.resolution_x=1600;scene.render.resolution_y=1000;scene.render.resolution_percentage=100
for tag,p,target in [('front',(0,-40,4.5),(0,0,4.5)),('back',(0,40,4.5),(0,0,4.5)),('left',(-35,-20,8),(0,0,4.5)),('right',(35,-20,8),(0,0,4.5)),('top',(0,0,40),(0,0,0)),('bottom',(0,0,-40),(0,0,4.5))]:
 cam.location=p;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler();scene.render.filepath=str(ROOT/('spruce_old_new_solid_final_'+tag+'_v01.png'));bpy.ops.render.render(write_still=True)
print('G45_SOLID_QA_COMPLETE')
