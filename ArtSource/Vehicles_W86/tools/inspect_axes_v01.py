import bpy
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.wm.obj_import(filepath=r'C:\Dev\Game\ArtSource\Vehicles_W86\SEDAN\source\NormalCar1.obj',forward_axis='NEGATIVE_Z',up_axis='Y');bpy.context.view_layer.update()
o=next(o for o in bpy.context.scene.objects if 'Cube.012' in o.name)
print('AXIS',list(o.dimensions),list(o.rotation_euler),list(o.data.vertices[0].co),list(o.matrix_world@o.data.vertices[0].co))
