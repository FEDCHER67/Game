using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;
using UnityEngine;
using UnityEditor;
using UnityEditor.SceneManagement;
using OnlyVolunteers.Map.Look;
using OnlyVolunteers.Map.Look.V3;
using OnlyVolunteers.ThirdParty.GrassInstancerMB;
using Object=UnityEngine.Object;

namespace OnlyVolunteers.Map.Grass.Editor
{
    public static class GrassPlacement24
    {
        public const string Root="Assets/OnlyVolunteers/Map/Grass";
        public const string Vendor="Assets/OnlyVolunteers/ThirdParty/GrassInstancer_MB";
        const float ChunkSize=16, Step=.5f;
        public static string Build(string revision="v01",string destinationScene=null)
        {
            if(EditorApplication.isPlaying) throw new InvalidOperationException("Stop Play before baking grass");
            var scene=UnityEngine.SceneManagement.SceneManager.GetActiveScene();
            if(!scene.name.StartsWith("Map_Look_v19")) throw new InvalidOperationException("G24 requires a v19 look scene");
            if(Object.FindAnyObjectByType<ChunkedGrassRenderer24>()) throw new InvalidOperationException("Grass already exists; never stack layers or overwrite delivered revisions");
            var terrain=Object.FindAnyObjectByType<MapHeightSampler>()?.Terrain;
            var weather=Object.FindAnyObjectByType<DistrictWeather19V05>();
            if(!terrain || !weather) throw new InvalidOperationException("v19 terrain/weather missing");
            string output=Root+"/Baked_"+revision;
            if(Directory.Exists(output)) throw new IOException("Baked revision already exists: "+output);
            string scenePath=destinationScene??("Assets/OnlyVolunteers/Scenes/Map/"+scene.name+"_Grass_"+revision+".unity");
            if(File.Exists(scenePath)) throw new IOException("Scene revision already exists");
            var watch=System.Diagnostics.Stopwatch.StartNew();
            var exclusion=GrassExclusion24.Build(terrain);
            var td=terrain.terrainData;var origin=terrain.transform.position;var size=td.size;
            var alpha=td.GetAlphamaps(0,0,td.alphamapWidth,td.alphamapHeight);
            var names=td.terrainLayers.Select(t=>t?t.name.ToLowerInvariant():"").ToArray();
            var districtBounds=weather.districts.Select(d=>d.bounds).ToArray();var weights=new float[districtBounds.Length];
            // Final v19 retains meadow splats in Downtown. Use its authored park polygons for land use.
            var parkPolygons=MapLookBuilder.Load("v19").ground.Where(g=>g.soft&&g.mat=="park_grass").Select(g=>g.pts).ToArray();
            var byChunk=new SortedDictionary<int,List<ChunkedGrassRenderer24.Blade>>();
            var districtCounts=new SortedDictionary<string,int>();
            int nx=Mathf.CeilToInt(size.x/ChunkSize), candidates=0, rejectedHard=0;
            // Canopy exclusion is baked from the actual terrain's tree positions.
            var canopy=new HashSet<long>();
            foreach(var tree in td.treeInstances)
            {
                var p=Vector3.Scale(tree.position,size)+origin;
                int tx=Mathf.FloorToInt(p.x/2),tz=Mathf.FloorToInt(p.z/2);
                for(int dz=-2;dz<=2;dz++)for(int dx=-2;dx<=2;dx++)canopy.Add(Key(tx+dx,tz+dz));
            }
            for(int iz=0;iz<size.z/Step;iz++) for(int ix=0;ix<size.x/Step;ix++)
            {
                float x=origin.x+(ix+.12f+.76f*Hash(ix,iz,1))*Step,z=origin.z+(iz+.12f+.76f*Hash(ix,iz,2))*Step;
                float clearance=exclusion.Distance(x,z);
                if(clearance<.9f) { rejectedHard++;continue; }
                int ax=Mathf.Clamp((int)((x-origin.x)/size.x*td.alphamapWidth),0,td.alphamapWidth-1),az=Mathf.Clamp((int)((z-origin.z)/size.z*td.alphamapHeight),0,td.alphamapHeight-1);
                float meadow=0,lawn=0,park=0,dry=0,sand=0;
                for(int l=0;l<names.Length;l++)
                {
                    string n=names[l];float w=alpha[az,ax,l];
                    if(n.Contains("meadow")||n.Contains("worn_grass"))meadow+=w;
                    else if(n.Contains("park"))park+=w;else if(n.Contains("lawn"))lawn+=w;
                    else if(n.Contains("dry")||n.Contains("dirt"))dry+=w;else if(n.Contains("sand"))sand+=w;
                }
                string district="between_districts";float districtEdge=0;
                for(int d=0;d<weather.districts.Length;d++)
                {var b=districtBounds[d];if(x>=b.x && x<=b.z && z>=b.y && z<=b.w){district=weather.districts[d].id;districtEdge=Mathf.Min(Mathf.Min(x-b.x,b.z-x),Mathf.Min(z-b.y,b.w-z));break;}}
                bool rough=district=="residential",beach=district=="beach",forest=district=="forest";
                float ground=meadow+lawn+park;
                if(district=="village")ground=Mathf.Max(ground,dry*.8f);
                if(beach)ground=Mathf.Max(ground,sand*.8f);
                if(rough)ground=Mathf.Max(ground,dry*.75f);
                if(ground<.55f)continue;
                if(district=="old_town" && park<.55f && !parkPolygons.Any(p=>LookGeom.Inside(p,x,z)))continue;
                if(forest && (meadow<.6f||canopy.Contains(Key(Mathf.FloorToInt(x/2),Mathf.FloorToInt(z/2)))))continue;
                float patch=Mathf.PerlinNoise(x*.047f+14.2f,z*.047f+19.4f);
                float pockets=Mathf.PerlinNoise(x*.18f+5.7f,z*.18f+28.1f);
                float density=Mathf.SmoothStep(0,1,Mathf.InverseLerp(.43f,.64f,patch))*ground;
                if(pockets<.31f)continue;
                bool roadside=clearance<4.5f;
                // The plan calls Quiet Valley "fields"; "transition" is the construction district.
                bool trim=district=="old_town" || ((district=="fields"||district=="elite") && (districtEdge>18||lawn+park>.35f));
                if(roadside)density*=.24f;else if(trim)density*=.42f;
                if(rough)density*=.17f;else if(beach)density*=.13f;else if(forest)density*=.42f;
                else if(district=="industrial"||district=="tramduro"||district=="transition")density*=.24f;
                if(Hash(ix,iz,3)>density)continue;
                float u=(x-origin.x)/size.x,v=(z-origin.z)/size.z;
                if(td.GetSteepness(u,v)>34)continue;
                float y=td.GetInterpolatedHeight(u,v)+origin.y;
                // v19's dry flat yards are at Y=0; only water membership rejects them.
                if(ObjectWater(terrain,x,z,y))continue;
                DistrictBlend19.Weights(districtBounds,new Vector2(x,z),weather.blendMetres,weights);
                float palette=0;for(int d=0;d<weights.Length;d++)palette+=weights[d]*weather.districts[d].palette;
                palette=Mathf.Min(.999f,palette)+(rough?2:beach?4:0);
                int blades=rough||beach?3:roadside||trim?2:4;
                for(int b=0;b<blades;b++)
                {
                    float bx=x+(Hash(ix,iz,10+b*3)-.5f)*.28f,bz=z+(Hash(ix,iz,11+b*3)-.5f)*.28f;
                    if(exclusion.Distance(bx,bz)<.75f)continue;
                    float by=td.GetInterpolatedHeight((bx-origin.x)/size.x,(bz-origin.z)/size.z)+origin.y;
                    if(ObjectWater(terrain,bx,bz,by))continue;
                    float h=roadside?Mathf.Lerp(.1f,.25f,Hash(ix,iz,30+b)):trim?Mathf.Lerp(.12f,.24f,Hash(ix,iz,30+b)):
                        rough?Mathf.Lerp(.22f,.48f,Hash(ix,iz,30+b)):beach?Mathf.Lerp(.28f,.55f,Hash(ix,iz,30+b)):Mathf.Lerp(.5f,.9f,Hash(ix,iz,30+b));
                    float yaw=Hash(ix,iz,40+b)*Mathf.PI*2;
                    float width=h<.26f?Mathf.Lerp(.035f,.06f,Hash(ix,iz,50+b)):Mathf.Lerp(.085f,.15f,Hash(ix,iz,50+b));
                    int key=Mathf.FloorToInt((bx-origin.x)/ChunkSize)+nx*Mathf.FloorToInt((bz-origin.z)/ChunkSize);
                    if(!byChunk.TryGetValue(key,out var list))byChunk[key]=list=new List<ChunkedGrassRenderer24.Blade>();
                    list.Add(new(){positionHeight=new Vector4(bx,by-.015f,bz,h),shape=new Vector4(Mathf.Cos(yaw),Mathf.Sin(yaw),width,palette)});
                    if(!districtCounts.ContainsKey(district))districtCounts[district]=0;districtCounts[district]++;candidates++;
                }
            }
            if(candidates<1000) throw new InvalidOperationException("Grass bake unexpectedly empty. Terrain layer names: "+string.Join(",",names));
            Directory.CreateDirectory(output);
            var data=ScriptableObject.CreateInstance<GrassPatchData24>();data.instanceCount=candidates;
            var chunkData=new List<GrassPatchData24.Chunk>();var worldBounds=new Bounds();bool first=true;uint start=0;
            string binary=output+"/GrassInstances_"+revision+".bytes";
            using(var writer=new BinaryWriter(File.Create(binary))) foreach(var pair in byChunk)
            {
                var bounds=new Bounds((Vector3)pair.Value[0].positionHeight,Vector3.zero);
                foreach(var blade in pair.Value)
                {
                    bounds.Encapsulate((Vector3)blade.positionHeight+Vector3.up*blade.positionHeight.w);
                    bounds.Encapsulate((Vector3)blade.positionHeight);
                    Write(writer,blade.positionHeight);Write(writer,blade.shape);
                }
                bounds.Expand(new Vector3(1.8f,.2f,1.8f));
                chunkData.Add(new(){centre=bounds.center,extents=bounds.extents,start=start,count=(uint)pair.Value.Count});start+=(uint)pair.Value.Count;
                if(first){worldBounds=bounds;first=false;}else worldBounds.Encapsulate(bounds);
            }
            AssetDatabase.ImportAsset(binary,ImportAssetOptions.ForceSynchronousImport);
            data.instances=AssetDatabase.LoadAssetAtPath<TextAsset>(binary);data.chunks=chunkData.ToArray();data.worldBounds=worldBounds;
            data.sourceScene=scene.path;data.sourceCommit="f5983739d6159dbad115950e9ac349a1dd44e78e";
            data.placementSummary=string.Join("; ",districtCounts.Select(p=>p.Key+"="+p.Value))+"; mask="+exclusion.Summary+"; rejectedHard="+rejectedHard+"; seconds="+watch.Elapsed.TotalSeconds.ToString("F2");
            AssetDatabase.CreateAsset(data,output+"/GrassData_"+revision+".asset");
            var mesh=MakeBlade();AssetDatabase.CreateAsset(mesh,output+"/Blade3Triangles_"+revision+".asset");
            var shader=Shader.Find("OnlyVolunteers/Grass/MB_TallGrass24");if(!shader)throw new InvalidOperationException("Grass shader missing");
            var mat=new Material(shader){name="TallGrass_"+revision,enableInstancing=true};AssetDatabase.CreateAsset(mat,output+"/TallGrass_"+revision+".mat");
            var renderer=new GameObject("G24_TallGrass_"+revision).AddComponent<ChunkedGrassRenderer24>();
            renderer.data=data;renderer.bladeMesh=mesh;renderer.material=mat;renderer.visibility=AssetDatabase.LoadAssetAtPath<ComputeShader>(Vendor+"/GrassVisibility24.compute");
            EditorSceneManager.MarkSceneDirty(scene);EditorSceneManager.SaveScene(scene,scenePath);
            string evidence="Working/Reviews/Grass/bake_"+revision+".txt";Directory.CreateDirectory(Path.GetDirectoryName(evidence));
            File.WriteAllText(evidence,scenePath+"\n"+data.placementSummary+"\ninstances="+candidates+"; chunks="+chunkData.Count+"; triangles per blade=3\nlayers="+string.Join(",",names));
            return File.ReadAllText(evidence);
        }
        static MapHeightSampler cachedSampler;
        static bool ObjectWater(Terrain terrain,float x,float z,float y)
        {
            if(!cachedSampler||cachedSampler.Terrain!=terrain)cachedSampler=Object.FindAnyObjectByType<MapHeightSampler>();
            return cachedSampler && cachedSampler.InWater(x,z,out _);
        }
        static void Write(BinaryWriter w,Vector4 v){w.Write(v.x);w.Write(v.y);w.Write(v.z);w.Write(v.w);}
        static long Key(int x,int z)=>((long)x<<32)^(uint)z;
        public static float Hash(int x,int z,int salt)
        {unchecked{uint h=(uint)(x*73856093)^(uint)(z*19349663)^(uint)(salt*83492791);h^=h>>13;h*=0x5bd1e995;h^=h>>15;return(h&0xffffff)/16777216f;}}
        public static Mesh MakeBlade()
        {
            var mesh=new Mesh{name="G24 broad tapered 3-triangle blade"};
            mesh.vertices=new[]{new Vector3(-.5f,0,0),new Vector3(.5f,0,0),new Vector3(-.3f,.56f,.06f),new Vector3(.3f,.56f,.06f),new Vector3(.06f,1,.16f)};
            mesh.uv=new[]{new Vector2(0,0),new Vector2(1,0),new Vector2(0,.56f),new Vector2(1,.56f),new Vector2(.5f,1)};
            mesh.triangles=new[]{0,2,1,1,2,3,2,4,3};mesh.RecalculateNormals();mesh.RecalculateBounds();return mesh;
        }
        public static string AttachPlay(string sourcePath,string revision="v01")
        {
            if(EditorApplication.isPlaying)throw new InvalidOperationException("Stop Play first");
            var scene=UnityEngine.SceneManagement.SceneManager.GetActiveScene();
            if(!scene.name.StartsWith("Map_Look_v19_Play"))throw new InvalidOperationException("Expected v19 Play scene");
            if(Object.FindAnyObjectByType<ChunkedGrassRenderer24>())throw new InvalidOperationException("Grass already exists");
            string dest="Assets/OnlyVolunteers/Scenes/Map/"+scene.name+"_Grass_"+revision+".unity";
            if(File.Exists(dest))throw new IOException("Scene revision exists");
            var data=AssetDatabase.LoadAssetAtPath<GrassPatchData24>(sourcePath);if(!data)throw new FileNotFoundException(sourcePath);
            var go=new GameObject("G24_TallGrass_"+revision);var render=go.AddComponent<ChunkedGrassRenderer24>();render.data=data;
            render.bladeMesh=AssetDatabase.LoadAssetAtPath<Mesh>(Root+"/Baked_"+revision+"/Blade3Triangles_"+revision+".asset");
            render.material=AssetDatabase.LoadAssetAtPath<Material>(Root+"/Baked_"+revision+"/TallGrass_"+revision+".mat");
            render.visibility=AssetDatabase.LoadAssetAtPath<ComputeShader>(Vendor+"/GrassVisibility24.compute");
            EditorSceneManager.MarkSceneDirty(scene);EditorSceneManager.SaveScene(scene,dest);return dest;
        }
    }
}
