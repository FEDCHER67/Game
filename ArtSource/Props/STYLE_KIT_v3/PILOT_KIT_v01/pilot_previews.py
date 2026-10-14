"""Studio previews; display geometry is never exported as a module."""
import sys, math, json
from pathlib import Path
sys.dont_write_bytecode=True
sys.path.insert(0,str(Path(__file__).resolve().parent))
import bpy
from mathutils import Vector
from pilot_geometry import Mesh, sk, SPECS
HERE=Path(__file__).resolve().parent

def plain_mat(name,rgb):
    m=bpy.data.materials.new(name); m.diffuse_color=(*rgb,1); m.use_nodes=True
    b=m.node_tree.nodes.get('Principled BSDF'); b.inputs['Base Color'].default_value=(*rgb,1); b.inputs['Roughness'].default_value=.92
    return m

def studio(name,samples):
    s=bpy.data.scenes.new(name); bpy.context.window.scene=s
    s.unit_settings.system='METRIC'; s.unit_settings.scale_length=1
    s.render.engine='CYCLES'; s.cycles.samples=samples; s.cycles.use_denoising=True
    s.cycles.max_bounces=4; s.cycles.diffuse_bounces=2; s.cycles.glossy_bounces=2
    # A fixed, quiet warm-sun studio. Standard view avoids a second saturation grade.
    s.view_settings.view_transform='Standard'; s.view_settings.look='None'; s.view_settings.exposure=0
    s.world=bpy.data.worlds.new(name+'_World'); s.world.use_nodes=True
    nt=s.world.node_tree; bg=nt.nodes.get('Background'); bg.inputs['Color'].default_value=(.34,.38,.43,1); bg.inputs['Strength'].default_value=.60
    sun=bpy.data.lights.new(name+'_Sun','SUN'); sun.energy=2.1; sun.angle=.12; sun.color=(1,.90,.78)
    so=bpy.data.objects.new(name+'_Sun',sun); s.collection.objects.link(so); so.rotation_euler=(.45,-.55,-.65)
    ca=bpy.data.cameras.new(name+'_Camera'); cam=bpy.data.objects.new(name+'_Camera',ca); s.collection.objects.link(cam); s.camera=cam; ca.type='ORTHO'
    s.render.image_settings.file_format='PNG'; s.render.image_settings.color_mode='RGB'
    s.render.resolution_percentage=100; s.render.film_transparent=False
    return s

def cube(s,name,size,at,mat):
    m=Mesh(); m.B(size,(0,0,0),kind=None)
    me=bpy.data.meshes.new(name); me.from_pydata(m.verts,[],m.faces); me.materials.append(mat)
    o=bpy.data.objects.new(name,me); s.collection.objects.link(o); o.location=at
    return o

def text(s,label,at,size=.20):
    cu=bpy.data.curves.new('Label_'+label,'FONT'); cu.body=label; cu.size=size; cu.align_x='CENTER'; cu.extrude=0
    ob=bpy.data.objects.new('Label_'+label,cu); s.collection.objects.link(ob); ob.location=at
    ob.rotation_euler=(math.pi/2,0,0)
    mat=bpy.data.materials.get('Preview_Ink') or plain_mat('Preview_Ink',(.07,.09,.10)); cu.materials.append(mat)
    return ob

def frame(s,objects,res,az=30,el=30,pad=1.16):
    bpy.context.view_layer.update()
    pts=[o.matrix_world@Vector(v) for o in objects for v in o.bound_box]
    mn=Vector([min(p[i] for p in pts) for i in range(3)]); mx=Vector([max(p[i] for p in pts) for i in range(3)])
    target=(mn+mx)/2
    a,e=math.radians(az),math.radians(el); direction=Vector((math.sin(a)*math.cos(e),-math.cos(a)*math.cos(e),math.sin(e)))
    cam=s.camera; cam.location=target+direction*50; cam.rotation_euler=(-direction).to_track_quat('-Z','Y').to_euler()
    inv=cam.rotation_euler.to_matrix().transposed()
    projected=[inv@(p-target) for p in pts]
    ranges=[max(p[i] for p in projected)-min(p[i] for p in projected) for i in (0,1)]
    offset=Vector([(max(p[i] for p in projected)+min(p[i] for p in projected))/2 for i in (0,1)]+[0])
    cam.location+=cam.rotation_euler.to_matrix()@offset
    cam.data.ortho_scale=max(ranges[0],ranges[1]*res[0]/res[1])*pad
    s.render.resolution_x,s.render.resolution_y=res

