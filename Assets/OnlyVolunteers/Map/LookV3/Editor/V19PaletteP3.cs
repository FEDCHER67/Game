using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;
using UnityEditor;
using UnityEditor.SceneManagement;
using Object=UnityEngine.Object;

namespace OnlyVolunteers.Map.Look.V3
{
    public static class V19PaletteP3
    {
        public const string Output=V19PaletteTest.Root+"/Test_v03";
        public const string Scene="Assets/OnlyVolunteers/Scenes/Map/Map_Look_v19_Palette_v03.unity";
        static string Review=>V19PilotTools.OutDir;
        public static string Build()
        {
            if(EditorApplication.isPlaying)throw new InvalidOperationException("Stop Play first");
            if(File.Exists(Scene)||Directory.Exists(Output))throw new IOException("v03 exists; use saved scene for review");
            EditorSceneManager.OpenScene(V19PaletteP2.Scene,OpenSceneMode.Single);
            LookAssetStore.EnsureFolder(Output);
            var old=Object.FindAnyObjectByType<DistrictWeather19V02>();old.enabled=false;
            var weather=old.gameObject.AddComponent<DistrictWeather19V03>();
            weather.districts=old.districts;
            weather.weather=old.weather.Select(w=>JsonUtility.FromJson<DistrictWeather19V03.Weather>(JsonUtility.ToJson(w))).ToArray();
            weather.skyTemplate=old.skyTemplate;weather.sun=old.sun;weather.blendVolume=old.blendVolume;weather.blendMetres=old.blendMetres;
            var fog=old.gameObject.AddComponent<DistrictFog19V03>();fog.enabled=false;weather.visibleFog=fog;
            var original=(UniversalRenderPipelineAsset)QualitySettings.renderPipeline;
            fog.baselinePipeline=original;
            AssetDatabase.CopyAsset(AssetDatabase.GetAssetPath(original),Output+"/PC_FogPipeline_v19.asset");
            fog.pipeline=AssetDatabase.LoadAssetAtPath<UniversalRenderPipelineAsset>(Output+"/PC_FogPipeline_v19.asset");
            var rp=new SerializedObject(fog.pipeline);var list=rp.FindProperty("m_RendererDataList");
            int index=rp.FindProperty("m_DefaultRendererIndex").intValue;
            var source=(ScriptableRendererData)list.GetArrayElementAtIndex(index).objectReferenceValue;
            AssetDatabase.CopyAsset(AssetDatabase.GetAssetPath(source),Output+"/PC_FogRenderer_v19.asset");
            var renderer=AssetDatabase.LoadAssetAtPath<ScriptableRendererData>(Output+"/PC_FogRenderer_v19.asset");
            list.GetArrayElementAtIndex(index).objectReferenceValue=renderer;rp.ApplyModifiedPropertiesWithoutUndo();
            fog.fogTemplate=new Material(Shader.Find("OnlyVolunteers/StyleV3/DistrictFog19V03")){name="DepthHeightFog_v19_v03"};
            AssetDatabase.CreateAsset(fog.fogTemplate,Output+"/DepthHeightFog.mat");
            fog.mistTemplate=new Material(Shader.Find("OnlyVolunteers/StyleV3/MistSoft19V03")){name="SoftMist_v19_v03"};
            fog.mistTemplate.SetFloat("_DepthFade",2.2f);AssetDatabase.CreateAsset(fog.mistTemplate,Output+"/SoftMist.mat");
            fog.haloTemplate=new Material(fog.mistTemplate){name="LightScatter_v19_v03"};
            fog.haloTemplate.SetFloat("_Glow",1);fog.haloTemplate.SetFloat("_DepthFade",.18f);AssetDatabase.CreateAsset(fog.haloTemplate,Output+"/LightScatter.mat");
            fog.feature=ScriptableObject.CreateInstance<FullScreenPassRendererFeature>();fog.feature.name="V19_DepthHeightFog_PC";
            fog.feature.injectionPoint=FullScreenPassRendererFeature.InjectionPoint.BeforeRenderingTransparents;
            fog.feature.fetchColorBuffer=false;fog.feature.requirements=ScriptableRenderPassInput.Depth;fog.feature.passMaterial=fog.fogTemplate;
            AssetDatabase.AddObjectToAsset(fog.feature,renderer);renderer.rendererFeatures.Add(fog.feature);
            var rd=new SerializedObject(renderer);var map=rd.FindProperty("m_RendererFeatureMap");map.arraySize=renderer.rendererFeatures.Count;
            for(int i=0;i<map.arraySize;i++){AssetDatabase.TryGetGUIDAndLocalFileIdentifier(renderer.rendererFeatures[i],out string guid,out long id);map.GetArrayElementAtIndex(i).longValue=id;}
            rd.ApplyModifiedPropertiesWithoutUndo();renderer.SetDirty();EditorUtility.SetDirty(renderer);EditorUtility.SetDirty(fog.feature);
            var terrain=Terrain.activeTerrain;
            AssetDatabase.CopyAsset(AssetDatabase.GetAssetPath(terrain.terrainData),Output+"/Terrain_fog_v03.asset");
            terrain.terrainData=AssetDatabase.LoadAssetAtPath<TerrainData>(Output+"/Terrain_fog_v03.asset");
            terrain.GetComponent<TerrainCollider>().terrainData=terrain.terrainData;
            fog.terrainWorld=new Vector4(terrain.transform.position.x,terrain.transform.position.z,terrain.terrainData.size.x,terrain.terrainData.size.z);
            var heights=new Texture2D(256,256,TextureFormat.RFloat,false,true){name="TerrainWorldHeights_v19_v03",wrapMode=TextureWrapMode.Clamp,filterMode=FilterMode.Bilinear};
            var pixels=new Color[256*256];for(int z=0;z<256;z++)for(int x=0;x<256;x++)
                pixels[z*256+x]=new Color(terrain.terrainData.GetInterpolatedHeight(x/255f,z/255f)+terrain.transform.position.y,0,0,1);
            heights.SetPixels(pixels);heights.Apply();AssetDatabase.CreateAsset(heights,Output+"/TerrainWorldHeights.asset");fog.groundHeights=heights;
            string audit="{\"trees_unchanged_from_v02\":true,\"tree_models_deferred\":true}";PlaceMist(fog);
            AssetDatabase.SaveAssetIfDirty(terrain.terrainData);AssetDatabase.SaveAssetIfDirty(renderer);AssetDatabase.SaveAssetIfDirty(fog.pipeline);
            AssetDatabase.SaveAssetIfDirty(fog.feature);
            fog.enabled=true;
            EditorSceneManager.SaveScene(UnityEngine.SceneManagement.SceneManager.GetActiveScene(),Scene);
            File.WriteAllText(Review+"/fog_tree_audit_v03.json",audit);
            return Scene+"; "+CompleteLighting()+"; tree audit saved";
        }
        static void PlaceMist(DistrictFog19V03 fog)
        {
            var sampler=Object.FindAnyObjectByType<MapHeightSampler>();float Y(float x,float z)=>sampler.Height(x,z);
            var locations=new[]{new Vector2(570,630),new(590,596),new(610,596),new(625,617),new(647,648),new(664,651),new(683,653),new(704,653),new(718,632),new(716,671),new(753,623),new(681,688),new(520,620),new(490,609),new(255,208),new(272,223),new(243,197),new(285,240)};
            fog.banks=locations.Select((p,i)=>new DistrictFog19V03.Bank{position=new Vector3(p.x,Y(p.x,p.y)+1.7f+(i%3)*.45f,p.y),size=new Vector2(12+(i%4)*3,3+(i%3)*.7f),phase=i*1.74f,forest=i>=14}).ToArray();
            var halos=new List<DistrictFog19V03.Halo>();
            foreach(var light in Object.FindObjectsByType<Light>())
                if(light.type!=LightType.Directional && light.gameObject.name=="Flicker")halos.Add(new(){light=light,size=2.3f,colour=new Color(.78f,.86f,.91f,.36f)});
            // Extract actual emissive lamp heads from merged street props, preserving their placement.
            foreach(var r in Object.FindObjectsByType<MeshRenderer>())
            {
                var filter=r.GetComponent<MeshFilter>();if(!filter || !filter.sharedMesh)continue;
                var mats=r.sharedMaterials;var mesh=filter.sharedMesh;
                for(int s=0;s<Mathf.Min(mats.Length,mesh.subMeshCount);s++)
                {
                    if(!mats[s] || !mats[s].name.Contains("Lamp_Glow"))continue;
                    var verts=mesh.vertices;var groups=new Dictionary<Vector2Int,List<Vector3>>();
                    foreach(int v in mesh.GetTriangles(s))
                    {
                        Vector3 p=r.transform.TransformPoint(verts[v]);if(p.x<520||p.x>855||p.z<530||p.z>735)continue;
                        var k=new Vector2Int(Mathf.RoundToInt(p.x/2),Mathf.RoundToInt(p.z/2));
                        if(!groups.ContainsKey(k))groups[k]=new();groups[k].Add(p);
                    }
                    foreach(var g in groups.Values)
                    {
                        Vector3 p=g.Aggregate(Vector3.zero,(a,b)=>a+b)/g.Count;
                        if(halos.Any(h=>Vector3.Distance(h.light?h.light.transform.position:h.position,p)<1.8f))continue;
                        if(halos.Count<26)halos.Add(new(){position=p,size=2.1f,colour=new Color(.80f,.86f,.88f,.31f)});
                    }
                }
            }
            // Existing van lights remain controlled by gameplay; halos follow their enabled state.
            var van=GameObject.Find("Van");if(van)foreach(var l in van.GetComponentsInChildren<Light>(true).Where(l=>l.type==LightType.Spot))
                if(halos.Count<32)halos.Add(new(){light=l,size=1.8f,colour=new Color(.91f,.89f,.76f,.3f)});
            fog.halos=halos.ToArray();
        }
        public static string CompleteLighting()
        {
            if(GameObject.Find("V19_FogLightCues_v03"))return "Light cues already placed";
            var fog=Object.FindAnyObjectByType<DistrictFog19V03>();var haloList=fog.halos.ToList();
            var root=new GameObject("V19_FogLightCues_v03");
            AlignLampHalos();
            var glow=new Material(Shader.Find("Universal Render Pipeline/Lit")){name="CoolGarageWindow_v19_v03"};
            glow.SetColor("_BaseColor",new Color(.25f,.31f,.34f));glow.SetColor("_EmissionColor",new Color(.34f,.43f,.46f));
            glow.EnableKeyword("_EMISSION");AssetDatabase.CreateAsset(glow,Output+"/CoolGarageWindow.mat");
            var windows=Object.FindObjectsByType<MeshRenderer>().Where(r=>r.name=="DetailSmall" && r.bounds.center.x>654 && r.bounds.center.x<663 && r.bounds.center.z>661 && r.bounds.center.z<665).OrderBy(r=>r.bounds.center.x).ToArray();int count=0;
            foreach(var r in windows)
            {
                var source=r.GetComponent<MeshFilter>().sharedMesh;var verts=source.vertices;var selected=new List<Vector3>();
                for(int s=0;s<Mathf.Min(source.subMeshCount,r.sharedMaterials.Length);s++)
                {
                    if(!r.sharedMaterials[s] || !r.sharedMaterials[s].name.Contains("glass"))continue;
                    var indices=source.GetTriangles(s);
                    for(int i=0;i<indices.Length;i+=3)
                    {
                        Vector3 a=r.transform.TransformPoint(verts[indices[i]]),b=r.transform.TransformPoint(verts[indices[i+1]]),c=r.transform.TransformPoint(verts[indices[i+2]]);
                        if((a.z+b.z+c.z)/3>660.1f)continue;
                        selected.Add(a-Vector3.forward*.012f);selected.Add(b-Vector3.forward*.012f);selected.Add(c-Vector3.forward*.012f);
                    }
                }
                if(selected.Count==0)continue;
                var mesh=new Mesh{name="ExistingWindowSurface_"+count};mesh.SetVertices(selected);mesh.SetTriangles(Enumerable.Range(0,selected.Count).ToArray(),0);mesh.RecalculateNormals();mesh.RecalculateBounds();
                AssetDatabase.CreateAsset(mesh,Output+"/WindowSurface_"+count+".asset");
                var g=new GameObject("DimGarageWindow_"+count);g.transform.SetParent(root.transform,false);g.AddComponent<MeshFilter>().sharedMesh=mesh;
                var mr=g.AddComponent<MeshRenderer>();mr.sharedMaterial=glow;mr.shadowCastingMode=ShadowCastingMode.Off;
                Vector3 p=mesh.bounds.center-Vector3.forward*.2f;
                haloList.Add(new(){position=p,size=1.8f,colour=new Color(.66f,.78f,.83f,.30f)});count++;
            }
            var van=GameObject.Find("Van");var headlights=new List<Light>();float nose=2.4f;
            if(van)
            {
                var body=van.GetComponentsInChildren<MeshFilter>().FirstOrDefault(m=>m.name=="VAN_Body");
                if(body)nose=body.sharedMesh.vertices.Max(p=>van.transform.InverseTransformPoint(body.transform.TransformPoint(p)).z)+.04f;
            }
            if(van)foreach(float side in new[]{-.71f,.71f})
            {
                var g=new GameObject("V19_MistHeadlamp");g.transform.SetParent(van.transform,false);g.transform.localPosition=new Vector3(side,.86f,nose);g.transform.localRotation=Quaternion.Euler(5,0,0);
                var light=g.AddComponent<Light>();light.type=LightType.Spot;light.range=26;light.spotAngle=62;light.innerSpotAngle=30;light.intensity=0;light.color=new Color(.92f,.91f,.82f);light.shadows=LightShadows.None;
                headlights.Add(light);haloList.Add(new(){light=light,size=1.7f,colour=new Color(.92f,.91f,.82f,.30f)});
            }
            fog.vanHeadlights=headlights.ToArray();fog.halos=haloList.ToArray();
            EditorSceneManager.MarkSceneDirty(UnityEngine.SceneManagement.SceneManager.GetActiveScene());EditorSceneManager.SaveScene(UnityEngine.SceneManagement.SceneManager.GetActiveScene());
            return count+" dim windows; "+headlights.Count+" mist headlamps; "+fog.halos.Length+" halo emitters";
        }
        public static string AlignLampHalos()
        {
            int count=0;
            foreach(var light in Object.FindObjectsByType<Light>().Where(l=>l.name=="Flicker"))
            {
                var r=light.transform.parent.GetComponent<MeshRenderer>();if(!r)continue;
                var mesh=r.GetComponent<MeshFilter>().sharedMesh;var vertices=mesh.vertices;var points=new List<Vector3>();
                for(int s=0;s<Mathf.Min(mesh.subMeshCount,r.sharedMaterials.Length);s++)
                    if(r.sharedMaterials[s] && r.sharedMaterials[s].name=="MP_Glass")
                        points.AddRange(mesh.GetTriangles(s).Select(i=>r.transform.TransformPoint(vertices[i])));
                if(points.Count>0){light.transform.position=points.Aggregate(Vector3.zero,(a,b)=>a+b)/points.Count-Vector3.up*.07f;count++;}
            }
            EditorSceneManager.MarkSceneDirty(UnityEngine.SceneManagement.SceneManager.GetActiveScene());EditorSceneManager.SaveScene(UnityEngine.SceneManagement.SceneManager.GetActiveScene());
            return count+" lamp halos aligned to actual glass bulbs";
        }
        public static string Capture(string label,string only="")
        {
            var sampler=Object.FindAnyObjectByType<MapHeightSampler>();var fog=Object.FindAnyObjectByType<DistrictFog19V03>();fog.reviewTime=12;
            int count=0;try
            {
                foreach(var p in V19PilotTools.LoadPoses("palette_fog_poses_v03.json"))
                {
                    if(!(p.Pilot=="rough" || p.Name.StartsWith("t") || p.Name=="o01_forest"))continue;
                    if(only!="" && p.Name!=only)continue;
                    string path=Review+"/"+label+p.Name+".png";if(File.Exists(path))continue;
                    float y=float.IsNaN(p.SurfaceY)?sampler.Height(p.X,p.Z)+p.Above:p.SurfaceY;
                    V19PilotTools.Render(path,new Vector3(p.X,y+V19PilotTools.WalkEye,p.Z),Quaternion.Euler(p.Pitch,p.Yaw,0),p.Fov>0?p.Fov:75,460,1920,1080,false,0,true);count++;
                }
            }
            finally{fog.reviewTime=-1;}
            return count+" captured: "+label;
        }
    }
}
