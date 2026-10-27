using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using OnlyVolunteers.Map.Crowd;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.SceneManagement;
using Object = UnityEngine.Object;

namespace OnlyVolunteers.Map.W85
{
    // G46: explicit road surface profiles and reviewed raster artifacts. No layout regeneration.
    // Called both by the builder and by the partial repair menu. Profile values are absolute surface Y.
    public static class W86RoadRepair
    {
        static string Data => Application.dataPath + "/OnlyVolunteers/Map/W85Build/Data/v02/road_repairs_v01.json";
        static string Review => System.IO.Path.GetFullPath(Application.dataPath + "/../Working/Reviews/W86Polish_2026-10-25/G46");
        public sealed class Route
        {
            public string Id, Group, Kind;
            public float Width, Clearance;
            public Vector2[] Points;
            public float[] Y;
            public float Length;
            public Vector3 At(float s)
            {
                for (int i = 1; i < Points.Length; i++)
                {
                    float l = Vector2.Distance(Points[i - 1], Points[i]);
                    if (s <= l || i == Points.Length - 1)
                    { float t = Mathf.Clamp01(s / Mathf.Max(.001f, l)); var p = Vector2.Lerp(Points[i - 1], Points[i], t); return new Vector3(p.x, Mathf.Lerp(Y[i - 1], Y[i], t), p.y); }
                    s -= l;
                }
                return Vector3.zero;
            }
            public float Surface(Vector2 p)
            {
                float best = float.MaxValue, y = Y[0];
                for (int i = 1; i < Points.Length; i++)
                {
                    var a = Points[i - 1]; var v = Points[i] - a;
                    float t = Mathf.Clamp01(Vector2.Dot(p - a, v) / Mathf.Max(.00001f, v.sqrMagnitude));
                    float d = (p - a - v * t).sqrMagnitude;
                    if (d < best) { best = d; y = Mathf.Lerp(Y[i - 1], Y[i], t); }
                }
                return y;
            }
        }
        static Dictionary<string, object> Obj(object v) => v as Dictionary<string, object>;
        static List<object> Arr(object v) => v as List<object> ?? new List<object>();
        static float F(object v) => Convert.ToSingle(v, System.Globalization.CultureInfo.InvariantCulture);
        static Dictionary<string, object> Doc() => Obj(MiniJson.Parse(File.ReadAllText(Data)));
        public static List<Route> Routes()
        {
            return Arr(Doc()["routes"]).Select(Obj).Select(o =>
            {
                var r = new Route { Id = (string)o["id"], Group = (string)o["group"], Kind = (string)o["kind"], Width = F(o["width"]), Clearance = F(o["clearance"]),
                    Points = Arr(o["points"]).Select(v => new Vector2(F(Arr(v)[0]), F(Arr(v)[1]))).ToArray(), Y = Arr(o["surface_y"]).Select(F).ToArray() };
                for (int i = 1; i < r.Points.Length; i++) r.Length += Vector2.Distance(r.Points[i - 1], r.Points[i]);
                return r;
            }).ToList();
        }

