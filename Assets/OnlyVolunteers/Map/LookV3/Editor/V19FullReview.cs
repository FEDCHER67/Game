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
    public static class V19FullReview
    {
        public static string CaptureFog(string label,string only="")
        {
            var ground=Object.FindAnyObjectByType<MapHeightSampler>();var fog=Object.FindAnyObjectByType<DistrictFog19V05>();fog.reviewTime=12;int count=0;
            try{foreach(var p in V19PilotTools.LoadPoses("palette_fog_poses_v03.json"))
            {
                if(only!=""&&p.Name!=only)continue;string path=V19PilotTools.OutDir+"/"+label+p.Name+".png";if(File.Exists(path))continue;
                float y=float.IsNaN(p.SurfaceY)?ground.Height(p.X,p.Z)+p.Above:p.SurfaceY;
                V19PilotTools.Render(path,new Vector3(p.X,y+V19PilotTools.WalkEye,p.Z),Quaternion.Euler(p.Pitch,p.Yaw,0),p.Fov>0?p.Fov:75,460,1920,1080,false,0,true);count++;
            }}finally{fog.reviewTime=-1;}return count+" fog poses captured";
        }
        public static string FinishGameplay()
        {
            if(EditorApplication.isPlaying)throw new InvalidOperationException("Stop Play first");
            typeof(OnlyVolunteers.Clinic.ClinicLoopSetup).GetMethod("Add",System.Reflection.BindingFlags.NonPublic|System.Reflection.BindingFlags.Static).Invoke(null,null);
            var fog=Object.FindAnyObjectByType<DistrictFog19V05>();var van=Object.FindAnyObjectByType<OnlyVolunteers.Vehicles.VanController>();
            fog.vanHeadlights=van.GetComponentsInChildren<Light>(true).Where(l=>l.type==LightType.Spot).ToArray();
            if(fog.vanHeadlights.Length==0)
            {
                var lamps=new List<Light>();var halos=fog.halos.Where(h=>Vector2.Distance(new Vector2(h.position.x,h.position.z),new Vector2(van.transform.position.x,van.transform.position.z))>5).ToList();
                float nose=2.4f;var body=van.GetComponentsInChildren<MeshFilter>().FirstOrDefault(m=>m.name=="VAN_Body");
                if(body)nose=body.sharedMesh.vertices.Max(p=>van.transform.InverseTransformPoint(body.transform.TransformPoint(p)).z)+.04f;
                foreach(float side in new[]{-.71f,.71f})
                {var go=new GameObject("V19_MistHeadlamp");go.transform.SetParent(van.transform,false);go.transform.localPosition=new Vector3(side,.86f,nose);go.transform.localRotation=Quaternion.Euler(5,0,0);var l=go.AddComponent<Light>();l.type=LightType.Spot;l.range=26;l.spotAngle=62;l.innerSpotAngle=30;l.intensity=0;l.color=new Color(.92f,.91f,.82f);l.shadows=LightShadows.None;lamps.Add(l);halos.Add(new(){light=l,size=1.7f,colour=new Color(.92f,.91f,.82f,.30f)});}
                fog.vanHeadlights=lamps.ToArray();fog.halos=halos.ToArray();
            }
            EditorSceneManager.MarkSceneDirty(van.gameObject.scene);EditorSceneManager.SaveScene(van.gameObject.scene);return "Clinic loop added; fog headlight references="+fog.vanHeadlights.Length;
        }
        public static string TerrainAudit(string revision="v03")
        {
            var ground=Object.FindAnyObjectByType<MapHeightSampler>();var target=ground.gameObject.scene;
            var before=EditorSceneManager.OpenScene("Assets/OnlyVolunteers/Scenes/Map/Map_Look_v18_Play.unity",OpenSceneMode.Additive);
            UnityEngine.SceneManagement.SceneManager.SetActiveScene(target);
            var old=before.GetRootGameObjects().SelectMany(g=>g.GetComponentsInChildren<Terrain>()).First();
            var td=ground.Terrain.terrainData;var oldData=old.terrainData;float max=0,min=0;int changed=0;
            var text=new System.Text.StringBuilder("v19 terrain versus immutable v18; world-space samples; metres\n");
            foreach(var box in new[]{new Vector4(130,380,390,607),new Vector4(390,530,554,662),new Vector4(548,545,825,710)})
            {
                float low=999,high=-999;Vector2 atLow=default,atHigh=default;
                for(float z=box.y;z<=box.w;z+=1)for(float x=box.x;x<=box.z;x+=1)
                {float delta=ground.Height(x,z)-(old.SampleHeight(new Vector3(x,0,z))+old.transform.position.y);if(Mathf.Abs(delta)>.05f)changed++;if(delta<low){low=delta;atLow=new(x,z);}if(delta>high){high=delta;atHigh=new(x,z);}min=Mathf.Min(min,delta);max=Mathf.Max(max,delta);}
                text.AppendLine(FormattableString.Invariant($"box {box}: min delta {low:F3} at {atLow}, max {high:F3} at {atHigh}"));
            }
            foreach(Dictionary<string,object> hill in V19Infill.List(V19Infill.Data(),"hills"))
            {float x=V19Infill.N(hill,"x"),z=V19Infill.N(hill,"z"),y=ground.Height(x,z),baseline=old.SampleHeight(new Vector3(x,0,z))+old.transform.position.y;text.AppendLine(FormattableString.Invariant($"{hill["id"]}: design {hill["height_m"]}m, centre worldY={y:F3}, centre delta={y-baseline:F3}"));}
            EditorSceneManager.CloseScene(before,true);UnityEngine.SceneManagement.SceneManager.SetActiveScene(target);
            text.AppendLine(V19PilotTools.GroundStats("Hamlet",130,380,390,607,2));text.AppendLine(V19PilotTools.GroundStats("road",390,530,554,662,2));text.AppendLine(V19PilotTools.GroundStats("Rough",548,545,825,710,2));
            string path=V19PilotTools.OutDir+"/terrain_full_"+revision+".txt";if(File.Exists(path))throw new IOException("Audit exists");File.WriteAllText(path,text.ToString());return text.ToString();
        }
    }
}
