using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using OnlyVolunteers.Map.Crowd;
using OnlyVolunteers.Audio;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;
using UnityEditor;
using UnityEditor.SceneManagement;
using Object=UnityEngine.Object;

namespace OnlyVolunteers.Map.Look.V3
{
    public static class V19PaletteP2
    {
        public const string Kit="Assets/OnlyVolunteers/Art/StyleKit_v3/PilotKit_v02";
        public const string Output=V19PaletteTest.Root+"/Test_v02";
        public const string Scene="Assets/OnlyVolunteers/Scenes/Map/Map_Look_v19_Palette_v02.unity";
        public static Color C(string hex) {ColorUtility.TryParseHtmlString(hex,out var c);return c;}
        static float F(object x)=>Convert.ToSingle(x);
        static Vector3 V(object x) {var a=(List<object>)x;return new Vector3(F(a[0]),F(a[1]),F(a[2]));}
        static Vector3 ConvertAxes(Vector3 v)=>new(v.x,v.z,v.y);

        public static string ImportKit()
        {
            var doc=(Dictionary<string,object>)MiniJson.Parse(File.ReadAllText(Kit+"/validation_v02.json"));
            var assets=(Dictionary<string,object>)doc["assets"];
            LookAssetStore.EnsureFolder(Kit+"/Prefabs");LookAssetStore.EnsureFolder(Kit+"/Materials");
            var ti=(TextureImporter)AssetImporter.GetAtPath(Kit+"/Pilot_Palette_v07_v02.png");
            ti.isReadable=true;ti.filterMode=FilterMode.Point;ti.mipmapEnabled=true;ti.alphaSource=TextureImporterAlphaSource.FromInput;ti.SaveAndReimport();
            var source=AssetDatabase.LoadAssetAtPath<Texture2D>(Kit+"/Pilot_Palette_v07_v02.png");
            var bright=new Texture2D(256,256,TextureFormat.RGBA32,true){name="Pilot_Hamlet_v19_v02",filterMode=FilterMode.Point,wrapMode=TextureWrapMode.Clamp};
            string[] hex={"#E1C9A6","#BC7451","#B7B4A6","#8B9C9A","#343D40","#A8855E","#64849B","#697980","#DBC984","#665044","#819FAD","#B8613F","#749B54","#ABAA91","#7B9457"};
            var pixels=source.GetPixels();
            for(int y=0;y<256;y++)for(int x=0;x<256;x++)
            {int n=y<16 ? x/16:2;Color a=pixels[y*256+x];if(n<hex.Length){var b=Color.Lerp(a,C(hex[n]),.8f);b.a=a.a;pixels[y*256+x]=b;}}
            bright.SetPixels(pixels);bright.Apply();AssetDatabase.CreateAsset(bright,Kit+"/Materials/Pilot_Hamlet_v19_v02.asset");
            var materials=new Material[8];var roles=((List<object>)doc["material_roles"]).Select(a=>(string)a).ToArray();
            for(int i=0;i<8;i++)
            {
                var mat=new Material(Shader.Find("Universal Render Pipeline/Lit")){name="P19_"+roles[i]};
                mat.SetTexture("_BaseMap",bright);mat.SetFloat("_Smoothness",i==6?.28f:.12f);mat.SetColor("_BaseColor",Color.white);
                AssetDatabase.CreateAsset(mat,Kit+"/Materials/"+mat.name+".mat");materials[i]=mat;
            }
            var audit=new List<string>();
            foreach(var pair in assets)
            {
                string path=Kit+"/"+pair.Key+"_v02.fbx";
                var m=(ModelImporter)AssetImporter.GetAtPath(path);
                m.globalScale=1;m.useFileScale=true;m.bakeAxisConversion=true;m.importAnimation=false;m.animationType=ModelImporterAnimationType.None;
                m.importCameras=false;m.importLights=false;m.importBlendShapes=false;m.importVisibility=false;m.addCollider=false;m.isReadable=true;
                m.meshCompression=ModelImporterMeshCompression.Off;m.importNormals=ModelImporterNormals.Import;m.importTangents=ModelImporterTangents.None;
                m.materialImportMode=ModelImporterMaterialImportMode.ImportStandard;m.materialLocation=ModelImporterMaterialLocation.InPrefab;m.SaveAndReimport();
                var root=new GameObject(pair.Key+"_v02");
                var model=(GameObject)PrefabUtility.InstantiatePrefab(AssetDatabase.LoadAssetAtPath<GameObject>(path));model.transform.SetParent(root.transform,false);
                foreach(var r in model.GetComponentsInChildren<MeshRenderer>())r.sharedMaterials=materials;
                var a=(Dictionary<string,object>)pair.Value;
                Matrix4x4 basis=Matrix4x4.identity;basis.SetColumn(1,new Vector4(0,0,1,0));basis.SetColumn(2,new Vector4(0,1,0,0));
                foreach(Dictionary<string,object> col in (List<object>)a["colliders"])
                {
                    var boxGo=new GameObject((string)col["id"]+"_"+col["name"]);boxGo.transform.SetParent(root.transform,false);
                    boxGo.transform.localPosition=ConvertAxes(V(col["center_m"]));
                    var q=(List<object>)col["rotation_quaternion_xyzw"];
                    var rot=basis*Matrix4x4.Rotate(new Quaternion(F(q[0]),F(q[1]),F(q[2]),F(q[3])))*basis.inverse;
                    boxGo.transform.localRotation=Quaternion.LookRotation(rot.GetColumn(2),rot.GetColumn(1));
                    boxGo.AddComponent<BoxCollider>().size=ConvertAxes(V(col["size_m"]));
                }
                var rs=root.GetComponentsInChildren<MeshRenderer>();Bounds bb=rs[0].bounds;foreach(var r in rs.Skip(1))bb.Encapsulate(r.bounds);
                Vector3 expected=ConvertAxes(V(a["size_m"]));float error=(bb.size-expected).magnitude;
                if(error>.002f)throw new InvalidDataException(pair.Key+" axis/scale mismatch "+error);
                string prefab=Kit+"/Prefabs/"+pair.Key+"_v02.prefab";
                if(File.Exists(prefab))throw new IOException("Existing kit prefab "+prefab);
                PrefabUtility.SaveAsPrefabAsset(root,prefab);Object.DestroyImmediate(root);
                audit.Add(pair.Key+" PASS size_error_m="+error.ToString("F7")+" boxes="+((List<object>)a["colliders"]).Count);
            }
            string decal="Assets/OnlyVolunteers/Art/StyleKit_v3/decals_v02/GRAFFITI_TORN_POSTERS_v02.png";
            var dt=(TextureImporter)AssetImporter.GetAtPath(decal);dt.alphaIsTransparency=true;dt.mipmapEnabled=true;dt.wrapMode=TextureWrapMode.Clamp;dt.SaveAndReimport();
            AssetDatabase.SaveAssets();File.WriteAllLines(V19PilotTools.OutDir+"/kit_unity_import_v02.txt",audit);
            return string.Join("\n",audit);
        }

