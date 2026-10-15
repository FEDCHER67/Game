import bpy,bmesh,math
from mathutils import Vector,Matrix
def mesh_obj(n,vs,fs,col=GEO,material=None):
 me=bpy.data.meshes.new(n+'_Mesh'); me.from_pydata(vs,[],fs); me.update(); o=bpy.data.objects.new(n,me); col.objects.link(o)
 if material: me.materials.append(material)
 bm=bmesh.new(); bm.from_mesh(me); bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces)); bm.to_mesh(me); bm.free()
 return o
def empty(n,p,col=GEO):
 o=bpy.data.objects.new(n,None); col.objects.link(o); o.location=p; o.empty_display_size=.035; return o
def parent(o,p):
 mw=o.matrix_world.copy(); o.parent=p; o.matrix_world=mw
def move_to(o,col):
 for c in list(o.users_collection): c.objects.unlink(o)
 col.objects.link(o)
def cube(n,p,size,material,bevel=0,col=GEO):
 bpy.ops.mesh.primitive_cube_add(size=1,location=p); o=bpy.context.object; o.name=n; move_to(o,col); o.scale=size
 bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
 o.data.materials.append(material)
 if bevel:
  mod=o.modifiers.new('Soft manufactured edge','BEVEL'); mod.width=bevel; mod.segments=1
  o.modifiers.new('Corner normals','WEIGHTED_NORMAL')
 return o
def cylinder(n,p,rad,depth,material,col=GEO):
 bpy.ops.mesh.primitive_cylinder_add(vertices=8,radius=rad,depth=depth,location=p)
 o=bpy.context.object; o.name=n; move_to(o,col); o.data.materials.append(material); return o
def line(n,pts,rad,material,col=GEO):
 cu=bpy.data.curves.new(n+'_Curve','CURVE'); cu.dimensions='3D'; cu.resolution_u=1; cu.bevel_depth=rad; cu.bevel_resolution=0; cu.resolution_u=1
 sp=cu.splines.new('POLY'); sp.points.add(len(pts)-1)
 for q,p in zip(sp.points,pts): q.co=(*p,1)
 o=bpy.data.objects.new(n,cu); col.objects.link(o); cu.materials.append(material); return o
def camera(n,p,target,ortho):
 d=bpy.data.cameras.new(n); d.type='ORTHO'; d.ortho_scale=ortho; o=bpy.data.objects.new(n,d); STAGE.objects.link(o); o.location=p; o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler(); return o
def light(n,p,power,size):
 d=bpy.data.lights.new(n,'AREA'); d.energy=power; d.shape='DISK'; d.size=size; o=bpy.data.objects.new(n,d); STAGE.objects.link(o); o.location=p; o.rotation_euler=(Vector((0,0,.7))-o.location).to_track_quat('-Z','Y').to_euler()
def band(n,pts,width,thick,material):
 vs=[]
 for i,p in enumerate(pts):
  tangent=Vector(pts[min(i+1,len(pts)-1)])-Vector(pts[max(0,i-1)])
  norm=Vector((-tangent.z,0,tangent.x)).normalized()
  if norm.z<0: norm=-norm
  for sy,sn in [(-1,-1),(1,-1),(1,1),(-1,1)]: vs.append(Vector(p)+Vector((0,sy*width/2,0))+sn*thick/2*norm)
 fs=[(3,2,1,0)]
 for i in range(len(pts)-1):
  for j in range(4): fs.append((i*4+j,i*4+(j+1)%4,(i+1)*4+(j+1)%4,(i+1)*4+j))
 fs.append(tuple((len(pts)-1)*4+j for j in range(4)))
 return mesh_obj(n,vs,fs,material=material)
def buckle(n,p,width,root):
 # Open rectangular steel frame, dark latch tongue and a pale release tab.
 x,y,z=p; length=.048; bw=width+.014; rod=.009
 bv=[]
 for zz in [z-.006,z+.006]:
  for sx,sy in [(length/2+rod/2,bw/2+rod/2),(length/2-rod/2,bw/2-rod/2)]:
   bv.extend([(x-sx,y-sy,zz),(x+sx,y-sy,zz),(x+sx,y+sy,zz),(x-sx,y+sy,zz)])
 bf=[]
 for j in range(4):
  k=(j+1)%4
  bf.extend([(j,k,8+k,8+j),(4+j,12+j,12+k,4+k),(j,4+j,4+k,k),(8+j,8+k,12+k,12+j)])
 o=mesh_obj(n+'_BUCKLE_FRAME',bv,bf,material=steel); parent(o,root)
 o=cube(n+'_BUCKLE_TONGUE',(x,y,z+.004),(length*.62,.012,.010),frame,0); parent(o,root)
 o=cube(n+'_RELEASE_TAB',(x+length*.24,y,z+.015),(.022,width*.62,.01),oat,.003); parent(o,root)
