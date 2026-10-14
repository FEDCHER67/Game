using System;
using System.Linq;
using UnityEngine;
using UnityEngine.Rendering;
using OnlyVolunteers.Map.Look;
using OnlyVolunteers.Map.Look.V3;
using Object=UnityEngine.Object;
namespace OnlyVolunteers.Map.Grass.Editor
{
    // Scoped reuse of v17's proven hard-surface rasteriser; no changes to its low grass layer.
    public sealed class GrassExclusion24
    {
        const float Fine=.5f;
        Vector3 origin;
        int width, height;
        float[] clearance;
        public string Summary;
        [Serializable] public sealed class Routes { public Route[] routes; }
        [Serializable] public sealed class Route { public string name; public float[] points; }
        public float Distance(float x,float z)
        {
            int ix=Mathf.FloorToInt(x-origin.x),iz=Mathf.FloorToInt(z-origin.z);
            return ix<0||iz<0||ix>=width||iz>=height ? 0 : clearance[iz*width+ix];
        }
        public static GrassExclusion24 Build(Terrain terrain)
        {
            var mask=new GrassExclusion24();mask.origin=terrain.transform.position;
            var size=terrain.terrainData.size;mask.width=Mathf.CeilToInt(size.x);mask.height=Mathf.CeilToInt(size.z);
            int fx=mask.width*2,fz=mask.height*2;var hard=new bool[fx*fz];long tris=0;
            foreach(var mf in Object.FindObjectsByType<MeshFilter>())
            {
                if(!mf.sharedMesh || !mf.gameObject.activeInHierarchy)continue;
                // The giant sea triangles extend below dry land. Its per-cell water test is authoritative.
                if(mf.name=="Sea")continue;
                bool surface=false;
                for(var t=mf.transform;t;t=t.parent)
                    if(t.name=="Roads"||t.name=="Water"||t.name=="RetainingWalls"||t.name.Contains("_big_")) {surface=true;break;}
                if(surface)tris+=Rasterise(mf,terrain,mask.origin,fx,fz,hard);
            }
            // Read actual relocated building footprints, including v19 infill.
            foreach(var b in Object.FindObjectsByType<MapBuildingInfo>())
            {
                if(b.Footprint==null||b.Footprint.Length<3)continue;
                var flat=b.Footprint.SelectMany(v=>new[]{v.x,v.y}).ToArray();
                Polygon(flat,mask.origin,fx,fz,hard);
            }
            var plan=MapLookBuilder.Load("v19");
            // Actual Roads meshes include the park cut-outs. Raw paving polygons overlap those
            // cut-outs and would wrongly erase every Downtown lawn if rasterised again.
            foreach(var yard in plan.yards)
                if(yard.ground!=null&&(yard.ground.Contains("pav")||yard.ground.Contains("asphalt")||yard.ground.Contains("concrete")))Polygon(yard.pts,mask.origin,fx,fz,hard);
            var routeAsset=UnityEditor.AssetDatabase.LoadAssetAtPath<TextAsset>(GrassPlacement24.Root+"/Editor/ApprovedVanCorridors24.json");
            if(!routeAsset)throw new InvalidOperationException("Approved van corridor data missing");
            var routes=JsonUtility.FromJson<Routes>(routeAsset.text).routes;
            foreach(var route in routes)for(int i=2;i<route.points.Length;i+=2)
                Corridor(new Vector2(route.points[i-2],route.points[i-1]),new Vector2(route.points[i],route.points[i+1]),2,mask.origin,fx,fz,hard);
            mask.clearance=new float[mask.width*mask.height];Array.Fill(mask.clearance,50);
            int blocked=0;
            for(int z=0;z<fz;z++)for(int x=0;x<fx;x++)if(hard[z*fx+x])
            {
                blocked++;
                for(int dz=-1;dz<=1;dz++)for(int dx=-1;dx<=1;dx++)
                {int xx=(x+dx)/2,zz=(z+dz)/2;if(xx>=0&&zz>=0&&xx<mask.width&&zz<mask.height)mask.clearance[zz*mask.width+xx]=0;}
            }
            mask.Chamfer();mask.Summary=$"{tris} surface triangles; {blocked} hard half-metre cells; footprint/paving/yard polygons; {routes.Length} approved van routes with 2m half-width; 1m distance grid";
            return mask;
        }
        static void Polygon(float[] poly,Vector3 origin,int fx,int fz,bool[] hard)
        {
            if(poly==null||poly.Length<6)return;
            float minX=float.PositiveInfinity,maxX=float.NegativeInfinity,minZ=minX,maxZ=maxX;
            for(int i=0;i<poly.Length;i+=2){minX=Mathf.Min(minX,poly[i]);maxX=Mathf.Max(maxX,poly[i]);minZ=Mathf.Min(minZ,poly[i+1]);maxZ=Mathf.Max(maxZ,poly[i+1]);}
            for(int z=Mathf.Max(0,Mathf.FloorToInt((minZ-origin.z)/Fine));z<=Mathf.Min(fz-1,Mathf.CeilToInt((maxZ-origin.z)/Fine));z++)
                for(int x=Mathf.Max(0,Mathf.FloorToInt((minX-origin.x)/Fine));x<=Mathf.Min(fx-1,Mathf.CeilToInt((maxX-origin.x)/Fine));x++)
                    if(LookGeom.Inside(poly,origin.x+(x+.5f)*Fine,origin.z+(z+.5f)*Fine))hard[z*fx+x]=true;
        }
        static void Corridor(Vector2 a,Vector2 b,float radius,Vector3 origin,int fx,int fz,bool[] hard)
        {
            var ab=b-a;float length=ab.sqrMagnitude;
            int x0=Mathf.Max(0,Mathf.FloorToInt((Mathf.Min(a.x,b.x)-radius-origin.x)/Fine));
            int x1=Mathf.Min(fx-1,Mathf.CeilToInt((Mathf.Max(a.x,b.x)+radius-origin.x)/Fine));
            int z0=Mathf.Max(0,Mathf.FloorToInt((Mathf.Min(a.y,b.y)-radius-origin.z)/Fine));
            int z1=Mathf.Min(fz-1,Mathf.CeilToInt((Mathf.Max(a.y,b.y)+radius-origin.z)/Fine));
            for(int z=z0;z<=z1;z++)for(int x=x0;x<=x1;x++)
            {
                var p=new Vector2(origin.x+(x+.5f)*Fine,origin.z+(z+.5f)*Fine);
                float t=length>1e-6f?Mathf.Clamp01(Vector2.Dot(p-a,ab)/length):0;
                if((p-a-ab*t).sqrMagnitude<=radius*radius)hard[z*fx+x]=true;
            }
        }
        void Chamfer()
        {
            for(int z=0;z<height;z++)for(int x=0;x<width;x++)
            {int i=z*width+x;float v=clearance[i];if(x>0)v=Mathf.Min(v,clearance[i-1]+1);if(z>0){v=Mathf.Min(v,clearance[i-width]+1);if(x>0)v=Mathf.Min(v,clearance[i-width-1]+1.414214f);if(x<width-1)v=Mathf.Min(v,clearance[i-width+1]+1.414214f);}clearance[i]=v;}
            for(int z=height-1;z>=0;z--)for(int x=width-1;x>=0;x--)
            {int i=z*width+x;float v=clearance[i];if(x<width-1)v=Mathf.Min(v,clearance[i+1]+1);if(z<height-1){v=Mathf.Min(v,clearance[i+width]+1);if(x>0)v=Mathf.Min(v,clearance[i+width-1]+1.414214f);if(x<width-1)v=Mathf.Min(v,clearance[i+width+1]+1.414214f);}clearance[i]=v;}
        }
        private static long Rasterise(MeshFilter mf, Terrain terrain, Vector3 origin, int fx, int fz, bool[] hard)
        {
            Matrix4x4 m = mf.transform.localToWorldMatrix;
            long count = 0;
            using (Mesh.MeshDataArray arr = Mesh.AcquireReadOnlyMeshData(mf.sharedMesh))
            {
                Mesh.MeshData md = arr[0];
                var verts = new Unity.Collections.NativeArray<Vector3>(md.vertexCount, Unity.Collections.Allocator.Temp);
                md.GetVertices(verts);
                var xz = new Vector2[verts.Length];
                var wy = new float[verts.Length];
                for (int i = 0; i < verts.Length; i++)
                {
                    Vector3 w = m.MultiplyPoint3x4(verts[i]);
                    xz[i] = new Vector2((w.x - origin.x) / Fine, (w.z - origin.z) / Fine);
                    wy[i] = w.y;
                }
                verts.Dispose();
                for (int s = 0; s < md.subMeshCount; s++)
                {
                    SubMeshDescriptor sd = md.GetSubMesh(s);
                    if (sd.topology != MeshTopology.Triangles) continue;
                    var idx = new Unity.Collections.NativeArray<int>(sd.indexCount, Unity.Collections.Allocator.Temp);
                    md.GetIndices(idx, s);
                    for (int t = 0; t + 2 < idx.Length; t += 3)
                    {
                        int a = idx[t], b = idx[t + 1], c = idx[t + 2];
                        Vector2 mid = (xz[a] + xz[b] + xz[c]) / 3f;
                        var centre = new Vector3(origin.x + mid.x * Fine, 0f, origin.z + mid.y * Fine);
                        float ground = terrain.SampleHeight(centre) + origin.y;
                        if (Mathf.Max(wy[a], Mathf.Max(wy[b], wy[c])) < ground - 0.4f) continue;
                        Triangle(xz[a], xz[b], xz[c], fx, fz, hard);
                        count++;
                    }
                    idx.Dispose();
                }
            }
            return count;
        }

