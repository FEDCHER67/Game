import sys
from pathlib import Path
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'PILOT_KIT_v01'))
import bpy, pilot_previews as pv
bpy.ops.wm.open_mainfile(filepath=str(HERE/'SK3-PILOT-001_v03.blend'))
source=bpy.data.objects['SM_LEAFLESS_TREE'];source.location=(0,0,0)
s=pv.studio('G18_Tree_v03',16);ob=bpy.data.objects.new('Tree_contact_review',source.data);s.collection.objects.link(ob)
for name,az,el in [('front',0,0),('back',180,0),('left',-90,0),('right',90,0),('top',0,89),('bottom',0,-89),('three_quarter',35,22)]:
    pv.frame(s,[ob],(420,600),az=az,el=el,pad=1.13)
    s.camera.data.ortho_scale*=1.6
    pv.render(s,HERE/'Previews/v03/contact_review_02'/('LEAFLESS_TREE_'+name+'.png'))
