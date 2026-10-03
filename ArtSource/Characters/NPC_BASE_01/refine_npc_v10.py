"""DRAFT (TASK-000052-000056): not a delivered revision; NPC_BASE_01_v10 is not saved in the
project yet and the emotion list awaits Vadim's decision.

v09 to v10: facial controls. Basis face = Satisfied (smug, after the
CharacterDirection reference); separate shape keys for each brow, the pupils,
the eyes and the graphic mouth line; emotion presets stored on the face mesh.
Head skin, nose and ears never move; the skeleton is untouched."""
import bpy,math,json,argparse,sys
from pathlib import Path
from mathutils import Vector,Matrix
from mathutils.bvhtree import BVHTree
sys.dont_write_bytecode=True
MOUTH_R=.122   # mouth strips sit 2 mm in front of the 0.12 m head cylinder

def parts(me):
    links=[[] for _ in me.vertices]
    for e in me.edges:
        a,b=e.vertices;links[a].append(b);links[b].append(a)
    mat={}
    for p in me.polygons:
        for v in p.vertices:mat[v]=me.materials[p.material_index].name
    left=set(range(len(links)));out={}
    while left:
        todo=[left.pop()];part=[]
        while todo:
            i=todo.pop();part.append(i)
            for j in links[i]:
                if j in left:left.remove(j);todo.append(j)
        cs=[me.vertices[i].co for i in part];x=sum(c.x for c in cs)/len(cs);side='L' if x>0 else 'R'
        ymin=min(c.y for c in cs);zmax=max(c.z for c in cs)
        if len(part)==20:name='mouth'
        elif len(part)==146:name='white_'+side
        elif len(part)==86:name='pupil_'+side
        elif mat[part[0]]=='Eyes_Ivory':name='glint_'+side
        elif ymin>-.06:name='lid_'+side
        else:name='brow_'+side
        out[name]=part
    return out

def on_cylinder(co,r):
    # keep the point on the front of a vertical cylinder of radius r
    return Vector((co.x,-math.sqrt(max(r*r-co.x*co.x,1e-9)),co.z))

