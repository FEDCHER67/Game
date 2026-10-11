import bpy,json,math
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=r'C:\Dev\Game\Working\Tripo\pan_tripo_base.fbx')
o=next(o for o in bpy.context.scene.objects if o.type=='MESH');bpy.context.view_layer.objects.active=o;bpy.ops.object.transform_apply(location=False,rotation=True,scale=True)
rows=[]
for v in o.data.vertices:
 x,y,z=v.co;r=math.hypot(x,z-.305)
 if r>.23 and z<.60 and (abs(x)<.03 or abs(z-.305)<.02):rows.append({'v':v.index,'co':list(v.co),'r':r})
print('CUP',json.dumps(rows))
