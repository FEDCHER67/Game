using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using OnlyVolunteers.Vehicles;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.SceneManagement;
using Object = UnityEngine.Object;

namespace OnlyVolunteers.Map.W85
{
    // Disposable local physics scene: real van / WheelColliders / max upgrades and copies of the current map collisions.
    // Controller's public input contract is used because VanDriveInput reads legacy Input (virtual devices cannot feed it).
    // Never starts the host, changes a save, sends OS keys or touches the human's camera.
    public static class W86RoadDriveCheck
    {
        [Serializable] public class Row { public string id,direction,result,reason; public float progress,length,seconds,maxSpeed,maxDeviation,minUpright; public int steps; }
        [Serializable] public class Report { public string scene,method;public bool startAtMax;public float topSpeed,torque,brakes;public int engine,handling,brakeLevel;public Row[] rows; }
        static string Review => System.IO.Path.GetFullPath(Application.dataPath+"/../Working/Reviews/W86Polish_2026-10-25/G46");
        static Scene sandbox;
        static PhysicsScene physics;
        static VanController van;
        static Rigidbody body;
        static MethodInfo tick;
        static List<W86RoadRepair.Route> routes;
        static List<Row> rows;
        static int index,direction;
        static float seconds,progress,bestProgress,stuck,spawnOffset,minS,endS;
        static Row current;
        static Report report;
        public static bool Running {get;private set;}
        public static string Status => Running?$"{index+1}/{routes.Count} {current.id} {current.direction} {progress:0}/{endS:0}m t={seconds:0}s":$"stopped, {rows?.Count ?? 0} results";
        public static string Start(string filter = null)
        {
            if(Running)throw new InvalidOperationException("G46 drive already running");
            if(EditorApplication.isPlaying)throw new InvalidOperationException("G46 uses an isolated edit-mode physics scene");
            var source=SceneManager.GetActiveScene();
            var original=source.GetRootGameObjects().SelectMany(g=>g.GetComponentsInChildren<VanController>(true)).Single();
            routes=W86RoadRepair.Routes().Where(r=>filter==null||filter.Split(',').Contains(r.Id)).ToList();
            if(routes.Count==0)throw new InvalidOperationException("No G46 routes");
            sandbox=EditorSceneManager.NewPreviewScene();physics=sandbox.GetPhysicsScene();
            int copied=0;
            foreach(var c in source.GetRootGameObjects().SelectMany(g=>g.GetComponentsInChildren<Collider>(true)))
            {
                if(!c.enabled||!c.gameObject.activeInHierarchy||c.isTrigger||c.attachedRigidbody)continue;
                if(!(c is BoxCollider)&&!(c is MeshCollider)&&!(c is TerrainCollider)&&!(c is CapsuleCollider)&&!(c is SphereCollider))continue;
                var go=new GameObject(c.name){hideFlags=HideFlags.DontSave};SceneManager.MoveGameObjectToScene(go,sandbox);
                go.transform.SetPositionAndRotation(c.transform.position,c.transform.rotation);go.transform.localScale=c.transform.lossyScale;
                Collider target=null;
                if(c is BoxCollider box){var q=go.AddComponent<BoxCollider>();q.center=box.center;q.size=box.size;target=q;}
                else if(c is MeshCollider mesh){var q=go.AddComponent<MeshCollider>();q.sharedMesh=mesh.sharedMesh;q.convex=mesh.convex;target=q;}
                else if(c is TerrainCollider ter){var q=go.AddComponent<TerrainCollider>();q.terrainData=ter.terrainData;target=q;}
                else if(c is SphereCollider sphere){var q=go.AddComponent<SphereCollider>();q.center=sphere.center;q.radius=sphere.radius;target=q;}
                else if(c is CapsuleCollider cap){var q=go.AddComponent<CapsuleCollider>();q.center=cap.center;q.radius=cap.radius;q.height=cap.height;q.direction=cap.direction;target=q;}
                if(target)target.sharedMaterial=c.sharedMaterial;copied++;
            }
            var clone=Object.Instantiate(original.gameObject);clone.name="G46 actual max-upgrade van";clone.hideFlags=HideFlags.DontSave;SceneManager.MoveGameObjectToScene(clone,sandbox);
            foreach(var b in clone.GetComponentsInChildren<MonoBehaviour>(true))if(!(b is VanController)&&!(b is VanUpgrades))Object.DestroyImmediate(b);
            van=clone.GetComponent<VanController>();body=clone.GetComponent<Rigidbody>();van.SendMessage("Awake");
            var upgrades=clone.GetComponent<VanUpgrades>();upgrades.SendMessage("Awake");
            for(int i=0;i<3;i++)upgrades.TrySetLevel((VanUpgradeCategory)i,VanUpgrades.MaxLevel);
            tick=typeof(VanController).GetMethod("FixedUpdate",BindingFlags.Instance|BindingFlags.NonPublic);
            spawnOffset=new[]{van.Front.Left,van.Front.Right,van.Rear.Left,van.Rear.Right}.Max(w=>w.radius-w.transform.localPosition.y+w.suspensionDistance*.5f)+.10f;
            report=new Report{scene=source.path,method="isolated local PhysicsScene, current map colliders, existing VanController.FixedUpdate + WheelColliders, public Throttle/Steer/Handbrake input, 0.02s steps; no OS/legacy key injection",startAtMax=upgrades.StartAtMax,topSpeed=van.MaxSpeedKmh,torque=van.MotorTorque,brakes=van.BrakeTorque,engine=upgrades.GetLevel(VanUpgradeCategory.Engine),handling=upgrades.GetLevel(VanUpgradeCategory.Handling),brakeLevel=upgrades.GetLevel(VanUpgradeCategory.Brakes)};
            rows=new List<Row>();index=direction=0;Running=true;Begin();EditorApplication.update+=Update;
            return $"G46 driving {routes.Count} routes x2; {copied} static colliders; max {report.topSpeed} km/h, engine/brakes/handling {report.engine}/{report.brakeLevel}/{report.handling}";
        }
        static Vector3 Point(float s)=>routes[index].At(direction==0?s:routes[index].Length-s);
        static void Begin()
        {
            var r=routes[index];minS=Mathf.Min(2.8f,r.Length*.12f);endS=r.Length-minS;
            var p=Point(minS);var d=Point(Mathf.Min(endS,minS+1))-p;
            van.ResetUpright(p+Vector3.up*spawnOffset,Mathf.Atan2(d.x,d.z)*Mathf.Rad2Deg);body.isKinematic=false;
            van.Throttle=van.Steer=0;van.Handbrake=true;Physics.SyncTransforms();
            for(int k=0;k<90;k++){tick.Invoke(van,null);physics.Simulate(.02f);}
            van.Handbrake=false;seconds=stuck=0;progress=bestProgress=minS;
            current=new Row{id=r.Id,direction=direction==0?"A_to_B":"B_to_A",length=r.Length,minUpright=1};
        }
        static void Update()
        {
            try
            {
                // Bound each callback so the Editor and shared bridge remain responsive.
                for(int n=0;n<250&&Running;n++)
                {
                    var r=routes[index];var p=body.position;float closest=progress,best=float.MaxValue;
                    for(float s=Mathf.Max(minS,progress-3);s<=Mathf.Min(endS,progress+12);s+=.35f)
                    {var q=Point(s);float ds=(new Vector2(q.x-p.x,q.z-p.z)).sqrMagnitude;if(ds<best){best=ds;closest=s;}}
                    progress=closest;float deviation=Mathf.Sqrt(best);current.maxDeviation=Mathf.Max(current.maxDeviation,deviation);
                    current.maxSpeed=Mathf.Max(current.maxSpeed,Mathf.Abs(van.SpeedKmh));current.minUpright=Mathf.Min(current.minUpright,Vector3.Dot(van.transform.up,Vector3.up));
                    if(progress>bestProgress+.25f){bestProgress=progress;stuck=0;}else stuck+=.02f;
                    if(progress>=endS-1.1f){Finish(deviation<r.Width*.5f?"PASS":"FAIL","completed route extent");continue;}
                    if(stuck>9||seconds>r.Length/1.2f+20||p.y<Point(progress).y-3||current.minUpright<.45f)
                    {Finish("FAIL",$"stuck/timeout/rollover at ({p.x:0.0},{p.y:0.0},{p.z:0.0}); surface={Point(progress).y:0.00}; deviation={deviation:0.00}");continue;}
                    float speed=Mathf.Abs(van.SpeedKmh);var target=Point(Mathf.Min(endS,progress+Mathf.Clamp(3+speed*.1f,3,6)));
                    var local=van.transform.InverseTransformPoint(target);float angle=Mathf.Atan2(2.8f*2*local.x,Mathf.Max(1,local.x*local.x+local.z*local.z))*Mathf.Rad2Deg;
                    float maxAngle=Mathf.Lerp(van.MaxSteerAngle,van.HighSpeedSteerAngle,Mathf.InverseLerp(10,90,speed));van.Steer=Mathf.Clamp(angle/maxAngle,-1,1);
                    float desired=Mathf.Lerp(24,9,Mathf.Clamp01(Mathf.Abs(angle)/28));if(r.Width<4.5f)desired=Mathf.Min(desired,14);
                    van.Throttle=speed<desired-1?.7f:speed>desired+1?-.35f:.10f;van.Handbrake=false;
                    tick.Invoke(van,null);physics.Simulate(.02f);seconds+=.02f;current.steps++;
                }
            }
            catch(Exception e){File.WriteAllText(Review+"/drive_exception.txt",e.ToString());Stop();throw;}
        }
        static void Finish(string result,string reason)
        {
            current.result=result;current.reason=reason;current.progress=progress;current.seconds=seconds;rows.Add(current);report.rows=rows.ToArray();File.WriteAllText(Review+"/drive_results.json",JsonUtility.ToJson(report,true));
            if(++direction>=2){direction=0;index++;}if(index>=routes.Count){Stop();return;}Begin();
        }
        public static void Stop()
        {
            EditorApplication.update-=Update;Running=false;if(sandbox.IsValid())EditorSceneManager.ClosePreviewScene(sandbox);
            Debug.Log($"[G46 drive] {rows?.Count ?? 0} direction results, {rows?.Count(r=>r.result=="PASS") ?? 0} passes");
        }
    }
}