class Face:
    def __init__(self,me):
        self.me=me;self.p=parts(me);self.base=[v.co.copy() for v in me.vertices]
    def center(self,name,co):
        ids=self.p[name];return sum((co[i] for i in ids),Vector())/len(ids)
    # --- eyes -------------------------------------------------------------
    def eye_surface(self,co,side):
        ids=self.p['white_'+side];idx={j:k for k,j in enumerate(ids)}
        polys=[[idx[v] for v in p.vertices] for p in self.me.polygons if p.vertices[0] in idx]
        return BVHTree.FromPolygons([co[i] for i in ids],polys)
    def place_pupil(self,co,side,shift=(0,0),scale=(1,1),src=None):
        """Move pupil+glint across the eye white: shift (dx,dz) of the pupil
        centre, scale its outline; keep each point's height above the white."""
        src=src or self.base;old=self.eye_surface(src,side);new=self.eye_surface(co,side)
        c=self.center('pupil_'+side,src)
        for name,s in [('pupil_'+side,scale),('glint_'+side,(min(scale[0],1)*.9+.1,min(scale[1],1)*.9+.1))]:
            gc=self.center(name,src)
            for i in self.p[name]:
                p=src[i];hit=old.ray_cast(Vector((p.x,-1,p.z)),Vector((0,1,0)))[0];lift=(hit.y-p.y) if hit else .001
                if name.startswith('glint'):
                    # the glint keeps its place on the pupil, scaled with it
                    x=c.x+(gc.x-c.x)*scale[0]+(p.x-gc.x)*s[0]+shift[0];z=c.z+(gc.z-c.z)*scale[1]+(p.z-gc.z)*s[1]+shift[1]
                else:
                    x=c.x+(p.x-c.x)*s[0]+shift[0];z=c.z+(p.z-c.z)*s[1]+shift[1]
                hit=new.ray_cast(Vector((x,-1,z)),Vector((0,1,0)))[0]
                co[i]=Vector((x,(hit.y if hit else p.y)-lift,z))
    def scale_eye(self,co,side,sx,sz,pivot_dz=0,src=None):
        src=src or self.base;c=self.center('white_'+side,src)
        for k in ['white_','pupil_','glint_']:
            for i in self.p[k+side]:
                p=src[i];co[i]=Vector((c.x+(p.x-c.x)*sx,p.y,c.z+pivot_dz+(p.z-c.z-pivot_dz)*sz))
    # --- brows ------------------------------------------------------------
    # The old brows were thin flat tubes in the plane y=-0.11: buried at the
    # inner end, floating 2-4 cm off the round head at the outer end. They are
    # rebuilt from their own 7 rings x 6 vertices as a bold rounded bar lying
    # on the skin, about as long as the eye (CharacterDirection reference).
    BROW=dict(cx=.054,z0=1.592,half=.037,arch=.003,rz=.0105,rd=.0055)
    def ring_layout(self):
        if hasattr(self,'rings'):return
        self.rings={}
        for side in 'LR':
            ids=sorted(self.p['brow_'+side]);groups=[ids[k:k+6] for k in range(0,len(ids),6)]
            groups.sort(key=lambda g:sum(abs(self.base[i].x) for i in g))
            for r,g in enumerate(groups):
                zc=sum(self.base[i].z for i in g)/6
                for i in g:self.rings[i]=(r,len(groups),math.atan2(-.11-self.base[i].y,self.base[i].z-zc))
    def brow(self,co,side,dz=0,angle=0):
        self.ring_layout();B=self.BROW;sg=1 if side=='L' else -1;th=math.radians(angle)*sg
        for i in self.p['brow_'+side]:
            r,n,a=self.rings[i];u=2*r/(n-1)-1
            rz=B['rz']*(1-.45*abs(u)**3)
            ox=sg*u*B['half'];oz=-B['arch']*u*u+rz*math.cos(a)
            x=ox*math.cos(th)-oz*math.sin(th);z=ox*math.sin(th)+oz*math.cos(th)
            co[i]=on_cylinder(Vector((sg*B['cx']+x,0,B['z0']+dz+z)),.1215+B['rd']*math.sin(a))
    # --- mouth ------------------------------------------------------------
    def mouth(self,co,hw=.033,arc=.0045,thick=.0026,tilt=0,smirk=0,open_up=0,open_down=0,wave=0,shift=0,z0=None):
        ids=self.p['mouth'];src=self.base
        xs=[src[i].x for i in ids];half=max(abs(x) for x in xs)
        import numpy as np
        A=np.array([[1,src[i].x,src[i].x**2] for i in ids]);k=np.linalg.lstsq(A,np.array([src[i].z for i in ids]),rcond=None)[0]
        z0=self.z0 if z0 is None else z0
        for i in ids:
            p=src[i];u=max(-1,min(1,p.x/half));side=0 if abs(abs(u)-1)<1e-3 else (1 if p.z>k[0]+k[1]*p.x+k[2]*p.x**2 else -1)
            zc=z0+arc*u*u+tilt*u+smirk*max(0,u)**2+wave*math.sin(3*math.pi*u)*(1-u*u)
            env=math.sqrt(max(0,1-u*u))
            z=zc+(thick/2+open_up)*env if side>0 else zc-(thick/2+open_down)*env if side<0 else zc
            co[i]=on_cylinder(Vector((shift+u*hw,0,z)),MOUTH_R)