def render(s,path):
    if path.exists(): return
    path.parent.mkdir(parents=True,exist_ok=True); s.render.filepath=str(path)
    bpy.ops.render.render(write_still=True,scene=s.name)
    print('PREVIEW_SAVED',path,flush=True)

def render_sets(objects,root,samples,tiles=True):
    floor=plain_mat('Preview_Ground',(.24,.26,.25)); slab=plain_mat('Preview_Plinth',(.34,.36,.34))
    records={}
    for group,title in [('A','Hamlet props'),('B','Rural house detail'),('C','Plots and yards'),('D','Rough District')]:
        path=root/f'0{ord(group)-63}_{group}_three_quarter.png'
        if path.exists(): continue
        s=studio('G16_'+group,samples); displayed=[]
        names=[n for n,v in SPECS.items() if v['group']==group]
        names.sort(key=lambda n:max(v.co.z for v in objects[n].data.vertices)-min(v.co.z for v in objects[n].data.vertices))
        for i,name in enumerate(names):
            src=objects[name]; ob=bpy.data.objects.new('Preview_'+name,src.data); s.collection.objects.link(ob)
            # Consistent metre scale within each group, stepped rows for visibility.
            col=i%3; row=i//3; ob.location=((col-1)*7,row*6,0)
            displayed.append(ob)
            # Basement remains fully visible on a cutaway plinth above the studio floor.
            mnz=min(v.co.z for v in ob.data.vertices)
            if mnz<-.01: ob.location.z=-mnz
            label=text(s,name.replace('_',' '),(ob.location.x,ob.location.y-2.8,.10),.19)
            displayed.append(label)
        scale=cube(s,'1_75m_scale_box',(.50,.32,1.75),(10,0,.875),plain_mat('Scale_Warm',(.35,.29,.20)))
        displayed.append(scale); displayed.append(text(s,'1.75 m',(10,-.25,1.95),.22))
        ground=cube(s,'studio_floor',(200,200,.12),(0,0,-.12),floor)
        frame(s,displayed,(1280,1000),az=23,el=34,pad=1.12)
        render(s,path)
        records[group]=dict(scene=s.name,path=str(path.relative_to(HERE)),camera=list(s.camera.location),rotation=list(s.camera.rotation_euler),scale=s.camera.data.ortho_scale)
    if tiles:
        for name,src in objects.items():
            path=root/'Tiles'/f'{name}_three_quarter.png'
            if path.exists(): continue
            s=studio('Tile_'+name,max(12,samples//2)); ob=bpy.data.objects.new('Tile_'+name,src.data); s.collection.objects.link(ob)
            mnz=min(v.co.z for v in ob.data.vertices)
            cube(s,'tile_floor',(50,50,.10),(0,0,mnz-.051),floor)
            frame(s,[ob],(320,260),az=32 if name!='TRACTOR_BROKEN' else 145,el=27,pad=1.18)
            render(s,path)
    return records

def previews(rev,samples=32):
    bpy.ops.wm.open_mainfile(filepath=str(HERE/f'SK3-PILOT-001_{rev}.blend'))
    objects={name:bpy.data.objects['SM_'+name] for name in SPECS}
    root=HERE/'Previews'/rev
    records=render_sets(objects,root,samples,True)
    from build_pilot_kit import ensure_new,write_json
    demo=HERE/f'SK3-PILOT-001_Previews_{rev}.blend'
    if not demo.exists(): bpy.ops.wm.save_as_mainfile(filepath=str(demo))
    path=HERE/f'preview_cameras_{rev}.json'
    if not path.exists(): write_json(path,records)

if __name__=='__main__':
    from build_pilot_kit import build
    objects,_,_,_=build('v01')
    render_sets(objects,HERE/'Review'/ 'check02',16,False)