        public static void Grade(float[,] h, float sizeY, float posY)
        {
            int nz = h.GetLength(0), nx = h.GetLength(1);
            var sum = new float[nz, nx]; var weights = new float[nz, nx]; var strongest = new float[nz, nx];
            foreach (var r in Routes())
            {
                if (r.Kind == "tunnel" || r.Kind == "bridge") continue;
                float inner = r.Width * .5f + .8f, outer = inner + 3f;
                // One nearest segment per route/cell avoids oversampling short polyline segments.
                var nearest = new Dictionary<int, (float distance, float y)>();
                for (int k = 1; k < r.Points.Length; k++)
                {
                    var a = r.Points[k - 1]; var b = r.Points[k]; var v = b - a;
                    int x0 = Mathf.Max(0, Mathf.FloorToInt((Mathf.Min(a.x, b.x) - outer) / 1744 * (nx - 1))), x1 = Mathf.Min(nx - 1, Mathf.CeilToInt((Mathf.Max(a.x, b.x) + outer) / 1744 * (nx - 1)));
                    int z0 = Mathf.Max(0, Mathf.FloorToInt((Mathf.Min(a.y, b.y) - outer) / 950 * (nz - 1))), z1 = Mathf.Min(nz - 1, Mathf.CeilToInt((Mathf.Max(a.y, b.y) + outer) / 950 * (nz - 1)));
                    for (int z = z0; z <= z1; z++) for (int x = x0; x <= x1; x++)
                    {
                        var p = new Vector2(x * 1744f / (nx - 1), z * 950f / (nz - 1));
                        float t = Mathf.Clamp01(Vector2.Dot(p - a, v) / Mathf.Max(.00001f, v.sqrMagnitude)), d = (p - a - t * v).magnitude;
                        if (d >= outer) continue;
                        int key = z * nx + x;
                        if (!nearest.TryGetValue(key, out var old) || d < old.distance) nearest[key] = (d, Mathf.Lerp(r.Y[k - 1], r.Y[k], t) - r.Clearance);
                    }
                }
                foreach (var kv in nearest)
                {
                    int z = kv.Key / nx, x = kv.Key % nx; var q = kv.Value;
                    float w = 1f - Mathf.SmoothStep(0, 1, Mathf.InverseLerp(inner, outer, q.distance));
                    // Nearby roads with different elevations (hairpins) use their closest core, never an average across the slope.
                    float priority = w / Mathf.Max(.2f, q.distance + .2f);
                    if (priority > weights[z, x]) { sum[z, x] = q.y; weights[z, x] = priority; strongest[z, x] = w; }
                }
            }
            int changed = 0;
            for (int z = 0; z < nz; z++) for (int x = 0; x < nx; x++)
            {
                if (weights[z, x] <= 0) continue;
                float old = h[z, x] * sizeY + posY, y = Mathf.Lerp(old, sum[z, x], strongest[z, x]);
                if (Mathf.Abs(y - old) > .005f) changed++;
                h[z, x] = (y - posY) / sizeY;
            }
            // Explicit reviewed connected components only. Leave all intentional offshore rocks and Tramduro intact.
            int removed = 0;
            foreach (var island in Arr(Doc()["removed_land"]).Select(Obj))
            {
                foreach (var run in Arr(island["runs"]).Select(Arr))
                {
                    int z = (int)F(run[0]); int a = (int)F(run[1]), b = (int)F(run[2]);
                    for (int x = Math.Max(0, a - 2); x <= Math.Min(nx - 1, b + 2); x++)
                        for (int j = Math.Max(0, z - 2); j <= Math.Min(nz - 1, z + 2); j++)
                            h[j, x] = Mathf.Min(h[j, x], (-.65f - posY) / sizeY);
                }
                removed++;
            }
            Debug.Log($"[G46] road terrain: {changed} vertices fitted to shared surface profiles; {removed} reviewed raster islands removed");
        }

        public static void TunnelHoles(bool[,] solid, float[,] heights, float heightRange, float yOffset)
        {
            var r = Routes().Single(v => v.Kind == "tunnel");
            int nz = solid.GetLength(0), nx = solid.GetLength(1), count = 0;
            for (float s = 0; s <= r.Length; s += .35f)
            {
                var p = r.At(s);
                // Cut only terrain that intersects the clearance volume. Keep the hill above the opaque roof.
                float radius = r.Width * .5f + .8f;
                int x0 = Mathf.Max(0, Mathf.FloorToInt((p.x - radius) / 1744 * nx)), x1 = Mathf.Min(nx - 1, Mathf.CeilToInt((p.x + radius) / 1744 * nx));
                int z0 = Mathf.Max(0, Mathf.FloorToInt((p.z - radius) / 950 * nz)), z1 = Mathf.Min(nz - 1, Mathf.CeilToInt((p.z + radius) / 950 * nz));
                for (int z = z0; z <= z1; z++) for (int x = x0; x <= x1; x++)
                {
                    var q = new Vector2((x + .5f) * 1744 / nx, (z + .5f) * 950 / nz);
                    if ((q - new Vector2(p.x, p.z)).sqrMagnitude > radius * radius) continue;
                    if (Vector2.Dot(q-r.Points[0],r.Points[1]-r.Points[0]) < 0 || Vector2.Dot(q-r.Points[r.Points.Length-1],r.Points[r.Points.Length-1]-r.Points[r.Points.Length-2]) > 0) continue;
                    float low = Mathf.Min(heights[z,x], heights[z+1,x], heights[z,x+1], heights[z+1,x+1])*heightRange+yOffset;
                    if(low > p.y+5.9f) continue;
                    if (solid[z, x]) count++;
                    solid[z, x] = false;
                }
            }
            Debug.Log($"[G46] tunnel: {count} extra full-width terrain-hole cells (roof and walls remain opaque)");
        }