        // Cell centres inside the triangle (grid units), either winding.
        private static void Triangle(Vector2 a, Vector2 b, Vector2 c, int fx, int fz, bool[] hard)
        {
            float area = (b.x - a.x) * (c.y - a.y) - (b.y - a.y) * (c.x - a.x);
            if (Mathf.Abs(area) < 1e-6f) return;
            int x0 = Mathf.Max(0, Mathf.FloorToInt(Mathf.Min(a.x, Mathf.Min(b.x, c.x)))), x1 = Mathf.Min(fx - 1, Mathf.CeilToInt(Mathf.Max(a.x, Mathf.Max(b.x, c.x))));
            int z0 = Mathf.Max(0, Mathf.FloorToInt(Mathf.Min(a.y, Mathf.Min(b.y, c.y)))), z1 = Mathf.Min(fz - 1, Mathf.CeilToInt(Mathf.Max(a.y, Mathf.Max(b.y, c.y))));
            float sgn = Mathf.Sign(area);
            for (int z = z0; z <= z1; z++)
                for (int x = x0; x <= x1; x++)
                {
                    float px = x + 0.5f, pz = z + 0.5f;
                    float e0 = ((b.x - a.x) * (pz - a.y) - (b.y - a.y) * (px - a.x)) * sgn;
                    float e1 = ((c.x - b.x) * (pz - b.y) - (c.y - b.y) * (px - b.x)) * sgn;
                    float e2 = ((a.x - c.x) * (pz - c.y) - (a.y - c.y) * (px - c.x)) * sgn;
                    if (e0 >= 0f && e1 >= 0f && e2 >= 0f) hard[z * fx + x] = true;
                }
        }

    }
}
