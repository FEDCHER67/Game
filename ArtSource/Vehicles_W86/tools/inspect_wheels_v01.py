import bpy
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.wm.obj_import(filepath=r'C:\Dev\Game\ArtSource\Vehicles_W86\BOX_TRUCK\source\truck.obj',use_split_groups=True)
for o in bpy.context.scene.objects:
 print(o.name,list(o.dimensions),sum(len(p.vertices)-2 for p in o.data.polygons))