        public static string Meshes(Transform root)
        {
            var routes = Routes(); int count = 0;
            foreach (var mf in root.GetComponentsInChildren<MeshFilter>(true))
            {
                var r = routes.FirstOrDefault(q => mf.name == "Road_" + q.Id || mf.name == "Street_" + q.Id || mf.name == "Bridge_" + q.Id + "_deck");
                if (r == null || mf.sharedMesh == null) continue;
                var mesh = mf.sharedMesh; var v = mesh.vertices;
                for (int i = 0; i < v.Length; i++)
                {
                    var p = mf.transform.TransformPoint(v[i]);p.y = r.Surface(new Vector2(p.x, p.z));v[i] = mf.transform.InverseTransformPoint(p);
                }
                mesh.vertices = v; mesh.RecalculateNormals(); mesh.RecalculateBounds(); EditorUtility.SetDirty(mesh);
                var mc = mf.GetComponent<MeshCollider>(); if (mc) { mc.sharedMesh = null; mc.sharedMesh = mesh; }
                count++;
            }
            RepairTunnel(root, routes.Single(r => r.Kind == "tunnel"));
            ClearApproaches(root, routes);
            int rocks = SeatRocks(root);
            return $"[G46] {count} road meshes and colliders share source profiles; tunnel sections welded; {rocks} unsupported cliff rocks seated";
        }

        static void RepairTunnel(Transform root, Route r)
        {
            var shell = root.Find("Tunnel/Tunnel_shell"); var floor = root.Find("Tunnel/Tunnel_road");
            if (!shell || !floor) throw new InvalidOperationException("G46: tunnel root missing");
            var left = new Vector3[r.Points.Length]; var right = new Vector3[r.Points.Length];
            for (int i = 0; i < r.Points.Length; i++)
            {
                var before = (r.Points[i] - r.Points[Mathf.Max(0, i - 1)]).normalized;
                var after = (r.Points[Mathf.Min(r.Points.Length - 1, i + 1)] - r.Points[i]).normalized;
                if (i == 0) before = after; if (i == r.Points.Length - 1) after = before;
                var tangent = (before + after).normalized; var normal = new Vector2(-tangent.y, tangent.x);
                float half = 4.5f / Mathf.Max(.8f, Vector2.Dot(tangent, after));
                var l = r.Points[i] + normal * half; var rr = r.Points[i] - normal * half;
                left[i] = new Vector3(l.x, r.Y[i], l.y);right[i] = new Vector3(rr.x, r.Y[i], rr.y);
            }
            Rebuild(floor.GetComponent<MeshFilter>(), false); Rebuild(shell.GetComponent<MeshFilter>(), true);
            void Rebuild(MeshFilter mf, bool walls)
            {
                var vertices = new List<Vector3>(); var uv = new List<Vector2>(); var triangles = new List<int>(); float acc = 0;
                void Quad(Vector3 a, Vector3 b, Vector3 c, Vector3 d, float u0, float u1, float v0, float v1)
                {
                    int n = vertices.Count;vertices.AddRange(new[] {a,b,c,d});uv.AddRange(new[] {new Vector2(u0,v1),new Vector2(u1,v1),new Vector2(u1,v0),new Vector2(u0,v0)});
                    triangles.AddRange(new[] {n,n+1,n+2,n,n+2,n+3});
                }
                for (int i = 1; i < left.Length; i++)
                {
                    float end = acc + Vector2.Distance(r.Points[i - 1],r.Points[i]);var up = Vector3.up * 5.5f;
                    if (!walls) Quad(left[i-1],left[i],right[i],right[i-1],acc/4,end/4,0,1);
                    else
                    {
                        Quad(left[i-1]+up,left[i]+up,left[i],left[i-1],acc/4,end/4,0,1);
                        Quad(right[i-1],right[i],right[i]+up,right[i-1]+up,acc/4,end/4,0,1);
                        Quad(right[i-1]+up,right[i]+up,left[i]+up,left[i-1]+up,acc/4,end/4,.6f,1);
                    }
                    acc=end;
                }
                var m = mf.sharedMesh;m.Clear();m.SetVertices(vertices);m.SetUVs(0,uv);m.SetTriangles(triangles,0);m.RecalculateNormals();m.RecalculateBounds();EditorUtility.SetDirty(m);
                var mc=mf.GetComponent<MeshCollider>();if(mc){mc.sharedMesh=null;mc.sharedMesh=m;}
            }
        }

