"""Geometry measurements in metres. No scene writes, no external dependencies."""
import math
import numpy as np
from mathutils import Vector,Matrix
from mathutils.bvhtree import BVHTree

class Mesh:
    def __init__(self,ob,transform=None):
        mw=ob.matrix_world if transform is None else transform@ob.matrix_world
        self.name=ob.name
        self.v=np.array([list(mw@v.co) for v in ob.data.vertices],dtype=np.float64)
        ob.data.calc_loop_triangles()
        self.t=np.array([list(t.vertices) for t in ob.data.loop_triangles],dtype=int)
        self.e=np.array(sorted({tuple(sorted((f[i],f[(i+1)%3]))) for f in self.t for i in range(3)}),dtype=int)
        self.bvh=BVHTree.FromPolygons(self.v.tolist(),self.t.tolist(),all_triangles=True)
        self.lo=self.v.min(axis=0);self.hi=self.v.max(axis=0)
        self.elo=np.minimum(self.v[self.e[:,0]],self.v[self.e[:,1]])
        self.ehi=np.maximum(self.v[self.e[:,0]],self.v[self.e[:,1]])

def segment_distances(a,b,c,d):
    """Exact closest distances: segment a-b against arrays of segments c-d."""
    u=b-a;v=d-c;w=a-c
    aa=np.dot(u,u);ee=np.einsum('ij,ij->i',v,v)
    bb=v@u;cc=w@u;ff=np.einsum('ij,ij->i',v,w)
    den=aa*ee-bb*bb
    s=np.zeros(len(c));good=den>1e-25
    s[good]=np.clip((bb[good]*ff[good]-cc[good]*ee[good])/den[good],0,1)
    t=(bb*s+ff)/np.maximum(ee,1e-25)
    low=t<0;high=t>1
    s[low]=np.clip(-cc[low]/max(aa,1e-25),0,1)
    s[high]=np.clip((bb[high]-cc[high])/max(aa,1e-25),0,1)
    t=np.clip(t,0,1)
    delta=a+s[:,None]*u-c-t[:,None]*v
    return np.einsum('ij,ij->i',delta,delta)

def distance(a,b,upper=math.inf):
    """Surface minimum including triangle crossings, vertex-face, edge-edge.
    AABB pruning has a conservative Euclidean lower bound, not a sample proxy.
    """
    sep=np.maximum(np.maximum(a.lo-b.hi,b.lo-a.hi),0)
    if np.linalg.norm(sep)>upper:return float(np.linalg.norm(sep)),False
    if a.bvh.overlap(b.bvh):return 0.0,True
    best=min(b.bvh.find_nearest(Vector(p))[3] for p in a.v)
    # Opposite vertex-to-face minima (including face interiors).
    lower=np.linalg.norm(np.maximum(np.maximum(a.lo-b.v,b.v-a.hi),0),axis=1)
    for p in b.v[lower<best]:best=min(best,a.bvh.find_nearest(Vector(p))[3])
    best2=best*best
    for i,j in a.e:
        p,q=a.v[i],a.v[j];lo=np.minimum(p,q);hi=np.maximum(p,q)
        sep=np.maximum(np.maximum(lo-b.ehi,b.elo-hi),0)
        mask=np.einsum('ij,ij->i',sep,sep)<best2
        if mask.any():
            edges=b.e[mask];ds=segment_distances(p,q,b.v[edges[:,0]],b.v[edges[:,1]])
            best2=min(best2,float(ds.min()))
    return math.sqrt(best2),False

def inside(mesh,p):
    origin=Vector(p);votes=[]
    for direction in ((.12137,.07319,1),(1,.19317,.06713),(.13771,1,.09137)):
        ray=Vector(direction).normalized();point=origin.copy();hits=0
        for _ in range(128):
            # 10 micrometres exceeds float32 world-coordinate ray noise and
            # prevents counting the same face repeatedly near Z=1.1 m.
            hit=mesh.bvh.ray_cast(point+ray*1e-5,ray)
            if hit[0] is None:break
            hits+=1;point=hit[0]
        votes.append(hits%2==1)
        if len(votes)==2 and votes[0]==votes[1]:return votes[0]
    return sum(votes)>=2

def mesh_health(ob):
    m=Mesh(ob);m.v=np.array([v.co[:] for v in ob.data.vertices],dtype=np.float64)
    norms=[];max_violation=0.0;min_area=math.inf
    for f in m.t:
        a,b,c=m.v[f];n=np.cross(b-a,c-a);area=np.linalg.norm(n);min_area=min(min_area,area/2)
        if area>1e-20:max_violation=max(max_violation,float(np.max((m.v-a)@(n/area))))
    edge_count={}
    for f in m.t:
        for i in range(3):
            key=tuple(sorted((int(f[i]),int(f[(i+1)%3]))));edge_count[key]=edge_count.get(key,0)+1
    adjacency=[set() for _ in m.v]
    for a,b in m.e:adjacency[a].add(int(b));adjacency[b].add(int(a))
    seen=set();components=0
    for start in range(len(m.v)):
        if start in seen:continue
        components+=1;queue=[start];seen.add(start)
        while queue:
            a=queue.pop()
            for b in adjacency[a]:
                if b not in seen:seen.add(b);queue.append(b)
    return {'vertices':len(m.v),'triangles':len(m.t),'components':components,'all_faces_triangles':all(len(p.vertices)==3 for p in ob.data.polygons),
            'nonmanifold_edges':sum(v!=2 for v in edge_count.values()),'minimum_triangle_area_m2':min_area,
            'convex':max_violation<=.000005,'max_convex_plane_violation_mm':max_violation*1000,
            'local_scale':list(ob.scale),'local_rotation':list(ob.rotation_euler),
            'local_translation':list(ob.location),'parent':ob.parent.name if ob.parent else None}

def combined(meshes):
    verts=[];faces=[];owners=[]
    for m in meshes:
        off=len(verts);verts+=m.v.tolist();faces.extend((m.t+off).tolist());owners.extend([m.name]*len(m.t))
    return BVHTree.FromPolygons(verts,faces,all_triangles=True),owners

def sweep(bvh,owners,origin,direction,length,radius=.004):
    """Conservative continuous sphere advancement, <=0.001 mm contact tolerance.
    Nearest-surface distance is 1-Lipschitz, so each advance cannot skip a hit.
    """
    origin=Vector(origin);direction=Vector(direction).normalized();t=0.0
    for step in range(5000):
        p=origin+direction*t;q,n,index,d=bvh.find_nearest(p)
        gap=d-radius
        if gap<=1e-6:return {'first_hit':owners[index],'travel_m':t,'contact_m':list(q),'steps':step+1}
        advance=max(1e-7,gap*.95)
        if t+advance>length:return {'first_hit':None,'travel_m':None,'steps':step+1}
        t+=advance
    return {'first_hit':None,'status':'INCONCLUSIVE_MAX_STEPS','travel_m':None,'steps':5000}

def surface_samples(mesh,spacing=.001):
    """Barycentric grid; every triangle point lies within spacing of a sample."""
    for f in mesh.t:
        a,b,c=mesh.v[f]
        count=max(1,math.ceil(max(np.linalg.norm(b-a),np.linalg.norm(c-a),np.linalg.norm(c-b))/spacing))
        for i in range(count+1):
            for j in range(count+1-i):yield a+(b-a)*(i/count)+(c-a)*(j/count)