def build(face_obj):
    me=face_obj.data;F=Face(me);kb=me.shape_keys.key_blocks
    F.z0=min(F.base[i].z for i in F.p['mouth'])+.0008
    # 1. Basis = Satisfied: rounder eyes, small round pupils looking at you,
    # short thick relaxed brows set apart, a small tight smug smile.
    sat=[c.copy() for c in F.base]
    for s,sg in [('L',1),('R',-1)]:
        F.scale_eye(sat,s,1,.86)
        F.place_pupil(sat,s,shift=(-sg*.004,.005),scale=(1.05,.78),src=[c for c in sat])
        F.ring_layout();F.brow(sat,s)
    F.base_raw=F.base;F.base=sat
    F.mouth(sat,hw=.04,arc=.005,thick=.0048,tilt=.0009)
    for name in [n for n in ['Happy','Worried','Surprised'] if n in kb]:face_obj.shape_key_remove(kb[name])
    for i,c in enumerate(sat):kb['Basis'].data[i].co=c;me.vertices[i].co=c
    F.base=[c.copy() for c in sat]
    # 2. Control keys, each relative to Satisfied.
    keys={}
    def key(name,fn):
        co=[c.copy() for c in F.base];fn(co);keys[name]=co
    for s,sg in [('L',1),('R',-1)]:
        key('Brow_%s_Up'%s,lambda co,s=s:F.brow(co,s,dz=.024))
        key('Brow_%s_Down'%s,lambda co,s=s:F.brow(co,s,dz=-.012))
        key('Brow_%s_Angry'%s,lambda co,s=s:F.brow(co,s,dz=-.007,angle=34))
        key('Brow_%s_Sad'%s,lambda co,s=s:F.brow(co,s,dz=.008,angle=-30))
        key('Eye_%s_Squint'%s,lambda co,s=s:F.scale_eye(co,s,1.04,.45,pivot_dz=-.012))
    key('Eyes_Wide',lambda co:[F.scale_eye(co,s,1.13,1.16) for s in 'LR'] and [F.place_pupil(co,s,src=None) for s in 'LR'])
    for name,(dx,dz) in {'Look_Left':(.012,0),'Look_Right':(-.012,0),'Look_Up':(0,.013),'Look_Down':(0,-.011)}.items():
        key(name,lambda co,dx=dx,dz=dz:[F.place_pupil(co,s,shift=(dx,dz),src=F.base) for s in 'LR'])
    key('Pupils_Small',lambda co:[F.place_pupil(co,s,scale=(.55,.55),src=F.base) for s in 'LR'])
    key('Pupils_Big',lambda co:[F.place_pupil(co,s,scale=(1.35,1.35),src=F.base) for s in 'LR'])
    key('Pupils_Cross',lambda co:[F.place_pupil(co,s,shift=(-sg*.012,-.003),src=F.base) for s,sg in [('L',1),('R',-1)]])
    key('Pupils_Apart',lambda co:[F.place_pupil(co,s,shift=(sg*.013,.002),src=F.base) for s,sg in [('L',1),('R',-1)]])
    mouths={'Mouth_Smile':dict(hw=0.040,arc=.009,thick=0.0052),'Mouth_Frown':dict(hw=0.034,arc=-.008,thick=0.0052),
            'Mouth_Flat':dict(hw=0.029,arc=0,thick=0.0046),'Mouth_Smirk_L':dict(hw=0.036,arc=.002,thick=0.0046,smirk=.007),
            'Mouth_Smirk_R':dict(hw=0.036,arc=.002,thick=0.0046,smirk=.007),'Mouth_O':dict(hw=0.010,arc=0,thick=0.0042,open_up=.005,open_down=.006),
            'Mouth_Open':dict(hw=0.027,arc=-.004,thick=0.0052,open_up=.006,open_down=.014),'Mouth_Wave':dict(hw=0.038,arc=0,thick=0.0048,wave=.0026),
            'Mouth_Side_L':dict(hw=0.029,arc=.002,thick=0.0046,shift=.013),'Mouth_Side_R':dict(hw=0.029,arc=.002,thick=0.0046,shift=-.013)}
    for name,kw in mouths.items():
        def fn(co,name=name,kw=kw):
            F.mouth(co,**kw)
            if name=='Mouth_Smirk_R':
                for i in F.p['mouth']:co[i]=Vector((co[i].x,co[i].y,co[i].z))
        key(name,fn)
    # Smirk_R mirrors Smirk_L across the face centre.
    l=keys['Mouth_Smirk_L'];ids=F.p['mouth']
    mirror={i:min(ids,key=lambda j:(F.base[j].x+F.base[i].x)**2+(F.base[j].z-F.base[i].z)**2) for i in ids}
    r=[c.copy() for c in F.base]
    for i in ids:m=l[mirror[i]];r[i]=Vector((-m.x,m.y,m.z))
    keys['Mouth_Smirk_R']=r
    for name,co in keys.items():
        k=face_obj.shape_key_add(name=name,from_mix=False)
        for i,c in enumerate(co):k.data[i].co=c
        k.slider_min=0;k.slider_max=1;k.value=0
    me.update();return list(keys)

