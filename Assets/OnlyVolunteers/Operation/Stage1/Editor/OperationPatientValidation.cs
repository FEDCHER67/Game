using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEngine;
using UnityEngine.Animations;
using UnityEngine.Playables;
using Object = UnityEngine.Object;

namespace OnlyVolunteers.Operation.Stage1.Editor
{
    public static class OperationPatientValidation
    {
        public static string Run()
        {
            const string folder="Working/Reviews/Operations/stage1";
            Directory.CreateDirectory(folder);
            const string path="Assets/OnlyVolunteers/Characters/SausageBuddy/Patient/SAUSAGE_BUDDY_PATIENT_v01.fbx";
            var importer=(ModelImporter)AssetImporter.GetAtPath(path);
            var original=AssetDatabase.LoadAssetAtPath<GameObject>("Assets/OnlyVolunteers/Characters/SausageBuddy/SAUSAGE_BUDDY_A_v04.fbx");
            var patient=Object.Instantiate(AssetDatabase.LoadAssetAtPath<GameObject>(path));
            var prefab=Object.Instantiate(AssetDatabase.LoadAssetAtPath<GameObject>(OperationStage1Builder.Root+"/Prefabs/Stage1_Patient_v01.prefab"));
            var graph=PlayableGraph.Create("G25 existing Buddy clip compatibility");
            var lines=new List<string>();
            try
            {
                var names=new HashSet<string>(patient.GetComponentsInChildren<Transform>(true).Select(t=>t.name));
                var bones=original.GetComponentsInChildren<Transform>(true).Where(t=>t.name.StartsWith("mixamorig:")).ToArray();
                var missing=bones.Where(t=>!names.Contains(t.name)).ToArray();
                lines.Add("import: "+importer.animationType+"; "+importer.avatarSetup+"; avatar="+importer.sourceAvatar.name+"; valid="+importer.sourceAvatar.isValid+"; preserveHierarchy="+importer.preserveHierarchy+"; compression="+importer.animationCompression);
                lines.Add("reference bones="+bones.Length+"; mapped="+(bones.Length-missing.Length)+"; missing="+string.Join(",",missing.Select(t=>t.name)));
                if(missing.Length!=0||!importer.sourceAvatar.isValid)throw new InvalidOperationException("Avatar/bone compatibility failed");
                foreach(var skin in patient.GetComponentsInChildren<SkinnedMeshRenderer>())
                {lines.Add(skin.name+" bones="+skin.bones.Length+" null="+skin.bones.Count(t=>t==null));if(skin.bones.Any(t=>t==null))throw new InvalidOperationException("Unmapped skin bone");}
                var anchors=prefab.GetComponent<OperationPatientAnchors>();
                for(int i=0;i<3;i++)
                {
                    prefab.transform.localScale=Vector3.one;
                    Vector3 position=anchors.Point(i,Vector3.zero);Vector3 guide=anchors.Point(i,Vector3.up*0.06f);
                    prefab.transform.localScale=Vector3.one*1.05f;
                    float positionError=Vector3.Distance(anchors.Point(i,Vector3.zero),position*1.05f);
                    float guideError=Vector3.Distance(anchors.Point(i,Vector3.up*0.06f),guide*1.05f);
                    float normalDot=Vector3.Dot(anchors.Normal(i),anchors.Marker(i).forward);
                    lines.Add(anchors.Marker(i).name+" parent="+anchors.Marker(i).parent.name+" scale1.05 positionError="+positionError+" guideError="+guideError+" normalDot="+normalDot);
                    if(positionError>0.00001f||guideError>0.00001f||normalDot<0.999f)throw new InvalidOperationException("Marker scaling failed");
                }
                var animator=patient.GetComponent<Animator>();if(animator==null)animator=patient.AddComponent<Animator>();
                animator.avatar=importer.sourceAvatar;animator.cullingMode=AnimatorCullingMode.AlwaysAnimate;animator.applyRootMotion=false;
                var clip=AssetDatabase.LoadAllAssetsAtPath("Assets/OnlyVolunteers/Characters/SausageBuddy/Animations/Walk_v04.fbx").OfType<AnimationClip>().First(c=>!c.name.StartsWith("__preview"));
                var bindings=AnimationUtility.GetCurveBindings(clip).Where(b=>b.type==typeof(Transform)).ToArray();
                int missingBindings=bindings.Count(b=>patient.transform.Find(b.path)==null);
                if(missingBindings!=0)throw new InvalidOperationException("Clip paths missing: "+missingBindings);
                var output=AnimationPlayableOutput.Create(graph,"Patient",animator);
                var playable=AnimationClipPlayable.Create(graph,clip);output.SetSourcePlayable(playable);
                graph.SetTimeUpdateMode(DirectorUpdateMode.Manual);graph.Play();graph.Evaluate(0.1f);
                var transforms=patient.GetComponentsInChildren<Transform>();var before=transforms.Select(t=>t.localRotation).ToArray();
                graph.Evaluate(0.3f);
                int moved=transforms.Where((t,i)=>Quaternion.Angle(before[i],t.localRotation)>0.01f).Count();
                lines.Add("PlayableGraph clip="+clip.name+" duration="+clip.length+" transformBindings="+bindings.Length+" missingBindings="+missingBindings+" animatedBones="+moved);
                if(moved==0)throw new InvalidOperationException("Buddy clip did not animate patient");
                lines.Add("PASS imported markers, scale 1.05, valid Generic avatar, complete bone paths, existing Buddy clip playback");
                File.WriteAllLines(folder+"/patient-import-validation.txt",lines);
                return string.Join("\n",lines);
            }
            finally {if(graph.IsValid())graph.Destroy();Object.DestroyImmediate(patient);Object.DestroyImmediate(prefab);}
        }
    }
}
