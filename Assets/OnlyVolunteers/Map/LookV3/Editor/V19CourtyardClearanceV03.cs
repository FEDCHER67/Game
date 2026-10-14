using System;
using UnityEngine;
using UnityEditor;
using UnityEditor.SceneManagement;
using Object=UnityEngine.Object;

namespace OnlyVolunteers.Map.Look.V3
{
    public static class V19CourtyardClearanceV03
    {
        public static string Apply()
        {
            if(EditorApplication.isPlaying)throw new InvalidOperationException("Stop Play first");
            var root=GameObject.Find("V19_R1_CourtyardFinish_v02");
            if(!root)throw new InvalidOperationException("Apply ReviewFinish v02 first");
            if(root.transform.Find("Clearance_v03"))return "courtyard clearance v03 already applied";
            var ground=Object.FindAnyObjectByType<MapHeightSampler>();int moved=0;
            foreach(Transform child in root.transform)
            {
                if(!child.name.StartsWith("R1_GARDEN_BED")&&!child.name.StartsWith("R1_FENCE_PICKET"))continue;
                var p=child.position;p.x+=8;p.y=ground.Height(p.x,p.z);child.position=p;moved++;
            }
            foreach(var child in Object.FindObjectsByType<Transform>(FindObjectsSortMode.None))
                if(child.name.StartsWith("V19_R1_K1_BENCH"))child.position=new Vector3(695,ground.Height(695,599),599);
            var soil=root.transform.Find("GardenWorkSoil").GetComponent<MeshFilter>();
            string path=V19ReviewFinishV02.Folder+"/GardenWorkSoil_v03.asset";
            var mesh=AssetDatabase.LoadAssetAtPath<Mesh>(path);
            if(!mesh)
            {
                mesh=Object.Instantiate(soil.sharedMesh);mesh.name="GardenWorkSoil_v03";
                var vertices=mesh.vertices;
                for(int i=0;i<vertices.Length;i++){var p=vertices[i];p.x+=8;p.y=ground.Height(p.x,p.z)+.035f;vertices[i]=p;}
                mesh.vertices=vertices;mesh.RecalculateNormals();mesh.RecalculateBounds();AssetDatabase.CreateAsset(mesh,path);
            }
            soil.sharedMesh=mesh;
            new GameObject("Clearance_v03").transform.SetParent(root.transform,false);
            Physics.SyncTransforms();EditorSceneManager.MarkSceneDirty(root.scene);EditorSceneManager.SaveScene(root.scene);AssetDatabase.SaveAssets();
            return "Moved "+moved+" garden/fence anchors 8m east, refitted soil, and moved bench to the drying-yard edge; original playground route retained";
        }
    }
}