        public static int SeatRocks(Transform root)
        {
            int n = 0;
            foreach (var t in root.GetComponentsInChildren<Transform>(true).Where(t => t.name.StartsWith("Rock_") && t.parent && t.parent.name == "RockOutcrops"))
                if (W85FloatCheck.SeatRock(t)) n++;
            return n;
        }

        static float Distance(Route r, Vector2 p)
        {
            float best=float.MaxValue;
            for(int i=1;i<r.Points.Length;i++){var v=r.Points[i]-r.Points[i-1];float t=Mathf.Clamp01(Vector2.Dot(p-r.Points[i-1],v)/Mathf.Max(.00001f,v.sqrMagnitude));best=Mathf.Min(best,(p-r.Points[i-1]-t*v).magnitude);}
            return best;
        }

        public static void PaintAccessRuts(TerrainData td)
        {
            // The corrected fork is a dirt road: reuse the current gravel/worn-grass terrain layers.
            int gravel=Array.FindIndex(td.terrainLayers,l=>l.name=="TL17_gravel");if(gravel<0)return;
            int n=td.alphamapResolution;
            int x0=Mathf.FloorToInt(273f/1744*n),z0=Mathf.FloorToInt(170f/950*n),x1=Mathf.CeilToInt(292f/1744*n),z1=Mathf.CeilToInt(197f/950*n);
            var a=td.GetAlphamaps(x0,z0,x1-x0,z1-z0);
            var roads=Routes().Where(r=>r.Id=="forest_road_hamlet"||r.Id=="forest_road_wagon_east").ToArray();
            for(int z=0;z<a.GetLength(0);z++)for(int x=0;x<a.GetLength(1);x++)
            {
                var p=new Vector2((x+x0+.5f)/n*1744,(z+z0+.5f)/n*950);float d=roads.Min(r=>Distance(r,p));
                float w=.80f*(1-Mathf.SmoothStep(.35f,1.0f,Mathf.Abs(d-.88f)));
                if(d>2||w<=0)continue;
                for(int l=0;l<a.GetLength(2);l++)a[z,x,l]*=1-w;a[z,x,gravel]+=w;
            }
            td.SetAlphamaps(x0,z0,a);EditorUtility.SetDirty(td);
        }
        static void ClearApproaches(Transform root, List<Route> routes)
        {
            var terrain=root.GetComponentsInChildren<Terrain>().First(t=>t.GetComponent<TerrainCollider>());
            int signs=0,hedges=0,triangles=0;
            foreach(var sign in root.GetComponentsInChildren<Transform>(true).Where(t=>t.name.StartsWith("sign_giveway_")))
            {
                var p=sign.position;bool moved=false;
                for(int k=0;k<4;k++)
                {
                    var r=routes.Where(r=>r.Kind!="tunnel").OrderBy(r=>Distance(r,new Vector2(p.x,p.z))-r.Width*.5f).First();
                    float gap=Distance(r,new Vector2(p.x,p.z));if(gap>=r.Width*.5f+1.2f)break;
                    Vector2 best=default;float dist=float.MaxValue;
                    for(int i=1;i<r.Points.Length;i++){var a=r.Points[i-1];var v=r.Points[i]-a;float t=Mathf.Clamp01(Vector2.Dot(new Vector2(p.x,p.z)-a,v)/Mathf.Max(.00001f,v.sqrMagnitude));var q=a+t*v;float d=(q-new Vector2(p.x,p.z)).sqrMagnitude;if(d<dist){dist=d;best=q;}}
                    var away=(new Vector2(p.x,p.z)-best).normalized;if(away.sqrMagnitude<.1f)away=Vector2.right;
                    var at=best+away*(r.Width*.5f+1.25f);p.x=at.x;p.z=at.y;moved=true;
                }
                if(moved){p.y=terrain.SampleHeight(p)+terrain.transform.position.y;sign.position=p;signs++;}
            }
            foreach(var hedge in root.GetComponentsInChildren<Collider>(true).Where(c=>c.name.StartsWith("Hedge_07-V")&&c.gameObject.activeSelf))
            {
                string id=hedge.name.Replace("Hedge_","").Replace("-plot","-drive");var r=routes.FirstOrDefault(r=>r.Id==id);if(r==null)continue;
                for(float s=0;s<=r.Length+1;s+=.4f)
                {
                    var p=r.At(Mathf.Min(s,r.Length))+Vector3.up*.9f;var q=hedge.ClosestPoint(p);
                    if(new Vector2(p.x-q.x,p.z-q.z).magnitude<r.Width*.5f+.45f){hedge.gameObject.SetActive(false);hedges++;break;}
                }
            }
            var approach=routes.Single(r=>r.Id=="forest_to_valley");
            foreach(var mf in root.GetComponentsInChildren<MeshFilter>(true).Where(m=>m.name=="BridgeSpan_to_quiet_valley_parapets"))
            {
                var mesh=mf.sharedMesh;var v=mesh.vertices;var old=mesh.triangles;var keep=new List<int>();
                for(int i=0;i<old.Length;i+=3)
                {
                    var center=mf.transform.TransformPoint((v[old[i]]+v[old[i+1]]+v[old[i+2]])/3);
                    if(Distance(approach,new Vector2(center.x,center.z))<approach.Width*.5f+.9f){triangles++;continue;}
                    keep.Add(old[i]);keep.Add(old[i+1]);keep.Add(old[i+2]);
                }
                mesh.triangles=keep.ToArray();mesh.RecalculateBounds();EditorUtility.SetDirty(mesh);var mc=mf.GetComponent<MeshCollider>();if(mc){mc.sharedMesh=null;mc.sharedMesh=mesh;}
            }
            Debug.Log($"[G46] approaches: {signs} signs moved to shoulders, {hedges} hedge segments cleared at villa gates, {triangles} parapet triangles cleared at the forest/valley T-junction");
        }

