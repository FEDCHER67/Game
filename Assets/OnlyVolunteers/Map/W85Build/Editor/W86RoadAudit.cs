using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEngine;
using UnityEngine.SceneManagement;
using Object = UnityEngine.Object;

namespace OnlyVolunteers.Map.W85
{
    public static class W86RoadAudit
    {
        const string Review = "C:/Dev/Game/Working/Reviews/W86Polish_2026-10-25/G46";
        [Serializable] public class Row { public string id, group, kind, result; public int samples, noFloor, obstructed, terrainIntrusions; public float length, worstFloorError, worstGrade; public string[] examples; }
        [Serializable] public class Report { public string scene, utc; public Row[] roads; public string groundFit, floatCheck; }
        public static string Run(string phase)
        {
            Physics.SyncTransforms();var scene=SceneManager.GetActiveScene();
            var terrain=scene.GetRootGameObjects().SelectMany(g=>g.GetComponentsInChildren<Terrain>()).First(t=>t.GetComponent<TerrainCollider>());
            var rows=new List<Row>();var sourceRoots=scene.GetRootGameObjects();
            foreach(var r in W86RoadRepair.Routes())
            {
                var row=new Row{id=r.Id,group=r.Group,kind=r.Kind,length=r.Length};var examples=new List<string>();
                float previousY=float.NaN;
                for(float s=0;s<=r.Length;s+=1f)
                {
                    var p=r.At(s);var tangent=(r.At(Mathf.Min(r.Length,s+1))-r.At(Mathf.Max(0,s-1))).normalized;
                    var hits=Physics.RaycastAll(p+Vector3.up*30,Vector3.down,65,~0,QueryTriggerInteraction.Ignore)
                        .Where(h=>h.collider.gameObject.scene==scene && !h.collider.attachedRigidbody && h.normal.y>.45f).OrderBy(h=>Mathf.Abs(h.point.y-p.y)).ToArray();
                    float floor=hits.Length>0?hits[0].point.y:float.NaN;row.samples++;
                    float delta=float.IsNaN(floor)?999:Mathf.Abs(floor-p.y);row.worstFloorError=Mathf.Max(row.worstFloorError,delta);
                    if(delta>.22f){row.noFloor++;if(examples.Count<5)examples.Add($"s={s:0} expected={p.y:0.00} floor={floor:0.00}");}
                    if(!float.IsNaN(previousY)&&!float.IsNaN(floor))row.worstGrade=Mathf.Max(row.worstGrade,Mathf.Abs(floor-previousY)*100);
                    previousY=floor;
                    var o=terrain.transform.position;var size=terrain.terrainData.size;
                    int hx=Mathf.Clamp((int)((p.x-o.x)/size.x*terrain.terrainData.holesResolution),0,terrain.terrainData.holesResolution-1),hz=Mathf.Clamp((int)((p.z-o.z)/size.z*terrain.terrainData.holesResolution),0,terrain.terrainData.holesResolution-1);
                    float ground=terrain.SampleHeight(p)+o.y;
                    if(ground>p.y+.22f && (r.Kind!="tunnel" || ground<p.y+5.5f) && terrain.terrainData.GetHoles(hx,hz,1,1)[0,0])
                    {row.terrainIntrusions++;if(examples.Count<5)examples.Add($"s={s:0} terrain={ground:0.00} above surface={p.y:0.00}");}
                    // 1.8m player capsule and a conservative van body clearance; inspect static obstructions, ignoring the van/player.
                    if(s>3 && s<r.Length-3)
                    {
                        var overlaps=Physics.OverlapBox(p+Vector3.up*1.38f,new Vector3(.93f,1.16f,2.35f),Quaternion.LookRotation(new Vector3(tangent.x,0,tangent.z)),~0,QueryTriggerInteraction.Ignore)
                            .Where(c=>c.gameObject.scene==scene && !(c is TerrainCollider) && !c.attachedRigidbody && !c.name.StartsWith("Road_") && !c.name.StartsWith("Street_") && !c.name.EndsWith("_deck") && c.bounds.max.y>p.y+.30f && c.bounds.min.y<p.y+2.55f).ToArray();
                        if(overlaps.Length>0){row.obstructed++;if(examples.Count<5)examples.Add($"s={s:0} collider={Path(overlaps[0].transform)}");}
                    }
                }
                row.result=row.noFloor==0&&row.terrainIntrusions==0&&row.obstructed==0?"PASS_GEOMETRY":"FAIL_GEOMETRY";row.examples=examples.ToArray();rows.Add(row);
            }
            int errors;var report=new Report{scene=scene.path,utc=DateTime.UtcNow.ToString("o"),roads=rows.ToArray(),groundFit=W85GroundFit.Run("C:/Dev/Game/Assets/OnlyVolunteers/Map/W85Build/Data/v02",terrain,out errors),floatCheck=W85FloatCheck.Run(scene,false)};
            File.WriteAllText(Review+"/geometry_"+phase+".json",JsonUtility.ToJson(report,true));
            string summary=$"G46 {phase}: {rows.Count} unique routes, {rows.Count(r=>r.result=="PASS_GEOMETRY")} geometry passes, {rows.Sum(r=>r.terrainIntrusions)} terrain intrusions, {rows.Sum(r=>r.obstructed)} obstructed samples";
            Debug.Log(summary);return summary;
        }
        static string Path(Transform t)=>t.parent?Path(t.parent)+"/"+t.name:t.name;

        public static void Render(string phase)
        {
            var views=new[]{new Vector3(748,10,675),new Vector3(805,13,560),new Vector3(1233,15,730)};
            var look=new[]{new Vector3(748,7,649),new Vector3(822,8,548),new Vector3(1233,.3f,706)};
            var names=new[]{"junction","tunnel","island"};var timings=new List<string>();
            var go=new GameObject("G46 temporary audit camera"){hideFlags=HideFlags.HideAndDontSave};var cam=go.AddComponent<Camera>();
            cam.nearClipPlane=.1f;cam.farClipPlane=1400;cam.fieldOfView=65;cam.allowHDR=true;
            var rt=new RenderTexture(1280,720,24,RenderTextureFormat.ARGB32);rt.Create();cam.targetTexture=rt;
            var old=RenderTexture.active;var tex=new Texture2D(1280,720,TextureFormat.RGB24,false);
            try
            {
                for(int i=0;i<views.Length;i++)
                {
                    go.transform.position=views[i];go.transform.LookAt(look[i]);for(int k=0;k<3;k++)cam.Render();
                    var durations=new List<double>();
                    for(int k=0;k<12;k++)
                    {
                        var sw=System.Diagnostics.Stopwatch.StartNew();cam.Render();RenderTexture.active=rt;tex.ReadPixels(new Rect(0,0,1280,720),0,0);tex.Apply();sw.Stop();durations.Add(sw.Elapsed.TotalMilliseconds);
                    }
                    File.WriteAllBytes(Review+"/"+names[i]+"_"+phase+".png",tex.EncodeToPNG());durations.Sort();timings.Add(names[i]+", median_ms="+durations[6].ToString("0.00",System.Globalization.CultureInfo.InvariantCulture)+", render_fps="+(1000/durations[6]).ToString("0.0",System.Globalization.CultureInfo.InvariantCulture));
                }
                File.WriteAllLines(Review+"/render_timing_"+phase+".csv",timings);
            }
            finally{RenderTexture.active=old;cam.targetTexture=null;Object.DestroyImmediate(tex);rt.Release();Object.DestroyImmediate(rt);Object.DestroyImmediate(go);}
        }
    }
}