        public static string Build()
        {
            if(AssetDatabase.LoadAssetAtPath<GameObject>(Kit+"/Prefabs/DOGHOUSE_v02.prefab")==null)throw new InvalidOperationException("Import kit first");
            V19PaletteTest.Build(2);
            var old=Object.FindAnyObjectByType<DistrictAtmosphere19>();var districts=old.districts;old.enabled=false;
            var weather=old.gameObject.AddComponent<DistrictWeather19V02>();weather.districts=districts;weather.sun=RenderSettings.sun;
            weather.weather=new DistrictWeather19V02.Weather[districts.Length];
            for(int i=0;i<districts.Length;i++)
            {
                var d=districts[i];
                var w=new DistrictWeather19V02.Weather{zenith=C("#408BCD"),horizon=C("#B4CDDC"),clouds=C("#F8F6EA"),
                    cloudCover=.44f,cloudDensity=1,sunColour=C("#FFF2D9"),sunIntensity=.98f,ambientIntensity=.85f,shadowStrength=.68f};
                switch(d.id)
                {
                    case "village": w.zenith=C("#3188D0");w.cloudCover=.46f;w.sunIntensity=1.10f;w.ambientIntensity=.95f;w.shadowStrength=.72f;break;
                    case "elite":w.zenith=C("#428CD2");w.cloudCover=.20f;w.sunIntensity=1.03f;break;
                    case "fields":w.zenith=C("#6AA2CE");w.cloudCover=.48f;w.sunIntensity=1.02f;break;
                    case "beach":w.zenith=C("#5799D0");w.horizon=C("#D3D9CE");w.cloudCover=.23f;w.sunColour=C("#FFF0D0");w.sunIntensity=1.04f;break;
                    case "old_town":w.zenith=C("#387CCE");w.cloudCover=.39f;w.sunIntensity=1.04f;break;
                    case "transition":w.zenith=C("#94A3AC");w.horizon=C("#C2BDB0");w.cloudCover=.58f;w.sunIntensity=.80f;w.shadowStrength=.4f;break;
                    case "tramduro":w.zenith=C("#7C9FB6");w.horizon=C("#BCCDD2");w.cloudCover=.48f;w.sunIntensity=.82f;break;
                    case "industrial":w.zenith=C("#8096A6");w.horizon=C("#B5C3CA");w.cloudCover=.61f;w.sunColour=C("#DDE6F1");w.sunIntensity=.71f;w.shadowStrength=.38f;break;
                    case "forest":
                        w.zenith=C("#626F6B");w.horizon=C("#A1ADA7");w.clouds=C("#8B9992");w.cloudCover=.94f;w.cloudDensity=1.05f;
                        w.sunColour=C("#D2DED9");w.sunIntensity=.43f;w.ambientIntensity=.70f;w.shadowStrength=.16f;
                        d.fogStart=8;d.fogEnd=70;d.fogColour=w.horizon;d.saturation=-28;d.exposure=.12f;d.temperature=-8;break;
                    case "residential":
                        w.zenith=C("#515E69");w.horizon=C("#9BA7B1");w.clouds=C("#788590");w.cloudCover=.96f;w.cloudDensity=1.08f;
                        w.sunColour=C("#CDD8E5");w.sunIntensity=.38f;w.ambientIntensity=.68f;w.shadowStrength=.10f;
                        d.fogStart=7;d.fogEnd=65;d.fogColour=w.horizon;d.saturation=-58;d.exposure=.08f;d.temperature=-18;d.contrast=-10;break;
                }
                weather.weather[i]=w;
                var volume=GameObject.Find("V19_Light_"+d.id).GetComponent<Volume>();
                volume.sharedProfile.TryGet<ColorAdjustments>(out var ca);ca.postExposure.value=d.exposure;ca.saturation.value=d.saturation;ca.contrast.value=d.contrast;
                volume.sharedProfile.TryGet<WhiteBalance>(out var wb);wb.temperature.value=d.temperature;
                EditorUtility.SetDirty(ca);EditorUtility.SetDirty(wb);EditorUtility.SetDirty(volume.sharedProfile);
            }
            weather.blendVolume=GameObject.Find("V19_Light_between_districts").GetComponent<Volume>();
            weather.skyTemplate=new Material(Shader.Find("OnlyVolunteers/StyleV3/DistrictSky19V02")){name="DistrictSky_v19_v02"};
            AssetDatabase.CreateAsset(weather.skyTemplate,Output+"/DistrictSky_v19_v02.mat");
            ReblendPalette(weather);
            V19PaletteP2Life.Place(weather);
            AssetDatabase.SaveAssets();EditorSceneManager.MarkSceneDirty(UnityEngine.SceneManagement.SceneManager.GetActiveScene());
            EditorSceneManager.SaveScene(UnityEngine.SceneManagement.SceneManager.GetActiveScene());
            return Scene+"; v02 district skies, fog, palette field, garden, Rough details and life";
        }