EMOTIONS={
 # one emotion = one simple thought; values are shape-key weights over the Satisfied basis
 'Satisfied':{'_thought':'я красавчик'},
 'SuspiciousDumb':{'_thought':'а?..','Brow_L_Up':1,'Brow_R_Down':.5,'Eye_R_Squint':.55,'Pupils_Small':.35,'Mouth_O':.45,'Mouth_Side_R':.6},
 'ThinkingDumb':{'_thought':'ща… ща… почти понял','Look_Up':.9,'Look_Left':.7,'Brow_L_Up':.7,'Brow_R_Sad':.35,'Mouth_Side_L':.9,'Mouth_Flat':.5,'Mouth_Wave':.25},
 'Fear':{'_thought':'БЛЯТЬ','Eyes_Wide':1,'Pupils_Small':1,'Brow_L_Up':1,'Brow_R_Up':1,'Brow_L_Sad':.7,'Brow_R_Sad':.6,'Mouth_Wave':1},
 'FearYell':{'_thought':'ААА ПУСТИ (тащат, вырывается)','Eyes_Wide':1,'Pupils_Small':1,'Brow_L_Up':1,'Brow_R_Up':.9,'Brow_L_Sad':.7,'Brow_R_Sad':.8,'Mouth_Open':1,'_flap':'Mouth_Open 1 <-> Mouth_O 0.6, ~8 Hz, pupils dart'},
 'GaveUpShock':{'_thought':'…это реально происходит (сдался, в ахуе)','Eyes_Wide':1,'Pupils_Small':1,'Brow_L_Up':.75,'Brow_R_Up':.7,'Mouth_Flat':1,'Mouth_O':.2,'_live':'no blinks, no pupil movement'},
 'VanShock':{'_thought':'ПИЗДЕЦ, МЕНЯ ГРУЗЯТ','Eyes_Wide':1,'Look_Up':1,'Pupils_Small':.8,'Brow_L_Up':1,'Brow_R_Up':1,'Brow_L_Sad':.5,'Brow_R_Sad':.5,'Mouth_Frown':1,'Mouth_Open':.45},
 'Angry':{'_thought':'ЩАС ДАМ','Brow_L_Angry':1,'Brow_R_Angry':.75,'Brow_R_Down':.3,'Mouth_Flat':.6,'Mouth_Frown':.45,'Mouth_Smirk_R':.35,'Pupils_Small':.2},
 'Dazed':{'_thought':'…ой','Pupils_Cross':1,'Eye_L_Squint':.35,'Brow_L_Down':.4,'Brow_R_Sad':.6,'Mouth_Smirk_L':.6,'Mouth_O':.3},
 'Ouch':{'_thought':'АЙ','Blink':.8,'Brow_L_Sad':1,'Brow_R_Sad':1,'Mouth_Wave':.8,'Mouth_Open':.3},
 'Sleep':{'_thought':'хррр (усыпили)','Blink':1,'Brow_L_Down':.35,'Brow_R_Down':.35,'Mouth_Flat':.6,'Mouth_O':.25},
}

# --- extra Mixamo clips (GAME/Animations) -----------------------------------
import re,hashlib
from mathutils import Quaternion
CLIP_DIR=Path(__file__).resolve().parents[3]/'Animations'
FINGERS=('Index','Middle','Ring','Pinky');FINGER_CURL=.55

def clip_name(path):
    return re.sub(r'[^A-Za-z0-9]','',path.stem.title())+'_InPlace'

def head_lag(rig,action,start,end,hz=2.2,damping=.35,tip_z=1.62,max_deg=10):
    """Bake the soft-sausage spring of v09 onto Neck/Head for one looping clip."""
    scene=bpy.context.scene;rest=rig.data.bones['mixamorig:Spine2'].matrix_local
    tip0=rest.inverted()@Vector((0,0,tip_z));base0=rest.inverted()@Vector((0,0,1.21))
    frames=list(range(start,end+1));T={};B={}
    for f in frames:
        scene.frame_set(f);m=rig.pose.bones['mixamorig:Spine2'].matrix.copy();T[f]=m@tip0;B[f]=m@base0
    w=2*math.pi*hz;P=T[start].copy();V=Vector();sub=8;dt=1/30/sub;lag={}
    for loop in range(3):
        for f in frames:
            a,b=T[f],(T[f+1] if f<end else T[start]);vel=(b-a)*30
            for s in range(sub):
                acc=w*w*(a.lerp(b,s/sub)-P)+2*damping*w*(vel-V);V+=acc*dt;P+=V*dt
            if loop==2:lag[f]=P.copy()
    prev={};angles=[]
    for f in frames:
        scene.frame_set(f);q=(T[f]-B[f]).rotation_difference(lag[f]-B[f]);ang=min(q.angle,math.radians(max_deg))
        half=Quaternion(q.axis,ang/2) if ang>1e-9 else Quaternion();angles.append(math.degrees(ang))
        for name in ['Neck','Head']:
            pb=rig.pose.bones['mixamorig:'+name];pb.rotation_quaternion=Quaternion();bpy.context.view_layer.update()
            fr=pb.matrix.to_quaternion();local=fr.inverted()@half@fr
            if name in prev and local.dot(prev[name])<0:local.negate()
            prev[name]=local;pb.rotation_quaternion=local;bpy.context.view_layer.update()
            pb.keyframe_insert('rotation_quaternion',frame=f,group=pb.name)
    return {'mean_bend_deg':round(sum(angles)/len(angles),2),'max_bend_deg':round(max(angles),2)}

