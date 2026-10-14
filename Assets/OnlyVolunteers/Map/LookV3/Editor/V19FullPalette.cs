using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;
using UnityEditor;
using UnityEditor.SceneManagement;
using OnlyVolunteers.Audio;
using Object=UnityEngine.Object;

namespace OnlyVolunteers.Map.Look.V3
{
    // Applies approved checkpoint assets read-only; the separately approved happykeys set replaces Rough trees.
    public static class V19FullPalette
    {
        public const string Output=V19PaletteTest.Root+"/Full_v07";
        static List<object> units;
        static Dictionary<string,LookBuilding> oldBuildings,newBuildings;
        static MapHeightSampler ground;
        static Terrain sourceTerrain;
        static Vector4 world;
        static Texture2D field;
        static readonly Dictionary<string,Material> variants=new();
        static float F(object v)=>Convert.ToSingle(v);
        static float[] Ring(object v)=>((List<object>)v).SelectMany(q=>((List<object>)q).Select(F)).ToArray();
        static Vector2 Xz(Vector3 p)=>new(p.x,p.z);
        public static Vector2 Move(Vector2 p)
        {
            if(oldBuildings!=null)foreach(var b in oldBuildings.Values)
            {
                if(!newBuildings.TryGetValue(b.id,out var n) || (b.x==n.x && b.y==n.y))continue;
                if(LookGeom.Inside(b.fp,p.x,p.y))return p+new Vector2(n.x-b.x,n.y-b.y);
            }
            foreach(Dictionary<string,object> u in units)
            {
                if(!LookGeom.Inside(Ring(u["region_m"]),p.x,p.y))continue;
                var c=(List<object>)u["centre_m"];var t=(List<object>)u["delta_m"];float s=F(u["scale"]);
                return new Vector2(F(c[0])+(p.x-F(c[0]))*s+F(t[0]),F(c[1])+(p.y-F(c[1]))*s+F(t[1]));
            }
            return p;
        }
        static Vector3 Relocate(Vector3 p)
        {
            Vector2 q=Move(Xz(p));float oldY=sourceTerrain.SampleHeight(p)+sourceTerrain.transform.position.y;
            return new Vector3(q.x,ground.Height(q.x,q.y)+(p.y-oldY),q.y);
        }
        public static string Apply()
        {
            if(EditorApplication.isPlaying)throw new InvalidOperationException("Stop Play first");
            if(Directory.Exists(Output))throw new IOException("Full palette asset revision exists");
            LookAssetStore.EnsureFolder(Output);LookAssetStore.EnsureFolder(Output+"/Materials");
            var target=UnityEngine.SceneManagement.SceneManager.GetActiveScene();
            ground=Object.FindAnyObjectByType<MapHeightSampler>();var terrain=ground.Terrain;
            units=V19Infill.List(V19Infill.Data(),"unit_transforms");
            oldBuildings=MapLookBuilder.Load("v18").buildings.ToDictionary(b=>b.id);newBuildings=MapLookBuilder.Load("v19").buildings.ToDictionary(b=>b.id);
            var source=EditorSceneManager.OpenScene(V19PaletteP4.Scene,OpenSceneMode.Additive);
            UnityEngine.SceneManagement.SceneManager.SetActiveScene(target);
            var roots=source.GetRootGameObjects();var srcRoot=roots.First(g=>g.name=="V19_Palette_v02");
            var oldWeather=srcRoot.GetComponent<DistrictWeather19V04>();var oldFog=oldWeather.visibleFog;
            oldWeather.enabled=false;oldFog.enabled=false;
            sourceTerrain=roots.SelectMany(g=>g.GetComponentsInChildren<Terrain>()).First();
            world=new Vector4(terrain.transform.position.x,terrain.transform.position.z,terrain.terrainData.size.x,terrain.terrainData.size.z);
            field=AssetDatabase.LoadAssetAtPath<Texture2D>(V19PaletteP2.Output+"/Palette_Field_v19.asset");
            var palette=Object.Instantiate(srcRoot);palette.name="V19_ApprovedPalette_Full_v01";
            UnityEngine.SceneManagement.SceneManager.MoveGameObjectToScene(palette,target);
            foreach(var c in palette.GetComponents<MonoBehaviour>())c.enabled=false;
            var weather=palette.AddComponent<DistrictWeather19V05>();weather.enabled=false;
            weather.districts=oldWeather.districts.Select(d=>JsonUtility.FromJson<DistrictAtmosphere19.District>(JsonUtility.ToJson(d))).ToArray();
            weather.weather=oldWeather.weather.Select(w=>JsonUtility.FromJson<DistrictWeather19V05.Weather>(JsonUtility.ToJson(w))).ToArray();
            weather.skyTemplate=oldWeather.skyTemplate;weather.blendMetres=oldWeather.blendMetres;
            weather.sun=target.GetRootGameObjects().SelectMany(g=>g.GetComponentsInChildren<Light>()).First(l=>l.type==LightType.Directional);
            weather.blendVolume=palette.GetComponentsInChildren<Volume>().First(v=>v.name=="V19_Light_between_districts");
            var fog=palette.AddComponent<DistrictFog19V05>();fog.enabled=false;weather.visibleFog=fog;
            fog.baselinePipeline=oldFog.baselinePipeline;fog.mistTemplate=oldFog.mistTemplate;fog.haloTemplate=oldFog.haloTemplate;
            fog.terrainWorld=world;fog.forestDensity=oldFog.forestDensity;fog.groundExtinction=oldFog.groundExtinction;
            var heights=new Texture2D(256,256,TextureFormat.RFloat,false,true){name="TerrainWorldHeights_full_v19",wrapMode=TextureWrapMode.Clamp,filterMode=FilterMode.Bilinear};
            var pixels=new Color[256*256];for(int z=0;z<256;z++)for(int x=0;x<256;x++)pixels[z*256+x]=new Color(terrain.terrainData.GetInterpolatedHeight(x/255f,z/255f)+terrain.transform.position.y,0,0,1);
            heights.SetPixels(pixels);heights.Apply();AssetDatabase.CreateAsset(heights,Output+"/TerrainWorldHeights.asset");fog.groundHeights=heights;
            var banks=new List<DistrictFog19V05.Bank>();
            foreach(var b in oldFog.banks)banks.Add(new(){position=Relocate(b.position),size=b.forest?b.size:Vector2.Lerp(b.size,new Vector2(18,3.7f),.25f),phase=b.phase,forest=b.forest,opacity=b.forest?.14f:.104f});
            var pockets=new[]{new Vector2(570,630),new(610,596),new(625,617),new(647,648),new(664,651),new(704,653),new(716,671),new(753,623),new(681,688),new(520,620),new(490,609)};
            for(int i=0;i<pockets.Length;i++){var q=Move(pockets[i]);banks.Add(new(){position=new Vector3(q.x,ground.Height(q.x,q.y)+1.05f,q.y),size=new Vector2(12+(i%4)*3,1.65f),phase=i*1.74f,opacity=.055f});}
            fog.banks=banks.ToArray();fog.halos=oldFog.halos.Select(h=>new DistrictFog19V05.Halo{position=Relocate(h.light?h.light.transform.position:h.position),colour=h.colour,size=h.size}).ToArray();
            CopyRenderer(fog);
            TerrainPalette(terrain,sourceTerrain,weather);
            // Reuse the approved surface assets by name. Only newly needed colours get v19-owned variants.
            variants.Clear();foreach(string guid in AssetDatabase.FindAssets("t:Material",new[]{V19PaletteP2.Output+"/Materials"}))
            {var m=AssetDatabase.LoadAssetAtPath<Material>(AssetDatabase.GUIDToAssetPath(guid));variants[m.name]=m;}
            int changed=0;
            foreach(var r in target.GetRootGameObjects().SelectMany(g=>g.GetComponentsInChildren<MeshRenderer>(true)))
            {
                var info=r.GetComponentInParent<MapBuildingInfo>();LookBuilding b=info && newBuildings.TryGetValue(info.Id,out var v)?v:null;
                var mats=r.sharedMaterials;bool altered=false;
                for(int i=0;i<mats.Length;i++)if(mats[i] && mats[i].shader.name=="OnlyVolunteers/StyleV3/Surface")
                {string hex=Bright(mats[i].name,b);if(hex!=null){mats[i]=Surface(mats[i],hex);altered=true;}}
                if(altered){r.sharedMaterials=mats;changed++;}
            }
            foreach(string name in new[]{"V19_Life_CheckpointP_v02","V19_FogLightCues_v03"})
            {
                var copy=Object.Instantiate(roots.First(g=>g.name==name));copy.name=name+"_Full_v01";
                UnityEngine.SceneManagement.SceneManager.MoveGameObjectToScene(copy,target);
                foreach(Transform t in copy.transform)
                {
                    foreach(var line in t.GetComponentsInChildren<LineRenderer>())if(line.useWorldSpace)for(int i=0;i<line.positionCount;i++)line.SetPosition(i,Relocate(line.GetPosition(i)));
                    t.position=Relocate(t.position);
                }
                foreach(var life in copy.GetComponentsInChildren<DistrictLife19V02>())foreach(var flyer in life.flyers)flyer.centre=Relocate(flyer.centre);
            }
            BakeAmbience(target);
            string nature=V19Happykeys.Apply(ground,weather);
            EditorSceneManager.CloseScene(source,true);UnityEngine.SceneManagement.SceneManager.SetActiveScene(target);
            sourceTerrain=null;weather.enabled=true;fog.enabled=true;AssetDatabase.SaveAssetIfDirty(terrain.terrainData);
            EditorSceneManager.MarkSceneDirty(target);EditorSceneManager.SaveScene(target);
            return "Approved v19 palette: "+changed+" renderers; "+nature+"; Rough distance=.01135, ground=.01375, v04 grade/sky; Forest atmosphere unchanged";
        }
        static void CopyRenderer(DistrictFog19V05 fog)
        {
            AssetDatabase.CopyAsset(AssetDatabase.GetAssetPath(fog.baselinePipeline),Output+"/PC_FogPipeline_v19.asset");
            fog.pipeline=AssetDatabase.LoadAssetAtPath<UniversalRenderPipelineAsset>(Output+"/PC_FogPipeline_v19.asset");
            var rp=new SerializedObject(fog.pipeline);var list=rp.FindProperty("m_RendererDataList");int index=rp.FindProperty("m_DefaultRendererIndex").intValue;
            var source=(ScriptableRendererData)list.GetArrayElementAtIndex(index).objectReferenceValue;
            AssetDatabase.CopyAsset(AssetDatabase.GetAssetPath(source),Output+"/PC_FogRenderer_v19.asset");
            var renderer=AssetDatabase.LoadAssetAtPath<ScriptableRendererData>(Output+"/PC_FogRenderer_v19.asset");list.GetArrayElementAtIndex(index).objectReferenceValue=renderer;rp.ApplyModifiedPropertiesWithoutUndo();
            fog.fogTemplate=new Material(Shader.Find("OnlyVolunteers/StyleV3/DistrictFog19V05")){name="DepthHeightFog_v19_v05"};AssetDatabase.CreateAsset(fog.fogTemplate,Output+"/DepthHeightFog.mat");
            fog.feature=ScriptableObject.CreateInstance<FullScreenPassRendererFeature>();fog.feature.name="V19_Fog_v05";fog.feature.injectionPoint=FullScreenPassRendererFeature.InjectionPoint.BeforeRenderingTransparents;
            fog.feature.fetchColorBuffer=false;fog.feature.requirements=ScriptableRenderPassInput.Depth;fog.feature.passMaterial=fog.fogTemplate;
            AssetDatabase.AddObjectToAsset(fog.feature,renderer);renderer.rendererFeatures.Add(fog.feature);
            var rd=new SerializedObject(renderer);var map=rd.FindProperty("m_RendererFeatureMap");map.arraySize=renderer.rendererFeatures.Count;
            for(int i=0;i<map.arraySize;i++){AssetDatabase.TryGetGUIDAndLocalFileIdentifier(renderer.rendererFeatures[i],out string guid,out long id);map.GetArrayElementAtIndex(i).longValue=id;}
            rd.ApplyModifiedPropertiesWithoutUndo();renderer.SetDirty();EditorUtility.SetDirty(renderer);EditorUtility.SetDirty(fog.feature);
            AssetDatabase.SaveAssetIfDirty(renderer);AssetDatabase.SaveAssetIfDirty(fog.pipeline);AssetDatabase.SaveAssetIfDirty(fog.feature);
        }
        static void TerrainPalette(Terrain terrain,Terrain approved,DistrictWeather19V05 weather)
        {
            var td=terrain.terrainData;var src=approved.terrainData;int w=td.alphamapWidth,h=td.alphamapHeight,n=td.terrainLayers.Length;
            var old=td.GetAlphamaps(0,0,w,h);var splat=new float[h,w,n*2];td.terrainLayers=src.terrainLayers;
            var bounds=weather.districts.Select(d=>d.bounds).ToArray();var weights=new float[bounds.Length];
            for(int z=0;z<h;z++)for(int x=0;x<w;x++)
            {
                DistrictBlend19.Weights(bounds,new Vector2(world.x+x/(float)(w-1)*world.z,world.y+z/(float)(h-1)*world.w),60,weights);
                float t=0;for(int i=0;i<weights.Length;i++)t+=weights[i]*weather.districts[i].palette;
                for(int k=0;k<n;k++){splat[z,x,k]=old[z,x,k]*(1-t);splat[z,x,k+n]=old[z,x,k]*t;}
            }
            td.SetAlphamaps(0,0,splat);td.detailPrototypes=src.detailPrototypes;td.treePrototypes=src.treePrototypes;
            var trees=src.treeInstances;int moved=0;
            var placements=V19Infill.List(V19Infill.Data(),"tree_placement_changes");
            for(int i=0;i<trees.Length;i++)
            {
                Vector3 p=Vector3.Scale(trees[i].position,src.size)+approved.transform.position;Vector2 q=Move(Xz(p));
                // Map the known cleared source instance where possible; preserve every prototype/scale/rotation/colour.
                float best=2.5f*2.5f;Dictionary<string,object> hit=null;
                foreach(Dictionary<string,object> t in placements)
                {var b=(Dictionary<string,object>)t["before"];float dist=(new Vector2(F(b["x"]),F(b["y"]))-Xz(p)).sqrMagnitude;if(dist<best){best=dist;hit=t;}}
                if(hit!=null){var a=(Dictionary<string,object>)hit["after"];q=new Vector2(F(a["x"]),F(a["y"]));}
                if((q-Xz(p)).sqrMagnitude>.0001f)moved++;
                var pos=new Vector3(q.x,ground.Height(q.x,q.y),q.y)-terrain.transform.position;trees[i].position=new Vector3(pos.x/td.size.x,pos.y/td.size.y,pos.z/td.size.z);
            }
            td.SetTreeInstances(trees,false);EditorUtility.SetDirty(td);AssetDatabase.SaveAssetIfDirty(td);td.SetAlphamaps(0,0,splat);EditorUtility.SetDirty(td);
            File.WriteAllText(V19PilotTools.OutDir+"/full_tree_audit_round1_v04.json",JsonUtility.ToJson(new TreeAudit{count=trees.Length,placementChanges=moved,prototypesUnchanged=true,instanceAppearanceUnchanged=true},true));
        }
        [Serializable]class TreeAudit{public int count,placementChanges;public bool prototypesUnchanged,instanceAppearanceUnchanged;}
        static string Bright(string name,LookBuilding b)
        {
            if(name.Contains("3a_brick"))return LookPalette.DefaultHex("mat/brick");
            if(name.Contains("3b_plaster")||name.Contains("3c_concrete")||name.Contains("3d_cinder"))return b!=null?b.wall:LookPalette.DefaultHex("mat/concrete");
            if(name.Contains("4a_")||name.Contains("4b_")||name.Contains("4c_")||name.Contains("4d_"))return b!=null?b.roof_col:LookPalette.DefaultHex("mat/roof/_default");
            if(name.Contains("5a_")||name.Contains("5b_"))return b!=null&&b.style=="rural_wood"?b.wall:LookPalette.DefaultHex("mat/wood");
            if(name.Contains("1a_grass"))return "#7D9A52";if(name.Contains("1b_dirt"))return LookPalette.DefaultHex("mat/road/dirt");
            if(name.Contains("1c_beach"))return "#E6D6A8";if(name.Contains("1d_gravel"))return "#9A907A";if(name.Contains("1e_mud"))return "#6E7A4B";
            if(name.Contains("2b_sidewalk"))return LookPalette.DefaultHex("mat/sidewalk/"+(b!=null?b.district:"_default"));
            if(name.Contains("2c_cobble"))return LookPalette.DefaultHex("mat/ground/cobble");return null;
        }
        static Material Surface(Material original,string hex)
        {
            string key="V19_"+original.name+"_"+hex.TrimStart('#');if(variants.TryGetValue(key,out var m))return m;
            m=new Material(original){name=key,shader=Shader.Find("OnlyVolunteers/StyleV3/Palette19")};m.SetTexture("_DistrictMask",field);m.SetVector("_DistrictWorld",world);m.SetColor("_BrightColor",V19PaletteP2.C(hex));m.SetFloat("_PaletteGrass",0);
            AssetDatabase.CreateAsset(m,Output+"/Materials/"+key+".mat");variants[key]=m;return m;
        }
        static void BakeAmbience(UnityEngine.SceneManagement.Scene target)
        {
            var src=AssetDatabase.LoadAssetAtPath<AmbienceData>("Assets/OnlyVolunteers/Audio/Resources/Ambience_v19.asset");var data=Object.Instantiate(src);data.name="Ambience_v19_full_v07";
            foreach(var spot in data.Spots)spot.Position=Relocate(spot.Position);
            foreach(var district in data.Districts)
            {
                var full=(Dictionary<string,object>)V3Json.Parse(File.ReadAllText("ArtSource/References/Map/MAP_PLAN_R01_v19_build_v07.json"));
                var row=V19Infill.List(full,"districts").Cast<Dictionary<string,object>>().First(d=>(string)d["id"]==district.Id);
                var ring=Ring(row["polygon_m"]);district.Polygon=Enumerable.Range(0,ring.Length/2).Select(i=>new Vector2(ring[i*2],ring[i*2+1])).ToArray();
            }
            data.WaterOverride=AssetDatabase.LoadAssetAtPath<WaterData>(V3WaterAudio17.AssetPath("v19"));
            AssetDatabase.CreateAsset(data,"Assets/OnlyVolunteers/Audio/Resources/Ambience_v19_full_v07.asset");
            var go=new GameObject("Ambience_v19_full_v01");UnityEngine.SceneManagement.SceneManager.MoveGameObjectToScene(go,target);go.AddComponent<AmbiencePlayer>().SceneData=data;
        }
    }
}
