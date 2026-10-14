using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;
using UnityEngine;
using UnityEditor;
using UnityEditor.SceneManagement;
using Object=UnityEngine.Object;

namespace OnlyVolunteers.Map.Look.V3
{
    public static class V19FinalGeometry
    {
        const string Folder=V19FullPalette.Output+"/Finish_v03";
        const string FenceId="02_v18_plotfence_02_ground_02_1_1";
        static float Hill(float x,float z){float r=Vector2.Distance(new Vector2(x,z),new Vector2(438,638))/22;return r>=1?0:11.8f*.5f*(1+Mathf.Cos(r*Mathf.PI));}
        public static string Apply()
        {
            if(EditorApplication.isPlaying)throw new InvalidOperationException("Stop Play first");
            var ground=Object.FindAnyObjectByType<MapHeightSampler>();var terrain=ground.Terrain;LookAssetStore.EnsureFolder(Folder);
            var td=AssetDatabase.LoadAssetAtPath<TerrainData>(Folder+"/Terrain_finish_v03.asset");
            if(!td)
            {
                td=Object.Instantiate(terrain.terrainData);td.name="Terrain_v19_finish_v03";var h=td.GetHeights(0,0,td.heightmapResolution,td.heightmapResolution);int n=td.heightmapResolution;
                for(int z=0;z<n;z++)for(int x=0;x<n;x++)h[z,x]+=Hill(terrain.transform.position.x+x*td.size.x/(n-1),terrain.transform.position.z+z*td.size.z/(n-1))/td.size.y;
                td.SetHeights(0,0,h);AssetDatabase.CreateAsset(td,Folder+"/Terrain_finish_v03.asset");
                var trees=td.treeInstances;for(int i=0;i<trees.Length;i++){var p=Vector3.Scale(trees[i].position,td.size)+terrain.transform.position;trees[i].position.y=(td.GetInterpolatedHeight(trees[i].position.x,trees[i].position.z))/td.size.y;}
                td.SetTreeInstances(trees,false);EditorUtility.SetDirty(td);AssetDatabase.SaveAssetIfDirty(td);
            }
            terrain.terrainData=td;terrain.GetComponent<TerrainCollider>().terrainData=td;
            var fog=Object.FindAnyObjectByType<DistrictFog19V05>();var field=AssetDatabase.LoadAssetAtPath<Texture2D>(Folder+"/GroundHeights_finish_v03.asset");
            if(!field)
            {
                field=new Texture2D(256,256,TextureFormat.RFloat,false,true){name="TerrainHeights_finish_v03",wrapMode=TextureWrapMode.Clamp,filterMode=FilterMode.Bilinear};var colours=new Color[256*256];
                for(int z=0;z<256;z++)for(int x=0;x<256;x++)colours[z*256+x]=new Color(td.GetInterpolatedHeight(x/255f,z/255f)+terrain.transform.position.y,0,0,1);
                field.SetPixels(colours);field.Apply();AssetDatabase.CreateAsset(field,Folder+"/GroundHeights_finish_v03.asset");
            }
            fog.groundHeights=field;
            int count=0;var proxyRoot=GameObject.Find("V19_Happykeys_TrunkProxies");
            if(!proxyRoot)
            {
                proxyRoot=new GameObject("V19_Happykeys_TrunkProxies");
                foreach(var tree in td.treeInstances)
                {
                    var prefab=td.treePrototypes[tree.prototypeIndex].prefab;if(!prefab.name.StartsWith("TREE_BARE_0"))continue;
                    var holder=new GameObject("Trunk_"+prefab.name);holder.transform.SetParent(proxyRoot.transform,false);holder.transform.position=Vector3.Scale(tree.position,td.size)+terrain.transform.position;
                    holder.transform.rotation=Quaternion.Euler(0,tree.rotation*Mathf.Rad2Deg,0);holder.transform.localScale=new Vector3(tree.widthScale,tree.heightScale,tree.widthScale);holder.isStatic=true;
                    foreach(var src in prefab.GetComponentsInChildren<CapsuleCollider>())
                    {
                        var go=new GameObject(src.name);go.transform.SetParent(holder.transform,false);go.transform.localPosition=src.transform.localPosition;go.transform.localRotation=src.transform.localRotation;go.transform.localScale=src.transform.localScale;
                        var c=go.AddComponent<CapsuleCollider>();c.center=src.center;c.radius=src.radius;c.height=src.height;c.direction=src.direction;go.isStatic=true;count++;
                    }
                }
            }
            else count=proxyRoot.GetComponentsInChildren<Collider>().Length;
            var gate=AssetDatabase.LoadAssetAtPath<GameObject>(Folder+"/OrchardGate_v03.prefab");
            if(!gate)
            {
                var prior=GameObject.Find("Fence_"+FenceId);var colours=prior.GetComponent<MeshRenderer>().sharedMaterials;
                V3LookData.Load("v19");var f=V3LookData.Fences.First(f=>f.Id==FenceId);var query=new Vector2(196.26f,506.57f);Vector2 nearest=query;float best=999;
                for(int i=1;i<f.Line.Count;i++){var a=f.Line[i-1];var d=f.Line[i]-a;var p=a+d*Mathf.Clamp01(Vector2.Dot(query-a,d)/d.sqrMagnitude);if(Vector2.Distance(query,p)<best){best=Vector2.Distance(query,p);nearest=p;}}
                f.Gates.Add((nearest,8.6f));V3LookData.Fences=new List<V3LookData.Fence>{f};
                var data=MapLookBuilder.Load("v19");var hm=new HeightModel(data,td.heightmapResolution);var hh=td.GetHeights(0,0,td.heightmapResolution,td.heightmapResolution);hm.Heights=new float[hh.Length];
                for(int z=0;z<td.heightmapResolution;z++)for(int x=0;x<td.heightmapResolution;x++)hm.Heights[z*td.heightmapResolution+x]=terrain.transform.position.y+hh[z,x]*td.size.y;
                MapLookBuilderV3.Current="v19";var store=new V3Store("G18_OrchardGate_v03");store.Reset();var holder=new GameObject("V19_OrchardGate_v03");V3Ground.Fences(hm,store,holder.transform,new List<string>());
                foreach(var r in holder.GetComponentsInChildren<MeshRenderer>())r.sharedMaterials=colours;
                AssetDatabase.SaveAssets();gate=PrefabUtility.SaveAsPrefabAsset(holder,Folder+"/OrchardGate_v03.prefab");Object.DestroyImmediate(holder);MapLookBuilderV3.Current="v16";
            }
            if(!GameObject.Find("V19_OrchardGate_v03"))
            {var prior=GameObject.Find("Fence_"+FenceId);if(prior)Object.DestroyImmediate(prior);var instance=(GameObject)PrefabUtility.InstantiatePrefab(gate);instance.name="V19_OrchardGate_v03";}
            Physics.SyncTransforms();EditorSceneManager.MarkSceneDirty(terrain.gameObject.scene);EditorSceneManager.SaveScene(terrain.gameObject.scene);
            return "finish v03: isolated 11.8m rise; "+count+" explicit manifest trunk capsules; visible orchard gate 8.6m";
        }
    }
}