def retarget(rig,path,dz=0):
    scene=bpy.context.scene;existing=set(bpy.data.objects);acts=set(bpy.data.actions)
    bpy.ops.import_scene.fbx(filepath=str(path),ignore_leaf_bones=False,automatic_bone_orientation=False)
    imported=set(bpy.data.objects)-existing;src=next(o for o in imported if o.type=='ARMATURE')
    nm=lambda n:re.sub(r'^mixamorig\d*:','mixamorig:',n);sa=src.animation_data.action
    start,end=map(lambda x:int(round(x)),sa.frame_range)
    src_rest={nm(b.name):src.matrix_world@b.matrix_local for b in src.data.bones};motion={}
    for f in range(start,end+1):
        scene.frame_set(f);motion[f]={nm(pb.name):src.matrix_world@pb.matrix for pb in src.pose.bones}
    for o in imported:bpy.data.objects.remove(o,do_unlink=True)
    for ac in set(bpy.data.actions)-acts:bpy.data.actions.remove(ac)
    rest={b.name:rig.matrix_world@b.matrix_local for b in rig.data.bones};L='mixamorig:Left'
    scale=(rest[L+'UpLeg'].translation-rest[L+'Foot'].translation).length/(src_rest[L+'UpLeg'].translation-src_rest[L+'Foot'].translation).length
    action=bpy.data.actions.new(clip_name(path));action.use_fake_user=True;rig.animation_data.action=action
    prev={}
    for f in range(start,end+1):
        desired={}
        for pb in rig.pose.bones:
            n=pb.name;rot=(motion[f][n].to_quaternion()@src_rest[n].to_quaternion().inverted()@rest[n].to_quaternion()).normalized()
            if pb.parent:pos=desired[pb.parent.name]@rest[pb.parent.name].inverted()@rest[n].translation
            else:
                d=(motion[f][n].translation-src_rest[n].translation)*scale;pos=rest[n].translation+Vector((0,0,d.z+dz))
            m=rot.to_matrix().to_4x4();m.translation=pos;desired[n]=m
            kw={} if not pb.parent else {'parent_matrix':desired[pb.parent.name],'parent_matrix_local':rest[pb.parent.name]}
            basis=pb.bone.convert_local_to_pose(m,rest[n],invert=True,**kw);q=basis.to_quaternion()
            if any('Hand'+d in n for d in FINGERS):q=Quaternion().slerp(Quaternion((q.w,q.x,0,0)).normalized(),FINGER_CURL)
            if n in prev and prev[n].dot(q)<0:q.negate()
            prev[n]=q;pb.rotation_mode='QUATERNION';pb.rotation_quaternion=q
            pb.keyframe_insert('rotation_quaternion',frame=f-start+1,group=n)
            if not pb.parent:pb.location=basis.translation;pb.keyframe_insert('location',frame=f-start+1,group=n)
        bpy.context.view_layer.update()
    for layer in action.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                for fc in bag.fcurves:
                    for k in fc.keyframe_points:k.interpolation='LINEAR'
    return action,end-start+1,scale

def lowest_shoe(n):
    shoes=bpy.data.objects['Outfit_Shoes'];low=9
    for f in range(1,n+1,2):
        bpy.context.scene.frame_set(f);e=shoes.evaluated_get(bpy.context.evaluated_depsgraph_get())
        low=min(low,min((e.matrix_world@v.co).z for v in e.data.vertices))
    return low