        static void ReblendPalette(DistrictWeather19V02 weather)
        {
            var terrain=Terrain.activeTerrain;var data=terrain.terrainData;var bounds=weather.districts.Select(d=>d.bounds).ToArray();var weights=new float[bounds.Length];
            float T(float x,float z)
            {DistrictBlend19.Weights(bounds,new Vector2(x,z),60,weights);float value=0;for(int i=0;i<weights.Length;i++)value+=weights[i]*weather.districts[i].palette;return value;}
            var mask=AssetDatabase.LoadAssetAtPath<Texture2D>(Output+"/Palette_Field_v19.asset");var px=mask.GetPixels();
            for(int z=0;z<mask.height;z++)for(int x=0;x<mask.width;x++)px[z*mask.width+x]=new Color(T(terrain.transform.position.x+(x+.5f)/mask.width*data.size.x,terrain.transform.position.z+(z+.5f)/mask.height*data.size.z),0,0,1);
            mask.SetPixels(px);mask.Apply();EditorUtility.SetDirty(mask);
            int w=data.alphamapWidth,h=data.alphamapHeight,n=data.terrainLayers.Length/2;var a=data.GetAlphamaps(0,0,w,h);
            for(int z=0;z<h;z++)for(int x=0;x<w;x++)
            {float t=T(terrain.transform.position.x+(float)x/(w-1)*data.size.x,terrain.transform.position.z+(float)z/(h-1)*data.size.z);for(int k=0;k<n;k++){float sum=a[z,x,k]+a[z,x,k+n];a[z,x,k]=sum*(1-t);a[z,x,k+n]=sum*t;}}
            data.SetAlphamaps(0,0,a);EditorUtility.SetDirty(data);AssetDatabase.SaveAssetIfDirty(data);
        }

        public static string Capture(string label,string poses="palette_poses_v02.json")
        {
            var sampler=Object.FindAnyObjectByType<MapHeightSampler>();int count=0;
            foreach(var p in V19PilotTools.LoadPoses(poses))
            {
                string path=V19PilotTools.OutDir+"/"+label+p.Name+".png";if(File.Exists(path))continue;
                float y=float.IsNaN(p.SurfaceY)?sampler.Height(p.X,p.Z)+p.Above:p.SurfaceY;
                V19PilotTools.Render(path,new Vector3(p.X,y+V19PilotTools.WalkEye,p.Z),Quaternion.Euler(p.Pitch,p.Yaw,0),p.Fov>0?p.Fov:75,460,1920,1080,false,0,true);count++;
            }
            return count+" captured: "+label;
        }
    }
}
