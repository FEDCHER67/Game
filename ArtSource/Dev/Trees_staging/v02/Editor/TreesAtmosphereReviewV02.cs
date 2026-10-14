using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.SceneManagement;
using Object = UnityEngine.Object;

namespace OnlyVolunteers.Map.Look.V3
{
    // Isolated review only: no pipeline/renderer asset or project setting is changed.
    public static class TreesAtmosphereReviewV02
    {
        public static string CaptureAndValidate(string take="v02")
        {
            if(SceneManager.GetActiveScene().path!=V19TreesCozyV02.ScenePath || EditorApplication.isPlaying)
                throw new InvalidOperationException("Open Trees_Test in Edit mode");
            var camera=GameObject.Find("Trees_ComparisonCamera").GetComponent<Camera>();
            var roots=SceneManager.GetActiveScene().GetRootGameObjects().Where(g=>g!=camera.gameObject && !g.GetComponent<Light>()).ToArray();
            var states=roots.Select(g=>g.activeSelf).ToArray();
            var pos=camera.transform.position; var rot=camera.transform.rotation;
            float size=camera.orthographicSize, aspect=camera.aspect;
            bool fog=RenderSettings.fog; var mode=RenderSettings.fogMode; var colour=RenderSettings.fogColor;
            float start=RenderSettings.fogStartDistance,end=RenderSettings.fogEndDistance;
            var clock=Shader.GetGlobalVector("_TreesPreviewClock");
            var messages=new List<string>();
            try
            {
                foreach(var root in roots) root.SetActive(false);
                Shader.SetGlobalVector("_TreesPreviewClock",new Vector4(3,0,0,1));
                string[] families={"forest_conifers","between_broadleaf","bare"};
                string[] sourceNames={"V19_tree_pine_a","V19_tree_oak_a","TREE_BARE_01_v19"};
                for(int i=0;i<families.Length;i++)
                {
                    var source=TreesCozyAuthoringV02.Sources().First(s=>s.name==sourceNames[i]);
                    var tree=(GameObject)PrefabUtility.InstantiatePrefab(V19TreesCozyV02.Resolve(source,"v19"));
                    try
                    {
                        tree.transform.position=Vector3.zero;
                        tree.GetComponent<LODGroup>()?.ForceLOD(0);
                        var b=TreesCozyAuthoringV02.VisualBounds(tree);
                        camera.transform.position=b.center+new Vector3(0,2,-32); camera.transform.LookAt(b.center);
                        camera.aspect=1; camera.orthographicSize=b.extents.y+1;
                        RenderSettings.fog=false;
                        string off=V19TreesCozyV02.Review+"/fog_"+families[i]+"_off_"+take+".png";
                        string on=V19TreesCozyV02.Review+"/fog_"+families[i]+"_on_"+take+".png";
                        TreesCozyReviewV02.Shot(camera,off,768,768);
                        RenderSettings.fog=true; RenderSettings.fogMode=FogMode.Linear;
                        RenderSettings.fogColor=camera.backgroundColor; RenderSettings.fogStartDistance=0; RenderSettings.fogEndDistance=60;
                        TreesCozyReviewV02.Shot(camera,on,768,768);
                        messages.Add(FogPixels(off,on,families[i]));
                        RenderSettings.fog=false;
                        // Refresh camera fog globals before the direct depth-pass draw.
                        var rt=new RenderTexture(16,16,24); var old=camera.targetTexture;
                        try {camera.targetTexture=rt;camera.Render();} finally {camera.targetTexture=old;rt.Release();Object.DestroyImmediate(rt);}
                        messages.Add(DepthOcclusion(camera,tree,families[i],take));
                    }
                    finally {Object.DestroyImmediate(tree);}
                }
                var shader=Shader.Find(V19TreesCozyV02.ShaderName);
                if(ShaderUtil.ShaderHasError(shader)) throw new InvalidDataException("Shader compile error after fog/depth variants rendered");
                string result=string.Join("\n",messages);
                TreesCozyAuthoringV02.WriteNew(V19TreesCozyV02.Review+"/fog_depth_validation_"+take+".txt",result);
                return result;
            }
            finally
            {
                for(int i=0;i<roots.Length;i++) roots[i].SetActive(states[i]);
                camera.transform.SetPositionAndRotation(pos,rot); camera.orthographicSize=size;camera.aspect=aspect;
                RenderSettings.fog=fog;RenderSettings.fogMode=mode;RenderSettings.fogColor=colour;
                RenderSettings.fogStartDistance=start;RenderSettings.fogEndDistance=end;
                Shader.SetGlobalVector("_TreesPreviewClock",clock);
            }
        }
        static string FogPixels(string off,string on,string family)
        {
            var a=new Texture2D(2,2);var b=new Texture2D(2,2);
            try
            {
                a.LoadImage(File.ReadAllBytes(off));b.LoadImage(File.ReadAllBytes(on));
                var ap=a.GetPixels();var bp=b.GetPixels();Color background=ap[0];
                double before=0,after=0;int pixels=0;
                for(int i=0;i<ap.Length;i++)
                {
                    var da=(Vector4)(ap[i]-background);if(da.sqrMagnitude<.02f)continue;
                    before+=da.sqrMagnitude;after+=((Vector4)(bp[i]-background)).sqrMagnitude;pixels++;
                }
                double ratio=after/before;
                if(pixels<100 || ratio>=.8)throw new InvalidDataException(family+" did not fade toward horizon colour: "+ratio+"; pixels="+pixels);
                return family+" URP fog PASS: "+pixels+" tree pixels; squared colour-distance ratio="+ratio.ToString("F4");
            }
            finally {Object.DestroyImmediate(a);Object.DestroyImmediate(b);}
        }
        static string DepthOcclusion(Camera camera,GameObject tree,string family,string take)
        {
            var rt=new RenderTexture(512,512,24,RenderTextureFormat.ARGB32);
            var blue=new Material(Shader.Find("Universal Render Pipeline/Unlit"));blue.SetColor("_BaseColor",Color.blue);blue.SetFloat("_Cull",0);
            var quad=GameObject.CreatePrimitive(PrimitiveType.Quad);quad.SetActive(false);
            var mesh=quad.GetComponent<MeshFilter>().sharedMesh;
            var command=new CommandBuffer{name="G23 depth-buffer occlusion proof"};
            Texture2D pixels=null;var oldActive=RenderTexture.active;
            try
            {
                rt.Create();command.SetRenderTarget(rt);
                command.ClearRenderTarget(true,true,Color.red,SystemInfo.usesReversedZBuffer?0:1);
                command.SetViewProjectionMatrices(camera.worldToCameraMatrix,GL.GetGPUProjectionMatrix(camera.projectionMatrix,true));
                var lod=tree.GetComponent<LODGroup>();
                var renderers=lod?lod.GetLODs()[0].renderers:tree.GetComponentsInChildren<Renderer>();
                foreach(var renderer in renderers)
                {
                    var filter=renderer.GetComponent<MeshFilter>();if(!filter)continue;
                    for(int sub=0;sub<renderer.sharedMaterials.Length;sub++)
                    {
                        var material=renderer.sharedMaterials[sub];int pass=material.FindPass("DepthOnly");
                        if(pass<0)throw new InvalidDataException("Missing DepthOnly pass");
                        command.DrawMesh(filter.sharedMesh,filter.transform.localToWorldMatrix,material,sub,pass);
                    }
                }
                // The blue plane is behind the tree. Only a working tree depth write can occlude it.
                var matrix=Matrix4x4.TRS(camera.transform.position+camera.transform.forward*60,camera.transform.rotation,Vector3.one*100);
                command.DrawMesh(mesh,matrix,blue,0,blue.FindPass("Unlit"));
                Graphics.ExecuteCommandBuffer(command);
                RenderTexture.active=rt;pixels=new Texture2D(512,512,TextureFormat.RGB24,false);
                pixels.ReadPixels(new Rect(0,0,512,512),0,0);pixels.Apply();
                var colours=pixels.GetPixels();int background=colours.Count(c=>c.b>.8f&&c.r<.1f&&c.g<.1f);
                int silhouette=colours.Length-background;
                if(background<colours.Length/2 || silhouette<100 || silhouette>colours.Length/2)
                    throw new InvalidDataException("Depth occlusion failed: "+family+"; silhouette="+silhouette+"; background="+background);
                string path=V19TreesCozyV02.Review+"/depth_occlusion_"+family+"_"+take+".png";
                if(File.Exists(path))throw new IOException("Capture exists: "+path);
                File.WriteAllBytes(path,pixels.EncodeToPNG());
                return family+" depth-buffer PASS: "+silhouette+" tree pixels occlude a later blue plane; "+background+" background pixels remain blue.";
            }
            finally
            {
                RenderTexture.active=oldActive;command.Release();rt.Release();Object.DestroyImmediate(rt);
                if(pixels)Object.DestroyImmediate(pixels);Object.DestroyImmediate(blue);Object.DestroyImmediate(quad);
            }
        }
    }
}