def add_clips(rig):
    out={}
    for path in sorted(CLIP_DIR.glob('*.fbx')):
        action,n,scale=retarget(rig,path);dz=.008-lowest_shoe(n)
        bpy.data.actions.remove(action);action,n,scale=retarget(rig,path,dz)
        if action.slots:rig.animation_data.action_slot=next(s for s in action.slots if s.target_id_type=='OBJECT')
        lag=head_lag(rig,action,1,n)
        out[action.name]={'source':'Animations/'+path.name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'frames':[1,n],
                          'root':'in place, vertical bob kept','vertical_scale':round(scale,4),'ground_shift_m':round(dz,4),'head_lag':lag}
        print('CLIP',action.name,n,lag)
    return out

def main():
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--output-dir',type=Path,required=True);p.add_argument('--revision',type=int,default=10)
    a=p.parse_args(sys.argv[sys.argv.index('--')+1:]);a.source=a.source.resolve();a.output_dir=a.output_dir.resolve();stem=f'NPC_BASE_01_v{a.revision:02d}'
    files=[a.output_dir/(stem+ext) for ext in ['.blend','.fbx']]+[a.output_dir/f'validation_v{a.revision:02d}.json']
    assert not any(f.exists() for f in files),'Choose an unused revision/output directory.'
    a.output_dir.mkdir(parents=True,exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=str(a.source));bpy.context.preferences.filepaths.save_version=0
    scene=bpy.context.scene;scene.name=stem;scene['npc_asset_revision']=stem;rig=bpy.data.objects['NPC_Rig_Mixamo65']
    face=bpy.data.objects['Face_Expressions'];names=build(face)
    face['emotion_presets']=json.dumps(EMOTIONS,ensure_ascii=False)
    # Glossy cartoon eyes: wet whites and near-black pupils with a sharp highlight.
    for name,(rough,col) in {'Eyes_Ivory':(.12,None),'Face_Dark':(.5,(.012,.008,.006,1))}.items():
        sh=next(n for n in bpy.data.materials[name].node_tree.nodes if n.type=='BSDF_PRINCIPLED');sh.inputs['Roughness'].default_value=rough
        if col:sh.inputs['Base Color'].default_value=col;bpy.data.materials[name].diffuse_color=col
    clips=add_clips(rig)
    rig.animation_data.action=bpy.data.actions['RunLookBack_InPlace']
    rig.animation_data.action_slot=next(s for s in rig.animation_data.action.slots if s.target_id_type=='OBJECT')
    report=json.loads(a.source.with_name('validation_'+a.source.stem.rsplit('_',1)[1]+'.json').read_text(encoding='utf-8'))
    for k in ['skin_validation','animated_fbx_roundtrip','joint_refinement_validation','hidden_fold_check']:report.pop(k,None)
    report.update(revision=stem,source_model=a.source.name)
    report['actions']=report['actions']+list(clips);report['clip_frames']={**{n:[1,68] for n in ['RunLookBack_InPlace','RunLookBack_RootMotion']},**{k:v['frames'] for k,v in clips.items()}}
    report['v10_clips']=clips
    report['v10_face']={'basis':'Satisfied (smug) after CharacterDirection_2026-09-29 Default','shape_keys':['Blink']+names,
        'removed_keys':['Happy','Worried','Surprised'],'emotions':EMOTIONS,
        'rules':'head skin, nose and ears never deform; emotion = eyes, pupils, brows and a flat graphic mouth line'}
    bpy.ops.object.select_all(action='DESELECT');rig.select_set(True)
    meshes=[o for o in bpy.data.collections['NPC_BASE_01'].objects if o.type=='MESH']
    for o in meshes:o.select_set(True)
    bpy.context.view_layer.objects.active=rig
    bpy.ops.export_scene.fbx(filepath=str(files[1]),use_selection=True,object_types={'MESH','ARMATURE'},add_leaf_bones=False,use_armature_deform_only=False,bake_anim=True,bake_anim_use_all_actions=True,bake_anim_use_nla_strips=False,bake_anim_simplify_factor=0,axis_forward='-Z',axis_up='Y',apply_unit_scale=True,use_mesh_modifiers=False)
    scene.frame_set(20);bpy.ops.wm.save_as_mainfile(filepath=str(files[0]));files[2].write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
    print('V10_SAVED',stem,len(names)+1)
if __name__=='__main__':main()
