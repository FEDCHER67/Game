"""Measured low-poly trailing caster module for the TABLE-ASTRA rig."""
import bpy
import math
from mathutils import Matrix, Vector

RADIUS = 0.105
TRAIL = 0.035
MOUNT_Z = 0.228

def rebuild_casters(root, geo_col, rig_col, frame_mat, rubber_mat):
    def box(obj):
        ps=[obj.matrix_world@v.co for v in obj.data.vertices]
        return [[min(p[i] for p in ps),max(p[i] for p in ps)] for i in range(3)]

    # Derive XY placement from the four source mounting footprints.
    anchors={}
    for suffix in ('Head_Left','Head_Right','Foot_Left','Foot_Right'):
        old=bpy.data.objects['GEO_Caster_Fork_'+suffix]
        b=box(old)
        anchors[suffix]=((b[0][0]+b[0][1])/2,(b[1][0]+b[1][1])/2,
                         0.2695314 if suffix.startswith('Head') else 0.2285155)
    for obj in list(bpy.data.objects):
        if obj.name.startswith(('GEO_Caster_Fork_','GEO_Wheel_','GEO_Caster_Socket_',
                                'RIG_CasterSteer_','RIG_WheelRoll_','RIG_WheelAxle_',
                                'RIG_WheelRadius_','RIG_GroundUp')):
            bpy.data.objects.remove(obj,do_unlink=True)

    def node(name,parent,location):
        o=bpy.data.objects.new(name,None)
        rig_col.objects.link(o)
        o.parent=parent
        o.matrix_parent_inverse=Matrix.Identity(4)
        o.location=location
        o.empty_display_type='PLAIN_AXES'
        o.empty_display_size=.025
        return o

    def mesh(name,verts,faces,parent,mat):
        data=bpy.data.meshes.new(name+'_Mesh')
        data.from_pydata(verts,[],faces)
        data.update()
        obj=bpy.data.objects.new(name,data)
        geo_col.objects.link(obj)
        obj.parent=parent
        obj.matrix_parent_inverse=Matrix.Identity(4)
        obj.data.materials.append(mat)
        return obj

    node('RIG_GroundUp',root,(0,0,.1))
    wheels={}; forks={}; report=[]
    for suffix,(x,y,leg_bottom) in anchors.items():
        caster=node('RIG_CasterSteer_'+suffix,root,(x,y,MOUNT_Z))
        roll=node('RIG_WheelRoll_'+suffix,caster,(0,-TRAIL,RADIUS-MOUNT_Z))
        roll['radius_m']=RADIUS
        roll['roll_axis']='local X; negative rotation travels local +Y'
        caster['trail_m']=TRAIL
        caster['steering_axis']='local Z'
        node('RIG_WheelAxle_'+suffix,roll,(.1,0,0))
        node('RIG_WheelRadius_'+suffix,roll,(0,0,-RADIUS))

        # One continuous closed U-shaped fork, extruded with a trailing slope.
        profile=[(-.046,.093),(-.034,.093),(-.034,.214),(.034,.214),
                 (.034,.093),(.046,.093),(.046,.228),(-.046,.228)]
        verts=[]
        for side in (-1,1):
            for px,pz in profile:
                ratio=max(0,min(1,(.214-pz)/(.214-RADIUS)))
                cy=-TRAIL*ratio
                verts.append((px,cy+side*.022,pz-MOUNT_Z))
        n=len(profile)
        faces=[tuple(reversed(range(n))),tuple(range(n,n*2))]
        faces.extend((i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n))
        fork=mesh('GEO_Caster_Fork_'+suffix,verts,faces,caster,frame_mat)
        forks[suffix]=fork

        # Rounded low-poly tire profile, identical on all four assemblies.
        rings=[(-.031,.045),(-.031,.097),(-.026,RADIUS),
               (.026,RADIUS),(.031,.097),(.031,.045)]
        sides=24
        verts=[(px,rad*math.sin(2*math.pi*j/sides),rad*math.cos(2*math.pi*j/sides))
               for px,rad in rings for j in range(sides)]
        faces=[]
        for i in range(len(rings)-1):
            for j in range(sides):
                k=(j+1)%sides
                faces.append((i*sides+j,i*sides+k,(i+1)*sides+k,(i+1)*sides+j))
        faces.append(tuple(reversed(range(sides))))
        faces.append(tuple((len(rings)-1)*sides+j for j in range(sides)))
        wheel=mesh('GEO_Wheel_'+suffix,verts,faces,roll,rubber_mat)
        wheel.data.materials.append(frame_mat)
        for face in wheel.data.polygons:
            face.use_smooth=face.index<5*sides
        wheel.data.polygons[-1].material_index=1
        wheel.data.polygons[-2].material_index=1
        wheels[suffix]=wheel

        # The fixed bearing socket seats between leg and swivelling fork crown.
        zlo=MOUNT_Z-.001
        zhi=leg_bottom+.008
        sides=12
        verts=[(x+.038*math.cos(2*math.pi*j/sides),
                y+.038*math.sin(2*math.pi*j/sides),z)
               for z in (zlo,zhi) for j in range(sides)]
        faces=[tuple(reversed(range(sides))),tuple(range(sides,2*sides))]
        faces.extend((j,(j+1)%sides,(j+1)%sides+sides,j+sides) for j in range(sides))
        mesh('GEO_Caster_Socket_'+suffix,verts,faces,root,frame_mat)
        report.append({'position':suffix,'caster':caster.name,'wheel':wheel.name,
            'roll_pivot':roll.name,'radius_m':RADIUS,'trail_m':TRAIL,
            'mount_world_m':[x,y,MOUNT_Z],'axle_local_m':[0,-TRAIL,RADIUS-MOUNT_Z],
            'fork_tire_clearance_m':.004,'fork_tire_side_clearance_m':.003,
            'socket_leg_overlap_m':.008,'socket_fork_overlap_m':.001})

    bpy.context.view_layer.update()
    # Recalculate normals for the complete named modules.
    bpy.ops.object.select_all(action='DESELECT')
    for o in list(wheels.values())+list(forks.values()):
        o.select_set(True)
    bpy.context.view_layer.objects.active=next(iter(wheels.values()))
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode='OBJECT')
    return forks,wheels,report