        [MenuItem("OnlyVolunteers/Map/G46 Apply roads, tunnel, terrain (open v02 scene)")]
        public static void ApplyOpenScene()
        {
            if (EditorApplication.isPlaying) throw new InvalidOperationException("Exit play before applying G46");
            var scene = SceneManager.GetActiveScene();
            if (!scene.path.EndsWith("_v02.unity")) throw new InvalidOperationException("G46 requires the W86 v02 scene");
            var terrain = scene.GetRootGameObjects().SelectMany(g => g.GetComponentsInChildren<Terrain>(true)).First(t => t.GetComponent<TerrainCollider>());
            var td = terrain.terrainData;
            // Reapply from the same RAW source as a full build, so repeated partial repairs never compound shoulder grading.
            int resolution=td.heightmapResolution;var raw=File.ReadAllBytes(Application.dataPath+"/OnlyVolunteers/Map/W85Build/Data/v02/Heightmap_v85_2049_r16.bytes");var h=new float[resolution,resolution];
            for(int z=0;z<resolution;z++)for(int x=0;x<resolution;x++){int k=(z*resolution+x)*2;h[z,x]=(raw[k]|raw[k+1]<<8)/65535f;}
            W85Builder.GradeFootprints(h,resolution,td.size.y,terrain.transform.position.y);
            Grade(h,td.size.y,terrain.transform.position.y);td.SetHeights(0,0,h);
            var holes=td.GetHoles(0,0,td.holesResolution,td.holesResolution);TunnelHoles(holes,h,td.size.y,terrain.transform.position.y);td.SetHoles(0,0,holes);EditorUtility.SetDirty(td);
            var root=terrain.transform.parent;string result=Meshes(root);Physics.SyncTransforms();
            PaintAccessRuts(td);
            EditorSceneManager.MarkSceneDirty(scene);AssetDatabase.SaveAssets();EditorSceneManager.SaveScene(scene);
            File.WriteAllText(Review+"/partial_apply.txt",result);Debug.Log(result);
        }
    }
}
